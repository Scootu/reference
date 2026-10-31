"""Bob - clothing: blue robe with gold trim, crossed collar, sleeves with gold cuffs,
navy sash with a small knot.

The robe is a lofted surface (super-ellipse rings along a smooth Catmull-Rom profile)
with soft pleats in the skirt. Every trim is generated in the robe's own (theta, z)
parameter space so it hugs the garment exactly, including the pleats.
theta = 0 is the front centre, +theta goes towards Bob's left (+X).
"""

import math
import bpy
import bmesh
from mathutils import Vector, Matrix
import bob_common as bc

# (z, rx, ry) from the collar down to the hem
# torso column -> sash -> slightly wider skirt column (reference: 0.69 HW / 0.82 HW)
PROFILE = [
    (1.775, 0.150, 0.140),
    (1.735, 0.225, 0.185),
    (1.680, 0.325, 0.235),
    (1.620, 0.375, 0.262),
    (1.530, 0.390, 0.275),
    (1.350, 0.385, 0.280),
    (1.170, 0.380, 0.282),
    (1.080, 0.392, 0.288),
    (0.990, 0.420, 0.302),
    (0.800, 0.438, 0.315),
    (0.550, 0.452, 0.325),
    (0.300, 0.466, 0.335),
]
HEM_Z = PROFILE[-1][0]
SE_N = 2.5   # super-ellipse exponent (slightly boxy torso)


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def catmull(p0, p1, p2, p3, t):
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


def radii_at(z):
    zs = [p[0] for p in PROFILE]
    z = min(max(z, zs[-1]), zs[0])
    for i in range(len(PROFILE) - 1):
        if zs[i] >= z >= zs[i + 1]:
            t = (zs[i] - z) / (zs[i] - zs[i + 1])
            i0, i3 = max(i - 1, 0), min(i + 2, len(PROFILE) - 1)
            rx = catmull(PROFILE[i0][1], PROFILE[i][1], PROFILE[i + 1][1], PROFILE[i3][1], t)
            ry = catmull(PROFILE[i0][2], PROFILE[i][2], PROFILE[i + 1][2], PROFILE[i3][2], t)
            return rx, ry
    return PROFILE[-1][1], PROFILE[-1][2]


def robe_point(theta, z, off=0.0):
    rx, ry = radii_at(z)
    pleat = 1.0   # flat 2.5D look: clean silhouette, no pleats
    s, c = math.sin(theta), math.cos(theta)
    e = 2.0 / SE_N
    x = rx * math.copysign(abs(s) ** e, s) * pleat
    y = -ry * math.copysign(abs(c) ** e, c) * pleat
    p = Vector((x, y, z))
    if off:
        n = Vector((x / (rx * rx), y / (ry * ry), 0.0))
        dz = (radii_at(z + 0.01)[0] - radii_at(z - 0.01)[0]) / 0.02
        n.z = -dz * 0.3 / max(rx, 1e-4)
        p += n.normalized() * off
    return p


def build_robe(M, coll):
    SEG, NZ = 112, 80
    bm = bmesh.new()
    zs = [PROFILE[0][0] - (PROFILE[0][0] - HEM_Z) * (i / NZ) for i in range(NZ + 1)]
    rows = [[bm.verts.new(robe_point(2 * math.pi * j / SEG, z)) for j in range(SEG)] for z in zs]
    # hem turn-up (thickness) in the inner material
    hem_in1 = [bm.verts.new(robe_point(2 * math.pi * j / SEG, HEM_Z - 0.006) * Vector((0.985, 0.985, 1)))
               for j in range(SEG)]
    hem_in2 = [bm.verts.new(robe_point(2 * math.pi * j / SEG, HEM_Z + 0.08) * Vector((0.955, 0.955, 1)))
               for j in range(SEG)]
    rows += [hem_in1, hem_in2]
    # close the collar opening towards the neck
    neck_ring = [bm.verts.new(Vector((0.11 * math.sin(2 * math.pi * j / SEG),
                                      -0.11 * math.cos(2 * math.pi * j / SEG), 1.76)))
                 for j in range(SEG)]
    rows.insert(0, neck_ring)
    for r in range(len(rows) - 1):
        for j in range(SEG):
            j1 = (j + 1) % SEG
            f = bm.faces.new((rows[r][j], rows[r][j1], rows[r + 1][j1], rows[r + 1][j]))
            zc = sum(v.co.z for v in f.verts) / 4
            f.material_index = 1 if r >= len(rows) - 3 else (2 if zc < 1.02 else 0)
    ob = bc.bm_to_object("BOB_Robe", bm, coll, [M["robe"], M["robe_inner"], M["skirt"]],
                         subsurf=1, render_subsurf=2)
    bc.add_outline(ob, 0.028)
    return ob


def ribbon(name, path, width, off, thick, mat, coll, samples=120):
    """path: list of (theta, z) control points -> ribbon on the robe surface."""
    pts = []
    n = len(path)
    for k in range(samples + 1):
        u = k / samples * (n - 1)
        i = min(int(u), n - 2)
        t = u - i
        P = [Vector(path[max(min(j, n - 1), 0)]) for j in (i - 1, i, i + 1, i + 2)]
        q = catmull(P[0], P[1], P[2], P[3], t)
        pts.append(q)
    bm = bmesh.new()
    left, right = [], []
    for k, (th, z) in enumerate(pts):
        p = robe_point(th, z, off)
        a = robe_point(*pts[max(k - 1, 0)], off)
        b = robe_point(*pts[min(k + 1, len(pts) - 1)], off)
        tan = (b - a).normalized()
        nrm = (robe_point(th, z, off + 0.01) - p).normalized()
        side = tan.cross(nrm).normalized()
        left.append(bm.verts.new(p + side * width / 2))
        right.append(bm.verts.new(p - side * width / 2))
    for k in range(len(pts) - 1):
        bm.faces.new((left[k], right[k], right[k + 1], left[k + 1]))
    ob = bc.bm_to_object(name, bm, coll, [mat])
    sol = ob.modifiers.new("Thickness", "SOLIDIFY")
    sol.thickness = thick
    sol.offset = 1.0
    sub = ob.modifiers.new("Subdivision", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2
    bc.add_outline(ob, 0.010)
    return ob


def band(name, z0, z1, off, thick, mat, coll, SEG=112):
    bm = bmesh.new()
    rows = []
    for k in range(5):
        z = z0 + (z1 - z0) * k / 4
        rows.append([bm.verts.new(robe_point(2 * math.pi * j / SEG, z, off)) for j in range(SEG)])
    for r in range(4):
        for j in range(SEG):
            j1 = (j + 1) % SEG
            bm.faces.new((rows[r][j], rows[r][j1], rows[r + 1][j1], rows[r + 1][j]))
    ob = bc.bm_to_object(name, bm, coll, [mat])
    sol = ob.modifiers.new("Thickness", "SOLIDIFY")
    sol.thickness = thick
    sol.offset = 1.0
    sub = ob.modifiers.new("Subdivision", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2
    bc.add_outline(ob, 0.018)
    return ob


def build_collar(M, coll):
    # Outer flap (Bob's right side crossing over to his left), gold trimmed
    path_a = [(-math.pi + 0.01, 1.745), (-2.2, 1.745), (-1.3, 1.725), (-0.6, 1.69), (-0.2, 1.62),
              (0.12, 1.50), (0.38, 1.34), (0.58, 1.16), (0.66, 1.08)]
    path_b = [(math.pi - 0.01, 1.745), (2.2, 1.745), (1.3, 1.725), (0.6, 1.69), (0.25, 1.63),
              (0.05, 1.56), (-0.10, 1.50)]
    ribbon("BOB_Collar_Inner", path_b, 0.06, 0.005, 0.010, M["trim"], coll)
    ribbon("BOB_Collar_Outer", path_a, 0.065, 0.013, 0.012, M["trim"], coll)
    # the outer flap itself: a slightly raised panel edge under the trim
    flap = ribbon("BOB_Collar_Flap", path_a[3:], 0.11, 0.006, 0.008, M["robe"], coll)
    flap.modifiers.remove(flap.modifiers["Outline"])


def build_arm(side, M, coll):
    """Reference style: the arm is a single thick ink line from the torso edge."""
    tag = "L" if side > 0 else "R"
    sh, el, wr = (bc.J[f"{n}.{tag}"] for n in ("shoulder", "elbow", "wrist"))
    start = Vector((0.26 * side, 0.0, 1.57))
    ctrl = [start, sh, el, wr]
    pts = []
    N = 40
    for k in range(N + 1):
        u = k / N * 3
        i = min(int(u), 2)
        t = u - i
        P = [ctrl[max(min(j, 3), 0)] for j in (i - 1, i, i + 1, i + 2)]
        pts.append(catmull(P[0], P[1], P[2], P[3], t))
    bm = bc.tube_along(pts, [0.030] * len(pts), rsegs=16)
    return bc.bm_to_object(f"BOB_Arm_{tag}", bm, coll, [M["outline_ink"]], subsurf=1)


def build_sash(M, coll):
    band("BOB_Sash", 1.00, 1.17, 0.010, 0.014, M["sash"], coll)
    band("BOB_Hem_Trim", HEM_Z + 0.004, HEM_Z + 0.065, 0.004, 0.010, M["trim"], coll)
    # knot at the front left + two hanging tails
    th = 0.62
    p = robe_point(th, 1.09, 0.03)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=1.0)
    n = (robe_point(th, 1.09, 0.05) - p).normalized()
    rot = n.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(p) @ rot
                        @ Matrix.Diagonal((0.05, 0.065, 0.03, 1)), verts=bm.verts)
    knot = bc.bm_to_object("BOB_Sash_Knot", bm, coll, [M["sash"]], subsurf=1)
    bc.add_outline(knot, 0.012)
    for k, (dth, ln) in enumerate(((-0.06, 0.30), (0.08, 0.24))):
        path = [(th + dth * 0.3, 1.08), (th + dth * 0.7, 1.0), (th + dth, 1.08 - ln)]
        ribbon(f"BOB_Sash_Tail_{k}", path, 0.06 - 0.008 * k, 0.03 - 0.004 * k, 0.008,
               M["sash"], coll, samples=24)


def build(M):
    coll = bc.sub_collection("Clothing")
    build_robe(M, coll)
    build_collar(M, coll)
    for side in (1, -1):
        build_arm(side, M, coll)
    build_sash(M, coll)


if __name__ == "__main__":
    build(bc.get_materials())
