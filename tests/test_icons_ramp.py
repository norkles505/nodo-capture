"""Prueba de los modulos icons.py y ramp.py (sacados de main.py). Sin ventana.

Comprueba que main sigue exponiendo los mismos objetos, que los 7 iconos pintan algo
y que un nodo Color Ramp se dibuja. Sale con codigo distinto de 0 si algo falla.
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # raiz del proyecto

from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
import icons
import main as M
import ramp

ICONOS = ("folder", "image", "object", "dropper", "uv", "scene", "layers")
fallos = []


def check(nombre, ok):
    print(("OK   " if ok else "FALLA"), nombre)
    if not ok:
        fallos.append(nombre)


# main sigue viendo exactamente los objetos de los modulos nuevos
for n in ICONOS:
    check(f"main.draw_{n}_icon es icons.draw_{n}_icon", getattr(M, f"draw_{n}_icon") is getattr(icons, f"draw_{n}_icon"))
for n in ("RAMP_CMODES", "RAMP_INTERPS", "_new_ramp", "ramp_eval", "ramp_samples"):
    check(f"main.{n} es ramp.{n}", getattr(M, n) is getattr(ramp, n))

# cada icono pinta algo dentro de su hueco
img = QImage(200, 32, QImage.Format_ARGB32)
img.fill(0)
p = QPainter(img)
for i, n in enumerate(ICONOS):
    getattr(icons, f"draw_{n}_icon")(p, QRectF(4 + i * 26, 4, 20, 20), "#ffffff")
p.end()
for i, n in enumerate(ICONOS):
    pinta = any(img.pixelColor(4 + i * 26 + x, 4 + y).alpha() > 0 for x in range(20) for y in range(20))
    check(f"icono {n} pinta", pinta)

# el color ramp evalua y un nodo ShaderNodeValToRGB se crea y se dibuja
rp = ramp._new_ramp()
check("ramp_eval 0.5 entre negro y blanco", all(abs(c - e) < 1e-9 for c, e in zip(ramp.ramp_eval(rp, 0.5), [0.5, 0.5, 0.5, 1.0])))
sc = M.NodeScene("shader")
spec = next(s for s in M.CATALOG["shader"] if s["idname"] == "ShaderNodeValToRGB")
nodo = M.NodeItem(spec, M.category(spec["idname"], "shader"))
sc.addItem(nodo)
check("el nodo Color Ramp tiene su ramp", nodo.ramp is not None)
img2 = QImage(500, 500, QImage.Format_ARGB32)
img2.fill(0)
p = QPainter(img2)
sc.render(p, QRectF(img2.rect()), sc.itemsBoundingRect().adjusted(-20, -20, 20, 20))
p.end()
check("el nodo Color Ramp se dibuja", any(img2.pixelColor(x, y).alpha() > 0 for x in range(0, 500, 5) for y in range(0, 500, 5)))

print("\nRESULTADO:", "TODO OK" if not fallos else f"{len(fallos)} FALLOS")
sys.exit(1 if fallos else 0)
