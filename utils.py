import bpy
import bmesh
from bpy.types import Context
from typing import List
import operator
from collections import defaultdict


def dummy_view_layer_update(context):
    pass


def create_color_material():
    """
    Creates and returns a new material with nodes set up for color visualization based on the 'ColorIndex' attribute.

    This function sets up a node-based material that uses the 'ColorIndex' attribute to generate a color
    visualization. It uses a Voronoi texture node to create a varied color pattern based on the attribute value.

    Returns:
        bpy.types.Material: The created material with the color visualization setup.
    """
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
    """
    Creates and returns a BMesh object from the active mesh in the given context.
    """
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
    """
    Updates the active mesh in the given context with the provided BMesh data.
    """
    if context.edit_object:
        me = context.edit_object.data
        bmesh.update_edit_mesh(me)
    else:
        me = context.active_object.data
        bm.to_mesh(me)
        me.update()
    bm.free()


def analyze_vertex_manifold(bm: bmesh.types.BMesh) -> List[bmesh.types.BMVert]:
    """
    Analyzes the given BMesh to detect non-manifold vertices based on face color indices.

    Algorithm:
    1. For each vertex, examine its adjacent faces (poly_fan).
    2. Count the occurrences of each color index in the adjacent faces.
    3. If there's more than one color, perform a connected component analysis:
       - Use a breadth-first search to find connected faces of the same color.
    4. If the number of distinct colors is less than the number of connected components,
       the vertex is considered non-manifold.

    This approach detects vertices where faces of the same color are not continuously connected,
    indicating a potential non-manifold condition in the color-based representation.

    Args:
        bm (bmesh.types.BMesh): The BMesh to analyze.

    Returns:
        List[bmesh.types.BMVert]: A list of detected non-manifold vertices.
    """
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
    """
    Wrapper function for analyze_vertex_manifold.
    """
    return analyze_vertex_manifold(bm)


def fix_non_manifold_vertices(bm: bmesh.types.BMesh, selected_vertices: List[bmesh.types.BMVert]) -> List[bmesh.types.BMVert]:
    int_layer = bm.faces.layers.int.get("ColorIndex")
    if int_layer is None:
        return []

    fixed_vertices = []
    original_selection = {v: v.select for v in bm.verts}

    try:
        for v in selected_vertices:
            immediate_fan = list(v.link_faces)
            
            # Count occurrences of each color in the immediate fan
            color_counts = defaultdict(int)
            for face in immediate_fan:
                color_counts[face[int_layer]] += 1

            if len(color_counts) <= 1:
                continue  # Vertex is already manifold

            # Identify disconnected clusters
            clusters = []
            for face in immediate_fan:
                if not any(face in cluster for cluster in clusters):
                    cluster = []
                    color = face[int_layer]
                    stack = [face]
                    while stack:
                        current_face = stack.pop()
                        if current_face not in cluster and current_face in immediate_fan and current_face[int_layer] == color:
                            cluster.append(current_face)
                            stack.extend(adj for edge in current_face.edges for adj in edge.link_faces if adj in immediate_fan)
                    clusters.append(cluster)

            # If there are disconnected clusters of the same color, connect them
            most_common_color = max(color_counts, key=color_counts.get)
            target_clusters = [c for c in clusters if c[0][int_layer] == most_common_color]

            if len(target_clusters) > 1:
                changes_made = False
                for i in range(1, len(target_clusters)):
                    # Find the shortest path between clusters
                    bridge = find_shortest_bridge(target_clusters[0], target_clusters[i], immediate_fan)
                    
                    # Change the color of bridge faces
                    for face in bridge:
                        if face[int_layer] != most_common_color:
                            face[int_layer] = most_common_color
                            changes_made = True

                if changes_made:
                    fixed_vertices.append(v)

    finally:
        # Restore the original selection state
        for v, was_selected in original_selection.items():
            v.select = was_selected

    return fixed_vertices

def find_shortest_bridge(cluster1, cluster2, all_faces):
    # Find the shortest path of faces connecting two clusters
    start_faces = set(cluster1)
    end_faces = set(cluster2)
    queue = [(face, [face]) for face in start_faces]
    visited = set(start_faces)

    while queue:
        current_face, path = queue.pop(0)
        if current_face in end_faces:
            return path[1:-1]  # Return the bridge faces (excluding start and end)

        for edge in current_face.edges:
            for adjacent_face in edge.link_faces:
                if adjacent_face in all_faces and adjacent_face not in visited:
                    visited.add(adjacent_face)
                    queue.append((adjacent_face, path + [adjacent_face]))

    return []  # No path found


def force_reanalyze_manifold(bm: bmesh.types.BMesh):
    if "manifold" in bm.verts.layers.int:
        bm.verts.layers.int.remove(bm.verts.layers.int["manifold"])
    analyze_vertex_manifold(bm)
