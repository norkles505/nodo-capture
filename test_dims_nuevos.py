import os, sys, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
out = open(os.path.join(HERE, "res_dims_nuevos.txt"), "w", encoding="utf-8")
from PySide6.QtWidgets import QApplication
app = QApplication([])
import main
real = json.load(open(os.path.join(main.DATA, "real_dimensions_shader.json"), encoding="utf-8"))
NUEVOS = ["FunctionNodeInputBool","FunctionNodeInputInt","FunctionNodeInputMenu","FunctionNodeInputVector","GeometryNodeInputSceneTime","GeometryNodeMenuSwitch","GeometryNodeRepeatInput","GeometryNodeRepeatOutput","NodeClosureInput","NodeClosureOutput","NodeCombineBundle","NodeEvaluateClosure","NodeJoinBundle","NodeSeparateBundle"]
by = {s["idname"]: s for s in main.CATALOG["shader"]}
print("idname | real w x h | app w x h | dh", file=out)
for i in NUEVOS:
    r = real[i]; n = main.NodeItem(by[i], main.category(i, "shader"))
    print(i, "|", r["w"], "x", r["h"], "|", round(n.w,1), "x", round(n.h,1), "| dh", round(n.h - r["h"],1), "| EXTRA_H" , main.EXTRA_H.get(i), file=out)
# resumen global de desajuste en los ya existentes
bad = 0; tot = 0
for s in main.CATALOG["shader"]:
    i = s["idname"]
    if i in real and i not in NUEVOS and i not in ("ShaderNodeTexImage","ShaderNodeGroup"):
        n = main.NodeItem(s, main.category(i, "shader")); tot += 1
        if abs(n.h - real[i]["h"]) > 1.0: bad += 1
print("existentes con |dh|>1:", bad, "de", tot, file=out)
out.close()
