# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
import time
import bmesh
import random
import operator
from pathlib import Path
from bpy.ops import _BPyOpsSubModOp


# bl_info = {
#     "name": "DShot92 Thesis Addon",
#     "version": (1, 5),
#     "author": "DShot92 (Original Author) <dshot92@gmail.com>",
#     "blender": (2, 90, 0),
#     "category": "3D View",
#     "location": "View3D > Tool Shelf > Thesis Addon",
#     "description": "Add-on implementing Thesis algorithm to detect non manifold vertex in a clusterized mesh with differents material indices",
#     "warning": "",
# }


def dummy_view_layer_update(context):
    pass


class MESH_OT_Thesis_Props(bpy.types.PropertyGroup):

    triangulate: bpy.props.BoolProperty(
        name="Triangulate Cuts",
        description="Triangulate Mesh Cuts",
        default=False

    )

# Progress Bar
# https://github.com/zachEastin/BlenderStuff/blob/main/progress_bar_example.py


class MESH_OT_add_test_mesh(bpy.types.Operator):
    """Add Test Mesh"""
    bl_idname = "mesh.add_test_mesh"
    bl_label = "Add Test Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    # # Allow program to select only when a vertex, edge ora face is selected in edit mode, otherwise deactivate panels buttons
    # @classmethod
    # def poll(cls, context):
    #     return context.active_object and context.active_object.type == 'MESH' and context.area.type == "VIEW_3D"

    def execute(self, context):

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
        colors = {
            "Red": (1.000000, 0.000000, 0.000000, 1.000000),
            "Blue": (0.000000, 0.001617, 1.000000, 1.000000),
            "Green": (0.004734, 1.000000, 0.000000, 1.000000),
            "Yellow": (0.800000, 0.716535, 0.000000, 1.000000),
            "Cyan": (0.000000, 0.748324, 0.800000, 1.000000),
            "Lime": (0.467342, 0.800000, 0.256636, 1.000000),
            "Pink": (0.642501, 0.000000, 0.800000, 1.000000),
            "Orange": (0.800000, 0.330545, 0.000000, 1.000000)
        }

        for col in colors.keys():

            mat = bpy.data.materials.get(col)
            if not mat:
                mat = bpy.data.materials.new(col)
                mat.diffuse_color = colors[col]

            obj_name_list = [
                slot.name for slot in bpy.context.active_object.material_slots]

            if col not in obj_name_list:
                bpy.context.active_object.data.materials.append(mat)

        self.report({'INFO'}, "Mesh Imported")

        return {'FINISHED'}


class MESH_OT_set_random_labels(bpy.types.Operator):
    """Set Random Material Index to each face of the mesh"""
    bl_idname = "mesh.set_random_labels"
    bl_label = "Set Random Labels"
    bl_options = {'REGISTER', 'UNDO'}

    # Allow program to select only when a vertex, edge ora face is selected in edit mode, otherwise deactivate panels buttons
    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'EDIT_MESH' or active_object.select_get()) and context.area.type == "VIEW_3D"

    def execute(self, context):

        start_time = time.time()

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="FACE")
        me = context.edit_object.data

        bm = bmesh.from_edit_mesh(me)

        i = 1
        for f in bm.faces:
            f.calc_center_median()
            f.material_index = i % 2
            f.material_index = random.randrange(8)
            i += 1

        me.update()

        bpy.ops.object.mode_set(mode="OBJECT")

        self.report({'INFO'}, f"Set: {time.time() - start_time} seconds")
        return {'FINISHED'}


class MESH_OT_set_labels_origin(bpy.types.Operator):
    """Set Labels"""
    bl_idname = "mesh.set_labels_origin"
    bl_label = "Set Labels"
    bl_options = {'REGISTER', 'UNDO'}

    # Allow program to select only when a vertex, edge ora face is selected in edit mode, otherwise deactivate panels buttons
    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'EDIT_MESH' or active_object.select_get()) and context.area.type == "VIEW_3D"

    def execute(self, context):

        start_time = time.time()

        obj = bpy.context.active_object

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="FACE")
        me = context.edit_object.data

        bm = bmesh.from_edit_mesh(me)

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

        me.update()
        bpy.ops.object.mode_set(mode="OBJECT")

        self.report({'INFO'}, f"Set: {time.time() - start_time} seconds")

        return {'FINISHED'}


class MESH_OT_detect_non_manifold(bpy.types.Operator):
    """Detect non manifold vertices"""
    bl_idname = "mesh.detect_non_manifold"
    bl_label = "Detect non manifold vertices"
    bl_options = {'REGISTER', 'UNDO'}

    # Allow program to select only when a vertex, edge ora face is selected in edit mode, otherwise deactivate panels buttons

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'EDIT_MESH' or active_object.select_get()) and context.area.type == "VIEW_3D"

    def execute(self, context):

        start_time = time.time()

        view_layer_update = _BPyOpsSubModOp._view_layer_update

        try:
            _BPyOpsSubModOp._view_layer_update = dummy_view_layer_update

            # Get the active mesh
            me = context.object.data

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode="OBJECT")

            # Get a BMesh representation
            bm = bmesh.new()   # create an empty BMesh
            bm.from_mesh(me)   # fill it in from a Mesh

            # Modify the BMesh, can do anything here...
            bm.verts.ensure_lookup_table()

            # Do breadth first search around each vertex
            for v in bm.verts:
                comps = []

                poly_fan = bm.verts[v.index].link_faces
                labels = {}
                for poly in poly_fan:
                    if poly.material_index not in labels:
                        labels[poly.material_index] = 1
                    else:
                        labels[poly.material_index] += 1

                if len(labels) > 1:  # vertex has only 1 label polys -> MANIFOLD 100%
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

                    if len(labels) < len(comps):
                        bm.verts[v.index].select = True

            # Update mesh
            me.update()
            bm.to_mesh(me)
            bm.free()

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")

        finally:
            _BPyOpsSubModOp._view_layer_update = view_layer_update

        self.report({'INFO'}, f"Detect: {time.time() - start_time} seconds")

        return {'FINISHED'}


class MESH_OT_cut_edge_star(bpy.types.Operator):
    """Cut edges around selected vertices"""
    bl_idname = "mesh.cut_edge_star"
    bl_label = "Cut Edge-Star around vertex"
    bl_options = {'REGISTER', 'UNDO'}

    # Allow program to select only when a vertex, edge ora face is selected in edit mode, otherwise deactivate panels buttons

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'EDIT_MESH' or active_object.select_get()) and context.area.type == "VIEW_3D"

    def execute(self, context):

        view_layer_update = _BPyOpsSubModOp._view_layer_update

        try:
            _BPyOpsSubModOp._view_layer_update = dummy_view_layer_update
            # Get bool from panel
            cut_and_triangulate = bpy.context.scene.thesis_props.triangulate

            start_time = time.time()

            # Get the active mesh
            me = context.object.data

            bpy.ops.object.mode_set(mode="EDIT")  # Activating Edit mode
            bpy.ops.object.mode_set(mode="OBJECT")  # Going back to Object mode

            # Get a BMesh representation
            bm = bmesh.new()   # create an empty BMesh
            bm.from_mesh(me)   # fill it in from a Mesh

            # Modify the BMesh, can do anything here...
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

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

            # selected_vertices = [v for v in bm.verts if v.select == True]

            bm.to_mesh(me)
            me.update()
            bm.free()

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode="OBJECT")

            # Get a BMesh representation
            bm = bmesh.new()   # create an empty BMesh
            bm.from_mesh(me)   # fill it in from a Mesh

            # Modify the BMesh, can do anything here...
            bm.verts.ensure_lookup_table()

            for v in bm.verts:
                comps = []

                poly_fan = bm.verts[v.index].link_faces
                labels = {}
                for poly in poly_fan:
                    if poly.material_index not in labels:
                        labels[poly.material_index] = 1
                    else:
                        labels[poly.material_index] += 1

                if len(labels) > 1:  # vertex has only 1 label polys -> MANIFOLD 100%
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

                    if len(labels) < len(comps):
                        bm.verts[v.index].select = True

            me.update()
            bm.to_mesh(me)
            bm.free()

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")

        finally:
            _BPyOpsSubModOp._view_layer_update = view_layer_update

        self.report({'INFO'}, f"Cut: {time.time() - start_time }seconds")

        return {'FINISHED'}


class MESH_OT_fix_non_manifold(bpy.types.Operator):
    """Fix non manifold vertices"""
    bl_idname = "mesh.fix_non_manifold"
    bl_label = "Fix non manifold vertices"
    bl_options = {'REGISTER', 'UNDO'}

    # Allow program to select only when a vertex, edge ora face is selected in edit mode, otherwise deactivate panels buttons
    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        return active_object is not None and active_object.type == 'MESH' and (context.mode == 'EDIT_MESH' or active_object.select_get()) and context.area.type == "VIEW_3D"

    def execute(self, context):

        # start time counter
        start_time = time.time()

        view_layer_update = _BPyOpsSubModOp._view_layer_update

        try:
            _BPyOpsSubModOp._view_layer_update = dummy_view_layer_update

            # Set mesh in edit vertex mode
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")

            # get edit object data
            me = context.edit_object.data

            # create BMesh data for editing
            bm = bmesh.from_edit_mesh(me)

            # Ensure vertices and faces lists exists
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            selected_vertices = [v for v in bm.verts if v.select == True]

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

                    # before_selection = {f for f in bm.faces if f.select}

                    bpy.ops.mesh.shortest_path_select(
                        use_topology_distance=True)

                    after_selection = {f for f in bm.faces if f.select}

                    # shortest_path_faces = after_selection.difference(before_selection)

                    for f in after_selection:
                        bm.faces[f.index].material_index = most_labels

            me.update()
            bm.free()

            bpy.ops.object.mode_set(mode="OBJECT")
            me.update()
            bpy.ops.object.mode_set(mode="EDIT")

        finally:
            _BPyOpsSubModOp._view_layer_update = view_layer_update

        self.report({'INFO'}, f"Fix: {time.time() - start_time} seconds")

        return {'FINISHED'}


class VIEW3D_PT_thesis(bpy.types.Panel):

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Thesis Addon"
    bl_category = "Thesis Addon"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Test Mesh")
        box.operator(
            'mesh.add_test_mesh',
            text="Test Bunny",
            icon="PROP_OFF",
        )

        box = layout.box()
        box.label(text="Set Colors")
        box.operator(
            'mesh.set_random_labels',
            text="Set Random Poly Labels",
            icon="PROP_OFF",
        )

        box.operator(
            'mesh.set_labels_origin',
            text="Set Labels (Origin Center)",
            icon="PROP_OFF",
        )

        box = layout.box()
        box.label(text="Fix")
        box.operator(
            'mesh.detect_non_manifold',
            text="Detect non manifold vertices",
            icon="PROP_OFF",
        )

        box.operator(
            'mesh.cut_edge_star',
            text="Cut Edge-Star",
            icon="SCULPTMODE_HLT",
        )
        box.prop(scene.thesis_props, "triangulate")

        box.operator(
            'mesh.fix_non_manifold',
            text="Fix non manifold vertices",
            icon="PROP_OFF",
        )

        """ self.layout.operator(
            'mesh.select_star_fan',
            text="Select Polygon Fan",
            icon="AXIS_TOP",
        ) """
        """ self.layout.operator(
            'mesh.select_vertex',
            text="Select vertex by id",
            icon="PROP_OFF",
        ) """


bl_classes = (
    MESH_OT_Thesis_Props,
    MESH_OT_add_test_mesh,
    MESH_OT_set_random_labels,
    MESH_OT_set_labels_origin,
    MESH_OT_detect_non_manifold,
    MESH_OT_cut_edge_star,
    MESH_OT_fix_non_manifold,
    VIEW3D_PT_thesis,
)


def register():
    for bl_class in bl_classes:
        bpy.utils.register_class(bl_class)
    bpy.types.Scene.thesis_props = bpy.props.PointerProperty(
        type=MESH_OT_Thesis_Props)


def unregister():
    for bl_class in bl_classes:
        bpy.utils.unregister_class(bl_class)
    del bpy.types.Scene.thesis_props
