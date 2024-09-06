# SPDX-License-Identifier: GPL-3.0-or-later

# ----------------------------------------------------------
# Author: Daniele Stochino (dshot92)
# ----------------------------------------------------------

import importlib

from . import properties, operators, panel, utils


modules = (
    properties,
    operators,
    panel,
)

if "bpy" in locals():
    importlib.reload(properties)
    importlib.reload(operators)
    importlib.reload(panel)


def register():
    for module in modules:
        importlib.reload(module)
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()