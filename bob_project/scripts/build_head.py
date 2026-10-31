"""Bob - head: a large, smooth, nearly circular head with organic volume.

Quad-sphere topology (no poles, even quads) shaped by bob_common.head_surface_dir:
slightly wider than tall and flattened front-to-back so it reads as the reference's
drawn disc, with a thick charcoal inverted-hull outline.
The mesh is dense enough (~10k quads) to be ray-cast for placing facial features,
so it uses no subdivision modifier (what you ray-cast is what renders).
"""

import bpy
import bob_common as bc


def build(M):
    coll = bc.sub_collection("Head")
    bm = bc.quad_sphere(cuts=40)
    for v in bm.verts:
        v.co = bc.head_surface_dir(v.co.normalized())
    ob = bc.bm_to_object("BOB_Head", bm, coll, [M["skin"]])
    ob.location = bc.HEAD_C
    bc.add_outline(ob, 0.034)
    bpy.context.view_layer.update()
    return ob


if __name__ == "__main__":
    build(bc.get_materials())
