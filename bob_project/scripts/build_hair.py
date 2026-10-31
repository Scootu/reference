"""Bob - hair: a combed-back hair cap with a clean hairline + a small topknot.

Sections:
  BOB_Hair_Cap    parametric shell that follows the head with real volume (thicker at
                  the crown, tapering into a crisp edge at the hairline). UV U runs
                  around the head so the hair shader draws comb lines front-to-back.
  BOB_Hair_Bun    the topknot, sitting slightly behind the crown so it reads in profile
  BOB_Hair_Band   a gold band at the base of the topknot
"""

import math
import bpy
import bmesh
from mathutils import Vector, Matrix
import bob_common as bc


def hairline(phi):
    """Normalised height (direction z) of the hairline at azimuth phi (0 = front)."""
    # rounded arc high on the forehead (0.50), down to brow level at the
    # temples (0.15) and low at the nape (-0.35)
    return 0.1125 + 0.425 * math.cos(phi) - 0.0375 * math.cos(2 * phi)


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def cap_point(phi, zn, thick):
    s = math.sqrt(max(0.0, 1 - zn * zn))
    d = Vector((s * math.sin(phi), -s * math.cos(phi), zn))
    p = bc.head_surface_dir(d)
    return bc.HEAD_C + p + p.normalized() * thick


def build_cap(M, coll):
    SEG, ROWS = 128, 34
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    grid = []
    for r in range(-1, ROWS + 1):
        row = []
        for i in range(SEG):
            phi = -math.pi + 2 * math.pi * i / SEG
            h = hairline(phi)
            if r < 0:          # tuck row under the skin to close the edge
                zn, thick = h, -0.004
            else:
                t = r / ROWS
                zn = h + (0.992 - h) * (t ** 0.85)
                thick = 0.004 + 0.016 * smoothstep(0.0, 0.30, zn - h) + 0.020 * max(zn, 0) ** 2
            row.append(bm.verts.new(cap_point(phi, zn, thick)))
        grid.append(row)
    for r in range(len(grid) - 1):
        for i in range(SEG):
            i1 = (i + 1) % SEG
            f = bm.faces.new((grid[r][i], grid[r][i1], grid[r + 1][i1], grid[r + 1][i]))
            u0, u1 = i / SEG, (i + 1) / SEG
            v0, v1 = r / ROWS, (r + 1) / ROWS
            for loop, co in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
                loop[uv].uv = co
    top = bm.verts.new(cap_point(0, 1.0, 0.004 + 0.016 + 0.020))
    for i in range(SEG):
        i1 = (i + 1) % SEG
        f = bm.faces.new((grid[-1][i], grid[-1][i1], top))
        for loop, co in zip(f.loops, ((i / SEG, 1), ((i + 1) / SEG, 1), ((i + 0.5) / SEG, 1))):
            loop[uv].uv = co
    ob = bc.bm_to_object("BOB_Hair_Cap", bm, coll, [M["hair"]], subsurf=1, render_subsurf=2)
    return ob


def build_bun(M, coll):
    d = Vector((0.0, 0.30, 0.95)).normalized()
    base = bc.HEAD_C + bc.head_surface_dir(d) + d * 0.02
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0, calc_uvs=True)
    for v in bm.verts:
        z = v.co.z
        # slightly pear-shaped knot: narrower towards the scalp
        k = 1.0 - 0.22 * max(0.0, -z)
        v.co.x *= 0.155 * k
        v.co.y *= 0.148 * k
        v.co.z *= 0.125
    bmesh.ops.transform(bm, matrix=Matrix.Translation(base + d * 0.10) @ rot, verts=bm.verts)
    bun = bc.bm_to_object("BOB_Hair_Bun", bm, coll, [M["hair"]], subsurf=1, render_subsurf=2)

    band = bc.torus_bm(0.098, 0.020, segs=48, rsegs=12,
                       axis_matrix=Matrix.Rotation(math.radians(90), 4, "X"))
    bmesh.ops.transform(band, matrix=Matrix.Translation(base + d * 0.03) @ rot,
                        verts=band.verts)
    bc.bm_to_object("BOB_Hair_Band", band, coll, [M["gold"]], subsurf=1)
    return bun


def build(M):
    coll = bc.sub_collection("Hair")
    build_cap(M, coll)
    build_bun(M, coll)


if __name__ == "__main__":
    build(bc.get_materials())
