import bpy
import bmesh
from bpy.types import Context
from typing import List, Set, Dict

MATERIAL_COLORS = {
    "Red": (1.0, 0.0, 0.0, 1.0),
    "Blue": (0.0, 0.001617, 1.0, 1.0),
    "Green": (0.004734, 1.0, 0.0, 1.0),
    "Yellow": (0.8, 0.716535, 0.0, 1.0),
    "Cyan": (0.0, 0.748324, 0.8, 1.0),
    "Lime": (0.467342, 0.8, 0.256636, 1.0),
    "Pink": (0.642501, 0.0, 0.8, 1.0),
    "Orange": (0.8, 0.330545, 0.0, 1.0)
}

def dummy_view_layer_update(context):
    pass

def create_bmesh(context: Context) -> bmesh.types.BMesh:
    if context.edit_object:
        me = context.edit_object.data
        bm = bmesh.from_edit_mesh(me)
    else:
        me = context.active_object.data
        bm = bmesh.new()
        bm.from_mesh(me)
    
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return bm

def update_mesh(context: Context, bm: bmesh.types.BMesh):
    if context.edit_object:
        me = context.edit_object.data
        bmesh.update_edit_mesh(me)
    else:
        me = context.active_object.data
        bm.to_mesh(me)
        me.update()
    bm.free()

def is_non_manifold(v: bmesh.types.BMVert, bm: bmesh.types.BMesh) -> bool:
    poly_fan = v.link_faces
    labels = {}
    for poly in poly_fan:
        labels[poly.material_index] = labels.get(poly.material_index, 0) + 1

    if len(labels) <= 1:
        return False

    comps = []
    for p in poly_fan:
        if not any(p in c for c in comps):
            visited = set()
            queue = [p]
            while queue:
                node = queue.pop(0)
                if node not in visited:
                    visited.add(node)
                    neighbours = [f for e in node.edges for f in e.link_faces 
                                  if f in poly_fan and f.material_index == node.material_index 
                                  and f not in visited]
                    queue.extend(neighbours)
            comps.append(visited)

    return len(labels) < len(comps)