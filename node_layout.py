"""Layout de NodeItem: que propiedades y sockets se ven, sus filas y la altura del nodo. LayoutMixin se
mezcla en NodeItem, que conserva el estado."""
from metrics import (BOOL_UP, BROW, ENUM_TIGHT, EROW, FH, GAP, HEADER, IMG_ALPHA_ITEMS, IMG_CS_ITEMS, IMG_LOADED_H, IMG_SRC_ITEMS, INPUT_PULL, LROW, MENU_DOWN, PANEL_GAP_END, PANEL_GAP_HEAD, ROW, STACKED, TIGHT_PAD, TOP_SHIFT)
from node_tables import (BLOCKS, EXTRA_H, GLARE_SOCKS, IMGSEL_H, IO_MERGE, MATH_1, MATH_3, MATH_LABELS, MENU_ITEMS, MIX_ORDER, MIX_SFX, PANELS, PROPS_FIRST, PROPS_TOP, PROP_EXTRA, PROP_ORDER, RL_PITCH, SKIP_PROPS, TRAILING_PANELS, VM_1, VM_3, VM_LABELS, VM_VAL)


class LayoutMixin:
    """Calculo de filas (relayout) y reglas dinamicas segun los menus del nodo."""

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
