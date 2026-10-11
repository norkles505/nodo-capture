"""Parche: afina la fila de imagen cargada (Multiple Images) para que coincida con Blender.
Hace copia de seguridad en main.py.pre_fila.bak y no se puede aplicar dos veces."""
import shutil
from pathlib import Path

SRC = Path(__file__).parent / "main.py"
txt = SRC.read_text(encoding="utf-8")
if "FILA_V2" in txt:
    raise SystemExit("ya aplicado")
shutil.copy(SRC, SRC.with_name("main.py.pre_fila.bak"))

NEW_FN = '''    def paint_imgloaded(self, p, r):
        """FILA_V2 - fila de imagen cargada (template_ID de Blender):
        selector | nombre (se estira) | usuarios | escudo | duplicar | carpeta | X.
        Medidas de la captura de Blender: selector ~30 u, iconos 20 u, usuarios ~0.108 del ancho."""
        from PySide6.QtGui import QFontMetrics
        d = self.img_loaded or {}
        x, fw = PAD, self.w - 2 * PAD
        yy, bh = r["y"] + IMG_TOP, 20.0
        wide = self.w >= 200
        sw = 30.5 if wide else 21.0
        ic_w = [20.0, 20.0, 20.0, 20.0]                  # escudo, duplicar, carpeta, X
        users = max(24.0, 0.108 * self.w)
        gw = fw - sw - 1
        rest = users + sum(ic_w)
        if gw - rest < 40:                                # nodo estrecho: se encogen los botones, no el nombre
            f = max(0.5, (gw - 40) / rest)
            users *= f
            ic_w = [v * f for v in ic_w]
        name_w = gw - users - sum(ic_w)

        # --- selector de imagen (icono + flechita)
        path = self.field(p, QRectF(x, yy, sw, bh), MENU)
        p.setPen(QPen(globals().get("WCOL_OUT", {}).get("menu", FIELD_LINE), FIELD_LINE_W))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        isz = 13.0 if wide else 10.0
        ic = QRectF(x + (4.5 if wide else 3.5), yy + (bh - isz) / 2, isz, isz)
        p.setPen(Qt.NoPen)
        p.setBrush(TXT)
        p.drawRoundedRect(ic, 2.0, 2.0)
        pt = lambda fx, fy: QPointF(ic.left() + fx * ic.width(), ic.top() + fy * ic.height())
        p.setBrush(MENU)
        p.drawPolygon(QPolygonF([pt(.12, .86), pt(.38, .50), pt(.55, .70), pt(.68, .56), pt(.88, .86)]))
        p.drawEllipse(pt(.29, .28), isz * 0.105, isz * 0.105)
        cx, cy = x + sw - (5.0 if wide else 4.5), yy + bh / 2
        hw = 2.6 if wide else 2.2
        p.setPen(QPen(MENU_ITEM, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(cx - hw, cy - 1.2), QPointF(cx, cy + 1.4), QPointF(cx + hw, cy - 1.2)]))

        # --- grupo: nombre | usuarios | iconos
        gx = x + sw + 1
        grp = QRectF(gx, yy, gw, bh)
        path = self.field(p, grp, FIELD)
        p.setPen(QPen(FIELD_LINE, FIELD_LINE_W))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        edges, acc = [], grp.left()
        for wv in [name_w, users] + ic_w:
            edges.append((acc, acc + wv))
            acc += wv
        for a, b in edges[:-1]:
            p.drawLine(QPointF(b, grp.top()), QPointF(b, grp.bottom()))
        fm = QFontMetrics(NodeItem.F)
        short = self._fit_text(fm, d.get("name", ""), name_w - 13.5)
        p.setPen(TXT)
        p.drawText(QRectF(edges[0][0] + 7.5, yy, name_w - 7.5, bh), AL, short)
        p.drawText(QRectF(edges[1][0], yy, edges[1][1] - edges[1][0], bh), Qt.AlignCenter, str(d.get("users", 1)))
        c = lambda i: QPointF((edges[i][0] + edges[i][1]) / 2, yy + bh / 2)
        pen = QPen(TXT, 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

        q = c(2)                                                     # escudo (usuario falso)
        sh = QPainterPath()
        sh.moveTo(q.x(), q.y() - 6.0)
        sh.lineTo(q.x() + 5.0, q.y() - 4.2)
        sh.lineTo(q.x() + 5.0, q.y() + 0.8)
        sh.quadTo(q.x() + 5.0, q.y() + 4.0, q.x(), q.y() + 6.2)
        sh.quadTo(q.x() - 5.0, q.y() + 4.0, q.x() - 5.0, q.y() + 0.8)
        sh.lineTo(q.x() - 5.0, q.y() - 4.2)
        sh.closeSubpath()
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(sh)

        q = c(3)                                                     # duplicar: hoja de atras + hoja con esquina doblada
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(q.x() - 6.0, q.y() - 6.0, 8.0, 9.5), 1.2, 1.2)
        front = QPainterPath()
        front.moveTo(q.x() - 3.5, q.y() - 3.0)
        front.lineTo(q.x() + 2.0, q.y() - 3.0)
        front.lineTo(q.x() + 6.0, q.y() + 1.0)
        front.lineTo(q.x() + 6.0, q.y() + 6.5)
        front.lineTo(q.x() - 3.5, q.y() + 6.5)
        front.closeSubpath()
        p.setBrush(FIELD)
        p.drawPath(front)
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(q.x() + 2.0, q.y() - 3.0), QPointF(q.x() + 2.0, q.y() + 1.0),
                                  QPointF(q.x() + 6.0, q.y() + 1.0)]))

        q = c(4)                                                     # carpeta (rellena, como en Blender)
        p.setPen(Qt.NoPen)
        p.setBrush(TXT)
        p.drawRoundedRect(QRectF(q.x() - 7.5, q.y() - 5.5, 6.5, 3.5), 1.0, 1.0)
        p.drawRoundedRect(QRectF(q.x() - 7.5, q.y() - 3.5, 15.0, 10.0), 1.2, 1.2)

        q = c(5)                                                     # X (quitar imagen)
        p.setPen(QPen(TXT, 1.4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(q.x() - 3.8, q.y() - 3.8), QPointF(q.x() + 3.8, q.y() + 3.8))
        p.drawLine(QPointF(q.x() - 3.8, q.y() + 3.8), QPointF(q.x() + 3.8, q.y() - 3.8))

'''

a = txt.index("    def paint_imgloaded(self, p, r):")
b = txt.index("    def paint_block(self, p, r):")
txt = txt[:a] + NEW_FN + txt[b:]

REPL = [
    # titulo y ojo de la cabecera
    ("tx = 19.0 if self.img_loaded is not None else 26.0   # con el ojo a la derecha el titulo arranca antes",
     "tx = 24.5 if self.img_loaded is not None else 26.0   # Blender: el titulo arranca a ~24.5 u", 1),
    ("p.drawText(QRectF(tx, 0, self.w - tx - 8, HEADER), AL, self.title())",
     "p.drawText(QRectF(tx, 0, self.w - tx - (26.0 if self.img_loaded is not None else 8.0), HEADER), AL, self.title())", 1),
    ("ex, ey = self.w - 14.0, HEADER / 2", "ex, ey = self.w - 16.0, HEADER / 2", 1),
    ("eye.moveTo(ex - 6.5, ey)", "eye.moveTo(ex - 7.0, ey)", 1),
    ("eye.quadTo(ex, ey - 7.5, ex + 6.5, ey)", "eye.quadTo(ex, ey - 8.0, ex + 7.0, ey)", 1),
    ("eye.quadTo(ex, ey + 7.5, ex - 6.5, ey)", "eye.quadTo(ex, ey + 8.0, ex - 7.0, ey)", 1),
    ("p.setPen(QPen(tcol, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))",
     "p.setPen(QPen(tcol, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))", 1),
    ("p.drawEllipse(QPointF(ex, ey), 2.6, 2.6)", "p.drawEllipse(QPointF(ex, ey), 3.1, 3.1)", 1),
    # menus: ancho de la etiqueta y posicion de la flechita (solo los de la imagen cargada usan lw/arrow)
    ("lw = fw * 0.36", 'lw = fw * r.get("lw", 0.36)', 1),
    ("cx, cy = rect.right() - 11, rect.center().y()", 'cx, cy = rect.right() - r.get("arrow", 11.0), rect.center().y()', 1),
    ("items=IMG_SRC_ITEMS))", "items=IMG_SRC_ITEMS, arrow=7.0))", 1),
    ("inline=True, nocolon=True))", "inline=True, nocolon=True, lw=0.344, arrow=7.0))", 2),
]
for old, new, n in REPL:
    if txt.count(old) != n:
        raise SystemExit(f"no encontre {n} vez/veces: {old[:60]}")
    txt = txt.replace(old, new)

SRC.write_text(txt, encoding="utf-8")
print("parche aplicado")
