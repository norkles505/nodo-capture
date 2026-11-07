"""Medidas fijas (px a escala 1; unidad de widget de Blender = 20 px) y formato de valores.
No cambian con el tema, asi que se importan tal cual. Los colores estan en style.py."""
import math

from PySide6.QtCore import Qt

# medidas en px a escala 1 (unidad de widget de Blender = 20 px)
HEADER, ROW, FH, GAP, PAD, R = 20.0, 20.0, 20.0, 2.0, 10.0, 6.0
FIELD_LINE_W = 0.8   # grosor del borde de los campos (menus, numeros, casillas)
NODE_LINE_W = 0.85   # grosor del borde del nodo (seleccionado: 2.0)
IMG_TOP = 3.0        # aire sobre la fila selector/New/Open de los nodos de imagen
NUM_PAD_L, NUM_PAD_R = 15.0, 13.5
AL = Qt.AlignLeft | Qt.AlignVCenter
AR = Qt.AlignRight | Qt.AlignVCenter


def fmt(v, st):
    if isinstance(v, bool):
        return str(v)
    if st == "INT":
        return str(int(v))
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def fmt_unit(v, r):
    u = r.get("unit")
    if u in ("deg", "m", "nm", "px"):
        x = math.degrees(float(v)) if u == "deg" else float(v)
        t = f"{x:.3f}" if u == "px" else f"{x:.3f}".rstrip("0").rstrip(".")   # px conserva los 3 decimales (6.000 px)
        return t + ("\u00b0" if u == "deg" else " " + u)
    return fmt(v, r["st"])
