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


# constantes de layout y estado de imagenes (antes en main.py)
IMG_CS_ITEMS = [{"id": "sRGB", "name": "sRGB"}, {"id": "Non-Color", "name": "Non-Color"},
                {"id": "Linear Rec.709", "name": "Linear Rec.709"}, {"id": "Linear Rec.2020", "name": "Linear Rec.2020"},
                {"id": "ACEScg", "name": "ACEScg"}, {"id": "Filmic Log", "name": "Filmic Log"}]
IMAGES = {}             # imagenes abiertas en esta sesion: nombre -> ruta (para el selector desplegable)
IMG_LOADED_H = 181.0    # alto real del nodo Image con imagen cargada (medido en tu Blender)
IMG_SRC_ITEMS = [{"id": "FILE", "name": "Single Image"}, {"id": "SEQUENCE", "name": "Image Sequence"},
                 {"id": "MOVIE", "name": "Movie"}, {"id": "GENERATED", "name": "Generated"},
                 {"id": "VIEWER", "name": "Viewer"}, {"id": "TILED", "name": "UDIM Tiles"}]
IMG_ALPHA_ITEMS = [{"id": "STRAIGHT", "name": "Straight"}, {"id": "PREMUL", "name": "Premultiplied"},
                   {"id": "CHANNEL_PACKED", "name": "Channel Packed"}, {"id": "NONE", "name": "None"}]
ENUM_TIGHT = {"ShaderNodeTexImage": 1.5, "ShaderNodeTexEnvironment": 1.5}   # menos aire entre menus (Blender: ~25 u de paso)
TOP_SHIFT = {"ShaderNodeBsdfPrincipled": 2.6}   # sube la primera fila (la salida) de estos nodos
INPUT_PULL = {"ShaderNodeMath": 2.0, "ShaderNodeVectorMath": 5.6, "ShaderNodeTexImage": 3.5, "ShaderNodeTexEnvironment": 3.5, "ShaderNodeBsdfPrincipled": 3.6}   # acerca las entradas al ultimo menu
LROW = 21.0   # fila de socket sin widget
PANEL_GAP_HEAD = 4.5   # aire bajo la cabecera de un panel abierto (Blender lo deja mas holgado)
PANEL_GAP_END = 3.0
MENU_DOWN = {"ShaderNodeMath": 2.0, "ShaderNodeVectorMath": 2.0}   # baja el primer menu de estos nodos (Blender lo deja ~2 u mas abajo); Clamp y entradas no se mueven
BOOL_UP = 2.0   # sube la casilla (Clamp...) hacia el menu de arriba; la altura total del nodo no cambia   # margen del texto en los campos numericos (Blender los deja mas holgados que los menus)    # aire antes de la cabecera siguiente si el panel anterior esta abierto
EROW = 26.5   # fila de menu desplegable (alto + espacio)
BROW = 23.5   # fila de casilla (medida en el PDF: ~25 px entre menu y casilla)
TIGHT_PAD = 1.8   # holgura final de los nodos que solo tienen salidas (Value, Light Path...)
STACKED = {"ShaderNodeTexSky", "ShaderNodeTexBrick"}
