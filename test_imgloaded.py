import os, sys, traceback
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
out = open(os.path.join(HERE, "res_imgloaded.txt"), "w", encoding="utf-8")
def log(*a): print(*a, file=out, flush=True)
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontMetrics
    import main
    app = QApplication(sys.argv)
    w = main.Window()
    w.scale_spin.setValue(3)
    sc = w.scenes["compositor"]
    spec = next(s for s in main.CATALOG["compositor"] if s["idname"] == "CompositorNodeImage")
    n = main.make_node(spec, "compositor"); n.setPos(0, 0)
    sc.addItem(n)
    log("antes  -> alto:", round(n.h, 1), "| filas:", [r["k"] for r in n.rows])
    n.load_image("Multiple Images.png", main.MULTI_IMG_USERS)
    log("despues-> alto:", round(n.h, 1), "(real Blender 181.0) | ancho:", n.w)
    log("filas:", [(r["k"], round(r["y"], 1), r.get("name", "")) for r in n.rows])
    log("titulo:", n.title())
    fm = QFontMetrics(main.NodeItem.F)
    log("ancho titulo:", fm.horizontalAdvance(n.title()), "| hueco disponible hasta el ojo:", n.w - 14 - 7 - 26)
    log("sockets visibles:", {k: s.isVisible() for k, s in n.socks.items()})
    for r in n.rows:
        try: log("edit", r["k"], "->", n.edit(r) if r["k"] == "imgloaded" else "omitido")
        except Exception: log("FALLO edit", r["k"], traceback.format_exc())
    # segundo nodo normal al lado para comparar
    n2 = main.make_node(spec, "compositor"); n2.setPos(220, 0); sc.addItem(n2)
    sc.sync()
    w.mode.setCurrentIndex(list(main.CATALOG).index("compositor"))
    w.export("png", False, path=os.path.join(HERE, "data", "test_imgloaded.png"))
    log("PNG exportado: data/test_imgloaded.png")
    log("FIN")
except Exception:
    log("ERROR"); log(traceback.format_exc())
out.close()
