import bpy
import bmesh
from bpy.types import Context
from typing import List, Set, Dict

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
    colors = {}
    color_attribute = bm.faces.layers.color.get("Color")
    
    if color_attribute is None:
        return False
    
    for poly in poly_fan:
        color = tuple(poly[color_attribute])
        colors[color] = colors.get(color, 0) + 1

    if len(colors) <= 1:
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
                                  if f in poly_fan and tuple(f[color_attribute]) == tuple(node[color_attribute]) 
                                  and f not in visited]
                    queue.extend(neighbours)
            comps.append(visited)

    return len(colors) < len(comps)

def get_or_create_color_attribute(mesh):
    color_attribute = mesh.color_attributes.get("Color")
    if color_attribute is None:
        color_attribute = mesh.color_attributes.new(name="Color", type='FLOAT_COLOR', domain='CORNER')
    elif color_attribute.domain != 'CORNER':
        mesh.color_attributes.remove(color_attribute)
        color_attribute = mesh.color_attributes.new(name="Color", type='FLOAT_COLOR', domain='CORNER')
    return color_attribute