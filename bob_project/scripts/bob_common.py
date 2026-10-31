"""Shared configuration and helpers for the Bob character build scripts.

Coordinate system: Z up, Bob faces -Y (front view camera looks along +Y).
Units: Blender units (Bob is ~3.1 units tall including the topknot).
"""

import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

# ----------------------------------------------------------------------------
# Design constants
# ----------------------------------------------------------------------------
HEAD_R = 0.62                      # base head radius
HEAD_C = Vector((0.0, 0.0, 2.32))  # head centre (rest pose)
HEAD_SCALE = Vector((1.03, 0.93, 1.0))

# Colours are sRGB (as picked in a colour picker); converted with lin()
C = {
    "skin": (0.965, 0.945, 0.915),
    "skin_shadow": (0.86, 0.80, 0.78),
    "hair": (0.035, 0.035, 0.045),
    "eye_white": (0.98, 0.98, 0.97),
    "iris": (0.22, 0.14, 0.09),
    "pupil": (0.015, 0.012, 0.012),
    "rim": (0.03, 0.025, 0.03),
    "brow": (0.03, 0.03, 0.035),
    "mouth": (0.32, 0.06, 0.07),
    "tongue": (0.85, 0.40, 0.42),
    "teeth": (0.97, 0.96, 0.93),
    "robe": (0.035, 0.13, 0.52),
    "robe_inner": (0.02, 0.06, 0.25),
    "trim": (0.98, 0.66, 0.06),
    "sash": (0.06, 0.09, 0.22),
    "pants": (0.07, 0.10, 0.22),
    "shoe": (0.05, 0.045, 0.045),
    "blush": (1.0, 0.55, 0.55),
    "tear": (0.55, 0.80, 1.0),
}

COLL = "BOB"

# Skeleton joint positions (rest pose). ".L" = Bob's left = +X. Mirrored for ".R".
_J = {
    "root": (0, 0, 0), "hips": (0, 0, 0.95), "spine": (0, 0, 1.15), "chest": (0, 0, 1.40),
    "neck": (0, 0, 1.62), "head": (0, 0, 1.74), "head_top": (0, 0, 2.95),
    "clavicle.L": (0.06, 0.0, 1.57), "shoulder.L": (0.33, 0.0, 1.555),
    "elbow.L": (0.49, 0.045, 1.29), "wrist.L": (0.60, 0.0, 1.035), "hand_tip.L": (0.645, -0.015, 0.915),
    "hip.L": (0.13, 0.0, 0.93), "knee.L": (0.13, -0.035, 0.50), "ankle.L": (0.13, 0.0, 0.115),
    "toe.L": (0.13, -0.17, 0.035),
}
J = {}
for _k, _v in _J.items():
    J[_k] = Vector(_v)
    if _k.endswith(".L"):
        J[_k[:-2] + ".R"] = Vector((-_v[0], _v[1], _v[2]))


def lin(c):
    def f(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return tuple(f(x) for x in c)


# ----------------------------------------------------------------------------
# Collections / objects
# ----------------------------------------------------------------------------

def collection(name=COLL, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def sub_collection(name):
    return collection(f"BOB_{name}", collection())


def remove_collection_objects(name):
    coll = bpy.data.collections.get(name)
    if not coll:
        return
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


def purge_orphans():
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                 bpy.data.metaballs, bpy.data.armatures, bpy.data.actions,
                 bpy.data.node_groups, bpy.data.lights, bpy.data.cameras):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def new_object(name, data, coll):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    ob = bpy.data.objects.new(name, data)
    coll.objects.link(ob)
    return ob


def bm_to_object(name, bm, coll, mats=(), smooth=True, subsurf=0, render_subsurf=None):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    for m in mats:
        me.materials.append(m)
    ob = new_object(name, me, coll)
    if subsurf:
        mod = ob.modifiers.new("Subdivision", "SUBSURF")
        mod.levels = subsurf
        mod.render_levels = render_subsurf if render_subsurf is not None else subsurf
    return ob


def zero_shape_keys(ob):
    """New shape keys default to 1.0 in Blender 5.x - start every key at rest."""
    keys = ob.data.shape_keys if ob.type == "MESH" else None
    if keys:
        for kb in keys.key_blocks[1:]:
            kb.value = 0.0


def merge_bm(dst, src):
    """Append bmesh src into dst (src is freed)."""
    me = bpy.data.meshes.new("_tmp")
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)


# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------

def quad_sphere(cuts=32, radius=1.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    for v in bm.verts:
        v.co = v.co.normalized() * radius
    return bm


def head_surface_dir(d):
    """Map a unit direction to the stylised head surface (head-centre relative)."""
    p = Vector(d) * HEAD_R
    p.x *= HEAD_SCALE.x
    p.y *= HEAD_SCALE.y
    p.z *= HEAD_SCALE.z
    if p.z < 0:  # fuller cheeks in the lower half
        k = 1.0 + 0.045 * min(1.0, -p.z / HEAD_R)
        p.x *= k
        p.y *= 1.0 + 0.02 * min(1.0, -p.z / HEAD_R)
    if p.z < -0.75 * HEAD_R:  # soften the very bottom
        p.z = -0.75 * HEAD_R + (p.z + 0.75 * HEAD_R) * 0.9
    return p


def look_rotation(forward, up=Vector((0, 0, 1))):
    """Matrix whose local -Y points along forward and local Z is as close to up as possible."""
    f = Vector(forward).normalized()
    x = (-f).cross(up)
    if x.length < 1e-6:
        x = Vector((1, 0, 0))
    x.normalize()
    # local axes: X = x, Y = -f, Z = x cross Y
    y = -f
    z = x.cross(y).normalized()
    return Matrix((x, y, z)).transposed().to_4x4()


def cap_bm(radius, theta, rings=8, segs=32, theta0=0.0):
    """Spherical cap around local -Y, polar angle from theta0..theta. Returns bmesh."""
    bm = bmesh.new()
    uv_rows = []
    rows = []
    for i in range(rings + 1):
        t = theta0 + (theta - theta0) * i / rings
        row = []
        n = 1 if (t == 0.0) else segs
        for j in range(n):
            a = 2 * math.pi * j / segs
            p = Vector((math.sin(t) * math.cos(a), -math.cos(t), math.sin(t) * math.sin(a)))
            row.append(bm.verts.new(p * radius))
        rows.append(row)
    for i in range(rings):
        r0, r1 = rows[i], rows[i + 1]
        for j in range(segs):
            j1 = (j + 1) % segs
            if len(r0) == 1:
                bm.faces.new((r0[0], r1[j], r1[j1]))
            else:
                bm.faces.new((r0[j], r1[j], r1[j1], r0[j1]))
    return bm


def torus_bm(major, minor, segs=48, rsegs=12, axis_matrix=Matrix()):
    """Torus in the local XZ plane (ring axis = Y)."""
    bm = bmesh.new()
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        c = Vector((math.cos(a), 0, math.sin(a)))
        ring = []
        for j in range(rsegs):
            b = 2 * math.pi * j / rsegs
            p = c * (major + minor * math.cos(b)) + Vector((0, minor * math.sin(b), 0))
            ring.append(bm.verts.new(axis_matrix @ p))
        rings.append(ring)
    for i in range(segs):
        r0, r1 = rings[i], rings[(i + 1) % segs]
        for j in range(rsegs):
            j1 = (j + 1) % rsegs
            bm.faces.new((r0[j], r1[j], r1[j1], r0[j1]))
    return bm


def tube_along(points, radii, rsegs=16, bm=None, caps=True):
    """Tube following a polyline with per-point radius. Returns bmesh."""
    bm = bm or bmesh.new()
    n = len(points)
    prev_side = None
    rings = []
    for i, p in enumerate(points):
        p = Vector(p)
        a = Vector(points[max(i - 1, 0)])
        b = Vector(points[min(i + 1, n - 1)])
        t = (b - a).normalized()
        if prev_side is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            side = t.cross(ref).normalized()
        else:
            side = (prev_side - t * prev_side.dot(t)).normalized()
        prev_side = side
        up = t.cross(side)
        ring = []
        for j in range(rsegs):
            ang = 2 * math.pi * j / rsegs
            ring.append(bm.verts.new(p + (side * math.cos(ang) + up * math.sin(ang)) * radii[i]))
        rings.append(ring)
    for i in range(n - 1):
        for j in range(rsegs):
            j1 = (j + 1) % rsegs
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][j1], rings[i][j1]))
    if caps:
        for ring, rev in ((rings[0], True), (rings[-1], False)):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            for j in range(rsegs):
                j1 = (j + 1) % rsegs
                f = (c, ring[j1], ring[j]) if rev else (c, ring[j], ring[j1])
                bm.faces.new(f)
    return bm


def metaball_to_bm(elements, resolution=0.012, threshold=0.6):
    """elements: list of dicts(type, co, radius, size_x, size_y, size_z, rotation, stiffness).
    Returns a bmesh of the polygonised metaball (in world space)."""
    mb = bpy.data.metaballs.new("_mb")
    mb.resolution = resolution
    mb.render_resolution = resolution
    mb.threshold = threshold
    for e in elements:
        el = mb.elements.new(type=e.get("type", "BALL"))
        el.co = e["co"]
        el.radius = e.get("radius", 0.1)
        el.stiffness = e.get("stiffness", 2.0)
        for k in ("size_x", "size_y", "size_z"):
            if k in e:
                setattr(el, k, e[k])
        if "rotation" in e:
            el.rotation = e["rotation"]
    ob = bpy.data.objects.new("_mb", mb)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.metaballs.remove(mb)
    bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    return bm


class Surface:
    """Ray-cast helper onto an object's evaluated mesh (world space)."""

    def __init__(self, ob):
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.transform(ob.matrix_world)
        self.tree = BVHTree.FromBMesh(bm)
        bm.free()
        ev.to_mesh_clear()

    def front(self, x, z, off=0.0, depth_dir=Vector((0, 1, 0))):
        """Hit the surface from the front (from -Y) at world x/z."""
        origin = Vector((x, -10.0, z))
        hit, nrm, _, _ = self.tree.ray_cast(origin, depth_dir)
        if hit is None:
            return None, None
        return hit + nrm * off, nrm

    def towards(self, origin, direction, off=0.0):
        hit, nrm, _, _ = self.tree.ray_cast(Vector(origin), Vector(direction).normalized())
        if hit is None:
            return None, None
        return hit + nrm * off, nrm


# ----------------------------------------------------------------------------
# Materials (Cycles / EEVEE, Principled based)
# ----------------------------------------------------------------------------

def _set(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def principled(name, color, rough=0.5, sss=0.0, sss_radius=(0.3, 0.15, 0.1), coat=0.0,
               sheen=0.0, spec=0.5, emission=None, emission_strength=0.0, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    col = (*lin(color), 1.0)
    _set(bsdf, "Base Color", col)
    _set(bsdf, "Roughness", rough)
    _set(bsdf, "Subsurface Weight", sss)
    _set(bsdf, "Subsurface Radius", sss_radius)
    _set(bsdf, "Subsurface Scale", 0.05)
    _set(bsdf, "Coat Weight", coat)
    _set(bsdf, "Coat Roughness", 0.08)
    _set(bsdf, "Sheen Weight", sheen)
    _set(bsdf, "Sheen Roughness", 0.4)
    _set(bsdf, "Specular IOR Level", spec)
    _set(bsdf, "Alpha", alpha)
    if emission:
        _set(bsdf, "Emission Color", (*lin(emission), 1.0))
        _set(bsdf, "Emission Strength", emission_strength)
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    mat.diffuse_color = col
    return mat, nt, bsdf


def add_bump(nt, bsdf, tex_node, strength=0.1, distance=0.02, output="Fac"):
    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = (-150, -300)
    bump.inputs["Strength"].default_value = strength
    if "Distance" in bump.inputs:
        bump.inputs["Distance"].default_value = distance
    nt.links.new(tex_node.outputs[output], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return bump


def get_materials():
    """Create (or fetch) every Bob material. Returns dict."""
    M = {}

    # Skin: soft off-white, light subsurface, subtle darker edge for a graphic read
    mat, nt, b = principled("BOB_Skin", C["skin"], rough=0.48, sss=0.15,
                            sss_radius=(0.6, 0.3, 0.2), spec=0.35)
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.18
    lw.location = (-500, 150)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-300, 150)
    ramp.color_ramp.elements[0].position = 0.55
    ramp.color_ramp.elements[0].color = (*lin(C["skin"]), 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (*lin(C["skin_shadow"]), 1)
    nt.links.new(lw.outputs["Facing"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    M["skin"] = mat

    # Hair: deep near-black, controlled spec, fine comb-line bump along U
    mat, nt, b = principled("BOB_Hair", C["hair"], rough=0.42, spec=0.32, coat=0.0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-800, -300)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.location = (-550, -300)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 110.0
    wave.inputs["Distortion"].default_value = 3.0
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 0.6
    nt.links.new(tc.outputs["UV"], wave.inputs["Vector"])
    add_bump(nt, b, wave, strength=0.07, distance=0.003)
    M["hair"] = mat

    M["eye_white"] = principled("BOB_EyeWhite", C["eye_white"], rough=0.25, coat=0.6,
                                sss=0.05)[0]
    mat, nt, b = principled("BOB_Iris", C["iris"], rough=0.3, coat=0.8)
    # radial gradient: lighter towards the outer iris
    M["iris"] = mat
    M["pupil"] = principled("BOB_Pupil", C["pupil"], rough=0.15, coat=1.0)[0]
    M["rim"] = principled("BOB_EyeRim", C["rim"], rough=0.6, spec=0.2)[0]
    M["brow"] = principled("BOB_Brow", C["brow"], rough=0.55, spec=0.25)[0]
    hl, nt, b = principled("BOB_EyeHighlight", (1, 1, 1), rough=0.2,
                           emission=(1, 1, 1), emission_strength=3.0)
    M["highlight"] = hl

    # Mouth interior with darker edges (UV v runs across the mouth)
    mat, nt, b = principled("BOB_Mouth", C["mouth"], rough=0.45, spec=0.3)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mth = nt.nodes.new("ShaderNodeMath")
    mth.operation = "PINGPONG"
    mth.inputs[1].default_value = 0.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*lin((0.05, 0.01, 0.015)), 1)
    ramp.color_ramp.elements[1].position = 0.22
    ramp.color_ramp.elements[1].color = (*lin(C["mouth"]), 1)
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], mth.inputs[0])
    nt.links.new(mth.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    M["mouth"] = mat
    M["teeth"] = principled("BOB_Teeth", C["teeth"], rough=0.3, coat=0.3)[0]
    M["tongue"] = principled("BOB_Tongue", C["tongue"], rough=0.4, sss=0.2)[0]

    # Cloth: rich blue, fabric sheen + subtle weave
    def cloth(name, color, sheen=0.6, scale=900.0, strength=0.06):
        mat, nt, b = principled(name, color, rough=0.78, sheen=sheen, spec=0.3)
        _set(b, "Sheen Tint", (0.75, 0.85, 1.0, 1.0))
        tc = nt.nodes.new("ShaderNodeTexCoord")
        tc.location = (-900, -300)
        mapping = nt.nodes.new("ShaderNodeMapping")
        mapping.location = (-700, -300)
        mapping.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
        w1 = nt.nodes.new("ShaderNodeTexWave")
        w1.location = (-500, -250)
        w1.bands_direction = "X"
        w1.inputs["Scale"].default_value = scale
        w2 = nt.nodes.new("ShaderNodeTexWave")
        w2.location = (-500, -450)
        w2.bands_direction = "Z"
        w2.inputs["Scale"].default_value = scale
        mix = nt.nodes.new("ShaderNodeMath")
        mix.operation = "MULTIPLY"
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 18.0
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "MULTIPLY_ADD"
        add.inputs[1].default_value = 0.6
        nt.links.new(tc.outputs["Object"], mapping.inputs["Vector"])
        nt.links.new(mapping.outputs["Vector"], w1.inputs["Vector"])
        nt.links.new(mapping.outputs["Vector"], w2.inputs["Vector"])
        nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
        nt.links.new(w1.outputs["Fac"], mix.inputs[0])
        nt.links.new(w2.outputs["Fac"], mix.inputs[1])
        nt.links.new(mix.outputs[0], add.inputs[0])
        nt.links.new(noise.outputs["Fac"], add.inputs[2])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = strength
        if "Distance" in bump.inputs:
            bump.inputs["Distance"].default_value = 0.003
        nt.links.new(add.outputs[0], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        return mat

    M["robe"] = cloth("BOB_Robe", C["robe"])
    M["robe_inner"] = cloth("BOB_RobeInner", C["robe_inner"], 0.3)
    M["sash"] = cloth("BOB_Sash", C["sash"], 0.5)
    M["pants"] = cloth("BOB_Pants", C["pants"], 0.4)
    mat, nt, b = principled("BOB_Trim", C["trim"], rough=0.38, sheen=0.4, spec=0.6, coat=0.2)
    M["trim"] = mat
    M["shoe"] = principled("BOB_Shoe", C["shoe"], rough=0.35, coat=0.4)[0]
    M["gold"] = principled("BOB_Gold", (1.0, 0.78, 0.35), rough=0.25, spec=0.8)[0]
    _set(bpy.data.materials["BOB_Gold"].node_tree.nodes["Principled BSDF"], "Metallic", 1.0)
    M["blush"] = principled("BOB_Blush", C["blush"], rough=0.5, alpha=0.55)[0]
    M["tear"] = principled("BOB_Tear", C["tear"], rough=0.05, coat=1.0, alpha=0.75)[0]
    for k in ("blush", "tear"):
        try:
            M[k].blend_method = "BLEND"
        except Exception:
            pass
    return M
