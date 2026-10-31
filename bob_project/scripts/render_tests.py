"""Bob - render setup (studio + cinematic) and the character test renders.

Usage (from the bob_project folder, after build_all.py has saved bob_character.blend):
    blender -b blender/bob_character.blend --python scripts/render_tests.py -- --all
    blender -b blender/bob_character.blend --python scripts/render_tests.py -- --only portraits
Options: --all | --only portraits,fullbody,expressions,turntable,interaction,cinematic
         --wip NAME  (quick low-sample previews of the portrait views into renders/wip)
         --samples N --scale PERCENT
"""

import os
import sys
import math
import importlib
import bpy
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PROJECT = os.path.dirname(HERE)
RENDERS = os.path.join(PROJECT, "renders")

import bob_common as bc  # noqa: E402

FOCUS_HEAD = Vector((0, 0, 2.30))
FOCUS_BODY = Vector((0, 0, 1.50))


# ----------------------------------------------------------------------------
# Render settings
# ----------------------------------------------------------------------------

ENGINE = "EEVEE"   # the flat 2.5D character is unlit; EEVEE renders it fast and exact


def setup_cycles(samples=96, res=(1600, 1600), percent=100):
    scn = bpy.context.scene
    if ENGINE == "EEVEE":
        for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            try:
                scn.render.engine = eng
                break
            except TypeError:
                continue
        ee = scn.eevee
        ee.taa_render_samples = max(16, min(samples, 64))
        for attr, val in (("use_shadows", True), ("use_raytracing", True),
                          ("use_gtao", True), ("shadow_ray_count", 2)):
            if hasattr(ee, attr):
                setattr(ee, attr, val)
        scn.render.resolution_x, scn.render.resolution_y = res
        scn.render.resolution_percentage = percent
        scn.render.film_transparent = False
        scn.render.filter_size = 1.2
        scn.view_settings.view_transform = "Standard"
        scn.view_settings.look = "None"
        scn.render.image_settings.file_format = "PNG"
        return
    scn.render.engine = "CYCLES"
    cy = scn.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_denoising = True
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    cy.max_bounces = 8
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 3
    cy.transmission_bounces = 6
    cy.transparent_max_bounces = 8
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.resolution_percentage = percent
    scn.render.film_transparent = False
    scn.render.filter_size = 1.5
    try:
        scn.view_settings.view_transform = "Standard"
        scn.view_settings.look = "None"
    except TypeError:
        scn.view_settings.view_transform = "Filmic"
    scn.render.image_settings.file_format = "PNG"


# ----------------------------------------------------------------------------
# Environments
# ----------------------------------------------------------------------------

def env_collection(name):
    coll = bpy.data.collections.get(name)
    if coll:
        for ob in list(coll.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    else:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def set_env_visible(name):
    for cname in ("ENV_Studio", "ENV_Cinematic"):
        c = bpy.data.collections.get(cname)
        if c:
            c.hide_render = (cname != name)
            c.hide_viewport = (cname != name)


def area_light(coll, name, loc, target, energy, size, color=(1, 1, 1), size_y=None):
    lt = bpy.data.lights.new(name, "AREA")
    lt.energy = energy
    lt.color = color
    lt.shape = "RECTANGLE" if size_y else "DISK"
    lt.size = size
    if size_y:
        lt.size_y = size_y
    ob = bpy.data.objects.new(name, lt)
    coll.objects.link(ob)
    ob.location = loc
    d = (Vector(target) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def world(color, strength, name="BOB_World"):
    w = bpy.data.worlds.get(name) or bpy.data.worlds.new(name)
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (*[c * 0.55 for c in bc.lin(color)], 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*bc.lin(color), 1)
    maprange = nt.nodes.new("ShaderNodeMapRange")
    maprange.inputs["From Min"].default_value = -1.0
    maprange.inputs["From Max"].default_value = 1.0
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], maprange.inputs["Value"])
    nt.links.new(maprange.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs[0])
    return w


def build_studio():
    bpy.context.scene["bob_scene_tint"] = 0.0     # exact reference palette in the studio
    coll = env_collection("ENV_Studio")
    # cyclorama: floor curving up into a back wall
    import bmesh
    bm = bmesh.new()
    W, D, H, R, Y0 = 30.0, 18.0, 12.0, 4.0, -9.0
    prof = []
    for i in range(16):
        prof.append((Y0 + (D - R) * i / 15, 0.0))
    for i in range(1, 17):
        a = math.pi / 2 * i / 16
        prof.append((Y0 + D - R + R * math.sin(a), R - R * math.cos(a)))
    for i in range(1, 8):
        prof.append((Y0 + D, R + (H - R) * i / 7))
    cols = 24
    rows = []
    for y, z in prof:
        rows.append([bm.verts.new((-W / 2 + W * c / cols, y, z)) for c in range(cols + 1)])
    for r in range(len(rows) - 1):
        for c in range(cols):
            bm.faces.new((rows[r][c], rows[r][c + 1], rows[r + 1][c + 1], rows[r + 1][c]))
    mat, nt, b = bc.principled("ENV_Cyc", (0.58, 0.60, 0.64), rough=0.85, spec=0.2)
    ob = bc.bm_to_object("ENV_Cyclorama", bm, coll, [mat])
    # three-point lighting
    area_light(coll, "ENV_Key", (-3.2, -4.0, 4.4), (0, 0, 1.9), 380, 4.0, (1.0, 0.95, 0.88))
    area_light(coll, "ENV_Fill", (3.6, -3.4, 2.0), (0, 0, 1.6), 140, 4.0, (0.85, 0.9, 1.0))
    area_light(coll, "ENV_Rim", (2.0, 3.5, 4.0), (0, 0, 2.1), 300, 2.0, (0.9, 0.95, 1.0))
    area_light(coll, "ENV_RimL", (-2.6, 3.0, 2.8), (0, 0, 1.6), 160, 2.0, (1.0, 0.9, 0.8))
    world((0.62, 0.66, 0.72), 0.35)
    return coll


def build_cinematic():
    """A small stylised interior: plank floor, plaster/stone wall with a bright window,
    a low table with a lantern, teapot and scroll, warm practical + cool window light."""
    import bmesh
    coll = env_collection("ENV_Cinematic")
    # floor planks
    wood, nt, b = bc.principled("ENV_Wood", (0.40, 0.25, 0.15), rough=0.55, spec=0.35)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 8.0
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 14.0, 1.0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*bc.lin((0.30, 0.17, 0.09)), 1)
    ramp.color_ramp.elements[1].color = (*bc.lin((0.52, 0.33, 0.19)), 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    for i in range(-30, 31):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((i * 0.36, 2.0, -0.04))
                            @ Matrix.Diagonal((0.345, 16.0, 0.08, 1)), verts=bm.verts)
        bevel = bc.bm_to_object(f"ENV_Plank_{i}", bm, coll, [wood], smooth=False)
        m = bevel.modifiers.new("Bevel", "BEVEL")
        m.width = 0.012
        m.segments = 2
        bevel.location.z += 0.0015 * ((i * 7) % 3)
    # back wall (plaster) with a window opening
    wall, nt, b = bc.principled("ENV_Wall", (0.80, 0.72, 0.62), rough=0.9, spec=0.2)
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 6.0
    add_b = bc.add_bump(nt, b, n2, strength=0.15, distance=0.02)
    for name, x0, x1, z0, z1 in (("L", -20, 0.6, 0, 6), ("R", 2.4, 20, 0, 6),
                                 ("B", 0.6, 2.4, 0, 1.4), ("T", 0.6, 2.4, 3.6, 6)):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(((x0 + x1) / 2, 3.2, (z0 + z1) / 2))
                            @ Matrix.Diagonal((x1 - x0, 0.3, z1 - z0, 1)), verts=bm.verts)
        bc.bm_to_object(f"ENV_Wall_{name}", bm, coll, [wall], smooth=False)
    # window frame (wood) + bright sky card
    for name, loc, scl in (("WinL", (0.6, 3.05, 2.5), (0.12, 0.12, 2.3)),
                           ("WinR", (2.4, 3.05, 2.5), (0.12, 0.12, 2.3)),
                           ("WinB", (1.5, 3.05, 1.4), (1.9, 0.14, 0.12)),
                           ("WinT", (1.5, 3.05, 3.6), (1.9, 0.14, 0.12)),
                           ("WinM", (1.5, 3.05, 2.5), (0.06, 0.08, 2.2)),
                           ("WinH", (1.5, 3.05, 2.5), (1.8, 0.08, 0.06))):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ Matrix.Diagonal((*scl, 1)),
                            verts=bm.verts)
        bc.bm_to_object(f"ENV_{name}", bm, coll, [wood], smooth=False)
    sky, _, _ = bc.principled("ENV_Sky", (0.75, 0.85, 1.0), emission=(0.75, 0.88, 1.0),
                              emission_strength=6.0)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((1.5, 3.8, 2.5))
                        @ Matrix.Rotation(math.radians(90), 4, "X")
                        @ Matrix.Diagonal((1.6, 1.6, 1, 1)), verts=bm.verts)
    skyob = bc.bm_to_object("ENV_SkyCard", bm, coll, [sky], smooth=False)
    skyob.visible_shadow = False
    # low table + props
    for name, loc, scl in (("Top", (-1.05, 0.3, 0.62), (1.2, 0.7, 0.07)),
                           ("Leg1", (-1.55, 0.05, 0.3), (0.08, 0.08, 0.6)),
                           ("Leg2", (-0.55, 0.05, 0.3), (0.08, 0.08, 0.6)),
                           ("Leg3", (-1.55, 0.55, 0.3), (0.08, 0.08, 0.6)),
                           ("Leg4", (-0.55, 0.55, 0.3), (0.08, 0.08, 0.6))):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ Matrix.Diagonal((*scl, 1)),
                            verts=bm.verts)
        t = bc.bm_to_object(f"ENV_Table{name}", bm, coll, [wood], smooth=False)
        m = t.modifiers.new("Bevel", "BEVEL")
        m.width = 0.015
        m.segments = 3
    # lantern: warm emissive paper lantern on the table
    paper, _, _ = bc.principled("ENV_Lantern", (1.0, 0.75, 0.45), emission=(1.0, 0.62, 0.30),
                                emission_strength=8.0, sss=0.3)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.16)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((-1.4, 0.35, 0.86))
                        @ Matrix.Diagonal((1, 1, 1.35, 1)), verts=bm.verts)
    bc.bm_to_object("ENV_Lantern", bm, coll, [paper])
    dark_wood, _, _ = bc.principled("ENV_DarkWood", (0.16, 0.09, 0.05), rough=0.45, coat=0.3)
    for zc in (0.655, 1.07):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.12, radius2=0.12,
                              depth=0.03, matrix=Matrix.Translation((-1.4, 0.35, zc)))
        bc.bm_to_object(f"ENV_LanternCap_{zc}", bm, coll, [dark_wood])
    # hanging scroll on the wall (paper + rods + simple ink mountain)
    paper2, _, _ = bc.principled("ENV_ScrollPaper", (0.93, 0.89, 0.78), rough=0.9, sss=0.1)
    ink, _, _ = bc.principled("ENV_Ink", (0.12, 0.13, 0.16), rough=0.9)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((-1.9, 3.03, 2.45))
                        @ Matrix.Diagonal((0.7, 0.01, 1.6, 1)), verts=bm.verts)
    bc.bm_to_object("ENV_ScrollPaper", bm, coll, [paper2], smooth=False)
    for zc in (1.62, 3.27):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.025, radius2=0.025,
                              depth=0.82, matrix=Matrix.Translation((-1.9, 3.0, zc))
                              @ Matrix.Rotation(math.radians(90), 4, "Y"))
        bc.bm_to_object(f"ENV_ScrollRod_{zc}", bm, coll, [dark_wood])
    bm = bmesh.new()
    pts = [(-0.28, 2.0), (-0.12, 2.45), (0.0, 2.3), (0.14, 2.62), (0.28, 2.0)]
    vs = [bm.verts.new((-1.9 + x, 3.02, z)) for x, z in pts]
    bm.faces.new(vs)
    bc.bm_to_object("ENV_ScrollInk", bm, coll, [ink], smooth=False)
    pl = bpy.data.lights.new("ENV_LanternLight", "POINT")
    pl.energy = 120
    pl.color = (1.0, 0.65, 0.35)
    pl.shadow_soft_size = 0.15
    plo = bpy.data.objects.new("ENV_LanternLight", pl)
    coll.objects.link(plo)
    plo.location = (-1.4, 0.35, 0.88)
    # teapot-ish pot and cups
    ceramic, _, _ = bc.principled("ENV_Ceramic", (0.25, 0.45, 0.42), rough=0.2, coat=0.6)
    for name, x, rad, h in (("Pot", -0.85, 0.12, 0.16), ("Cup1", -0.6, 0.045, 0.06)):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=rad)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((x, 0.4, 0.655 + h * 0.5))
                            @ Matrix.Diagonal((1, 1, h / (2 * rad) * 1.4, 1)), verts=bm.verts)
        bc.bm_to_object(f"ENV_{name}", bm, coll, [ceramic])
    # lights: cool window key + warm bounce + soft fill
    sun = bpy.data.lights.new("ENV_WindowSun", "SUN")
    sun.energy = 3.5
    sun.color = (0.80, 0.88, 1.0)
    sun.angle = math.radians(4)
    so = bpy.data.objects.new("ENV_WindowSun", sun)
    coll.objects.link(so)
    so.rotation_euler = (math.radians(-60), math.radians(-12), math.radians(200))
    area_light(coll, "ENV_CineFill", (2.8, -3.5, 2.6), (0, 0, 1.8), 220, 3.0, (0.75, 0.82, 1.0))
    area_light(coll, "ENV_CineWarm", (-2.5, -1.5, 1.6), (0, 0, 1.6), 260, 2.0, (1.0, 0.72, 0.45))
    area_light(coll, "ENV_CineRim", (1.6, 2.6, 3.4), (0, 0, 2.0), 600, 1.5, (0.85, 0.92, 1.0))
    world((0.45, 0.42, 0.40), 0.25)
    return coll


# ----------------------------------------------------------------------------
# Cameras
# ----------------------------------------------------------------------------

def camera(name, target, dist, yaw, pitch=0.0, lens=85, fstop=None, focus=None, shift_z=0.0):
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        bpy.context.scene.collection.objects.link(cam)
    t = Vector(target)
    y = math.radians(yaw)
    p = math.radians(pitch)
    offs = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
    cam.location = t + offs
    cam.rotation_euler = (-offs).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    cam.data.shift_y = shift_z
    cam.data.dof.use_dof = fstop is not None
    if fstop:
        cam.data.dof.aperture_fstop = fstop
        cam.data.dof.focus_distance = ((focus or t) - cam.location).length
    bpy.context.scene.camera = cam
    return cam


VIEWS = {
    "01_front_portrait": dict(target=FOCUS_HEAD + Vector((0, 0, 0.05)), dist=4.2, yaw=0,
                              pitch=2, lens=85, fstop=2.8),
    "02_three_quarter_portrait": dict(target=FOCUS_HEAD + Vector((0, 0, 0.05)), dist=4.2,
                                      yaw=38, pitch=4, lens=85, fstop=2.8),
    "03_side_profile": dict(target=FOCUS_HEAD + Vector((0, 0, 0.05)), dist=4.2, yaw=90,
                            pitch=2, lens=85, fstop=2.8),
    "04_back_view": dict(target=FOCUS_HEAD + Vector((0, 0, 0.0)), dist=4.4, yaw=165,
                         pitch=6, lens=85, fstop=2.8),
    "05_fullbody_front": dict(target=FOCUS_BODY, dist=7.6, yaw=0, pitch=3, lens=55, fstop=4.0,
                              focus=FOCUS_HEAD),
    "06_fullbody_three_quarter": dict(target=FOCUS_BODY, dist=7.6, yaw=-35, pitch=5, lens=55,
                                      fstop=4.0, focus=FOCUS_HEAD),
}


def render(path, cam_kwargs=None):
    if cam_kwargs:
        camera("CAM_Test", **cam_kwargs)
    scn = bpy.context.scene
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[bob] rendered {path}")


# ----------------------------------------------------------------------------
# Character posing helpers (work once the rig exists)
# ----------------------------------------------------------------------------

def rig():
    return bpy.data.objects.get("BOB_Rig")


def reset_pose():
    r = rig()
    if not r:
        return
    for pb in r.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    try:
        import build_expressions as be
        be.apply_expression("Neutral")
    except Exception as exc:  # rig not built yet
        print("[bob] no expressions:", exc)
    for side in "LR":
        r[f"arm_ik_{side}"] = 0.0
    pose_relaxed()


def set_expression(name):
    import build_expressions as be
    be.apply_expression(name)
    bpy.context.view_layer.update()


def rotate_world(pb, axis, degrees):
    """Pose a bone by a rotation expressed in world (armature) space at rest."""
    ml = pb.bone.matrix_local.to_3x3()
    rw = Matrix.Rotation(math.radians(degrees), 3, Vector(axis))
    local = (ml.inverted() @ rw @ ml).to_quaternion()
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = local @ pb.rotation_quaternion


def move_world(pb, target):
    """Place a parentless-at-rest control bone's head at a world position."""
    ml = pb.bone.matrix_local
    pb.location = ml.to_3x3().inverted() @ (Vector(target) - ml.translation)


def pose_relaxed():
    """Natural standing pose: arms closer to the body, elbows softly bent, hands relaxed."""
    r = rig()
    if not r:
        return
    ctrl = r.pose.bones["CTRL_face"]
    for side, s in (("L", 1), ("R", -1)):
        rotate_world(r.pose.bones[f"upper_arm.{side}"], (0, 1, 0), 22 * s)
        rotate_world(r.pose.bones[f"upper_arm.{side}"], (1, 0, 0), -6)
        rotate_world(r.pose.bones[f"forearm.{side}"], (1, 0, 0), -16)
        rotate_world(r.pose.bones[f"forearm.{side}"], (0, 1, 0), 8 * s)
        ctrl[f"hand_{side}_relax"] = 1.0
    bpy.context.view_layer.update()


# ----------------------------------------------------------------------------
# Test sets
# ----------------------------------------------------------------------------

def do_portraits(samples, folder="portraits", prefix=""):
    setup_cycles(samples, (1400, 1400))
    set_env_visible("ENV_Studio")
    for name, kw in VIEWS.items():
        if "fullbody" in name:
            continue
        render(os.path.join(RENDERS, folder, f"{prefix}{name}.png"), kw)


def do_fullbody(samples):
    setup_cycles(samples, (1200, 1800))
    set_env_visible("ENV_Studio")
    for name, kw in VIEWS.items():
        if "fullbody" in name:
            render(os.path.join(RENDERS, "portraits", f"{name}.png"), kw)


def do_expressions(samples):
    import build_expressions as be
    setup_cycles(samples, (540, 540))
    set_env_visible("ENV_Studio")
    paths = []
    for i, name in enumerate(be.EXPRESSION_ORDER):
        reset_pose()
        set_expression(name)
        p = os.path.join(RENDERS, "expressions", f"expr_{i + 1:02d}_{name.lower()}.png")
        render(p, dict(target=FOCUS_HEAD + Vector((0, 0, 0.06)), dist=4.0, yaw=12, pitch=3,
                       lens=85, fstop=4.0))
        paths.append((name, p))
    reset_pose()
    contact_sheet(paths, os.path.join(RENDERS, "expressions", "bob_expression_sheet.png"), cols=4)


def contact_sheet(items, out, cols=4, label_h=56):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[bob] PIL not available - skipping contact sheet")
        return
    ims = [(n, Image.open(p).convert("RGB")) for n, p in items]
    w, h = ims[0][1].size
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new("RGB", (cols * w, rows * (h + label_h)), (28, 30, 36))
    font = None
    for fp in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "C:/Windows/Fonts/arialbd.ttf", "/Library/Fonts/Arial Bold.ttf"):
        if os.path.exists(fp):
            font = ImageFont.truetype(fp, 34)
            break
    draw = ImageDraw.Draw(sheet)
    for i, (n, im) in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * (h + label_h)
        sheet.paste(im, (x, y))
        draw.text((x + 18, y + h + 8), f"{i + 1}. {n}", fill=(235, 235, 240), font=font)
    sheet.save(out)
    print(f"[bob] contact sheet {out}")


def do_turntable(samples, frames=24):
    setup_cycles(samples, (720, 960))
    set_env_visible("ENV_Studio")
    r = rig()
    root = r.pose.bones["root"] if r else None
    folder = os.path.join(RENDERS, "turntable")
    paths = []
    for i in range(frames):
        ang = 2 * math.pi * i / frames
        if root:
            root.rotation_mode = "XYZ"
            root.rotation_euler = (0, 0, 0)
            # root bone points along +Y (rest), so its local Y axis is world Z after the
            # roll; rotate the whole armature object instead for a clean turntable
            r.rotation_euler = (0, 0, ang)
        bpy.context.view_layer.update()
        p = os.path.join(folder, f"turntable_{i:03d}.png")
        render(p, dict(target=FOCUS_BODY + Vector((0, 0, 0.1)), dist=7.2, yaw=0, pitch=4,
                       lens=55, fstop=5.6, focus=FOCUS_HEAD))
        paths.append(p)
    if r:
        r.rotation_euler = (0, 0, 0)
    # encode a video + gif if ffmpeg is available
    try:
        import subprocess
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "12", "-i",
                        os.path.join(folder, "turntable_%03d.png"), "-pix_fmt", "yuv420p",
                        "-vf", "scale=720:-2", os.path.join(folder, "bob_turntable.mp4")],
                       check=False)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "12", "-i",
                        os.path.join(folder, "turntable_%03d.png"), "-vf",
                        "scale=450:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse",
                        os.path.join(folder, "bob_turntable.gif")], check=False)
    except Exception as exc:
        print("[bob] ffmpeg encode skipped:", exc)


def do_interaction(samples):
    """Bob holding a teacup and admiring it."""
    import bmesh
    setup_cycles(samples, (1400, 1400))
    set_env_visible("ENV_Studio")
    r = rig()
    reset_pose()
    coll = env_collection("ENV_Props")
    cup_mat, _, _ = bc.principled("PROP_Cup", (0.92, 0.90, 0.85), rough=0.15, coat=0.8)
    tea, _, _ = bc.principled("PROP_Tea", (0.55, 0.30, 0.10), rough=0.05, coat=1.0)
    bm = bmesh.new()
    prof = [(0.0, 0.0), (0.045, 0.0), (0.06, 0.012), (0.075, 0.06), (0.085, 0.10),
            (0.078, 0.10), (0.068, 0.062), (0.052, 0.02), (0.0, 0.02)]
    segs = 48
    rings = []
    for (rr, zz) in prof:
        rings.append([bm.verts.new((rr * math.cos(2 * math.pi * k / segs),
                                    rr * math.sin(2 * math.pi * k / segs), zz))
                      for k in range(segs)])
    for i in range(len(rings) - 1):
        for k in range(segs):
            k1 = (k + 1) % segs
            bm.faces.new((rings[i][k], rings[i][k1], rings[i + 1][k1], rings[i + 1][k]))
    cup = bc.bm_to_object("PROP_Teacup", bm, coll, [cup_mat], subsurf=1, render_subsurf=2)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=48, radius=0.07)
    bmesh.ops.translate(bm, vec=(0, 0, 0.075), verts=bm.verts)
    liquid = bc.bm_to_object("PROP_Tea", bm, coll, [tea])
    liquid.parent = cup
    if r:
        ik = r.pose.bones["hand_ik.R"]
        r["arm_ik_R"] = 1.0
        # offering pose: right hand forward at chest height, palm turned up
        move_world(ik, Vector((-0.42, -0.48, 1.36)))
        rotate_world(ik, (0, 1, 0), -95)
        rotate_world(ik, (0, 0, 1), 35)
        ctrl = r.pose.bones["CTRL_face"]
        ctrl["hand_R_relax"] = 0.0
        ctrl["hand_R_fist"] = 0.35
        set_expression("Happy")
        ctrl["look_x"] = -0.6
        ctrl["look_y"] = -0.55
        head = r.pose.bones["head"]
        head.rotation_mode = "XYZ"
        head.rotation_euler = (math.radians(10), math.radians(-12), math.radians(-6))
        bpy.context.view_layer.update()
        # sit the cup on the palm: palm centre + palm normal (right palm = local +X at rest)
        hand_ob = bpy.data.objects["BOB_Hand_R"]
        mw = hand_ob.matrix_world
        palm = mw @ Vector((0.0, 0.0, -0.06))
        normal = (mw.to_3x3() @ Vector((1, 0, 0))).normalized()
        cup.location = palm + normal * 0.045 - Vector((0, 0, 0.012))
        bpy.context.view_layer.update()
    render(os.path.join(RENDERS, "cinematic_tests", "09_interaction_teacup.png"),
           dict(target=Vector((-0.22, -0.1, 1.80)), dist=5.4, yaw=-28, pitch=5, lens=65,
                fstop=3.2, focus=Vector((-0.3, -0.45, 1.6))))
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    if r:
        r["arm_ik_R"] = 0.0
    reset_pose()


def do_cinematic(samples):
    setup_cycles(samples, (1920, 1080))
    if not bpy.data.collections.get("ENV_Cinematic"):
        build_cinematic()
    set_env_visible("ENV_Cinematic")
    bpy.context.scene["bob_scene_tint"] = 0.6     # character picks up the set's light hue
    r = rig()
    reset_pose()
    if r:
        set_expression("Thinking")
        head = r.pose.bones["head"]
        head.rotation_mode = "XYZ"
        head.rotation_euler = (math.radians(4), math.radians(-6), math.radians(-14))
        r.rotation_euler = (0, 0, math.radians(-18))
        bpy.context.view_layer.update()
    render(os.path.join(RENDERS, "cinematic_tests", "10_cinematic_interior.png"),
           dict(target=Vector((-0.75, 0.6, 1.55)), dist=7.6, yaw=14, pitch=7, lens=38,
                fstop=2.2, focus=FOCUS_HEAD + Vector((0, -0.3, 0))))
    if r:
        r.rotation_euler = (0, 0, 0)
    reset_pose()
    bpy.context.scene["bob_scene_tint"] = 0.0
    set_env_visible("ENV_Studio")


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"only": None, "wip": None, "samples": None, "all": False, "save_envs": False}
    for i, a in enumerate(argv):
        if a == "--only":
            opts["only"] = argv[i + 1].split(",")
        elif a == "--wip":
            opts["wip"] = argv[i + 1]
        elif a == "--samples":
            opts["samples"] = int(argv[i + 1])
        elif a == "--all":
            opts["all"] = True
        elif a == "--save-envs":
            opts["save_envs"] = True
    return opts


def save_env_files():
    blender_dir = os.path.join(PROJECT, "blender")
    build_studio()
    set_env_visible("ENV_Studio")
    camera("CAM_Studio", **VIEWS["06_fullbody_three_quarter"])
    setup_cycles(128, (1600, 1600))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(blender_dir, "bob_studio.blend"),
                                copy=True)
    build_cinematic()
    set_env_visible("ENV_Cinematic")
    camera("CAM_Cinematic", target=Vector((-0.75, 0.6, 1.55)), dist=7.6, yaw=14, pitch=7,
           lens=38, fstop=2.2, focus=FOCUS_HEAD + Vector((0, -0.3, 0)))
    setup_cycles(128, (1920, 1080))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(blender_dir, "bob_cinematic_test.blend"),
                                copy=True)
    set_env_visible("ENV_Studio")


def main():
    o = parse()
    if not bpy.data.collections.get("ENV_Studio"):
        build_studio()
    set_env_visible("ENV_Studio")
    reset_pose()
    if o["wip"]:
        setup_cycles(o["samples"] or 24, (900, 900))
        names = list(VIEWS) if o["only"] is None else [n for n in VIEWS
                                                        if any(k in n for k in o["only"])]
        for name in names:
            if "fullbody" in name:
                setup_cycles(o["samples"] or 24, (600, 900))
            else:
                setup_cycles(o["samples"] or 24, (900, 900))
            render(os.path.join(RENDERS, "wip", f"{o['wip']}_{name}.png"), VIEWS[name])
        return
    sets = o["only"] or (["portraits", "fullbody", "expressions", "turntable", "interaction",
                          "cinematic"] if o["all"] else [])
    s = o["samples"]
    if "portraits" in sets:
        do_portraits(s or 96)
    if "fullbody" in sets:
        do_fullbody(s or 96)
    if "expressions" in sets:
        do_expressions(s or 64)
    if "turntable" in sets:
        do_turntable(s or 32)
    if "interaction" in sets:
        do_interaction(s or 96)
    if "cinematic" in sets:
        do_cinematic(s or 96)
    if o["save_envs"]:
        save_env_files()


if __name__ == "__main__":
    main()
