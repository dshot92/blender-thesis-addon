import bpy
from bpy.props import BoolProperty, IntProperty, FloatProperty
from bpy.types import PropertyGroup

class MESH_OT_Thesis_Props(PropertyGroup):
    triangulate: BoolProperty(
        name="Triangulate Cuts",
        description="Triangulate Mesh Cuts",
        default=False
    )
    random_seed: IntProperty(
        name="Random Seed",
        description="Seed for random material assignment",
        default=42,
        min=0
    )
    noise_scale: FloatProperty(
        name="Noise Scale",
        description="Scale of the noise pattern for material assignment",
        default=0.1,
        min=0.01,
        soft_max=1.0
    )
    num_clusters: IntProperty(
        name="Num Clusters",
        description="Number of clusters for color assignment",
        default=8,
        min=2,
        max=100
    )
    use_voronoi: BoolProperty(
        name="Use Voronoi",
        description="Toggle between Voronoi noise and simple noise",
        default=True
    )

def register():
    bpy.utils.register_class(MESH_OT_Thesis_Props)
    bpy.types.Scene.thesis_props = bpy.props.PointerProperty(type=MESH_OT_Thesis_Props)

def unregister():
    del bpy.types.Scene.thesis_props
    bpy.utils.unregister_class(MESH_OT_Thesis_Props)