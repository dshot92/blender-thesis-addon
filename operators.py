import bpy
import bmesh
import time
import random
import operator
from bpy.types import Operator, Context
from mathutils import noise, Color, Vector
from .utils import create_bmesh, update_mesh, is_non_manifold, dummy_view_layer_update, get_or_create_color_attribute
from bpy.ops import _BPyOpsSubModOp
from pathlib import Path


class MESH_OT_add_test_mesh(Operator):
    """Add Test Mesh"""
    bl_idname = "mesh.add_test_mesh"
    bl_label = "Add Test Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context):
        path = str(Path(__file__).parent / "mesh" / "bunny.obj")
        bpy.ops.wm.obj_import(filepath=str(Path(path)), import_vertex_groups=True)

        obj = context.active_object
        mesh = obj.data

        # Create BMesh
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # Remove existing color layers
        while bm.faces.layers.float_color:
            bm.faces.layers.float_color.remove(bm.faces.layers.float_color[-1])

        # Create new color layer
        color_layer = bm.faces.layers.float_color.new("Color")

        # Set all colors to white
        for face in bm.faces:
            face[color_layer] = (1, 1, 1, 1)

        # Update mesh
        bm.to_mesh(mesh)
        bm.free()

        mesh.update()

        self.report({'INFO'}, "Mesh Imported")
        return {'FINISHED'}


class MESH_OT_set_noise_colors(Operator):
    """Set Clustered Colors to each face of the mesh"""
    bl_idname = "mesh.set_noise_colors"
    bl_label = "Set Clustered Colors"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context: Context):
        start_time = time.time()
        obj = context.active_object
        mesh = obj.data

        bpy.ops.object.mode_set(mode="OBJECT")

        # Create BMesh
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # Get or create color layer
        color_layer = bm.faces.layers.float_color.get("Color")
        if color_layer is None:
            color_layer = bm.faces.layers.float_color.new("Color")

        random.seed(context.scene.thesis_props.random_seed)
        cluster_scale = context.scene.thesis_props.noise_scale
        use_voronoi = context.scene.thesis_props.use_voronoi

        # Define distinct colors
        distinct_colors = [
            (1, 0, 0, 1),  # Red
            (0, 1, 0, 1),  # Green
            (0, 0, 1, 1),  # Blue
            (1, 1, 0, 1),  # Yellow
            (1, 0, 1, 1),  # Magenta
            (0, 1, 1, 1),  # Cyan
            (1, 0.5, 0, 1),  # Orange
            (0.5, 0, 1, 1),  # Purple
        ]

        if use_voronoi:
            # Generate Voronoi points
            num_points = context.scene.thesis_props.voronoi_points
            voronoi_points = [Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))) * cluster_scale for _ in range(num_points)]
            
            for face in bm.faces:
                center = obj.matrix_world @ face.calc_center_median()
                distances = [(center - point).length_squared for point in voronoi_points]
                nearest_point_index = distances.index(min(distances))
                color_index = nearest_point_index % len(distinct_colors)
                face[color_layer] = distinct_colors[color_index]
        else:
            # Use simple noise for clustering
            for face in bm.faces:
                center = obj.matrix_world @ face.calc_center_median()
                noise_value = noise.noise(center * cluster_scale)
                color_index = int((noise_value + 1) * 4) % len(distinct_colors)
                face[color_layer] = distinct_colors[color_index]

        # Update mesh
        bm.to_mesh(mesh)
        bm.free()

        mesh.update()

        noise_type = "Voronoi" if use_voronoi else "Simple"
        self.report({'INFO'}, f"Set {noise_type} clustered colors: {time.time() - start_time:.2f} seconds")
        return {'FINISHED'}


class MESH_OT_detect_non_manifold(Operator):
    """Detect non manifold vertices"""
    bl_idname = "mesh.detect_non_manifold"
    bl_label = "Detect non manifold vertices"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context: Context):
        start_time = time.time()
        view_layer_update = _BPyOpsSubModOp._view_layer_update

        try:
            _BPyOpsSubModOp._view_layer_update = dummy_view_layer_update

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action='DESELECT')
            bm = create_bmesh(context)

            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

            for v in bm.verts:
                if is_non_manifold(v, bm):
                    v.select = True

            update_mesh(context, bm)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")

        finally:
            _BPyOpsSubModOp._view_layer_update = view_layer_update

        self.report(
            {'INFO'}, f"Detect: {time.time() - start_time:.2f} seconds")
        return {'FINISHED'}


class MESH_OT_fix_non_manifold(Operator):
    """Fix non manifold vertices"""
    bl_idname = "mesh.fix_non_manifold"
    bl_label = "Fix non manifold vertices"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'EDIT_MESH' or active_object.select_get()) and context.area.type == "VIEW_3D"

    def execute(self, context: Context):
        start_time = time.time()
        view_layer_update = _BPyOpsSubModOp._view_layer_update

        try:
            _BPyOpsSubModOp._view_layer_update = dummy_view_layer_update

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")

            bm = create_bmesh(context)

            selected_vertices = [v for v in bm.verts if v.select]

            bpy.ops.mesh.select_mode(type="FACE")

            for v in selected_vertices:
                comps = []
                bpy.ops.mesh.select_all(action='DESELECT')

                poly_fan = bm.verts[v.index].link_faces

                for p in poly_fan:
                    already_checked = False
                    for c in comps:
                        if p in c:
                            already_checked = True
                    if not already_checked:
                        visited = []
                        queue = [p]

                        while queue:
                            node = queue.pop(0)
                            label = node.material_index
                            if node not in visited:
                                visited.append(node)
                                neighbours = []
                                for e in node.edges:
                                    for f in e.link_faces:
                                        if f in poly_fan and f.material_index == label and f not in neighbours and f not in visited:
                                            neighbours.append(f)
                                    for neighbour in neighbours:
                                        queue.append(neighbour)
                        comps.append(visited)

                labels = {}
                for c in comps:
                    if bm.faces[c[0].index].material_index not in labels:
                        labels[bm.faces[c[0].index].material_index] = 1
                    else:
                        labels[bm.faces[c[0].index].material_index] += 1

                if len(labels) < len(comps):
                    bm.verts[v.index].select = True
                    most_labels = max(
                        labels.items(), key=operator.itemgetter(1))[0]

                    for c in comps:
                        if bm.faces[c[0].index].material_index == most_labels:
                            bm.faces[c[0].index].select = True

                    bpy.ops.mesh.shortest_path_select(
                        use_topology_distance=True)

                    after_selection = {f for f in bm.faces if f.select}

                    for f in after_selection:
                        bm.faces[f.index].material_index = most_labels

            update_mesh(context, bm)
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.mode_set(mode="EDIT")

        finally:
            _BPyOpsSubModOp._view_layer_update = view_layer_update

        self.report({'INFO'}, f"Fix: {time.time() - start_time:.2f} seconds")
        return {'FINISHED'}


class MESH_OT_cut_edge_star(Operator):
    """Cut edges around selected vertices"""
    bl_idname = "mesh.cut_edge_star"
    bl_label = "Cut Edge-Star around vertex"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'EDIT_MESH' or active_object.select_get()) and context.area.type == "VIEW_3D"

    def execute(self, context: Context):
        view_layer_update = _BPyOpsSubModOp._view_layer_update

        try:
            _BPyOpsSubModOp._view_layer_update = dummy_view_layer_update
            cut_and_triangulate = bpy.context.scene.thesis_props.triangulate

            start_time = time.time()

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.object.mode_set(mode="OBJECT")

            bm = create_bmesh(context)

            selected_vertices = [v for v in bm.verts if v.select == True]

            edge_indices = {
                e for v in selected_vertices for e in bm.verts[v.index].link_edges}

            bmesh.ops.subdivide_edges(
                bm,
                edges=list(edge_indices),
                cuts=1,
                use_grid_fill=True,
            )

            if cut_and_triangulate:
                bmesh.ops.triangulate(bm, faces=bm.faces[:])

            update_mesh(context, bm)

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode="OBJECT")

            bm = create_bmesh(context)

            for v in bm.verts:
                if is_non_manifold(v, bm):
                    v.select = True

            update_mesh(context, bm)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")

        finally:
            _BPyOpsSubModOp._view_layer_update = view_layer_update

        self.report({'INFO'}, f"Cut: {time.time() - start_time:.2f} seconds")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MESH_OT_add_test_mesh)
    bpy.utils.register_class(MESH_OT_set_noise_colors)
    bpy.utils.register_class(MESH_OT_detect_non_manifold)
    bpy.utils.register_class(MESH_OT_fix_non_manifold)
    bpy.utils.register_class(MESH_OT_cut_edge_star)


def unregister():
    bpy.utils.unregister_class(MESH_OT_cut_edge_star)
    bpy.utils.unregister_class(MESH_OT_fix_non_manifold)
    bpy.utils.unregister_class(MESH_OT_detect_non_manifold)
    bpy.utils.unregister_class(MESH_OT_set_noise_colors)
    bpy.utils.unregister_class(MESH_OT_add_test_mesh)
