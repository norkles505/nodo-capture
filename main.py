"""Nodo Capture - replica visual (no funcional) de los nodos de Blender
para sacar capturas en alta definicion (PNG a cualquier escala o SVG).
Los datos (nodos, colores del tema, widgets, fuente Inter) vienen de data/,
extraidos de tu propio Blender."""
import sys
import json
import copy
import math
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF, QSize
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush, QFont, QPainterPath,
                           QPainterPathStroker, QImage, QPolygonF, QCursor,
                           QAction, QPalette, QFontDatabase, QConicalGradient,
                           QRadialGradient, QLinearGradient)
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
                               QGraphicsItem, QGraphicsPathItem, QGraphicsEllipseItem,
                               QComboBox, QSpinBox, QFileDialog, QDialog, QVBoxLayout,
                               QLineEdit, QListWidget, QListWidgetItem, QInputDialog,
                               QColorDialog, QMenu)

from icons import (draw_folder_icon, draw_image_icon, draw_object_icon, draw_dropper_icon,
                   draw_uv_icon, draw_scene_icon, draw_layers_icon)
from ramp import RAMP_CMODES, RAMP_INTERPS, _new_ramp, ramp_eval, ramp_samples
import style as S
from style import DATA, load, THEME, WID, col, lin2s, s2lin
from metrics import (HEADER, ROW, FH, GAP, PAD, R, NODE_LINE_W, FIELD_LINE_W, IMG_TOP, NUM_PAD_L, NUM_PAD_R,
                     AL, AR, fmt, fmt_unit)
from node_paint import NodePaintMixin
from node_ramp import RampMixin
from graph_items import (SocketItem, LinkItem, RerouteSocket, RerouteItem, SR, LINK_W, LINK_LINE_W,
                         BAR_W, BAR_H, BAR_SHAPES, BAR_FALLBACK, SOCK_LINE_W)
from node_tables import (_GLARE_COMMON, BLOCKS, category, CO_COLOR, CO_DIST, CO_FILTER, CO_IN,
                          CO_MATTE, CO_OUT, CO_SHARED_IN, CO_VEC, CPANEL_BOX, EXTRA_H, GLARE_SOCKS,
                          IMGSEL_H, IO_MERGE, MATH_1, MATH_3, MATH_LABELS, MENU_ITEMS, MIX_ORDER,
                          MIX_SFX, OPEN_DEFAULT, PANELS, PREVIEW_ICON, PROP_DEFAULTS, PROP_EXTRA,
                          PROP_ORDER, PROP_PANEL, PROPS_FIRST, PROPS_TOP, RL_PITCH, SH_COLOR,
                          SH_CONV, SH_IN, SH_VEC, SKIP_PROPS, TRAILING_PANELS, VM_1, VM_3,
                          VM_LABELS, VM_VAL)

# Los colores y el estilo que cambia el tema viven en style.py (themes.py los reasigna alli y las clases los
# leen como S.BG, S.TXT...). main.BG, main.TXT... siguen respondiendo con el valor vigente: main_func.py,
# las pruebas y las herramientas los leen asi.
_STYLE_NAMES = frozenset(['BG', 'BODY', 'CHECK_ON', 'CURVING', 'DIM', 'FIELD', 'FIELD_LINE', 'GRID_MAJOR', 'GRID_MINOR', 'HEAD', 'LINK_LINE', 'MENU', 'MENU_ITEM', 'OUTLINE', 'RAD', 'SEL', 'SLIDER', 'SOCK', 'SOCK_LINE', 'TEXT_FIELD', 'TITLE', 'TXT', 'WCOL_OUT', 'WCOL_SKIN', 'WIRE', 'WIRE_SEL'])


def __getattr__(name):
    if name in _STYLE_NAMES:
        return getattr(S, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


CATALOG = {"shader": load("shader_nodes.json"), "compositor": load("compositor_nodes.json")}


def _co_group_image():
    """Blender crea los grupos del compositor con un item Image: Group Output lo muestra como entrada y
    Group Input como salida (el JSON se exporto de un grupo sin items y solo trae el socket virtual)."""
    nodes = CATALOG["compositor"]
    nodes = list(nodes.values()) if isinstance(nodes, dict) else nodes
    for n in nodes:
        if not isinstance(n, dict):
            continue
        sock = {"name": "Image", "identifier": "Image", "type": "NodeSocketColor", "stype": "RGBA",
                "hide_value": False, "enabled": True, "default": [0.0, 0.0, 0.0, 1.0]}
        if n.get("idname") == "NodeGroupOutput" and not any(s["name"] == "Image" for s in n["inputs"]):
            n["inputs"].insert(0, dict(sock))
        elif n.get("idname") == "NodeGroupInput" and not any(s["name"] == "Image" for s in n["outputs"]):
            n["outputs"].insert(0, dict(sock, hide_value=True))


_co_group_image()
WIDTH_LIMITS = load("width_limits.json") if (DATA / "width_limits.json").exists() else {}   # idname -> [ancho min, max] de Blender
# Frame y Reroute son nodos de "layout": no vienen del exportador, se dibujan con clases propias
LAYOUT_SPECS = [
    {"idname": "NodeFrame", "label": "Frame", "width": 300.0, "inputs": [], "outputs": [], "props": []},
    {"idname": "NodeReroute", "label": "Reroute", "width": 11.0,
     "inputs": [{"name": "Input", "identifier": "Input", "type": "NodeSocketColor", "stype": "VALUE",
                 "hide_value": True, "enabled": True, "default": None}],
     "outputs": [{"name": "Output", "identifier": "Output", "type": "NodeSocketColor", "stype": "VALUE",
                  "hide_value": False, "enabled": True, "default": None}],
     "props": []},
]
for _m in CATALOG:
    CATALOG[_m] = CATALOG[_m] + copy.deepcopy(LAYOUT_SPECS)


# ------------------------------------------------------------------ estilo
# (colores y estilo del tema: style.py)

IMG_CS_ITEMS = [{"id": "sRGB", "name": "sRGB"}, {"id": "Non-Color", "name": "Non-Color"},
                {"id": "Linear Rec.709", "name": "Linear Rec.709"}, {"id": "Linear Rec.2020", "name": "Linear Rec.2020"},
                {"id": "ACEScg", "name": "ACEScg"}, {"id": "Filmic Log", "name": "Filmic Log"}]
IMAGES = {}             # imagenes abiertas en esta sesion: nombre -> ruta (para el selector desplegable)
MULTI_IMG_USERS = 3     # usuarios que Blender muestra en "Multiple Images.png" (el 3 junto al nombre)
IMG_LOADED_W = 257.0    # ancho por defecto de Multiple Images (el de tu captura)
IMG_LOADED_H = 181.0    # alto real del nodo Image con imagen cargada (medido en tu Blender)
IMG_SRC_ITEMS = [{"id": "FILE", "name": "Single Image"}, {"id": "SEQUENCE", "name": "Image Sequence"},
                 {"id": "MOVIE", "name": "Movie"}, {"id": "GENERATED", "name": "Generated"},
                 {"id": "VIEWER", "name": "Viewer"}, {"id": "TILED", "name": "UDIM Tiles"}]
IMG_ALPHA_ITEMS = [{"id": "STRAIGHT", "name": "Straight"}, {"id": "PREMUL", "name": "Premultiplied"},
                   {"id": "CHANNEL_PACKED", "name": "Channel Packed"}, {"id": "NONE", "name": "None"}]
ENUM_TIGHT = {"ShaderNodeTexImage": 1.5, "ShaderNodeTexEnvironment": 1.5}   # menos aire entre menus (Blender: ~25 u de paso)
TOP_SHIFT = {"ShaderNodeBsdfPrincipled": 2.6}   # sube la primera fila (la salida) de estos nodos
INPUT_PULL = {"ShaderNodeMath": 2.0, "ShaderNodeVectorMath": 5.6, "ShaderNodeTexImage": 3.5, "ShaderNodeTexEnvironment": 3.5, "ShaderNodeBsdfPrincipled": 3.6}   # acerca las entradas al ultimo menu
# CURVING (style.py) = noodle_curving del tema (0 = cable recto, 10 = muy curvo); 5 es el valor de Blender
LROW = 21.0   # fila de socket sin widget
PANEL_GAP_HEAD = 4.5   # aire bajo la cabecera de un panel abierto (Blender lo deja mas holgado)
PANEL_GAP_END = 3.0
MENU_DOWN = {"ShaderNodeMath": 2.0, "ShaderNodeVectorMath": 2.0}   # baja el primer menu de estos nodos (Blender lo deja ~2 u mas abajo); Clamp y entradas no se mueven
BOOL_UP = 2.0   # sube la casilla (Clamp...) hacia el menu de arriba; la altura total del nodo no cambia   # margen del texto en los campos numericos (Blender los deja mas holgados que los menus)    # aire antes de la cabecera siguiente si el panel anterior esta abierto
EROW = 26.5   # fila de menu desplegable (alto + espacio)
BROW = 23.5   # fila de casilla (medida en el PDF: ~25 px entre menu y casilla)
TIGHT_PAD = 1.8   # holgura final de los nodos que solo tienen salidas (Value, Light Path...)
# nodos cuyos deslizadores van apilados sin hueco, con esquinas unidas (como en el PDF)
STACKED = {"ShaderNodeTexSky", "ShaderNodeTexBrick"}

_FAMILY = None


def font_family():
    global _FAMILY
    if _FAMILY is None:
        _FAMILY = "Inter"
        fid = QFontDatabase.addApplicationFont(str(DATA / "Inter.ttf"))
        fams = QFontDatabase.applicationFontFamilies(fid) if fid != -1 else []
        if fams:
            _FAMILY = fams[0]
        print("Fuente:", _FAMILY, "(Inter.woff2 cargada)" if fams else "(no se pudo cargar Inter.woff2)")
    return _FAMILY


def make_font():
    f = QFont(font_family())
    f.setFamilies([font_family(), "Inter", "Segoe UI", "Arial"])
    f.setPixelSize(11)
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


# ------------------------------------------------------------ categorias
# ------------------------------------------------------------------ items
class NodeItem(NodePaintMixin, RampMixin, QGraphicsItem):
    F = None

    def __init__(self, spec, cat):
        super().__init__()
        if NodeItem.F is None:
            NodeItem.F = make_font()
        self.spec, self.cat = copy.deepcopy(spec), cat
        self._ed = None
        spec = self.spec
        self.w = max(100.0, float(spec.get("width", 140)))
        self.h = 60.0
        self.vals = {s["identifier"]: (list(s["default"]) if isinstance(s.get("default"), list)
                                       else s.get("default")) for s in spec["inputs"]}
        self.pvals = {p["id"]: p.get("value") for p in spec["props"]}
        for (_n, _pid), _dv in PROP_DEFAULTS.items():
            if _n == spec["idname"] and not self.pvals.get(_pid):
                self.pvals[_pid] = _dv
        self.panels = PANELS.get(spec["idname"], [])
        self.panel_open = {name: (spec["idname"] in OPEN_DEFAULT) for name, _ in self.panels}
        if spec["idname"] in TRAILING_PANELS:
            self.panel_open.setdefault(TRAILING_PANELS[spec["idname"]], False)
        if spec["idname"] == "CompositorNodeGlare":
            self.panel_open["Clamp"] = False   # subpanel Clamp (con casilla) dentro de Highlights; cerrado por defecto
        self.pmap = {sock: name for name, socks in self.panels for sock in socks}
        self.panel_props = PROP_PANEL.get(spec["idname"], {})
        self.lin_in, self.lin_out = set(), set()
        self.hide_unused = False
        self._rm = None   # accion en curso sobre el Color Ramp (arrastrar marcador, menus...)
        self.ramp = _new_ramp() if spec["idname"] == "ShaderNodeValToRGB" else None
        self.img_loaded = None   # nodo Image con imagen cargada (Multiple Images): dict con nombre y usuarios
        self.rows = []
        self.socks = {}
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(1)
        self._rs = None                     # redimensionado del ancho en curso
        self.setAcceptHoverEvents(True)
        for s in spec["inputs"]:
            self.socks[("in", s["identifier"])] = SocketItem(self, s, False)
        for s in spec["outputs"]:
            self.socks[("out", s["identifier"])] = SocketItem(self, s, True)
        self.relayout()

    # ---- layout
    def shown_props(self):
        order = PROP_ORDER.get(self.spec["idname"])
        if self.spec["idname"] == "ShaderNodeMix":
            order = MIX_ORDER.get(self.pvals.get("data_type"), ["data_type"])
        if order is None:
            return self._auto_props()
        extra = PROP_EXTRA.get(self.spec["idname"], {})
        by_id = {p["id"]: p for p in self.spec["props"]}
        out = []
        for pid in order:
            if pid.startswith("_"):
                q = {"id": pid, "type": "WARN", "name": ""}
            elif pid in by_id:
                q = dict(by_id[pid])
            else:
                continue
            q.update(extra.get(pid, {}))
            out.append(q)
        out = self._cond_props(out)
        return out if any(not q["id"].startswith("_") for q in out) else self._auto_props()

    def _cond_props(self, out):
        """Menus/casillas que Blender oculta segun otras propiedades."""
        idn, pv = self.spec["idname"], self.pvals
        if idn == "ShaderNodeNormalMap" and pv.get("space", "TANGENT") != "TANGENT":
            out = [q for q in out if q["id"] not in ("base", "uv_map")]   # Base y UV Map solo existen en Tangent Space
        elif idn == "ShaderNodeTexImage" and pv.get("projection") != "BOX":
            out = [q for q in out if q["id"] != "projection_blend"]
        elif idn == "ShaderNodeTexVoronoi":
            edge = pv.get("feature") in ("DISTANCE_TO_EDGE", "N_SPHERE_RADIUS")
            one_d = pv.get("voronoi_dimensions") == "1D"
            out = [q for q in out if not (q["id"] == "normalize" and edge)
                   and not (q["id"] == "distance" and (edge or one_d))]
        return out

    def _auto_props(self):
        out = []
        for p in self.spec["props"]:
            if self.spec["idname"] == "ShaderNodeTexWave" and p["id"] == (
                    "bands_direction" if self.pvals.get("wave_type") == "RINGS" else "rings_direction"):
                continue
            v = p.get("value")
            if p["id"] in SKIP_PROPS or (p["id"] == "ycc_mode" and self.pvals.get("mode") != "YCC"):
                continue
            if p["type"] == "ENUM" and isinstance(v, str) and p.get("items"):
                out.append(p)
            elif p["type"] == "BOOLEAN" and isinstance(v, bool):
                out.append(p)
        return out

    def _apply_dyn(self):
        """Sockets/etiquetas que cambian segun los menus (Math, Vector Math, Map Range, Combine/Separate Color)."""
        idn, pv = self.spec["idname"], self.pvals
        ins, outs = self.spec["inputs"], self.spec["outputs"]
        if idn == "ShaderNodeMath" and len(ins) >= 3:
            op = pv.get("operation") or "ADD"
            n = 1 if op in MATH_1 else 3 if op in MATH_3 else 2
            lab = MATH_LABELS.get(op, ["Value", "Value", "Value"])
            for i, s in enumerate(ins[:3]):
                s["enabled"], s["name"] = i < n, lab[i]
        elif idn == "ShaderNodeVectorMath" and len(ins) >= 4 and len(outs) >= 2:
            op = pv.get("operation") or "ADD"
            n = 1 if (op in VM_1 or op == "SCALE") else 3 if op in VM_3 else 2
            lab = VM_LABELS.get(op, ["Vector", "Vector", "Vector"])
            for i, s in enumerate(ins[:3]):
                s["enabled"], s["name"] = i < n, lab[i]
            ins[3]["enabled"] = op in ("SCALE", "REFRACT")
            ins[3]["name"] = "IOR" if op == "REFRACT" else "Scale"
            outs[0]["enabled"] = op not in VM_VAL
            outs[1]["enabled"] = op in VM_VAL
        elif idn == "ShaderNodeMapRange":
            vec = pv.get("data_type") == "FLOAT_VECTOR"
            stepped = pv.get("interpolation_type") == "STEPPED"
            for s in ins:
                ident = s["identifier"]
                isv = ident == "Vector" or ident.endswith("_FLOAT3")
                st = ident in ("Steps", "Steps_FLOAT3")
                s["enabled"] = (isv == vec) and (stepped or not st)
            if len(outs) >= 2:
                outs[0]["enabled"], outs[1]["enabled"] = not vec, vec
        elif idn == "ShaderNodeTexNoise":
            dim, typ = pv.get("noise_dimensions"), pv.get("noise_type")
            on = {"Vector": dim != "1D", "W": dim in ("1D", "4D"), "Offset": typ != "FBM",
                  "Gain": typ in ("RIDGED_MULTIFRACTAL", "HYBRID_MULTIFRACTAL")}
            for s in ins:
                if s["name"] in on:
                    s["enabled"] = on[s["name"]]
        elif idn == "ShaderNodeTexWhiteNoise":
            dim = pv.get("noise_dimensions")
            for s in ins:
                if s["name"] == "Vector":
                    s["enabled"] = dim != "1D"
                elif s["name"] == "W":
                    s["enabled"] = dim in ("1D", "4D")
        elif idn == "ShaderNodeTexVoronoi":
            dim, feat, dist = pv.get("voronoi_dimensions"), pv.get("feature"), pv.get("distance")
            fract = feat not in ("DISTANCE_TO_EDGE", "N_SPHERE_RADIUS")
            on = {"Vector": dim != "1D", "W": dim in ("1D", "4D"), "Detail": fract,
                  "Roughness": fract, "Lacunarity": fract, "Smoothness": feat == "SMOOTH_F1",
                  "Exponent": dist == "MINKOWSKI" and dim != "1D" and fract}
            for s in ins:
                if s["name"] in on:
                    s["enabled"] = on[s["name"]]
            on_o = {"Distance": feat != "N_SPHERE_RADIUS", "Color": fract,
                    "Position": fract and dim != "1D", "W": fract and dim in ("1D", "4D"),
                    "Radius": feat == "N_SPHERE_RADIUS"}
            for s in outs:
                if s["name"] in on_o:
                    s["enabled"] = on_o[s["name"]]
        elif idn == "CompositorNodeKuwahara":
            aniso = str(self.vals.get("Type") or "Anisotropic") == "Anisotropic"
            for s in ins:
                if s["name"] in ("Uniformity", "Sharpness", "Eccentricity"):
                    s["enabled"] = aniso          # solo en Anisotropic
                elif s["name"] == "High Precision":
                    s["enabled"] = not aniso      # solo en Classic
        elif idn == "ShaderNodeTexGabor":
            is3 = pv.get("gabor_type") == "3D"
            for s in ins:
                if s["name"] == "Orientation":
                    s["enabled"] = (s.get("stype") == "VECTOR") == is3
        elif idn == "CompositorNodeColorBalance":
            t = str(self.vals.get("Type") or "")
            mode = "wp" if t.startswith("White") else ("cdl" if ("Offset" in t or "ASC" in t) else "lgg")
            grp = {"lgg": ("Lift", "Gamma", "Gain"), "cdl": ("Offset", "Power", "Slope")}.get(mode, ())
            for s in ins:
                ident = s["identifier"]
                if ident.startswith(("Base ", "Color ")):
                    s["enabled"] = ident.split(" ", 1)[1] in grp
                elif ident.startswith(("Input ", "Output ")):
                    s["enabled"] = mode == "wp"
        elif idn in ("CompositorNodeConvolve", "CompositorNodeGlare"):
            is_col = "color" in str(self.vals.get("Kernel Data Type") or "").lower()
            for s in ins:
                if s["identifier"] == "Float Kernel":
                    s["enabled"] = not is_col
                elif s["identifier"] == "Color Kernel":
                    s["enabled"] = is_col
            if idn == "CompositorNodeGlare":
                self._glare_dyn(ins)
        elif idn == "CompositorNodeLensdist":
            # Horizontal solo tiene Dispersion; Radial muestra tambien Distortion, Jitter y Fit (capturas de Blender)
            horiz = "horizontal" in str(self.vals.get("Type") or "").lower()
            for s in ins:
                if s["name"] in ("Distortion", "Jitter", "Fit"):
                    s["enabled"] = not horiz
        elif idn in ("ShaderNodeCombineColor", "ShaderNodeSeparateColor",
                     "CompositorNodeCombineColor", "CompositorNodeSeparateColor"):
            names = {"HSV": ["Hue", "Saturation", "Value"],
                     "HSL": ["Hue", "Saturation", "Lightness"],
                     "YUV": ["Y", "U", "V"],
                     "YCC": ["Y", "Cb", "Cr"]}.get(pv.get("mode"),
                                                                    ["Red", "Green", "Blue"])
            for s, nm in zip(ins if idn.endswith("CombineColor") else outs, names):
                s["name"] = nm

    def _glare_dyn(self, ins):
        """Glare: oculta los sockets que no aplican al Type elegido (si el Type no se reconoce, no toca nada)."""
        t = str(self.vals.get("Type") or "").lower().replace("_", " ")
        key = next((k for k in GLARE_SOCKS if k in t), None)
        if key is None:
            return
        on = GLARE_SOCKS[key]
        is_col = "color" in str(self.vals.get("Kernel Data Type") or "").lower()
        for s in ins:
            nm = s["name"]
            if nm in ("Image", "Type"):
                continue
            if nm == "Kernel":
                s["enabled"] = "Kernel" in on and (s["identifier"] == "Color Kernel") == is_col
            else:
                s["enabled"] = nm in on

    def _cat(self):
        """Categoria (color de cabecera). El Mix de Shader cambia con el tipo de dato, como en Blender 5.2:
        Float = Converter (azul claro), Vector = Vector (indigo), Color = Color."""
        if self.spec["idname"] == "ShaderNodeMix":
            return {"VECTOR": "vector_node", "RGBA": "color_node"}.get(self.pvals.get("data_type"),
                                                                       "converter_node")
        return self.cat

    def _inactive(self, s):
        """Entradas que no influyen en el resultado (Blender las atenua). Mix: con Factor = 1 no cuenta A
        y con Factor = 0 no cuenta B (solo si el Factor no esta conectado)."""
        if self.spec["idname"] != "ShaderNodeMix":
            return False
        ident = s["identifier"]
        if ident[:2] == "A_":
            which = "A"
        elif ident[:2] == "B_":
            which = "B"
        else:
            return False
        dt = self.pvals.get("data_type") or "FLOAT"
        if dt == "ROTATION" or (dt == "RGBA" and (self.pvals.get("blend_type") or "MIX") != "MIX"):
            return False
        fid = next((q["identifier"] for q in self.spec["inputs"]
                    if q["identifier"].startswith("Factor") and self._mix_enabled(q)), None)
        if fid is None or fid in self.lin_in:
            return False
        f = self.vals.get(fid)
        try:
            fs = [float(x) for x in (f if isinstance(f, list) else [f])]
        except (TypeError, ValueError):
            return False
        if self.pvals.get("clamp_factor", True):
            fs = [min(1.0, max(0.0, x)) for x in fs]
        return all(x == 1.0 for x in fs) if which == "A" else all(x == 0.0 for x in fs)

    def title(self):
        idn = self.spec["idname"]
        if self.img_loaded is not None:
            return self.img_loaded["name"]   # Blender titula el nodo con el nombre de la imagen
        if idn == "CompositorNodeGlare" and self.vals.get("Type"):
            return str(self.vals.get("Type"))   # Blender titula el nodo con el tipo elegido
        if idn == "ShaderNodeMix" and self.pvals.get("data_type") == "RGBA":
            bt = self.pvals.get("blend_type")
            for p in self.spec["props"]:
                if p["id"] == "blend_type":
                    for it in p.get("items", []):
                        if it["id"] == bt:
                            return it["name"]   # Blender titula el Mix de color con el modo de mezcla
        if idn in ("ShaderNodeMath", "ShaderNodeVectorMath"):
            op = self.pvals.get("operation")
            for p in self.spec["props"]:
                if p["id"] == "operation":
                    for it in p.get("items", []):
                        if it["id"] == op:
                            return it["name"]
        return self.spec["label"]

    def _mix_enabled(self, s):
        ident = s["identifier"]
        sfx = ident.rsplit("_", 1)[-1]
        dt = self.pvals.get("data_type") or "FLOAT"
        if ident.startswith("Factor"):
            nonuni = dt == "VECTOR" and self.pvals.get("factor_mode") == "NON_UNIFORM"
            return sfx == ("Vector" if nonuni else "Float")
        return sfx == MIX_SFX.get(dt, "Float")

    def _visible(self, s, linked):
        en = self._mix_enabled(s) if self.spec["idname"] == "ShaderNodeMix" else s["enabled"]
        return (en and (s["type"] != "NodeSocketVirtual" or self.spec["idname"] in ("NodeGroupInput", "NodeGroupOutput")) and
                not (self.hide_unused and s["identifier"] not in linked))

    def prop_row(self, p, y):
        t, ref = p["type"], ("p", p["id"])
        if t == "ENUM":
            if p.get("rl"):
                return dict(k="enum", y=y, h=FH, name=p["name"], ref=ref, items=p["items"], rl=p["rl"]), RL_PITCH[p["rl"]]
            return dict(k="enum", y=y, h=FH, name=p["name"], ref=ref, items=p["items"],
                        seg=p.get("seg", False), inline=p.get("inline", False)), EROW - ENUM_TIGHT.get(self.spec["idname"], 0.0)
        if t in ("INT", "FLOAT"):
            return dict(k="num", y=y, h=FH, name=p["name"], ref=ref,
                        st="INT" if t == "INT" else "VALUE", fac=p.get("fac", False),
                        lo=p.get("lo"), hi=p.get("hi"), unit=p.get("unit")), \
                FH + (0.0 if self.spec["idname"] in STACKED else GAP)
        if t in ("STRING", "POINTER"):
            if p.get("rl"):
                return dict(k="str", y=y, h=FH, name=p["name"], ref=ref, ph=p.get("ph", ""),
                            icon=p.get("icon"), rl=p["rl"]), RL_PITCH[p["rl"]]
            return dict(k="str", y=y, h=FH, name=p["name"], ref=ref, ph=p.get("ph", ""),
                        icon=p.get("icon")), FH + GAP
        if t == "WARN":
            return dict(k="warn", y=y, h=ROW, name=p.get("name", "")), ROW
        return dict(k="bool", y=y - BOOL_UP - MENU_DOWN.get(self.spec["idname"], 0.0), h=BROW, name=p["name"], ref=ref), BROW

    def relayout(self):
        self.prepareGeometryChange()
        self._apply_dyn()
        idn = self.spec["idname"]
        if self.img_loaded is not None:
            self._relayout_loaded_image()
            return
        tight = (not (idn in BLOCKS or idn in EXTRA_H or idn in PROP_ORDER or idn in PANELS)
                 and not any(i["enabled"] and i["type"] != "NodeSocketVirtual" for i in self.spec["inputs"])
                 and not self.shown_props())
        orow = ROW + 2 if tight else 21.5
        rows, y = [], HEADER + (2 if tight else 5) - TOP_SHIFT.get(idn, 0.0)
        blk = BLOCKS.get(self.spec["idname"])
        wheel = blk is not None and blk[0] == "wheel"
        merged_in = None
        if idn in PROPS_FIRST:
            for q in self.shown_props():
                if q["id"] in self.panel_props:
                    continue
                row, hh = self.prop_row(q, y)
                rows.append(row)
                y += hh
        y_out0 = y
        blk_y = 0.0
        for s in self.spec["outputs"]:
            sk = self.socks[("out", s["identifier"])]
            vis = self._visible(s, self.lin_out)
            sk.setVisible(vis)
            if not vis:
                continue
            if wheel:
                sk.setPos(self.w, y + ROW / 2 + 12)
                y += ROW
                continue
            if idn in IO_MERGE and merged_in is None:
                fin = next((i for i in self.spec["inputs"] if self._visible(i, self.lin_in)), None)
                if fin is not None and (fin["hide_value"] or fin["identifier"] in self.lin_in):
                    merged_in = (fin["identifier"], y + LROW / 2)
                    rows.append(dict(k="io", y=y, h=LROW, inname=fin["name"],
                                     outname=s["name"] if IO_MERGE[idn] else ""))
                    sk.setPos(self.w, y + LROW / 2)
                    y += LROW
                    continue
            rows.append(dict(k="out", y=y, h=orow, name=s["name"]))
            sk.setPos(self.w, y + orow / 2)
            y += orow
        y += (TIGHT_PAD if tight else (0 if merged_in is not None else 3)) + MENU_DOWN.get(idn, 0.0)
        if blk is not None:
            top = y_out0 if wheel else y
            blk_y = top
            if self._sh_img and blk[0] == "imgsel":
                rows.append(dict(k="imgloaded", y=top, h=(y - top) + blk[1]))
            else:
                rows.append(dict(k="block", y=top, h=(y - top) + blk[1], kind=blk[0]))
            y += blk[1]
        y += PROPS_TOP.get(idn, 0.0)
        for p in (self.shown_props() if idn not in PROPS_FIRST else []):
            if p["id"] in self.panel_props:
                continue
            row, hh = self.prop_row(p, y)
            rows.append(row)
            y += hh
        if self._sh_img:   # imagen cargada: Source / Color Space / Alpha tras los menus de Interpolation...
            for _nm, _id, _it in (("Source", "_img_src", IMG_SRC_ITEMS), ("Color Space", "_img_cs", IMG_CS_ITEMS),
                                  ("Alpha", "_img_alpha", IMG_ALPHA_ITEMS)):
                rows.append(dict(k="enum", y=y, h=FH, name=_nm, ref=("p", _id), items=_it,
                                 inline=_id != "_img_src", nocolon=True, lw=0.344, arrow=5.8))
                y += 25.0
        y -= INPUT_PULL.get(idn, 0.0)   # en Blender las entradas quedan mas cerca del ultimo menu
        panel_y = {}
        for s in self.spec["inputs"]:
            sk = self.socks[("in", s["identifier"])]
            vis = self._visible(s, self.lin_in)
            if not vis:
                sk.setVisible(False)
                continue
            sk.setVisible(True)
            if merged_in is not None and s["identifier"] == merged_in[0]:
                sk.setPos(0, merged_in[1])
                continue
            if self.spec["idname"] == "ShaderNodeNormal":
                sk.setPos(0, blk_y + blk[1] / 2)
                continue
            ident, st = s["identifier"], s.get("stype")
            pname = self.pmap.get(s["name"])
            if pname and s["name"].startswith(pname + " "):
                s = dict(s, name=s["name"][len(pname) + 1:])   # dentro de su panel Blender muestra "Roughness", no "Diffuse Roughness"
            if pname:
                if pname not in panel_y:
                    if panel_y and self.panel_open[list(panel_y)[-1]]:
                        y += PANEL_GAP_END
                    panel_y[pname] = y
                    rows.append(dict(k="panel", y=y, h=ROW, name=pname, panel=pname))
                    y += ROW
                    if self.panel_open[pname]:
                        y += PANEL_GAP_HEAD
                    if self.panel_open[pname]:
                        for pp in self.shown_props():
                            if self.panel_props.get(pp["id"]) == pname and pp["type"] == "ENUM":
                                rows.append(dict(k="enum", y=y, h=FH, name=pp["name"],
                                                 ref=("p", pp["id"]), items=pp["items"]))
                                y += FH + GAP
                if not self.panel_open[pname]:
                    sk.setVisible(ident in self.lin_in)
                    sk.setPos(0, panel_y[pname] + ROW / 2)
                    continue
            d = self.vals.get(ident)
            ref = ("v", ident)
            plain = (ident in self.lin_in or s["hide_value"] or d is None)
            if not plain and st in ("VECTOR", "ROTATION") and isinstance(d, list):
                _r0 = len(rows)
                rows.append(dict(k="label", y=y, h=LROW, name=s["name"]))
                sk.setPos(0, y + LROW / 2)
                y += LROW
                for i in range(len(d)):
                    rows.append(dict(k="vec", y=y, h=FH,
                                     name="" if s["type"] in ("NodeSocketVector", "NodeSocketVector2D")
                                     else ("XYZ"[i] if i < 3 else "?"),
                                     ref=ref, i=i, st=st, vt=s["type"],
                                     unit={"NodeSocketVectorTranslation": "m",
                                           "NodeSocketVectorEuler": "deg"}.get(s["type"])))
                    y += FH
                if self._inactive(s):   # entrada que no influye: etiqueta y los tres campos atenuados
                    for _rr in rows[_r0:]:
                        _rr["dim"] = True
                y += GAP   # hueco tras cada grupo X/Y/Z
                continue
            kind = None
            if not plain:
                kind = {"VALUE": "num", "INT": "num", "RGBA": "color", "BOOLEAN": "boolin",
                        "STRING": "str", "MENU": "str"}.get(st)
            if kind is None:
                rows.append(dict(k="label", y=y, h=LROW, name=s["name"]))
                sk.setPos(0, y + LROW / 2)
                y += LROW
            else:
                if kind == "boolin":
                    y -= 1.0   # Thin Wall: Blender la deja ~1 unidad mas arriba (paso 21 desde Alpha)
                lo, hi = s.get("min"), s.get("max")
                if "Factor" in s["type"] and not isinstance(lo, (int, float)):
                    lo, hi = ((-1.0, 1.0) if s["identifier"] == "Subsurface Anisotropy"
                              else (0.0, 2.0) if (idn, s["identifier"]) == ("CompositorNodeKuwahara", "Eccentricity")
                              else (-1.0, 1.0) if (idn, s["identifier"]) == ("CompositorNodeLensdist", "Distortion")   # 0.000 = barra a medias (captura de Blender)
                              else (0.0, 1.0))   # factores de 0 a 1 (el JSON no trae min/max); Anisotropy va de -1 a 1
                fac = ("Factor" in s["type"]) and isinstance(lo, (int, float)) and hi != lo
                rows.append(dict(k=kind, y=y, h=FH, name=s["name"], ref=ref, st=st,
                                 fac=fac, lo=lo, hi=hi, dim=self._inactive(s), unit={"NodeSocketFloatDistance": "m", "NodeSocketFloatWavelength": "nm", "NodeSocketFloatPixel": "px", "NodeSocketFloatAngle": "deg"}.get(s["type"])))
                if st == "MENU" and (idn, s["name"]) in MENU_ITEMS:   # desplegable en vez de campo de texto
                    rows[-1].update(k="enum", items=MENU_ITEMS[(idn, s["name"])])
                sk.setPos(0, y + FH / 2)
                if kind == "boolin":
                    y += 1.0   # compensa: las filas siguientes no se mueven
                y += FH + GAP
        if idn in TRAILING_PANELS:
            tp = TRAILING_PANELS[idn]
            rows.append(dict(k="panel", y=y, h=ROW, name=tp, panel=tp))
            y += ROW
        if idn in STACKED:
            for a, b in zip(rows, rows[1:]):
                if (a["k"] == "num" and b["k"] == "num"
                        and abs(a["y"] + a["h"] - b["y"]) < 0.01):
                    a["jb"] = True      # el campo de abajo esta pegado: esquinas inferiores rectas
                    b["jt"] = True      # el de arriba esta pegado: esquinas superiores rectas
        self.rows = rows
        self.h = y + 4.2 + EXTRA_H.get(self.spec["idname"], 0)
        self.update()

    def load_image(self, name, users=1, cs="", path=None):
        """Deja el nodo Image como en Blender cuando ya tiene una imagen cargada (p. ej. Multiple Images)."""
        self.img_loaded = {"name": name, "users": users, "path": path}
        lo, hi = self.width_limits()
        if self.spec["idname"].startswith("Compositor"):   # el Image Texture de Shader conserva su ancho
            self.w = max(lo, min(hi, IMG_LOADED_W))
        self.pvals.update({"_img_src": "FILE", "_img_cs": cs, "_img_alpha": "STRAIGHT"})
        self.relayout()

    def _relayout_loaded_dispatch(self):
        """Compositor: diseno propio de imagen cargada. Shader (Image/Environment Texture): el diseno normal
        con la fila de imagen cargada y los menus Source / Color Space / Alpha al final."""
        if self.spec["idname"].startswith("Compositor"):
            self._relayout_loaded_image()
            return
        saved, self.img_loaded, self._sh_img = self.img_loaded, None, True
        try:
            self.relayout()
        finally:
            self.img_loaded, self._sh_img = saved, False
        self.update()

    def _img_parent(self):
        sc = self.scene()
        return sc.views()[0] if sc is not None and sc.views() else None

    def set_image(self, name, path=None):
        """Carga una imagen en el nodo (como elegirla en Blender) y actualiza el contador de usuarios."""
        if path:
            IMAGES[name] = path
        sc = self.scene()
        others = [q for q in (sc.nodes() if sc is not None else [])
                  if q is not self and q.img_loaded is not None and q.img_loaded["name"] == name]
        self.load_image(name, len(others) + 1, "sRGB", IMAGES.get(name))
        for q in others:
            q.img_loaded["users"] = len(others) + 1
            q.update()
        if sc is not None:
            sc.sync()

    def unload_image(self):
        """La X de la fila: quita la imagen y vuelve a mostrar el selector con New / Open."""
        self.img_loaded = None
        self.relayout()
        if self.scene() is not None:
            self.scene().sync()

    def open_image_file(self):
        fn, _ = QFileDialog.getOpenFileName(
            self._img_parent(), "Open Image", "",
            "Imagenes (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.tga *.webp *.gif *.exr *.hdr);;Todos los archivos (*)")
        if fn:
            self.set_image(Path(fn).name, fn)

    def new_image(self):
        t, ok = QInputDialog.getText(self._img_parent(), "New Image", "Nombre", text="Untitled")
        if ok and t.strip():
            self.set_image(t.strip())

    def pick_image(self):
        """Selector desplegable: imagenes ya abiertas en esta sesion (o directamente Open si no hay ninguna)."""
        if not IMAGES:
            self.open_image_file()
            return
        menu = QMenu(self._img_parent())
        for nm in IMAGES:
            menu.addAction(nm)
        menu.addSeparator()
        op = menu.addAction("Open Image...")
        act = menu.exec(QCursor.pos())
        if act is None:
            return
        if act is op:
            self.open_image_file()
        else:
            self.set_image(act.text().replace("&&", "&"), IMAGES.get(act.text()))

    def _img_hit(self, pos):
        """Zona pulsada en la fila de imagen: 'sel', 'new', 'open' o 'unlink' (None si no es esa fila)."""
        x, fw = PAD, self.w - 2 * PAD
        for r in self.rows:
            if r["k"] == "block" and r.get("kind") == "imgsel":
                yy = r["y"] + IMG_TOP
                if not (yy <= pos.y() <= yy + 20.0) or not (x <= pos.x() <= x + fw):
                    return None
                sw = 31.0
                if pos.x() < x + sw:
                    return "sel"
                gx = x + sw + 1
                if pos.x() < gx:
                    return None
                return "new" if pos.x() < (gx + x + fw) / 2 else "open"
            if r["k"] == "imgloaded":
                yy = r["y"] + IMG_TOP
                if not (yy <= pos.y() <= yy + 20.0) or not (x <= pos.x() <= x + fw):
                    return None
                wide = self.w >= 200
                sw = 30.5 if wide else 21.0
                if pos.x() < x + sw:
                    return "sel"
                ic_w = [20.0] * 4
                users = max(24.0, 0.108 * self.w)
                gw = fw - sw - 1
                rest = users + sum(ic_w)
                if gw - rest < 40:
                    f = max(0.5, (gw - 40) / rest)
                    users *= f
                    ic_w = [v * f for v in ic_w]
                acc = x + sw + 1
                for name, wv in zip(("sel", "users", "shield", "dup", "open", "unlink"),
                                    [gw - users - sum(ic_w), users] + ic_w):
                    if pos.x() < acc + wv:
                        return name if name in ("sel", "open", "unlink") else None
                    acc += wv
                return None
        return None

    def _img_do(self, what):
        if what == "sel":
            self.pick_image()
        elif what == "open":
            self.open_image_file()
        elif what == "new":
            self.new_image()
        elif what == "unlink":
            self.unload_image()

    def _relayout_shader_img(self):
        """Image/Environment Texture con imagen: diseno normal + fila de imagen cargada + Source/Color Space/Alpha."""
        saved, self.img_loaded, self._sh_img = self.img_loaded, None, True
        try:
            self.relayout()
        finally:
            self.img_loaded, self._sh_img = saved, False
        self.update()

    def _relayout_loaded_image(self):
        if not self.spec["idname"].startswith("Compositor"):
            self._relayout_shader_img()
            return
        rows, y = [], HEADER + 5
        for key, sk in self.socks.items():
            if key[0] == "in":
                sk.setVisible(False)
        for s in self.spec["outputs"]:
            sk = self.socks[("out", s["identifier"])]
            sk.setVisible(True)
            rows.append(dict(k="out", y=y, h=21.5, name=s["name"]))
            sk.setPos(self.w, y + 21.5 / 2)
            y += 21.5
        y += 3
        rows.append(dict(k="imgloaded", y=y, h=IMGSEL_H))
        y += IMGSEL_H
        rows.append(dict(k="enum", y=y, h=FH, name="Source", ref=("p", "_img_src"), items=IMG_SRC_ITEMS, arrow=5.8))
        y += 25.0
        rows.append(dict(k="enum", y=y, h=FH, name="Color Space", ref=("p", "_img_cs"), items=IMG_CS_ITEMS,
                         inline=True, nocolon=True, lw=0.344, arrow=5.8))
        y += 25.0
        rows.append(dict(k="enum", y=y, h=FH, name="Alpha", ref=("p", "_img_alpha"), items=IMG_ALPHA_ITEMS,
                         inline=True, nocolon=True, lw=0.344, arrow=5.8))
        self.rows = rows
        self.h = IMG_LOADED_H
        self.update()

    def boundingRect(self):
        return QRectF(-8, -8, self.w + 16, self.h + 16)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene() is not None:
            for l in self.scene().links:
                if l.a.node is self or l.b.node is self:
                    l.update_path()
        return super().itemChange(change, value)

    # ---- valores
    def get(self, r):
        src = self.pvals if r["ref"][0] == "p" else self.vals
        return src[r["ref"][1]]

    def put(self, r, v):
        src = self.pvals if r["ref"][0] == "p" else self.vals
        src[r["ref"][1]] = v

    # ---- dibujo
    # ---- interaccion
    # ---- Color Ramp interactivo (marcadores que se deslizan, como en Blender)
    def _panel_at(self, pos):
        for r in self.rows:
            if r["k"] == "panel" and r["y"] <= pos.y() < r["y"] + r["h"] and 0 <= pos.x() <= self.w:
                return r
        return None

    # ---- ancho (arrastrar los bordes izquierdo/derecho, como en Blender)
    EDGE = 5.0
    _imgclk = None     # zona de la fila de imagen pulsada (se ejecuta al soltar)
    _sh_img = False    # True solo mientras se calcula el diseno de un Image Texture con imagen

    def width_limits(self):
        lo, hi = WIDTH_LIMITS.get(self.spec["idname"], (80.0, 700.0))
        return float(lo), float(hi)

    def _edge_at(self, pos):
        lo, hi = self.width_limits()
        if hi - lo < 1.0 or not (0.0 <= pos.y() <= self.h):
            return None
        if abs(pos.x()) <= self.EDGE:
            return "l"
        if abs(pos.x() - self.w) <= self.EDGE:
            return "r"
        return None

    def set_width(self, nw, rs=None):
        lo, hi = self.width_limits()
        nw = max(lo, min(hi, float(nw)))
        if abs(nw - self.w) < 0.01:
            return
        self.w = nw
        self.relayout()
        if rs is not None and rs["edge"] == "l":
            self.setPos(rs["x0"] + rs["w0"] - nw, self.pos().y())   # el borde derecho se queda quieto
        sc = self.scene()
        if sc is not None:
            for l in sc.links:
                if l.a.node is self or l.b.node is self:
                    l.update_path()

    def hoverMoveEvent(self, e):
        if self._rs is None:
            if self._edge_at(e.pos()) is not None:
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.unsetCursor()
        super().hoverMoveEvent(e)

    def hoverLeaveEvent(self, e):
        if self._rs is None:
            self.unsetCursor()
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            edge = self._edge_at(e.pos())
            if edge is not None and self.scene() is not None:
                if not self.isSelected():
                    self.scene().clearSelection()
                    self.setSelected(True)
                self._rs = dict(edge=edge, sx=e.scenePos().x(), w0=self.w, x0=self.pos().x())
                e.accept()
                return
            if self.ramp is not None and self._ramp_press(e):
                e.accept()
                return
            ih = self._img_hit(e.pos())
            if ih is not None and self.scene() is not None:
                if not self.isSelected():
                    self.scene().clearSelection()
                    self.setSelected(True)
                self._imgclk = ih
                e.accept()
                return
            fr = self._field_at(e.pos())
            if fr is not None and self.scene() is not None:
                if not self.isSelected():
                    self.scene().clearSelection()
                    self.setSelected(True)
                self._press_field(fr, e)
                e.accept()
                return
            r = self._panel_at(e.pos())
            if r is not None:
                self.panel_open[r["panel"]] = not self.panel_open[r["panel"]]
                if self.scene() is not None:
                    self.scene().sync()
                e.accept()
                return
        super().mousePressEvent(e)

    FIELD_KINDS = ("enum", "bool", "boolin", "num", "vec", "color", "str")

    def _field_at(self, pos):
        if not (PAD <= pos.x() <= self.w - PAD):
            return None
        for r in self.rows:
            if r["k"] in self.FIELD_KINDS and r["y"] <= pos.y() < r["y"] + r["h"]:
                return r
        return None

    def _num_get(self, r):
        v = self.get(r)
        return v[r["i"]] if r["k"] == "vec" else v

    def _num_set(self, r, x):
        if r["k"] == "vec":
            self.get(r)[r["i"]] = x
        else:
            self.put(r, int(round(x)) if r.get("st") == "INT" else float(x))

    def _press_field(self, r, e):
        """Clic sobre un campo: casillas y botones segmentados al instante, numeros se arrastran,
        menus/colores/textos se abren al soltar (como en Blender)."""
        k = r["k"]
        self._ed = dict(r=r, sx=e.screenPos().x(), moved=False, mode="noop")
        if k == "str" and r.get("rl") == "scene" and e.pos().x() >= self.w - PAD - 20.0:
            self.put(r, "")                    # X de Render Layers: quita la escena
            self.scene().sync()
            return
        if k in ("bool", "boolin"):
            self.put(r, not self.get(r))
            self.scene().sync()
        elif k == "enum" and r.get("seg"):
            n = len(r["items"])
            fw = self.w - 2 * PAD
            idx = max(0, min(n - 1, int((e.pos().x() - PAD) / (fw / n))))
            self.put(r, r["items"][idx]["id"])
            self.scene().sync()
        elif k in ("num", "vec"):
            self._ed.update(mode="num", v0=self._num_get(r))
        else:
            self._ed["mode"] = "dialog"

    def _drag_num(self, ed, e, dx):
        r = ed["r"]
        lo, hi = r.get("lo"), r.get("hi")
        has = isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and hi > lo
        mods = e.modifiers()
        shift, ctrl = bool(mods & Qt.ShiftModifier), bool(mods & Qt.ControlModifier)
        deg, isint = r.get("unit") == "deg", r.get("st") == "INT"
        if r.get("fac") and has:
            t = max(0.0, min(1.0, (e.pos().x() - PAD) / (self.w - 2 * PAD)))
            nv = lo + t * (hi - lo)
            if ctrl:
                nv = round(nv * 10) / 10
        else:
            v0 = ed["v0"]
            base = math.degrees(v0) if deg else float(v0)
            if isint:
                step = 0.1
            elif deg:
                step = 0.5
            else:
                a = abs(base)
                step = 0.01 if a < 10 else 0.1 if a < 100 else 1.0
            if shift:
                step /= 10
            nd = base + dx * step
            if ctrl:
                snap = 5.0 if deg else (1.0 if isint else 0.1)
                nd = round(nd / snap) * snap
            nv = math.radians(nd) if deg else nd
        if has:
            nv = max(lo, min(hi, nv))
        self._num_set(r, nv)
        self.update()

    def mouseMoveEvent(self, e):
        if self._rm is not None:
            self._ramp_move(e)
            e.accept()
            return
        rs = self._rs
        if rs is not None:
            dx = e.scenePos().x() - rs["sx"]
            self.set_width(rs["w0"] + dx if rs["edge"] == "r" else rs["w0"] - dx, rs)
            e.accept()
            return
        ed = self._ed
        if ed is None:
            super().mouseMoveEvent(e)
            return
        dx = e.screenPos().x() - ed["sx"]
        if abs(dx) >= 3:
            ed["moved"] = True
        if ed["mode"] == "num" and ed["moved"]:
            self._drag_num(ed, e, dx)
        e.accept()

    def mouseReleaseEvent(self, e):
        if self._rm is not None:
            self._ramp_release(e)
            e.accept()
            return
        if self._imgclk is not None:
            ih, self._imgclk = self._imgclk, None
            self._img_do(ih)
            e.accept()
            return
        if self._rs is not None:
            self._rs = None
            if self.scene() is not None:
                self.scene().sync()
            e.accept()
            return
        ed = self._ed
        if ed is None:
            super().mouseReleaseEvent(e)
            return
        self._ed = None
        if ed["mode"] in ("num", "dialog") and not ed["moved"]:
            self.edit(ed["r"])
        if ed["mode"] != "noop":
            if self.scene() is not None:
                self.scene().sync()
            else:
                self.relayout()
        e.accept()

    def mouseDoubleClickEvent(self, e):
        if self._field_at(e.pos()) is not None:
            e.accept()
            return
        pos = e.pos()
        if self._panel_at(pos) is not None:
            e.accept()
            return
        if PAD <= pos.x() <= self.w - PAD:
            for r in self.rows:
                if r["y"] <= pos.y() < r["y"] + r["h"] and self.edit(r):
                    if self.scene() is not None:
                        self.scene().sync()
                    else:
                        self.relayout()
                    e.accept()
                    return
        super().mouseDoubleClickEvent(e)

    def edit(self, r):
        parent = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if r["k"] in ("out", "label", "panel", "block", "warn", "imgloaded"):
            return False
        k, v = r["k"], self.get(r)
        if k == "enum":
            names = [i["name"] for i in r["items"]]
            cur = next((n for n, i in enumerate(r["items"]) if i["id"] == v), 0)
            menu = QMenu(parent)
            for nm in names:
                a = menu.addAction(nm)
                a.setCheckable(True)
                a.setChecked(nm == names[cur])
            act = menu.exec(QCursor.pos())
            item, ok = (act.text(), True) if act is not None else (None, False)
            if ok:
                self.put(r, r["items"][names.index(item)]["id"])
            return True
        if k in ("bool", "boolin"):
            self.put(r, not v)
            return True
        if k == "num":
            deg = r.get("unit") == "deg"
            if r["st"] == "INT":
                n, ok = QInputDialog.getInt(parent, "Valor", r["name"], int(v), -2**31, 2**31 - 1)
            else:
                cur = math.degrees(float(v)) if deg else float(v)
                n, ok = QInputDialog.getDouble(parent, "Valor", r["name"], cur, -1e9, 1e9, 4)
                if ok and deg:
                    n = math.radians(n)
            if ok:
                self.put(r, n)
            return True
        if k == "vec":
            vdeg = r.get("unit") == "deg"
            cur = math.degrees(float(v[r["i"]])) if vdeg else float(v[r["i"]])
            n, ok = QInputDialog.getDouble(parent, "Valor", r["name"] or "Valor", cur, -1e9, 1e9, 4)
            if ok and vdeg:
                n = math.radians(n)
            if ok:
                v[r["i"]] = n
            return True
        if k == "color":
            c = QColorDialog.getColor(QColor.fromRgbF(lin2s(v[0]), lin2s(v[1]), lin2s(v[2])), parent, "Color")
            if c.isValid():
                self.put(r, [s2lin(c.redF()), s2lin(c.greenF()), s2lin(c.blueF()), v[3] if len(v) > 3 else 1.0])
            return True
        if k == "str":
            t, ok = QInputDialog.getText(parent, "Texto", r["name"], text=str(v or ""))
            if ok:
                self.put(r, t)
            return True
        return False


# ------------------------------------------------------------ Reroute y Frame
class FrameItem(QGraphicsItem):
    """Frame: recuadro con etiqueta que agrupa nodos. Al moverlo arrastra los nodos que contiene;
    se redimensiona desde la esquina inferior derecha y se renombra con doble clic."""
    is_frame = True
    GRIP = 16.0

    def __init__(self, spec, cat=None):
        super().__init__()
        self.spec = copy.deepcopy(spec)
        self.cat = None
        self.w, self.h = 300.0, 200.0
        self.label = "Frame"
        self.lin_in, self.lin_out = set(), set()
        self.socks = {}
        self.rows = []
        self._kids, self._prev, self._resizing = [], None, False
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(-1)      # por debajo de los cables y de los nodos

    def relayout(self):
        pass

    def boundingRect(self):
        return QRectF(-3, -3, self.w + 6, self.h + 6)

    def paint(self, p, opt, widget=None):
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.w, self.h), 4, 4)
        p.fillPath(path, S.HEAD["frame_node"])
        sel = self.isSelected()
        p.setPen(QPen(S.SEL if sel else S.OUTLINE, 2.0 if sel else NODE_LINE_W))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        if NodeItem.F is None:
            NodeItem.F = make_font()
        p.setFont(NodeItem.F)
        p.setPen(S.TITLE)
        p.drawText(QRectF(8, 4, self.w - 16, 20), Qt.AlignHCenter | Qt.AlignVCenter, self.label)
        p.setPen(QPen(S.DIM, 1.0))        # asa de redimensionado
        p.drawLine(QPointF(self.w - 12, self.h - 4), QPointF(self.w - 4, self.h - 12))
        p.drawLine(QPointF(self.w - 8, self.h - 4), QPointF(self.w - 4, self.h - 8))

    def _grab_kids(self):
        sc = self.scene()
        self._prev = QPointF(self.pos())
        self._kids = []
        if sc is None:
            return
        r = self.mapRectToScene(QRectF(0, 0, self.w, self.h))
        for it in sc.items(r):
            if isinstance(it, (NodeItem, RerouteItem)) and not it.isSelected():
                body = (QRectF(-it.R, -it.R, 2 * it.R, 2 * it.R) if isinstance(it, RerouteItem)
                        else QRectF(0, 0, it.w, it.h))
                if r.contains(it.mapRectToScene(body)):
                    self._kids.append(it)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if e.pos().x() > self.w - self.GRIP and e.pos().y() > self.h - self.GRIP:
                self._resizing = True
                if self.scene() is not None and not self.isSelected():
                    self.scene().clearSelection()
                    self.setSelected(True)
                e.accept()
                return
            self._grab_kids()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._resizing:
            self.prepareGeometryChange()
            self.w, self.h = max(60.0, e.pos().x()), max(40.0, e.pos().y())
            self.update()
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._resizing, self._kids = False, []
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        parent = self.scene().views()[0] if self.scene() and self.scene().views() else None
        t, ok = QInputDialog.getText(parent, "Frame", "Etiqueta", text=self.label)
        if ok:
            self.label = t
            self.update()
        e.accept()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self._kids and self._prev is not None:
            d = value - self._prev
            self._prev = QPointF(value)
            for k in self._kids:
                k.setPos(k.pos() + d)
        return super().itemChange(change, value)


def make_node(spec, mode):
    idn = spec["idname"]
    if idn == "NodeFrame":
        return FrameItem(spec)
    if idn == "NodeReroute":
        return RerouteItem(spec)
    return NodeItem(spec, category(idn, mode))


# ------------------------------------------------------------------ escena
class NodeScene(QGraphicsScene):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.links = []
        self.temp = None
        self.exporting = False
        self.drag_src = None
        self.setSceneRect(-50000, -50000, 100000, 100000)

    def drawBackground(self, p, rect):
        if self.exporting:
            return
        p.fillRect(rect, S.BG)
        step = 20
        if rect.width() / step > 300:
            return
        x0 = int(math.floor(rect.left() / step)) * step
        y0 = int(math.floor(rect.top() / step)) * step
        for x in range(x0, int(rect.right()) + step, step):
            p.setPen(QPen(S.GRID_MAJOR if x % (step * 5) == 0 else S.GRID_MINOR, 0))
            p.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        for y in range(y0, int(rect.bottom()) + step, step):
            p.setPen(QPen(S.GRID_MAJOR if y % (step * 5) == 0 else S.GRID_MINOR, 0))
            p.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def nodes(self):
        return [i for i in self.items() if isinstance(i, NodeItem)]

    def sync(self):
        nodes = self.nodes()
        for n in nodes:
            n.lin_in, n.lin_out = set(), set()
        for l in self.links:
            l.a.node.lin_out.add(l.a.spec["identifier"])
            l.b.node.lin_in.add(l.b.spec["identifier"])
        for n in nodes:
            n.relayout()
        self._sync_reroutes()
        for l in self.links:
            l.update_path()

    def layout_items(self):
        return [i for i in self.items() if isinstance(i, (RerouteItem, FrameItem))]

    def _sync_reroutes(self):
        """Cada Reroute toma el tipo de lo que tiene conectado; se repite para cadenas de Reroute."""
        rer = [i for i in self.items() if isinstance(i, RerouteItem)]
        for _ in range(len(rer) + 1):
            for r in rer:
                r.update_type(self.links)
        for r in rer:
            r.update()

    def drag_begin(self, sock, pos):
        src = sock
        if not sock.is_out:
            # arrastrar desde una entrada ya conectada despega el link (como en Blender)
            old = next((l for l in self.links if l.b is sock), None)
            if old is not None:
                src = old.a
                self.links.remove(old)
                self.removeItem(old)
                self.sync()
        self.drag_src = src
        self.temp = LinkItem(src, None)
        self.addItem(self.temp)
        self.temp.end = pos
        self.temp.update_path()

    def drag_update(self, pos):
        if self.temp is not None:
            self.temp.end = pos
            self.temp.update_path()

    def drag_end(self, src, pos):
        if self.temp is not None:
            self.removeItem(self.temp)
            self.temp = None
        r = 14.0   # tolerancia al soltar: engancha al socket mas cercano
        near = [i for i in self.items(QRectF(pos.x() - r, pos.y() - r, 2 * r, 2 * r))
                if isinstance(i, SocketItem)]
        near.sort(key=lambda s: (s.scenePos() - pos).manhattanLength())
        for it in near:
            if isinstance(it, SocketItem) and it.is_out != src.is_out and it.node is not src.node:
                o, i = (src, it) if src.is_out else (it, src)
                self.connect_socks(o, i)
                return

    def connect_socks(self, o, i):
        for l in list(self.links):
            if l.b is i:
                self.links.remove(l)
                self.removeItem(l)
        l = LinkItem(o, i)
        self.addItem(l)
        self.links.append(l)
        self.sync()

    def delete_selected(self):
        for it in self.selectedItems():
            if isinstance(it, (NodeItem, RerouteItem)):
                for l in [l for l in self.links if l.a.node is it or l.b.node is it]:
                    self.links.remove(l)
                    self.removeItem(l)
                self.removeItem(it)
            elif isinstance(it, FrameItem):
                self.removeItem(it)
            elif isinstance(it, LinkItem) and it in self.links:
                self.links.remove(it)
                self.removeItem(it)
        self.sync()


class NodeView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._pan = None

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale(f, f)

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._pan = e.position()
            self.setCursor(Qt.ClosedHandCursor)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._pan is not None:
            d = e.position() - self._pan
            self._pan = e.position()
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - d.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - d.y()))
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton and self._pan is not None:
            self._pan = None
            self.unsetCursor()
            e.accept()
            return
        super().mouseReleaseEvent(e)


# Entradas del menu Add que Node Wrangler pone en Blender: no son tipos de nodo, crean nodos Image
VIRTUAL_ADD = [{"idname": "_MultipleImages", "label": "Multiple Images"},
               {"idname": "_ImageSequence", "label": "Image Sequence"}]
IMAGE_NODE = {"compositor": "CompositorNodeImage", "shader": "ShaderNodeTexImage"}


class AddDialog(QDialog):
    def __init__(self, specs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Añadir nodo")
        self.resize(360, 480)
        self.specs = sorted(specs, key=lambda s: s["label"].lower())
        self.chosen = None
        lay = QVBoxLayout(self)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Buscar nodo...")
        self.lst = QListWidget()
        lay.addWidget(self.edit)
        lay.addWidget(self.lst)
        self.edit.textChanged.connect(self.refill)
        self.edit.returnPressed.connect(self.accept)
        self.lst.itemDoubleClicked.connect(lambda _i: self.accept())
        self.refill("")

    def refill(self, t):
        from difflib import SequenceMatcher
        self.lst.clear()
        t = t.strip().lower()
        hits = []
        for s in self.specs:
            lab, idn = s["label"].lower(), s["idname"].lower()
            if t in lab or t in idn:
                hits.append((0.0, s))                      # coincidencia exacta: va primero
            elif len(t) >= 4:                              # tolera erratas ("kawahura" -> Kuwahara)
                sc = max(SequenceMatcher(None, t, w).ratio() for w in [lab] + lab.split())
                if sc >= 0.6:
                    hits.append((1.0 - sc, s))
        hits.sort(key=lambda h: h[0])                      # estable: exactos en orden alfabetico, luego por parecido
        for _score, s in hits:
            it = QListWidgetItem(s["label"])
            it.setData(Qt.UserRole, s["idname"])
            self.lst.addItem(it)
        if self.lst.count():
            self.lst.setCurrentRow(0)

    def accept(self):
        it = self.lst.currentItem()
        if it is not None:
            self.chosen = it.data(Qt.UserRole)
            super().accept()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nodo Capture")
        self.resize(1280, 800)
        self.scenes = {m: NodeScene(m) for m in CATALOG}
        self.view = NodeView()
        self.setCentralWidget(self.view)
        self.mode = QComboBox()
        self.mode.addItem("Shader Editor", "shader")
        self.mode.addItem("Compositor", "compositor")
        self.mode.currentIndexChanged.connect(self.switch)
        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(1, 16)
        self.scale_spin.setValue(4)
        self.scale_spin.setPrefix("Escala ×")
        tb = self.addToolBar("main")
        tb.setMovable(False)
        tb.addWidget(self.mode)
        self._act(tb, "Añadir nodo", "Shift+A", self.add_node)
        self._act(tb, "Borrar", "Delete", lambda: self.cur.delete_selected())
        self._act(tb, "Ocultar sin conectar", "Ctrl+H", self.toggle_hide)
        tb.addSeparator()
        tb.addWidget(self.scale_spin)
        self._act(tb, "Exportar PNG", "Ctrl+E", lambda: self.export("png", False))
        self._act(tb, "PNG transparente", "Ctrl+Shift+E", lambda: self.export("png", True))
        self._act(tb, "Exportar SVG", "Ctrl+Alt+E", lambda: self.export("svg", False))
        self.switch()
        import project
        project.init(self)   # menu Archivo: Nuevo / Abrir / Guardar / Guardar como (proyectos .nodocap)
        import copypaste
        copypaste.init(self)   # menu Editar: Copiar (Ctrl+C) / Pegar (Ctrl+V) / Duplicar (Shift+D)
        import blender_export
        blender_export.init(self)   # menu Blender + boton "Copiar para Blender" (Ctrl+Shift+C)

    def _act(self, tb, text, key, fn):
        a = QAction(text, self)
        a.setShortcut(key)
        a.setToolTip(f"{text} ({key})")
        a.triggered.connect(lambda _c=False: fn())
        tb.addAction(a)
        self.addAction(a)

    def closeEvent(self, e):
        import project
        if project.confirm_discard(self):   # pregunta si hay cambios sin guardar
            e.accept()
        else:
            e.ignore()

    @property
    def cur(self):
        return self.scenes[self.mode.currentData()]

    def switch(self, _i=0):
        self.view.setScene(self.cur)

    def add_node(self):
        sc = self.cur
        vp = self.view.viewport()
        local = vp.mapFromGlobal(QCursor.pos())
        pt = local if vp.rect().contains(local) else vp.rect().center()
        pos = self.view.mapToScene(pt)
        dlg = AddDialog(CATALOG[sc.mode] + VIRTUAL_ADD, self)
        if not dlg.exec() or not dlg.chosen:
            return
        if dlg.chosen in ("_MultipleImages", "_ImageSequence"):
            spec = next(s for s in CATALOG[sc.mode] if s["idname"] == IMAGE_NODE[sc.mode])
            node = make_node(spec, sc.mode)
            node.setPos(pos)
            if dlg.chosen == "_MultipleImages" and sc.mode == "compositor":
                node.load_image("Multiple Images.png", MULTI_IMG_USERS)   # un solo nodo, como Node Wrangler
            sc.clearSelection()
            sc.addItem(node)
            node.setSelected(True)
        else:
            spec = next(s for s in CATALOG[sc.mode] if s["idname"] == dlg.chosen)
            node = make_node(spec, sc.mode)
            node.setPos(pos)
            sc.clearSelection()
            sc.addItem(node)
            node.setSelected(True)

    def toggle_hide(self):
        sc = self.cur
        for n in sc.selectedItems():
            if isinstance(n, NodeItem):
                n.hide_unused = not n.hide_unused
        sc.sync()

    def export(self, kind, transparent, path=None):
        sc = self.cur
        if not sc.nodes() and not sc.layout_items():
            return
        rect = sc.itemsBoundingRect().adjusted(-24, -24, 24, 24)
        if path is None:
            flt = "PNG (*.png)" if kind == "png" else "SVG (*.svg)"
            path, _ = QFileDialog.getSaveFileName(self, "Exportar", str(Path.home() / f"nodos.{kind}"), flt)
            if not path:
                return
        scale = self.scale_spin.value()
        sel = sc.selectedItems()
        sc.clearSelection()
        sc.exporting = True
        try:
            if kind == "png":
                img = QImage(max(1, int(rect.width() * scale)), max(1, int(rect.height() * scale)),
                             QImage.Format_ARGB32)
                img.fill(Qt.transparent if transparent else S.BG)
                p = QPainter(img)
                p.setRenderHint(QPainter.Antialiasing)
                p.setRenderHint(QPainter.TextAntialiasing)
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                sc.render(p, QRectF(img.rect()), rect)
                p.end()
                img.save(path)
            else:
                g = QSvgGenerator()
                g.setFileName(path)
                g.setSize(QSize(int(rect.width()), int(rect.height())))
                g.setViewBox(QRectF(0, 0, rect.width(), rect.height()))
                p = QPainter(g)
                p.setRenderHint(QPainter.Antialiasing)
                if not transparent:
                    p.fillRect(QRectF(0, 0, rect.width(), rect.height()), S.BG)
                sc.render(p, QRectF(0, 0, rect.width(), rect.height()), rect)
                p.end()
        finally:
            sc.exporting = False
            for it in sel:
                it.setSelected(True)


def apply_dark(app):
    app.setStyle("Fusion")
    pal = QPalette()
    for role, c in ((QPalette.Window, "#2b2b2b"), (QPalette.WindowText, "#e6e6e6"),
                    (QPalette.Base, "#1e1e1e"), (QPalette.AlternateBase, "#2b2b2b"),
                    (QPalette.Text, "#e6e6e6"), (QPalette.Button, "#3a3a3a"),
                    (QPalette.ButtonText, "#e6e6e6"), (QPalette.Highlight, "#4772b3"),
                    (QPalette.HighlightedText, "#ffffff")):
        pal.setColor(role, QColor(c))
    app.setPalette(pal)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_dark(app)
    w = Window()
    import themes
    themes.install(w)
    w.show()
    sys.exit(app.exec())
