"""Parche: redibuja el bloque 'ramp' (Color Ramp) de paint_block en main.py para igualar a Blender.
Hace backup en main.py.pre_ramp.bak, valida la sintaxis y restaura el backup si algo falla.
Resultado en res_ramp.txt."""
import os, shutil, py_compile, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "main.py")
BAK = os.path.join(HERE, "main.py.pre_ramp.bak")
LOG = os.path.join(HERE, "res_ramp.txt")

NEW = r'''        elif kind == "ramp":
            # medidas de Blender 5.2 (sacadas de capturas), relativas al inicio del bloque (y)
            by = y + 8.0                                  # fila de iconos + menu doble
            cy = by + 10.0
            p.setPen(QPen(TXT, 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            cx = x + 10.0                                 # "+"
            p.drawLine(QPointF(cx - 4.5, cy), QPointF(cx + 4.5, cy))
            p.drawLine(QPointF(cx, cy - 4.5), QPointF(cx, cy + 4.5))
            cx = x + 35.5                                 # "-"
            p.drawLine(QPointF(cx - 5.0, cy), QPointF(cx + 5.0, cy))
            cx = x + 66.5                                 # "v"
            p.drawPolyline(QPolygonF([QPointF(cx - 4.5, cy - 2.2), QPointF(cx, cy + 2.2),
                                      QPointF(cx + 4.5, cy - 2.2)]))
            gx = x + 92.8                                 # RGB | Linear: una sola caja con linea divisoria
            grp = QRectF(gx, by, x + fw - gx, 20.0)
            path = self.field(p, grp, MENU)
            self.outline(p, path)
            mid = x + 156.0
            p.setPen(QPen(FIELD_LINE, FIELD_LINE_W))
            p.drawLine(QPointF(mid, grp.top()), QPointF(mid, grp.bottom()))
            p.setPen(TXT)
            p.drawText(QRectF(x + 100.0, by, mid - x - 100.0, 20.0), AL, "RGB")
            p.drawText(QRectF(x + 163.3, by, x + fw - x - 163.3, 20.0), AL, "Linear")
            p.setPen(QPen(MENU_ITEM, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            for ax in (x + 150.4, x + 213.2):             # flechitas de cada menu
                p.drawLine(QPointF(ax - 2.6, cy - 1.2), QPointF(ax, cy + 1.4))
                p.drawLine(QPointF(ax, cy + 1.4), QPointF(ax + 2.6, cy - 1.2))
            # barra del degradado (metida 5 u por cada lado, esquinas rectas)
            gr = QRectF(x + 5.0, y + 33.5, fw - 10.0, 18.5)
            lg = QLinearGradient(gr.left(), 0, gr.right(), 0)
            lg.setColorAt(0, QColor("#000000"))
            lg.setColorAt(1, QColor("#ffffff"))
            p.fillRect(gr, QBrush(lg))
            p.setPen(QPen(FIELD_LINE, FIELD_LINE_W))
            p.setBrush(Qt.NoBrush)
            p.drawRect(gr)
            # marcadores: pentagono con la punta hacia arriba, centrado en cada extremo de la barra
            for xx, cc, selm in ((gr.left(), "#000000", True), (gr.right(), "#ffffff", False)):
                tip, bot, hw = gr.top() + 9.0, gr.top() + 22.8, 5.8
                if selm:                                   # linea punteada del marcador activo
                    p.setPen(QPen(QColor("#ffffff"), 1.0, Qt.DashLine))
                    p.drawLine(QPointF(xx, gr.top()), QPointF(xx, tip))
                p.setPen(QPen(QColor("#ffffff") if selm else QColor("#8a8a8a"), 1.2))
                p.setBrush(QColor("#f2f2f2") if selm else QColor("#c8c8c8"))
                p.drawPolygon(QPolygonF([QPointF(xx, tip), QPointF(xx + hw, tip + 5.0), QPointF(xx + hw, bot),
                                         QPointF(xx - hw, bot), QPointF(xx - hw, tip + 5.0)]))
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(cc))
                p.drawRect(QRectF(xx - 4.0, bot - 8.0, 8.0, 6.5))
            # fila "0" + Pos
            py = y + 63.2
            z = QRectF(x, py, 63.0, 20.0)
            path = self.field(p, z, FIELD)
            self.outline(p, path)
            p.setPen(TXT)
            p.drawText(z, Qt.AlignCenter, "0")
            f2 = QRectF(x + 71.7, py, fw - 71.7, 20.0)
            path = self.field(p, f2, FIELD)
            self.outline(p, path)
            p.setPen(TXT)
            p.drawText(f2.adjusted(NUM_PAD_L, 0, -NUM_PAD_R, 0), AL, "Pos")
            p.drawText(f2.adjusted(NUM_PAD_L, 0, -NUM_PAD_R, 0), AR, "0.000")
            # muestra de color (queda a 2 u del Factor, como en Blender)
            path = self.field(p, QRectF(x, y + 88.0, fw, 20.0), QColor("#000000"))
            self.outline(p, path)
'''

START = '        elif kind == "ramp":'
END = '        elif kind == "imgsel":'


def main():
    with open(MAIN, "r", encoding="utf-8", newline="") as f:
        s = f.read()
    nl = "\r\n" if "\r\n" in s else "\n"
    if s.count(START) != 1 or s.count(END) != 1:
        return "ABORTADO: marcadores no unicos (ramp=%d, imgsel=%d). main.py sin cambios." % (s.count(START), s.count(END))
    a = s.index(START)
    b = s.index(END, a)
    shutil.copyfile(MAIN, BAK)
    new = NEW.replace("\r\n", "\n").replace("\n", nl)
    out = s[:a] + new + s[b:]
    with open(MAIN, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    try:
        py_compile.compile(MAIN, doraise=True)
    except Exception:
        shutil.copyfile(BAK, MAIN)
        return "SINTAXIS INVALIDA, se restauro el backup.\n" + traceback.format_exc()
    return "OK: bloque ramp reemplazado (%d -> %d caracteres). Backup: main.py.pre_ramp.bak" % (b - a, len(new))


if __name__ == "__main__":
    try:
        msg = main()
    except Exception:
        msg = "ERROR:\n" + traceback.format_exc()
    with open(LOG, "w", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)
