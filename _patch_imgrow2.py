"""Parche 2: iconos de la fila de imagen (mas grandes y finos como en Blender), ojo y flecha de la cabecera.
Copia de seguridad en main.py.pre_fila2.bak; no se puede aplicar dos veces."""
import shutil
from pathlib import Path

SRC = Path(__file__).parent / "main.py"
txt = SRC.read_text(encoding="utf-8")
if "FILA_V3" in txt:
    raise SystemExit("ya aplicado")
if "FILA_V2" not in txt:
    raise SystemExit("falta aplicar _patch_imgrow.py primero")
shutil.copy(SRC, SRC.with_name("main.py.pre_fila2.bak"))

NEW_FN = '''    def paint_imgloaded(self, p, r):
        """FILA_V3 - fila de imagen cargada (template_ID de Blender):
        selector | nombre (se estira) | usuarios | escudo | duplicar | carpeta | X."""
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

        # --- selector de imagen: marco fino con montana y sol (como el icono de Blender) + flechita
        path = self.field(p, QRectF(x, yy, sw, bh), MENU)
        p.setPen(QPen(globals().get("WCOL_OUT", {}).get("menu", FIELD_LINE), FIELD_LINE_W))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        isz = 14.5 if wide else 10.5
        ic = QRectF(x + (4.0 if wide else 3.2), yy + (bh - isz) / 2, isz, isz)
        pt = lambda fx, fy: QPointF(ic.left() + fx * ic.width(), ic.top() + fy * ic.height())
        p.setPen(QPen(TXT, 1.3, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(ic.adjusted(0.65, 0.65, -0.65, -0.65), 1.2, 1.2)
        p.setPen(Qt.NoPen)
        p.setBrush(TXT)
        p.drawPolygon(QPolygonF([pt(.14, .86), pt(.40, .45), pt(.58, .68), pt(.70, .54), pt(.86, .86)]))
        p.drawEllipse(pt(.30, .30), isz * 0.09, isz * 0.09)
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
        pen = QPen(TXT, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

        q, s = c(2), 1.2                                             # escudo (usuario falso)
        sh = QPainterPath()
        sh.moveTo(q.x(), q.y() - 6.0 * s)
        sh.lineTo(q.x() + 5.0 * s, q.y() - 4.2 * s)
        sh.lineTo(q.x() + 5.0 * s, q.y() + 0.8 * s)
        sh.quadTo(q.x() + 5.0 * s, q.y() + 4.0 * s, q.x(), q.y() + 6.2 * s)
        sh.quadTo(q.x() - 5.0 * s, q.y() + 4.0 * s, q.x() - 5.0 * s, q.y() + 0.8 * s)
        sh.lineTo(q.x() - 5.0 * s, q.y() - 4.2 * s)
        sh.closeSubpath()
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(sh)

        q, s = c(3), 1.15                                            # duplicar: hoja de atras + hoja con esquina doblada
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(q.x() - 6.0 * s, q.y() - 6.0 * s, 8.0 * s, 9.5 * s), 1.2, 1.2)
        front = QPainterPath()
        front.moveTo(q.x() - 3.5 * s, q.y() - 3.0 * s)
        front.lineTo(q.x() + 1.5 * s, q.y() - 3.0 * s)
        front.lineTo(q.x() + 6.0 * s, q.y() + 1.5 * s)
        front.lineTo(q.x() + 6.0 * s, q.y() + 6.5 * s)
        front.lineTo(q.x() - 3.5 * s, q.y() + 6.5 * s)
        front.closeSubpath()
        p.setBrush(FIELD)
        p.drawPath(front)
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(q.x() + 1.5 * s, q.y() - 3.0 * s), QPointF(q.x() + 1.5 * s, q.y() + 1.5 * s),
                                  QPointF(q.x() + 6.0 * s, q.y() + 1.5 * s)]))

        q, s = c(4), 1.1                                             # carpeta (rellena, como en Blender)
        p.setPen(Qt.NoPen)
        p.setBrush(TXT)
        p.drawRoundedRect(QRectF(q.x() - 7.5 * s, q.y() - 5.5 * s, 6.5 * s, 3.5 * s), 1.0, 1.0)
        p.drawRoundedRect(QRectF(q.x() - 7.5 * s, q.y() - 3.5 * s, 15.0 * s, 10.0 * s), 1.2, 1.2)

        q = c(5)                                                     # X (quitar imagen)
        p.setPen(QPen(TXT, 1.3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(q.x() - 3.8, q.y() - 3.8), QPointF(q.x() + 3.8, q.y() + 3.8))
        p.drawLine(QPointF(q.x() - 3.8, q.y() + 3.8), QPointF(q.x() + 3.8, q.y() - 3.8))

'''

a = txt.index("    def paint_imgloaded(self, p, r):")
b = txt.index("    def paint_block(self, p, r):")
txt = txt[:a] + NEW_FN + txt[b:]

REPL = [
    # ojo mas pequeno y fino
    ("eye.moveTo(ex - 7.0, ey)", "eye.moveTo(ex - 5.8, ey)", 1),
    ("eye.quadTo(ex, ey - 8.0, ex + 7.0, ey)", "eye.quadTo(ex, ey - 6.4, ex + 5.8, ey)", 1),
    ("eye.quadTo(ex, ey + 8.0, ex - 7.0, ey)", "eye.quadTo(ex, ey + 6.4, ex - 5.8, ey)", 1),
    ("p.setPen(QPen(tcol, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))",
     "p.setPen(QPen(tcol, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))", 1),
    ("p.drawEllipse(QPointF(ex, ey), 3.1, 3.1)", "p.drawEllipse(QPointF(ex, ey), 2.5, 2.5)", 1),
    # flecha de plegar mas a la derecha (solo nodo con imagen cargada)
    ("p.drawPolyline(QPolygonF([QPointF(8.5, 8.2), QPointF(12, 11.8), QPointF(15.5, 8.2)]))",
     "dx = 3.5 if self.img_loaded is not None else 0.0\n"
     "        p.drawPolyline(QPolygonF([QPointF(8.5 + dx, 8.2), QPointF(12 + dx, 11.8), QPointF(15.5 + dx, 8.2)]))", 1),
    # flechita de los menus un poco mas pegada al borde
    ("arrow=7.0))", "arrow=5.8))", 3),
]
for old, new, n in REPL:
    if txt.count(old) != n:
        raise SystemExit(f"no encontre {n} vez/veces: {old[:60]}")
    txt = txt.replace(old, new)

SRC.write_text(txt, encoding="utf-8")
print("parche 2 aplicado")
