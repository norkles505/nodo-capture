"""Agrega a cada socket de data/compositor_nodes.json su forma ("shape") tal como la dibuja Blender 5.x.

Ejecutar DENTRO de Blender 5.2 (Scripting > Text > Open este archivo > Run Script).
- Crea cada nodo del JSON en un arbol de compositor temporal y lee socket.display_shape
  (CIRCLE = dinamico, SQUARE = un solo valor -> barra vertical, etc.).
- Solo AÑADE las claves "shape" y "structure" a los sockets; no toca nada mas
  (la calibracion de cada nodo se conserva).
- Hace copia de seguridad en compositor_nodes.json.bak_shapes la primera vez.
"""
import bpy
import json
import os
import shutil
from collections import Counter

DATA = r"/home/kenny/Escritorio/proyectos/nodo-capture/data"   # cambia esta ruta si mueves el proyecto
PATH = os.path.join(DATA, "compositor_nodes.json")
SKIP = {"NodeFrame", "NodeReroute"}     # nodos de layout, no tienen sockets reales


def main():
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)
    if not os.path.exists(PATH + ".bak_shapes"):
        shutil.copy(PATH, PATH + ".bak_shapes")

    tree = bpy.data.node_groups.new("__shapes__", "CompositorNodeTree")
    shapes, failed, nodes_ok = Counter(), [], 0
    try:
        for spec in data:
            idn = spec["idname"]
            if idn in SKIP:
                continue
            try:
                nd = tree.nodes.new(idn)
            except Exception as e:
                failed.append((idn, str(e)))
                continue
            try:
                tree.update()
            except Exception:
                pass
            for kind, socks in (("inputs", nd.inputs), ("outputs", nd.outputs)):
                by_id = {s.identifier: s for s in socks}
                for sp in spec.get(kind, []):
                    s = by_id.get(sp["identifier"])
                    if s is None:
                        continue
                    shape = getattr(s, "display_shape", None)
                    if shape is not None:
                        sp["shape"] = shape
                        shapes[shape] += 1
                    st = getattr(s, "structure_type", None)
                    if st is not None:
                        sp["structure"] = st
            nodes_ok += 1
            tree.nodes.remove(nd)
    finally:
        bpy.data.node_groups.remove(tree)

    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(json.dumps(data, indent=1, ensure_ascii=False))
    print("nodos procesados:", nodes_ok, "| fallidos:", failed)
    print("formas encontradas:", dict(shapes))
    k = next((n for n in data if n["idname"] == "CompositorNodeKuwahara"), None)
    if k:
        print("Kuwahara:", {s["name"]: s.get("shape") for s in k["inputs"] + k["outputs"]})


main()
