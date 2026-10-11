"""Parche: el nodo Multiple Images nace con el ancho de la captura (257). Copia en main.py.pre_ancho2.bak."""
import shutil
from pathlib import Path

SRC = Path(__file__).parent / "main.py"
txt = SRC.read_text(encoding="utf-8")
if "IMG_LOADED_W" in txt:
    raise SystemExit("ya aplicado")
shutil.copy(SRC, SRC.with_name("main.py.pre_ancho2.bak"))

REPL = [
    ("IMG_LOADED_H = 181.0",
     "IMG_LOADED_W = 257.0    # ancho por defecto de Multiple Images (el de tu captura)\nIMG_LOADED_H = 181.0", 1),
    ('self.img_loaded = {"name": name, "users": users}',
     'self.img_loaded = {"name": name, "users": users}\n'
     '        lo, hi = self.width_limits()\n'
     '        self.w = max(lo, min(hi, IMG_LOADED_W))', 1),
]
for old, new, n in REPL:
    if txt.count(old) != n:
        raise SystemExit(f"no encontre {n} vez/veces: {old[:60]}")
    txt = txt.replace(old, new)
SRC.write_text(txt, encoding="utf-8")
print("parche de ancho aplicado")
