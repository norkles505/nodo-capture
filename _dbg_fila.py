"""Renderiza el nodo Multiple Images a PNG (escala 4) y anota donde caen los separadores de la fila."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

app = QApplication([])
import main as M

sc = M.NodeScene("compositor")
sc.exporting = True
spec = next(s for s in M.CATALOG["compositor"] if s["idname"] == "CompositorNodeImage")
lines = []
for w in (None, 392.0, 446.0):
    n = M.make_node(spec, "compositor")
    n.load_image("Multiple Images.png", 3)
    if w:
        n.set_width(w)
    sc.addItem(n)
    n.setPos(0, 0)
    rect = QRectF(-4, -4, n.w + 8, n.h + 8)
    for scale in (1, 4):
        img = QImage(int(rect.width() * scale), int(rect.height() * scale), QImage.Format_ARGB32)
        img.fill(M.BG)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        sc.render(p, QRectF(img.rect()), rect)
        p.end()
        if scale == 4:
            img.save(str(HERE / f"out_fila_{int(n.w)}.png"))
        else:
            row = next(r for r in n.rows if r["k"] == "imgloaded")
            y = int(row["y"] + M.IMG_TOP + 2.5 + 4)
            xs, ref = [], M.FIELD.rgb()
            for x in range(img.width()):
                c = img.pixelColor(x, y)
                d = abs(c.red() - M.FIELD.red()) + abs(c.green() - M.FIELD.green()) + abs(c.blue() - M.FIELD.blue())
                if d > 40:
                    xs.append(x - 4)
            lines.append(f"w={n.w:.0f} h={n.h:.0f} fila_y={row['y']:.1f} columnas_no_campo={xs}")
    sc.removeItem(n)
(HERE / "res_fila.txt").write_text("\n".join(lines), encoding="utf-8")
print("listo")
