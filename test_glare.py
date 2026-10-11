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


def mk():
    s = next(x for x in main.CATALOG["compositor"] if x["idname"] == "CompositorNodeGlare")
    return main.NodeItem(s, main.category("CompositorNodeGlare", "compositor"))


def names(n):
    return [s["name"] for s in n.spec["inputs"] if n._visible(s, n.lin_in)]


def panels(n):
    return [r["name"] for r in n.rows if r["k"] == "panel"]


EXPECT = {
    "Streaks": ["Quality", "Threshold", "Smoothness", "Clamp", "Strength", "Saturation", "Tint",
                "Streaks", "Streaks Angle", "Iterations", "Fade", "Color Modulation"],
    "Bloom": ["Quality", "Threshold", "Smoothness", "Clamp", "Strength", "Saturation", "Tint", "Size"],
    "Fog Glow": ["Quality", "Threshold", "Smoothness", "Clamp", "Strength", "Saturation", "Tint", "Size"],
    "Simple Star": ["Quality", "Threshold", "Smoothness", "Clamp", "Strength", "Saturation", "Tint",
                    "Iterations", "Fade", "Diagonal"],
    "Ghosts": ["Quality", "Threshold", "Smoothness", "Clamp", "Strength", "Saturation", "Tint",
               "Iterations", "Color Modulation"],
    "Sun Beams": ["Quality", "Threshold", "Smoothness", "Clamp", "Strength", "Saturation", "Tint",
                  "Size", "Sun Position", "Jitter"],
    "Kernel": ["Quality", "Threshold", "Smoothness", "Clamp", "Strength", "Saturation", "Tint",
               "Kernel Data Type", "Kernel"],
}

n = mk()
print("Type por defecto:", n.vals.get("Type"), "| titulo:", n.title(), "| altura:", round(n.h, 1))
for t, exp in EXPECT.items():
    n.vals["Type"] = t
    n.relayout()
    got = [x for x in names(n) if x not in ("Image", "Type")]
    check(f"Glare {t}: sockets", got == exp, got)
    check(f"Glare {t}: titulo", n.title() == t, n.title())
n.vals["Type"] = "Streaks"
n.relayout()
check("Paneles", panels(n) == ["Highlights", "Adjust", "Glare"], panels(n))
n.vals["Type"] = "Kernel"
n.vals["Kernel Data Type"] = "Color"
n.relayout()
got = names(n)
check("Kernel Color: un solo Kernel", got.count("Kernel") == 1, got)
print("RESULTADO:", "TODO OK" if ok else "HAY FALLOS")
