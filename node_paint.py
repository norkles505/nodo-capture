"""Dibujo de los nodos (cuerpo, filas, campos, bloques, selector de imagen). NodePaintMixin se mezcla
en NodeItem, que conserva el estado, el layout y la interaccion. Lee los colores como S.X (style.py)."""
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush, QPainterPath, QPolygonF, QConicalGradient,
                           QRadialGradient, QLinearGradient)

import style as S
from style import lin2s
from icons import (draw_folder_icon, draw_image_icon, draw_object_icon, draw_dropper_icon,
                   draw_uv_icon, draw_scene_icon, draw_layers_icon)
from ramp import ramp_eval, ramp_samples
from metrics import (HEADER, PAD, R, NODE_LINE_W, FIELD_LINE_W, IMG_TOP, NUM_PAD_L, NUM_PAD_R,
                     AL, AR, fmt_unit)
from node_tables import PREVIEW_ICON


class NodePaintMixin:
    """Metodos de dibujo de NodeItem. Usa self.F (la fuente de clase de NodeItem)."""

    def field(self, p, rect, fill, jt=False, jb=False):
        path = QPainterPath()
        self._rr(path, rect, jt, jb)
        p.fillPath(path, fill)
        return path

    @staticmethod
    def _rr(path, rect, jt=False, jb=False):
        """Rectangulo redondeado; jt/jb = esquinas superiores/inferiores rectas (campo apilado)."""
        if not (jt or jb):
            path.addRoundedRect(rect, S.RAD, S.RAD)
            return
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        rt = 0.0 if jt else S.RAD
        rb = 0.0 if jb else S.RAD
        path.moveTo(x + rt, y)
        path.lineTo(x + w - rt, y)
        if rt:
            path.arcTo(QRectF(x + w - 2 * rt, y, 2 * rt, 2 * rt), 90, -90)
        else:
            path.lineTo(x + w, y)
        path.lineTo(x + w, y + h - rb)
        if rb:
            path.arcTo(QRectF(x + w - 2 * rb, y + h - 2 * rb, 2 * rb, 2 * rb), 0, -90)
        else:
            path.lineTo(x + w, y + h)
        path.lineTo(x + rb, y + h)
        if rb:
            path.arcTo(QRectF(x, y + h - 2 * rb, 2 * rb, 2 * rb), 270, -90)
        else:
            path.lineTo(x, y + h)
        path.lineTo(x, y + rt)
        if rt:
            path.arcTo(QRectF(x, y, 2 * rt, 2 * rt), 180, -90)
        else:
            path.lineTo(x, y)
        path.closeSubpath()

    def outline(self, p, path):
        p.setPen(QPen(S.FIELD_LINE, FIELD_LINE_W))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    def _outline_legacy(self, p, path):
        p.setPen(QPen(S.FIELD_LINE, 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    def paint(self, p, opt, widget=None):
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        k = 0.55 if S.BODY.lightness() > 128 else 1.0   # sombra suave bajo el nodo (mas tenue en temas claros)
        for i, a in ((4, 10), (3, 14), (2, 18), (1, 22)):
            sh = QPainterPath()
            sh.addRoundedRect(QRectF(-i + 0.5, -i + 2.5, self.w + 2 * i - 1, self.h + 2 * i - 1), R + i, R + i)
            p.fillPath(sh, QColor(0, 0, 0, int(a * k)))
        body = QPainterPath()
        body.addRoundedRect(QRectF(0, 0, self.w, self.h), R, R)
        p.fillPath(body, S.BODY)
        p.save()
        p.setClipPath(body)
        p.fillRect(QRectF(0, 0, self.w, HEADER), S.HEAD[self._cat()])
        p.restore()
        sel = self.isSelected()
        p.setPen(QPen(S.SEL if sel else S.OUTLINE, 2.0 if sel else NODE_LINE_W))
        p.setBrush(Qt.NoBrush)
        p.drawPath(body)
        p.setFont(self.F)
        hc = S.HEAD[self._cat()]
        tcol = S.TITLE   # Blender: titulo claro sobre cabeceras oscuras
        p.setPen(tcol)
        tx = 24.5 if self.img_loaded is not None else 26.0   # Blender: el titulo arranca a ~24.5 u
        p.drawText(QRectF(tx, 0, self.w - tx - (26.0 if self.img_loaded is not None else 8.0), HEADER), AL, self.title())
        p.setBrush(QColor("#d9d9d9"))
        p.setPen(Qt.NoPen)
        p.setPen(QPen(tcol, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))   # "v" fina como en Blender
        dx = 3.5 if self.img_loaded is not None else 0.0
        p.drawPolyline(QPolygonF([QPointF(8.5 + dx, 8.2), QPointF(12 + dx, 11.8), QPointF(15.5 + dx, 8.2)]))
        if self.spec["idname"] in PREVIEW_ICON:   # ojo cerrado (vista previa apagada) a la derecha de la cabecera
            ex, ey = self.w - 16.0, HEADER / 2
            lid = QPainterPath()
            lid.moveTo(ex - 6.0, ey - 1.6)
            lid.quadTo(ex, ey + 6.0, ex + 6.0, ey - 1.6)
            p.setPen(QPen(tcol, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(lid)
        if self.spec["idname"] == "CompositorNodeViewer":   # icono de monitor (Viewer) a la derecha de la cabecera
            ex, ey = self.w - 16.0, HEADER / 2
            p.setPen(QPen(tcol, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(ex - 6.5, ey - 5.5, 13.0, 9.0), 1.6, 1.6)   # pantalla
            p.drawLine(QPointF(ex, ey + 3.5), QPointF(ex, ey + 5.6))             # pie
            p.drawLine(QPointF(ex - 3.2, ey + 5.8), QPointF(ex + 3.2, ey + 5.8))  # base
        if self.img_loaded is not None and self.spec["idname"].startswith("Compositor"):   # icono del ojo (vista previa) a la derecha de la cabecera
            ex, ey = self.w - 16.0, HEADER / 2
            eye = QPainterPath()
            eye.moveTo(ex - 5.8, ey)
            eye.quadTo(ex, ey - 6.4, ex + 5.8, ey)
            eye.quadTo(ex, ey + 6.4, ex - 5.8, ey)
            p.setPen(QPen(tcol, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(eye)
            p.setPen(Qt.NoPen)
            p.setBrush(tcol)
            p.drawEllipse(QPointF(ex, ey), 2.5, 2.5)
        for r in self.rows:
            if r.get("dim") and r["k"] != "color":
                p.save()
                p.setOpacity(0.45)     # entrada que no influye en el resultado: Blender la atenua
                self.paint_row(p, r)
                p.restore()
            else:
                self.paint_row(p, r)

    def paint_row(self, p, r):
        k, y, h = r["k"], r["y"], r["h"]
        fw = self.w - 2 * PAD
        if k == "block":
            self.paint_block(p, r)
            return
        if k == "imgloaded":
            self.paint_imgloaded(p, r)
            return
        p.setPen(S.TXT)
        if k == "out":
            p.drawText(QRectF(PAD, y, fw, h), AR, r["name"])
            return
        if k == "io":
            p.drawText(QRectF(PAD, y, fw, h), AL, r["inname"])
            p.drawText(QRectF(PAD, y, fw, h), AR, r["outname"])
            return
        if k == "label":
            p.drawText(QRectF(PAD, y, fw, h), AL, r["name"])
            return
        if k == "warn":
            cx, cy = PAD + 7, y + h / 2
            p.setBrush(QColor("#e0b000"))
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF([QPointF(cx, cy - 6), QPointF(cx + 6.5, cy + 5), QPointF(cx - 6.5, cy + 5)]))
            p.setPen(S.TXT)
            p.drawText(QRectF(PAD + 20, y, fw - 20, h), AL, r["name"])
            return
        if k == "panel":
            op = self.panel_open[r["panel"]]
            if op:
                p.fillRect(QRectF(0, y, self.w, h), QColor(0, 0, 0, 12 if S.BODY.lightness() > 128 else 38))
            cx, cy = PAD + 5, y + h / 2
            p.setBrush(QColor("#d9d9d9"))
            p.setPen(Qt.NoPen)
            if op:
                p.setPen(QPen(S.TXT, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(Qt.NoBrush)
                p.drawPolyline(QPolygonF([QPointF(cx - 4, cy - 1.8), QPointF(cx, cy + 1.8), QPointF(cx + 4, cy - 1.8)]))
            else:
                p.setPen(QPen(S.TXT, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(Qt.NoBrush)
                p.drawPolyline(QPolygonF([QPointF(cx - 1.8, cy - 4), QPointF(cx + 1.8, cy), QPointF(cx - 1.8, cy + 4)]))
            p.setPen(S.TXT)
            p.drawText(QRectF(PAD + 16, y, fw - 16, h), AL, r["name"])
            return
        rect = QRectF(PAD, y, fw, h)
        v = self.get(r)
        if k == "enum" and r.get("seg"):
            sw = fw / len(r["items"])
            for i, it in enumerate(r["items"]):
                self.mini_btn(p, QRectF(PAD + i * sw, y, sw, h), it["name"], it["id"] == v)
            return
        if k == "enum":
            if r.get("rl"):
                self.paint_rl(p, r, rect, v)
                return
            if r.get("inline"):
                lw = fw * r.get("lw", 0.36)
                p.setPen(S.TXT)
                p.drawText(QRectF(PAD, y, lw, h), AL, r["name"] + ("" if r.get("nocolon") else ":"))
                rect = QRectF(PAD + lw, y, fw - lw, h)
            path = self.field(p, rect, S.MENU)
            self.outline(p, path)
            name = next((i["name"] for i in r["items"] if i["id"] == v), str(v))
            p.setPen(S.TXT)
            left = 8
            if r["ref"][1] == "data_type":
                dc = {"FLOAT": "#a1a1a1", "FLOAT_VECTOR": "#6363c7", "VECTOR": "#6363c7",
                      "RGBA": "#c7c729", "INT": "#598c5c", "BOOLEAN": "#cca6d6",
                      "ROTATION": "#a64dc7"}.get(v, "#a1a1a1")
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(dc))
                p.drawEllipse(QPointF(rect.x() + 12, rect.center().y()), 3.5, 3.5)
                left = 22
            p.setPen(S.TXT)
            p.drawText(rect.adjusted(left, 0, -22, 0), AL, name)
            cx, cy = rect.right() - r.get("arrow", 11.0), rect.center().y()
            p.setPen(QPen(S.MENU_ITEM, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(QPointF(cx - 2.6, cy - 1.2), QPointF(cx, cy + 1.4))
            p.drawLine(QPointF(cx, cy + 1.4), QPointF(cx + 2.6, cy - 1.2))
        elif k in ("bool", "boolin"):
            box = QRectF(PAD, y + (h - 14) / 2, 14, 14)
            bp = QPainterPath()
            bp.addRoundedRect(box, 3, 3)
            p.fillPath(bp, S.CHECK_ON if v else S.FIELD)
            self.outline(p, bp)
            if v:
                p.setPen(QPen(QColor("#ffffff"), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawLine(QPointF(box.x() + 3.2, box.y() + 7.3), QPointF(box.x() + 6, box.y() + 10.3))
                p.drawLine(QPointF(box.x() + 6, box.y() + 10.3), QPointF(box.x() + 10.8, box.y() + 3.8))
            p.setPen(S.TXT)
            p.drawText(QRectF(PAD + 17, y, fw - 17, h), AL, r["name"])
        elif k == "num":
            path = self.field(p, rect, S.FIELD, r.get("jt", False), r.get("jb", False))
            if r.get("fac"):
                frac = max(0.0, min(1.0, (float(v) - r["lo"]) / (r["hi"] - r["lo"])))
                if frac > 0:
                    p.save()
                    p.setClipPath(path)
                    p.fillRect(QRectF(rect.x(), rect.y(), rect.width() * frac, rect.height()), S.SLIDER)
                    p.restore()
            self.outline(p, path)
            p.setPen(S.TXT)
            inner = rect.adjusted(NUM_PAD_L, 0, -NUM_PAD_R, 0)
            vtxt = fmt_unit(v, r)
            fm = p.fontMetrics()
            # el nombre se corta con "…" para no pisar el valor (como hace Blender)
            avail = max(0.0, inner.width() - fm.horizontalAdvance(vtxt) - 2)
            p.drawText(inner, AL, fm.elidedText(r["name"], Qt.ElideRight, int(avail)))
            p.drawText(inner, AR, vtxt)
        elif k == "num_legacy":   # rama antigua (margen 8), ya sin uso
            path = self.field(p, rect, S.FIELD, r.get("jt", False), r.get("jb", False))
            if r.get("fac"):
                frac = max(0.0, min(1.0, (float(v) - r["lo"]) / (r["hi"] - r["lo"])))
                if frac > 0:
                    p.save()
                    p.setClipPath(path)
                    p.fillRect(QRectF(rect.x(), rect.y(), rect.width() * frac, rect.height()), S.SLIDER)
                    p.restore()
            self.outline(p, path)
            p.setPen(S.TXT)
            p.drawText(rect.adjusted(8, 0, -8, 0), AL, r["name"])
            p.drawText(rect.adjusted(8, 0, -8, 0), AR, fmt_unit(v, r))
        elif k == "vec":
            path = self.field(p, rect, S.FIELD)
            self.outline(p, path)
            p.setPen(S.TXT)
            p.drawText(rect.adjusted(8, 0, -8, 0), AL, r["name"])
            vtxt = fmt_unit(v[r["i"]], {"unit": r.get("unit"), "st": "VALUE"})
            if r["name"]:
                p.drawText(rect.adjusted(8, 0, -8, 0), AR, vtxt)
            else:
                p.drawText(rect, Qt.AlignCenter, vtxt)
        elif k == "color":
            c = QColor.fromRgbF(lin2s(v[0]), lin2s(v[1]), lin2s(v[2]))
            p.setPen(S.TXT)
            if r.get("dim"):   # entrada que no influye: solo la etiqueta se atenua, la muestra de color no
                p.setPen(QColor(S.TXT.red(), S.TXT.green(), S.TXT.blue(), 115))
            p.drawText(QRectF(rect.x(), y, rect.width() * 0.4, h), AL, r["name"])   # etiqueta fuera del campo
            rect = QRectF(rect.x() + rect.width() * 0.42, rect.y(), rect.width() * 0.58, rect.height())
            path = self.field(p, rect, c)
            self.outline(p, path)
            lum = 0.299 * c.redF() + 0.587 * c.greenF() + 0.114 * c.blueF()
            r = dict(r, name="")   # el nombre ya se dibujo a la izquierda; la muestra va sin texto
            p.setPen(QColor("#111111") if lum > 0.6 else QColor("#ffffff"))
            p.drawText(rect.adjusted(8, 0, -8, 0), AL, r["name"])
        elif k == "str":
            if r.get("rl"):
                self.paint_rl(p, r, rect, v)
                return
            path = self.field(p, rect, S.TEXT_FIELD if r.get("icon") == "uvmap" else S.FIELD)
            self.outline(p, path)
            left = 8
            if r.get("icon"):
                p.setPen(QPen(S.TXT, 1.1))
                p.setBrush(Qt.NoBrush)
                if r["icon"] == "uvmap":
                    draw_uv_icon(p, QRectF(rect.x() + 5, rect.center().y() - 7, 14, 14), S.TXT)
                elif r["icon"] == "circle":
                    p.drawEllipse(QRectF(rect.x() + 7, rect.center().y() - 4, 9, 9))
                elif r["icon"] == "obj":
                    draw_object_icon(p, QRectF(rect.x() + 4, rect.center().y() - 7.5, 15, 15), S.TXT)
                else:
                    p.drawRect(QRectF(rect.x() + 7, rect.center().y() - 4, 8, 8))
                left = 22
            right = 8
            if r.get("icon") == "obj":   # selector de objeto: cuentagotas a la derecha, como en Blender
                draw_dropper_icon(p, QRectF(rect.right() - 20, rect.center().y() - 7.5, 15, 15), S.TXT)
                right = 24
            shown = str(v) if v else ""
            p.setPen(S.TXT if shown else S.DIM)
            p.drawText(rect.adjusted(left, 0, -right, 0), AL, shown or r.get("ph", ""))

    def paint_rl(self, p, r, rect, v):
        """Render Layers: fila Scene (selector | nombre | X) y fila Layer (menu | boton de capas)."""
        x, y, fw, h = rect.x(), rect.y(), rect.width(), rect.height()
        bw = 20.0                                              # ancho del boton de la derecha (X / capas)

        def chevron(cx, cy):
            p.setPen(QPen(S.MENU_ITEM, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPolyline(QPolygonF([QPointF(cx - 2.6, cy - 1.2), QPointF(cx, cy + 1.4), QPointF(cx + 2.6, cy - 1.2)]))

        cy = y + h / 2
        btn = QRectF(x + fw - bw, y, bw, h)
        if r["rl"] == "scene":
            sw = 31.0                                          # selector de escena: icono + flechita
            path = self.field(p, QRectF(x, y, sw, h), S.MENU)
            self.outline(p, path)
            draw_scene_icon(p, QRectF(x + 3.0, cy - 7.5, 15.0, 15.0), S.TXT)
            chevron(x + sw - 6.5, cy)
            tx = x + sw + 1                                    # nombre de la escena (campo de texto oscuro)
            tf = QRectF(tx, y, btn.left() - 1 - tx, h)
            path = self.field(p, tf, S.TEXT_FIELD)
            self.outline(p, path)
            shown = str(v) if v else ""
            p.setPen(S.TXT if shown else S.DIM)
            p.drawText(tf.adjusted(8, 0, -6, 0), AL, shown or r.get("ph", ""))
            path = self.field(p, btn, S.FIELD)                   # X: quitar la escena
            self.outline(p, path)
            p.setPen(QPen(S.TXT, 1.3, Qt.SolidLine, Qt.RoundCap))
            c = btn.center()
            p.drawLine(QPointF(c.x() - 3.8, c.y() - 3.8), QPointF(c.x() + 3.8, c.y() + 3.8))
            p.drawLine(QPointF(c.x() - 3.8, c.y() + 3.8), QPointF(c.x() + 3.8, c.y() - 3.8))
        else:
            fld = QRectF(x, y, fw - bw - 1, h)                 # menu de la capa
            path = self.field(p, fld, S.MENU)
            self.outline(p, path)
            name = next((i["name"] for i in r["items"] if i["id"] == v), str(v))
            p.setPen(S.TXT)
            p.drawText(fld.adjusted(8, 0, -22, 0), AL, name)
            chevron(fld.right() - 11.0, cy)
            path = self.field(p, btn, S.FIELD)                   # boton de capas de render
            self.outline(p, path)
            draw_layers_icon(p, QRectF(btn.center().x() - 8.0, cy - 8.0, 16.0, 16.0), S.TXT)

    def mini_btn(self, p, rect, text, active=False):
        path = self.field(p, rect, S.CHECK_ON if active else S.FIELD)
        self.outline(p, path)
        p.setPen(QColor("#ffffff") if active else S.TXT)
        p.drawText(rect, Qt.AlignCenter, text)

    def paint_imgsel(self, p, x, y, fw):
        """Fila selector de imagen + New + Open como en Blender: el selector lleva su icono y su flechita,
        y New/Open van pegados formando un solo grupo con una linea de union."""
        yy, bh, sw = y + IMG_TOP, 20.0, 31.0
        # selector (estilo menu)
        path = self.field(p, QRectF(x, yy, sw, bh), S.MENU)
        p.setPen(QPen(S.WCOL_OUT.get("menu", S.FIELD_LINE), FIELD_LINE_W))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        ic = QRectF(x + 2.3, yy + 1.85, 16.3, 16.3)           # icono de imagen (tu SVG)
        p.setPen(Qt.NoPen)
        p.setBrush(S.TXT)
        draw_image_icon(p, ic, S.TXT)
        p.setBrush(Qt.NoBrush)   # (el dibujo viejo de la montana ya no se ve: lo reemplaza draw_image_icon)
        p.drawPolygon(QPolygonF([QPointF(ic.left() + 1.5, ic.bottom() - 1.5),
                                 QPointF(ic.left() + 4.5, ic.bottom() - 5.5),
                                 QPointF(ic.left() + 6.5, ic.bottom() - 3.5),
                                 QPointF(ic.left() + 8.0, ic.bottom() - 5.0),
                                 QPointF(ic.right() - 1.5, ic.bottom() - 1.5)]))
        pass
        cx, cy = x + sw - 7.5, yy + bh / 2                    # flechita del menu
        p.setPen(QPen(S.MENU_ITEM, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(cx - 2.6, cy - 1.2), QPointF(cx, cy + 1.4), QPointF(cx + 2.6, cy - 1.2)]))
        # grupo New | Open
        gx = x + sw + 1
        grp = QRectF(gx, yy, x + fw - gx, bh)
        path = self.field(p, grp, S.FIELD)
        p.setPen(QPen(S.FIELD_LINE, FIELD_LINE_W))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        mid = grp.center().x()
        p.drawLine(QPointF(mid, grp.top()), QPointF(mid, grp.bottom()))
        p.setPen(S.TXT)
        p.drawText(QRectF(grp.left() + 14, yy, mid - grp.left() - 14, bh), Qt.AlignCenter, "New")
        p.drawText(QRectF(mid + 14, yy, grp.right() - mid - 14, bh), Qt.AlignCenter, "Open")
        pc = QPointF(grp.left() + 12, yy + bh / 2)            # "+" de New
        p.setPen(QPen(S.TXT, 1.2))
        p.drawLine(QPointF(pc.x() - 4, pc.y()), QPointF(pc.x() + 4, pc.y()))
        p.drawLine(QPointF(pc.x(), pc.y() - 4), QPointF(pc.x(), pc.y() + 4))
        fx, fy = mid + 8, yy + 5.5                            # carpeta de Open
        p.setPen(Qt.NoPen)
        p.setBrush(S.TXT)
        draw_folder_icon(p, QRectF(fx - 0.5, yy + bh / 2 - 6.5, 13.0, 13.0), S.TXT)   # tu folder.svg
        pass

    def _fit_text(self, fm, text, width):
        if fm.horizontalAdvance(text) <= width:
            return text
        while text and fm.horizontalAdvance(text + "...") > width:
            text = text[:-1]
        return text.rstrip() + "..."

    def paint_imgloaded(self, p, r):
        """FILA_V3 - fila de imagen cargada (template_ID de Blender):
        selector | nombre (se estira) | usuarios | escudo | duplicar | carpeta | X."""
        from PySide6.QtGui import QFontMetrics
        d = self.img_loaded or {}
        x, fw = PAD, self.w - 2 * PAD
        yy, bh = r["y"] + IMG_TOP, 20.0
        wide = self.w >= 200
        sw = 30.5 if wide else 21.0
        ic_w = [20.0, 20.0, 20.0, 20.0]                  # escudo, duplicar, carpeta, X
        users = max(24.0, 0.108 * self.w)
        gw = fw - sw - 1
        rest = users + sum(ic_w)
        if gw - rest < 40:                                # nodo estrecho: se encogen los botones, no el nombre
            f = max(0.5, (gw - 40) / rest)
            users *= f
            ic_w = [v * f for v in ic_w]
        name_w = gw - users - sum(ic_w)

        # --- selector de imagen: marco fino con montana y sol (como el icono de Blender) + flechita
        path = self.field(p, QRectF(x, yy, sw, bh), S.MENU)
        p.setPen(QPen(S.WCOL_OUT.get("menu", S.FIELD_LINE), FIELD_LINE_W))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        isz = 16.3 if wide else 11.8
        ic = QRectF(x + (4.0 if wide else 3.2), yy + (bh - isz) / 2, isz, isz)
        pt = lambda fx, fy: QPointF(ic.left() + fx * ic.width(), ic.top() + fy * ic.height())
        p.setPen(QPen(S.TXT, 1.3, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
        p.setBrush(Qt.NoBrush)
        draw_image_icon(p, ic, S.TXT)
        p.setPen(Qt.NoPen)
        p.setBrush(S.TXT)
        pass
        pass
        cx, cy = x + sw - (5.0 if wide else 4.5), yy + bh / 2
        hw = 2.6 if wide else 2.2
        p.setPen(QPen(S.MENU_ITEM, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(cx - hw, cy - 1.2), QPointF(cx, cy + 1.4), QPointF(cx + hw, cy - 1.2)]))

        # --- grupo: nombre | usuarios | iconos
        gx = x + sw + 1
        grp = QRectF(gx, yy, gw, bh)
        path = self.field(p, grp, S.FIELD)
        p.setPen(QPen(S.FIELD_LINE, FIELD_LINE_W))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        edges, acc = [], grp.left()
        for wv in [name_w, users] + ic_w:
            edges.append((acc, acc + wv))
            acc += wv
        for a, b in edges[:-1]:
            p.drawLine(QPointF(b, grp.top()), QPointF(b, grp.bottom()))
        fm = QFontMetrics(self.F)
        short = self._fit_text(fm, d.get("name", ""), name_w - 13.5)
        p.setPen(S.TXT)
        p.drawText(QRectF(edges[0][0] + 7.5, yy, name_w - 7.5, bh), AL, short)
        p.drawText(QRectF(edges[1][0], yy, edges[1][1] - edges[1][0], bh), Qt.AlignCenter, str(d.get("users", 1)))
        c = lambda i: QPointF((edges[i][0] + edges[i][1]) / 2, yy + bh / 2)
        pen = QPen(S.TXT, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

        q, s = c(2), 1.2                                             # escudo (usuario falso)
        sh = QPainterPath()
        sh.moveTo(q.x(), q.y() - 6.0 * s)
        sh.lineTo(q.x() + 5.0 * s, q.y() - 4.2 * s)
        sh.lineTo(q.x() + 5.0 * s, q.y() + 0.8 * s)
        sh.quadTo(q.x() + 5.0 * s, q.y() + 4.0 * s, q.x(), q.y() + 6.2 * s)
        sh.quadTo(q.x() - 5.0 * s, q.y() + 4.0 * s, q.x() - 5.0 * s, q.y() + 0.8 * s)
        sh.lineTo(q.x() - 5.0 * s, q.y() - 4.2 * s)
        sh.closeSubpath()
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(sh)

        q, s = c(3), 1.15                                            # duplicar: hoja de atras + hoja con esquina doblada
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(q.x() - 6.0 * s, q.y() - 6.0 * s, 8.0 * s, 9.5 * s), 1.2, 1.2)
        front = QPainterPath()
        front.moveTo(q.x() - 3.5 * s, q.y() - 3.0 * s)
        front.lineTo(q.x() + 1.5 * s, q.y() - 3.0 * s)
        front.lineTo(q.x() + 6.0 * s, q.y() + 1.5 * s)
        front.lineTo(q.x() + 6.0 * s, q.y() + 6.5 * s)
        front.lineTo(q.x() - 3.5 * s, q.y() + 6.5 * s)
        front.closeSubpath()
        p.setBrush(S.FIELD)
        p.drawPath(front)
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(q.x() + 1.5 * s, q.y() - 3.0 * s), QPointF(q.x() + 1.5 * s, q.y() + 1.5 * s),
                                  QPointF(q.x() + 6.0 * s, q.y() + 1.5 * s)]))

        q, s = c(4), 1.1                                             # carpeta (rellena, como en Blender)
        p.setPen(Qt.NoPen)
        p.setBrush(S.TXT)
        draw_folder_icon(p, QRectF(q.x() - 8.0, q.y() - 8.0, 16.0, 16.0), S.TXT)   # tu folder.svg
        pass

        q = c(5)                                                     # X (quitar imagen)
        p.setPen(QPen(S.TXT, 1.3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(q.x() - 3.8, q.y() - 3.8), QPointF(q.x() + 3.8, q.y() + 3.8))
        p.drawLine(QPointF(q.x() - 3.8, q.y() + 3.8), QPointF(q.x() + 3.8, q.y() - 3.8))

    def paint_block(self, p, r):
        kind, y, h = r["kind"], r["y"], r["h"]
        x, fw = PAD, self.w - 2 * PAD
        if kind == "wheel":
            bar_w, sw_h = 12.0, 18.0
            d = min(fw - bar_w - 10, h - sw_h - 10)
            cx, cy = x + (fw - bar_w - 6) / 2, y + 4 + d / 2
            cg = QConicalGradient(QPointF(cx, cy), 0)
            for i in range(7):
                cg.setColorAt(i / 6, QColor.fromHsvF((i % 6) / 6.0, 1.0, 1.0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(cg))
            p.drawEllipse(QPointF(cx, cy), d / 2, d / 2)
            rg = QRadialGradient(QPointF(cx, cy), d / 2)
            rg.setColorAt(0, QColor(255, 255, 255, 255))
            rg.setColorAt(1, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(rg))
            p.drawEllipse(QPointF(cx, cy), d / 2, d / 2)
            p.setPen(QPen(QColor("#999999"), 1.0))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), 3.5, 3.5)
            bar = QRectF(x + fw - bar_w, y + 4, bar_w, d)
            lg = QLinearGradient(0, bar.top(), 0, bar.bottom())
            lg.setColorAt(0, QColor("#ffffff"))
            lg.setColorAt(1, QColor("#000000"))
            bp = QPainterPath()
            bp.addRoundedRect(bar, 2, 2)
            p.fillPath(bp, QBrush(lg))
            self.outline(p, bp)
            p.fillRect(QRectF(bar.left() - 1, bar.top() + 3, bar_w + 2, 4), QColor("#cfcfcf"))
            c = QColor("#b8b8b8")
            try:
                dv = self.spec["outputs"][0].get("default")
                if isinstance(dv, list) and len(dv) >= 3:
                    c = QColor.fromRgbF(lin2s(dv[0]), lin2s(dv[1]), lin2s(dv[2]))
            except Exception:
                pass
            sw = QRectF(x, y + h - sw_h - 2, fw, sw_h)
            path = self.field(p, sw, c)
            self.outline(p, path)
        elif kind in ("curve", "curve_rgb", "curve_xyz"):
            bh = 18.0
            labels = {"curve_rgb": ["C", "R", "G", "B"], "curve_xyz": ["X", "Y", "Z"]}.get(kind, [])
            bx = x
            for i, t in enumerate(labels):
                self.mini_btn(p, QRectF(bx, y + 2, 20, bh), t, i == 0)
                bx += 21
            zx = x + fw - 3 * 21
            for t in ("+", "-", "o"):
                self.mini_btn(p, QRectF(zx, y + 2, 20, bh), t)
                zx += 21
            gr = QRectF(x, y + bh + 6, fw, h - bh - 6 - 4)
            p.fillRect(gr, QColor("#424242"))
            p.setPen(QPen(QColor("#575757"), 1.0))
            for i in range(1, 4):
                p.drawLine(QPointF(gr.left() + gr.width() * i / 4, gr.top()),
                           QPointF(gr.left() + gr.width() * i / 4, gr.bottom()))
                p.drawLine(QPointF(gr.left(), gr.top() + gr.height() * i / 4),
                           QPointF(gr.right(), gr.top() + gr.height() * i / 4))
            if kind == "curve_xyz":
                p.setPen(QPen(QColor("#8f8f2e"), 1.0))
                p.drawLine(QPointF(gr.center().x(), gr.top()), QPointF(gr.center().x(), gr.bottom()))
                p.setPen(QPen(QColor("#a54545"), 1.0))
                p.drawLine(QPointF(gr.left(), gr.center().y()), QPointF(gr.right(), gr.center().y()))
            p.setPen(QPen(QColor("#0d0d0d"), 1.3))
            p.drawLine(QPointF(gr.left(), gr.bottom()), QPointF(gr.right(), gr.top()))
            p.setPen(QPen(S.FIELD_LINE, 1.0))
            p.setBrush(Qt.NoBrush)
            p.drawRect(gr)
        elif kind == "ramp":
            # medidas de Blender 5.2 (sacadas de capturas), relativas al inicio del bloque (y)
            by = y + 8.0                                  # fila de iconos + menu doble
            cy = by + 10.0
            p.setPen(QPen(S.TXT, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            cx = x + 10.0                                 # "+"
            p.drawLine(QPointF(cx - 3.9, cy), QPointF(cx + 3.9, cy))
            p.drawLine(QPointF(cx, cy - 3.9), QPointF(cx, cy + 3.9))
            cx = x + 35.5                                 # "-"
            p.drawLine(QPointF(cx - 3.9, cy), QPointF(cx + 3.9, cy))
            cx = x + 66.5                                 # "v"
            p.drawPolyline(QPolygonF([QPointF(cx - 3.7, cy - 2.0), QPointF(cx, cy + 2.0),
                                      QPointF(cx + 3.7, cy - 2.0)]))
            gx = x + 92.8                                 # RGB | Linear: una sola caja con linea divisoria
            grp = QRectF(gx, by, x + fw - gx, 20.0)
            path = self.field(p, grp, S.MENU)
            self.outline(p, path)
            mid = x + 156.0
            p.setPen(QPen(S.FIELD_LINE, FIELD_LINE_W))
            p.drawLine(QPointF(mid, grp.top()), QPointF(mid, grp.bottom()))
            p.setPen(S.TXT)
            p.drawText(QRectF(x + 100.0, by, mid - x - 100.0, 20.0), AL, self.ramp["cmode"])
            p.drawText(QRectF(x + 163.3, by, x + fw - x - 163.3, 20.0), AL, self.ramp["interp"])
            p.setPen(QPen(S.MENU_ITEM, 1.1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            for ax in (x + 150.4, x + 213.2):             # flechitas de cada menu
                p.drawLine(QPointF(ax - 2.6, cy - 1.2), QPointF(ax, cy + 1.4))
                p.drawLine(QPointF(ax, cy + 1.4), QPointF(ax + 2.6, cy - 1.2))
            # barra del degradado (metida 5 u por cada lado, esquinas rectas)
            gr = QRectF(x + 5.0, y + 33.5, fw - 10.0, 18.5)
            lg = QLinearGradient(gr.left(), 0, gr.right(), 0)
            for _t in ramp_samples(self.ramp):
                _c = ramp_eval(self.ramp, _t)
                lg.setColorAt(_t, QColor.fromRgbF(lin2s(_c[0]), lin2s(_c[1]), lin2s(_c[2]), 1.0))
            # (degradado muestreado desde los marcadores)
            p.fillRect(gr, QBrush(lg))
            p.setPen(QPen(QColor(S.TXT.red(), S.TXT.green(), S.TXT.blue(), 70), 0.8))   # borde fino de la barra
            p.setBrush(Qt.NoBrush)
            p.drawRect(gr)
            # marcadores: pentagono con la punta hacia arriba, centrado en cada extremo de la barra
            for xx, cc, selm in self._ramp_markers(gr):
                tip, bot, hw = gr.top() + 9.0, gr.top() + 22.8, 5.8
                # linea punteada de cada marcador (blanca en el activo, gris en el otro)
                _bc = ramp_eval(self.ramp, (xx - gr.left()) / gr.width())
                _lum = 0.299 * lin2s(_bc[0]) + 0.587 * lin2s(_bc[1]) + 0.114 * lin2s(_bc[2])
                _lc = QColor("#000000") if _lum > 0.5 else QColor("#ffffff")   # contrasta con el degradado de fondo
                if not selm:
                    _lc.setAlpha(150)
                _lp = QPen(_lc, 0.9)
                _lp.setDashPattern([2.0, 2.0])   # rayas cortas con hueco, como en Blender
                _hc = QColor("#ffffff") if _lum > 0.5 else QColor("#000000")   # halo opuesto a la raya, como en Blender
                _hc.setAlpha(255 if selm else 150)
                p.setPen(Qt.NoPen)   # sin contorno en la linea punteada (halo desactivado)
                p.drawLine(QPointF(xx, gr.top()), QPointF(xx, tip))
                p.setPen(_lp)
                p.drawLine(QPointF(xx, gr.top()), QPointF(xx, tip))
                oc = QColor("#1a1a1a")   # contorno oscuro en ambos (en Blender el inactivo tambien lo lleva negro)   # contorno oscuro (el activo mas negro)
                p.setPen(QPen(oc, 0.35))
                p.setBrush(QColor("#d9d9d9") if selm else QColor("#606060"))   # techo: gris claro si esta activo
                p.drawPolygon(QPolygonF([QPointF(xx, tip), QPointF(xx + hw, tip + 5.0), QPointF(xx + hw, bot),
                                         QPointF(xx - hw, bot), QPointF(xx - hw, tip + 5.0)]))
                if not selm:                               # techo del marcador inactivo en gris oscuro
                    p.setBrush(QColor("#606060"))
                    p.drawPolygon(QPolygonF([QPointF(xx, tip), QPointF(xx + hw, tip + 5.0),
                                             QPointF(xx - hw, tip + 5.0)]))
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(cc))
                _by = tip + 5.0
                p.setBrush(QColor("#808080"))   # anillo gris: igual en activo e inactivo (como en Blender)
                p.drawRect(QRectF(xx - hw + 0.18, _by, 2 * hw - 0.36, bot - _by - 0.18))
                p.setBrush(QColor(cc))
                p.drawRect(QRectF(xx - hw + 0.58, _by + 0.4, 2 * hw - 1.16, bot - _by - 0.98))
            # fila "0" + Pos
            py = y + 63.2
            z = QRectF(x, py, 63.0, 20.0)
            path = self.field(p, z, S.FIELD)
            self.outline(p, path)
            p.setPen(S.TXT)
            p.drawText(z, Qt.AlignCenter, str(self.ramp["active"]))
            f2 = QRectF(x + 71.7, py, fw - 71.7, 20.0)
            path = self.field(p, f2, S.FIELD)
            _pf = 0.0   # en Blender el campo Pos no lleva relleno
            if _pf > 0:                                   # Pos es un deslizador 0-1: relleno proporcional
                p.save()
                p.setClipPath(path)
                p.fillRect(QRectF(f2.x(), f2.y(), f2.width() * _pf, f2.height()), S.SLIDER)
                p.restore()
            self.outline(p, path)
            p.setPen(S.TXT)
            p.drawText(f2.adjusted(NUM_PAD_L, 0, -NUM_PAD_R, 0), AL, "Pos")
            p.drawText(f2.adjusted(NUM_PAD_L, 0, -NUM_PAD_R, 0), AR, f'{self.ramp["stops"][self.ramp["active"]]["pos"]:.3f}')
            # muestra de color (queda a 2 u del Factor, como en Blender)
            _ac = self.ramp["stops"][self.ramp["active"]]["color"]
            path = self.field(p, QRectF(x, y + 88.0, fw, 20.0), QColor.fromRgbF(lin2s(_ac[0]), lin2s(_ac[1]), lin2s(_ac[2])))
            self.outline(p, path)
        elif kind == "imgsel":
            self.paint_imgsel(p, x, y, fw)
            
            p.setPen(QPen(S.TXT, 1.2))
            p.setBrush(Qt.NoBrush)
            
            
            
            
        elif kind == "spheres":
            sh = (h - 6) / 2
            for i in range(2):
                box = QRectF(x, y + i * (sh + 3), fw, sh)
                path = self.field(p, box, QColor("#4a4a4a"))
                self.outline(p, path)
                rad = min(box.width(), box.height()) / 2 - 3
                c = box.center()
                rg = QRadialGradient(QPointF(c.x() - rad * 0.3, c.y() - rad * 0.3), rad * 1.4)
                rg.setColorAt(0, QColor("#ffffff"))
                rg.setColorAt(1, QColor("#5a5a5a") if i == 0 else QColor("#707070"))
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(rg))
                p.drawEllipse(c, rad, rad)
        elif kind == "groupsel":
            f = QRectF(x, y + 2, fw, 18)
            path = self.field(p, f, S.FIELD)
            self.outline(p, path)
            p.setPen(S.TXT)
            p.drawText(f.adjusted(8, 0, -8, 0), AL, self.spec["label"])
