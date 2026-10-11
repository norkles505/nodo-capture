import os, sys, traceback
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
out = open(os.path.join(HERE, "res_ancho.txt"), "w", encoding="utf-8")
def log(*a): print(*a, file=out, flush=True)
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QPointF
    from PySide6.QtTest import QTest
    import main
    app = QApplication(sys.argv)
    win = main.Window(); win.resize(1000, 700); win.show()
    win.mode.setCurrentIndex(list(main.CATALOG).index("compositor"))
    sc = win.cur; view = win.view
    spec = {s["idname"]: s for s in main.CATALOG["compositor"]}
    n = main.make_node(spec["CompositorNodeImage"], "compositor"); n.setPos(100, 100); sc.addItem(n)
    m = main.make_node(spec["CompositorNodeViewer"], "compositor"); m.setPos(400, 100); sc.addItem(m)
    sc.connect_socks(n.socks[("out", "Image")], next(s for k, s in m.socks.items() if k[0] == "in"))
    sc.sync(); app.processEvents()
    log("limites Image:", n.width_limits(), "| ancho inicial:", n.w, "| alto:", round(n.h, 1))
    def vp(sx, sy):
        return view.mapFromScene(QPointF(sx, sy))
    def drag(x0, y0, x1, y1):
        QTest.mousePress(view.viewport(), Qt.LeftButton, Qt.NoModifier, vp(x0, y0))
        steps = 6
        for i in range(1, steps + 1):
            QTest.mouseMove(view.viewport(), vp(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps))
            app.processEvents()
        QTest.mouseRelease(view.viewport(), Qt.LeftButton, Qt.NoModifier, vp(x1, y1))
        app.processEvents()
    ylow = 100 + n.h - 10        # zona baja, sin sockets
    log("borde detectado r/l:", n._edge_at(QPointF(n.w, 120)), n._edge_at(QPointF(0, 120)), "| centro:", n._edge_at(QPointF(70, 120)))
    # 1) borde derecho +60
    x_right = 100 + n.w
    drag(x_right, ylow, x_right + 60, ylow)
    log("tras arrastrar derecha +60 -> ancho:", round(n.w, 1), "| x:", n.pos().x(), "| esperado 200 / 100")
    # 2) borde izquierdo -40: ancho +40 y borde derecho fijo
    right_before = n.pos().x() + n.w
    drag(n.pos().x(), ylow, n.pos().x() - 40, ylow)
    log("tras arrastrar izquierda -40 -> ancho:", round(n.w, 1), "| x:", round(n.pos().x(), 1),
        "| borde derecho antes/despues:", round(right_before, 1), round(n.pos().x() + n.w, 1))
    # 3) limites
    drag(n.pos().x() + n.w, ylow, n.pos().x() + n.w + 2000, ylow)
    log("estirar de mas -> ancho:", round(n.w, 1), "(max", n.width_limits()[1], ")")
    drag(n.pos().x() + n.w, ylow, n.pos().x() - 500, ylow)
    log("encoger de mas -> ancho:", round(n.w, 1), "(min", n.width_limits()[0], ")")
    # 4) el cable sigue pegado al socket de salida
    l = sc.links[0]
    sp = n.socks[("out", "Image")].scenePos()
    log("cable: inicio", [round(v, 1) for v in (l.path().pointAtPercent(0).x(), l.path().pointAtPercent(0).y())],
        "| socket", [round(sp.x(), 1), round(sp.y(), 1)])
    # 5) mover el nodo por el centro sigue funcionando
    px = n.pos().x()
    drag(n.pos().x() + n.w / 2, 100 + 8, n.pos().x() + n.w / 2 + 50, 108)
    log("mover por la cabecera -> x:", round(px, 1), "->", round(n.pos().x(), 1), "| ancho sin cambio:", round(n.w, 1))
    # 6) nodo con imagen cargada
    k = main.make_node(spec["CompositorNodeImage"], "compositor"); k.setPos(100, 400); sc.addItem(k)
    k.load_image("Multiple Images.png", 3); k.set_width(232)
    log("Multiple Images ancho 232 -> alto:", k.h, "| filas:", [r["k"] for r in k.rows])
    sc.sync()
    win.export("png", False, path=os.path.join(HERE, "data", "test_ancho.png"))
    log("FIN")
except Exception:
    log("ERROR"); log(traceback.format_exc())
out.close()
