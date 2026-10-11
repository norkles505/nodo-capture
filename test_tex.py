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


def mk(n):
    s = next(x for x in main.CATALOG["shader"] if x["idname"] == "ShaderNodeTex" + n)
    return main.NodeItem(s, main.category(s["idname"], "shader"))


def ins(n):
    return [s["name"] for s in n.spec["inputs"] if n._visible(s, n.lin_in)]


def outs(n):
    return [s["name"] for s in n.spec["outputs"] if n._visible(s, n.lin_out)]


def menus(n):
    return [r["name"] for r in n.rows if r["k"] in ("enum", "bool", "num") and r["ref"][0] == "p"]


def setp(n, **kw):
    n.pvals.update(kw)
    n.relayout()


# ---- Image
n = mk("Image")
print("  Image menus:", menus(n), "pvals:", sorted(n.pvals))
check("Image orden Interpolation, Projection, Extension",
      menus(n) == ["Interpolation", "Projection", "Extension"], menus(n))
h0 = n.h
setp(n, projection="BOX")
check("Image BOX muestra Blend", "Blend" in menus(n), menus(n))
check("Image BOX crece", n.h > h0, (h0, n.h))

# ---- Voronoi
n = mk("Voronoi")
print("  Voronoi pvals:", sorted(n.pvals))
check("Voronoi orden por defecto", menus(n) == ["Dimensions", "Feature Output", "Distance Metric", "Normalize"], menus(n))
check("Voronoi 3D F1 entradas", ins(n) == ["Vector", "Scale", "Detail", "Roughness", "Lacunarity", "Randomness"], ins(n))
check("Voronoi 3D F1 salidas", outs(n) == ["Distance", "Color", "Position"], outs(n))
setp(n, voronoi_dimensions="1D")
check("Voronoi 1D: W en vez de Vector", "W" in ins(n) and "Vector" not in ins(n), ins(n))
check("Voronoi 1D: sin Distance Metric", "Distance Metric" not in menus(n), menus(n))
check("Voronoi 1D salidas Distance, Color, W", outs(n) == ["Distance", "Color", "W"], outs(n))
setp(n, voronoi_dimensions="4D")
check("Voronoi 4D: Vector y W", "W" in ins(n) and "Vector" in ins(n), ins(n))
setp(n, voronoi_dimensions="3D", feature="SMOOTH_F1")
check("Voronoi Smooth F1: Smoothness", "Smoothness" in ins(n), ins(n))
setp(n, feature="F1", distance="MINKOWSKI")
check("Voronoi Minkowski: Exponent", "Exponent" in ins(n), ins(n))
setp(n, distance="EUCLIDEAN", feature="DISTANCE_TO_EDGE")
check("Voronoi Dist. al borde: sin Detail/Roughness", not {"Detail", "Roughness", "Lacunarity"} & set(ins(n)), ins(n))
check("Voronoi Dist. al borde: solo Distance", outs(n) == ["Distance"], outs(n))
check("Voronoi Dist. al borde: sin Normalize ni Distance Metric",
      not {"Normalize", "Distance Metric"} & set(menus(n)), menus(n))
setp(n, feature="N_SPHERE_RADIUS")
check("Voronoi N-Sphere: solo Radius", outs(n) == ["Radius"], outs(n))

# ---- Noise
n = mk("Noise")
check("Noise 3D FBM entradas", ins(n) == ["Vector", "Scale", "Detail", "Roughness", "Lacunarity", "Distortion"], ins(n))
setp(n, noise_dimensions="1D")
check("Noise 1D: W sin Vector", "W" in ins(n) and "Vector" not in ins(n), ins(n))
setp(n, noise_dimensions="4D")
check("Noise 4D: Vector y W", "W" in ins(n) and "Vector" in ins(n), ins(n))
setp(n, noise_dimensions="3D", noise_type="RIDGED_MULTIFRACTAL")
check("Noise Ridged: Offset y Gain", {"Offset", "Gain"} <= set(ins(n)), ins(n))
setp(n, noise_type="MULTIFRACTAL")
check("Noise Multifractal: Offset sin Gain", "Offset" in ins(n) and "Gain" not in ins(n), ins(n))

# ---- White Noise
n = mk("WhiteNoise")
check("WhiteNoise 3D: Vector", ins(n) == ["Vector"], ins(n))
setp(n, noise_dimensions="4D")
check("WhiteNoise 4D: Vector y W", ins(n) == ["Vector", "W"], ins(n))
setp(n, noise_dimensions="1D")
check("WhiteNoise 1D: W", ins(n) == ["W"], ins(n))

# ---- Gabor
n = mk("Gabor")
vec = [s for s in n.spec["inputs"] if s["name"] == "Orientation"]
print("  Gabor Orientation stype:", [s.get("stype") for s in vec])
setp(n, gabor_type="3D")
en = [(s.get("stype"), n._visible(s, n.lin_in)) for s in vec]
check("Gabor 3D: Orientation vector", ("VECTOR", True) in en and ("VALUE", False) in en, en)
setp(n, gabor_type="2D")
en = [(s.get("stype"), n._visible(s, n.lin_in)) for s in vec]
check("Gabor 2D: Orientation valor", ("VALUE", True) in en and ("VECTOR", False) in en, en)

# ---- Wave
n = mk("Wave")
check("Wave bandas: Bands Direction", "Bands Direction" in menus(n), menus(n))
setp(n, wave_type="RINGS")
check("Wave anillos: Rings Direction", "Rings Direction" in menus(n) and "Bands Direction" not in menus(n), menus(n))

print("RESULTADO:", "TODO OK" if ok else "HAY FALLOS")
