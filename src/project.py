"""Guardar y abrir proyectos de Nodo Capture (archivos .nodocap, que son JSON).

Un proyecto guarda los dos editores (Shader y Compositor): cada nodo con su posicion, ancho,
valores, menus, paneles abiertos, Color Ramp e imagen cargada, mas los frames, reroutes y cables.
main.py solo crea el menu Archivo y llama aqui; main_func.py lo hereda sin cambios.
"""
import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMessageBox

APP = "nodo-capture"
VERSION = 1
EXT = ".nodocap"
FILTER = "Proyecto Nodo Capture (*.nodocap);;Todos los archivos (*)"
TITLE = "Nodo Capture"


def _M(win):
    """Modulo donde vive la clase Window (main o __main__), igual que hace themes.py."""
    return sys.modules[type(win).__module__]


def _plain(v):
    """Convierte a tipos que JSON entiende (listas, dicts, numeros, texto)."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_plain(x) for x in v]
    return str(v)


def _spec(M, mode, idname):
    return next((s for s in M.CATALOG[mode] if s["idname"] == idname), None)


# ------------------------------------------------------------ escena <-> dict
def _items(M, sc):
    """Nodos, reroutes y frames de la escena, en orden de apilado (de abajo hacia arriba)."""
    return [i for i in sc.items(Qt.AscendingOrder)
            if isinstance(i, (M.NodeItem, M.RerouteItem, M.FrameItem))]


def _node_to_dict(M, mode, n):
    d = {"id": n.spec["idname"], "x": n.pos().x(), "y": n.pos().y()}
    if isinstance(n, M.FrameItem):
        d.update(w=n.w, h=n.h, label=n.label)
        return d
    if isinstance(n, M.RerouteItem):
        return d
    d["w"] = n.w
    d["vals"] = _plain(n.vals)
    d["pvals"] = _plain(n.pvals)
    if n.hide_unused:
        d["hide_unused"] = True
    if n.panel_open:
        d["panel_open"] = {str(k): bool(v) for k, v in n.panel_open.items()}
    if n.ramp is not None:
        d["ramp"] = _plain(n.ramp)
    if n.img_loaded is not None:
        d["img"] = _plain(n.img_loaded)
    base = _spec(M, mode, d["id"])
    if base is not None:   # valores propios de las salidas (p. ej. el color del nodo RGB)
        diff = {}
        for s, b in zip(n.spec["outputs"], base["outputs"]):
            if s.get("default") != b.get("default"):
                diff[s["identifier"]] = _plain(s.get("default"))
        if diff:
            d["out_defaults"] = diff
    return d


def scene_to_dict(M, sc):
    items = _items(M, sc)
    idx = {id(i): k for k, i in enumerate(items)}
    links = []
    for l in sc.links:
        if l.b is None:
            continue
        a, b = idx.get(id(l.a.node)), idx.get(id(l.b.node))
        if a is not None and b is not None:
            links.append([a, l.a.spec["identifier"], b, l.b.spec["identifier"]])
    return {"nodes": [_node_to_dict(M, sc.mode, i) for i in items], "links": links}


def _make(M, mode, d):
    spec = _spec(M, mode, d.get("id"))
    if spec is None:
        return None
    n = M.make_node(spec, mode)
    if isinstance(n, M.FrameItem):
        n.prepareGeometryChange()
        n.w, n.h = float(d.get("w", n.w)), float(d.get("h", n.h))
        n.label = str(d.get("label", n.label))
        return n
    if isinstance(n, M.RerouteItem):
        return n
    n.vals.update(d.get("vals") or {})
    img = d.get("img")
    if isinstance(img, dict):
        if img.get("path"):
            M.IMAGES[img.get("name", "")] = img["path"]
        n.load_image(img.get("name", ""), int(img.get("users", 1)), "", img.get("path"))
    n.pvals.update(d.get("pvals") or {})   # despues de load_image, que reinicia Source / Color Space / Alpha
    n.hide_unused = bool(d.get("hide_unused", False))
    n.panel_open.update({k: bool(v) for k, v in (d.get("panel_open") or {}).items()})
    rp = d.get("ramp")
    if n.ramp is not None and isinstance(rp, dict) and rp.get("stops"):
        rp["active"] = max(0, min(len(rp["stops"]) - 1, int(rp.get("active", 0))))
        n.ramp = rp
    for ident, dv in (d.get("out_defaults") or {}).items():
        for s in n.spec["outputs"]:
            if s["identifier"] == ident:
                s["default"] = dv
    if "w" in d:
        n.w = float(d["w"])
    n.relayout()
    return n


def clear_scene(sc):
    for it in list(sc.items()):
        if it.parentItem() is None and it.scene() is sc:
            sc.removeItem(it)
    sc.links.clear()
    sc.temp = None
    sc.drag_src = None


def scene_from_dict(M, sc, data):
    """Vacia la escena y la rellena con `data`. Devuelve cuantos nodos no se pudieron crear."""
    clear_scene(sc)
    made, skipped = [], 0
    for d in data.get("nodes", []):
        try:
            n = _make(M, sc.mode, d)
        except Exception:
            n = None
        if n is None:
            skipped += 1
            made.append(None)
            continue
        n.setPos(QPointF(float(d.get("x", 0)), float(d.get("y", 0))))
        sc.addItem(n)
        made.append(n)
    for lk in data.get("links", []):
        try:
            a, aid, b, bid = lk
            o, i = made[a].socks.get(("out", aid)), made[b].socks.get(("in", bid))
        except (ValueError, TypeError, IndexError, AttributeError):
            continue
        if o is None or i is None:
            continue
        link = M.LinkItem(o, i)
        sc.addItem(link)
        sc.links.append(link)
    sc.sync()
    return skipped


# ------------------------------------------------------------ proyecto completo
def to_dict(win):
    M = _M(win)
    view = win.view
    c = view.mapToScene(view.viewport().rect().center())
    return {"app": APP, "version": VERSION, "mode": win.mode.currentData(),
            "scale": win.scale_spin.value(),
            "view": {"zoom": view.transform().m11(), "center": [c.x(), c.y()]},
            "scenes": {m: scene_to_dict(M, sc) for m, sc in win.scenes.items()}}


def snapshot(win):
    """Texto que describe el contenido (sin la vista); sirve para saber si hay cambios sin guardar."""
    M = _M(win)
    return json.dumps({m: scene_to_dict(M, sc) for m, sc in win.scenes.items()}, sort_keys=True)


def write(win, path):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(to_dict(win), ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)   # asi un fallo a medias no deja el proyecto anterior a medio escribir


def _apply_view(win, view):
    try:
        z = float(view["zoom"])
        cx, cy = view["center"]
        if not 0.01 < z < 100:
            raise ValueError
        win.view.resetTransform()
        win.view.scale(z, z)
        win.view.centerOn(QPointF(float(cx), float(cy)))
    except (KeyError, TypeError, ValueError):
        r = win.cur.itemsBoundingRect()
        if not r.isNull():
            win.view.centerOn(r.center())


def read_into(win, path):
    """Carga el proyecto en la ventana. Lanza ValueError/OSError si el archivo no sirve.
    Devuelve cuantos nodos se omitieron (tipos que esta version no conoce)."""
    M = _M(win)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("app") != APP or not isinstance(data.get("scenes"), dict):
        raise ValueError("Ese archivo no es un proyecto de Nodo Capture.")
    skipped = 0
    for mode, sc in win.scenes.items():
        skipped += scene_from_dict(M, sc, data["scenes"].get(mode) or {})
    try:
        win.scale_spin.setValue(int(data.get("scale", win.scale_spin.value())))
    except (TypeError, ValueError):
        pass
    i = win.mode.findData(data.get("mode"))
    if i >= 0:
        win.mode.setCurrentIndex(i)
    _apply_view(win, data.get("view") or {})
    return skipped


# ------------------------------------------------------------ interfaz (menu Archivo)
def update_title(win):
    try:
        dirty = snapshot(win) != win._snap
    except Exception:
        return
    name = Path(win.project_path).name if win.project_path else "Sin título"
    t = f"{'*' if dirty else ''}{name} - {TITLE}"
    if win.windowTitle() != t:
        win.setWindowTitle(t)


def _mark_clean(win, path):
    win.project_path = path
    win._snap = snapshot(win)
    update_title(win)


def confirm_discard(win):
    """True si se puede seguir (no habia cambios, se guardaron o se decidio descartarlos)."""
    if snapshot(win) == win._snap:
        return True
    r = QMessageBox.question(win, "Cambios sin guardar", "El proyecto tiene cambios sin guardar.\n¿Quieres guardarlos?",
                             QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
    if r == QMessageBox.Cancel:
        return False
    if r == QMessageBox.Save:
        return save(win)
    return True


def save(win):
    if not win.project_path:
        return save_as(win)
    try:
        write(win, win.project_path)
    except OSError as ex:
        QMessageBox.warning(win, "Guardar proyecto", f"No se pudo guardar:\n{ex}")
        return False
    _mark_clean(win, win.project_path)
    return True


def save_as(win):
    start = win.project_path or str(Path.home() / ("proyecto" + EXT))
    path, _ = QFileDialog.getSaveFileName(win, "Guardar proyecto", start, FILTER)
    if not path:
        return False
    if not Path(path).suffix:
        path += EXT
    try:
        write(win, path)
    except OSError as ex:
        QMessageBox.warning(win, "Guardar proyecto", f"No se pudo guardar:\n{ex}")
        return False
    _mark_clean(win, path)
    return True


def load_path(win, path):
    try:
        skipped = read_into(win, path)
    except (OSError, ValueError, KeyError, TypeError) as ex:
        QMessageBox.warning(win, "Abrir proyecto", f"No se pudo abrir el proyecto:\n{ex}")
        return False
    _mark_clean(win, str(path))
    if skipped:
        QMessageBox.information(win, "Abrir proyecto",
                                f"{skipped} nodo(s) no existen en esta versión del programa y se omitieron.")
    return True


def open_(win):
    if not confirm_discard(win):
        return
    start = str(Path(win.project_path).parent) if win.project_path else str(Path.home())
    path, _ = QFileDialog.getOpenFileName(win, "Abrir proyecto", start, FILTER)
    if path:
        load_path(win, path)


def new(win):
    if not confirm_discard(win):
        return
    for sc in win.scenes.values():
        clear_scene(sc)
        sc.sync()
    _mark_clean(win, None)


def init(win):
    """Crea el menu Archivo (Nuevo, Abrir, Guardar, Guardar como) y el aviso de cambios sin guardar."""
    win.project_path = None
    win._snap = snapshot(win)
    menu = win.menuBar().addMenu("&Archivo")
    for text, key, fn in (("Nuevo", "Ctrl+N", new), ("Abrir...", "Ctrl+O", open_),
                          ("Guardar", "Ctrl+S", save), ("Guardar como...", "Ctrl+Shift+S", save_as)):
        a = QAction(text, win)
        a.setShortcut(key)
        a.triggered.connect(lambda _c=False, f=fn: f(win))
        menu.addAction(a)
    win._proj_timer = QTimer(win)
    win._proj_timer.timeout.connect(lambda: update_title(win))
    win._proj_timer.start(1000)
    update_title(win)
