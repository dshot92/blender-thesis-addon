# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
from . import properties, operators, panel, utils

bl_info = {
    "name": "Thesis Addon",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Thesis Addon",
    "description": "Addon for thesis project",
    "category": "Mesh",
}

def register():
    properties.register()
    operators.register()
    panel.register()

def unregister():
    panel.unregister()
    operators.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()
