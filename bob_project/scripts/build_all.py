"""Build Bob from scratch and save blender/bob_character.blend.

Usage (from the bob_project folder):
    blender -b --python scripts/build_all.py
    blender -b --python scripts/build_all.py -- --stages head,face,hair --no-save

Or open this file in Blender's Scripting tab and press Run Script
(the scripts folder must sit next to it).
"""

import os
import sys
import importlib
import bpy

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    bpy.path.abspath("//scripts")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PROJECT = os.path.dirname(HERE)

STAGES = ["head", "face", "hair", "body", "clothing", "rig", "expressions"]


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stages = STAGES
    save = True
    for i, a in enumerate(argv):
        if a == "--stages":
            stages = argv[i + 1].split(",")
        if a == "--no-save":
            save = False
    return stages, save


def reset_scene():
    import bob_common as bc
    for coll in list(bpy.data.collections):
        if coll.name.startswith("BOB"):
            for ob in list(coll.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.collections.remove(coll)
    for ob in list(bpy.data.objects):
        if ob.name.startswith("BOB"):
            bpy.data.objects.remove(ob, do_unlink=True)
    bc.purge_orphans()


def main():
    stages, save = args()
    import bob_common as bc
    importlib.reload(bc)
    reset_scene()
    M = bc.get_materials()
    for st in stages:
        mod = importlib.import_module(f"build_{st}")
        importlib.reload(mod)
        print(f"[bob] building {st} ...")
        mod.build(M)
        bpy.context.view_layer.update()
    if save:
        path = os.path.join(PROJECT, "blender", "bob_character.blend")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=path)
        print(f"[bob] saved {path}")


if __name__ == "__main__":
    main()
