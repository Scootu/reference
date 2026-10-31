"""Bob - body parts that are not clothing: neck, hands, legs (trousers), shoes.

Hands are polygonised metaballs (palm + three stubby fingers + thumb) so the
fingers blend organically into the palm. Each hand carries shape keys for
"Relax", "Fist" and "Point" (index finger out), driven later from the rig.
"""

import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion
import bob_common as bc

KNUCKLE_Z = -0.072
FINGERS = [  # (name, y offset across the palm, length) - index is closest to the thumb
    ("index", -0.027, 0.034),
    ("middle", 0.0, 0.036),
    ("ring", 0.027, 0.031),
]


def smooth01(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def hand_elements():
    q_down = Quaternion((0, 1, 0), math.radians(90))     # capsule X axis -> -Z
    els = [dict(type="ELLIPSOID", co=(0, 0, -0.040), radius=0.062,
                size_x=0.40, size_y=0.78, size_z=0.80, stiffness=2.0)]
    for _, y, ln in FINGERS:
        els.append(dict(type="CAPSULE", co=(0, y, KNUCKLE_Z - ln * 0.9), radius=0.028,
                        size_x=ln, rotation=q_down, stiffness=1.6))
    thumb_dir = Vector((0.25, -0.75, -0.6)).normalized()
    q_t = Vector((1, 0, 0)).rotation_difference(thumb_dir)
    els.append(dict(type="CAPSULE", co=(0.008, -0.050, -0.045), radius=0.026, size_x=0.022,
                    rotation=q_t, stiffness=1.6))
    # wrist stub so the hand tucks into the sleeve
    els.append(dict(type="CAPSULE", co=(0, 0, 0.0), radius=0.03, size_x=0.02,
                    rotation=q_down, stiffness=1.5))
    return els


def curl_coords(co, side, amounts, thumb_amt):
    """Rotate finger vertices about the knuckle line. side +1 = left hand (palm -X)."""
    co = Vector(co)
    if co.z < KNUCKLE_Z + 0.006:
        # which finger?
        best = min(range(len(FINGERS)), key=lambda i: abs(co.y - FINGERS[i][1]))
        amt = amounts[best]
        if amt:
            depth = smooth01((KNUCKLE_Z + 0.006 - co.z) / 0.055)
            ang = math.radians(100) * amt * depth * side
            piv = Vector((0, co.y, KNUCKLE_Z))
            co = piv + Matrix.Rotation(ang, 3, "Y") @ (co - piv)
    elif co.y < -0.035 and co.z < -0.02 and thumb_amt:
        piv = Vector((0.0, -0.035, -0.03))
        co = piv + Matrix.Rotation(math.radians(55) * thumb_amt * side, 3, "Z") @ (co - piv)
    return co


def build_hand(side, M, coll):
    tag = "L" if side > 0 else "R"
    bm = bc.metaball_to_bm(hand_elements(), resolution=0.0045)
    # mirror palm direction for the right hand: geometry is symmetric in X already,
    # palms face -X (left) / +X (right) via the curl direction only.
    wrist = bc.J[f"wrist.{tag}"]
    tip = bc.J[f"hand_tip.{tag}"]
    d = (tip - wrist).normalized()
    rot = Vector((0, 0, -1)).rotation_difference(d).to_matrix().to_4x4()
    frame = Matrix.Translation(wrist) @ rot
    ob = bc.bm_to_object(f"BOB_Hand_{tag}", bm, coll, [M["skin"]])
    ob.matrix_world = frame
    me = ob.data
    base = [v.co.copy() for v in me.vertices]
    ob.shape_key_add(name="Basis")
    for name, amounts, thumb in (("Relax", (0.25, 0.3, 0.35), 0.1),
                                 ("Fist", (1.0, 1.0, 1.0), 1.0),
                                 ("Point", (0.0, 1.0, 1.0), 0.9)):
        kb = ob.shape_key_add(name=name, from_mix=False)
        for i, co in enumerate(base):
            kb.data[i].co = curl_coords(co, side, amounts, thumb)
    # scale the finished hand (and every shape key) up around the wrist
    HAND_SCALE = 1.32
    for kb in ob.data.shape_keys.key_blocks:
        for d in kb.data:
            d.co = d.co * HAND_SCALE
    for v in ob.data.vertices:
        v.co = v.co * HAND_SCALE
    bc.zero_shape_keys(ob)
    return ob


def build(M):
    coll = bc.sub_collection("Body")
    # neck (mostly hidden between collar and head)
    bm = bc.tube_along([Vector((0, 0, 1.60)), Vector((0, 0, 1.80))], [0.11, 0.11], rsegs=24)
    bc.bm_to_object("BOB_Neck", bm, coll, [M["skin"]])

    for side in (1, -1):
        tag = "L" if side > 0 else "R"
        build_hand(side, M, coll)
        # trousers: thin legs, mostly hidden by the robe
        hip, knee, ankle = (bc.J[f"{n}.{tag}"] for n in ("hip", "knee", "ankle"))
        pts, radii = [], []
        for seg, (a, b) in enumerate(((hip, knee), (knee, ankle))):
            for i in range(12):
                t = i / 12
                pts.append(a.lerp(b, t))
                radii.append(0.062 - 0.008 * (seg + t) / 2)
        pts.append(ankle + Vector((0, 0, -0.02)))
        radii.append(0.05)
        bm = bc.tube_along(pts, radii, rsegs=20)
        bc.bm_to_object(f"BOB_Leg_{tag}", bm, coll, [M["pants"]], subsurf=1)
        # shoe: rounded, slightly upturned toe, flat sole
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=1.0)
        for v in bm.verts:
            x, y, z = v.co
            front = max(0.0, -y)
            v.co = Vector((x * (0.078 + 0.012 * front), y * 0.155, z * 0.062))
            if v.co.z < -0.035:
                v.co.z = -0.035 - (v.co.z + 0.035) * 0.15
            v.co.z += 0.02 * front ** 3
        bmesh.ops.translate(bm, vec=Vector((bc.J[f"ankle.{tag}"].x, -0.055, 0.052)),
                            verts=bm.verts)
        bc.bm_to_object(f"BOB_Shoe_{tag}", bm, coll, [M["shoe"]], subsurf=1)


if __name__ == "__main__":
    build(bc.get_materials())
