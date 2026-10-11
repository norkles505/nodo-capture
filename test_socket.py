"""Mide el borde de los sockets: colores de los pixeles de izquierda a derecha cruzando un socket."""
import os
import sys
import traceback
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
out = []
try:
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QApplication
    import main as M

    app = QApplication([])
    sc = M.NodeScene("shader")
    spec = next(s for s in M.CATALOG["shader"] if s["idname"] == "ShaderNodeMath")
    n = M.NodeItem(spec, M.category(spec["idname"], "shader"))
    sc.addItem(n)
    sk = next(s for (k, _), s in n.socks.items() if k == "in" and s.isVisible())
    c = sk.scenePos()
    out.append(f"socket en {c.x():.1f},{c.y():.1f}  pen={sk.pen().color().name()} w={sk.pen().widthF()} brush={sk.brush().color().name()}")
    S = 8
    rect = QRectF(c.x() - 20, c.y() - 20, 40, 40)
    img = QImage(40 * S, 40 * S, QImage.Format_ARGB32)
    img.fill(M.BG)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    sc.exporting = True
    sc.render(p, QRectF(img.rect()), rect)
    p.end()
    y = 20 * S
    for x in range(8, 33):
        px = img.pixelColor(int(x * S), y)
        out.append(f"x={x - 20:+3d}  {px.name()}")
    img.save(str(HERE / "data" / "test_socket.png"))
except Exception:
    out.append(traceback.format_exc())
(HERE / "res_socket.txt").write_text("\n".join(out), encoding="utf-8")
