"""Mide el borde de un cable: pixeles de arriba a abajo cruzando el hilo (en su punto medio)."""
import os
import sys
import traceback
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
out = []
try:
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QApplication
    import main as M

    app = QApplication([])
    sc = M.NodeScene("shader")
    idn = {s["idname"]: s for s in M.CATALOG["shader"]}
    ns = []
    for k, name in enumerate(("ShaderNodeValue", "ShaderNodeMath")):
        spec = idn[name]
        n = M.NodeItem(spec, M.category(name, "shader"))
        n.setPos(k * 400, 0)
        sc.addItem(n)
        ns.append(n)
    o = next(s for (k, _), s in ns[0].socks.items() if k == "out")
    i = next(s for (k, _), s in ns[1].socks.items() if k == "in")
    sc.connect_socks(o, i)
    l = sc.links[0]
    mid = l.path().pointAtPercent(0.5)
    out.append(f"punto medio {mid.x():.1f},{mid.y():.1f}")
    S = 8
    rect = QRectF(mid.x() - 20, mid.y() - 20, 40, 40)
    img = QImage(40 * S, 40 * S, QImage.Format_ARGB32)
    img.fill(M.BG)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    sc.exporting = True
    sc.clearSelection()
    sc.render(p, QRectF(img.rect()), rect)
    p.end()
    x = 20 * S
    for yy in range(-6, 7):
        out.append(f"dy={yy:+3d}  {img.pixelColor(x, int((20 + yy) * S)).name()}")
except Exception:
    out.append(traceback.format_exc())
(HERE / "res_wire.txt").write_text("\n".join(out), encoding="utf-8")
