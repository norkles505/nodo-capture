import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtWidgets import QApplication
app = QApplication([])
import main

ok = True


def check(label, cond, extra=""):
    global ok
    ok &= bool(cond)
    print(("OK   " if cond else "FAIL ") + label, extra)


def mk(mode, idn):
    s = next(x for x in main.CATALOG[mode] if x["idname"] == idn)
    return main.NodeItem(s, main.category(idn, mode))


def menus(n):
    return [r["name"] for r in n.rows if r.get("ref") and r["ref"][0] == "p"]


def names(n, key):
    return [s["name"] for s in n.spec[key] if n._visible(s, n.lin_in if key == "inputs" else n.lin_out)]


def setp(n, **kw):
    n.pvals.update(kw)
    n.relayout()


for kind in ("Combine", "Separate"):
    n = mk("compositor", f"CompositorNode{kind}Color")
    key = "inputs" if kind == "Combine" else "outputs"
    check(f"{kind} RGB: solo Mode", menus(n) == ["Mode"], menus(n))
    check(f"{kind} RGB canales", names(n, key)[:3] == ["Red", "Green", "Blue"], names(n, key))
    h_rgb = n.h
    setp(n, mode="HSV")
    check(f"{kind} HSV canales", names(n, key)[:3] == ["Hue", "Saturation", "Value"], names(n, key))
    setp(n, mode="HSL")
    check(f"{kind} HSL canales", names(n, key)[:3] == ["Hue", "Saturation", "Lightness"], names(n, key))
    setp(n, mode="YUV")
    check(f"{kind} YUV canales", names(n, key)[:3] == ["Y", "U", "V"], names(n, key))
    check(f"{kind} YUV: sin Color Space", menus(n) == ["Mode"], menus(n))
    setp(n, mode="YCC")
    check(f"{kind} YCC canales", names(n, key)[:3] == ["Y", "Cb", "Cr"], names(n, key))
    check(f"{kind} YCC: Mode y Color Space", menus(n) == ["Mode", "Color Space"], menus(n))
    check(f"{kind} YCC crece", n.h > h_rgb, (h_rgb, n.h))

# el nodo de Shader sigue igual
n = mk("shader", "ShaderNodeCombineColor")
setp(n, mode="HSV")
check("Shader Combine HSV", names(n, "inputs")[:3] == ["Hue", "Saturation", "Value"], names(n, "inputs"))
print("RESULTADO:", "TODO OK" if ok else "HAY FALLOS")
