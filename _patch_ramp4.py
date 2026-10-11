"""Parche 4: marcadores del Color Ramp mas finos, cuadrado de color a ras del cuerpo y borde visible en la barra.
Backup en main.py.pre_ramp4.bak, valida sintaxis, restaura si falla. Resultado en res_ramp4.txt."""
import os, re, shutil, py_compile, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "main.py")
BAK = os.path.join(HERE, "main.py.pre_ramp4.bak")
LOG = os.path.join(HERE, "res_ramp4.txt")

PAIRS = [
    ('p.setPen(QPen(oc, 1.2))',
     'p.setPen(QPen(oc, 0.9))'),
    ('p.setPen(QPen(oc, 1.0))',
     'p.setPen(Qt.NoPen)'),
    ('p.drawRect(QRectF(xx - 4.0, bot - 8.0, 8.0, 6.5))',
     'p.drawRect(QRectF(xx - hw + 0.9, tip + 5.0, 2 * hw - 1.8, bot - tip - 5.9))'),
]

BAR_RE = re.compile(
    r'p\.setPen\(QPen\(FIELD_LINE, FIELD_LINE_W\)\)(\r?\n) +p\.setBrush\(Qt\.NoBrush\)(\r?\n) +p\.drawRect\(gr\)')


def main():
    with open(MAIN, "r", encoding="utf-8", newline="") as f:
        s = f.read()
    for old, _ in PAIRS:
        if s.count(old) != 1:
            return "ABORTADO: '%s' aparece %d veces. main.py sin cambios." % (old, s.count(old))
    if len(BAR_RE.findall(s)) != 1:
        return "ABORTADO: bloque del borde de la barra no encontrado (%d). main.py sin cambios." % len(BAR_RE.findall(s))
    shutil.copyfile(MAIN, BAK)
    for old, new in PAIRS:
        s = s.replace(old, new)

    def bar(m):
        # mismo sangrado que la linea original: se toma de la linea de setBrush/drawRect
        start = m.start()
        line_start = s.rfind("\n", 0, start) + 1
        ind = s[line_start:start]
        nl1, nl2 = m.group(1), m.group(2)
        return ('p.setPen(QPen(QColor(TXT.red(), TXT.green(), TXT.blue(), 70), 0.8))   # borde fino de la barra' + nl1 +
                ind + 'p.setBrush(Qt.NoBrush)' + nl2 +
                ind + 'p.drawRect(gr)')

    s = BAR_RE.sub(bar, s)
    with open(MAIN, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    try:
        py_compile.compile(MAIN, doraise=True)
    except Exception:
        shutil.copyfile(BAK, MAIN)
        return "SINTAXIS INVALIDA, se restauro el backup.\n" + traceback.format_exc()
    return "OK: marcadores y borde de la barra actualizados. Backup: main.py.pre_ramp4.bak"


if __name__ == "__main__":
    try:
        msg = main()
    except Exception:
        msg = "ERROR:\n" + traceback.format_exc()
    with open(LOG, "w", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)
