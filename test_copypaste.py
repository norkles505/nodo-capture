"""Prueba copiar / pegar / duplicar nodos (Ctrl+C, Ctrl+V, Shift+D)."""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtWidgets import QApplication
app = QApplication([])
import main
import copypaste
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


def count(sc):
    return len(project._items(main, sc))


w = main.Window()
sh = w.scenes["shader"]
val = mk(w, "shader", "ShaderNodeValue", 0, 0)
mth = mk(w, "shader", "ShaderNodeMath", 300, 0)
mth.pvals["operation"] = "MULTIPLY"
mth.vals[mth.spec["inputs"][1]["identifier"]] = 7.5
other = mk(w, "shader", "ShaderNodeTexCoord", 0, 300)
sh.connect_socks(sock(val, "out"), sock(mth, "in", 0))
sh.connect_socks(sock(other, "out"), sock(mth, "in", 1))
sh.clearSelection()
w.mode.setCurrentIndex(0)

# ---- copiar y pegar dos nodos que estan unidos
val.setSelected(True)
mth.setSelected(True)
copypaste.copy_selected(w)
check("se copiaron 2 nodos y 1 cable", len(copypaste.CLIP["nodes"]) == 2 and len(copypaste.CLIP["links"]) == 1,
      (len(copypaste.CLIP["nodes"]), copypaste.CLIP["links"]))
copypaste.paste(w)
check("pegar crea 2 nodos mas", count(sh) == 5, count(sh))
check("el cable interno se copia (el externo no)", len(sh.links) == 3, len(sh.links))
news = [n for n in sh.selectedItems()]
check("lo pegado queda seleccionado", len(news) == 2 and all(n not in (val, mth) for n in news))
nm = next(n for n in news if n.spec["idname"] == "ShaderNodeMath")
check("Math pegado: menu y valor", nm.pvals["operation"] == "MULTIPLY"
      and nm.vals[nm.spec["inputs"][1]["identifier"]] == 7.5)
check("el original no cambio", mth.pvals["operation"] == "MULTIPLY" and mth.isSelected() is False)

# ---- se puede pegar varias veces y las copias son independientes
nm.pvals["operation"] = "ADD"
copypaste.paste(w)
check("pegar otra vez crea 2 mas", count(sh) == 7, count(sh))
nm2 = [n for n in sh.selectedItems() if n.spec["idname"] == "ShaderNodeMath"][0]
check("la segunda copia sale como el original, no como la editada", nm2.pvals["operation"] == "MULTIPLY")

# ---- duplicar un solo nodo con Color Ramp
sh.clearSelection()
ramp = mk(w, "shader", "ShaderNodeValToRGB", 600, 300)
ramp.ramp["stops"].append({"pos": 0.5, "color": [1.0, 0.0, 0.0, 1.0]})
ramp.ramp["stops"].sort(key=lambda s: s["pos"])
ramp.setSelected(True)
before = count(sh)
copypaste.duplicate(w)
check("duplicar crea 1 nodo", count(sh) == before + 1)
dup = sh.selectedItems()[0]
check("Color Ramp duplicado con sus marcadores", len(dup.ramp["stops"]) == len(ramp.ramp["stops"]))
check("el duplicado es independiente", dup.ramp is not ramp.ramp)
check("duplicado desplazado", dup.pos().x() == ramp.pos().x() + copypaste.DUP_OFFSET)
check("duplicar no pisa lo copiado", len(copypaste.CLIP["nodes"]) == 2)

# ---- Frame y Reroute
sh.clearSelection()
fr = mk(w, "shader", "NodeFrame", -50, -50)
fr.w, fr.h, fr.label = 500.0, 300.0, "Grupo"
rr = mk(w, "shader", "NodeReroute", 100, 100)
fr.setSelected(True)
rr.setSelected(True)
copypaste.copy_selected(w)
copypaste.paste(w)
fnew = next(n for n in sh.selectedItems() if n.spec["idname"] == "NodeFrame")
check("Frame pegado con etiqueta y tamano", fnew.label == "Grupo" and fnew.w == 500.0 and fnew.h == 300.0)

# ---- lo pegado queda centrado en el cursor (sin mouse en el viewport -> centro de la vista)
c = copypaste._cursor_pos(w)
sh.clearSelection()
val.setSelected(True)
copypaste.copy_selected(w)
copypaste.paste(w)
n = sh.selectedItems()[0]
mid = n.mapToScene(n.w / 2, n.h / 2)
check("centrado en el cursor", abs(mid.x() - c.x()) < 1 and abs(mid.y() - c.y()) < 1, (mid, c))

# ---- sin seleccion no hace nada; otro editor no pega
sh.clearSelection()
n0 = count(sh)
copypaste.duplicate(w)
check("duplicar sin seleccion no hace nada", count(sh) == n0)
w.mode.setCurrentIndex(1)
comp = w.scenes["compositor"]
copypaste.paste(w)
check("no se pega en el otro editor", count(comp) == 0)

# ---- cambios sin guardar
w.mode.setCurrentIndex(0)
check("pegar marca cambios sin guardar", project.snapshot(w) != w._snap)

print("RESULTADO:", "TODO OK" if ok else "HAY FALLOS")
