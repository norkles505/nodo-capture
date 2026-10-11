import os
import sys
import traceback

os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PySide6.QtWidgets import QApplication
import main

app = QApplication(sys.argv)
w = main.Window()
w.scale_spin.setValue(1)
for idx, (mode, specs) in enumerate(main.CATALOG.items()):
    sc = w.scenes[mode]
    nodes = []
    for i, s in enumerate(specs):
        try:
            n = main.NodeItem(s, main.category(s["idname"], mode))
            n.setPos((i % 10) * 320, (i // 10) * 700)
            sc.addItem(n)
            nodes.append(n)
        except Exception:
            print("FAIL", s["idname"])
            traceback.print_exc()
    try:
        a = next(n for n in nodes if n.spec["outputs"])
        b = next(n for n in nodes if n is not a and n.spec["inputs"])
        sc.connect_socks(a.socks[("out", a.spec["outputs"][0]["identifier"])],
                         b.socks[("in", b.spec["inputs"][0]["identifier"])])
        nodes[3].hide_unused = True
        sc.sync()
    except Exception:
        print("FAIL connect")
        traceback.print_exc()
    w.mode.setCurrentIndex(idx)
    w.export("png", False, path=os.path.join(HERE, "data", f"test_{mode}.png"))
    w.export("svg", False, path=os.path.join(HERE, "data", f"test_{mode}.svg"))
    print(mode, len(nodes), "nodos OK", flush=True)
pr = next(n for n in w.scenes["shader"].nodes() if n.spec["idname"] == "ShaderNodeBsdfPrincipled")
print("Principled alto cerrado:", pr.h, "ancho:", pr.w)
pr.panel_open["Coat"] = True
w.scenes["shader"].sync()
print("Principled alto con Coat abierto:", pr.h)
print("FIN")
