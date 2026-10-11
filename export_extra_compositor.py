"""Añade a data/compositor_nodes.json los nodos del menú Add del compositor de Blender que aún no estén.

Ejecutar DENTRO de Blender (Text Editor > Run Script, o por el MCP de Blender).
- La lista de nodos sale del propio menú Add del compositor de tu Blender
  (scripts/startup/bl_ui/node_add_menu_compositor.py), así que sirve para cualquier versión.
- No toca las entradas que ya existen (conservan su calibración); solo agrega las que faltan.
- Hace copia de seguridad en compositor_nodes.json.bak la primera vez.
"""
import bpy
import json
import os
import re
import shutil

DATA = (os.path.join(os.path.dirname(os.path.abspath(__file__)), "data") if "__file__" in globals()
        else r"c:\Users\HP\Desktop\proyectos\nodo capture\data")
PATH = os.path.join(DATA, "compositor_nodes.json")
BASE_PROPS = {p.identifier for p in bpy.types.Node.bl_rna.properties}


def to_py(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, bpy.types.ID):
        return None
    try:
        return [to_py(x) for x in v]      # Vector, Color, Euler, bpy_prop_array...
    except TypeError:
        return None


def sock_spec(s):
    d = {"name": s.name, "identifier": s.identifier, "type": s.bl_idname, "stype": s.type,
         "hide_value": s.hide_value, "enabled": s.enabled}
    if s.bl_idname != "NodeSocketVirtual":
        dv = None
        if s.type != "MATRIX" and hasattr(s, "default_value"):
            dv = to_py(s.default_value)
        d["default"] = dv
    return d


def prop_specs(node):
    out = []
    for p in node.bl_rna.properties:
        pid, t = p.identifier, p.type
        if pid in BASE_PROPS or pid == "rna_type" or p.is_readonly or t == "COLLECTION":
            continue
        if t == "POINTER":
            ft = getattr(bpy.types, p.fixed_type.identifier, None) if p.fixed_type else None
            if ft is not None and issubclass(ft, bpy.types.ID):
                out.append({"id": pid, "name": p.name, "type": "POINTER", "value": None})
            continue
        if t == "ENUM":
            if p.is_enum_flag:
                continue
            items = [{"id": it.identifier, "name": it.name} for it in p.enum_items]
            out.append({"id": pid, "name": p.name, "type": "ENUM", "value": getattr(node, pid),
                        "items": items})
            continue
        out.append({"id": pid, "name": p.name, "type": t, "value": to_py(getattr(node, pid))})
    return out


def menu_idnames():
    src = open(os.path.join(bpy.utils.system_resource('SCRIPTS'), "startup", "bl_ui",
                            "node_add_menu_compositor.py"), encoding="utf-8").read()
    ids = re.findall(r'"((?:CompositorNode|ShaderNode|FunctionNode|GeometryNode|NodeGroupInput|NodeGroupOutput)[A-Za-z0-9_]*)"', src)
    seen = []
    for i in ids:
        if i not in seen:
            seen.append(i)
    return seen


def main():
    raw = open(PATH, encoding="utf-8").read()
    data = json.loads(raw)
    have = {n["idname"] for n in data}
    missing = [i for i in menu_idnames() if i not in have]
    if not os.path.exists(PATH + ".bak"):
        shutil.copy(PATH, PATH + ".bak")

    tree = bpy.data.node_groups.new("__export_extra__", "CompositorNodeTree")
    added, failed = [], []
    try:
        for idn in missing:
            try:
                nd = tree.nodes.new(idn)
            except Exception as e:
                failed.append((idn, str(e)))
                continue
            data.append({"idname": idn, "label": nd.bl_label, "width": float(nd.width),
                         "inputs": [sock_spec(s) for s in nd.inputs],
                         "outputs": [sock_spec(s) for s in nd.outputs],
                         "props": prop_specs(nd)})
            added.append(idn)
            tree.nodes.remove(nd)
    finally:
        bpy.data.node_groups.remove(tree)

    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(json.dumps(data, indent=1, ensure_ascii=False))
    print("agregados:", len(added), "| fallidos:", failed, "| total en el JSON:", len(data))


main()
