import bpy
import bmesh
import time
from bpy.types import Operator, Context
from mathutils import noise
from .utils import create_bmesh, update_mesh, is_non_manifold, MATERIAL_COLORS, dummy_view_layer_update
from bpy.ops import _BPyOpsSubModOp
from pathlib import Path

class MESH_OT_add_test_mesh(Operator):
    """Add Test Mesh"""
    bl_idname = "mesh.add_test_mesh"
    bl_label = "Add Test Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context):
        # Scene update for viewing colors
        bpy.context.scene.eevee.taa_render_samples = 16
        bpy.context.scene.eevee.use_taa_reprojection = False

        # make collection
        name = "Test_Collection"
        scene = bpy.context.scene
        coll = bpy.data.collections.get(name)

        # if it doesn't exist create it
        if coll is None:
            coll = bpy.data.collections.new(name)
        # if it is not linked to scene colleciton treelink it
        if not scene.user_of_id(coll):
            context.collection.children.link(coll)

        # Load mesh
        path = str(Path(__file__).parent / "mesh" / "bunny.obj")

        # Import obj
        bpy.ops.wm.obj_import(filepath=str(Path(path)),
                              import_vertex_groups=True)

        # Assign obj to collection
        objects = [
            obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

        for obj in objects:
            coll.objects.link(obj)
            bpy.context.scene.collection.objects.unlink(obj)

        # Add colors materials
        for col, color in MATERIAL_COLORS.items():
            mat = bpy.data.materials.get(col)
            if not mat:
                mat = bpy.data.materials.new(col)
                mat.diffuse_color = color

            obj_name_list = [
                slot.name for slot in bpy.context.active_object.material_slots]

            if col not in obj_name_list:
                bpy.context.active_object.data.materials.append(mat)

        self.report({'INFO'}, "Mesh Imported")

        return {'FINISHED'}

class MESH_OT_set_random_labels(Operator):
    """Set Noise-based Material Index to each face of the mesh"""
    bl_idname = "mesh.set_random_labels"
    bl_label = "Set Noise-based Labels"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'EDIT_MESH' or active_object.select_get()) and context.area.type == "VIEW_3D"

    def execute(self, context: Context):
        start_time = time.time()
        bpy.ops.object.mode_set(mode="EDIT")
        bm = create_bmesh(context)

        # Set the seed for the noise generator
        noise.seed_set(context.scene.thesis_props.random_seed)

        obj = context.active_object
        num_materials = len(MATERIAL_COLORS)
        noise_scale = context.scene.thesis_props.noise_scale

        for f in bm.faces:
            # Get the face center in world coordinates
            center = obj.matrix_world @ f.calc_center_median()
            
            # Generate noise value using random_unit_vector
            noise_vec = noise.random_unit_vector()
            noise_val = noise_vec.dot(center * noise_scale)
            
            # Map noise value to material index
            f.material_index = int((noise_val + 1) * 0.5 * num_materials) % num_materials

        update_mesh(context, bm)
        bpy.ops.object.mode_set(mode="OBJECT")

        self.report({'INFO'}, f"Set: {time.time() - start_time:.2f} seconds")
        return {'FINISHED'}

class MESH_OT_set_labels_origin(Operator):
    """Set Labels"""
    bl_idname = "mesh.set_labels_origin"
    bl_label = "Set Labels"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'EDIT_MESH' or active_object.select_get()) and context.area.type == "VIEW_3D"

    def execute(self, context: Context):
        start_time = time.time()
        obj = bpy.context.active_object

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="FACE")
        bm = create_bmesh(context)

        for f in bm.faces:
            x, y, z = obj.matrix_world @ f.calc_center_median()

            label_x = 0
            label_y = 0
            label_z = 0

            if x > 0:
                label_x += 1
            if y > 0:
                label_y += 10
            if z > 0:
                label_z += 100
            s = label_x + label_y + label_z
            s = str(s)
            label = int(s, 2)
            f.material_index = label

        update_mesh(context, bm)
        bpy.ops.object.mode_set(mode="OBJECT")

        self.report({'INFO'}, f"Set: {time.time() - start_time:.2f} seconds")
        return {'FINISHED'}

class MESH_OT_detect_non_manifold(Operator):
    """Detect non manifold vertices"""
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

        self.report({'INFO'}, f"Detect: {time.time() - start_time:.2f} seconds")
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
            # Get bool from panel
            cut_and_triangulate = bpy.context.scene.thesis_props.triangulate

            start_time = time.time()

            bpy.ops.object.mode_set(mode="EDIT")  # Activating Edit mode
            bpy.ops.object.mode_set(mode="OBJECT")  # Going back to Object mode

            bm = create_bmesh(context)

            # Get Selected Vertices
            selected_vertices = [v for v in bm.verts if v.select == True]

            # Retrieve the edges index from the selected vertices
            edge_indices = {
                e for v in selected_vertices for e in bm.verts[v.index].link_edges}

            # Cut each edge aound the selected vertices
            bmesh.ops.subdivide_edges(
                bm,
                edges=list(edge_indices),
                cuts=1,
                use_grid_fill=True,
            )

            # Tirangulate the mesh
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

            # Ensure we're in edit mode
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
                    most_labels = max(labels.items(), key=lambda x: x[1])[0]

                    for c in comps:
                        if bm.faces[c[0].index].material_index == most_labels:
                            bm.faces[c[0].index].select = True

                    bpy.ops.mesh.shortest_path_select(use_topology_distance=True)

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

def register():
    bpy.utils.register_class(MESH_OT_add_test_mesh)
    bpy.utils.register_class(MESH_OT_set_random_labels)
    bpy.utils.register_class(MESH_OT_set_labels_origin)
    bpy.utils.register_class(MESH_OT_detect_non_manifold)
    bpy.utils.register_class(MESH_OT_cut_edge_star)
    bpy.utils.register_class(MESH_OT_fix_non_manifold)

def unregister():
    bpy.utils.unregister_class(MESH_OT_fix_non_manifold)
    bpy.utils.unregister_class(MESH_OT_cut_edge_star)
    bpy.utils.unregister_class(MESH_OT_detect_non_manifold)
    bpy.utils.unregister_class(MESH_OT_set_labels_origin)
    bpy.utils.unregister_class(MESH_OT_set_random_labels)
    bpy.utils.unregister_class(MESH_OT_add_test_mesh)