"""Parche: Glare muestra solo los sockets que corresponden a su Type + quita una clave duplicada.
Tabla verificada contra Blender 5.2.0 LTS (sockets activos por Type).
Uso: guarda main.py en VS Code (Ctrl+S) y ejecuta:  python _patch_glare.py
Hace copia en main_backup_antes_glare.py y no toca nada si algun ancla no coincide."""
import shutil
from pathlib import Path

here = Path(__file__).parent
src = here / "main.py"
raw = src.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

CONST = '''# Glare: sockets activos segun el Type (verificado en Blender 5.2.0 LTS)
_GLARE_COMMON = {"Quality", "Threshold", "Smoothness", "Clamp", "Maximum", "Strength", "Saturation",
                 "Tint"}
GLARE_SOCKS = {
    "bloom": _GLARE_COMMON | {"Size"},
    "fog glow": _GLARE_COMMON | {"Size"},
    "streaks": _GLARE_COMMON | {"Streaks", "Streaks Angle", "Iterations", "Fade", "Color Modulation"},
    "simple star": _GLARE_COMMON | {"Iterations", "Fade", "Diagonal"},
    "ghosts": _GLARE_COMMON | {"Iterations", "Color Modulation"},
    "sun beams": _GLARE_COMMON | {"Size", "Sun Position", "Jitter"},
    "kernel": _GLARE_COMMON | {"Kernel Data Type", "Kernel"},
}


'''

METHOD = '''    def _glare_dyn(self, ins):
        """Glare: oculta los sockets que no aplican al Type elegido (si el Type no se reconoce, no toca nada)."""
        t = str(self.vals.get("Type") or "").lower().replace("_", " ")
        key = next((k for k in GLARE_SOCKS if k in t), None)
        if key is None:
            return
        on = GLARE_SOCKS[key]
        is_col = "color" in str(self.vals.get("Kernel Data Type") or "").lower()
        for s in ins:
            nm = s["name"]
            if nm in ("Image", "Type"):
                continue
            if nm == "Kernel":
                s["enabled"] = "Kernel" in on and (s["identifier"] == "Color Kernel") == is_col
            else:
                s["enabled"] = nm in on

'''

HOOK_OLD = '''                elif s["identifier"] == "Color Kernel":
                    s["enabled"] = is_col
'''
HOOK_NEW = HOOK_OLD + '''            if idn == "CompositorNodeGlare":
                self._glare_dyn(ins)
'''

DUP_OLD = '''    "ShaderNodeVectorTransform": ["vector_type", "convert_from", "convert_to"],
    "ShaderNodeTexEnvironment": ["interpolation", "projection"],
'''
DUP_NEW = '''    "ShaderNodeVectorTransform": ["vector_type", "convert_from", "convert_to"],
'''

edits = [
    ("def fmt(v, st):", CONST + "def fmt(v, st):"),
    ("    def title(self):", METHOD + "    def title(self):"),
    (HOOK_OLD, HOOK_NEW),
    (DUP_OLD, DUP_NEW),
]

if "_glare_dyn" in text:
    raise SystemExit("El parche ya esta aplicado.")
for old, _ in edits:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"Ancla encontrada {n} veces (se esperaba 1), no se cambio nada:\n{old[:70]!r}")

for old, new in edits:
    text = text.replace(old, new)

shutil.copy(src, here / "main_backup_antes_glare.py")
out = text.replace("\n", "\r\n") if crlf else text
src.write_bytes(out.encode("utf-8"))
print("Parche aplicado. Copia: main_backup_antes_glare.py. Regenera el volcado con: python dump_comp.py")
