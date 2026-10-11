import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(__file__))
from PySide6.QtWidgets import QApplication
app = QApplication([])
import main

def mk(idn):
    s = next(x for x in main.CATALOG["shader"] if x["idname"] == idn)
    return main.NodeItem(s, main.category(idn, "shader"))

def vis(n):
    ins = [s["name"] + "(" + s["identifier"] + ")" for s in n.spec["inputs"] if n._visible(s, n.lin_in)]
    outs = [s["name"] for s in n.spec["outputs"] if n._visible(s, n.lin_out)]
    return ins, outs

ok = True
def check(label, cond, extra=""):
    global ok
    ok &= bool(cond)
    print(("OK   " if cond else "FAIL ") + label, extra)

# ---- Map Range
n = mk("ShaderNodeMapRange")
h0 = n.h
i, o = vis(n)
check("MapRange float lineal: 5 entradas", len(i) == 5, i)
n.pvals["interpolation_type"] = "STEPPED"; n.relayout()
i, o = vis(n)
check("MapRange float stepped: 6 entradas (Steps)", len(i) == 6 and any(x.startswith("Steps(") for x in i), i)
check("MapRange stepped crece", n.h > h0, (h0, n.h))
n.pvals["data_type"] = "FLOAT_VECTOR"; n.relayout()
i, o = vis(n)
check("MapRange vector stepped: entradas vectoriales", all("FLOAT3" in x or x.startswith("Vector") for x in i) and len(i) == 6, i)
check("MapRange vector: salida Vector", o == ["Vector"], o)
n.pvals["interpolation_type"] = "LINEAR"; n.relayout()
i, o = vis(n)
check("MapRange vector lineal: 5 entradas", len(i) == 5, i)
# el spec de un nodo no contamina al catalogo ni a otro nodo
n2 = mk("ShaderNodeMapRange")
i2, o2 = vis(n2)
check("MapRange nuevo no hereda cambios", len(i2) == 5 and o2 == ["Result"], (i2, o2))

# ---- Math
m = mk("ShaderNodeMath")
m.pvals["operation"] = "ADD"; m.relayout()
check("Math ADD titulo", m.title() == "Add", m.title())
i, _ = vis(m); check("Math ADD 2 entradas", len(i) == 2, i)
hadd = m.h
m.pvals["operation"] = "SINE"; m.relayout()
i, _ = vis(m); check("Math SINE 1 entrada", len(i) == 1, i)
check("Math SINE mas bajo que ADD", m.h < hadd, (m.h, hadd))
m.pvals["operation"] = "MULTIPLY_ADD"; m.relayout()
i, _ = vis(m); check("Math MULTIPLY_ADD 3 entradas", len(i) == 3, i)
check("Math MULTIPLY_ADD etiquetas", [x.split("(")[0] for x in i] == ["Value", "Multiplier", "Addend"], i)
m.pvals["operation"] = "POWER"; m.relayout()
i, _ = vis(m); check("Math POWER etiquetas", [x.split("(")[0] for x in i] == ["Base", "Exponent"], i)

# ---- Vector Math
v = mk("ShaderNodeVectorMath")
v.pvals["operation"] = "DOT_PRODUCT"; v.relayout()
_, o = vis(v); check("VectorMath DOT salida Value", o == ["Value"], o)
v.pvals["operation"] = "SCALE"; v.relayout()
i, o = vis(v); check("VectorMath SCALE: Vector + Scale", len(i) == 2 and o == ["Vector"], (i, o))

# ---- cambio via sync en escena (doble clic) con enlaces
sc = main.NodeScene("shader"); sc.addItem(n); sc.sync()
check("sync no rompe", True)
print("RESULTADO:", "TODO OK" if ok else "HAY FALLOS")
