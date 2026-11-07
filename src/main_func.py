"""Nodo Capture funcional: parchea main.py (sin modificarlo) para que los nodos calculen.

Ejecuta este archivo en vez de main.py:  python main_func.py

Que anade:
  - Los enlaces ahora cuentan: el valor de cada salida se calcula con evaluator.py y se
    muestra junto al nombre de la salida (boton "Mostrar resultados", Ctrl+R, para apagarlo
    antes de sacar capturas limpias).
  - El nodo Value tiene su campo numerico editable (arrastrar o clic) y el nodo RGB abre el
    selector de color al hacer clic en la rueda / muestra.
  - Conexiones validas: no se puede unir un Shader con un valor/color/vector ni crear ciclos.
"""
import sys

from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import QApplication, QColorDialog, QToolBar

import main as M
import evaluator as EV

STATE = {"show": True}
VALUE_IDS = {"ShaderNodeValue", "CompositorNodeValue"}
RGB_IDS = {"ShaderNodeRGB", "CompositorNodeRGB"}
NO_RESULT = VALUE_IDS | RGB_IDS      # estos ya muestran su propio widget

# la rueda de color tambien en el compositor
M.BLOCKS.setdefault("CompositorNodeRGB", ("wheel", 98))
M.EXTRA_H.setdefault("CompositorNodeRGB", 1.8)


# ------------------------------------------------------------ escena: calculo
def recompute(self):
    nodes = self.nodes()
    links = [(l.a.node, l.a.spec["identifier"], l.b.node, l.b.spec["identifier"])
             for l in self.links if l.b is not None]
    res = EV.evaluate(nodes, links)
    for n in nodes:
        n.results = res.get(n, {})
    self.update()


_orig_sync = M.NodeScene.sync


def sync(self):
    _orig_sync(self)
    self.recompute()


def _reaches(self, start, goal):
    """True si desde `start` se llega a `goal` siguiendo los enlaces hacia adelante."""
    seen, stack = set(), [start]
    while stack:
        cur = stack.pop()
        if cur is goal:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(l.b.node for l in self.links if l.a.node is cur and l.b is not None)
    return False


_orig_connect = M.NodeScene.connect_socks


def connect_socks(self, o, i):
    if (o.spec.get("stype") == "SHADER") != (i.spec.get("stype") == "SHADER"):
        return                               # Shader solo con Shader
    if self._reaches(i.node, o.node):
        return                               # evita ciclos
    _orig_connect(self, o, i)


M.NodeScene.recompute = recompute
M.NodeScene.sync = sync
M.NodeScene._reaches = _reaches
M.NodeScene.connect_socks = connect_socks


# ---- Reroute: el calculo y la validacion atraviesan los puntos de paso
def _src_of(self, sock):
    """Sube por los Reroute hasta el socket de salida real (None si queda sin conectar)."""
    seen = set()
    while sock is not None and getattr(sock.node, "is_reroute", False):
        if sock.node in seen:
            return None
        seen.add(sock.node)
        si = sock.node.socks[("in", "Input")]
        sock = next((l.a for l in self.links if l.b is si), None)
    return sock


def recompute_rr(self):
    nodes = self.nodes()
    links = []
    for l in self.links:
        if l.b is None or getattr(l.b.node, "is_reroute", False):
            continue
        a = self._src_of(l.a)
        if a is not None:
            links.append((a.node, a.spec["identifier"], l.b.node, l.b.spec["identifier"]))
    res = EV.evaluate(nodes, links)
    for n in nodes:
        n.results = res.get(n, {})
    self.update()


def _eff(sock):
    """Tipo efectivo de un socket; un Reroute sin conectar acepta cualquier tipo (None)."""
    n = sock.node
    return n.eff if getattr(n, "is_reroute", False) else sock.spec.get("stype")


def connect_socks_rr(self, o, i):
    a, b = _eff(o), _eff(i)
    if a is not None and b is not None and (a == "SHADER") != (b == "SHADER"):
        return                               # Shader solo con Shader
    if self._reaches(i.node, o.node):
        return                               # evita ciclos
    _orig_connect(self, o, i)


M.NodeScene._src_of = _src_of
M.NodeScene.recompute = recompute_rr
M.NodeScene.connect_socks = connect_socks_rr


# ------------------------------------------------------------ nodos
_orig_relayout = M.NodeItem.relayout


def relayout(self):
    idn = self.spec["idname"]
    is_val = idn in VALUE_IDS
    oid = None
    if is_val:
        o = self.spec["outputs"][0]
        oid = o["identifier"]
        if oid not in self.vals:
            d = o.get("default")
            self.vals[oid] = float(d) if isinstance(d, (int, float)) else 0.0
    _orig_relayout(self)
    if is_val:
        y = max((r["y"] + r["h"] for r in self.rows), default=M.HEADER) + 1
        self.rows.append(dict(k="num", y=y, h=M.FH, name="", ref=("v", oid), st="VALUE",
                              fac=False, lo=None, hi=None, unit=None, center=True))
        self.h = y + M.FH + 5
        self.update()


_orig_paint_row = M.NodeItem.paint_row


def paint_row(self, p, r):
    if r["k"] == "num" and r.get("center"):
        rect = QRectF(M.PAD, r["y"], self.w - 2 * M.PAD, r["h"])
        path = self.field(p, rect, M.FIELD)
        self.outline(p, path)
        p.setPen(M.TXT)
        p.drawText(rect, Qt.AlignCenter, M.fmt_unit(self.get(r), r))
        return
    _orig_paint_row(self, p, r)


def _fmt_result(v):
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, (list, tuple)):
        return " ".join(f"{x:.2f}" for x in v[:3])
    return str(v)


_orig_paint = M.NodeItem.paint


def paint(self, p, opt, widget=None):
    _orig_paint(self, p, opt, widget)
    res = getattr(self, "results", None)
    if not STATE["show"] or not res or self.spec["idname"] in NO_RESULT:
        return
    outs = [s for s in self.spec["outputs"] if self._visible(s, self.lin_out)]
    used = set()
    p.save()
    p.setFont(M.NodeItem.F)
    for r in self.rows:
        if r["k"] != "out":
            continue
        s = next((s for s in outs if s["name"] == r["name"] and s["identifier"] not in used), None)
        if s is None:
            continue
        used.add(s["identifier"])
        v = res.get(s["identifier"])
        if v is None:
            continue
        rect = QRectF(M.PAD, r["y"], self.w - 2 * M.PAD, r["h"])
        if isinstance(v, (list, tuple)) and len(v) == 4 and s.get("stype") == "RGBA":
            c = QColor.fromRgbF(M.lin2s(v[0]), M.lin2s(v[1]), M.lin2s(v[2]))
            sw = QRectF(rect.x(), rect.y() + 4, 26, rect.height() - 8)
            path = self.field(p, sw, c)
            self.outline(p, path)
        else:
            p.setPen(QColor("#8fb8ff"))
            p.drawText(rect.adjusted(0, 0, -rect.width() * 0.45, 0), M.AL, _fmt_result(v))
    p.restore()


_orig_drag = M.NodeItem._drag_num


def _drag_num(self, ed, e, dx):
    _orig_drag(self, ed, e, dx)
    if self.scene() is not None:
        self.scene().recompute()


_orig_press = M.NodeItem.mousePressEvent


def mousePressEvent(self, e):
    if e.button() == Qt.LeftButton and self.spec["idname"] in RGB_IDS and self.scene() is not None:
        blk = next((r for r in self.rows if r["k"] == "block"), None)
        pos = e.pos()
        if blk and blk["y"] <= pos.y() < blk["y"] + blk["h"] and M.PAD <= pos.x() <= self.w - M.PAD:
            if not self.isSelected():
                self.scene().clearSelection()
                self.setSelected(True)
            QTimer.singleShot(0, self.pick_color)
            e.accept()
            return
    _orig_press(self, e)


def pick_color(self):
    sc = self.scene()
    if sc is None:
        return
    o = self.spec["outputs"][0]
    d = o.get("default")
    if not (isinstance(d, list) and len(d) >= 3):
        d = [0.8, 0.8, 0.8, 1.0]
    parent = sc.views()[0] if sc.views() else None
    c = QColorDialog.getColor(QColor.fromRgbF(M.lin2s(d[0]), M.lin2s(d[1]), M.lin2s(d[2])), parent, "Color")
    if c.isValid():
        o["default"] = [M.s2lin(c.redF()), M.s2lin(c.greenF()), M.s2lin(c.blueF()),
                        d[3] if len(d) > 3 else 1.0]
        sc.sync()


M.NodeItem.relayout = relayout
M.NodeItem.paint_row = paint_row
M.NodeItem.paint = paint
M.NodeItem._drag_num = _drag_num
M.NodeItem.mousePressEvent = mousePressEvent
M.NodeItem.pick_color = pick_color


# ------------------------------------------------------------ ventana
_orig_add_node = M.Window.add_node


def add_node(self):
    _orig_add_node(self)
    self.cur.sync()


M.Window.add_node = add_node


def main():
    app = QApplication(sys.argv)
    M.apply_dark(app)
    w = M.Window()
    tb = w.findChildren(QToolBar)[0]
    act = QAction("Mostrar resultados", w)
    act.setCheckable(True)
    act.setChecked(True)
    act.setShortcut("Ctrl+R")
    act.setToolTip("Mostrar resultados (Ctrl+R)")

    def toggle(on):
        STATE["show"] = bool(on)
        for sc in w.scenes.values():
            sc.update()

    act.toggled.connect(toggle)
    tb.insertAction(tb.actions()[3], act) if len(tb.actions()) > 3 else tb.addAction(act)
    w.addAction(act)
    import themes
    themes.install(w)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
