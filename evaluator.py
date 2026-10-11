"""Evaluador de nodos para Nodo Capture (sin dependencias de Qt).

Recorre el grafo desde las entradas hasta las salidas y calcula el valor de cada
socket de salida con las mismas formulas que Blender. Cada nodo se evalua con una
funcion registrada en FUNCS; para soportar un nodo nuevo basta con anadir una funcion
y registrarla con @node("NombreSinPrefijo").

Los valores se representan asi: float/int/bool = escalar, VECTOR/ROTATION = lista de 3,
RGBA = lista de 4 (color lineal). Los nodos sin funcion (texturas, BSDF...) no producen valor
y los nodos que dependen de ellos tampoco.
"""
import math
import colorsys

LUMA = (0.2126, 0.7152, 0.0722)


class Unsupported(Exception):
    """El nodo (o alguna de sus entradas) no se puede calcular."""


# ------------------------------------------------------------ conversiones
def _seq(v):
    return isinstance(v, (list, tuple))


def to_float(v):
    if v is None:
        raise Unsupported
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if _seq(v):
        if len(v) >= 4:
            return LUMA[0] * v[0] + LUMA[1] * v[1] + LUMA[2] * v[2]
        return sum(v) / len(v) if v else 0.0
    return float(v)


def conv(v, st):
    """Convierte v a la forma del socket destino (st = tipo del socket de entrada)."""
    if v is None:
        raise Unsupported
    if st in ("VALUE", "INT", "BOOLEAN"):
        f = to_float(v)
        if st == "INT":
            return int(round(f))
        if st == "BOOLEAN":
            return f > 0.0
        return f
    if st in ("VECTOR", "ROTATION"):
        if _seq(v):
            l = [float(x) for x in v][:3]
            return l + [0.0] * (3 - len(l))
        f = float(v)
        return [f, f, f]
    if st == "RGBA":
        if _seq(v):
            l = [float(x) for x in v][:4]
            if len(l) == 3:
                return l + [1.0]
            if len(l) < 3:
                f = l[0] if l else 0.0
                return [f, f, f, 1.0]
            return l
        f = float(v)
        return [f, f, f, 1.0]
    if st in ("SHADER", "STRING", "MENU"):
        raise Unsupported
    return v


def clamp01(x):
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------ grafo
FUNCS = {}


def node(name):
    def deco(fn):
        FUNCS[name] = fn
        return fn
    return deco


def base_name(idname):
    for pre in ("ShaderNode", "CompositorNode"):
        if idname.startswith(pre):
            return idname[len(pre):]
    return idname


class Ctx:
    """Acceso a las entradas de un nodo: valor del enlace conectado o el valor por defecto."""

    def __init__(self, graph, nd):
        self.g, self.n = graph, nd
        self.specs = {s["identifier"]: s for s in nd.spec["inputs"]}

    def get(self, ident):
        s = self.specs.get(ident)
        if s is None:
            raise Unsupported
        st = s.get("stype")
        src = self.g.inc.get((self.n, ident))
        if src is not None:
            v = self.g.outputs(src[0]).get(src[1])
        else:
            v = self.n.vals.get(ident)
        if v is None:
            raise Unsupported
        return conv(v, st)

    def get_idx(self, i):
        return self.get(self.n.spec["inputs"][i]["identifier"])


def out_id(nd, i):
    return nd.spec["outputs"][i]["identifier"]


class Graph:
    def __init__(self, nodes, links):
        self.nodes = list(nodes)
        self.inc = {}
        for na, oid, nb, iid in links:
            self.inc[(nb, iid)] = (na, oid)
        self.cache, self.busy = {}, set()

    def outputs(self, nd):
        if nd in self.cache:
            return self.cache[nd]
        if nd in self.busy:          # ciclo: sin valor
            return {}
        self.busy.add(nd)
        res = {}
        fn = FUNCS.get(base_name(nd.spec["idname"]))
        if fn is not None:
            try:
                res = fn(nd, Ctx(self, nd)) or {}
            except (Unsupported, ArithmeticError, ValueError, IndexError, KeyError, TypeError):
                res = {}
        self.busy.discard(nd)
        self.cache[nd] = res
        return res


def evaluate(nodes, links):
    """nodes: objetos con .spec/.vals/.pvals; links: (nodo_salida, id_salida, nodo_entrada, id_entrada).
    Devuelve {nodo: {id_salida: valor}} (diccionario vacio si el nodo no se puede calcular)."""
    g = Graph(nodes, links)
    return {n: g.outputs(n) for n in g.nodes}


# ------------------------------------------------------------ entradas
@node("Value")
def _value(nd, c):
    d = nd.spec["outputs"][0].get("default")
    d = nd.vals.get(out_id(nd, 0), d)   # el campo editable guarda el valor en vals
    return {out_id(nd, 0): float(d) if d is not None and not _seq(d) else 0.0}


@node("RGB")
def _rgb(nd, c):
    d = nd.spec["outputs"][0].get("default")
    return {out_id(nd, 0): conv(d if d is not None else [0.8, 0.8, 0.8, 1.0], "RGBA")}


# ------------------------------------------------------------ Math
MATH_1 = {"SQRT", "INVERSE_SQRT", "ABSOLUTE", "EXPONENT", "SIGN", "ROUND", "FLOOR", "CEIL", "TRUNC",
          "FRACT", "SINE", "COSINE", "TANGENT", "ARCSINE", "ARCCOSINE", "ARCTANGENT", "SINH",
          "COSH", "TANH", "RADIANS", "DEGREES"}
MATH_3 = {"MULTIPLY_ADD", "COMPARE", "SMOOTH_MIN", "SMOOTH_MAX", "WRAP"}


def safe_pow(a, b):
    try:
        if a >= 0.0:
            return a ** b
        return a ** b if float(b).is_integer() else 0.0
    except (OverflowError, ZeroDivisionError):
        return 0.0


def smooth_min(a, b, d):
    if d != 0.0:
        h = max(d - abs(a - b), 0.0) / d
        return min(a, b) - h * h * h * d * (1.0 / 6.0)
    return min(a, b)


def wrap(a, hi, lo):
    r = hi - lo
    return a - r * math.floor((a - lo) / r) if r != 0.0 else lo


def pingpong(a, s):
    if s == 0.0:
        return 0.0
    t = (a - s) / (s * 2.0)
    return abs((t - math.floor(t)) * s * 2.0 - s)


def math_op(op, a, b, c):
    try:
        if op == "ADD": return a + b
        if op == "SUBTRACT": return a - b
        if op == "MULTIPLY": return a * b
        if op == "DIVIDE": return a / b if b != 0.0 else 0.0
        if op == "MULTIPLY_ADD": return a * b + c
        if op == "POWER": return safe_pow(a, b)
        if op == "LOGARITHM": return math.log(a) / math.log(b) if a > 0 and b > 0 and b != 1.0 else 0.0
        if op == "SQRT": return math.sqrt(a) if a > 0 else 0.0
        if op == "INVERSE_SQRT": return 1.0 / math.sqrt(a) if a > 0 else 0.0
        if op == "ABSOLUTE": return abs(a)
        if op == "EXPONENT": return math.exp(a)
        if op == "MINIMUM": return min(a, b)
        if op == "MAXIMUM": return max(a, b)
        if op == "LESS_THAN": return 1.0 if a < b else 0.0
        if op == "GREATER_THAN": return 1.0 if a > b else 0.0
        if op == "SIGN": return (a > 0) - (a < 0) + 0.0
        if op == "COMPARE": return 1.0 if abs(a - b) <= max(c, 1e-5) else 0.0
        if op == "SMOOTH_MIN": return smooth_min(a, b, c)
        if op == "SMOOTH_MAX": return -smooth_min(-a, -b, c)
        if op == "ROUND": return math.floor(a + 0.5)
        if op == "FLOOR": return float(math.floor(a))
        if op == "CEIL": return float(math.ceil(a))
        if op == "TRUNC": return float(math.trunc(a))
        if op == "FRACT": return a - math.floor(a)
        if op == "MODULO": return math.fmod(a, b) if b != 0.0 else 0.0
        if op == "FLOORED_MODULO": return a - math.floor(a / b) * b if b != 0.0 else 0.0
        if op == "WRAP": return wrap(a, b, c)
        if op == "SNAP": return math.floor(a / b) * b if b != 0.0 else 0.0
        if op == "PINGPONG": return pingpong(a, b)
        if op == "SINE": return math.sin(a)
        if op == "COSINE": return math.cos(a)
        if op == "TANGENT": return math.tan(a)
        if op == "ARCSINE": return math.asin(max(-1.0, min(1.0, a)))
        if op == "ARCCOSINE": return math.acos(max(-1.0, min(1.0, a)))
        if op == "ARCTANGENT": return math.atan(a)
        if op == "ARCTAN2": return math.atan2(a, b)
        if op == "SINH": return math.sinh(a)
        if op == "COSH": return math.cosh(a)
        if op == "TANH": return math.tanh(a)
        if op == "RADIANS": return math.radians(a)
        if op == "DEGREES": return math.degrees(a)
    except (OverflowError, ValueError, ZeroDivisionError):
        return 0.0
    raise Unsupported


@node("Math")
def _math(nd, c):
    op = nd.pvals.get("operation") or "ADD"
    n = 1 if op in MATH_1 else 3 if op in MATH_3 else 2
    a = c.get_idx(0)
    b = c.get_idx(1) if n >= 2 else 0.0
    d = c.get_idx(2) if n >= 3 else 0.0
    r = math_op(op, a, b, d)
    if nd.pvals.get("use_clamp"):
        r = clamp01(r)
    return {out_id(nd, 0): r}


# ------------------------------------------------------------ Vector Math
def vsafe_div(a, b):
    return a / b if b != 0.0 else 0.0


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def vlen(a):
    return math.sqrt(dot(a, a))


def vnorm(a):
    l = vlen(a)
    return [x / l for x in a] if l != 0.0 else [0.0, 0.0, 0.0]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def vm_op(op, a, b, c, s):
    m = lambda f: [f(x, y) for x, y in zip(a, b)]
    u = lambda f: [f(x) for x in a]
    if op == "ADD": return m(lambda x, y: x + y)
    if op == "SUBTRACT": return m(lambda x, y: x - y)
    if op == "MULTIPLY": return m(lambda x, y: x * y)
    if op == "DIVIDE": return m(vsafe_div)
    if op == "MULTIPLY_ADD": return [x * y + z for x, y, z in zip(a, b, c)]
    if op == "CROSS_PRODUCT": return cross(a, b)
    if op == "PROJECT":
        d = dot(b, b)
        return [x * dot(a, b) / d for x in b] if d != 0.0 else [0.0, 0.0, 0.0]
    if op == "REFLECT":
        n = vnorm(b)
        k = 2.0 * dot(a, n)
        return [x - k * y for x, y in zip(a, n)]
    if op == "REFRACT":
        n = vnorm(b)
        d = dot(n, a)
        k = 1.0 - s * s * (1.0 - d * d)
        if k < 0.0:
            return [0.0, 0.0, 0.0]
        return [s * x - (s * d + math.sqrt(k)) * y for x, y in zip(a, n)]
    if op == "FACEFORWARD": return list(a) if dot(b, c) < 0.0 else [-x for x in a]
    if op == "DOT_PRODUCT": return dot(a, b)
    if op == "DISTANCE": return vlen([x - y for x, y in zip(a, b)])
    if op == "LENGTH": return vlen(a)
    if op == "SCALE": return [x * s for x in a]
    if op == "NORMALIZE": return vnorm(a)
    if op == "ABSOLUTE": return u(abs)
    if op == "POWER": return m(safe_pow)
    if op == "SIGN": return u(lambda x: (x > 0) - (x < 0) + 0.0)
    if op == "MINIMUM": return m(min)
    if op == "MAXIMUM": return m(max)
    if op == "FLOOR": return u(lambda x: float(math.floor(x)))
    if op == "CEIL": return u(lambda x: float(math.ceil(x)))
    if op == "ROUND": return u(lambda x: float(math.floor(x + 0.5)))
    if op == "FRACTION": return u(lambda x: x - math.floor(x))
    if op == "MODULO": return m(lambda x, y: math.fmod(x, y) if y != 0.0 else 0.0)
    if op == "WRAP": return [wrap(x, y, z) for x, y, z in zip(a, b, c)]
    if op == "SNAP": return m(lambda x, y: math.floor(x / y) * y if y != 0.0 else 0.0)
    if op == "SINE": return u(math.sin)
    if op == "COSINE": return u(math.cos)
    if op == "TANGENT": return u(math.tan)
    raise Unsupported


VM_1 = {"NORMALIZE", "LENGTH", "ABSOLUTE", "SIGN", "ROUND", "FLOOR", "CEIL", "FRACTION", "SINE",
        "COSINE", "TANGENT", "SCALE"}
VM_3 = {"MULTIPLY_ADD", "FACEFORWARD", "WRAP"}
VM_VAL = {"LENGTH", "DISTANCE", "DOT_PRODUCT"}


@node("VectorMath")
def _vector_math(nd, c):
    op = nd.pvals.get("operation") or "ADD"
    n = 1 if op in VM_1 else 3 if op in VM_3 else 2
    a = c.get_idx(0)
    b = c.get_idx(1) if n >= 2 else [0.0, 0.0, 0.0]
    d = c.get_idx(2) if n >= 3 else [0.0, 0.0, 0.0]
    s = c.get_idx(3) if op in ("SCALE", "REFRACT") else 1.0
    r = vm_op(op, a, b, d, s)
    return {out_id(nd, 1 if op in VM_VAL else 0): r}


# ------------------------------------------------------------ Mix
def rgb_to_hsv(c):
    return colorsys.rgb_to_hsv(*c)


def hsv_to_rgb(h, s, v):
    return list(colorsys.hsv_to_rgb(h % 1.0, clamp01(s), v))


def blend(bt, f, a, b):
    """Mezcla de colores RGB (listas de 3) con factor f, segun el modo de Blender."""
    fm = 1.0 - f
    if bt == "MIX": return [lerp(x, y, f) for x, y in zip(a, b)]
    if bt == "ADD": return [x + f * y for x, y in zip(a, b)]
    if bt == "SUBTRACT": return [x - f * y for x, y in zip(a, b)]
    if bt == "MULTIPLY": return [fm * x + f * x * y for x, y in zip(a, b)]
    if bt == "DIVIDE": return [fm * x + f * x / y if y != 0.0 else x for x, y in zip(a, b)]
    if bt == "SCREEN": return [1.0 - (fm + f * (1.0 - y)) * (1.0 - x) for x, y in zip(a, b)]
    if bt == "OVERLAY":
        return [x * (fm + 2.0 * f * y) if x < 0.5 else 1.0 - (fm + 2.0 * f * (1.0 - y)) * (1.0 - x)
                for x, y in zip(a, b)]
    if bt == "DARKEN": return [lerp(x, min(x, y), f) for x, y in zip(a, b)]
    if bt == "LIGHTEN": return [max(x, y * f) for x, y in zip(a, b)]
    if bt == "DIFFERENCE": return [fm * x + f * abs(x - y) for x, y in zip(a, b)]
    if bt == "EXCLUSION": return [max(fm * x + f * (x + y - 2.0 * x * y), 0.0) for x, y in zip(a, b)]
    if bt == "DODGE":
        out = []
        for x, y in zip(a, b):
            if x == 0.0:
                out.append(0.0)
                continue
            t = 1.0 - f * y
            out.append(1.0 if t <= 0.0 else min(x / t, 1.0))
        return out
    if bt == "BURN":
        out = []
        for x, y in zip(a, b):
            t = fm + f * y
            out.append(0.0 if t <= 0.0 else clamp01(1.0 - (1.0 - x) / t))
        return out
    if bt == "SOFT_LIGHT":
        out = []
        for x, y in zip(a, b):
            scr = 1.0 - (1.0 - y) * (1.0 - x)
            out.append(fm * x + f * ((1.0 - x) * y * x + x * scr))
        return out
    if bt == "LINEAR_LIGHT":
        return [x + f * (2.0 * (y - 0.5)) if y > 0.5 else x + f * (2.0 * y - 1.0) for x, y in zip(a, b)]
    if bt in ("HUE", "SATURATION", "COLOR", "VALUE"):
        ha, sa, va = rgb_to_hsv(a)
        hb, sb, vb = rgb_to_hsv(b)
        if bt == "HUE": t = hsv_to_rgb(hb, sa, va) if sb != 0.0 else list(a)
        elif bt == "SATURATION": t = hsv_to_rgb(ha, sb, va) if sa != 0.0 else list(a)
        elif bt == "COLOR": t = hsv_to_rgb(hb, sb, va) if sb != 0.0 else list(a)
        else: t = hsv_to_rgb(ha, sa, vb)
        return [lerp(x, y, f) for x, y in zip(a, t)]
    raise Unsupported


@node("Mix")
def _mix(nd, c):
    dt = nd.pvals.get("data_type") or "FLOAT"
    sfx = {"FLOAT": "Float", "VECTOR": "Vector", "RGBA": "Color"}.get(dt)
    if sfx is None:
        raise Unsupported            # rotaciones: sin soporte
    pv = nd.pvals

    def ident(prefix, suffix):
        for s in nd.spec["inputs"]:
            i = s["identifier"]
            if i.startswith(prefix) and i.rsplit("_", 1)[-1] == suffix:
                return i
        raise Unsupported

    nonuni = dt == "VECTOR" and pv.get("factor_mode") == "NON_UNIFORM"
    fac = c.get(ident("Factor", "Vector" if nonuni else "Float"))
    if pv.get("clamp_factor", True):
        fac = [clamp01(x) for x in fac] if _seq(fac) else clamp01(fac)
    a, b = c.get(ident("A", sfx)), c.get(ident("B", sfx))
    if dt == "FLOAT":
        r = lerp(a, b, fac)
    elif dt == "VECTOR":
        fv = fac if _seq(fac) else [fac] * 3
        r = [lerp(x, y, t) for x, y, t in zip(a, b, fv)]
    else:
        rgb = blend(pv.get("blend_type") or "MIX", fac, a[:3], b[:3])
        if pv.get("clamp_result"):
            rgb = [clamp01(x) for x in rgb]
        r = rgb + [a[3]]
    for s in nd.spec["outputs"]:
        if s["identifier"].rsplit("_", 1)[-1] == sfx:
            return {s["identifier"]: r}
    raise Unsupported


# ------------------------------------------------------------ Map Range / Clamp
def _mr1(v, fmin, fmax, tmin, tmax, steps, interp, clamp):
    if fmax == fmin:
        return 0.0
    t = (v - fmin) / (fmax - fmin)
    if interp == "STEPPED":
        t = math.floor(t * (steps + 1.0)) / steps if steps > 0.0 else 0.0
    elif interp == "SMOOTHSTEP":
        t = clamp01(t)
        t = t * t * (3.0 - 2.0 * t)
    elif interp == "SMOOTHERSTEP":
        t = clamp01(t)
        t = t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
    r = tmin + t * (tmax - tmin)
    if clamp and interp in ("LINEAR", "STEPPED"):
        r = max(min(r, max(tmin, tmax)), min(tmin, tmax))
    return r


@node("MapRange")
def _map_range(nd, c):
    vec = nd.pvals.get("data_type") == "FLOAT_VECTOR"
    interp = nd.pvals.get("interpolation_type") or "LINEAR"
    clamp = bool(nd.pvals.get("clamp"))
    names = (("Vector", "From_Min_FLOAT3", "From_Max_FLOAT3", "To_Min_FLOAT3", "To_Max_FLOAT3", "Steps_FLOAT3")
             if vec else ("Value", "From Min", "From Max", "To Min", "To Max", "Steps"))
    v, fmin, fmax, tmin, tmax = (c.get(n) for n in names[:5])
    steps = c.get(names[5]) if interp == "STEPPED" else (0.0 if not vec else [0.0] * 3)
    if vec:
        r = [_mr1(v[i], fmin[i], fmax[i], tmin[i], tmax[i], steps[i], interp, clamp) for i in range(3)]
    else:
        r = _mr1(v, fmin, fmax, tmin, tmax, steps, interp, clamp)
    return {out_id(nd, 1 if vec else 0): r}


@node("Clamp")
def _clamp(nd, c):
    v, lo, hi = c.get("Value"), c.get("Min"), c.get("Max")
    if nd.pvals.get("clamp_type") == "RANGE":
        lo, hi = min(lo, hi), max(lo, hi)
    return {out_id(nd, 0): min(max(v, lo), hi)}


# ------------------------------------------------------------ Color
@node("Invert")
def _invert(nd, c):
    f, col = clamp01(c.get("Fac")), c.get("Color")
    return {out_id(nd, 0): [lerp(x, 1.0 - x, f) for x in col[:3]] + [col[3]]}


@node("MixRGB")
def _mix_rgb(nd, c):
    f = clamp01(c.get("Fac"))
    a, b = c.get("Color1"), c.get("Color2")
    rgb = blend(nd.pvals.get("blend_type") or "MIX", f, a[:3], b[:3])
    if nd.pvals.get("use_clamp"):
        rgb = [clamp01(x) for x in rgb]
    return {out_id(nd, 0): rgb + [a[3]]}


@node("Gamma")
def _gamma(nd, c):
    col, g = c.get("Color"), c.get("Gamma")
    return {out_id(nd, 0): [safe_pow(x, g) if x > 0.0 else x for x in col[:3]] + [col[3]]}


@node("BrightContrast")
def _bright_contrast(nd, c):
    col, br, ct = c.get("Color"), c.get("Bright"), c.get("Contrast")
    a, b = 1.0 + ct, br - ct * 0.5
    return {out_id(nd, 0): [max(a * x + b, 0.0) for x in col[:3]] + [col[3]]}


@node("HueSaturation")
def _hue_sat(nd, c):
    hue, sat, val, fac = c.get("Hue"), c.get("Saturation"), c.get("Value"), c.get("Fac")
    col = c.get("Color")
    h, s, v = rgb_to_hsv(col[:3])
    t = list(colorsys.hsv_to_rgb((h + hue + 0.5) % 1.0, clamp01(s * sat), v * val))
    return {out_id(nd, 0): [lerp(x, y, fac) for x, y in zip(col[:3], t)] + [col[3]]}


@node("RGBToBW")
def _rgb_to_bw(nd, c):
    return {out_id(nd, 0): to_float(c.get_idx(0)[:3] + [1.0] if False else c.get_idx(0))}


@node("ValToRGB")
def _color_ramp(nd, c):
    # la rampa se dibuja siempre negro -> blanco, asi que se evalua igual
    f = clamp01(c.get_idx(0))
    return {out_id(nd, 0): [f, f, f, 1.0], out_id(nd, 1): 1.0}


# ------------------------------------------------------------ Combine / Separate
@node("CombineXYZ")
def _combine_xyz(nd, c):
    return {out_id(nd, 0): [c.get_idx(0), c.get_idx(1), c.get_idx(2)]}


@node("SeparateXYZ")
def _separate_xyz(nd, c):
    v = c.get_idx(0)
    return {out_id(nd, i): v[i] for i in range(3)}


@node("CombineColor")
def _combine_color(nd, c):
    mode = nd.pvals.get("mode") or "RGB"
    x, y, z, a = c.get_idx(0), c.get_idx(1), c.get_idx(2), c.get_idx(3)
    if mode == "HSV": rgb = list(colorsys.hsv_to_rgb(x % 1.0, clamp01(y), z))
    elif mode == "HSL": rgb = list(colorsys.hls_to_rgb(x % 1.0, z, clamp01(y)))
    else: rgb = [x, y, z]
    return {out_id(nd, 0): rgb + [a]}


@node("SeparateColor")
def _separate_color(nd, c):
    mode = nd.pvals.get("mode") or "RGB"
    col = c.get_idx(0)
    if mode == "HSV": r = list(colorsys.rgb_to_hsv(*col[:3]))
    elif mode == "HSL":
        h, l, s = colorsys.rgb_to_hls(*col[:3])
        r = [h, s, l]
    else: r = list(col[:3])
    return {out_id(nd, i): v for i, v in enumerate(r + [col[3]])}
