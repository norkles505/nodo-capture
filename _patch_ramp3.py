"""Parche 3: iconos + - v del Color Ramp mas chicos/finos y linea punteada en ambos marcadores.
Backup en main.py.pre_ramp3.bak, valida sintaxis, restaura si falla. Resultado en res_ramp3.txt."""
import os, re, shutil, py_compile, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "main.py")
BAK = os.path.join(HERE, "main.py.pre_ramp3.bak")
LOG = os.path.join(HERE, "res_ramp3.txt")

PAIRS = [
    ('p.setPen(QPen(TXT, 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))',
     'p.setPen(QPen(TXT, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))'),
    ('p.drawLine(QPointF(cx - 4.5, cy), QPointF(cx + 4.5, cy))',
     'p.drawLine(QPointF(cx - 3.9, cy), QPointF(cx + 3.9, cy))'),
    ('p.drawLine(QPointF(cx, cy - 4.5), QPointF(cx, cy + 4.5))',
     'p.drawLine(QPointF(cx, cy - 3.9), QPointF(cx, cy + 3.9))'),
    ('p.drawLine(QPointF(cx - 5.0, cy), QPointF(cx + 5.0, cy))',
     'p.drawLine(QPointF(cx - 3.9, cy), QPointF(cx + 3.9, cy))'),
    ('p.drawPolyline(QPolygonF([QPointF(cx - 4.5, cy - 2.2), QPointF(cx, cy + 2.2),',
     'p.drawPolyline(QPolygonF([QPointF(cx - 3.7, cy - 2.0), QPointF(cx, cy + 2.0),'),
    ('QPointF(cx + 4.5, cy - 2.2)]))',
     'QPointF(cx + 3.7, cy - 2.0)]))'),
]

DASH_RE = re.compile(
    r'( +)if selm:[^\r\n]*(\r?\n) +p\.setPen\(QPen\(QColor\("#ffffff"\), 1\.0, Qt\.DashLine\)\)(\r?\n)'
    r' +p\.drawLine\(QPointF\(xx, gr\.top\(\)\), QPointF\(xx, tip\)\)')


def main():
    with open(MAIN, "r", encoding="utf-8", newline="") as f:
        s = f.read()
    for old, _ in PAIRS:
        if s.count(old) != 1:
            return "ABORTADO: '%s' aparece %d veces. main.py sin cambios." % (old, s.count(old))
    if len(DASH_RE.findall(s)) != 1:
        return "ABORTADO: bloque de la linea punteada no encontrado (%d). main.py sin cambios." % len(DASH_RE.findall(s))
    shutil.copyfile(MAIN, BAK)
    for old, new in PAIRS:
        s = s.replace(old, new)

    def dash(m):
        ind, nl = m.group(1), m.group(2)
        return (ind + '# linea punteada de cada marcador (blanca en el activo, gris en el otro)' + nl +
                ind + 'p.setPen(QPen(QColor("#ffffff") if selm else QColor("#9a9a9a"), 1.0, Qt.DashLine))' + nl +
                ind + 'p.drawLine(QPointF(xx, gr.top()), QPointF(xx, tip))')

    s = DASH_RE.sub(dash, s)
    with open(MAIN, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    try:
        py_compile.compile(MAIN, doraise=True)
    except Exception:
        shutil.copyfile(BAK, MAIN)
        return "SINTAXIS INVALIDA, se restauro el backup.\n" + traceback.format_exc()
    return "OK: iconos y linea punteada actualizados. Backup: main.py.pre_ramp3.bak"


if __name__ == "__main__":
    try:
        msg = main()
    except Exception:
        msg = "ERROR:\n" + traceback.format_exc()
    with open(LOG, "w", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)
