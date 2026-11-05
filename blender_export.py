"""Pasar el arbol de nodos de Nodo Capture a Blender (boton "Copiar para Blender").

Blender no tiene un formato de portapapeles para nodos que se pueda generar desde fuera, asi que
se copia un script de Python autocontenido: en Blender se pega en el Text Editor y se ejecuta
(Alt+P); el script crea los nodos, sus valores, los cables, los frames y los reroutes.

Funciona con el editor activo (Shader -> material del objeto activo, Compositor -> compositor de
la escena). Si hay nodos seleccionados se copian solo esos (como Ctrl+C en Blender); si no hay
seleccion se copia todo el arbol.

main.py solo llama a  blender_export.init(ventana);  main_func.py lo hereda sin cambios.
"""
import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QToolBar

SKIP_PROPS = {"is_active_output", "use_custom_color"}
RAMP_INTERP = {"Ease": "EASE", "Cardinal": "CARDINAL", "B-Spline": "B_SPLINE",
               "Linear": "LINEAR", "Constant": "CONSTANT"}


def _M(win):
    """Modulo donde vive la clase Window (main o __main__), igual que hace project.py."""
    return sys.modules[type(win).__module__]


def _plain(v):
    """Convierte a tipos que JSON entiende."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_plain(x) for x in v]
    return str(v)


def _base_spec(M, mode, idname):
    return next((s for s in M.CATALOG[mode] if s["idname"] == idname), None)


# ------------------------------------------------------------ escena -> datos
def _rect(M, it):
    """(x, y, ancho, alto) del elemento en coordenadas de escena."""
    x, y = it.pos().x(), it.pos().y()
    if isinstance(it, M.RerouteItem):
        return (x - it.R, y - it.R, 2 * it.R, 2 * it.R)
    return (x, y, it.w, it.h)


def _contains(a, b):
    return a[0] <= b[0] and a[1] <= b[1] and a[0] + a[2] >= b[0] + b[2] and a[1] + a[3] >= b[1] + b[3]


def _entry(M, mode, n):
    d = {"id": n.spec["idname"], "x": n.pos().x(), "y": n.pos().y()}
    if isinstance(n, M.FrameItem):
        d.update(t="frame", w=n.w, h=n.h, label=n.label)
        return d
    if isinstance(n, M.RerouteItem):
        d["t"] = "reroute"
        return d
    d.update(t="node", w=n.w)
    base = _base_spec(M, mode, d["id"])
    base_p = {p["id"]: p.get("value") for p in base["props"]} if base else {}
    props = {}
    for k, v in n.pvals.items():
        if k.startswith("_") or k in SKIP_PROPS or v is None or v == "":
            continue
        if k in base_p and base_p[k] == v:
            continue                      # igual que el valor por defecto de Blender: no hace falta tocarlo
        props[k] = _plain(v)
    base_in = {s["identifier"]: s.get("default") for s in base["inputs"]} if base else {}
    in_ids = {s["identifier"] for s in n.spec["inputs"]}
    out_ids = {s["identifier"] for s in n.spec["outputs"]}
    ins, outs = {}, {}
    if base:                              # valores propios de las salidas (color del nodo RGB, numero del nodo Value)
        for s, b in zip(n.spec["outputs"], base["outputs"]):
            if s.get("default") is not None and s.get("default") != b.get("default"):
                outs[s["identifier"]] = _plain(s["default"])
    for ident, v in n.vals.items():
        if v is None:
            continue
        if ident not in in_ids and ident in out_ids:
            outs[ident] = _plain(v)       # main_func.py guarda el numero del nodo Value en vals, con el id de la salida
            continue
        if ident in base_in and base_in[ident] == v:
            continue
        ins[ident] = _plain(v)
    d.update(props=props, inputs=ins, outputs=outs)
    if n.ramp is not None:
        stops = sorted(n.ramp["stops"], key=lambda s: s["pos"])
        d["ramp"] = {"cmode": n.ramp.get("cmode", "RGB"),
                     "interp": RAMP_INTERP.get(n.ramp.get("interp"), "LINEAR"),
                     "stops": [{"pos": float(s["pos"]), "color": _plain(s["color"])} for s in stops]}
    if n.img_loaded is not None and n.img_loaded.get("path"):
        d["img"] = str(n.img_loaded["path"])
    if n.hide_unused:
        d["hide_unused"] = True
    return d


def payload(M, sc):
    """Datos del arbol (o de la seleccion) listos para el script. Devuelve (datos, usa_seleccion)."""
    items = [i for i in sc.items(Qt.AscendingOrder)
             if isinstance(i, (M.NodeItem, M.RerouteItem, M.FrameItem))]
    sel = [i for i in items if i.isSelected()]
    if sel:
        items = sel
    idx = {id(i): k for k, i in enumerate(items)}
    nodes = [_entry(M, sc.mode, i) for i in items]
    rects = [_rect(M, i) for i in items]
    frames = [k for k, i in enumerate(items) if isinstance(i, M.FrameItem)]
    for k, e in enumerate(nodes):         # un nodo dentro de un frame pasa a ser hijo de ese frame
        best = None
        for f in frames:
            if f != k and _contains(rects[f], rects[k]):
                if best is None or rects[f][2] * rects[f][3] < rects[best][2] * rects[best][3]:
                    best = f
        if best is not None:
            e["parent"] = best
    links = []
    for l in sc.links:
        if l.b is None:
            continue
        a, b = idx.get(id(l.a.node)), idx.get(id(l.b.node))
        if a is not None and b is not None:
            links.append([a, l.a.spec["identifier"], b, l.b.spec["identifier"]])
    return {"nodes": nodes, "links": links}, bool(sel)


TEMPLATE = r'''# Nodo Capture -> Blender
# Como usarlo: en Blender abre la pestana "Scripting", pulsa "New" en el Text Editor,
# pega esto (Ctrl+V) y pulsa "Run Script" (Alt+P). Los nodos aparecen en el editor.
import json
import os

import bpy

MODE = "__MODE__"      # "shader" = material del objeto activo, "compositor" = compositor de la escena
REPLACE = False        # True = borra los nodos que ya hay en el destino antes de pegar
DATA = json.loads(__DATA__)

_warn = []


def _try(what, fn):
    try:
        fn()
    except Exception as ex:
        _warn.append("%s: %s" % (what, ex))


def get_tree():
    """Devuelve (arbol de nodos, es_nuevo)."""
    if MODE == "compositor":
        scene = bpy.context.scene
        if hasattr(scene, "compositing_node_group"):          # Blender 5.x
            tree = scene.compositing_node_group
            if tree is None:
                tree = bpy.data.node_groups.new("Compositing Nodetree", "CompositorNodeTree")
                scene.compositing_node_group = tree
                return tree, True
            return tree, False
        if not scene.use_nodes:
            scene.use_nodes = True
            return scene.node_tree, True
        return scene.node_tree, False
    obj = bpy.context.view_layer.objects.active
    mat = obj.active_material if obj is not None else None
    fresh = False
    if mat is None:
        mat = bpy.data.materials.new("Nodo Capture")
        fresh = True
        if obj is not None and hasattr(obj.data, "materials"):
            if obj.material_slots:
                obj.active_material = mat
            else:
                obj.data.materials.append(mat)
    if mat.node_tree is None or not getattr(mat, "use_nodes", True):
        mat.use_nodes = True
        fresh = True
    return mat.node_tree, fresh


def sock(coll, ident, node):
    for s in coll:
        if s.identifier == ident:
            return s
    if node.bl_idname == "NodeReroute" and len(coll):
        return coll[0]
    return None


def set_ramp(n, rp):
    cr = n.color_ramp
    _try("modo del Color Ramp", lambda: setattr(cr, "color_mode", rp["cmode"]))
    _try("interpolacion del Color Ramp", lambda: setattr(cr, "interpolation", rp["interp"]))
    while len(cr.elements) > 1:
        cr.elements.remove(cr.elements[-1])
    st = rp["stops"]
    first = cr.elements[0]
    first.position = st[0]["pos"]
    first.color = st[0]["color"]
    for s in st[1:]:                  # en orden ascendente: cada marcador nuevo queda al final
        e = cr.elements.new(s["pos"])
        e.color = s["color"]


def setup(n, it):
    kind = it["t"]
    if kind == "frame":
        n.label = it.get("label", "")
        _try("Frame: auto-ajuste", lambda: setattr(n, "shrink", False))
        _try("Frame: ancho", lambda: setattr(n, "width", it["w"]))
        _try("Frame: alto", lambda: setattr(n, "height", it["h"]))
        return
    if kind == "reroute":
        return
    if it.get("w"):
        _try("ancho de %s" % it["id"], lambda: setattr(n, "width", it["w"]))
    for k, v in it.get("props", {}).items():
        _try("%s.%s" % (it["id"], k), lambda k=k, v=v: setattr(n, k, v))
    for ident, v in it.get("inputs", {}).items():
        s = sock(n.inputs, ident, n)
        if s is None:
            _warn.append("%s: no hay entrada '%s'" % (it["id"], ident))
            continue
        _try("%s.%s" % (it["id"], ident), lambda s=s, v=v: setattr(s, "default_value", v))
    for ident, v in it.get("outputs", {}).items():
        s = sock(n.outputs, ident, n)
        if s is not None and hasattr(s, "default_value"):
            _try("%s salida %s" % (it["id"], ident), lambda s=s, v=v: setattr(s, "default_value", v))
    if it.get("ramp") and hasattr(n, "color_ramp"):
        _try("Color Ramp", lambda: set_ramp(n, it["ramp"]))
    path = it.get("img")
    if path and hasattr(n, "image"):
        if os.path.exists(path):
            _try("imagen %s" % path, lambda: setattr(n, "image", bpy.data.images.load(path, check_existing=True)))
        else:
            _warn.append("imagen no encontrada: %s" % path)


def build():
    tree, fresh = get_tree()
    nodes = tree.nodes
    if fresh or REPLACE:
        nodes.clear()
    items = DATA["nodes"]
    dx = 0.0
    top = [n for n in nodes if n.parent is None]
    if top and items:                 # si ya hay nodos, se pega a su derecha para no taparlos
        dx = max(n.location.x + n.width for n in top) + 100.0 - min(it["x"] for it in items)
    for n in nodes:
        n.select = False
    made = []
    for it in items:
        try:
            n = nodes.new(it["id"])
        except Exception as ex:
            _warn.append("no se pudo crear %s (%s)" % (it["id"], ex))
            made.append(None)
            continue
        made.append(n)
        setup(n, it)
    for i, it in enumerate(items):    # primero los padres, despues las posiciones (son relativas al padre)
        p = it.get("parent")
        if made[i] is not None and p is not None and made[p] is not None:
            made[i].parent = made[p]
    for i, it in enumerate(items):
        n = made[i]
        if n is None:
            continue
        x, y = it["x"] + dx, -it["y"]           # en Blender la Y crece hacia arriba
        p = it.get("parent")
        if p is not None and made[p] is not None:
            x -= items[p]["x"] + dx
            y -= -items[p]["y"]
        n.location = (x, y)
        n.select = True
    for a, aid, b, bid in DATA["links"]:
        na, nb = made[a], made[b]
        if na is None or nb is None:
            continue
        so, si = sock(na.outputs, aid, na), sock(nb.inputs, bid, nb)
        if so is None or si is None:
            _warn.append("cable perdido: %s.%s -> %s.%s" % (items[a]["id"], aid, items[b]["id"], bid))
            continue
        _try("cable", lambda so=so, si=si: tree.links.new(so, si))
    for i, it in enumerate(items):    # "Ocultar sin conectar" (Ctrl+H)
        n = made[i]
        if n is not None and it.get("hide_unused"):
            for s in list(n.inputs) + list(n.outputs):
                if not s.is_linked:
                    _try("ocultar socket", lambda s=s: setattr(s, "hide", True))
    return len([n for n in made if n is not None])


def _popup(title, lines):
    def draw(self, context):
        for line in lines:
            self.layout.label(text=line)
    _try("aviso", lambda: bpy.context.window_manager.popup_menu(draw, title=title, icon="INFO"))


count = build()
print("Nodo Capture: %d de %d nodos creados, %d aviso(s)" % (count, len(DATA["nodes"]), len(_warn)))
for w in _warn:
    print("  - " + w)
_popup("Nodo Capture", ["%d nodos pegados." % count] + (["%d aviso(s): mira la consola del sistema." % len(_warn)] if _warn else []))
'''


def build_script(M, sc):
    """Script de Blender para el editor actual. Devuelve (texto, cantidad de nodos, usa_seleccion)."""
    data, used_sel = payload(M, sc)
    text = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    script = TEMPLATE.replace("__MODE__", sc.mode).replace("__DATA__", repr(text))
    return script, len(data["nodes"]), used_sel


# ------------------------------------------------------------ interfaz
def _make(win):
    M = _M(win)
    sc = win.cur
    script, n, used_sel = build_script(M, sc)
    return script, n, used_sel, sc


def copy_script(win):
    script, n, used_sel, sc = _make(win)
    if n == 0:
        win.statusBar().showMessage("No hay nodos para copiar.", 6000)
        return
    QApplication.clipboard().setText(script)
    que = f"{n} nodo(s) seleccionados" if used_sel else f"todo el arbol ({n} nodos)"
    win.statusBar().showMessage(
        f"Copiado para Blender: {que}. En Blender: Scripting > Text Editor > New > Ctrl+V > Run Script (Alt+P).",
        15000)


def save_script(win):
    script, n, used_sel, sc = _make(win)
    if n == 0:
        win.statusBar().showMessage("No hay nodos para guardar.", 6000)
        return
    path, _ = QFileDialog.getSaveFileName(win, "Guardar script para Blender",
                                          str(Path.home() / "nodos_blender.py"), "Python (*.py)")
    if not path:
        return
    try:
        Path(path).write_text(script, encoding="utf-8")
    except OSError as ex:
        QMessageBox.warning(win, "Guardar script", f"No se pudo guardar:\n{ex}")
        return
    win.statusBar().showMessage(f"Script guardado: {path}", 8000)


def init(win):
    """Menu Blender (Copiar para Blender / Guardar script) y boton en la barra de herramientas."""
    menu = win.menuBar().addMenu("&Blender")
    copy = QAction("Copiar para Blender", win)
    copy.setShortcut("Ctrl+Shift+C")
    copy.setToolTip("Copiar los nodos (la seleccion, o todo si no hay seleccion) para pegarlos en Blender (Ctrl+Shift+C)")
    copy.triggered.connect(lambda _c=False: copy_script(win))
    menu.addAction(copy)
    save = QAction("Guardar script para Blender...", win)
    save.triggered.connect(lambda _c=False: save_script(win))
    menu.addAction(save)
    tbs = win.findChildren(QToolBar)
    if tbs:
        tbs[0].addAction(copy)
