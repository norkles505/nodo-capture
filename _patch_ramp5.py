"""Parche 5: contorno de los marcadores del Color Ramp a 0.5 y cuadrado de color pegado al contorno (sin franja blanca).
Backup en main.py.pre_ramp5.bak, valida sintaxis, restaura si falla. Resultado en res_ramp5.txt."""
import os, shutil, py_compile, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "main.py")
BAK = os.path.join(HERE, "main.py.pre_ramp5.bak")
LOG = os.path.join(HERE, "res_ramp5.txt")

SQ_OLD = 'p.drawRect(QRectF(xx - hw + 0.9, tip + 5.0, 2 * hw - 1.8, bot - tip - 5.9))'
SQ_NEW = 'p.drawRect(QRectF(xx - hw + 0.25, tip + 5.0, 2 * hw - 0.5, bot - tip - 5.25))'
PEN_OLD = 'p.setPen(QPen(oc, 0.9))'
PEN_NEW = 'p.setPen(QPen(oc, 0.5))'


def main():
    with open(MAIN, "r", encoding="utf-8", newline="") as f:
        s = f.read()
    if s.count(SQ_OLD) != 1:
        return "ABORTADO: la linea del cuadrado aparece %d veces. main.py sin cambios." % s.count(SQ_OLD)
    shutil.copyfile(MAIN, BAK)
    s = s.replace(SQ_OLD, SQ_NEW)
    note = ""
    if s.count(PEN_OLD) == 1:
        s = s.replace(PEN_OLD, PEN_NEW)
    else:
        note = " (el grosor del contorno ya no estaba en 0.9, no se toco)"
    with open(MAIN, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    try:
        py_compile.compile(MAIN, doraise=True)
    except Exception:
        shutil.copyfile(BAK, MAIN)
        return "SINTAXIS INVALIDA, se restauro el backup.\n" + traceback.format_exc()
    return "OK: marcadores actualizados" + note + ". Backup: main.py.pre_ramp5.bak"


if __name__ == "__main__":
    try:
        msg = main()
    except Exception:
        msg = "ERROR:\n" + traceback.format_exc()
    with open(LOG, "w", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)
