import bpy
import bmesh
from bpy.types import Context
from typing import List
import operator


def dummy_view_layer_update(context):
    pass


def create_color_material():
    # Create new material
    material = bpy.data.materials.new(name="Color_Material")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()

    # Create nodes
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_voronoi = nodes.new(type='ShaderNodeTexVoronoi')
    node_attribute = nodes.new(type='ShaderNodeAttribute')

    # Set up nodes
    node_attribute.attribute_name = "ColorIndex"
    node_voronoi.voronoi_dimensions = '3D'

    # Position nodes
    node_output.location = (700, 0)
    node_bsdf.location = (400, 0)
    node_voronoi.location = (200, 0)
    node_attribute.location = (0, 0)

    # Link nodes
    links = material.node_tree.links
    links.new(node_attribute.outputs["Vector"], node_voronoi.inputs["Vector"])
    links.new(node_voronoi.outputs["Color"], node_bsdf.inputs["Base Color"])
    links.new(node_bsdf.outputs["BSDF"], node_output.inputs["Surface"])

    return material


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


def analyze_vertex_manifold(bm: bmesh.types.BMesh) -> List[bmesh.types.BMVert]:
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
            labels[color_index] = labels.get(color_index, 0) + 1

        if len(labels) > 1:
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

            if len(labels) < len(comps):
                non_manifold_verts.append(v)

    return non_manifold_verts


def is_non_manifold(v: bmesh.types.BMVert, bm: bmesh.types.BMesh) -> bool:
    manifold_layer = bm.verts.layers.int.get("manifold")
    return v[manifold_layer] == 0 if manifold_layer is not None else False


def detect_non_manifold_vertices(bm: bmesh.types.BMesh) -> List[bmesh.types.BMVert]:
    return analyze_vertex_manifold(bm)


def fix_non_manifold_vertices(bm: bmesh.types.BMesh, selected_vertices: List[bmesh.types.BMVert]) -> List[bmesh.types.BMVert]:
    int_layer = bm.faces.layers.int.get("ColorIndex")
    if int_layer is None:
        return []

    fixed_vertices = []

    # Store the original selection state
    original_selection = {v: v.select for v in bm.verts}

    try:
        for v in selected_vertices:
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

                if len(labels) < len(comps):
                    most_labels = max(
                        labels.items(), key=operator.itemgetter(1))[0]

                    for c in comps:
                        for f in c:
                            f[int_layer] = most_labels

                    fixed_vertices.append(v)

    finally:
        # Restore the original selection state
        for v, was_selected in original_selection.items():
            v.select = was_selected

    return fixed_vertices


def force_reanalyze_manifold(bm: bmesh.types.BMesh):
    if "manifold" in bm.verts.layers.int:
        bm.verts.layers.int.remove(bm.verts.layers.int["manifold"])
    analyze_vertex_manifold(bm)
