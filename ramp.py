"""Color Ramp: estado (marcadores, modo de color, interpolacion) y evaluacion.

Sin dependencias de Qt. Los colores son RGBA lineales.
"""
import colorsys


RAMP_CMODES = ["RGB", "HSV", "HSL"]
RAMP_INTERPS = ["Ease", "Cardinal", "B-Spline", "Linear", "Constant"]


def _new_ramp():
    """Estado de un Color Ramp: marcadores (pos 0-1, color lineal RGBA), el activo, modo de color e interpolacion."""
    return {"stops": [{"pos": 0.0, "color": [0.0, 0.0, 0.0, 1.0]},
                      {"pos": 1.0, "color": [1.0, 1.0, 1.0, 1.0]}],
            "active": 0, "cmode": "RGB", "interp": "Linear"}


def _ramp_mix(a, b, u, cmode):
    if cmode == "RGB":
        return [a[k] + (b[k] - a[k]) * u for k in range(4)]
    to = colorsys.rgb_to_hsv if cmode == "HSV" else colorsys.rgb_to_hls
    back = colorsys.hsv_to_rgb if cmode == "HSV" else colorsys.hls_to_rgb
    ca, cb = to(*a[:3]), to(*b[:3])
    dh = cb[0] - ca[0]
    if dh > 0.5:
        dh -= 1.0
    elif dh < -0.5:
        dh += 1.0
    h = (ca[0] + dh * u) % 1.0          # el tono toma el camino corto ("Near" de Blender)
    r, g, bl = back(h, ca[1] + (cb[1] - ca[1]) * u, ca[2] + (cb[2] - ca[2]) * u)
    return [r, g, bl, a[3] + (b[3] - a[3]) * u]


def ramp_eval(rp, t):
    """Color (lineal RGBA) del ramp en la posicion t."""
    st = rp["stops"]
    if t <= st[0]["pos"]:
        return list(st[0]["color"])
    if t >= st[-1]["pos"]:
        return list(st[-1]["color"])
    for a, b in zip(st, st[1:]):
        if a["pos"] <= t < b["pos"]:
            if rp["interp"] == "Constant":
                return list(a["color"])
            d = b["pos"] - a["pos"]
            u = 0.0 if d < 1e-9 else (t - a["pos"]) / d
            if rp["interp"] in ("Ease", "Cardinal", "B-Spline"):
                u = u * u * (3.0 - 2.0 * u)      # aproximacion suave (no son las splines exactas de Blender)
            return _ramp_mix(a["color"], b["color"], u, rp["cmode"])
    return list(st[-1]["color"])


def ramp_samples(rp):
    ts = {i / 64.0 for i in range(65)}
    for s in rp["stops"]:
        ts.add(s["pos"])
        if rp["interp"] == "Constant":
            ts.add(max(0.0, s["pos"] - 1e-4))   # salto seco justo antes de cada marcador
    return sorted(ts)
