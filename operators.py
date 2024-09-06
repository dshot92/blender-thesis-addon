import bpy
import bmesh
import time
import random
from bpy.types import Operator, Context
from mathutils import noise, Color
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

        color_attribute = get_or_create_color_attribute(mesh)

        for face in mesh.polygons:
            color_attribute.data[face.index].color = (1, 1, 1, 1)

        self.report({'INFO'}, "Mesh Imported")
        return {'FINISHED'}


class MESH_OT_set_noise_colors(Operator):
    """Set Noise-based Colors to each face of the mesh"""
    bl_idname = "mesh.set_noise_colors"
    bl_label = "Set Noise-based Colors"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context: Context):
        start_time = time.time()
        obj = context.active_object
        mesh = obj.data

        bpy.ops.object.mode_set(mode="OBJECT")

        color_attribute = get_or_create_color_attribute(mesh)

        noise.seed_set(context.scene.thesis_props.random_seed)
        noise_scale = context.scene.thesis_props.noise_scale

        for face in mesh.polygons:
            center = obj.matrix_world @ face.center
            noise_value = noise.noise(center * noise_scale)
            color = Color()
            color.hsv = (noise_value, 1.0, 1.0)
            color_attribute.data[face.index].color = (*color, 1.0)

        mesh.update()

        self.report({'INFO'}, f"Set colors: {time.time() - start_time:.2f} seconds")
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


def register():
    bpy.utils.register_class(MESH_OT_add_test_mesh)
    bpy.utils.register_class(MESH_OT_set_noise_colors)
    bpy.utils.register_class(MESH_OT_detect_non_manifold)


def unregister():
    bpy.utils.unregister_class(MESH_OT_detect_non_manifold)
    bpy.utils.unregister_class(MESH_OT_set_noise_colors)
    bpy.utils.unregister_class(MESH_OT_add_test_mesh)
