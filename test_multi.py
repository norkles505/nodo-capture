import os, sys, traceback
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
out = open(os.path.join(HERE, "res_multi.txt"), "w", encoding="utf-8")
def log(*a): print(*a, file=out, flush=True)
try:
    from PySide6.QtWidgets import QApplication
    import main
    app = QApplication(sys.argv)
    w = main.Window()
    for mode in ("compositor", "shader"):
        d = main.AddDialog(main.CATALOG[mode] + main.VIRTUAL_ADD)
        for q in ("multiple", "sequence"):
            d.refill(q)
            log(mode, q, "->", [d.lst.item(i).text() for i in range(d.lst.count())])
        idn = main.IMAGE_NODE[mode]
        log(mode, "nodo imagen en CATALOG:", any(s["idname"] == idn for s in main.CATALOG[mode]))
        # simular el reparto de nodos como lo hace add_node (3 imagenes)
        sc = w.scenes[mode]
        spec = next(s for s in main.CATALOG[mode] if s["idname"] == idn)
        y = 0
        for _ in range(3):
            n = main.make_node(spec, mode); n.setPos(0, y); sc.addItem(n); y += n.h + 24
        log(mode, "3 nodos Image creados, alto cada uno:", round(n.h, 1))
    log("FIN")
except Exception:
    log("ERROR"); log(traceback.format_exc())
out.close()
