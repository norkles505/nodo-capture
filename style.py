"""Colores y estilo de Nodo Capture que cambian con el tema.

themes.py reasigna estos nombres (style.BG = ..., etc.) y las clases de main.py los leen como S.BG en cada
dibujo, asi el cambio de tema llega a todo. Los datos (data/theme.json y data/widgets.json) vienen de tu Blender.
"""
import json
from pathlib import Path

from PySide6.QtGui import QColor

DATA = Path(__file__).parent / "data"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


THEME = load("theme.json")
WID = load("widgets.json")


def col(v):
    return QColor.fromRgbF(v[0], v[1], v[2], v[3] if len(v) > 3 else 1.0)


def lin2s(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def s2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


HEAD = {k: col(THEME[k]) for k in ("input_node", "output_node", "shader_node", "texture_node",
                                   "converter_node", "vector_node", "filter_node", "color_node",
                                   "matte_node", "distor_node", "group_node", "group_socket_node",
                                   "frame_node")}
BG = QColor("#1a1a1a")                      # fondo del Node Editor (tema de tu Blender)
GRID_MINOR = QColor("#212121")
GRID_MAJOR = col(THEME["grid"])
BODY = col(THEME["node_backdrop"])
OUTLINE = col(THEME["node_outline"])
SEL = col(THEME["node_selected"])           # naranja de seleccion
TXT = col(WID["wcol_regular"]["text"])
TITLE = QColor("#eeeeee")
DIM = QColor("#7d7d7d")
FIELD = col(WID["wcol_regular"]["inner"])
FIELD_LINE = col(WID["wcol_regular"]["outline"])
TEXT_FIELD = col(WID["wcol_text"]["inner"]) if "wcol_text" in WID else QColor("#1d1d1d")   # fondo oscuro de los campos de busqueda (UV Map)
MENU = col(WID["wcol_menu"]["inner"])
MENU_ITEM = col(WID["wcol_menu"]["item"])   # color de la flechita de los menus
SLIDER = col(WID["wcol_numslider"]["item"])
CHECK_ON = col(WID["wcol_option"]["inner_sel"])
WIRE = col(THEME["wire"])
WIRE_SEL = col(THEME["wire_select"])
SOCK = {"VALUE": "#a1a1a1", "INT": "#598c5c", "BOOLEAN": "#cca6d6", "VECTOR": "#6363c7",
        "RGBA": "#c7c729", "SHADER": "#63c763", "STRING": "#71b2ff", "ROTATION": "#a64dc7",
        "MATRIX": "#8c2b4f", "MENU": "#a1a1a1"}
LINK_LINE = "#000000"   # color del borde de los cables
SOCK_LINE = "#000000"   # color del borde de los sockets
RAD = 4.0               # esquinas de campos (roundness 0.4 del tema)
CURVING = 5.0           # noodle_curving del tema (0 = cable recto, 10 = muy curvo); 5 es el valor de Blender
WCOL_OUT = {}           # contorno propio por tipo de widget (lo llena themes.py)
WCOL_SKIN = {}          # relleno, texto y esquinas por tipo de widget (lo llena themes.py)
