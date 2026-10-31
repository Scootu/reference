"""
BOB - stylized cartoon character generator for Blender (4.2+ / 5.x)

HOW TO USE
  1. Open Blender, go to the "Scripting" tab.
  2. Click "Open", choose this file, then press "Run Script" (or Alt+P).
  3. Press Space in the viewport (or play the timeline) to watch Bob animate.
  4. Select the "Bob_FACE_CONTROLS" object -> Object Properties -> Custom Properties
     to drive every expression with sliders (smile, grin, bored, angry, ...).

WHAT GETS BUILT
  - Round head, spiky hair, bean-shaped body, noodle arms and legs
  - "Drawn-on" 2D-style face (eyes, highlights, brows, mouth, teeth, blush)
    built as decals that hug the head and morph with shape keys
  - A face-control object whose custom properties drive every shape key
  - Hand controls (hooks) so arms can wave / gesture
  - A ~12 second demo animation cycling through Bob's emotions
  - Toon (cel-shaded) materials, camera and lights

Tweak the CONFIG section to change Bob's look.
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# ----------------------------------------------------------------------------
# CONFIG - change Bob's look here
# ----------------------------------------------------------------------------
SKIN_COLOR = (1.00, 0.95, 0.88)
HAIR_COLOR = (0.10, 0.07, 0.06)
INK_COLOR = (0.04, 0.03, 0.03)      # eyes, brows, mouth outline, limbs
MOUTH_INNER = (0.30, 0.05, 0.06)
SHIRT_COLOR = (0.95, 0.45, 0.12)    # Bob's orange hoodie
COLLAR_COLOR = (0.98, 0.93, 0.80)
BLUSH_COLOR = (1.00, 0.55, 0.55)
SHOE_COLOR = (0.12, 0.12, 0.14)
BG_COLOR = (0.18, 0.20, 0.26)

HEAD_R = 1.0             # head radius
NECK_PIVOT = 0.9         # head pivots this far below its centre
HEAD_BASE_Z = 2.15       # world height of the neck pivot
FPS = 24
END_FRAME = 288          # 12 seconds

# ----------------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------------

def clean_scene():
    for ob in list(bpy.data.objects):
        if ob.name.startswith("Bob") or ob.name in ("Cam_Bob", "Key_Light", "Rim_Light"):
            bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                 bpy.data.cameras, bpy.data.lights, bpy.data.actions):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def get_collection():
    coll = bpy.data.collections.get("Bob")
    if coll is None:
        coll = bpy.data.collections.new("Bob")
        bpy.context.scene.collection.children.link(coll)
    return coll


COLL = None


def link(ob):
    COLL.objects.link(ob)
    return ob


def toon_material(name, color, shadow=0.62, emission_only=False):
    """Two-tone cel shader (EEVEE). Falls back gracefully in Cycles."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.location = (400, 0)
    nt.links.new(emit.outputs[0], out.inputs[0])
    col = (*color, 1.0)
    if emission_only:
        emit.inputs["Color"].default_value = col
        mat.diffuse_color = col
        return mat
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.location = (-200, 0)
    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.location = (0, 0)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (150, 0)
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    els[0].position = 0.0
    els[0].color = (color[0] * shadow, color[1] * shadow, color[2] * shadow * 1.05, 1)
    els[1].position = 0.18
    els[1].color = col
    nt.links.new(diff.outputs[0], s2rgb.inputs[0])
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])
    mat.diffuse_color = col
    return mat


def shade_smooth(mesh):
    for p in mesh.polygons:
        p.use_smooth = True


def new_mesh_object(name, bm, mat=None, parent=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        shade_smooth(me)
    ob = link(bpy.data.objects.new(name, me))
    if mat:
        me.materials.append(mat)
    if parent:
        ob.parent = parent
    return ob


def sphere_bm(radius=1.0, u=48, v=32, matrix=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=radius)
    if matrix is not None:
        bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
    return bm


def add_driver(target, path, ctrl, props, expr, index=-1):
    fc = target.driver_add(path, index) if index >= 0 else target.driver_add(path)
    drv = fc.driver
    drv.type = "SCRIPTED"
    for p in props:
        var = drv.variables.new()
        var.name = p
        var.type = "SINGLE_PROP"
        var.targets[0].id = ctrl
        var.targets[0].data_path = f'["{p}"]'
    drv.expression = expr
    return fc


# ----------------------------------------------------------------------------
# Face decals: 2D drawn shapes wrapped onto the front of the head.
# A shape is a function u in [-1, 1] -> (x, top, bottom), in head units,
# relative to the decal centre. Each decal is a strip grid between top/bottom,
# so concave shapes (crescent smiles, slanted lids) work fine.
# ----------------------------------------------------------------------------
COLS, ROWS = 28, 4


def ell(u, p=2.0):
    return max(0.0, 1.0 - abs(u) ** p) ** 0.5


def surface_point(x, z, off):
    """Point on the front of the head sphere (front = -Y) in head-local space."""
    r = HEAD_R + off
    d2 = r * r - x * x - z * z
    y = -math.sqrt(max(d2, 0.0001))
    return Vector((x, y, z + NECK_PIVOT))


def decal_points(shape, cx, cz, off):
    pts = []
    for i in range(COLS + 1):
        u = -1.0 + 2.0 * i / COLS
        x, top, bot = shape(u)
        for j in range(ROWS + 1):
            t = j / ROWS
            z = bot + (top - bot) * t
            pts.append(surface_point(cx + x, cz + z, off))
    return pts


def make_decal(name, base_shape, keys, cx, cz, off, mat, parent):
    """keys: dict key_name -> (shape_fn, dcx, dcz)"""
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in decal_points(base_shape, cx, cz, off)]
    for i in range(COLS):
        for j in range(ROWS):
            a = i * (ROWS + 1) + j
            b = (i + 1) * (ROWS + 1) + j
            bm.faces.new((verts[a], verts[b], verts[b + 1], verts[a + 1]))
    ob = new_mesh_object(name, bm, mat, parent, smooth=False)
    ob.shape_key_add(name="Basis")
    for kname, (shape, dx, dz) in keys.items():
        kb = ob.shape_key_add(name=kname, from_mix=False)
        for v, p in zip(kb.data, decal_points(shape, cx + dx, cz + dz, off)):
            v.co = p
    return ob


# ----------------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------------

def build():
    global COLL
    clean_scene()
    COLL = get_collection()
    scn = bpy.context.scene
    scn.render.fps = FPS
    scn.frame_start = 1
    scn.frame_end = END_FRAME

    m_skin = toon_material("Bob_Skin", SKIN_COLOR, 0.80)
    m_hair = toon_material("Bob_Hair", HAIR_COLOR, 0.55)
    m_ink = toon_material("Bob_Ink", INK_COLOR, emission_only=True)
    m_white = toon_material("Bob_White", (1, 1, 1), emission_only=True)
    m_mouth = toon_material("Bob_MouthInner", MOUTH_INNER, emission_only=True)
    m_shirt = toon_material("Bob_Shirt", SHIRT_COLOR, 0.70)
    m_collar = toon_material("Bob_Collar", COLLAR_COLOR, 0.78)
    m_blush = toon_material("Bob_Blush", BLUSH_COLOR, emission_only=True)
    m_shoe = toon_material("Bob_Shoe", SHOE_COLOR, 0.6)

    # --- Rig objects -------------------------------------------------------
    root = link(bpy.data.objects.new("Bob_ROOT", None))
    root.empty_display_type = "ARROWS"

    ctrl = link(bpy.data.objects.new("Bob_FACE_CONTROLS", None))
    ctrl.empty_display_type = "CIRCLE"
    ctrl.empty_display_size = 0.4
    ctrl.location = (2.2, 0, 3.4)
    ctrl.rotation_euler = (math.radians(90), 0, 0)
    face_props = {
        "smile": "Closed happy smile",
        "grin": "Big open grin with teeth",
        "frown": "Downturned mouth",
        "mouth_O": "Surprised 'O' mouth",
        "talk": "Open mouth for talking/lip-sync",
        "blink": "Close both eyes",
        "bored": "Half-closed unimpressed lids",
        "angry": "Angry slanted lids + brows",
        "sad": "Sad lids + brows",
        "wide_eyes": "Bigger eyes (surprise)",
        "brow_up": "Raise both brows",
        "brow_skeptic": "Raise one brow (skeptical)",
        "look_x": "Look left/right (-1..1)",
        "look_y": "Look down/up (-1..1)",
        "blush": "Rosy cheeks",
        "head_turn": "Turn head (-1..1)",
        "head_tilt": "Tilt head (-1..1)",
        "head_nod": "Nod head (-1..1)",
    }
    for p, desc in face_props.items():
        ctrl[p] = 0.0
        lo = -1.0 if p.startswith(("look", "head")) else 0.0
        ui = ctrl.id_properties_ui(p)
        ui.update(min=lo, max=1.0, soft_min=lo, soft_max=1.0, description=desc)

    # --- Body --------------------------------------------------------------
    body_bm = sphere_bm(1.0, matrix=Matrix.Diagonal((0.62, 0.50, 0.80, 1.0)))
    bmesh.ops.translate(body_bm, vec=(0, 0, 1.45), verts=body_bm.verts)
    body = new_mesh_object("Bob_Body", body_bm, m_shirt, root)

    collar_bm = bmesh.new()
    bmesh.ops.create_cone(collar_bm, cap_ends=False, segments=32, radius1=0.42,
                          radius2=0.30, depth=0.16,
                          matrix=Matrix.Translation((0, 0, 2.13)))
    new_mesh_object("Bob_Collar", collar_bm, m_collar, root)

    # hoodie pocket stripe
    pocket_bm = sphere_bm(1.0, 24, 16, Matrix.Diagonal((0.36, 0.08, 0.14, 1.0)))
    bmesh.ops.translate(pocket_bm, vec=(0, -0.44, 1.10), verts=pocket_bm.verts)
    new_mesh_object("Bob_Pocket", pocket_bm, m_collar, root)

    # --- Head --------------------------------------------------------------
    head = link(bpy.data.objects.new("Bob_Head", None))
    head.empty_display_size = 0.2
    head.parent = root
    head.location = (0, 0, HEAD_BASE_Z)
    head.rotation_mode = "XYZ"

    skull_bm = sphere_bm(HEAD_R, 64, 40)
    bmesh.ops.translate(skull_bm, vec=(0, 0, NECK_PIVOT), verts=skull_bm.verts)
    new_mesh_object("Bob_Skull", skull_bm, m_skin, head)

    # Hair: a cap with a hairline plus spiky tufts
    hair_bm = sphere_bm(HEAD_R * 1.07, 64, 40,
                        Matrix.Diagonal((1.0, 1.0, 1.08, 1.0)))

    def hairline(x, y):
        # wavy hairline: high on the forehead, low at the back / sides
        t = min(max((y + 0.45) / 0.9, 0.0), 1.0)
        t = t * t * (3 - 2 * t)
        wave = 0.06 * math.sin(math.atan2(y, x) * 9.0)
        return 0.50 + (-0.55 - 0.50) * t + wave

    kill = [v for v in hair_bm.verts if v.co.z < hairline(v.co.x, v.co.y)]
    bmesh.ops.delete(hair_bm, geom=kill, context="VERTS")
    up_swoosh = Vector((0, -0.25, 0.35))
    fringe = Vector((0, -0.6, -0.55))
    tufts = [  # (direction, length, base radius, bend)
        # messy fringe falling over the forehead
        ((0.05, -0.75, 0.62), 0.42, 0.20, fringe),
        ((-0.28, -0.70, 0.60), 0.36, 0.18, fringe + Vector((-0.3, 0, 0))),
        ((0.33, -0.68, 0.60), 0.34, 0.18, fringe + Vector((0.4, 0, 0))),
        # top volume
        ((0.00, -0.55, 0.85), 0.55, 0.32, up_swoosh),
        ((-0.35, -0.45, 0.82), 0.48, 0.28, up_swoosh),
        ((0.38, -0.40, 0.83), 0.45, 0.27, up_swoosh),
        ((0.15, 0.00, 1.00), 0.55, 0.32, up_swoosh),
        ((-0.25, 0.15, 0.95), 0.48, 0.30, up_swoosh),
        ((0.55, 0.20, 0.80), 0.42, 0.28, Vector((0.3, 0.1, 0.1))),
        ((-0.62, 0.05, 0.70), 0.42, 0.26, Vector((-0.3, 0.1, 0.0))),
        ((0.10, 0.60, 0.75), 0.45, 0.30, Vector((0, 0.3, 0.1))),
        ((-0.30, 0.65, 0.55), 0.38, 0.27, Vector((0, 0.3, -0.1))),
        ((0.45, 0.62, 0.45), 0.36, 0.26, Vector((0.1, 0.3, -0.1))),
        # side tufts
        ((0.80, -0.20, 0.50), 0.34, 0.20, Vector((0.4, -0.1, -0.2))),
        ((-0.82, -0.20, 0.48), 0.34, 0.20, Vector((-0.4, -0.1, -0.2))),
        ((0.85, 0.30, 0.25), 0.30, 0.20, Vector((0.3, 0.2, -0.3))),
        ((-0.85, 0.30, 0.22), 0.30, 0.20, Vector((-0.3, 0.2, -0.3))),
    ]
    for d, length, rad, bend in tufts:
        d = Vector(d).normalized()
        tip_dir = (d + bend).normalized()
        rot = tip_dir.to_track_quat("Z", "Y").to_matrix().to_4x4()
        loc = Matrix.Translation(d * (HEAD_R * 0.98) + tip_dir * (length * 0.5))
        bmesh.ops.create_cone(hair_bm, cap_ends=True, segments=12, radius1=rad,
                              radius2=0.0, depth=length, matrix=loc @ rot)
    bmesh.ops.translate(hair_bm, vec=(0, 0, NECK_PIVOT), verts=hair_bm.verts)
    new_mesh_object("Bob_Hair", hair_bm, m_hair, head)

    # --- Face decals -------------------------------------------------------
    eye_cx, eye_cz = 0.30, 0.10
    look_dx, look_dz = 0.06, 0.05

    def eye_open(u):
        return 0.075 * u, 0.10 * ell(u), -0.10 * ell(u)

    def eye_wide(u):
        return 0.092 * u, 0.13 * ell(u), -0.13 * ell(u)

    def eye_blink(u):
        e = ell(u, 4)
        return 0.085 * u, -0.025 + 0.012 * e, -0.025 - 0.012 * e

    def eye_clip(line):
        def f(u):
            x, top, bot = eye_open(u)
            top = min(top, line(u))
            return x, max(top, bot + 0.004), bot
        return f

    def eye_keys(side):
        # side = +1 for Bob's left eye (+X), -1 for right eye (-X)
        # "inner" corner (towards the nose) is u = -side
        return {
            "Blink": (eye_blink, 0, 0),
            "Bored": (eye_clip(lambda u: 0.012), 0, 0),
            "Angry": (eye_clip(lambda u: 0.025 + 0.065 * u * side), 0, 0),
            "Sad": (eye_clip(lambda u: 0.035 - 0.055 * u * side), 0, 0),
            "Wide": (eye_wide, 0, 0),
            "LookX": (eye_open, look_dx, 0),
            "LookY": (eye_open, 0, look_dz),
        }

    def hl_shape(u):
        return 0.022 * u, 0.022 * ell(u), -0.022 * ell(u)

    def hl_gone(u):
        return 0.0, 0.0, 0.0

    def hl_keys():
        return {
            "Hide": (hl_gone, 0, 0),
            "LookX": (hl_shape, look_dx, 0),
            "LookY": (hl_shape, 0, look_dz),
        }

    eyes, highlights = [], []
    for side, tag in ((1, "L"), (-1, "R")):
        cx = eye_cx * side
        e = make_decal(f"Bob_Eye_{tag}", eye_open, eye_keys(side), cx, eye_cz,
                       0.004, m_ink, head)
        h = make_decal(f"Bob_EyeHighlight_{tag}", hl_shape, hl_keys(),
                       cx + 0.025, eye_cz + 0.045, 0.007, m_white, head)
        eyes.append(e)
        highlights.append(h)

    # Brows
    def brow_base(u, lift=0.0, slope=0.0):
        c = 0.025 * (1 - u * u) + lift + slope * u
        th = 0.017 * ell(u, 4) + 0.004
        return 0.095 * u, c + th, c - th

    def brow_keys(side):
        return {
            "Up": (lambda u: brow_base(u, 0.08), 0, 0),
            "Angry": (lambda u: brow_base(u, -0.015, 0.045 * side), 0, 0),
            "Sad": (lambda u: brow_base(u, 0.02, -0.04 * side), 0, 0),
            "Skeptic": (lambda u: brow_base(u, 0.10 if side > 0 else -0.03,
                                            0.0 if side > 0 else 0.02 * side), 0, 0),
        }

    brows = []
    for side, tag in ((1, "L"), (-1, "R")):
        brows.append(make_decal(f"Bob_Brow_{tag}", brow_base, brow_keys(side),
                                eye_cx * side, 0.30, 0.005, m_ink, head))

    # Mouth (dark inside) + teeth
    m_cz = -0.36

    def m_neutral(u):
        e = ell(u, 4)
        return 0.15 * u, 0.012 * e, -0.012 * e

    def m_smile(u):
        e = ell(u, 4)
        c = 0.10 * u * u - 0.03
        return 0.24 * u, c + 0.016 * e, c - 0.016 * e

    def m_grin(u):
        top = 0.11 * u * u + 0.01
        return 0.30 * u, top, top - 0.27 * ell(u, 2.4)

    def m_frown(u):
        e = ell(u, 4)
        c = 0.03 - 0.09 * u * u
        return 0.19 * u, c + 0.016 * e, c - 0.016 * e

    def m_O(u):
        return 0.09 * u, 0.11 * ell(u), -0.11 * ell(u)

    def m_talk(u):
        return 0.16 * u, 0.03 * ell(u), -0.17 * ell(u)

    mouth = make_decal("Bob_Mouth", m_neutral, {
        "Smile": (m_smile, 0, 0), "Grin": (m_grin, 0, 0), "Frown": (m_frown, 0, 0),
        "O": (m_O, 0, 0), "Talk": (m_talk, 0, 0),
    }, 0.0, m_cz, 0.004, m_mouth, head)

    def teeth_hidden(u):
        return 0.0, 0.0, 0.0

    def teeth_show(u):
        x, top, bot = m_grin(u * 0.92)
        top = top - 0.012
        return x, top, max(bot, top - 0.075)

    teeth = make_decal("Bob_Teeth", teeth_hidden, {"Grin": (teeth_show, 0, 0)},
                       0.0, m_cz, 0.007, m_white, head)

    # Mouth outline (slightly bigger, ink coloured, behind the inner mouth)
    def grow(shape, k=0.012):
        def f(u):
            x, top, bot = shape(u)
            return x * 1.04 + 0.006 * u, top + k, bot - k
        return f

    mouth_line = make_decal("Bob_MouthLine", grow(m_neutral, 0.004), {
        "Smile": (grow(m_smile, 0.004), 0, 0), "Grin": (grow(m_grin), 0, 0),
        "Frown": (grow(m_frown, 0.004), 0, 0), "O": (grow(m_O), 0, 0),
        "Talk": (grow(m_talk), 0, 0),
    }, 0.0, m_cz, 0.002, m_ink, head)

    # Blush
    def blush_hidden(u):
        return 0.0, 0.0, 0.0

    def blush_show(u):
        return 0.10 * u, 0.045 * ell(u), -0.045 * ell(u)

    blushes = [make_decal(f"Bob_Blush_{t}", blush_hidden, {"Show": (blush_show, 0, 0)},
                          0.48 * s, -0.12, 0.003, m_blush, head)
               for s, t in ((1, "L"), (-1, "R"))]

    # --- Drivers: face controls -> shape keys --------------------------------
    def kdrv(ob, key, props, expr):
        kb = ob.data.shape_keys.key_blocks[key]
        kb.slider_min = -1.0
        add_driver(kb, "value", ctrl, props, expr)

    for e in eyes:
        kdrv(e, "Blink", ["blink"], "blink")
        kdrv(e, "Bored", ["bored", "blink"], "bored*(1-blink)")
        kdrv(e, "Angry", ["angry", "blink"], "angry*(1-blink)")
        kdrv(e, "Sad", ["sad", "blink"], "sad*(1-blink)")
        kdrv(e, "Wide", ["wide_eyes", "blink"], "wide_eyes*(1-blink)")
        kdrv(e, "LookX", ["look_x"], "look_x")
        kdrv(e, "LookY", ["look_y"], "look_y")
    for h in highlights:
        kdrv(h, "Hide", ["blink", "bored", "angry", "sad"],
             "min(1, blink + bored + angry + sad)")
        kdrv(h, "LookX", ["look_x"], "look_x")
        kdrv(h, "LookY", ["look_y"], "look_y")
    for b in brows:
        kdrv(b, "Up", ["brow_up", "wide_eyes"], "min(1, brow_up + 0.5*wide_eyes)")
        kdrv(b, "Angry", ["angry"], "angry")
        kdrv(b, "Sad", ["sad"], "sad")
        kdrv(b, "Skeptic", ["brow_skeptic"], "brow_skeptic")
    for m in (mouth, mouth_line):
        kdrv(m, "Smile", ["smile"], "smile")
        kdrv(m, "Grin", ["grin"], "grin")
        kdrv(m, "Frown", ["frown"], "frown")
        kdrv(m, "O", ["mouth_O"], "mouth_O")
        kdrv(m, "Talk", ["talk"], "talk")
    kdrv(teeth, "Grin", ["grin"], "grin")
    for b in blushes:
        kdrv(b, "Show", ["blush"], "blush")

    add_driver(head, "rotation_euler", ctrl, ["head_nod"], "-0.35*head_nod", 0)
    add_driver(head, "rotation_euler", ctrl, ["head_tilt"], "0.30*head_tilt", 1)
    add_driver(head, "rotation_euler", ctrl, ["head_turn"], "0.55*head_turn", 2)

    # --- Limbs (noodle curves + hooks) --------------------------------------
    def noodle(name, pts, radius, parent):
        cu = bpy.data.curves.new(name, "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = radius
        cu.bevel_resolution = 4
        cu.resolution_u = 16
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(pts) - 1)
        for bp, p in zip(sp.bezier_points, pts):
            bp.co = p
            bp.handle_left_type = bp.handle_right_type = "AUTO"
        cu.materials.append(m_ink)
        ob = link(bpy.data.objects.new(name, cu))
        ob.parent = parent
        return ob

    bpy.context.view_layer.update()

    def hook_end(curve_ob, point_index, ctl):
        mod = curve_ob.modifiers.new("Hook", "HOOK")
        mod.object = ctl
        i = point_index * 3
        mod.vertex_indices_set([i, i + 1, i + 2])
        bpy.context.view_layer.update()
        mod.matrix_inverse = (curve_ob.matrix_world.inverted() @ ctl.matrix_world).inverted()

    hands = {}
    for s, t in ((1, "L"), (-1, "R")):
        shoulder = Vector((0.52 * s, 0, 1.85))
        hand_rest = Vector((0.80 * s, -0.10, 1.05))
        arm = noodle(f"Bob_Arm_{t}", [shoulder, (shoulder + hand_rest) / 2 + Vector((0.12 * s, 0, 0)),
                                      hand_rest], 0.035, root)
        hc = link(bpy.data.objects.new(f"Bob_HandCtrl_{t}", None))
        hc.empty_display_type = "SPHERE"
        hc.empty_display_size = 0.12
        hc.parent = root
        hc.location = hand_rest
        hook_end(arm, 2, hc)
        hand = new_mesh_object(f"Bob_Hand_{t}", sphere_bm(0.085, 16, 12), m_ink, hc)
        hands[t] = hc

        hip = Vector((0.24 * s, 0, 0.85))
        foot = Vector((0.30 * s, 0, 0.10))
        noodle(f"Bob_Leg_{t}", [hip, (hip + foot) / 2 + Vector((0.03 * s, 0, 0)), foot],
               0.04, root)
        shoe_bm = sphere_bm(1.0, 24, 16, Matrix.Diagonal((0.13, 0.20, 0.08, 1.0)))
        bmesh.ops.translate(shoe_bm, vec=(0.30 * s, -0.07, 0.07), verts=shoe_bm.verts)
        new_mesh_object(f"Bob_Shoe_{t}", shoe_bm, m_shoe, root)

    # --- Camera, lights, world ---------------------------------------------
    cam_data = bpy.data.cameras.new("Cam_Bob")
    cam_data.lens = 50
    cam = bpy.data.objects.new("Cam_Bob", cam_data)
    scn.collection.objects.link(cam)
    cam.location = (0.0, -11.0, 2.4)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scn.camera = cam

    sun = bpy.data.lights.new("Key_Light", "SUN")
    sun.energy = 3.0
    sun_ob = bpy.data.objects.new("Key_Light", sun)
    scn.collection.objects.link(sun_ob)
    sun_ob.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-30))

    world = scn.world or bpy.data.worlds.new("World")
    scn.world = world
    world.use_nodes = True
    bgn = world.node_tree.nodes.get("Background")
    if bgn:
        bgn.inputs[0].default_value = (*BG_COLOR, 1)
        bgn.inputs[1].default_value = 1.0

    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scn.render.engine = eng
            break
        except TypeError:
            continue
    try:
        scn.view_settings.view_transform = "Standard"
    except TypeError:
        pass

    animate(ctrl, root, hands)
    scn.frame_set(1)
    return ctrl


# ----------------------------------------------------------------------------
# Demo animation
# ----------------------------------------------------------------------------

def animate(ctrl, root, hands):
    props = [k for k in ctrl.keys() if not k.startswith("_")]

    def pose(frame, **vals):
        for p in props:
            if p == "blink":
                continue
            ctrl[p] = vals.get(p, 0.0)
            ctrl.keyframe_insert(f'["{p}"]', frame=frame)

    def hold(f0, f1, **vals):
        pose(f0, **vals)
        pose(f1, **vals)

    # Emotion beats (frame ranges)
    hold(1, 16)                                                       # neutral
    hold(24, 48, smile=1, blush=0.6, head_tilt=0.3, look_x=0.2)      # happy
    pose(56, grin=1, brow_up=0.6, blush=0.9, head_nod=-0.3)          # laugh
    pose(62, grin=0.8, talk=0.3, brow_up=0.6, blush=0.9, head_nod=0.1)
    pose(68, grin=1, brow_up=0.6, blush=0.9, head_nod=-0.3)
    pose(74, grin=0.8, talk=0.3, brow_up=0.6, blush=0.9, head_nod=0.1)
    pose(82, grin=1, brow_up=0.5, blush=0.8, head_nod=-0.15)
    hold(96, 136, bored=1, brow_skeptic=1, look_x=-0.5,              # unimpressed
         head_turn=0.25, head_tilt=-0.15)
    pose(146, wide_eyes=1, mouth_O=1, brow_up=1, head_nod=0.25)      # surprised
    pose(166, wide_eyes=0.9, mouth_O=0.85, brow_up=1, head_nod=0.2)
    hold(178, 206, angry=1, frown=0.8, head_nod=-0.35, look_y=-0.2)  # angry
    hold(216, 246, sad=1, frown=1, look_y=-0.6, head_tilt=-0.35,     # sad
         head_nod=-0.3)
    pose(258, smile=0.8, talk=0.4, look_x=0.2)                       # talking
    pose(264, smile=0.6, talk=0.0)
    pose(270, smile=0.8, talk=0.6)
    pose(276, smile=0.7, talk=0.1)
    hold(282, END_FRAME, smile=1, blush=0.4)

    # Blinks (fast: open-closed-open)
    for f in (20, 52, 90, 140, 172, 210, 252):
        for df, v in ((-2, 0.0), (0, 1.0), (3, 0.0)):
            ctrl["blink"] = v
            ctrl.keyframe_insert('["blink"]', frame=f + df)
    # bored droopy slow blink
    for df, v in ((0, 0.0), (5, 1.0), (14, 0.0)):
        ctrl["blink"] = v
        ctrl.keyframe_insert('["blink"]', frame=118 + df)

    # Body bounce + squash
    def body_key(frame, z=0.0, sq=1.0):
        root.location = (0, 0, z)
        root.scale = (1.0 / math.sqrt(sq), 1.0 / math.sqrt(sq), sq)
        root.keyframe_insert("location", frame=frame)
        root.keyframe_insert("scale", frame=frame)

    body_key(1)
    body_key(16)
    for f in (56, 68, 80):                       # laugh bounce
        body_key(f - 4, 0.0, 0.94)
        body_key(f, 0.12, 1.04)
    body_key(90)
    body_key(144, 0.0, 0.92)                     # surprise jump
    body_key(150, 0.25, 1.08)
    body_key(160, 0.0, 1.0)
    body_key(214)
    body_key(226, -0.03, 0.95)                   # sad slump
    body_key(246, -0.03, 0.95)
    body_key(256)
    body_key(END_FRAME)

    # Hands
    L, R = hands["L"], hands["R"]
    restL, restR = L.location.copy(), R.location.copy()

    def hand_key(h, frame, loc):
        h.location = loc
        h.keyframe_insert("location", frame=frame)

    for h, rest in ((L, restL), (R, restR)):
        hand_key(h, 1, rest)
        hand_key(h, 20, rest)
    # wave with right hand during "happy"
    hand_key(R, 26, Vector((-1.05, -0.15, 2.45)))
    for i, f in enumerate(range(30, 50, 5)):
        hand_key(R, f, Vector((-1.05 + (0.18 if i % 2 else -0.05), -0.15, 2.45)))
    # laugh: hands on belly
    hand_key(R, 56, Vector((-0.38, -0.50, 1.25)))
    hand_key(L, 56, Vector((0.38, -0.50, 1.25)))
    hand_key(R, 86, Vector((-0.38, -0.50, 1.25)))
    hand_key(L, 86, Vector((0.38, -0.50, 1.25)))
    # bored: one hand on hip, other limp
    hand_key(L, 98, Vector((0.62, -0.05, 1.35)))
    hand_key(R, 98, restR)
    hand_key(L, 138, Vector((0.62, -0.05, 1.35)))
    hand_key(R, 138, restR)
    # surprise: hands up
    hand_key(L, 146, Vector((0.95, -0.2, 2.6)))
    hand_key(R, 146, Vector((-0.95, -0.2, 2.6)))
    hand_key(L, 168, Vector((0.90, -0.2, 2.5)))
    hand_key(R, 168, Vector((-0.90, -0.2, 2.5)))
    # angry: fists clenched by sides, shaking
    for f in range(180, 208, 4):
        j = 0.03 if (f // 4) % 2 else -0.03
        hand_key(L, f, Vector((0.74 + j, -0.15, 1.15)))
        hand_key(R, f, Vector((-0.74 - j, -0.15, 1.15)))
    # sad: arms droop low
    hand_key(L, 218, Vector((0.62, 0.0, 0.80)))
    hand_key(R, 218, Vector((-0.62, 0.0, 0.80)))
    hand_key(L, 246, Vector((0.62, 0.0, 0.80)))
    hand_key(R, 246, Vector((-0.62, 0.0, 0.80)))
    # talking gestures
    hand_key(R, 260, Vector((-0.75, -0.45, 1.65)))
    hand_key(R, 268, Vector((-0.85, -0.40, 1.80)))
    hand_key(R, 276, Vector((-0.75, -0.45, 1.65)))
    hand_key(L, 260, restL)
    for h, rest in ((L, restL), (R, restR)):
        hand_key(h, END_FRAME, rest)


if __name__ == "__main__":
    build()
    print("Bob is ready! Press Space to play the animation.")
