"""Comprueba que los nodos compartidos agregados al compositor se crean y se dibujan sin errores."""
import os, sys, json, traceback
os.environ["QT_QPA_PLATFORM"] = "offscreen"
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QRectF
app = QApplication([])
import main

new = [s for s in main.CATALOG["compositor"] if not s["idname"].startswith("CompositorNode")]
sc = main.NodeScene("compositor")
ok, bad = 0, []
for s in new:
    try:
        n = main.NodeItem(s, main.category(s["idname"], "compositor"))
        sc.addItem(n)
        img = QImage(int(n.w) + 40, int(n.h) + 40, QImage.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        sc.render(p, QRectF(img.rect()), n.sceneBoundingRect().adjusted(-20, -20, 20, 20))
        p.end()
        sc.removeItem(n)
        ok += 1
    except Exception:
        bad.append((s["idname"], traceback.format_exc().strip().splitlines()[-1]))

cats = {}
for s in new:
    cats.setdefault(main.category(s["idname"], "compositor"), []).append(s["label"])
out = f"nuevos={len(new)} ok={ok} fallan={len(bad)}\n" + "\n".join(f"  {i}: {e}" for i, e in bad)
out += "\n\n" + json.dumps(cats, ensure_ascii=False, indent=1)
open(os.path.join(here, "res_extra.txt"), "w", encoding="utf-8").write(out)
print("listo")
