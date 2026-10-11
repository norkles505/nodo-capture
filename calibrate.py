"""Recalibra EXTRA_H en main.py para que la altura de cada nodo coincida con Blender."""
import os, sys, re, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from PySide6.QtWidgets import QApplication
app = QApplication([])
import main

real = json.load(open(os.path.join(main.DATA, "real_dimensions_shader.json"), encoding="utf-8"))
SKIP = {"ShaderNodeTexImage", "ShaderNodeGroup"}   # el alto real viene de nodos con imagen/sockets cargados
extra = dict(main.EXTRA_H)
log = []
for s in main.CATALOG["shader"]:
    idn = s["idname"]
    r = real.get(idn)
    if not r or idn in SKIP:
        continue
    n = main.NodeItem(s, main.category(idn, "shader"))
    if idn == "ShaderNodeMix":
        n.pvals["data_type"] = "RGBA"
        n.relayout()
    dh = n.h - r["h"]
    if abs(dh) > 14:
        log.append(f"SKIP {idn} dh={dh:.1f}")
        continue
    if idn in extra or abs(dh) > 1.0:
        new = round(extra.get(idn, 0.0) - dh, 1)
        log.append(f"{idn}: {extra.get(idn, 0.0)} -> {new} (dh {dh:.1f})")
        extra[idn] = new

body = "EXTRA_H = {" + ",\n           ".join(f'"{k}": {v}' for k, v in extra.items()) + "}\n"
path = os.path.join(here, "main.py")
txt = open(path, encoding="utf-8", newline="").read()
new_txt, cnt = re.subn(r"EXTRA_H = \{.*?\}\r?\n", lambda m: body, txt, count=1, flags=re.S)
assert cnt == 1
open(path, "w", encoding="utf-8", newline="").write(new_txt)
open(os.path.join(here, "calibrate_log.txt"), "w", encoding="utf-8").write("\n".join(log))
print("ok", len(log))
