"""Prueba sin ventana de los temas: aplica cada uno, exporta un PNG y prueba el importador XML."""
import os
import sys
import traceback
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
LOG = HERE / "res_themes.txt"
out = []


def log(*a):
    out.append(" ".join(str(x) for x in a))


try:
    from PySide6.QtWidgets import QApplication
    import main as M
    import themes

    app = QApplication([])
    M.apply_dark(app)
    w = M.Window()
    themes.install(w)
    sc = w.scenes["shader"]
    idn = {s["idname"]: s for s in M.CATALOG["shader"]}
    nodes = []
    for k, name in enumerate(("ShaderNodeValue", "ShaderNodeMath", "ShaderNodeMix")):
        spec = idn.get(name) or M.CATALOG["shader"][k]
        n = M.NodeItem(spec, M.category(spec["idname"], "shader"))
        n.setPos(k * 260, 0)
        sc.addItem(n)
        nodes.append(n)
    o = next(s for (kind, _), s in nodes[0].socks.items() if kind == "out")
    i = next(s for (kind, _), s in nodes[1].socks.items() if kind == "in")
    sc.connect_socks(o, i)
    log("enlaces:", len(sc.links))

    for name, data in themes.available().items():
        themes.apply(data)
        p = HERE / "data" / f"test_theme_{name.replace(' ', '_')}.png"
        w.export("png", False, str(p))
        log("OK", name, "BG=", M.BG.name(), "BODY=", M.BODY.name(), "PNG", p.exists())

    xml = HERE / "zz_test.xml"
    xml.write_text(
        '<bpy><Theme><user_interface><ThemeUserInterface>'
        '<wcol_regular><ThemeWidgetColors outline="#191919" inner="#cccccc" text="#000000" roundness="0.4"/></wcol_regular>'
        '</ThemeUserInterface></user_interface>'
        '<node_editor><ThemeNodeEditor node_backdrop="#9b9b9ba0" wire="#000000" grid="#2d2d2d">'
        '<space><ThemeSpaceGeneric back="#303030"/></space></ThemeNodeEditor></node_editor></Theme></bpy>',
        encoding="utf-8")
    log("import:", themes.import_blender_xml(str(xml)))
    log("temas:", list(themes.available()))
    themes.apply(themes.available()["Zz Test"])
    log("OK importado BG=", M.BG.name())
    xml.unlink()
    (HERE / "data" / "themes" / "zz_test.json").unlink()
    themes.apply({"name": themes.BUILTIN})
    log("BUILTIN BG=", M.BG.name(), "(debe ser #1a1a1a)")
except Exception:
    log("ERROR")
    log(traceback.format_exc())
LOG.write_text("\n".join(out), encoding="utf-8")
