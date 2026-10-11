
import os, sys, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(__file__))
from PySide6.QtWidgets import QApplication
app = QApplication([])
import main
real = json.load(open(os.path.join(main.DATA, "real_dimensions_shader.json"), encoding="utf-8"))
rows = []
for s in main.CATALOG["shader"]:
    r = real.get(s["idname"])
    if not r:
        continue
    n = main.NodeItem(s, main.category(s["idname"], "shader"))
    if s["idname"] == "ShaderNodeMix":      # el alto real de Blender se midio con Mix en modo Color
        n.pvals["data_type"] = "RGBA"
        n.relayout()
    rows.append({"id": s["idname"].replace("ShaderNode", ""), "w_app": n.w, "w_real": r["w"],
                 "h_app": round(n.h, 1), "h_real": r["h"], "dh": round(n.h - r["h"], 1)})
rows.sort(key=lambda x: -abs(x["dh"]))
json.dump(rows, open(os.path.join(os.path.dirname(__file__), "compare.json"), "w"), indent=0)
print("ok", len(rows))
