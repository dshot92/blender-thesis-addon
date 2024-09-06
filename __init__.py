# SPDX-License-Identifier: GPL-3.0-or-later

# ----------------------------------------------------------
# Author: Daniele Stochino (dshot92)
# ----------------------------------------------------------

import importlib

from . import properties, operators, panel


modules = (
    operators,
    panel,
    properties,
)

if "bpy" in locals():
    importlib.reload(operators)
    importlib.reload(panel)
    importlib.reload(properties)


def register():
    for module in modules:
        importlib.reload(module)
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
