"""Iconos vectoriales de Nodo Capture (carpeta, imagen, objeto, cuentagotas, UV, escena, view layer).

Cada draw_*_icon(p, rect, color) dibuja el icono en el QPainter p, dentro de rect y del color dado.
Los iconos SVG se cachean por color.
"""
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtSvg import QSvgRenderer


_FOLDER_D1 = ("m 1349.3299,859.095 h -257.2746 c -6.1776,0 -12.2083,-1.721 -17.2846,-4.932 l -10.5205,-32.39424 "
              "c -5.0773,-3.211 -11.1081,-4.9066 -17.2858,-4.932 L 854.69997,816.046 c -16.7573,-0.0689 -30.3434,12.396 "
              "-30.3434,27.687 v 83.735 h 555.31573 v -40.687 c 0,-15.29 -13.5849,-27.686 -30.3424,-27.686 z")
_FOLDER_D2 = ("m 1333.778,1290 -487.82453,1.3499 c -18.03793,0.05 -32.958,-13.4311 -34.047,-30.6491 L 816.498,990.44461 "
              "c -1.186,-18.75479 14.399,-34.58715 34.047,-34.58715 h 500.239 c 19.648,0 35.233,15.83236 34.047,34.58715 "
              "l -17.007,268.90629 c -1.089,17.218 -16.0081,30.5992 -34.046,30.6491 z")
_ICON_CACHE = {}


def draw_folder_icon(p, rect, color):
    """Icono de carpeta (tu folder.svg, viewBox 640x640), vectorial y del color dado."""
    c = QColor(color).name()
    r = _ICON_CACHE.get(c)
    if r is None:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640">'
               '<g transform="translate(-778.41648,-712.75182)" fill="%s">'
               '<path d="%s"/><path d="%s"/></g></svg>') % (c, _FOLDER_D1, _FOLDER_D2)
        r = _ICON_CACHE[c] = QSvgRenderer(svg.encode("utf-8"))
    r.render(p, QRectF(rect))


def draw_image_icon(p, rect, color):
    """Icono 'Empty Image' (tu SVG, viewBox 640x640) dibujado con trazos vectoriales del color dado."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(rect.x(), rect.y())
    s = min(rect.width(), rect.height()) / 640.0
    p.scale(s, s)
    c = QColor(color)
    pen = QPen(c, 64.5207, Qt.SolidLine, Qt.RoundCap, Qt.MiterJoin)    # montana
    pen.setMiterLimit(20)
    p.setPen(pen)
    p.setBrush(c)
    p.drawPolygon(QPolygonF([QPointF(93.0315, 567.7364), QPointF(221.8555, 344.6067),
                             QPointF(349.4812, 565.6609)]))
    p.setPen(QPen(c, 62.4615, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))   # sol
    p.drawEllipse(QPointF(421.1183, 218.8413), 31.2883, 31.2883)
    pen = QPen(c, 48.0485, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)      # marco abierto
    pen.setMiterLimit(20)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawPolyline(QPolygonF([QPointF(61.4552, 425.9284), QPointF(61.4552, 59.0979),
                              QPointF(585.7934, 59.0979), QPointF(585.7934, 574.6404),
                              QPointF(451.4899, 574.6404)]))
    p.restore()


_OBJ_ICON_CACHE = {}


def draw_object_icon(p, rect, color):
    """Icono de objeto (tu cuadrado.svg, viewBox 500x500): cuadrado central relleno y cuatro esquinas, vectorial y del color dado."""
    c = QColor(color).name()
    r = _OBJ_ICON_CACHE.get(c)
    if r is None:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">'
               '<path d="M133.458 116.727 L366.542 116.727 C375.782 116.727 383.273 124.218 383.273 133.458 '
               'L383.273 366.542 C383.273 375.782 375.782 383.273 366.542 383.273 L133.458 383.273 '
               'C124.218 383.273 116.727 375.782 116.727 366.542 L116.727 133.458 '
               'C116.727 124.218 124.218 116.727 133.458 116.727 Z" fill="%(c)s" stroke="%(c)s" stroke-miterlimit="10"/>'
               '<g fill="none" stroke="%(c)s" stroke-width="45" stroke-linecap="round" stroke-linejoin="round" opacity="0.75">'
               '<path d="M359.004 43.432 L458.463 43.432 L458.463 141.34"/>'
               '<path d="M141.954 43.432 L42.494 43.432 L42.494 141.34"/>'
               '<path d="M359.004 455.5 L458.463 455.5 L458.463 357.592"/>'
               '<path d="M141.954 455.5 L42.494 455.5 L42.494 357.592"/>'
               '</g></svg>') % {"c": c}
        r = _OBJ_ICON_CACHE[c] = QSvgRenderer(svg.encode("utf-8"))
    r.render(p, QRectF(rect))


_DROPPER_ICON_CACHE = {}


def draw_dropper_icon(p, rect, color):
    """Icono de cuentagotas (tu drop.svg, viewBox 500x500), vectorial y del color dado."""
    c = QColor(color).name()
    r = _DROPPER_ICON_CACHE.get(c)
    if r is None:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">'
               '<g fill="none" stroke="%(c)s" stroke-width="30" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="M202.628 120.346 L377.06 294.777"/>'
               '<path d="M250 180.999 L118.759 311.269 L109.017 358.274 L58.175 408.051"/>'
               '<path d="M313.155 239.994 L182.884 371.235 L135.879 380.977 L86.102 431.819"/>'
               '</g>'
               '<path d="M337.743 243.28 L405.04 177.379 C441.119 145.071 452.09 97.205 426.465 68.244 '
               'C402.655 41.334 351.39 51.312 315.528 87.173 L246.902 151.258" '
               'fill="%(c)s" stroke="%(c)s" stroke-width="30" stroke-miterlimit="10"/>'
               '</svg>') % {"c": c}
        r = _DROPPER_ICON_CACHE[c] = QSvgRenderer(svg.encode("utf-8"))
    r.render(p, QRectF(rect))


_UV_ICON_CACHE = {}


def draw_uv_icon(p, rect, color):
    """Icono de UV Map (tu SVG, viewBox 500x500), vectorial y del color dado."""
    c = QColor(color).name()
    r = _UV_ICON_CACHE.get(c)
    if r is None:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">'
               '<g fill="none" stroke="%(c)s" stroke-width="26" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="M364.668 42.015 L462.875 42.015 L462.875 140.222 L364.668 140.222 Z"/>'
               '<path d="M364.668 321.854 L462.875 321.854 L462.875 420.06 L364.668 420.06 Z"/>'
               '<path d="M413.771 133.124 L413.771 329.306" stroke-linecap="butt" stroke-linejoin="miter" stroke-miterlimit="10"/>'
               '<path d="M227.794 382.8 L363.991 382.8"/>'
               '<path d="M362.991 80.481 L87.489 80.481 C64.415 80.481 45.709 99.187 45.709 122.262 L45.709 122.262 '
               'C45.709 145.336 64.415 164.042 87.489 164.042 L182.991 164.042 L182.991 448.716 L87.489 448.716 '
               'C64.415 448.716 45.709 430.011 45.709 406.936 L45.709 406.936 L45.745 120.524"/>'
               '</g>'
               '<path fill="%(c)s" d="M45.709 406.936 L45.744 123.989 C46.65 146.262 64.993 164.042 87.489 164.042 '
               'L182.991 164.042 L182.991 448.716 L87.489 448.716 C64.415 448.716 45.709 430.011 45.709 406.936 Z"/>'
               '</svg>') % {"c": c}
        r = _UV_ICON_CACHE[c] = QSvgRenderer(svg.encode("utf-8"))
    r.render(p, QRectF(rect))


_SCENE_ICON_CACHE = {}


def draw_scene_icon(p, rect, color):
    """Icono 'Scene' de Blender (tu SVG, viewBox 500x500), vectorial y del color dado."""
    c = QColor(color).name()
    r = _SCENE_ICON_CACHE.get(c)
    if r is None:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">'
               '<path d="M230.551 342.382 C230.551 285.583 276.596 239.538 333.395 239.538 '
               'C390.194 239.538 436.239 285.583 436.239 342.382 C436.239 399.181 390.194 445.225 333.395 445.225 '
               'C276.596 445.225 230.551 399.181 230.551 342.382 Z" '
               'fill="none" stroke="%(c)s" stroke-width="32" stroke-miterlimit="10"/>'
               '<path d="M342.839 113.025 C342.839 87.233 363.747 66.325 389.539 66.325 '
               'C415.331 66.325 436.239 87.233 436.239 113.025 C436.239 138.817 415.331 159.725 389.539 159.725 '
               'C363.747 159.725 342.839 138.817 342.839 113.025 Z" '
               'fill="%(c)s" stroke="%(c)s" stroke-width="34" stroke-miterlimit="10"/>'
               '<path d="M324.177 294.48 C324.177 294.48 294.701 297.896 288.07 330.587" '
               'fill="%(c)s" stroke="%(c)s" stroke-width="29" stroke-linecap="round" stroke-linejoin="round"/>'
               '<path d="M52.258 330.587 L174.538 61.737 L260.815 204.709 L266.075 213.138 '
               'C215.906 233.522 180.532 282.747 180.532 340.235 C180.532 360.433 183.192 378.853 192.74 395.877 '
               'C190.125 396.594 183.999 398.133 174.384 398.487 C82.832 401.866 52.258 330.587 52.258 330.587 Z" '
               'fill="%(c)s" stroke="%(c)s" stroke-width="32" stroke-linecap="round" stroke-linejoin="round"/>'
               '</svg>') % {"c": c}
        r = _SCENE_ICON_CACHE[c] = QSvgRenderer(svg.encode("utf-8"))
    r.render(p, QRectF(rect))


_LAYERS_ICON_CACHE = {}


def draw_layers_icon(p, rect, color):
    """Icono de View Layer (tu SVG, viewBox 500x500), vectorial y del color dado."""
    c = QColor(color).name()
    r = _LAYERS_ICON_CACHE.get(c)
    if r is None:
        dot = ('<path d="M%(x0)s 219.071 C%(x0)s 217.533 %(a)s 216.287 %(x1)s 216.287 '
               'C%(b)s 216.287 %(x2)s 217.533 %(x2)s 219.071 C%(x2)s 220.609 %(b)s 221.855 %(x1)s 221.855 '
               'C%(a)s 221.855 %(x0)s 220.609 %(x0)s 219.071 Z" '
               'fill="%(c)s" stroke="%(c)s" stroke-width="26" stroke-miterlimit="10"/>')
        dots = "".join(dot % {"x0": x0, "a": a, "x1": x1, "b": b, "x2": x2, "c": c} for x0, a, x1, b, x2 in (
            ("207.505", "208.751", "210.289", "211.826", "213.073"),
            ("261.223", "262.469", "264.007", "265.544", "266.791"),
            ("318.605", "319.851", "321.389", "322.926", "324.173"),
            ("370.742", "371.989", "373.526", "375.064", "376.31")))
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">'
               '<path d="M130.585 66.361 L213.789 66.361" fill="%(c)s" stroke="%(c)s" stroke-width="30" '
               'stroke-linecap="round" stroke-linejoin="round"/>'
               '<g fill="none" stroke="%(c)s" stroke-width="28" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="M269.933 430.315 L78.902 430.315 L78.902 119.941 L261.743 119.941 L261.743 175.008 '
               'L416.36 175.008 L416.36 261.776 L389.817 288.318 L340.999 288.318 L340.999 373.267 L206.505 373.267"/>'
               '<path d="M88.307 175.178 L264.007 175.178"/>'
               '</g>'
               '<path d="M82.414 182.959 L168.447 182.959 L168.447 372.87 L82.414 372.87 Z" fill="%(c)s" '
               'stroke="%(c)s" stroke-width="26" stroke-linecap="round" stroke-linejoin="round"/>'
               ) % {"c": c} + dots + '</svg>'
        r = _LAYERS_ICON_CACHE[c] = QSvgRenderer(svg.encode("utf-8"))
    r.render(p, QRectF(rect))
