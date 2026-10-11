"""Temas de color para Nodo Capture (como los themes de Blender).

Uso:  main.py y main_func.py llaman a  themes.install(ventana)  y la barra de
herramientas recibe un selector "Tema" y el boton "Importar tema Blender (.xml)".

Cada tema es un JSON en data/themes/ con SOLO lo que cambia respecto a tu Blender
(data/theme.json y data/widgets.json). Colores como "#rrggbb", "#rrggbbaa" o [r,g,b,a] 0-1:

{
  "name": "Mi tema",
  "theme":   {"node_backdrop": "#202020", "node_outline": "#000000", "grid": "#2d2d2d", ...},
  "widgets": {"wcol_regular": {"inner": "#333333", "outline": "#191919", "text": "#ffffff"},
              "wcol_menu": {"inner": "#2a2a2a"}, "wcol_numslider": {"item": "#4772b3"},
              "wcol_option": {"inner_sel": "#4772b3"}},
  "extra":   {"bg": "#1a1a1a", "grid_minor": "#212121", "title": "#eeeeee", "dim": "#7d7d7d"},
  "sock":    {"VALUE": "#a1a1a1", ...},           # colores de sockets (opcional)
  "ui":      {"window": "#d9d9d9", "text": "#1a1a1a", ...}   # paleta de la ventana (opcional)
}
"""
import copy
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QBrush, QColor, QPalette, QPen
from PySide6.QtWidgets import QApplication, QComboBox, QFileDialog, QMessageBox, QToolBar

BUILTIN = "Blender Dark"
EXTRA_BASE = {"link_line": "#000000", "sock_line": "#000000", "curving": 5.0, "bg": "#1a1a1a", "grid_minor": "#212121", "title": "#eeeeee", "dim": "#7d7d7d"}
HEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})")
WCOL_KINDS = {"num": "wcol_num", "slider": "wcol_numslider", "menu": "wcol_menu", "opt": "wcol_option",
              "text": "wcol_text", "radio": "wcol_radio"}

M = None            # modulo donde vive la clase Window (main o __main__)
WIN = None
DIR = None
THEME_BASE = WID_BASE = SOCK_BASE = None


def _rgba(v):
    """'#rrggbb' / '#rrggbbaa' (orden Blender) o lista -> [r, g, b, a] en 0-1."""
    if isinstance(v, str):
        if not v.startswith("#"):
            return float(v)          # numeros (roundness) que vienen como texto en el XML
        s = v.lstrip("#")
        vals = [int(s[i:i + 2], 16) / 255.0 for i in range(0, len(s), 2)]
        return vals if len(vals) == 4 else vals[:3] + [1.0]
    return v if isinstance(v, (int, float)) else list(v)


def _shift(hexc, d):
    c = QColor(hexc)
    f = lambda x: max(0, min(255, x + d))
    return QColor(f(c.red()), f(c.green()), f(c.blue())).name()


def available():
    out = {BUILTIN: {"name": BUILTIN}}
    if DIR is not None and DIR.is_dir():
        for f in sorted(DIR.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(d, dict):
                out[d.get("name", f.stem)] = d
    return out


# ------------------------------------------------------------ aplicar
_SKIN_SRC = {"FIELD": "inner", "MENU": "inner", "MENU_ITEM": "item", "SLIDER": "item", "TXT": "text", "CHECK_ON": "inner_sel"}


def _skins(wd):
    """Colores y esquinas propios de cada tipo de widget (numero, deslizador, menu, casilla, texto, botones)."""
    out = {}
    for kind, w in WCOL_KINDS.items():
        d = wd.get(w)
        if not d:
            continue
        skin = {name: M.col(d[key]) for name, key in _SKIN_SRC.items() if key in d}
        if "roundness" in d:
            skin["RAD"] = float(d["roundness"]) * M.FH / 2
        out[kind] = skin
    return out


def apply(data):
    th = copy.deepcopy(THEME_BASE)
    for k, v in (data.get("theme") or {}).items():
        th[k] = _rgba(v)
    wd = copy.deepcopy(WID_BASE)
    for wname, d in (data.get("widgets") or {}).items():
        wd.setdefault(wname, {}).update({k: _rgba(v) for k, v in d.items()})
    ex = dict(EXTRA_BASE)
    ex.update(data.get("extra") or {})
    col = M.col
    M.HEAD = {k: col(th[k]) for k in M.HEAD}
    M.BG = QColor(ex["bg"])
    M.GRID_MINOR = QColor(ex["grid_minor"])
    M.GRID_MAJOR = col(th["grid"])
    M.BODY = col(th["node_backdrop"])
    M.OUTLINE = col(th["node_outline"])
    M.SEL = col(th["node_selected"])
    M.TXT = col(wd["wcol_regular"]["text"])
    M.TITLE = QColor(ex["title"])
    M.DIM = QColor(ex["dim"])
    M.FIELD = col(wd["wcol_regular"]["inner"])
    M.FIELD_LINE = col(wd["wcol_regular"]["outline"])
    M.MENU = col(wd["wcol_menu"]["inner"])
    M.MENU_ITEM = col(wd["wcol_menu"]["item"])
    M.SLIDER = col(wd["wcol_numslider"]["item"])
    M.CHECK_ON = col(wd["wcol_option"]["inner_sel"])
    M.WIRE = col(th["wire"])
    M.WIRE_SEL = col(th["wire_select"])
    M.SOCK.clear()
    M.SOCK.update(SOCK_BASE)
    M.SOCK.update(data.get("sock") or {})
    M.SOCK_LINE = ex["sock_line"]
    M.LINK_LINE = ex["link_line"]
    M.CURVING = max(0.0, min(10.0, float(ex.get("curving", 5.0))))
    # esquinas de los campos: radio = roundness * alto / 2 (0.4 -> 4 px, como tenia fijo)
    M.RAD = float(wd["wcol_regular"].get("roundness", 0.4)) * M.FH / 2
    # contorno propio de cada tipo de widget (numeros, deslizadores, menus, casillas)
    M.WCOL_OUT = {kind: col(wd[w]["outline"]) for kind, w in WCOL_KINDS.items() if w in wd}
    # relleno, texto, relleno activo y esquinas por tipo de widget; el tema integrado se deja
    # tal cual esta calibrado (solo los temas importados/personalizados usan estos valores)
    M.WCOL_SKIN = _skins(wd) if (data.get("theme") or data.get("widgets")) else {}
    _apply_ui(data.get("ui"))
    for sc in WIN.scenes.values():
        for it in sc.items():
            if isinstance(it, M.SocketItem):
                it.setBrush(QBrush(QColor(M.SOCK.get(it.spec.get("stype"), "#a1a1a1"))))
                it.setPen(QPen(QColor(M.SOCK_LINE), M.SOCK_LINE_W))
        for lk in getattr(sc, "links", []):
            lk.update_path()      # la curvatura (noodle_curving) cambia con el tema
        sc.update()
    WIN.view.viewport().update()


def _apply_ui(ui):
    app = QApplication.instance()
    if not ui:
        M.apply_dark(app)
        return
    pal = QPalette()
    g = lambda k, d: QColor(ui.get(k, d))
    for role, c in ((QPalette.Window, g("window", "#2b2b2b")), (QPalette.WindowText, g("text", "#e6e6e6")),
                    (QPalette.Base, g("base", "#1e1e1e")), (QPalette.AlternateBase, g("window", "#2b2b2b")),
                    (QPalette.Text, g("text", "#e6e6e6")), (QPalette.Button, g("button", "#3a3a3a")),
                    (QPalette.ButtonText, g("text", "#e6e6e6")),
                    (QPalette.Highlight, g("highlight", "#4772b3")),
                    (QPalette.HighlightedText, QColor("#ffffff"))):
        pal.setColor(role, c)
    app.setPalette(pal)


# ------------------------------------------------------------ importar de Blender
def import_blender_xml(path):
    """Convierte un preset de Blender (scripts/presets/interface_theme/*.xml) a un tema JSON."""
    root = ET.parse(path).getroot()
    parent = {c: p for p in root.iter() for c in p}
    theme, widgets, extra = {}, {}, {}
    for el in root.iter():
        if el.tag == "ThemeWidgetColors":
            wname = parent[el].tag if el in parent else ""
            if wname in WID_BASE:
                widgets[wname] = {k: v for k, v in el.attrib.items()
                                  if (k in WID_BASE[wname] or k == "roundness") and (HEX.fullmatch(v) or k == "roundness")}
        elif el.tag == "ThemeNodeEditor":
            theme = {k: v for k, v in el.attrib.items() if k in THEME_BASE and HEX.fullmatch(v)}
            if "noodle_curving" in el.attrib:
                extra["curving"] = float(el.attrib["noodle_curving"])
            for g in el.iter("ThemeSpaceGeneric"):
                b = g.attrib.get("back", "")
                if HEX.fullmatch(b):
                    extra["bg"] = b[:7]
                t = g.attrib.get("text", "")
                if HEX.fullmatch(t):
                    extra["title"] = t[:7]
    if "wire" in theme:
        extra["link_line"] = theme["wire"][:7]     # 'wire' es el contorno del cable en Blender
    if not theme and not widgets and "bg" not in extra:
        raise ValueError("No encontre colores del Node Editor en ese archivo.")
    bg = extra.get("bg", EXTRA_BASE["bg"])
    extra["bg"] = bg
    extra["grid_minor"] = _shift(bg, 7 if QColor(bg).lightness() < 128 else -7)
    data = {"name": Path(path).stem.replace("_", " ").title(), "theme": theme,
            "widgets": widgets, "extra": extra}
    if QColor(bg).lightness() >= 128:
        data["ui"] = {"window": "#d9d9d9", "text": "#1a1a1a", "base": "#f2f2f2", "button": "#cfcfcf"}
        extra["dim"] = "#6a6a6a"
    DIR.mkdir(exist_ok=True)
    (DIR / (Path(path).stem + ".json")).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data["name"]


# ------------------------------------------------------------ interfaz
def install(window):
    global M, WIN, DIR, THEME_BASE, WID_BASE, SOCK_BASE
    M = sys.modules[type(window).__module__]
    WIN, DIR = window, M.DATA / "themes"
    THEME_BASE, WID_BASE = copy.deepcopy(M.THEME), copy.deepcopy(M.WID)
    if "wcol_toggle" in WID_BASE:
        # tu widgets.json no trae wcol_radio: se parte de wcol_toggle para que el XML pueda sobrescribirlo
        WID_BASE.setdefault("wcol_radio", copy.deepcopy(WID_BASE["wcol_toggle"]))
    SOCK_BASE = dict(M.SOCK)
    choice_file = M.DATA / "theme_choice.txt"

    # el contorno de cada campo depende del tipo de widget (como en Blender: wcol_num, wcol_menu...)
    NI = M.NodeItem
    if not getattr(NI, "_wk_wrapped", False):
        orig_row, orig_outline = NI.paint_row, NI.outline

        def paint_row(self, p, r):
            k = r["k"]
            if k == "enum" and not r.get("seg"):
                self._wk = "menu"
            elif k == "num":
                self._wk = "slider" if r.get("fac") else "num"
            elif k == "vec":
                self._wk = "num"
            elif k in ("bool", "boolin"):
                self._wk = "opt"
            elif k == "enum":
                self._wk = "radio"        # botones segmentados (los menus ya entraron arriba)
            elif k == "str":
                self._wk = "text"
            else:
                self._wk = None
            try:
                skin = getattr(M, "WCOL_SKIN", {}).get(self._wk) or {}
                saved = {n: getattr(M, n) for n in skin}
                for n, v in skin.items():
                    setattr(M, n, v)          # colores/esquinas de este tipo de widget, solo durante la fila
                try:
                    orig_row(self, p, r)
                finally:
                    for n, v in saved.items():
                        setattr(M, n, v)
            finally:
                self._wk = None

        def outline(self, p, path):
            c = getattr(M, "WCOL_OUT", {}).get(getattr(self, "_wk", None))
            if c is None:
                orig_outline(self, p, path)
                return
            p.setPen(QPen(c, getattr(M, "FIELD_LINE_W", 1.0)))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)

        NI.paint_row, NI.outline, NI._wk_wrapped = paint_row, outline, True

    tb = window.findChildren(QToolBar)[0]
    combo = QComboBox()
    combo.setToolTip("Tema de colores")
    acts = tb.actions()
    if len(acts) > 1:
        tb.insertWidget(acts[1], combo)
    else:
        tb.addWidget(combo)

    def fill(select):
        combo.blockSignals(True)
        combo.clear()
        for name in available():
            combo.addItem("Tema: " + name, name)
        i = combo.findData(select)
        combo.setCurrentIndex(i if i >= 0 else 0)
        combo.blockSignals(False)

    def on_change(_i=0):
        name = combo.currentData()
        apply(available().get(name, {"name": BUILTIN}))
        try:
            choice_file.write_text(name or BUILTIN, encoding="utf-8")
        except OSError:
            pass

    def do_import():
        path, _ = QFileDialog.getOpenFileName(window, "Preset de tema de Blender", "", "Tema Blender (*.xml)")
        if not path:
            return
        try:
            name = import_blender_xml(path)
        except Exception as ex:      # xml invalido, sin colores, etc.
            QMessageBox.warning(window, "Importar tema", str(ex))
            return
        fill(name)
        on_change()

    imp = QAction("Importar tema Blender (.xml)", window)
    imp.setToolTip("Importar tema de Blender (.xml)")
    imp.triggered.connect(lambda _c=False: do_import())
    tb.addAction(imp)
    window.addAction(imp)

    def do_delete():
        name = combo.currentData()
        if not name or name == BUILTIN:
            QMessageBox.information(window, "Eliminar tema", "El tema integrado no se puede eliminar.")
            return
        target = None
        for f in sorted(DIR.glob("*.json")):
            try:
                if json.loads(f.read_text(encoding="utf-8")).get("name", f.stem) == name:
                    target = f
                    break
            except Exception:
                continue
        if target is None:
            return
        ok = QMessageBox.question(window, "Eliminar tema", f"¿Eliminar el tema \"{name}\"?\n({target.name})")
        if ok != QMessageBox.Yes:
            return
        try:
            target.unlink()
        except OSError as ex:
            QMessageBox.warning(window, "Eliminar tema", str(ex))
            return
        fill(BUILTIN)
        on_change()

    dele = QAction("Eliminar tema", window)
    dele.setToolTip("Eliminar el tema seleccionado (se puede volver a importar del .xml)")
    dele.triggered.connect(lambda _c=False: do_delete())
    tb.addAction(dele)
    window.addAction(dele)

    try:
        saved = choice_file.read_text(encoding="utf-8").strip()
    except OSError:
        saved = BUILTIN
    fill(saved)
    combo.currentIndexChanged.connect(on_change)
    if combo.currentData() != BUILTIN:
        on_change()
