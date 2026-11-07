"""Color Ramp interactivo de NodeItem (marcadores que se deslizan, menus, Pos, indice, muestra de color).
RampMixin se mezcla en NodeItem; el dibujo del ramp esta en node_paint.py (paint_block)."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import QMenu, QInputDialog, QColorDialog

from style import lin2s, s2lin
from ramp import RAMP_CMODES, RAMP_INTERPS, _new_ramp, ramp_eval
from metrics import PAD


class RampMixin:
    """Metodos _ramp_* de NodeItem: geometria, marcadores y eventos del Color Ramp."""

    def _ramp_geom(self):
        r = next((q for q in self.rows if q["k"] == "block" and q.get("kind") == "ramp"), None)
        if r is None:
            return None
        y, x, fw = r["y"], PAD, self.w - 2 * PAD
        mid = x + 156.0
        return dict(y=y, h=r["h"],
                    gr=QRectF(x + 5.0, y + 33.5, fw - 10.0, 18.5),
                    plus=QRectF(x, y + 8.0, 23.0, 20.0),
                    minus=QRectF(x + 24.0, y + 8.0, 23.0, 20.0),
                    tools=QRectF(x + 50.0, y + 8.0, 34.0, 20.0),
                    cmode=QRectF(x + 92.8, y + 8.0, mid - x - 92.8, 20.0),
                    interp=QRectF(mid, y + 8.0, x + fw - mid, 20.0),
                    idx=QRectF(x, y + 63.2, 63.0, 20.0),
                    pos=QRectF(x + 71.7, y + 63.2, fw - 71.7, 20.0),
                    swatch=QRectF(x, y + 88.0, fw, 20.0))

    def _ramp_markers(self, gr):
        """(x, color hex, activo) de cada marcador; el activo va al final para dibujarse encima."""
        rp, out = self.ramp, []
        for i, s in enumerate(rp["stops"]):
            c = s["color"]
            out.append((gr.left() + s["pos"] * gr.width(),
                        QColor.fromRgbF(lin2s(c[0]), lin2s(c[1]), lin2s(c[2])).name(), i == rp["active"]))
        out.sort(key=lambda m: m[2])
        return out

    def _ramp_resort(self, stop):
        rp = self.ramp
        rp["stops"].sort(key=lambda s: s["pos"])
        rp["active"] = next(i for i, s in enumerate(rp["stops"]) if s is stop)

    def _ramp_insert(self, t):
        rp = self.ramp
        if len(rp["stops"]) >= 32:
            return None
        s = {"pos": t, "color": ramp_eval(rp, t)}
        rp["stops"].append(s)
        self._ramp_resort(s)
        return s

    def _ramp_add(self):
        st, i = self.ramp["stops"], self.ramp["active"]
        if i < len(st) - 1:
            t = (st[i]["pos"] + st[i + 1]["pos"]) / 2
        elif i > 0:
            t = (st[i - 1]["pos"] + st[i]["pos"]) / 2
        else:
            t = st[0]["pos"] + (0.5 if st[0]["pos"] < 0.5 else -0.5)
        self._ramp_insert(t)

    def _ramp_remove(self):
        rp = self.ramp
        if len(rp["stops"]) > 1:
            rp["stops"].pop(rp["active"])
            rp["active"] = max(0, rp["active"] - 1)

    def _ramp_parent(self):
        return self.scene().views()[0] if self.scene() and self.scene().views() else None

    def _ramp_pick(self, names, cur):
        menu = QMenu(self._ramp_parent())
        for nm in names:
            a = menu.addAction(nm)
            if cur is not None:
                a.setCheckable(True)
                a.setChecked(nm == cur)
        act = menu.exec(QCursor.pos())
        return act.text() if act is not None else None

    def _ramp_click(self, what):
        rp = self.ramp
        if what == "cmode":
            ch = self._ramp_pick(RAMP_CMODES, rp["cmode"])
            if ch:
                rp["cmode"] = ch
        elif what == "interp":
            ch = self._ramp_pick(RAMP_INTERPS, rp["interp"])
            if ch:
                rp["interp"] = ch
        elif what == "tools":
            ch = self._ramp_pick(["Flip Color Ramp", "Distribute Stops Evenly", "Reset Color Ramp"], None)
            st = rp["stops"]
            act = st[rp["active"]]
            if ch == "Flip Color Ramp":
                for s in st:
                    s["pos"] = 1.0 - s["pos"]
                st.reverse()
                rp["active"] = next(i for i, s in enumerate(st) if s is act)
            elif ch == "Distribute Stops Evenly" and len(st) > 1:
                for i, s in enumerate(st):
                    s["pos"] = i / (len(st) - 1)
            elif ch == "Reset Color Ramp":
                rp["stops"], rp["active"] = _new_ramp()["stops"], 0
        elif what == "swatch":
            s = rp["stops"][rp["active"]]
            c = s["color"]
            q = QColorDialog.getColor(QColor.fromRgbF(lin2s(c[0]), lin2s(c[1]), lin2s(c[2])),
                                      self._ramp_parent(), "Color")
            if q.isValid():
                s["color"] = [s2lin(q.redF()), s2lin(q.greenF()), s2lin(q.blueF()), c[3] if len(c) > 3 else 1.0]

    def _ramp_select_node(self):
        sc = self.scene()
        if sc is not None and not self.isSelected():
            sc.clearSelection()
            self.setSelected(True)

    def _ramp_press(self, e):
        rp, g = self.ramp, self._ramp_geom()
        if rp is None or g is None:
            return False
        pos = e.pos()
        if not (g["y"] <= pos.y() < g["y"] + g["h"] and 0.0 <= pos.x() <= self.w):
            return False
        sx, gr, stops = e.screenPos().x(), g["gr"], rp["stops"]
        # marcadores y barra: clic = seleccionar y arrastrar; Ctrl+clic = crear uno nuevo ahi
        if gr.left() - 7 <= pos.x() <= gr.right() + 7 and gr.top() - 1 <= pos.y() <= gr.top() + 24:
            if e.modifiers() & Qt.ControlModifier:
                self._ramp_select_node()
                t = max(0.0, min(1.0, (pos.x() - gr.left()) / gr.width()))
                s = self._ramp_insert(t)
                if s is not None:
                    self._rm = dict(mode="drag", stop=s, off=0.0, sx=sx, moved=True)
                self.update()
                return True
            best = None
            for i, s in enumerate(stops):
                d = abs(gr.left() + s["pos"] * gr.width() - pos.x())
                if d <= 7 and (best is None or d < best[0] or (d == best[0] and i == rp["active"])):
                    best = (d, i)
            if best is None:
                return False
            self._ramp_select_node()
            rp["active"] = best[1]
            s = stops[best[1]]
            self._rm = dict(mode="drag", stop=s, off=pos.x() - (gr.left() + s["pos"] * gr.width()),
                            sx=sx, moved=False)
            self.update()
            return True
        if g["plus"].contains(pos):
            self._ramp_select_node()
            self._ramp_add()
            self.update()
            return True
        if g["minus"].contains(pos):
            self._ramp_select_node()
            self._ramp_remove()
            self.update()
            return True
        for key in ("tools", "cmode", "interp", "swatch"):
            if g[key].contains(pos):
                self._ramp_select_node()
                self._rm = dict(mode="click", what=key, sx=sx, moved=False)
                return True
        if g["idx"].contains(pos):
            self._ramp_select_node()
            self._rm = dict(mode="idx", i0=rp["active"], sx=sx, moved=False)
            return True
        if g["pos"].contains(pos):
            self._ramp_select_node()
            self._rm = dict(mode="pos", sx=sx, moved=False)
            return True
        return False

    def _ramp_move(self, e):
        rm, rp, g = self._rm, self.ramp, self._ramp_geom()
        if abs(e.screenPos().x() - rm["sx"]) >= 3:
            rm["moved"] = True
        if g is None:
            return
        if rm["mode"] == "drag":
            gr = g["gr"]
            t = (e.pos().x() - rm["off"] - gr.left()) / gr.width()
            rm["stop"]["pos"] = max(0.0, min(1.0, t))
            self._ramp_resort(rm["stop"])      # al cruzar a otro marcador se reordenan, como en Blender
            rm["moved"] = True
        elif rm["mode"] == "pos" and rm["moved"]:
            f = g["pos"]
            st = rp["stops"][rp["active"]]
            st["pos"] = max(0.0, min(1.0, (e.pos().x() - f.left()) / f.width()))
            self._ramp_resort(st)
        elif rm["mode"] == "idx" and rm["moved"]:
            n = len(rp["stops"])
            rp["active"] = max(0, min(n - 1, rm["i0"] + int((e.screenPos().x() - rm["sx"]) / 12)))
        self.update()

    def _ramp_release(self, e):
        rm, rp = self._rm, self.ramp
        self._rm = None
        if rm["mode"] == "click" and not rm["moved"]:
            self._ramp_click(rm["what"])
        elif rm["mode"] == "idx" and not rm["moved"]:
            n, ok = QInputDialog.getInt(self._ramp_parent(), "Valor", "Index", rp["active"], 0,
                                        len(rp["stops"]) - 1)
            if ok:
                rp["active"] = n
        elif rm["mode"] == "pos" and not rm["moved"]:
            st = rp["stops"][rp["active"]]
            n, ok = QInputDialog.getDouble(self._ramp_parent(), "Valor", "Pos", st["pos"], 0.0, 1.0, 4)
            if ok:
                st["pos"] = n
                self._ramp_resort(st)
        self.update()
