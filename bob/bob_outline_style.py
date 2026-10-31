"""
BOB (outline style) - original cartoon character generator for Blender 4.2+ / 5.x

"2D cartoon in a 3D world": thick black outlines, flat colours, big white
round head with drawn-on face, stick arms with stubby hands, emotion symbols.

HOW TO USE
  Scripting tab -> Open this file -> Run Script, then press Space to play.
  Headless:  blender -b --python bob_outline_style.py -o //bob_ -f 60
  Re-running the script rebuilds Bob cleanly (no duplicates).

CONTROLS
  Select "Bob_CONTROLS" -> Object Properties -> Custom Properties.
  Every face shape, symbol, hand pose and head motion is a slider there.
  Move/rotate "Bob_Hand_L" / "Bob_Hand_R" to pose the arms, "Bob_ROOT" to move him.
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
SKIN = (0.98, 0.97, 0.94)
INK = (0.02, 0.02, 0.02)
HAIR = (0.24, 0.14, 0.08)
TUNIC = (0.86, 0.63, 0.14)        # mustard yellow
ROBE = (0.62, 0.42, 0.10)         # darker mustard for the long lower robe
BELT = (0.10, 0.36, 0.20)         # dark green band
COLLAR = (0.97, 0.96, 0.92)
SCARF = (0.82, 0.12, 0.10)
SWEAT = (0.45, 0.75, 1.00)
ANGER = (0.90, 0.10, 0.10)
SPARKLE = (1.00, 0.85, 0.25)
BACKGROUND = (0.78, 0.72, 0.66)

OUTLINE = 0.034                   # outline thickness (Blender units)
HEAD_R = 0.85
NECK_PIVOT = 0.80                 # head centre above the neck pivot
NECK_Z = 2.15
FPS = 24
END = 288
RES = (1080, 1920)

COLL_NAME = "Bob"


def _lin(c):
    """Config colours are sRGB (like a colour picker); Blender wants linear."""
    def f(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return tuple(f(x) for x in c)

# ----------------------------------------------------------------------------
# Scene helpers
# ----------------------------------------------------------------------------

def clean():
    coll = bpy.data.collections.get(COLL_NAME)
    if coll:
        for ob in list(coll.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    for ob in list(bpy.data.objects):
        if ob.name.startswith(("Bob_", "BobCam", "BobSun")):
            bpy.data.objects.remove(ob, do_unlink=True)
    for coll_data in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                      bpy.data.cameras, bpy.data.lights, bpy.data.actions):
        for block in list(coll_data):
            if block.users == 0:
                coll_data.remove(block)
    if coll is None:
        coll = bpy.data.collections.new(COLL_NAME)
        bpy.context.scene.collection.children.link(coll)
    return coll


COLL = None
MATS = {}


def link(ob):
    COLL.objects.link(ob)
    return ob


def flat_mat(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    color = _lin(color)
    em.inputs["Color"].default_value = (*color, 1)
    nt.links.new(em.outputs[0], out.inputs[0])
    mat.diffuse_color = (*color, 1)
    return mat


def toon_mat(name, color, shadow=0.82):
    """Flat colour with a soft 2-tone cel shadow (EEVEE)."""
    color = _lin(color)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    e = ramp.color_ramp.elements
    e[0].color = (color[0] * shadow, color[1] * shadow, color[2] * shadow, 1)
    e[1].position = 0.12
    e[1].color = (*color, 1)
    nt.links.new(diff.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs[0])
    mat.diffuse_color = (*color, 1)
    return mat


def outline_mat():
    mat = flat_mat("Bob_M_Outline", INK)
    mat.use_backface_culling = True
    return mat


def mesh_ob(name, bm, mat, parent=None, outline=True, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = link(bpy.data.objects.new(name, me))
    me.materials.append(mat)
    if parent:
        ob.parent = parent
    if outline:
        me.materials.append(MATS["outline"])
        mod = ob.modifiers.new("Outline", "SOLIDIFY")
        mod.thickness = OUTLINE
        mod.offset = 1.0
        mod.use_flip_normals = True
        mod.use_rim = False
        mod.use_even_offset = True
        mod.material_offset = 1
    return ob


def sphere(r=1.0, u=48, v=32, scale=(1, 1, 1), loc=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    bmesh.ops.transform(bm, matrix=Matrix.Diagonal((*scale, 1)), verts=bm.verts)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    return bm


def capsule_bm(rx, ry, z0, z1, cap_h, segs=48):
    """Tube from z0 to z1 with a rounded top cap of height cap_h."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=32, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        if z >= 0:
            v.co = Vector((x * rx, y * ry, z1 + z * cap_h))
        else:
            # squash lower hemisphere into a straight tube with flat bottom
            k = math.sqrt(max(0.0, 1 - z * z))
            f = 1.0 if z > -0.97 else k / max(math.sqrt(1 - 0.97 ** 2), 1e-4)
            n = Vector((x, y, 0))
            n = n.normalized() if n.length > 1e-6 else n
            v.co = Vector((n.x * rx * f, n.y * ry * f, z1 + (z0 - z1) * (-z)))
    return bm


def add_driver(id_block, path, ctrl, props, expr, index=-1):
    fc = id_block.driver_add(path, index) if index >= 0 else id_block.driver_add(path)
    d = fc.driver
    d.type = "SCRIPTED"
    for p in props:
        var = d.variables.new()
        var.name = p
        var.targets[0].id = ctrl
        var.targets[0].data_path = f'["{p}"]'
    d.expression = expr
    return fc


def key_driver(ob, key, ctrl, props, expr):
    kb = ob.data.shape_keys.key_blocks[key]
    kb.slider_min = -1.0
    add_driver(kb, "value", ctrl, props, expr)


# ----------------------------------------------------------------------------
# Face decals: shapes drawn on the head surface. A shape maps u in [-1, 1] to
# (x, top, bottom) relative to the decal centre (head units).
# ----------------------------------------------------------------------------
COLS, ROWS = 28, 4


def ell(u, p=2.0):
    return max(0.0, 1.0 - abs(u) ** p) ** 0.5


def head_point(x, z, off):
    r = HEAD_R + off
    y = -math.sqrt(max(r * r - x * x - z * z, 1e-4))
    return Vector((x, y, z + NECK_PIVOT))


def decal_pts(shape, cx, cz, off):
    pts = []
    for i in range(COLS + 1):
        u = -1 + 2 * i / COLS
        x, top, bot = shape(u)
        for j in range(ROWS + 1):
            z = bot + (top - bot) * j / ROWS
            pts.append(head_point(cx + x, cz + z, off))
    return pts


def grid_faces(bm, verts, cols, rows):
    for i in range(cols):
        for j in range(rows):
            a = i * (rows + 1) + j
            b = (i + 1) * (rows + 1) + j
            bm.faces.new((verts[a], verts[b], verts[b + 1], verts[a + 1]))


def decal(name, base, keys, cx, cz, off, mat, parent):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in decal_pts(base, cx, cz, off)]
    grid_faces(bm, vs, COLS, ROWS)
    ob = mesh_ob(name, bm, mat, parent, outline=False, smooth=False)
    ob.shape_key_add(name="Basis")
    for kname, (shape, dx, dz) in keys.items():
        kb = ob.shape_key_add(name=kname, from_mix=False)
        for v, p in zip(kb.data, decal_pts(shape, cx + dx, cz + dz, off)):
            v.co = p
    return ob


def gone(u):
    return 0.0, 0.0, 0.0


# ----------------------------------------------------------------------------
# Flat 2D symbol cards (in the XZ plane, facing the camera at -Y)
# ----------------------------------------------------------------------------

def strip_bm(bm, pts2d, width, y, taper=False):
    """Thick polyline in XZ plane at depth y."""
    n = len(pts2d)
    left, right = [], []
    for i, p in enumerate(pts2d):
        a = Vector(pts2d[max(i - 1, 0)])
        b = Vector(pts2d[min(i + 1, n - 1)])
        t = (b - a).normalized()
        nrm = Vector((-t.y, t.x))
        w = width * 0.5
        if taper:
            w *= 0.35 + 0.65 * math.sin(math.pi * i / (n - 1))
        p = Vector(p)
        left.append(bm.verts.new((p.x + nrm.x * w, y, p.y + nrm.y * w)))
        right.append(bm.verts.new((p.x - nrm.x * w, y, p.y - nrm.y * w)))
    for i in range(n - 1):
        bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))


def fan_bm(bm, pts2d, y, center=(0, 0)):
    c = bm.verts.new((center[0], y, center[1]))
    ring = [bm.verts.new((p[0], y, p[1])) for p in pts2d]
    for i in range(len(ring)):
        bm.faces.new((c, ring[i], ring[(i + 1) % len(ring)]))


def drop_outline(scale=1.0, n=40):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x = math.sin(a)
        z = -math.cos(a)
        # pull the top into a point
        z = z if z < 0 else z * (1 + 0.9 * z)
        x = x * (1 - 0.75 * max(z, 0) / 1.9)
        pts.append((x * 0.07 * scale, z * 0.07 * scale))
    return pts


def symbol_card(name, parent, loc, builder):
    bm = bmesh.new()
    builder(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    ob.parent = parent
    ob.location = loc
    return ob


# ----------------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------------

def build():
    global COLL
    COLL = clean()
    scn = bpy.context.scene
    scn.render.fps = FPS
    scn.frame_start, scn.frame_end = 1, END
    scn.render.resolution_x, scn.render.resolution_y = RES

    MATS.update({
        "outline": outline_mat(),
        "skin": toon_mat("Bob_M_Skin", SKIN, 0.86),
        "ink": flat_mat("Bob_M_Ink", INK),
        "white": flat_mat("Bob_M_White", (1, 1, 1)),
        "hair": toon_mat("Bob_M_Hair", HAIR, 0.75),
        "tunic": toon_mat("Bob_M_Tunic", TUNIC),
        "robe": toon_mat("Bob_M_Robe", ROBE),
        "belt": toon_mat("Bob_M_Belt", BELT),
        "collar": flat_mat("Bob_M_Collar", COLLAR),
        "scarf": toon_mat("Bob_M_Scarf", SCARF),
        "sweat": flat_mat("Bob_M_Sweat", SWEAT),
        "anger": flat_mat("Bob_M_Anger", ANGER),
        "sparkle": flat_mat("Bob_M_Sparkle", SPARKLE),
    })
    M = MATS

    # ---- control object --------------------------------------------------
    ctrl = link(bpy.data.objects.new("Bob_CONTROLS", None))
    ctrl.empty_display_type = "CIRCLE"
    ctrl.empty_display_size = 0.35
    ctrl.location = (1.6, 0, 3.6)
    ctrl.rotation_euler = (math.radians(90), 0, 0)
    props = [
        ("eyes_deadpan", 1.0), ("eyes_shocked", 0), ("eyes_closed", 0),
        ("eyes_squint", 0), ("blink", 0), ("look_x", 0), ("look_y", 0),
        ("brow_smug", 0), ("brow_angry", 0), ("brow_worried", 0), ("brow_raise", 0),
        ("mouth_small_o", 0), ("mouth_flat", 0), ("mouth_open_talk", 0),
        ("mouth_smile", 0), ("mouth_frown", 0), ("mouth_grin", 0),
        ("sweat_drop", 0), ("anger_mark", 0), ("sparkle", 0), ("question", 0),
        ("hand_L_point", 0), ("hand_L_fist", 0), ("hand_R_point", 0), ("hand_R_fist", 0),
        ("head_turn", 0), ("head_tilt", 0), ("head_nod", 0),
    ]
    for p, v in props:
        ctrl[p] = float(v)
        lo = -1.0 if p.startswith(("look", "head")) else 0.0
        ctrl.id_properties_ui(p).update(min=lo, max=1.0, soft_min=lo, soft_max=1.0)

    root = link(bpy.data.objects.new("Bob_ROOT", None))
    root.empty_display_type = "ARROWS"

    # ---- body ------------------------------------------------------------
    mesh_ob("Bob_Robe", capsule_bm(0.60, 0.50, 0.0, 1.20, 0.05), M["robe"], root)
    mesh_ob("Bob_Tunic", capsule_bm(0.56, 0.47, 1.05, 1.80, 0.38), M["tunic"], root)
    mesh_ob("Bob_Belt", capsule_bm(0.575, 0.485, 1.12, 1.30, 0.0), M["belt"], root)

    # V collar: two white strips on the chest front
    def tunic_y(x, z, off):
        rx, ry = 0.56, 0.47
        h = 1.0
        if z > 1.80:
            h = max(1e-4, 1 - ((z - 1.80) / 0.38) ** 2)
        s = max(1e-4, h - (x / rx) ** 2)
        return -ry * math.sqrt(s) - off

    def collar_builder(width, off):
        def build(bm):
            for side in (1, -1):
                pts = [(side * (0.22 - 0.22 * t), 2.02 - 0.40 * t) for t in
                       [i / 10 for i in range(11)]]
                n = len(pts)
                left, right = [], []
                for i, (x, z) in enumerate(pts):
                    w = width * 0.5
                    left.append(bm.verts.new((x - w, tunic_y(x - w, z, off), z)))
                    right.append(bm.verts.new((x + w, tunic_y(x + w, z, off), z)))
                for i in range(n - 1):
                    bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))
        return build

    for nm, w, off, mat in (("Bob_CollarLine", 0.13, 0.006, M["ink"]),
                            ("Bob_Collar", 0.08, 0.012, M["collar"])):
        bm = bmesh.new()
        collar_builder(w, off)(bm)
        mesh_ob(nm, bm, mat, root, outline=False, smooth=False)

    # Scarf: ring at the neck + a short tail
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=40, radius1=0.46, radius2=0.36,
                          depth=0.20, matrix=Matrix.Translation((0, 0, 2.12)))
    bmesh.ops.transform(bm, matrix=Matrix.Diagonal((1, 0.88, 1, 1)), verts=bm.verts)
    mesh_ob("Bob_Scarf", bm, M["scarf"], root)
    tail = capsule_bm(0.09, 0.04, 1.55, 1.95, 0.08)
    bmesh.ops.transform(tail, matrix=Matrix.Rotation(math.radians(-12), 4, "Y"),
                        verts=tail.verts)
    bmesh.ops.translate(tail, vec=(0.68, -0.48, 0.16), verts=tail.verts)
    mesh_ob("Bob_ScarfTail", tail, M["scarf"], root)

    # ---- head ------------------------------------------------------------
    head = link(bpy.data.objects.new("Bob_Head", None))
    head.parent = root
    head.location = (0, 0, NECK_Z)
    head.empty_display_size = 0.2
    mesh_ob("Bob_Skull", sphere(HEAD_R, 64, 40, loc=(0, 0, NECK_PIVOT)), M["skin"], head)

    # Hair: cap + rounded spikes leaning forward
    hair = sphere(HEAD_R * 1.04, 64, 40)

    def hairline(y):
        t = min(max((y + 0.35) / 0.75, 0), 1)
        t = t * t * (3 - 2 * t)
        return 0.50 + (-0.30 - 0.50) * t

    bmesh.ops.delete(hair, geom=[v for v in hair.verts if v.co.z < hairline(v.co.y)],
                     context="VERTS")
    spikes = [((0.05, -0.55, 0.85), 0.34), ((-0.35, -0.45, 0.80), 0.30),
              ((0.42, -0.40, 0.80), 0.28), ((-0.10, -0.05, 1.0), 0.32),
              ((0.30, 0.10, 0.95), 0.28), ((-0.55, 0.10, 0.80), 0.26),
              ((0.10, 0.50, 0.85), 0.26)]
    for d, ln in spikes:
        d = Vector(d).normalized()
        tip = (d + Vector((0, -1.1, -0.15))).normalized()
        rot = tip.to_track_quat("Z", "Y").to_matrix().to_4x4()
        mat = Matrix.Translation(d * HEAD_R * 0.96 + tip * ln * 0.45) @ rot \
            @ Matrix.Diagonal((0.20, 0.15, ln, 1))
        e = bmesh.new()
        bmesh.ops.create_uvsphere(e, u_segments=20, v_segments=12, radius=1.0)
        bmesh.ops.transform(e, matrix=mat, verts=e.verts)
        tmp = bpy.data.meshes.new("tmp")
        e.to_mesh(tmp)
        e.free()
        hair.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    bmesh.ops.translate(hair, vec=(0, 0, NECK_PIVOT), verts=hair.verts)
    mesh_ob("Bob_Hair", hair, M["hair"], head)

    # ---- face ------------------------------------------------------------
    EX, EZ = 0.25, 0.02          # eye centre
    LX, LZ = 0.05, 0.04          # look offsets

    def eye_open(u):            # basis: small black oval eyes
        return 0.055 * u, 0.075 * ell(u), -0.075 * ell(u)

    def eye_deadpan(u):         # thick dash, heavier flat top
        return 0.12 * u, 0.034 * ell(u, 6), -0.030 * ell(u, 2)

    def eye_closed(u):
        e = ell(u, 4)
        return 0.11 * u, -0.01 + 0.011 * e, -0.01 - 0.011 * e

    def eye_squint(u):
        e = ell(u, 6)
        return 0.12 * u, 0.012 * e, -0.012 * e

    eye_keys = {"Deadpan": (eye_deadpan, 0, 0), "Closed": (eye_closed, 0, 0),
                "Squint": (eye_squint, 0, 0), "Hide": (gone, 0, 0),
                "LookX": (eye_open, LX, 0), "LookY": (eye_open, 0, LZ)}

    def ring(r):
        return lambda u: (r * u, r * ell(u), -r * ell(u))

    eyes, shock_parts, pupils = [], [], []
    for s, t in ((1, "L"), (-1, "R")):
        cx = EX * s
        eyes.append(decal(f"Bob_Eye_{t}", eye_open, eye_keys, cx, EZ, 0.004, M["ink"], head))
        shock_parts.append(decal(f"Bob_ShockRing_{t}", gone, {"Show": (ring(0.115), 0, 0)},
                                 cx, EZ + 0.01, 0.003, M["ink"], head))
        shock_parts.append(decal(f"Bob_ShockWhite_{t}", gone, {"Show": (ring(0.085), 0, 0)},
                                 cx, EZ + 0.01, 0.006, M["white"], head))
        pupils.append(decal(f"Bob_ShockPupil_{t}", gone, {
            "Show": (ring(0.032), 0, 0), "LookX": (gone, LX * 0.8, 0),
            "LookY": (gone, 0, LZ * 0.8)}, cx, EZ + 0.01, 0.009, M["ink"], head))

    # Brows (inner end is u = -s)
    def brow(lift=0.0, slope=0.0, arch=0.012):
        def f(u):
            c = arch * (1 - u * u) + lift + slope * u
            th = 0.016 * ell(u, 6) + 0.005
            return 0.085 * u, c + th, c - th
        return f

    brows = []
    for s, t in ((1, "L"), (-1, "R")):
        keys = {
            "Smug": (brow(-0.045, 0.02 * s) if s > 0 else brow(0.04, -0.035 * s), 0, 0),
            "Angry": (brow(-0.02, 0.05 * s, 0.0), 0, 0),
            "Worried": (brow(0.03, -0.045 * s), 0, 0),
            "Raise": (brow(0.08), 0, 0),
        }
        brows.append(decal(f"Bob_Brow_{t}", brow(0.0, 0.012 * s), keys,
                           EX * s, 0.21, 0.005, M["ink"], head))

    # Mouth
    MZ = -0.24

    def m_base(u):
        return 0.06 * u, 0.035 * ell(u), -0.035 * ell(u)

    def m_o(u):
        return 0.075 * u, 0.085 * ell(u), -0.085 * ell(u)

    def m_flat(u):
        e = ell(u, 6)
        return 0.12 * u, 0.016 * e, -0.016 * e

    def m_talk(u):
        return 0.13 * u, 0.016 * ell(u, 8), -0.13 * ell(u, 2.2)

    def m_smile(u):
        e = ell(u, 4)
        c = 0.06 * u * u - 0.02
        return 0.13 * u, c + 0.014 * e, c - 0.014 * e

    def m_frown(u):
        e = ell(u, 4)
        c = 0.02 - 0.06 * u * u
        return 0.11 * u, c + 0.014 * e, c - 0.014 * e

    def m_grin(u):
        top = 0.06 * u * u + 0.01
        return 0.17 * u, top, top - 0.16 * ell(u, 2.4)

    mouth = decal("Bob_Mouth", m_base, {
        "SmallO": (m_o, 0, 0), "Flat": (m_flat, 0, 0), "Talk": (m_talk, 0, 0),
        "Smile": (m_smile, 0, 0), "Frown": (m_frown, 0, 0), "Grin": (m_grin, 0, 0),
    }, 0.0, MZ, 0.004, M["ink"], head)

    def teeth(u):
        x, top, bot = m_grin(u * 0.9)
        return x, top - 0.012, max(bot, top - 0.055)

    teeth_ob = decal("Bob_Teeth", gone, {"Grin": (teeth, 0, 0)}, 0.0, MZ, 0.007,
                     M["white"], head)

    # ---- symbols (2D cards parented to the head) ---------------------------
    def sweat_builder(bm):
        fan_bm(bm, drop_outline(1.35), 0.004)          # ink border (behind)
        tmp = bmesh.new()
        fan_bm(tmp, drop_outline(1.0), 0.0)
        for f in tmp.faces:
            pass
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        tmp.free()
        n0 = len(bm.faces)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n0:]:
            f.material_index = 1

    sweat = symbol_card("Bob_Sym_Sweat", head, (0.62, -0.80, NECK_PIVOT + 0.45), sweat_builder)
    sweat.data.materials.append(M["ink"])
    sweat.data.materials.append(M["sweat"])

    def anger_builder(bm):
        for qx, qz in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            pts = []
            for i in range(9):
                a = math.radians(90) * i / 8
                # quarter arcs bulging towards the centre
                pts.append((qx * (0.10 - 0.06 * math.cos(a)), qz * (0.10 - 0.06 * math.sin(a))))
            strip_bm(bm, pts, 0.035, 0.0)

    anger = symbol_card("Bob_Sym_Anger", head, (-0.55, -0.75, NECK_PIVOT + 0.55), anger_builder)
    anger.data.materials.append(M["anger"])

    def sparkle_builder(bm):
        for a in (-35, 0, 35):
            r = math.radians(a)
            d = Vector((math.sin(r), math.cos(r)))
            pts = [tuple(d * (0.05 + 0.13 * i / 6)) for i in range(7)]
            strip_bm(bm, pts, 0.04, 0.0, taper=True)

    sparkle = symbol_card("Bob_Sym_Sparkle", head, (0.80, -0.55, NECK_PIVOT + 0.55), sparkle_builder)
    sparkle.rotation_euler = (0, math.radians(-40), 0)
    sparkle.data.materials.append(M["sparkle"])

    def question_builder(bm):
        pts = []
        for i in range(16):
            a = math.radians(160 - 250 * i / 15)
            pts.append((0.09 * math.cos(a), 0.10 + 0.09 * math.sin(a)))
        pts += [(0.0, -0.02), (0.0, -0.06)]
        strip_bm(bm, pts, 0.045, 0.0)
        ring_pts = [(0.026 * math.cos(2 * math.pi * i / 16),
                     -0.13 + 0.026 * math.sin(2 * math.pi * i / 16)) for i in range(16)]
        fan_bm(bm, ring_pts, 0.0, (0, -0.13))

    question = symbol_card("Bob_Sym_Question", head, (-0.75, -0.6, NECK_PIVOT + 0.75),
                           question_builder)
    question.data.materials.append(M["ink"])

    for ob, p in ((sweat, "sweat_drop"), (anger, "anger_mark"),
                  (sparkle, "sparkle"), (question, "question")):
        for i in range(3):
            add_driver(ob, "scale", ctrl, [p], p, i)

    # ---- face drivers -------------------------------------------------------
    CL = "min(1, blink + eyes_closed)"
    for e in eyes:
        key_driver(e, "Deadpan", ctrl, ["eyes_deadpan", "blink", "eyes_closed", "eyes_squint"],
                   f"eyes_deadpan*(1-{CL})*(1-eyes_squint)")
        key_driver(e, "Closed", ctrl, ["blink", "eyes_closed"], CL)
        key_driver(e, "Squint", ctrl, ["eyes_squint", "blink", "eyes_closed"],
                   f"eyes_squint*(1-{CL})")
        key_driver(e, "Hide", ctrl, ["eyes_shocked"], "eyes_shocked")
        key_driver(e, "LookX", ctrl, ["look_x"], "look_x")
        key_driver(e, "LookY", ctrl, ["look_y"], "look_y")
    for p in shock_parts:
        key_driver(p, "Show", ctrl, ["eyes_shocked", "blink"], "eyes_shocked*(1-blink)")
    for p in pupils:
        key_driver(p, "Show", ctrl, ["eyes_shocked", "blink"], "eyes_shocked*(1-blink)")
        key_driver(p, "LookX", ctrl, ["look_x"], "look_x")
        key_driver(p, "LookY", ctrl, ["look_y"], "look_y")
    for b in brows:
        key_driver(b, "Smug", ctrl, ["brow_smug"], "brow_smug")
        key_driver(b, "Angry", ctrl, ["brow_angry"], "brow_angry")
        key_driver(b, "Worried", ctrl, ["brow_worried"], "brow_worried")
        key_driver(b, "Raise", ctrl, ["brow_raise", "eyes_shocked"],
                   "min(1, brow_raise + 0.5*eyes_shocked)")
    for k, p in (("SmallO", "mouth_small_o"), ("Flat", "mouth_flat"),
                 ("Talk", "mouth_open_talk"), ("Smile", "mouth_smile"),
                 ("Frown", "mouth_frown"), ("Grin", "mouth_grin")):
        key_driver(mouth, k, ctrl, [p], p)
    key_driver(teeth_ob, "Grin", ctrl, ["mouth_grin"], "mouth_grin")

    head.rotation_mode = "XYZ"
    add_driver(head, "rotation_euler", ctrl, ["head_nod"], "-0.35*head_nod", 0)
    add_driver(head, "rotation_euler", ctrl, ["head_tilt"], "0.30*head_tilt", 1)
    add_driver(head, "rotation_euler", ctrl, ["head_turn"], "0.55*head_turn", 2)

    # ---- arms + hands -----------------------------------------------------
    bpy.context.view_layer.update()
    hands = {}
    for s, t in ((1, "L"), (-1, "R")):
        shoulder = Vector((0.50 * s, -0.05, 1.78))
        rest = Vector((0.76 * s, -0.08, 1.10))
        cu = bpy.data.curves.new(f"Bob_Arm_{t}", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = 0.026
        cu.bevel_resolution = 3
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(2)
        for bp, p in zip(sp.bezier_points,
                         (shoulder, (shoulder + rest) / 2 + Vector((0.10 * s, 0, 0)), rest)):
            bp.co = p
            bp.handle_left_type = bp.handle_right_type = "AUTO"
        cu.materials.append(M["ink"])
        arm = link(bpy.data.objects.new(f"Bob_Arm_{t}", cu))
        arm.parent = root

        hc = link(bpy.data.objects.new(f"Bob_Hand_{t}", None))
        hc.empty_display_type = "SPHERE"
        hc.empty_display_size = 0.1
        hc.parent = root
        hc.location = rest
        hc.rotation_mode = "XYZ"
        bpy.context.view_layer.update()
        mod = arm.modifiers.new("Hook", "HOOK")
        mod.object = hc
        mod.vertex_indices_set([6, 7, 8])
        mod.matrix_inverse = (arm.matrix_world.inverted() @ hc.matrix_world).inverted()

        # Hand: palm + 3 stubby fingers + thumb, fingers point down (-Z)
        hb = sphere(0.055, 16, 12, scale=(1.0, 0.8, 1.0))
        fingers = []          # (vertex index range, base point)
        specs = [(-0.035 * s, 0.0), (0.0, 0.0), (0.035 * s, 0.0), (0.06 * s, 0.035)]
        for i, (fx, fz) in enumerate(specs):
            f = bmesh.new()
            bmesh.ops.create_uvsphere(f, u_segments=10, v_segments=8, radius=1.0)
            ang = 0.0 if i < 3 else -0.9 * s
            m = Matrix.Translation((fx, 0, fz - 0.07)) @ Matrix.Rotation(ang, 4, "Y") \
                @ Matrix.Diagonal((0.02, 0.02, 0.045, 1))
            bmesh.ops.transform(f, matrix=m, verts=f.verts)
            tmp = bpy.data.meshes.new("tmp")
            f.to_mesh(tmp)
            f.free()
            start = len(hb.verts)
            hb.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)
            fingers.append((start, len(hb.verts), Vector((fx, 0, fz - 0.03))))
        hand = mesh_ob(f"Bob_HandMesh_{t}", hb, M["ink"], hc, outline=False)
        hand.shape_key_add(name="Basis")
        for kname, curled in (("Point", (0, 2, 3)), ("Fist", (0, 1, 2, 3))):
            kb = hand.shape_key_add(name=kname, from_mix=False)
            for i, (a, b, base) in enumerate(fingers):
                for vi in range(a, b):
                    co = Vector(hand.data.vertices[vi].co)
                    if i in curled:
                        kb.data[vi].co = base + (co - base) * 0.35
                    elif kname == "Point":
                        kb.data[vi].co = base + (co - base) * Vector((1, 1, 1.6))
        key_driver(hand, "Point", ctrl, [f"hand_{t}_point", f"hand_{t}_fist"],
                   f"hand_{t}_point*(1-hand_{t}_fist)")
        key_driver(hand, "Fist", ctrl, [f"hand_{t}_fist"], f"hand_{t}_fist")
        hands[t] = hc

    # ---- camera, light, world ----------------------------------------------
    cam = bpy.data.objects.new("BobCam", bpy.data.cameras.new("BobCam"))
    scn.collection.objects.link(cam)
    cam.data.lens = 50
    cam.location = (0, -7.6, 2.55)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scn.camera = cam
    sun = bpy.data.objects.new("BobSun", bpy.data.lights.new("BobSun", "SUN"))
    scn.collection.objects.link(sun)
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(55), math.radians(-20), math.radians(-35))

    world = scn.world or bpy.data.worlds.new("World")
    scn.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (*_lin(BACKGROUND), 1)

    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scn.render.engine = eng
            break
        except TypeError:
            pass
    scn.view_settings.view_transform = "Standard"

    animate(ctrl, root, hands, sweat)
    scn.frame_set(1)


# ----------------------------------------------------------------------------
# Demo animation
# ----------------------------------------------------------------------------

def animate(ctrl, root, hands, sweat):
    face = [k for k in ctrl.keys() if not k.startswith(("hand_", "blink"))]
    defaults = {"eyes_deadpan": 1.0}

    def pose(f, **v):
        for p in face:
            ctrl[p] = v.get(p, defaults.get(p, 0.0))
            ctrl.keyframe_insert(f'["{p}"]', frame=f)

    def hold(a, b, **v):
        pose(a, **v)
        pose(b, **v)

    def handpose(f, t, point=0.0, fist=0.0):
        ctrl[f"hand_{t}_point"] = point
        ctrl[f"hand_{t}_fist"] = fist
        ctrl.keyframe_insert(f'["hand_{t}_point"]', frame=f)
        ctrl.keyframe_insert(f'["hand_{t}_fist"]', frame=f)

    def blink(f, slow=False):
        seq = ((0, 0), (5, 1), (9, 1), (15, 0)) if slow else ((-2, 0), (0, 1), (3, 0))
        for d, v in seq:
            ctrl["blink"] = v
            ctrl.keyframe_insert('["blink"]', frame=f + d)

    L, R = hands["L"], hands["R"]
    restL, restR = L.location.copy(), R.location.copy()

    def hk(h, f, loc, rot_y=0.0, rot_x=0.0):
        h.location = loc
        h.rotation_euler = (math.radians(rot_x), math.radians(rot_y), 0)
        h.keyframe_insert("location", frame=f)
        h.keyframe_insert("rotation_euler", frame=f)

    def body(f, z=0.0, sq=1.0):
        root.location = (0, 0, z)
        root.scale = (1 / math.sqrt(sq), 1 / math.sqrt(sq), sq)
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("scale", frame=f)

    # 1) deadpan idle (1-60)
    hold(1, 56)
    blink(22)
    blink(48)
    for f in range(1, 60, 12):
        body(f, 0, 1.0 if (f // 12) % 2 == 0 else 1.015)
    for t, h, r in (("L", L, restL), ("R", R, restR)):
        hk(h, 1, r)
        hk(h, 58, r)
        handpose(1, t)

    # 2) smug + reach and point (60-110)
    pose(62, brow_smug=1, head_tilt=0.15, look_x=-0.6, mouth_flat=0.6)
    hold(66, 106, brow_smug=1, head_tilt=0.12, head_turn=-0.15, look_x=-0.8,
         mouth_flat=0.6)
    hk(R, 64, Vector((-0.95, -0.35, 1.70)), 70)
    hk(R, 68, Vector((-1.18, -0.45, 1.95)), 95)     # overshoot
    hk(R, 72, Vector((-1.10, -0.42, 1.90)), 90)
    hk(R, 104, Vector((-1.10, -0.42, 1.90)), 90)
    handpose(62, "R")
    handpose(66, "R", point=1)
    handpose(104, "R", point=1)
    body(60, 0, 1.0)
    body(64, 0, 0.97)
    body(68, 0, 1.03)
    body(72, 0, 1.0)
    blink(90)

    # 3) talking with gestures (110-170)
    talk_shapes = [dict(mouth_open_talk=1), dict(mouth_flat=0.7), dict(mouth_open_talk=0.7),
                   dict(mouth_small_o=0.8), dict(mouth_open_talk=1), dict(mouth_flat=1)]
    for i, f in enumerate(range(112, 166, 4)):
        v = dict(talk_shapes[i % len(talk_shapes)])
        v.update(eyes_deadpan=0.6, brow_raise=0.35 if i % 4 < 2 else 0.1,
                 head_nod=0.12 if i % 2 else -0.05, look_x=0.1)
        pose(f, **v)
    pose(168, mouth_flat=0.5, eyes_deadpan=0.8)
    hk(R, 112, Vector((-0.75, -0.35, 1.45)), 30, -20)
    handpose(110, "R", point=0)
    hk(L, 112, restL)
    hk(L, 120, Vector((0.80, -0.45, 1.65)), -40, -30)
    hk(L, 132, Vector((0.70, -0.40, 1.45)), -20, -30)
    hk(L, 144, Vector((0.85, -0.50, 1.75)), -50, -30)
    hk(R, 140, Vector((-0.80, -0.40, 1.60)), 40, -20)
    hk(L, 156, Vector((0.72, -0.40, 1.50)), -25, -30)
    hk(R, 162, Vector((-0.75, -0.35, 1.45)), 30, -20)
    blink(150)

    # 4) shocked (170-215)
    pose(171, mouth_flat=0.5)
    pose(174, eyes_shocked=1, mouth_small_o=1, brow_raise=1, sparkle=1.2, head_nod=0.2)
    pose(178, eyes_shocked=1, mouth_small_o=1, brow_raise=1, sparkle=1.0, head_nod=0.15)
    pose(196, eyes_shocked=1, mouth_small_o=0.9, brow_raise=1, sparkle=0.0, head_nod=0.1)
    pose(210, eyes_shocked=1, mouth_small_o=0.8, brow_raise=0.9, head_nod=0.05)
    body(168, 0, 1.0)
    body(171, 0, 0.88)                    # anticipation squash
    body(176, 0.35, 1.12)                 # jump + stretch
    body(182, 0.0, 0.90)                  # land
    body(186, 0.0, 1.03)
    body(190, 0.0, 1.0)
    hk(L, 172, restL)
    hk(L, 176, Vector((0.80, -0.35, 2.35)), 180)    # finger up
    hk(L, 180, Vector((0.76, -0.32, 2.22)), 175)
    hk(L, 208, Vector((0.76, -0.32, 2.22)), 175)
    handpose(172, "L")
    handpose(175, "L", point=1)
    handpose(208, "L", point=1)
    hk(R, 172, Vector((-0.75, -0.35, 1.45)), 30, -20)
    hk(R, 178, Vector((-0.85, -0.20, 1.30)), 20)

    # 5) nervous (215-262)
    hold(216, 258, eyes_squint=1, eyes_deadpan=0, mouth_flat=1, sweat_drop=1.0,
         brow_worried=0.6, look_x=0.3)
    pose(213, eyes_shocked=0.0, eyes_squint=1, eyes_deadpan=0, mouth_flat=1,
         sweat_drop=0.0, brow_worried=0.6)
    pose(219, eyes_squint=1, eyes_deadpan=0, mouth_flat=1, sweat_drop=1.25,
         brow_worried=0.6, look_x=0.3)
    s0 = sweat.location.copy()
    sweat.keyframe_insert("location", frame=216)
    sweat.location = s0 + Vector((0.02, 0, -0.35))
    sweat.keyframe_insert("location", frame=256)
    sweat.location = s0
    sweat.keyframe_insert("location", frame=262)
    hk(L, 214, Vector((0.74, -0.05, 0.95)))
    hk(R, 214, Vector((-0.74, -0.05, 0.95)))
    hk(L, 256, Vector((0.74, -0.05, 0.95)))
    hk(R, 256, Vector((-0.74, -0.05, 0.95)))
    handpose(212, "L", point=0)
    body(212, 0, 1.0)
    body(216, -0.02, 0.96)
    body(256, -0.02, 0.96)

    # 6) back to deadpan + slow blink (262-288)
    hold(264, END)
    blink(270, slow=True)
    for h, r in ((L, restL), (R, restR)):
        hk(h, 266, r)
        hk(h, END, r)
    body(264, 0, 1.0)
    body(276, 0, 1.015)
    body(END, 0, 1.0)


if __name__ == "__main__":
    build()
    print("Bob (outline style) is ready - press Space to play.")
