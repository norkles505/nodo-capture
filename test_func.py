"""Prueba sin ventana del modo funcional. Escribe el resultado en out_func.txt."""
import os
import sys
import traceback

os.environ["QT_QPA_PLATFORM"] = "offscreen"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_func.txt")
lines = []


def log(*a):
    lines.append(" ".join(str(x) for x in a))


try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtCore import QRectF
    app = QApplication(sys.argv)
    import main_func as F
    import main as M

    def mk(sc, idn, mode="shader"):
        spec = next(s for s in M.CATALOG[mode] if s["idname"] == idn)
        n = M.NodeItem(spec, M.category(idn, mode))
        sc.addItem(n)
        return n

    def out(n, i=0):
        return n.socks[("out", n.spec["outputs"][i]["identifier"])]

    def inp(n, i):
        return n.socks[("in", n.spec["inputs"][i]["identifier"])]

    sc = M.NodeScene("shader")
    a = mk(sc, "ShaderNodeValue")
    a.vals["Value"] = 2.0
    b = mk(sc, "ShaderNodeValue")
    b.vals["Value"] = 3.5
    m = mk(sc, "ShaderNodeMath")          # ADD por defecto
    sc.connect_socks(out(a), inp(m, 0))
    sc.connect_socks(out(b), inp(m, 1))
    log("links:", len(sc.links), "(esperado 2)")
    log("Value + Value =", m.results, "(esperado 5.5)")

    m.pvals["operation"] = "MULTIPLY"
    sc.sync()
    log("MULTIPLY =", m.results, "(esperado 7.0)")

    # cambiar un valor reevalua
    a.vals["Value"] = 4.0
    sc.recompute()
    log("tras cambiar a=4:", m.results, "(esperado 14.0)")

    # ciclo
    n = len(sc.links)
    sc.connect_socks(out(m), inp(a, 0)) if a.spec["inputs"] else None
    m2 = mk(sc, "ShaderNodeMath")
    sc.connect_socks(out(m), inp(m2, 0))
    sc.connect_socks(out(m2), inp(m, 0))
    log("ciclo rechazado:", len(sc.links) == n + 1, "(esperado True)")

    # Shader vs valor
    em = mk(sc, "ShaderNodeEmission")
    k = len(sc.links)
    sc.connect_socks(out(em), inp(m, 0))
    log("shader->float rechazado:", len(sc.links) == k, "(esperado True)")

    # mezcla de colores
    rgb1 = mk(sc, "ShaderNodeRGB")
    rgb1.spec["outputs"][0]["default"] = [1.0, 0.0, 0.0, 1.0]
    rgb2 = mk(sc, "ShaderNodeRGB")
    rgb2.spec["outputs"][0]["default"] = [0.0, 0.0, 1.0, 1.0]
    mx = mk(sc, "ShaderNodeMix")
    mx.pvals["data_type"] = "RGBA"; mx.vals["Factor_Float"] = 0.5  # el catalogo trae 1.0 por defecto
    sc.sync()
    ids = [(s["identifier"], s.get("stype")) for s in mx.spec["inputs"]]
    log("Mix inputs:", ids)
    ca = next(s for s in mx.spec["inputs"] if s["identifier"].startswith("A") and s["identifier"].endswith("Color"))
    cb = next(s for s in mx.spec["inputs"] if s["identifier"].startswith("B") and s["identifier"].endswith("Color"))
    sc.connect_socks(out(rgb1), mx.socks[("in", ca["identifier"])])
    sc.connect_socks(out(rgb2), mx.socks[("in", cb["identifier"])])
    log("Mix RGBA 50%:", mx.results, "(esperado ~[0.5,0,0.5,1])")

    # render sin errores
    img = QImage(800, 600, QImage.Format_ARGB32)
    p = QPainter(img)
    sc.render(p, QRectF(img.rect()), sc.itemsBoundingRect().adjusted(-20, -20, 20, 20))
    p.end()
    img.save(os.path.join(os.path.dirname(OUT), "out_func.png"))
    log("render OK")

    # compositor
    sc2 = M.NodeScene("compositor")
    vid = "CompositorNodeValue" if any(s["idname"] == "CompositorNodeValue" for s in M.CATALOG["compositor"]) else "CompositorNodeRGB"; log("compositor usa:", vid); v = mk(sc2, vid, "compositor")
    v.vals["Value"] = 0.25
    log("compositor Value fila:", [r["k"] for r in v.rows])
except Exception:
    log("ERROR:\n" + traceback.format_exc())

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
