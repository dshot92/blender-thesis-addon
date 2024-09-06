import bpy
import bmesh
import time
import random
import operator
from bpy.types import Operator, Context
from mathutils import noise, Vector
from .utils import create_bmesh, update_mesh, is_non_manifold, dummy_view_layer_update, detect_non_manifold_vertices, fix_non_manifold_vertices
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
        node_output.location = (600, 0)
        node_bsdf.location = (400, 0)
        node_voronoi.location = (200, 0)
        node_attribute.location = (0, 0)

        # Link nodes
        links = material.node_tree.links
        links.new(node_attribute.outputs["Vector"], node_voronoi.inputs["Vector"])
        links.new(node_voronoi.outputs["Color"], node_bsdf.inputs["Base Color"])
        links.new(node_bsdf.outputs["BSDF"], node_output.inputs["Surface"])

        # Assign material to object
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

        self.report({'INFO'}, "Mesh Imported and Material Added")
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

        # Get or create integer attribute for color indices
        color_index_layer = bm.faces.layers.int.get("ColorIndex")
        if color_index_layer is None:
            color_index_layer = bm.faces.layers.int.new("ColorIndex")

        seed = context.scene.thesis_props.random_seed
        cluster_scale = context.scene.thesis_props.noise_scale
        use_voronoi = context.scene.thesis_props.use_voronoi

        # Set seed for both noise and random
        noise.seed_set(seed)
        random.seed(seed)

        # Number of distinct colors (now using num_clusters)
        num_clusters = context.scene.thesis_props.num_clusters

        if use_voronoi:
            # Generate Voronoi points
            voronoi_points = [Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))) * cluster_scale for _ in range(num_clusters)]
            
            for face in bm.faces:
                center = obj.matrix_world @ face.calc_center_median()
                distances = [(center - point).length_squared for point in voronoi_points]
                nearest_point_index = distances.index(min(distances))
                face[color_index_layer] = nearest_point_index
        else:
            # Use simple noise for clustering
            for face in bm.faces:
                center = obj.matrix_world @ face.calc_center_median()
                noise_value = noise.noise(center * cluster_scale)
                color_index = int((noise_value + 1) * 0.5 * num_clusters) % num_clusters
                face[color_index_layer] = color_index

        # Update mesh
        bm.to_mesh(mesh)
        bm.free()

        mesh.update()

        noise_type = "Voronoi" if use_voronoi else "Simple"
        self.report({'INFO'}, f"Set {noise_type} clustered colors: {time.time() - start_time:.2f} seconds")
        return {'FINISHED'}

class MESH_OT_detect_non_manifold(Operator):
    """Detect non manifold vertices based on face color attribute"""
    bl_idname = "mesh.detect_non_manifold"
    bl_label = "Detect non manifold vertices"
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

            me = context.object.data

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode="OBJECT")

            bm = bmesh.new()
            bm.from_mesh(me)
            bm.verts.ensure_lookup_table()

            non_manifold_verts = detect_non_manifold_vertices(bm)

            for v in non_manifold_verts:
                v.select = True

            bm.to_mesh(me)
            bm.free()
            me.update()

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")

        finally:
            _BPyOpsSubModOp._view_layer_update = view_layer_update

        self.report({'INFO'}, f"Detect: {time.time() - start_time:.2f} seconds. Found {len(non_manifold_verts)} non-manifold vertices.")
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

            int_layer = bm.faces.layers.int.get("ColorIndex")
            if int_layer is None:
                self.report({'ERROR'}, "No 'ColorIndex' face attribute found. Please set colors first.")
                return {'CANCELLED'}

            selected_vertices = [v for v in bm.verts if v.select]

            fixed_vertices = fix_non_manifold_vertices(bm, selected_vertices)

            # Clear selection
            for v in bm.verts:
                v.select = False

            # Select fixed vertices
            for v in fixed_vertices:
                v.select = True

            update_mesh(context, bm)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")

        finally:
            _BPyOpsSubModOp._view_layer_update = view_layer_update

        if fixed_vertices:
            self.report({'INFO'}, f"Fix: {time.time() - start_time:.2f} seconds. Fixed {len(fixed_vertices)} vertices.")
        else:
            self.report({'INFO'}, f"Fix: {time.time() - start_time:.2f} seconds. No vertices needed fixing.")

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

            selected_vertices = [v for v in bm.verts if v.select]
            edge_indices = {e for v in selected_vertices for e in bm.verts[v.index].link_edges}

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
