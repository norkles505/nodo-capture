"""Prueba guardar/abrir proyectos: guarda, abre en una ventana nueva y compara."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from PySide6.QtWidgets import QApplication
app = QApplication([])
import main
import project

ok = True


def check(label, cond, extra=""):
    global ok
    ok &= bool(cond)
    print(("OK   " if cond else "FAIL ") + label, extra)


def mk(win, mode, idn, x, y):
    spec = next(s for s in main.CATALOG[mode] if s["idname"] == idn)
    n = main.make_node(spec, mode)
    n.setPos(x, y)
    win.scenes[mode].addItem(n)
    return n


def sock(n, kind, i=0):
    ident = n.spec["inputs" if kind == "in" else "outputs"][i]["identifier"]
    return n.socks[(kind, ident)]


w1 = main.Window()
check("ventana sin cambios no esta sucia", project.snapshot(w1) == w1._snap)

# ---- Shader: Value -> Reroute -> Math (con menu y valor cambiados), Color Ramp, TexCoord, Frame
sh = w1.scenes["shader"]
val = mk(w1, "shader", "ShaderNodeValue", 0, 0)
rr = mk(w1, "shader", "NodeReroute", 200, 20)
mth = mk(w1, "shader", "ShaderNodeMath", 300, 0)
mth.pvals["operation"] = "MULTIPLY"
mth.vals[mth.spec["inputs"][1]["identifier"]] = 7.5
mth.hide_unused = True
sh.connect_socks(sock(val, "out"), rr.socks[("in", "Input")])
sh.connect_socks(rr.socks[("out", "Output")], sock(mth, "in", 0))
ramp = mk(w1, "shader", "ShaderNodeValToRGB", 0, 300)
ramp.ramp["stops"].append({"pos": 0.5, "color": [1.0, 0.0, 0.0, 1.0]})
ramp.ramp["stops"].sort(key=lambda s: s["pos"])
ramp.ramp["active"], ramp.ramp["interp"] = 1, "Constant"
tc = mk(w1, "shader", "ShaderNodeTexCoord", 400, 300)
tc.pvals["object"] = "Cube"
fr = mk(w1, "shader", "NodeFrame", -40, -40)
fr.w, fr.h, fr.label = 700.0, 420.0, "Mi grupo"
sh.sync()

# ---- Compositor: Image con imagen cargada y ancho cambiado
img = mk(w1, "compositor", "CompositorNodeImage", 0, 0)
img.load_image("foto.png", 2, "sRGB")
img.set_width(232)
w1.scenes["compositor"].sync()
w1.scale_spin.setValue(3)
w1.mode.setCurrentIndex(1)

path = os.path.join(tempfile.mkdtemp(), "prueba" + project.EXT)
project.write(w1, path)
check("el archivo existe", Path(path).exists())
check("sin .tmp sobrante", not Path(path + ".tmp").exists())

# ---- abrir en una ventana nueva
w2 = main.Window()
skipped = project.read_into(w2, path)
check("no se omitio ningun nodo", skipped == 0, skipped)
check("contenido identico", project.snapshot(w1) == project.snapshot(w2))
check("modo", w2.mode.currentData() == "compositor", w2.mode.currentData())
check("escala", w2.scale_spin.value() == 3, w2.scale_spin.value())

s2 = w2.scenes["shader"]
byid = {}
for n in s2.items():
    if hasattr(n, "spec") and hasattr(n, "socks") and n.parentItem() is None:
        byid.setdefault(n.spec["idname"], n)
check("cantidad de nodos shader", len(project._items(project._M(w2), s2)) == 6, len(project._items(project._M(w2), s2)))
check("cables", len(s2.links) == 2, len(s2.links))
check("Math: menu", byid["ShaderNodeMath"].pvals["operation"] == "MULTIPLY")
check("Math: valor", byid["ShaderNodeMath"].vals[byid["ShaderNodeMath"].spec["inputs"][1]["identifier"]] == 7.5)
check("Math: ocultar sin conectar", byid["ShaderNodeMath"].hide_unused is True)
rp = byid["ShaderNodeValToRGB"].ramp
check("Color Ramp: marcadores", len(rp["stops"]) == 3 and rp["interp"] == "Constant" and rp["active"] == 1, rp)
check("TexCoord: objeto", byid["ShaderNodeTexCoord"].pvals["object"] == "Cube")
check("Frame: etiqueta y tamano", byid["NodeFrame"].label == "Mi grupo" and byid["NodeFrame"].w == 700.0)
im2 = next(n for n in w2.scenes["compositor"].nodes())
check("Image: imagen y ancho", im2.img_loaded and im2.img_loaded["name"] == "foto.png" and im2.w == 232, (im2.img_loaded, im2.w))

# ---- cambios sin guardar y archivos malos
w2.scenes["shader"].clearSelection()
byid["ShaderNodeMath"].setPos(0, 999)
check("mover un nodo marca cambios", project.snapshot(w2) != w2._snap)
bad = os.path.join(os.path.dirname(path), "malo.nodocap")
Path(bad).write_text("esto no es json", encoding="utf-8")
try:
    project.read_into(w2, bad)
    check("JSON malo da error", False)
except ValueError:
    check("JSON malo da error", True)
Path(bad).write_text('{"app": "otra-cosa", "scenes": {}}', encoding="utf-8")
try:
    project.read_into(w2, bad)
    check("archivo ajeno da error", False)
except ValueError:
    check("archivo ajeno da error", True)

print("RESULTADO:", "TODO OK" if ok else "HAY FALLOS")
