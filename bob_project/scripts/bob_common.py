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
HEAD_SCALE = Vector((1.04, 0.80, 1.0))   # flattened front-to-back: reads as a drawn disc

# Colours are sRGB, measured from the reference frames (style_extraction_2_5d.md)
C = {
    "skin": (0.965, 0.969, 0.941),        # #F6F7F0 lit
    "skin_shade": (0.905, 0.895, 0.870),  # soft grey-warm edge
    "ink": (0.165, 0.137, 0.141),         # #2A2324 outlines
    "stroke": (0.227, 0.204, 0.212),      # #3A3436 facial strokes
    "eye_white": (0.98, 0.98, 0.96),
    "mouth": (0.227, 0.176, 0.184),
    "tongue": (0.55, 0.30, 0.32),
    "teeth": (0.97, 0.96, 0.93),
    "hair": (0.118, 0.125, 0.235),        # #1E203C
    "hair_stripe": (0.55, 0.54, 0.59),    # #8C8A96
    "robe": (0.149, 0.251, 0.502),        # #264080
    "robe_shade": (0.114, 0.157, 0.337),  # #1D2856
    "robe_rim": (0.306, 0.392, 0.576),    # #4E6493
    "skirt": (0.133, 0.224, 0.478),       # #22397A
    "skirt_shade": (0.118, 0.196, 0.396),
    "sash": (0.863, 0.647, 0.294),        # #DCA54B
    "sash_shade": (0.725, 0.522, 0.184),
    "trim": (0.93, 0.74, 0.30),
    "trim_shade": (0.78, 0.58, 0.20),
    "shoe": (0.17, 0.14, 0.14),
    "blush": (1.0, 0.70, 0.70),
    "tear": (0.55, 0.80, 1.0),
    "gold": (0.95, 0.76, 0.32),
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
        # the base mesh, not the evaluated one: the outline hull must not be hit
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.transform(ob.matrix_world)
        self.tree = BVHTree.FromBMesh(bm)
        bm.free()

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


# Fixed "painted" light direction (upper left, slightly in front). The character
# is unlit like a drawing: colours never change with the set lighting.
PAINT_LIGHT = Vector((-0.55, -0.45, 0.70)).normalized()


def scene_light_group():
    """Node group BOB_SceneLight: lets the flat character pick up the *hue* of the set
    lighting (blue moonlight, orange sunset) the way the reference characters do,
    while keeping the painted look. Strength = scene custom property "bob_scene_tint"
    (0 = exact palette, ~0.6 = cinematic). EEVEE only (Shader to RGB); with 0 it is a
    no-op in any engine."""
    ng = bpy.data.node_groups.get("BOB_SceneLight")
    if ng:
        return ng
    ng = bpy.data.node_groups.new("BOB_SceneLight", "ShaderNodeTree")
    ng.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    ng.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    n = ng.nodes
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    diff = n.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = n.new("ShaderNodeShaderToRGB")
    bw = n.new("ShaderNodeRGBToBW")
    mx = n.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    mx.inputs[1].default_value = 0.001
    hue = n.new("ShaderNodeVectorMath")
    hue.operation = "DIVIDE"
    bright = n.new("ShaderNodeMapRange")
    bright.inputs["To Min"].default_value = 0.45
    bright.inputs["To Max"].default_value = 1.0
    bright.clamp = True
    scale = n.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    mul = n.new("ShaderNodeVectorMath")
    mul.operation = "MULTIPLY"
    attr = n.new("ShaderNodeAttribute")
    attr.attribute_type = "VIEW_LAYER"
    attr.attribute_name = "bob_scene_tint"
    mix = n.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.clamp_factor = True
    L = ng.links.new
    L(diff.outputs[0], s2r.inputs[0])
    L(s2r.outputs["Color"], bw.inputs[0])
    L(bw.outputs[0], mx.inputs[0])
    L(s2r.outputs["Color"], hue.inputs[0])
    L(mx.outputs[0], hue.inputs[1])
    L(bw.outputs[0], bright.inputs["Value"])
    L(hue.outputs["Vector"], scale.inputs[0])
    L(bright.outputs["Result"], scale.inputs["Scale"])
    L(gi.outputs["Color"], mul.inputs[0])
    L(scale.outputs["Vector"], mul.inputs[1])
    L(attr.outputs["Fac"], mix.inputs["Factor"])
    L(gi.outputs["Color"], mix.inputs["A"])
    L(mul.outputs["Vector"], mix.inputs["B"])
    L(mix.outputs["Result"], go.inputs["Color"])
    return ng


def flat_mat(name, lit, shade=None, rim=None, rim_width=0.22, softness=0.35, alpha=1.0,
             feather=0.0):
    """Unlit 2.5D fill: lit/shade colours blended by a fixed painted light direction,
    plus an optional soft rim band on the lit side (as on the reference robe).
    feather > 0 gives drawn strokes soft brush edges (uses the decal UVs)."""
    mat = bpy.data.materials.get(name)
    if mat:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    col_socket = None
    if shade is None:
        em.inputs["Color"].default_value = (*lin(lit), 1)
    else:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        dot.inputs[1].default_value = PAINT_LIGHT
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        e = ramp.color_ramp.elements
        e[0].position = 0.5 - softness * 0.5
        e[0].color = (*lin(shade), 1)
        e[1].position = 0.5 + softness * 0.5
        e[1].color = (*lin(lit), 1)
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = -1.0
        mr.inputs["From Max"].default_value = 1.0
        nt.links.new(geo.outputs["Normal"], dot.inputs[0])
        nt.links.new(dot.outputs["Value"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
        col_socket = ramp.outputs["Color"]
        if rim:
            lw = nt.nodes.new("ShaderNodeLayerWeight")
            lw.inputs["Blend"].default_value = 0.5
            rr = nt.nodes.new("ShaderNodeValToRGB")
            rr.color_ramp.elements[0].position = 1.0 - rim_width - 0.06
            rr.color_ramp.elements[0].color = (0, 0, 0, 1)
            rr.color_ramp.elements[1].position = 1.0 - rim_width
            rr.color_ramp.elements[1].color = (1, 1, 1, 1)
            side = nt.nodes.new("ShaderNodeMath")
            side.operation = "MULTIPLY"
            lit_side = nt.nodes.new("ShaderNodeMath")
            lit_side.operation = "GREATER_THAN"
            lit_side.inputs[1].default_value = 0.52
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.inputs["B"].default_value = (*lin(rim), 1)
            nt.links.new(lw.outputs["Facing"], rr.inputs["Fac"])
            nt.links.new(mr.outputs["Result"], lit_side.inputs[0])
            nt.links.new(rr.outputs["Color"], side.inputs[0])
            nt.links.new(lit_side.outputs[0], side.inputs[1])
            nt.links.new(side.outputs[0], mix.inputs["Factor"])
            nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
            col_socket = mix.outputs["Result"]
        nt.links.new(col_socket, em.inputs["Color"])
    # route the final colour through the scene-light tint group
    grp = nt.nodes.new("ShaderNodeGroup")
    grp.node_tree = scene_light_group()
    col_in = em.inputs["Color"]
    if col_in.links:
        src = col_in.links[0].from_socket
        nt.links.remove(col_in.links[0])
        nt.links.new(src, grp.inputs["Color"])
    else:
        grp.inputs["Color"].default_value = col_in.default_value
    nt.links.new(grp.outputs["Color"], col_in)
    shader_out = em.outputs[0]
    if feather > 0.0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["UV"], sep.inputs[0])

        def edge(sock, width):
            inv = nt.nodes.new("ShaderNodeMath")
            inv.operation = "SUBTRACT"
            inv.inputs[0].default_value = 1.0
            nt.links.new(sock, inv.inputs[1])
            mn = nt.nodes.new("ShaderNodeMath")
            mn.operation = "MINIMUM"
            nt.links.new(sock, mn.inputs[0])
            nt.links.new(inv.outputs[0], mn.inputs[1])
            mr2 = nt.nodes.new("ShaderNodeMapRange")
            mr2.interpolation_type = "SMOOTHSTEP"
            mr2.inputs["From Min"].default_value = 0.0
            mr2.inputs["From Max"].default_value = width
            nt.links.new(mn.outputs[0], mr2.inputs["Value"])
            return mr2.outputs["Result"]

        a_v = edge(sep.outputs["Y"], feather)
        a_u = edge(sep.outputs["X"], feather * 0.3)
        am = nt.nodes.new("ShaderNodeMath")
        am.operation = "MULTIPLY"
        nt.links.new(a_v, am.inputs[0])
        nt.links.new(a_u, am.inputs[1])
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mxf = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(am.outputs[0], mxf.inputs[0])
        nt.links.new(tr.outputs[0], mxf.inputs[1])
        nt.links.new(em.outputs[0], mxf.inputs[2])
        shader_out = mxf.outputs[0]
        # smooth alpha (no dither grain) for the soft stroke edges
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(mat, attr, val)
            except Exception:
                pass
    if alpha < 1.0:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(shader_out, mx.inputs[2])
        shader_out = mx.outputs[0]
    nt.links.new(shader_out, out.inputs["Surface"])
    mat.diffuse_color = (*lin(lit), 1)
    return mat


def outline_material():
    """Inverted-hull outline: charcoal where the (flipped) hull faces the camera from
    behind the object, transparent elsewhere. Works in Cycles and EEVEE."""
    name = "BOB_Outline"
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*lin(C["ink"]), 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mx.inputs[0])
    nt.links.new(em.outputs[0], mx.inputs[1])
    nt.links.new(tr.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    mat.diffuse_color = (*lin(C["ink"]), 1)
    return mat


def add_outline(ob, thickness=0.026, wobble=0.45, freq=2.4):
    """Charcoal hull outline whose weight varies smoothly along the contour like a
    hand-drawn brush line (thickness between (1 - wobble) and 1 x base)."""
    from mathutils import noise
    vg = ob.vertex_groups.get("outline_weight") or ob.vertex_groups.new(name="outline_weight")
    mw = ob.matrix_world
    for v in ob.data.vertices:
        p = (mw @ v.co) * freq
        w = 0.5 + 0.5 * noise.noise(p)
        vg.add([v.index], min(1.0, max(0.0, w)), "REPLACE")
    thickness *= 1.18
    mat = outline_material()
    if mat.name not in ob.data.materials:
        ob.data.materials.append(mat)
    idx = list(ob.data.materials).index(mat)
    mod = ob.modifiers.new("Outline", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.use_even_offset = True
    mod.material_offset = idx
    mod.material_offset_rim = idx
    mod.vertex_group = vg.name
    mod.thickness_vertex_group = 1.0 - wobble
    return mod


def get_materials():
    """Create (or fetch) every Bob material for the flat 2.5D look. Returns dict."""
    M = {}
    M["skin"] = flat_mat("BOB_Skin", C["skin"], C["skin_shade"], softness=0.55)
    M["ink"] = flat_mat("BOB_Ink", C["stroke"], feather=0.12)
    M["ink_solid"] = flat_mat("BOB_InkSolid", C["stroke"])
    M["outline_ink"] = flat_mat("BOB_LineInk", C["ink"])
    M["eye_white"] = flat_mat("BOB_EyeWhite", C["eye_white"])
    M["mouth"] = flat_mat("BOB_Mouth", C["mouth"], feather=0.10)
    M["teeth"] = flat_mat("BOB_Teeth", C["teeth"])
    M["tongue"] = flat_mat("BOB_Tongue", C["tongue"])

    M["hair"] = flat_mat("BOB_Hair", C["hair"])
    # topknot cover: navy-black with thin light vertical stripes along UV U
    mat = flat_mat("BOB_HairBun", C["hair"])
    nt = mat.node_tree
    em = next(n for n in nt.nodes if n.type == "EMISSION")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.bands_direction = "X"
    wave.wave_profile = "SIN"
    wave.inputs["Scale"].default_value = 9.0
    nt.links.new(tc.outputs["UV"], wave.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.84
    ramp.color_ramp.elements[0].color = (*lin(C["hair"]), 1)
    ramp.color_ramp.elements[1].position = 0.97
    ramp.color_ramp.elements[1].color = (*lin(C["hair_stripe"]), 1)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    M["hair_bun"] = mat

    M["robe"] = flat_mat("BOB_Robe", C["robe"], C["robe_shade"], rim=C["robe_rim"])
    M["skirt"] = flat_mat("BOB_Skirt", C["skirt"], C["skirt_shade"], rim=C["robe_rim"],
                          rim_width=0.15)
    M["robe_inner"] = flat_mat("BOB_RobeInner", C["robe_shade"])
    M["sash"] = flat_mat("BOB_Sash", C["sash"], C["sash_shade"])
    M["trim"] = flat_mat("BOB_Trim", C["trim"], C["trim_shade"])
    M["gold"] = flat_mat("BOB_Gold", C["gold"], C["trim_shade"])
    M["shoe"] = flat_mat("BOB_Shoe", C["shoe"])
    M["blush"] = flat_mat("BOB_Blush", C["blush"], alpha=0.45)
    M["tear"] = flat_mat("BOB_Tear", C["tear"], (0.40, 0.66, 0.92))
    M["outline"] = outline_material()
    # aliases used by older build stages
    M["pants"] = M["outline_ink"]
    return M
