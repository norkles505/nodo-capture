"""Copiar, pegar y duplicar nodos, como en Blender.

  Ctrl+C            copia los nodos seleccionados (con sus valores, menus, Color Ramp, imagen...)
                    y los cables que hay ENTRE ellos
  Ctrl+V            pega la copia centrada donde esta el cursor (queda seleccionada para moverla)
  Shift+D / Ctrl+D  duplica la seleccion al lado, sin tocar lo que hayas copiado

Reutiliza la misma conversion nodo <-> dict que usa project.py para guardar proyectos, asi que
todo lo que se guarda en un .nodocap tambien se copia. main.py solo llama a init(win).
"""
import copy
import sys

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import QToolTip

import project as P

DUP_OFFSET = 40.0
CLIP = {"mode": None, "nodes": [], "links": [], "rects": []}   # lo ultimo copiado (Ctrl+C)


def _M(win):
    return sys.modules[type(win).__module__]


def _snapshot(win):
    """Describe la seleccion actual: nodos, cables internos y el rectangulo que ocupa cada uno."""
    M, sc = _M(win), win.cur
    items = [i for i in P._items(M, sc) if i.isSelected()]
    if not items:
        return None
    idx = {id(i): k for k, i in enumerate(items)}
    links = []
    for l in sc.links:
        if l.b is None:
            continue
        a, b = idx.get(id(l.a.node)), idx.get(id(l.b.node))
        if a is not None and b is not None:
            links.append([a, l.a.spec["identifier"], b, l.b.spec["identifier"]])
    rects = []
    for i in items:
        if isinstance(i, M.RerouteItem):
            r = i.mapRectToScene(QRectF(-i.R, -i.R, 2 * i.R, 2 * i.R))
        else:
            r = i.mapRectToScene(QRectF(0, 0, i.w, i.h))
        rects.append((r.left(), r.top(), r.right(), r.bottom()))
    return {"mode": sc.mode, "nodes": [P._node_to_dict(M, sc.mode, i) for i in items],
            "links": links, "rects": rects}


def _center(snap):
    r = snap["rects"]
    return QPointF((min(a[0] for a in r) + max(a[2] for a in r)) / 2,
                   (min(a[1] for a in r) + max(a[3] for a in r)) / 2)


def _cursor_pos(win):
    vp = win.view.viewport()
    local = vp.mapFromGlobal(QCursor.pos())
    return win.view.mapToScene(local if vp.rect().contains(local) else vp.rect().center())


def _insert(win, snap, delta):
    """Crea los nodos de `snap` movidos `delta`, los deja seleccionados y rehace los cables."""
    M, sc = _M(win), win.cur
    snap = copy.deepcopy(snap)   # asi se puede pegar muchas veces la misma copia
    made = []
    for d in snap["nodes"]:
        try:
            n = P._make(M, sc.mode, d)
        except Exception:
            n = None
        if n is not None:
            n.setPos(QPointF(float(d.get("x", 0)) + delta.x(), float(d.get("y", 0)) + delta.y()))
        made.append(n)
    if not any(made):
        return False
    sc.clearSelection()
    for n in made:
        if n is not None:
            sc.addItem(n)
            n.setSelected(True)
    for a, aid, b, bid in snap["links"]:
        na, nb = made[a], made[b]
        if na is None or nb is None:
            continue
        o, i = na.socks.get(("out", aid)), nb.socks.get(("in", bid))
        if o is None or i is None:
            continue
        link = M.LinkItem(o, i)
        sc.addItem(link)
        sc.links.append(link)
    sc.sync()
    return True


# ------------------------------------------------------------ acciones
def copy_selected(win):
    snap = _snapshot(win)
    if snap is not None:
        CLIP.update(snap)


def paste(win):
    if not CLIP["nodes"]:
        return
    if CLIP["mode"] != win.cur.mode:
        QToolTip.showText(QCursor.pos(), "Lo copiado es del otro editor (Shader / Compositor).", win.view)
        return
    _insert(win, CLIP, _cursor_pos(win) - _center(CLIP))


def duplicate(win):
    snap = _snapshot(win)
    if snap is not None:
        _insert(win, snap, QPointF(DUP_OFFSET, DUP_OFFSET))


def init(win):
    """Menu Editar con Copiar, Pegar y Duplicar (y sus atajos)."""
    menu = win.menuBar().addMenu("&Editar")
    for text, keys, fn in (("Copiar", ["Ctrl+C"], copy_selected),
                           ("Pegar", ["Ctrl+V"], paste),
                           ("Duplicar", ["Shift+D", "Ctrl+D"], duplicate)):
        a = QAction(text, win)
        a.setShortcuts(keys)
        a.triggered.connect(lambda _c=False, f=fn: f(win))
        menu.addAction(a)
