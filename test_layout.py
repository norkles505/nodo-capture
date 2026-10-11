"""Prueba Reroute y Frame: tipos, cadenas, calculo a traves del reroute, validacion y arrastre del frame."""
import os, sys, traceback
os.environ["QT_QPA_PLATFORM"] = "offscreen"
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QRectF, QPointF
app = QApplication([])
import main as M
import main_func  # aplica el parche de calculo (no abre la ventana)

out = []


def log(*a):
    out.append(" ".join(str(x) for x in a))


def spec(mode, idn):
    return next(s for s in M.CATALOG[mode] if s["idname"] == idn)


def sock(n, kind):
    return next(s for (k, _), s in n.socks.items() if k == kind)


try:
    for mode in ("compositor", "shader"):
        log(mode, "tiene Frame/Reroute:", all(any(s["idname"] == i for s in M.CATALOG[mode])
                                              for i in ("NodeFrame", "NodeReroute")))

    sc = M.NodeScene("shader")
    val = M.make_node(spec("shader", "ShaderNodeValue"), "shader")
    mth = M.make_node(spec("shader", "ShaderNodeMath"), "shader")
    r1 = M.make_node(spec("shader", "NodeReroute"), "shader")
    r2 = M.make_node(spec("shader", "NodeReroute"), "shader")
    bsdf = M.make_node(spec("shader", "ShaderNodeBsdfDiffuse"), "shader")
    for i, n in enumerate((val, r1, r2, mth)):
        n.setPos(i * 160, 40)
        sc.addItem(n)
    bsdf.setPos(0, 300)
    sc.addItem(bsdf)
    log("clases:", type(r1).__name__, type(mth).__name__)

    # Value -> R1 -> R2 -> Math(entrada 1)
    min1 = next(s for (k, ident), s in mth.socks.items() if k == "in" and ident == mth.spec["inputs"][0]["identifier"])
    sc.connect_socks(sock(val, "out"), sock(r1, "in"))
    sc.connect_socks(sock(r1, "out"), sock(r2, "in"))
    sc.connect_socks(sock(r2, "out"), min1)
    log("cables:", len(sc.links), "| tipo r1:", r1.eff, "| tipo r2:", r2.eff)
    log("resultado Math atraviesa reroutes:", getattr(mth, "results", None))

    # un SHADER no debe poder entrar por un reroute a un socket de valor
    before = len(sc.links)
    sc.connect_socks(sock(bsdf, "out"), sock(r1, "in"))          # r1 ya tiene entrada -> la reemplaza (VALUE->SHADER)
    log("SHADER -> reroute que ya alimenta un valor, cables:", before, "->", len(sc.links), "(si no cambia o se rechaza es correcto)")

    # Frame: arrastra lo que contiene
    fr = M.make_node(spec("shader", "NodeFrame"), "shader")
    fr.setPos(-20, -20)
    sc.addItem(fr)
    fr.w, fr.h = 700.0, 330.0
    fr._grab_kids()
    kids = len(fr._kids)
    p0 = {id(n): QPointF(n.pos()) for n in (val, r1, r2, mth)}
    fr.setPos(fr.pos() + QPointF(100, 50))
    moved = all(abs((n.pos() - p0[id(n)]).x() - 100) < 0.01 and abs((n.pos() - p0[id(n)]).y() - 50) < 0.01
                for n in (val, r1, r2, mth))
    log("frame arrastra hijos:", kids, "hijos | todos se movieron igual:", moved,
        "| bsdf (fuera) sin mover:", bsdf.pos().y() == 300)

    # dibujo y exportacion
    rect = sc.itemsBoundingRect().adjusted(-24, -24, 24, 24)
    img = QImage(int(rect.width() * 2), int(rect.height() * 2), QImage.Format_ARGB32)
    img.fill(M.BG)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    sc.render(p, QRectF(img.rect()), rect)
    p.end()
    img.save(os.path.join(here, "out_layout.png"))
    log("render ok:", img.width(), "x", img.height())

    # borrar reroute y frame
    sc.clearSelection()
    r2.setSelected(True)
    fr.setSelected(True)
    sc.delete_selected()
    log("tras borrar r2 y frame -> cables:", len(sc.links), "| layout items:", len(sc.layout_items()))
    log("RESULTADO: OK")
except Exception:
    log("ERROR:\n" + traceback.format_exc())

open(os.path.join(here, "res_layout.txt"), "w", encoding="utf-8").write("\n".join(out))
print("listo")
