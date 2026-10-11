"""Detecta nodos cuyo contenido (filas o sockets) se sale del cuerpo del nodo."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from PySide6.QtWidgets import QApplication
app = QApplication([])
import main

lines, bad = [], 0
for mode in ("shader", "compositor"):
    for s in main.CATALOG[mode]:
        n = main.NodeItem(s, main.category(s["idname"], mode))
        bottom = max([r["y"] + r["h"] for r in n.rows] + [0])
        sock = max([sk.pos().y() + main.SR for sk in n.socks.values() if sk.isVisible()] + [0])
        over = max(bottom, sock) - n.h
        if over > 0.01:
            bad += 1
            lines.append(f"{mode} {s['idname']}: h={n.h:.1f} contenido llega a {max(bottom, sock):.1f} (se sale {over:.1f})")
lines.append(f"nodos con contenido fuera del cuerpo: {bad}")
open(os.path.join(here, "out_overflow.txt"), "w", encoding="utf-8").write("\n".join(lines))
print("ok")
