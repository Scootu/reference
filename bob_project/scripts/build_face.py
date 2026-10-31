"""Bob - face, flat 2.5D style (see documentation/style_extraction_2_5d.md).

Every feature is a flat "drawn" stroke lying on the head surface (ray-cast onto the
render mesh), coloured in charcoal ink, morphing with shape keys:

  BOB_Eye_{L,R}          charcoal stroke: Basis = dash (default). Keys: Closed, Happy (^),
                         Angry, Sad, Smug (half-lid "D"), Hide (for round eyes), LookX, LookY
  BOB_EyeRing/White/Pupil_{L,R}   round "surprised" eye (ring, white, dot pupil): key Show
                         (+ LookX/LookY on the pupil)
  BOB_Brow_{L,R}         brow stroke: Up, Down, Angry, Worried, Arch, Flat, Squeeze
  BOB_Mouth / Teeth / Tongue   mouth shapes + visemes (matching keys)
  BOB_Blush_*, BOB_Tear_*, BOB_Sweat   extras (key Show)
"""

import math
import bpy
import bmesh
from mathutils import Vector, Matrix
import bob_common as bc

EYE_X = 0.150
EYE_Z = 0.005
BROW_Z = 0.150
MOUTH_Z = -0.255
LOOK_DX, LOOK_DZ = 0.035, 0.028


def ell(u, p=2.0):
    return max(0.0, 1.0 - abs(u) ** p) ** 0.5


def gone(u):
    return 0.0, 0.0, 0.0


# ----------------------------------------------------------------------------
# Decal machinery
# ----------------------------------------------------------------------------
COLS, ROWS = 36, 6


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
    """keys: name -> shape  or  name -> (shape, dx, dz)"""
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
    ob.visible_shadow = False
    ob.shape_key_add(name="Basis")
    for kname, spec in keys.items():
        shape, dx, dz = spec if isinstance(spec, tuple) else (spec, 0.0, 0.0)
        kb = ob.shape_key_add(name=kname, from_mix=False)
        for v, p in zip(kb.data, decal_points(surf, shape, cx + dx, cz + dz, off)):
            v.co = p
    bc.zero_shape_keys(ob)
    return ob


def stroke(w, th, c=lambda u: 0.0, p=2.4):
    """A brush stroke: half width w, half thickness th, centre-line c(u), rounded ends."""
    def f(u):
        e = ell(u, p)
        cc = c(u)
        return w * u, cc + th * e, cc - th * e
    return f


def disc(r):
    return lambda u: (r * u, r * ell(u), -r * ell(u))


# ----------------------------------------------------------------------------
# Eyes
# ----------------------------------------------------------------------------

def eye_shapes(side):
    dash = stroke(0.092, 0.027, p=3.0)
    closed = stroke(0.085, 0.0095, c=lambda u: -0.004 - 0.008 * u * u, p=3.0)
    happy = stroke(0.082, 0.012, c=lambda u: 0.024 * (1 - u * u) - 0.012, p=3.0)
    angry = stroke(0.086, 0.025, c=lambda u: 0.024 * u * side - 0.004, p=3.0)
    sad = stroke(0.084, 0.020, c=lambda u: -0.022 * u * side + 0.004, p=3.0)

    def smug(u):  # flat lid line with a half-disc pupil hanging below
        top = 0.012 * ell(u, 6) + 0.004
        pup = 0.050 * max(0.0, 1 - (u / 0.48) ** 2) ** 0.5
        return 0.10 * u, top, -0.008 * ell(u, 6) - pup

    def tiny(u):
        return 0.004 * u, 0.0, 0.0

    return dash, {
        "Closed": closed, "Happy": happy, "Angry": angry, "Sad": sad, "Smug": smug,
        "Hide": tiny, "LookX": (dash, LOOK_DX, 0.0), "LookY": (dash, 0.0, LOOK_DZ),
    }


def build_eyes(surf, M, coll):
    for side, tag in ((1, "L"), (-1, "R")):
        cx = bc.HEAD_C.x + EYE_X * side
        cz = bc.HEAD_C.z + EYE_Z
        base, keys = eye_shapes(side)
        build_decal(f"BOB_Eye_{tag}", surf, base, keys, cx, cz, 0.004, [M["ink"]], coll)
        # round "surprised" eye: ring (filled ink disc) + white + dot pupil
        build_decal(f"BOB_EyeRing_{tag}", surf, gone, {"Show": disc(0.094)}, cx, cz + 0.01,
                    0.0035, [M["ink_solid"]], coll)
        build_decal(f"BOB_EyeWhite_{tag}", surf, gone, {"Show": disc(0.066)}, cx, cz + 0.01,
                    0.0055, [M["eye_white"]], coll)
        build_decal(f"BOB_EyePupil_{tag}", surf, gone,
                    {"Show": disc(0.026), "LookX": (gone, LOOK_DX * 0.9, 0.0),
                     "LookY": (gone, 0.0, LOOK_DZ * 0.9)},
                    cx, cz + 0.01, 0.0075, [M["ink_solid"]], coll)


# ----------------------------------------------------------------------------
# Brows
# ----------------------------------------------------------------------------

def build_brows(surf, M, coll):
    for side, tag in ((1, "L"), (-1, "R")):
        def brow(lift=0.0, slope=0.0, arch=0.012, side=side):
            # slope > 0 lowers the inner end (towards the centre line) => angry
            return stroke(0.096, 0.020,
                          c=lambda u: arch * (1 - u * u) + lift + slope * u * side, p=2.2)
        keys = {
            "Up": brow(0.060),
            "Down": brow(-0.035),
            "Angry": brow(-0.010, 0.036),
            "Worried": brow(0.018, -0.034),
            "Arch": brow(0.004, 0.0, 0.040),
            "Flat": brow(0.0, 0.0, -0.004),
            "Squeeze": (brow(), -0.024 * side, 0.0),
        }
        build_decal(f"BOB_Brow_{tag}", surf, brow(0.0, 0.006), keys,
                    bc.HEAD_C.x + EYE_X * side, bc.HEAD_C.z + BROW_Z, 0.004, [M["ink"]], coll)


# ----------------------------------------------------------------------------
# Mouth
# ----------------------------------------------------------------------------

def line(w, c2=0.0, c0=0.0, th=0.0085, c1=0.0):
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
    # name: (shape, open interior?)
    "Smile": (line(0.095, 0.045, -0.012, 0.010), False),
    "Frown": (line(0.075, -0.036, 0.012, 0.010), False),
    "Open": (lambda u: (0.065 * u, 0.012 * ell(u, 8), -0.070 * ell(u, 2.2)), True),
    "Wide": (line(0.10, 0.0, 0.0, 0.008), False),
    "Narrow": (oval(0.026, 0.020, -0.020), False),
    "SmirkL": (line(0.065, 0.016, -0.002, 0.009, 0.020), False),
    "SmirkR": (line(0.065, 0.016, -0.002, 0.009, -0.020), False),
    "A": (lambda u: (0.075 * u, 0.014 * ell(u, 8), -0.095 * ell(u, 2.2)), True),
    "E": (lambda u: (0.090 * u, 0.016 * ell(u, 6), -0.036 * ell(u, 2)), True),
    "O": (oval(0.042, 0.045, -0.045), True),
    "U": (oval(0.026, 0.024, -0.024), True),
    "MBP": (line(0.058, 0.0, 0.0, 0.006), False),
    "FV": (oval(0.062, 0.012, -0.014), True),
    "Grin": (lambda u: (0.11 * u, 0.04 * u * u + 0.012, 0.04 * u * u + 0.012
                        - 0.085 * ell(u, 2.4)), True),
    "Cry": (lambda u: (0.08 * u, 0.018 - 0.035 * u * u,
                       0.018 - 0.035 * u * u - 0.055 * ell(u, 2)), True),
}
MOUTH_BASE = oval(0.030, 0.016, -0.016)     # small "o" dot, as in the reference


def teeth_shape(shape):
    def f(u):
        x, top, bot = shape(u * 0.9)
        h = top - bot
        return x * 0.9, top - 0.004, max(bot, top - max(0.006, min(0.022, h * 0.35)))
    return f


def tongue_shape(shape):
    def f(u):
        x, top, bot = shape(u)
        h = top - bot
        return x * 0.6, bot + h * 0.40 * ell(u, 2), bot + 0.003
    return f


def build_mouth(surf, M, coll):
    cx, cz = bc.HEAD_C.x, bc.HEAD_C.z + MOUTH_Z
    build_decal("BOB_Mouth", surf, MOUTH_BASE, {k: s for k, (s, _) in MOUTH_SHAPES.items()},
                cx, cz, 0.0035, [M["mouth"]], coll)
    build_decal("BOB_Teeth", surf, gone,
                {k: (teeth_shape(s) if o and k == "Grin" else gone)
                 for k, (s, o) in MOUTH_SHAPES.items()},
                cx, cz, 0.0065, [M["teeth"]], coll)
    build_decal("BOB_Tongue", surf, gone,
                {k: (tongue_shape(s) if o and k in ("Open", "A", "O", "Grin", "Cry") else gone)
                 for k, (s, o) in MOUTH_SHAPES.items()},
                cx, cz, 0.005, [M["tongue"]], coll)


# ----------------------------------------------------------------------------
# Extras
# ----------------------------------------------------------------------------

def build_extras(surf, M, coll):
    for side, tag in ((1, "L"), (-1, "R")):
        build_decal(f"BOB_Blush_{tag}", surf, gone, {"Show": oval(0.07, 0.03, -0.03)},
                    bc.HEAD_C.x + 0.30 * side, bc.HEAD_C.z - 0.13, 0.002, [M["blush"]], coll)
        # tear stream: a flat stroke running down the cheek
        build_decal(f"BOB_Tear_{tag}", surf, gone,
                    {"Show": lambda u: (0.017 * u, -0.02 * ell(u, 2), -0.24 + 0.02 * u * u)},
                    bc.HEAD_C.x + (EYE_X + 0.02) * side, bc.HEAD_C.z + EYE_Z - 0.02, 0.006,
                    [M["tear"]], coll)
    # sweat drop: flat teardrop card on the temple
    S, N = surf.towards(bc.HEAD_C + Vector((2.0, -1.4, 1.0)), Vector((-2.0, 1.4, -1.0)),
                        off=0.02)
    bm = bmesh.new()
    pts = []
    for i in range(40):
        a = 2 * math.pi * i / 40
        x, z = math.sin(a), -math.cos(a)
        z = z if z < 0 else z * (1 + 0.9 * z)
        x *= 1 - 0.75 * max(z, 0) / 1.9
        pts.append((x * 0.045, z * 0.045))
    c = bm.verts.new((0, 0, 0))
    ring = [bm.verts.new((x, 0, z)) for x, z in pts]
    for i in range(len(ring)):
        bm.faces.new((c, ring[(i + 1) % len(ring)], ring[i]))
    rot = (-N).to_track_quat("-Y", "Z").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(S) @ rot, verts=bm.verts)
    ob = bc.bm_to_object("BOB_Sweat", bm, coll, [M["tear"]], smooth=False)
    ob.shape_key_add(name="Basis")
    k = ob.shape_key_add(name="Show", from_mix=False)
    for v, kv in zip(ob.data.vertices, k.data):
        kv.co = v.co.copy()
    for kv in ob.data.shape_keys.key_blocks["Basis"].data:
        kv.co = S
    for v in ob.data.vertices:
        v.co = S
    bc.zero_shape_keys(ob)


def build(M):
    coll = bc.sub_collection("Face")
    head = bpy.data.objects["BOB_Head"]
    surf = bc.Surface(head)
    build_eyes(surf, M, coll)
    build_brows(surf, M, coll)
    build_mouth(surf, M, coll)
    build_extras(surf, M, coll)


if __name__ == "__main__":
    build(bc.get_materials())
