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
from node_edit import EditMixin
from node_layout import LayoutMixin
from metrics import (BOOL_UP, BROW, ENUM_TIGHT, EROW, IMAGES, IMG_ALPHA_ITEMS, IMG_CS_ITEMS, IMG_LOADED_H, IMG_SRC_ITEMS, INPUT_PULL, LROW, MENU_DOWN, PANEL_GAP_END, PANEL_GAP_HEAD, STACKED, TIGHT_PAD, TOP_SHIFT)
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

MULTI_IMG_USERS = 3     # usuarios que Blender muestra en "Multiple Images.png" (el 3 junto al nombre)
IMG_LOADED_W = 257.0    # ancho por defecto de Multiple Images (el de tu captura)
# CURVING (style.py) = noodle_curving del tema (0 = cable recto, 10 = muy curvo); 5 es el valor de Blender
# nodos cuyos deslizadores van apilados sin hueco, con esquinas unidas (como en el PDF)

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
class NodeItem(NodePaintMixin, RampMixin, EditMixin, LayoutMixin, QGraphicsItem):
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
    def load_image(self, name, users=1, cs="", path=None):
        """Deja el nodo Image como en Blender cuando ya tiene una imagen cargada (p. ej. Multiple Images)."""
        self.img_loaded = {"name": name, "users": users, "path": path}
        lo, hi = self.width_limits()
        if self.spec["idname"].startswith("Compositor"):   # el Image Texture de Shader conserva su ancho
            self.w = max(lo, min(hi, IMG_LOADED_W))
        self.pvals.update({"_img_src": "FILE", "_img_cs": cs, "_img_alpha": "STRAIGHT"})
        self.relayout()

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
    # ---- ancho (arrastrar los bordes izquierdo/derecho, como en Blender)
    EDGE = 5.0
    _imgclk = None     # zona de la fila de imagen pulsada (se ejecuta al soltar)
    _sh_img = False    # True solo mientras se calcula el diseno de un Image Texture con imagen

    def width_limits(self):
        lo, hi = WIDTH_LIMITS.get(self.spec["idname"], (80.0, 700.0))
        return float(lo), float(hi)

    FIELD_KINDS = ("enum", "bool", "boolin", "num", "vec", "color", "str")


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
