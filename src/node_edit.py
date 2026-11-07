"""Interaccion de NodeItem: ancho por los bordes, clic y arrastre en campos, menus, dialogos y la fila de
imagen. EditMixin se mezcla en NodeItem."""
import math
from PySide6.QtCore import (Qt)
from PySide6.QtGui import (QColor, QCursor)
from PySide6.QtWidgets import (QColorDialog, QFileDialog, QInputDialog, QMenu)
from metrics import (IMAGES, IMG_TOP, PAD)
from pathlib import (Path)
from style import (lin2s, s2lin)


class EditMixin:
    """Eventos de raton y edicion de valores de NodeItem."""

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

    def _panel_at(self, pos):
        for r in self.rows:
            if r["k"] == "panel" and r["y"] <= pos.y() < r["y"] + r["h"] and 0 <= pos.x() <= self.w:
                return r
        return None

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
