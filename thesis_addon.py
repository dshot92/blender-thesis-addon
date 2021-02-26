import bpy
import time
import bmesh
import random
import operator


bl_info = {
    "name": "DShot92 Thesis Addon",
    "version": (1, 0),
    "author": "DShot92 (Original Author) <dshot92@gmail.com>",
    "blender": (2, 90, 0),
    "category": "3D View",
    "location": "View3D > Tool Shelf > Thesis Addon",
    "description": "Add-on implementing Thesis algorithm to detect non manifold vertex in a clusterized mesh with differents material indices",
    "warning": "",
    "doc_url": "https://github.com/dshot92/internship_volume_mesh",
    "tracker_url": "https://github.com/dshot92/internship_volume_mesh",
}


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

        self.report({'INFO'}, "Detect: %s seconds" %
                    (time.time() - start_time))

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

        selected_vertices = [v for v in bm.verts if v.select == True]

        edge_indices = {
            e for v in selected_vertices for e in bm.verts[v.index].link_edges}

        bmesh.ops.subdivide_edges(
            bm,
            edges=list(edge_indices),
            cuts=1,
            use_grid_fill=True,
        )

        #bmesh.ops.triangulate(bm, faces=bm.faces[:])

        #selected_vertices = [v for v in bm.verts if v.select == True]

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

        self.report({'INFO'}, "Cut: %s seconds" % (time.time() - start_time))

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

                #before_selection = {f for f in bm.faces if f.select}

                bpy.ops.mesh.shortest_path_select(use_topology_distance=True)

                after_selection = {f for f in bm.faces if f.select}

                #shortest_path_faces = after_selection.difference(before_selection)

                for f in after_selection:
                    bm.faces[f.index].material_index = most_labels

        me.update()
        bm.free()

        bpy.ops.object.mode_set(mode="OBJECT")
        me.update()
        bpy.ops.object.mode_set(mode="EDIT")

        self.report({'INFO'}, "Fix: %s seconds" % (time.time() - start_time))

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
        self.report({'INFO'}, "Set: %s seconds" % (time.time() - start_time))
        return {'FINISHED'}


class MESH_OT_set_labels(bpy.types.Operator):
    """Set Labels"""
    bl_idname = "mesh.set_labels"
    bl_label = "Set Labels"
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

        for f in bm.faces:
            x, y, z = f.calc_center_median()

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

        self.report({'INFO'}, "Set: %s seconds" % (time.time() - start_time))

        return {'FINISHED'}


class VIEW3D_PT_thesis(bpy.types.Panel):

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Thesis Addon"
    bl_category = "Thesis Addon"

    def draw(self, context):
        self.layout.operator(
            'mesh.detect_non_manifold',
            text="Detect non manifold vertices",
            icon="PROP_OFF",
        )
        self.layout.operator(
            'mesh.cut_edge_star',
            text="Cut Edge-Star",
            icon="SCULPTMODE_HLT",
        )
        self.layout.operator(
            'mesh.fix_non_manifold',
            text="Fix non manifold vertices",
            icon="PROP_OFF",
        )
        self.layout.operator(
            'mesh.set_random_labels',
            text="Set Random Poly Labels",
            icon="PROP_OFF",
        )
        self.layout.operator(
            'mesh.set_labels',
            text="Set Labels (Origin Center)",
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
    MESH_OT_detect_non_manifold,
    MESH_OT_cut_edge_star,
    MESH_OT_fix_non_manifold,
    MESH_OT_set_random_labels,
    MESH_OT_set_labels,
    VIEW3D_PT_thesis,
)


def register():
    for bl_class in bl_classes:
        bpy.utils.register_class(bl_class)


def unregister():
    for bl_class in bl_classes:
        bpy.utils.unregister_class(bl_class)
