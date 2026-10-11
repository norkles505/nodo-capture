"""Parche 2: marcadores del Color Ramp con contorno oscuro (se perdian blanco sobre blanco).
Backup en main.py.pre_ramp2.bak, valida sintaxis, restaura si falla. Resultado en res_ramp2.txt."""
import os, shutil, py_compile, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "main.py")
BAK = os.path.join(HERE, "main.py.pre_ramp2.bak")
LOG = os.path.join(HERE, "res_ramp2.txt")

OLD = r'''                p.setPen(QPen(QColor("#ffffff") if selm else QColor("#8a8a8a"), 1.2))
                p.setBrush(QColor("#f2f2f2") if selm else QColor("#c8c8c8"))
                p.drawPolygon(QPolygonF([QPointF(xx, tip), QPointF(xx + hw, tip + 5.0), QPointF(xx + hw, bot),
                                         QPointF(xx - hw, bot), QPointF(xx - hw, tip + 5.0)]))
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(cc))
                p.drawRect(QRectF(xx - 4.0, bot - 8.0, 8.0, 6.5))
'''

NEW = r'''                oc = QColor("#1a1a1a") if selm else QColor("#707070")   # contorno oscuro (el activo mas negro)
                p.setPen(QPen(oc, 1.2))
                p.setBrush(QColor("#ffffff"))
                p.drawPolygon(QPolygonF([QPointF(xx, tip), QPointF(xx + hw, tip + 5.0), QPointF(xx + hw, bot),
                                         QPointF(xx - hw, bot), QPointF(xx - hw, tip + 5.0)]))
                if not selm:                               # techo del marcador inactivo en gris oscuro
                    p.setBrush(oc)
                    p.drawPolygon(QPolygonF([QPointF(xx, tip), QPointF(xx + hw, tip + 5.0),
                                             QPointF(xx - hw, tip + 5.0)]))
                p.setPen(QPen(oc, 1.0))
                p.setBrush(QColor(cc))
                p.drawRect(QRectF(xx - 4.0, bot - 8.0, 8.0, 6.5))
'''


def main():
    with open(MAIN, "r", encoding="utf-8", newline="") as f:
        s = f.read()
    nl = "\r\n" if "\r\n" in s else "\n"
    old = OLD.replace("\n", nl)
    new = NEW.replace("\n", nl)
    if s.count(old) != 1:
        return "ABORTADO: el bloque a reemplazar aparece %d veces. main.py sin cambios." % s.count(old)
    shutil.copyfile(MAIN, BAK)
    with open(MAIN, "w", encoding="utf-8", newline="") as f:
        f.write(s.replace(old, new))
    try:
        py_compile.compile(MAIN, doraise=True)
    except Exception:
        shutil.copyfile(BAK, MAIN)
        return "SINTAXIS INVALIDA, se restauro el backup.\n" + traceback.format_exc()
    return "OK: marcadores del ramp actualizados. Backup: main.py.pre_ramp2.bak"


if __name__ == "__main__":
    try:
        msg = main()
    except Exception:
        msg = "ERROR:\n" + traceback.format_exc()
    with open(LOG, "w", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)
