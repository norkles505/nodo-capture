import os, sys, traceback
os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
out = open(os.path.join(HERE, "res_nuevos.txt"), "w", encoding="utf-8")
def log(*a):
    print(*a, file=out, flush=True)

NUEVOS = {
 "shader": ["FunctionNodeInputBool","FunctionNodeInputInt","FunctionNodeInputMenu","FunctionNodeInputVector",
            "GeometryNodeInputSceneTime","GeometryNodeMenuSwitch","GeometryNodeRepeatInput","GeometryNodeRepeatOutput",
            "NodeClosureInput","NodeClosureOutput","NodeCombineBundle","NodeEvaluateClosure","NodeJoinBundle","NodeSeparateBundle"],
 "compositor": ["NodeEnableOutput","ShaderNodeMixRGB","ShaderNodeRGBCurve"],
}
try:
    from PySide6.QtWidgets import QApplication
    import main
    app = QApplication(sys.argv)
    w = main.Window()
    w.scale_spin.setValue(1)
    log("modos en CATALOG:", {k: len(v) for k, v in main.CATALOG.items()})
    for idx, (mode, specs) in enumerate(main.CATALOG.items()):
        by = {s["idname"]: s for s in specs}
        sc = w.scenes[mode]
        faltan = [i for i in NUEVOS.get(mode, []) if i not in by]
        log(mode, "-> nuevos que NO llegan al CATALOG:", faltan)
        # 1) crear TODOS los nodos para detectar fallos
        fallos = 0
        for s in specs:
            try:
                n = main.NodeItem(s, main.category(s["idname"], mode))
                n.relayout() if hasattr(n, "relayout") else None
            except Exception:
                fallos += 1
                log("FAIL", mode, s["idname"]); log(traceback.format_exc())
        log(mode, "creados:", len(specs) - fallos, "de", len(specs))
        # 2) dibujar los nuevos
        x = 0
        for idn in NUEVOS.get(mode, []):
            if idn not in by: continue
            try:
                n = main.NodeItem(by[idn], main.category(idn, mode))
                n.setPos(x, 0); x += n.w + 60
                sc.addItem(n)
                log("  OK", idn, "ancho", round(n.w, 1), "alto", round(n.h, 1), "categoria", main.category(idn, mode))
            except Exception:
                log("  FAIL dibujo", idn); log(traceback.format_exc())
        sc.sync()
        w.mode.setCurrentIndex(idx)
        w.export("png", False, path=os.path.join(HERE, "data", f"test_nuevos_{mode}.png"))
        log(mode, "PNG exportado")
    log("FIN")
except Exception:
    log("ERROR GENERAL"); log(traceback.format_exc())
out.close()
