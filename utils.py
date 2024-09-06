import bpy
import bmesh
from bpy.types import Context
from typing import List
import operator

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
    int_layer = bm.faces.layers.int.get("ColorIndex")
    if int_layer is None:
        return False

    face_colors = [face[int_layer] for face in v.link_faces]
    unique_colors = set(face_colors)

    if len(unique_colors) <= 1:
        return False

    # Check if the vertex is at the boundary of different color regions
    color_regions = {}
    for face in v.link_faces:
        color = face[int_layer]
        if color not in color_regions:
            color_regions[color] = set()
        color_regions[color].add(face)

    # Check if there are disconnected regions of the same color
    for color, region in color_regions.items():
        if len(region) > 1:
            # Check if all faces in this region are connected
            start_face = next(iter(region))
            connected = set([start_face])
            to_check = set([start_face])
            while to_check:
                current_face = to_check.pop()
                for edge in current_face.edges:
                    if v in edge.verts:
                        for neighbor_face in edge.link_faces:
                            if neighbor_face in region and neighbor_face not in connected:
                                connected.add(neighbor_face)
                                to_check.add(neighbor_face)
            if len(connected) != len(region):
                return True

    return False

def detect_non_manifold_vertices(bm: bmesh.types.BMesh) -> List[bmesh.types.BMVert]:
    int_layer = bm.faces.layers.int.get("ColorIndex")
    if int_layer is None:
        return []

    non_manifold_verts = []

    for v in bm.verts:
        comps = []
        poly_fan = v.link_faces
        labels = {}
        for poly in poly_fan:
            color_index = poly[int_layer]
            if color_index not in labels:
                labels[color_index] = 1
            else:
                labels[color_index] += 1

        if len(labels) > 1:  # vertex has more than 1 color -> potential non-manifold
            for p in poly_fan:
                flag = False
                for c in comps:
                    if p in c:
                        flag = True
                if not flag:
                    visited = []
                    queue = [p]

                    while queue:  # select adj faces
                        node = queue.pop(0)
                        label = node[int_layer]
                        if node not in visited:
                            visited.append(node)
                            neighbours = []
                            for e in node.edges:
                                for f in e.link_faces:
                                    if f in poly_fan and f[int_layer] == label and f not in neighbours and f not in visited:
                                        neighbours.append(f)
                                for neighbour in neighbours:
                                    queue.append(neighbour)

                    comps.append(visited)

            if len(labels) < len(comps):
                non_manifold_verts.append(v)

    return non_manifold_verts

def fix_non_manifold_vertices(bm: bmesh.types.BMesh, selected_vertices: List[bmesh.types.BMVert]) -> None:
    int_layer = bm.faces.layers.int.get("ColorIndex")
    if int_layer is None:
        return

    for v in selected_vertices:
        comps = []
        poly_fan = v.link_faces

        for p in poly_fan:
            if not any(p in c for c in comps):
                visited = []
                queue = [p]

                while queue:
                    node = queue.pop(0)
                    label = node[int_layer]
                    if node not in visited:
                        visited.append(node)
                        neighbours = [f for e in node.edges for f in e.link_faces 
                                      if f in poly_fan and f[int_layer] == label and f not in visited]
                        queue.extend(neighbours)
                comps.append(visited)

        labels = {}
        for c in comps:
            label = c[0][int_layer]
            labels[label] = labels.get(label, 0) + 1

        if len(labels) < len(comps):
            v.select = True
            most_labels = max(labels.items(), key=operator.itemgetter(1))[0]

            for c in comps:
                if c[0][int_layer] == most_labels:
                    c[0].select = True

            # Note: We can't use bpy.ops inside this function, so we'll handle the selection in the operator

            after_selection = {f for f in v.link_faces if f.select}

            for f in after_selection:
                f[int_layer] = most_labels