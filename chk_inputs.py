import json
from pathlib import Path

d = Path(__file__).parent / "data"
cat = json.loads((d / "compositor_nodes.json").read_text(encoding="utf-8"))
want = ["Bool", "Int", "String", "Vector", "Rotation", "Object", "Font", "Menu", "RGB", "Value", "Normal", "Color"]
print("total nodos compositor:", len(cat))
for s in cat:
    idn = s["idname"]
    if idn.startswith(("FunctionNode", "GeometryNode")) or any(w in idn for w in want):
        print(idn, "|", s["label"], "| outs:", [(o["name"], o.get("stype")) for o in s["outputs"]],
              "| ins:", len(s["inputs"]), "| props:", [p["id"] for p in s["props"]])
