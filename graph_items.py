"""Items graficos simples del lienzo: sockets, cables y Reroute.
Leen los colores del tema como S.X (style.py), asi el cambio de tema les llega.
NodeItem y FrameItem siguen en main.py."""
import copy

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush, QPainterPath, QPainterPathStroker,
                           QLinearGradient)
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsEllipseItem

import style as S

# medidas en px a escala 1 (unidad de widget de Blender = 20 px)
SR = 5.0   # radio del socket
LINK_LINE_W = 1.0   # grosor del borde de los cables a cada lado del hilo (su color, LINK_LINE, esta en style.py)
BAR_W, BAR_H = 5.0, 11.5     # socket de "un solo valor" de Blender 5.x: barra vertical en vez de circulo
BAR_SHAPES = {"SQUARE"}      # valores de socket.display_shape (los exporta export_socket_shapes.py) que se dibujan como barra
# respaldo mientras el JSON no traiga "shape": nodo -> entradas que son barra (medido en capturas de Blender 5.2)
BAR_FALLBACK = {"CompositorNodeKuwahara": {"Type", "Uniformity", "Sharpness", "Eccentricity", "High Precision"},
                # Glare (captura de Blender): todas las entradas son barras salvo Image y Kernel
                "CompositorNodeGlare": {"Type", "Quality", "Threshold", "Smoothness", "Clamp", "Maximum", "Strength",
                                        "Saturation", "Tint", "Size", "Streaks", "Streaks Angle", "Iterations",
                                        "Fade", "Color Modulation", "Diagonal", "Sun Position", "Jitter",
                                        "Kernel Data Type"},
                # Lens Distortion (captura de Blender): todas las entradas son barras salvo Image
                "CompositorNodeLensdist": {"Type", "Distortion", "Dispersion", "Jitter", "Fit"},
                # Filter (captura de Blender): solo el menu Type es barra; Factor es circulo
                "CompositorNodeFilter": {"Type"},
                # Group Output/Input (captura de Blender): el item Image va como barra; el socket virtual, circulo
                "NodeGroupOutput": {"Image"}, "NodeGroupInput": {"Image"}}
SOCK_LINE_W = 1.0   # grosor del borde de los sockets (fino, como en Blender; su color, SOCK_LINE, esta en style.py)
LINK_W = 3.5   # grosor del hilo del cable (antes 2.2); sube o baja este valor para ajustarlo


# ------------------------------------------------------------------ items
class SocketItem(QGraphicsEllipseItem):
    def __init__(self, node, spec, is_out):
        super().__init__(-SR, -SR, 2 * SR, 2 * SR, node)
        self.node, self.spec, self.is_out = node, spec, is_out
        self.setBrush(QBrush(QColor(S.SOCK.get(spec.get("stype"), "#a1a1a1"))))
        self.setPen(QPen(QColor(S.SOCK_LINE), SOCK_LINE_W))
        self.setZValue(2)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(Qt.CrossCursor)

    def is_bar(self):
        """True si Blender dibuja este socket como barra vertical (solo acepta un valor, no una imagen)."""
        sh = self.spec.get("shape")
        if sh is not None:
            return sh in BAR_SHAPES
        return self.spec.get("name") in BAR_FALLBACK.get(self.node.spec["idname"], ())

    def paint(self, p, opt, widget=None):
        if self.is_bar():
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(self.pen())
            p.setBrush(self.brush())
            p.drawRoundedRect(QRectF(-BAR_W / 2, -BAR_H / 2, BAR_W, BAR_H), 1.3, 1.3)
        else:
            super().paint(p, opt, widget)

    HIT = 8.0   # area de clic mas grande que el circulo dibujado (como en Blender)

    def boundingRect(self):
        h = SocketItem.HIT + 1
        return QRectF(-h, -h, 2 * h, 2 * h)

    def shape(self):
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), SocketItem.HIT, SocketItem.HIT)
        return path

    def mousePressEvent(self, e):
        self.scene().drag_begin(self, e.scenePos())
        e.accept()

    def mouseMoveEvent(self, e):
        self.scene().drag_update(e.scenePos())

    def mouseReleaseEvent(self, e):
        sc = self.scene()
        sc.drag_end(sc.drag_src or self, e.scenePos())
        sc.drag_src = None


class LinkItem(QGraphicsPathItem):
    def __init__(self, a, b):
        super().__init__()
        self.a, self.b, self.end = a, b, None
        pen = QPen(S.WIRE, LINK_W)
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)
        self.setZValue(0)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def gradient(self):
        """Color del cable segun el tipo de socket (como 'Wire Colors' de Blender)."""
        ca = QColor(S.SOCK.get(self.a.spec.get("stype"), "#a1a1a1"))
        cb = QColor(S.SOCK.get(self.b.spec.get("stype"), "#a1a1a1")) if self.b is not None else ca
        pa = self.a.scenePos()
        pb = self.b.scenePos() if self.b is not None else (self.end or pa)
        g = QLinearGradient(pa, pb)
        g.setColorAt(0, ca)
        g.setColorAt(1, cb)
        return g

    def boundingRect(self):
        m = LINK_LINE_W + 1
        return super().boundingRect().adjusted(-m, -m, m, m)   # espacio para el borde

    def update_path(self):
        pa = self.a.scenePos()
        pb = self.b.scenePos() if self.b is not None else (self.end or pa)
        if self.b is None and not self.a.is_out:
            pa, pb = pb, pa
        d = max(abs(pb.x() - pa.x()) * S.CURVING * 0.1, S.CURVING * 8.0)
        path = QPainterPath(pa)
        path.cubicTo(QPointF(pa.x() + d, pa.y()), QPointF(pb.x() - d, pb.y()), pb)
        self.setPath(path)

    def shape(self):
        s = QPainterPathStroker()
        s.setWidth(10)
        return s.createStroke(self.path())

    def paint(self, p, opt, widget=None):
        pen = QPen(self.pen())
        if self.isSelected():
            pen.setColor(S.WIRE_SEL)
        else:
            pen.setBrush(QBrush(self.gradient()))
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        border = QPen(QColor(S.LINK_LINE), pen.widthF() + 2 * LINK_LINE_W)
        border.setCapStyle(Qt.RoundCap)
        p.setPen(border)
        p.drawPath(self.path())     # primero el borde oscuro, luego el hilo encima
        p.setPen(pen)
        p.drawPath(self.path())


class RerouteSocket(SocketItem):
    """Socket de un Reroute: la mitad izquierda del punto es la entrada y la derecha la salida.
    El punto lo dibuja el propio Reroute."""

    def shape(self):
        path = QPainterPath()
        h = SocketItem.HIT
        path.addRect(QRectF(0 if self.is_out else -h, -h, h, 2 * h))
        return path

    def paint(self, p, opt, widget=None):
        pass

    def mousePressEvent(self, e):
        if e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
            e.ignore()      # Ctrl/Mayus + arrastrar mueve el Reroute en vez de sacar un cable
            return
        super().mousePressEvent(e)


class RerouteItem(QGraphicsItem):
    """Punto de paso de un cable (Reroute). Toma el color del tipo de socket al que se conecta."""
    R = 5.5
    is_reroute = True

    def __init__(self, spec, cat=None):
        super().__init__()
        self.spec = copy.deepcopy(spec)
        self.cat = None
        self.w = self.h = 2 * self.R
        self.vals, self.pvals = {}, {}
        self.lin_in, self.lin_out = set(), set()
        self.hide_unused = False
        self.rows = []
        self.eff = None          # tipo efectivo (None = sin conectar)
        self.socks = {("in", "Input"): RerouteSocket(self, self.spec["inputs"][0], False),
                      ("out", "Output"): RerouteSocket(self, self.spec["outputs"][0], True)}
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(1)

    def relayout(self):
        pass

    def update_type(self, links):
        si, so = self.socks[("in", "Input")], self.socks[("out", "Output")]
        t = next((l.a.spec.get("stype") for l in links if l.b is si), None)
        if t is None:
            t = next((l.b.spec.get("stype") for l in links if l.a is so and l.b is not None), None)
        self.eff = t
        si.spec["stype"] = so.spec["stype"] = t or "VALUE"

    def boundingRect(self):
        m = self.R + 4
        return QRectF(-m, -m, 2 * m, 2 * m)

    def shape(self):
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), self.R + 2, self.R + 2)
        return path

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene() is not None:
            for l in self.scene().links:
                if l.a.node is self or l.b.node is self:
                    l.update_path()
        return super().itemChange(change, value)

    def paint(self, p, opt, widget=None):
        p.setRenderHint(QPainter.Antialiasing)
        if self.isSelected():
            p.setPen(QPen(S.SEL, 2.0))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(0, 0), self.R + 2.5, self.R + 2.5)
        p.setPen(QPen(QColor(S.SOCK_LINE), SOCK_LINE_W))
        p.setBrush(QBrush(QColor(S.SOCK.get(self.eff or "VALUE", "#a1a1a1"))))
        p.drawEllipse(QPointF(0, 0), self.R, self.R)
