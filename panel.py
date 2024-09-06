import bpy
from bpy.types import Panel

class VIEW3D_PT_thesis(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Thesis Addon"
    bl_category = "Thesis Addon"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Test Mesh")
        box.operator('mesh.add_test_mesh', text="Test Bunny", icon="PROP_OFF")

        box = layout.box()
        box.label(text="Set Colors")
        box.prop(scene.thesis_props, "random_seed")
        box.prop(scene.thesis_props, "noise_scale")
        box.operator('mesh.set_noise_colors', text="Set Noise-based Colors", icon="PROP_OFF")

        box = layout.box()
        box.label(text="Fix")
        box.operator('mesh.detect_non_manifold', text="Detect non manifold vertices", icon="PROP_OFF")

def register():
    bpy.utils.register_class(VIEW3D_PT_thesis)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_thesis)