"""Bob - face: layered 3D eyes with lids, brows, nose, mouth (+teeth, tongue),
blush, tears and sweat drop.

Every feature is a separate object so the rig can drive it:
  eyes   -> eyeball (static), iris+pupil (eye bone), upper/lower lids (lid bones),
            dark rim ring + highlights (head)
  brows  -> brow bones (+ "Arch" shape key)
  mouth  -> shape keys (expressions + visemes), with matching teeth/tongue keys
  extras -> "Show" shape keys (blush, tears, sweat)
"""

import math
import bpy
import bmesh
from mathutils import Vector, Matrix
import bob_common as bc

EYE_X = 0.205          # eye centre offset from the face centre line
EYE_Z = 0.035          # eye height relative to head centre
EYE_R = 0.140          # eyeball radius
EYE_SINK = 0.68        # eyeball centre sits this * r behind the surface
LID_OPEN = math.radians(58)
BROW_Z = 0.205
MOUTH_Z = -0.245


def ell(u, p=2.0):
    return max(0.0, 1.0 - abs(u) ** p) ** 0.5


def to_local(bm, mat):
    inv = mat.inverted()
    for v in bm.verts:
        v.co = inv @ v.co


def obj_with_matrix(name, bm_world, mat, coll, mats, smooth=True, subsurf=0):
    to_local(bm_world, mat)
    ob = bc.bm_to_object(name, bm_world, coll, mats, smooth=smooth, subsurf=subsurf)
    ob.matrix_world = mat
    return ob


# ----------------------------------------------------------------------------
# Eyes
# ----------------------------------------------------------------------------

def masked_material(base, name, eye_ob, cos_limit):
    """Copy of `base` that is only visible inside the eye opening: a cone around the
    eye's forward axis, measured in the (static) eyeball's space. Lets the lids rotate
    freely without their skin or lash line ever showing outside the eye."""
    mat = bpy.data.materials.get(name)
    if mat:
        bpy.data.materials.remove(mat)
    mat = base.copy()
    mat.name = name
    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    src = out.inputs["Surface"].links[0].from_socket
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.object = eye_ob
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    div = nt.nodes.new("ShaderNodeMath")
    div.operation = "DIVIDE"
    neg = nt.nodes.new("ShaderNodeMath")
    neg.operation = "MULTIPLY"
    neg.inputs[1].default_value = -1.0
    gt = nt.nodes.new("ShaderNodeMath")
    gt.operation = "GREATER_THAN"
    gt.inputs[1].default_value = cos_limit
    transp = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(tc.outputs["Object"], ln.inputs[0])
    nt.links.new(sep.outputs["Y"], neg.inputs[0])
    nt.links.new(neg.outputs[0], div.inputs[0])
    nt.links.new(ln.outputs["Value"], div.inputs[1])
    nt.links.new(div.outputs[0], gt.inputs[0])
    nt.links.new(gt.outputs[0], mix.inputs[0])
    nt.links.new(transp.outputs[0], mix.inputs[1])
    nt.links.new(src, mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        mat.blend_method = "HASHED"
    except Exception:
        pass
    return mat


def build_eye(side, surf, M, coll):
    tag = "L" if side > 0 else "R"
    x = bc.HEAD_C.x + EYE_X * side
    z = bc.HEAD_C.z + EYE_Z
    S, N = surf.front(x, z)
    axis = (N + Vector((0, -2.4, 0))).normalized()     # mostly forward, slightly outward
    r = EYE_R
    centre = S - axis * (EYE_SINK * r)
    frame = Matrix.Translation(centre) @ bc.look_rotation(axis)
    rim_theta = math.acos(EYE_SINK)

    # eyeball (white)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=r)
    white = bc.bm_to_object(f"BOB_Eye_{tag}_White", bm, coll, [M["eye_white"]])
    white.matrix_world = frame

    # iris + pupil (two caps, one object, two materials)
    bm = bc.cap_bm(r * 1.004, math.radians(31), rings=10, segs=48)
    for f in bm.faces:
        f.material_index = 0
    pup = bc.cap_bm(r * 1.008, math.radians(15), rings=6, segs=48)
    n0 = len(bm.faces)
    bc.merge_bm(bm, pup)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n0:]:
        f.material_index = 1
    iris = bc.bm_to_object(f"BOB_Eye_{tag}_Iris", bm, coll, [M["iris"], M["pupil"]])
    iris.matrix_world = frame

    # dark rim ring where the eye meets the face
    ring_m = Matrix.Translation((0, -r * math.cos(rim_theta), 0))
    bm = bc.torus_bm(r * math.sin(rim_theta) + 0.003, 0.0165, segs=64, rsegs=14,
                     axis_matrix=ring_m)
    rim = bc.bm_to_object(f"BOB_Eye_{tag}_Rim", bm, coll, [M["rim"]])
    rim.matrix_world = frame

    # highlights (fixed to the head, so they stay put while the eye looks around)
    bm = bmesh.new()
    for ang_up, ang_side, size in ((26, -24, 8.0), (-18, 20, 3.5)):
        # same light direction for both eyes: upper-left catch-light, small lower-right one
        d = (Matrix.Rotation(math.radians(ang_side), 4, "Z")
             @ Matrix.Rotation(math.radians(-ang_up), 4, "X"))
        cap = bc.cap_bm(r * 1.013, math.radians(size), rings=3, segs=24)
        bmesh.ops.transform(cap, matrix=d, verts=cap.verts)
        bc.merge_bm(bm, cap)
    hl = bc.bm_to_object(f"BOB_Eye_{tag}_Highlight", bm, coll, [M["highlight"]])
    hl.matrix_world = frame
    hl.visible_shadow = False

    # lids: skin hemispheres pivoting on the eye centre, with a dark lash line
    def lid(name, elev, lower):
        n_up = Vector((0, math.sin(elev), math.cos(elev)))
        axis_l = -n_up if lower else n_up
        rot = bc.look_rotation(axis_l, up=Vector((0, -1, 0)) if abs(axis_l.z) > 0.9
                               else Vector((0, 0, 1)))
        rl = r * 1.035
        bm = bc.cap_bm(rl, math.radians(90), rings=16, segs=48)
        bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
        for f in bm.faces:
            f.material_index = 0
        lash = bc.torus_bm(rl, 0.011 if not lower else 0.006, segs=64, rsegs=10)
        bmesh.ops.transform(lash, matrix=rot, verts=lash.verts)
        n0 = len(bm.faces)
        bc.merge_bm(bm, lash)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n0:]:
            f.material_index = 1
        lim = math.cos(rim_theta + math.radians(3))
        mats = [masked_material(M["skin"], f"BOB_Lid_{tag}", white, lim),
                masked_material(M["rim"], f"BOB_Lash_{tag}", white, lim)]
        ob = bc.bm_to_object(name, bm, coll, mats)
        ob.matrix_world = frame
        return ob

    lid(f"BOB_Eye_{tag}_LidUp", LID_OPEN, False)
    lid(f"BOB_Eye_{tag}_LidLow", -LID_OPEN, True)
    white["eye_radius"] = r
    return frame


# ----------------------------------------------------------------------------
# Brows
# ----------------------------------------------------------------------------

def brow_points(surf, side, arch=0.018, lift=0.0, n=18):
    cx = bc.HEAD_C.x + EYE_X * side
    cz = bc.HEAD_C.z + BROW_Z + lift
    pts, nrms = [], []
    for i in range(n):
        u = -1 + 2 * i / (n - 1)
        x = cx + 0.095 * u
        # inner end (towards the centre line) a touch lower for a natural look
        z = cz + arch * (1 - u * u) + 0.008 * u * side
        p, nrm = surf.front(x, z, off=0.006)
        pts.append(p)
        nrms.append(nrm)
    return pts, nrms


def build_brow(side, surf, M, coll):
    tag = "L" if side > 0 else "R"
    n = 18
    radii = [0.012 + 0.0135 * ell(-1 + 2 * i / (n - 1), 3) for i in range(n)]
    pts, nrms = brow_points(surf, side)
    centre = pts[n // 2]
    frame = Matrix.Translation(centre) @ bc.look_rotation(nrms[n // 2])
    bm = bc.tube_along(pts, radii, rsegs=12)
    # flatten slightly against the face
    inv = frame.inverted()
    ob = obj_with_matrix(f"BOB_Brow_{tag}", bm, frame, coll, [M["brow"]])
    ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
    sk = ob.shape_key_add(name="Basis")
    arch_pts, _ = brow_points(surf, side, arch=0.045)
    bm2 = bc.tube_along(arch_pts, radii, rsegs=12)
    k = ob.shape_key_add(name="Arch", from_mix=False)
    for v, bv in zip(k.data, bm2.verts):
        v.co = inv @ bv.co
    bm2.free()
    flat_pts, _ = brow_points(surf, side, arch=-0.004)
    bm3 = bc.tube_along(flat_pts, radii, rsegs=12)
    k = ob.shape_key_add(name="Flat", from_mix=False)
    for v, bv in zip(k.data, bm3.verts):
        v.co = inv @ bv.co
    bm3.free()
    return ob


# ----------------------------------------------------------------------------
# Surface decals (mouth layers, blush)
# ----------------------------------------------------------------------------
COLS, ROWS = 36, 8


def decal_points(surf, shape, cx, cz, off):
    pts = []
    for i in range(COLS + 1):
        u = -1 + 2 * i / COLS
        x, top, bot = shape(u)
        for j in range(ROWS + 1):
            zz = bot + (top - bot) * j / ROWS
            p, _ = surf.front(cx + x, cz + zz, off=off)
            pts.append(p)
    return pts


def build_decal(name, surf, base, keys, cx, cz, off, mats, coll):
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in decal_points(surf, base, cx, cz, off)]
    uv = bm.loops.layers.uv.new("UVMap")
    for i in range(COLS):
        for j in range(ROWS):
            a = i * (ROWS + 1) + j
            b = (i + 1) * (ROWS + 1) + j
            f = bm.faces.new((verts[a], verts[b], verts[b + 1], verts[a + 1]))
            for loop, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (uu / COLS, vv / ROWS)
    ob = bc.bm_to_object(name, bm, coll, mats, smooth=True)
    ob.shape_key_add(name="Basis")
    for kname, shape in keys.items():
        kb = ob.shape_key_add(name=kname, from_mix=False)
        for v, p in zip(kb.data, decal_points(surf, shape, cx, cz, off)):
            v.co = p
    return ob


def gone(u):
    return 0.0, 0.0, 0.0


def line(w, c2=0.0, c0=0.0, th=0.0075, c1=0.0):
    def f(u):
        e = ell(u, 4)
        c = c0 + c1 * u + c2 * u * u
        return w * u, c + th * e, c - th * e
    return f


def oval(w, top, bot, p=2.0):
    def f(u):
        return w * u, top * ell(u, p), bot * ell(u, p)
    return f


MOUTH_SHAPES = {
    # name: (shape, has_open_interior)
    "Smile": (line(0.105, 0.05, -0.014, 0.009), False),
    "Frown": (line(0.08, -0.038, 0.012, 0.009), False),
    "Open": (oval(0.06, 0.022, -0.065), True),
    "Wide": (line(0.11, 0.0, 0.0, 0.006), False),
    "Narrow": (oval(0.028, 0.009, -0.009), False),
    "SmirkL": (line(0.07, 0.018, -0.002, 0.008, 0.018), False),
    "SmirkR": (line(0.07, 0.018, -0.002, 0.008, -0.018), False),
    "A": (lambda u: (0.075 * u, 0.016 * ell(u, 8), -0.10 * ell(u, 2.2)), True),
    "E": (lambda u: (0.095 * u, 0.018 * ell(u, 6), -0.038 * ell(u, 2)), True),
    "O": (oval(0.046, 0.048, -0.05), True),
    "U": (oval(0.028, 0.024, -0.026), True),
    "MBP": (line(0.06, 0.0, 0.0, 0.0035), False),
    "FV": (oval(0.068, 0.012, -0.014), True),
    "Grin": (lambda u: (0.12 * u, 0.045 * u * u + 0.012, 0.045 * u * u + 0.012
                        - 0.088 * ell(u, 2.4)), True),
    "Cry": (lambda u: (0.085 * u, 0.018 - 0.035 * u * u,
                       0.018 - 0.035 * u * u - 0.06 * ell(u, 2)), True),
}
MOUTH_BASE = line(0.064, 0.016, -0.004, 0.0085)


def teeth_shape(shape):
    def f(u):
        x, top, bot = shape(u * 0.9)
        x, top2, bot2 = shape(u)
        h = top - bot
        return x * 0.92, top - 0.003, max(bot, top - max(0.006, min(0.024, h * 0.4)))
    return f


def tongue_shape(shape):
    def f(u):
        x, top, bot = shape(u)
        h = top - bot
        return x * 0.62, bot + h * 0.42 * ell(u, 2), bot + 0.003
    return f


def build_mouth(surf, M, coll):
    cx, cz = bc.HEAD_C.x, bc.HEAD_C.z + MOUTH_Z
    mouth = build_decal("BOB_Mouth", surf, MOUTH_BASE,
                        {k: s for k, (s, _) in MOUTH_SHAPES.items()},
                        cx, cz, 0.0025, [M["mouth"]], coll)
    teeth = build_decal("BOB_Teeth", surf, gone,
                        {k: (teeth_shape(s) if o else gone) for k, (s, o) in MOUTH_SHAPES.items()},
                        cx, cz, 0.0055, [M["teeth"]], coll)
    tongue = build_decal("BOB_Tongue", surf, gone,
                         {k: (tongue_shape(s) if o and k not in ("FV", "E") else gone)
                          for k, (s, o) in MOUTH_SHAPES.items()},
                         cx, cz, 0.004, [M["tongue"]], coll)
    return mouth, teeth, tongue


# ----------------------------------------------------------------------------
# Extras
# ----------------------------------------------------------------------------

def build_extras(surf, M, coll):
    # blush
    blush = []
    for side, tag in ((1, "L"), (-1, "R")):
        blush.append(build_decal(f"BOB_Blush_{tag}", surf, gone,
                                 {"Show": oval(0.075, 0.042, -0.042)},
                                 bc.HEAD_C.x + 0.33 * side, bc.HEAD_C.z - 0.115, 0.0015,
                                 [M["blush"]], coll))
    # tears: streams running from the lower lid down the cheek
    for side, tag in ((1, "L"), (-1, "R")):
        pts = []
        n = 14
        for i in range(n):
            t = i / (n - 1)
            x = bc.HEAD_C.x + (EYE_X + 0.02 + 0.03 * t) * side
            z = bc.HEAD_C.z + EYE_Z - 0.10 - 0.30 * t
            p, _ = surf.front(x, z, off=0.008)
            pts.append(p)
        radii = [0.008 + 0.012 * math.sin(math.pi * min(1, (i + 1) / n)) for i in range(n)]
        bm = bc.tube_along(pts, radii, rsegs=10)
        ob = bc.bm_to_object(f"BOB_Tear_{tag}", bm, coll, [M["tear"]])
        ob.shape_key_add(name="Basis")
        k = ob.shape_key_add(name="Show", from_mix=False)
        # basis = collapsed at the start point, "Show" = full stream
        start = Vector(pts[0])
        for v, kv in zip(ob.data.vertices, k.data):
            kv.co = v.co.copy()
        for kv in ob.data.shape_keys.key_blocks["Basis"].data:
            kv.co = start
        for v in ob.data.vertices:
            v.co = start
    # sweat drop on the temple
    S, N = surf.towards(bc.HEAD_C + Vector((2.0, -1.2, 1.1)), Vector((-2.0, 1.2, -1.1)), off=0.03)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.045)
    for v in bm.verts:
        z = v.co.z / 0.045
        if z > 0:
            k = 1.0 - 0.85 * z
            v.co.x *= k
            v.co.y *= k
            v.co.z *= 1.9
    bmesh.ops.translate(bm, vec=S, verts=bm.verts)
    ob = bc.bm_to_object("BOB_Sweat", bm, coll, [M["tear"]])
    ob.shape_key_add(name="Basis")
    k = ob.shape_key_add(name="Show", from_mix=False)
    for v, kv in zip(ob.data.vertices, k.data):
        kv.co = v.co.copy()
    for kv in ob.data.shape_keys.key_blocks["Basis"].data:
        kv.co = S
    for v in ob.data.vertices:
        v.co = S


def build_nose(surf, M, coll):
    S, N = surf.front(bc.HEAD_C.x, bc.HEAD_C.z - 0.105)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Diagonal((0.034, 0.022, 0.028, 1)), verts=bm.verts)
    bmesh.ops.translate(bm, vec=S - N * 0.004 + Vector((0, 0, 0.004)), verts=bm.verts)
    return bc.bm_to_object("BOB_Nose", bm, coll, [M["skin"]])


def build(M):
    coll = bc.sub_collection("Face")
    head = bpy.data.objects["BOB_Head"]
    surf = bc.Surface(head)
    for side in (1, -1):
        build_eye(side, surf, M, coll)
        build_brow(side, surf, M, coll)
    build_nose(surf, M, coll)
    build_mouth(surf, M, coll)
    build_extras(surf, M, coll)
    for ob in coll.objects:
        bc.zero_shape_keys(ob)


if __name__ == "__main__":
    build(bc.get_materials())
