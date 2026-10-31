"""Bob - rig: body skeleton with IK/FK arms, IK legs, and a bone + shape-key face rig.

Body:   root > hips > spine > chest > neck > head
        chest > clavicle.L/R > upper_arm > forearm > hand        (FK, IK via hand_ik.*)
        hips > thigh.L/R > shin > foot                              (IK via foot_ik.*)
Face:   head > eye.L/R (look), lid_up.L/R + lid_low.L/R (blink / lid shapes),
        brow.L/R (move / tilt), CTRL_face (all facial sliders live here)
Switches (custom props on the BOB_Rig object):
        arm_ik_L / arm_ik_R   0 = FK, 1 = IK          leg_ik_L / leg_ik_R  (default 1)

Cloth, sleeves and legs are skinned with generated weights (distance-to-bone with
smooth falloff and per-region masks); rigid parts (head, hair, eyes, hands) are
bone-parented.
"""

import math
import bpy
from mathutils import Vector, Matrix
import bob_common as bc

FACE_PROPS = {
    # name: (default, min, max, description)
    "blink_L": (0.0, 0, 1, "Close Bob's left eye"),
    "blink_R": (0.0, 0, 1, "Close Bob's right eye"),
    "lids_sleepy": (0.0, 0, 1, "Upper lids half closed (bored / tired)"),
    "lids_happy": (0.0, 0, 1, "Lower lids push up (smiling eyes)"),
    "lids_angry": (0.0, 0, 1, "Upper lids slant down towards the nose"),
    "lids_sad": (0.0, 0, 1, "Upper lids slant down towards the outside"),
    "lids_wide": (0.0, 0, 1, "Eyes wide open"),
    "look_x": (0.0, -1, 1, "Both eyes look left/right (+ = Bob's left)"),
    "look_y": (0.0, -1, 1, "Both eyes look down/up"),
    "eye_L_x": (0.0, -1, 1, "Left eye only, left/right"),
    "eye_L_y": (0.0, -1, 1, "Left eye only, down/up"),
    "eye_R_x": (0.0, -1, 1, "Right eye only, left/right"),
    "eye_R_y": (0.0, -1, 1, "Right eye only, down/up"),
    "brow_L_up": (0.0, -1, 1, "Left brow down/up"),
    "brow_R_up": (0.0, -1, 1, "Right brow down/up"),
    "brow_L_tilt": (0.0, -1, 1, "Left brow tilt (+ = angry, - = worried)"),
    "brow_R_tilt": (0.0, -1, 1, "Right brow tilt (+ = angry, - = worried)"),
    "brow_L_arch": (0.0, -1, 1, "Left brow shape (- flat, + arched)"),
    "brow_R_arch": (0.0, -1, 1, "Right brow shape (- flat, + arched)"),
    "brow_squeeze": (0.0, 0, 1, "Pull both brows towards the centre"),
    "mouth_smile": (0.0, 0, 1, "Closed smile"),
    "mouth_frown": (0.0, 0, 1, "Frown"),
    "mouth_open": (0.0, 0, 1, "Jaw open"),
    "mouth_wide": (0.0, 0, 1, "Stretch mouth wide"),
    "mouth_narrow": (0.0, 0, 1, "Pucker / narrow"),
    "mouth_smirk": (0.0, -1, 1, "Smirk (+ left corner, - right corner)"),
    "mouth_grin": (0.0, 0, 1, "Big open grin with teeth"),
    "mouth_cry": (0.0, 0, 1, "Wobbly crying mouth"),
    "vis_A": (0.0, 0, 1, "Viseme AA / AH"),
    "vis_E": (0.0, 0, 1, "Viseme EE / EH"),
    "vis_O": (0.0, 0, 1, "Viseme OH"),
    "vis_U": (0.0, 0, 1, "Viseme OO / W"),
    "vis_MBP": (0.0, 0, 1, "Viseme M / B / P"),
    "vis_FV": (0.0, 0, 1, "Viseme F / V"),
    "blush": (0.0, 0, 1, "Rosy cheeks"),
    "tears": (0.0, 0, 1, "Tear streams"),
    "sweat": (0.0, 0, 1, "Sweat drop"),
    "hand_L_relax": (0.0, 0, 1, "Left hand relaxed curl"),
    "hand_L_fist": (0.0, 0, 1, "Left hand fist"),
    "hand_L_point": (0.0, 0, 1, "Left hand pointing"),
    "hand_R_relax": (0.0, 0, 1, "Right hand relaxed curl"),
    "hand_R_fist": (0.0, 0, 1, "Right hand fist"),
    "hand_R_point": (0.0, 0, 1, "Right hand pointing"),
}

DEFORM = ["hips", "spine", "chest", "neck", "head"] + [
    f"{b}.{s}" for s in "LR" for b in ("clavicle", "upper_arm", "forearm", "hand",
                                       "thigh", "shin", "foot")]


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------
# Skeleton
# ----------------------------------------------------------------------------

def build_armature(coll):
    J = bc.J
    arm = bpy.data.armatures.new("BOB_RigData")
    arm.display_type = "OCTAHEDRAL"
    rig = bc.new_object("BOB_Rig", arm, coll)
    rig.show_in_front = True
    bpy.context.view_layer.objects.active = rig
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.edit_bones

    def bone(name, head, tail, parent=None, connect=False, deform=False, roll_up=None):
        b = eb.new(name)
        b.head, b.tail = Vector(head), Vector(tail)
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        b.use_deform = deform
        if roll_up is not None:
            b.align_roll(Vector(roll_up))
        return b

    bone("root", (0, 0, 0), (0, 0.6, 0))
    bone("hips", J["hips"], J["spine"], "root", deform=True)
    bone("spine", J["spine"], J["chest"], "hips", True, True)
    bone("chest", J["chest"], J["neck"], "spine", True, True)
    bone("neck", J["neck"], J["head"], "chest", True, True)
    bone("head", J["head"], J["head_top"], "neck", True, True)
    for s in "LR":
        sgn = 1 if s == "L" else -1
        fwd = (0, -1, 0)
        bone(f"clavicle.{s}", J[f"clavicle.{s}"], J[f"shoulder.{s}"], "chest", deform=True,
             roll_up=(0, 0, 1))
        bone(f"upper_arm.{s}", J[f"shoulder.{s}"], J[f"elbow.{s}"], f"clavicle.{s}", True, True,
             roll_up=fwd)
        bone(f"forearm.{s}", J[f"elbow.{s}"], J[f"wrist.{s}"], f"upper_arm.{s}", True, True,
             roll_up=fwd)
        bone(f"hand.{s}", J[f"wrist.{s}"], J[f"hand_tip.{s}"], f"forearm.{s}", True, True,
             roll_up=fwd)
        hand_dir = (J[f"hand_tip.{s}"] - J[f"wrist.{s}"]).normalized()
        bone(f"hand_ik.{s}", J[f"wrist.{s}"], J[f"wrist.{s}"] + hand_dir * 0.16, "root",
             roll_up=fwd)
        bone(f"elbow_pole.{s}", J[f"elbow.{s}"] + Vector((0.05 * sgn, 0.7, 0)),
             J[f"elbow.{s}"] + Vector((0.05 * sgn, 0.8, 0)), "root")
        bone(f"thigh.{s}", J[f"hip.{s}"], J[f"knee.{s}"], "hips", deform=True, roll_up=fwd)
        bone(f"shin.{s}", J[f"knee.{s}"], J[f"ankle.{s}"], f"thigh.{s}", True, True,
             roll_up=fwd)
        bone(f"foot.{s}", J[f"ankle.{s}"], J[f"toe.{s}"], f"shin.{s}", True, True,
             roll_up=(0, 0, 1))
        bone(f"foot_ik.{s}", J[f"ankle.{s}"], J[f"toe.{s}"], "root", roll_up=(0, 0, 1))
        bone(f"knee_pole.{s}", J[f"knee.{s}"] + Vector((0, -0.8, 0)),
             J[f"knee.{s}"] + Vector((0, -0.9, 0)), "root")

    # face bones from the face geometry frames
    for s in "LR":
        white = bpy.data.objects[f"BOB_Eye_{s}_White"]
        m = white.matrix_world
        c = m.translation
        fwd = -Vector(m.col[1][:3]).normalized()
        up = Vector(m.col[2][:3])
        for name in (f"eye.{s}", f"lid_up.{s}", f"lid_low.{s}"):
            bone(name, c, c + fwd * 0.16, "head", roll_up=up)
        brow = bpy.data.objects[f"BOB_Brow_{s}"]
        bm_ = brow.matrix_world
        bc_ = bm_.translation
        bfwd = -Vector(bm_.col[1][:3]).normalized()
        bone(f"brow.{s}", bc_, bc_ + bfwd * 0.08, "head", roll_up=Vector(bm_.col[2][:3]))
    hc = bc.HEAD_C
    bone("CTRL_face", hc + Vector((0, -0.95, 0.75)), hc + Vector((0, -0.95, 0.88)), "head")
    for b in eb:
        b.use_deform = b.name in DEFORM
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def bone_collections(rig):
    arm = rig.data
    groups = {
        "Body": ["root", "hips", "spine", "chest", "neck", "head"] +
                [f"{b}.{s}" for s in "LR" for b in ("clavicle", "thigh", "shin", "foot")],
        "Arms FK": [f"{b}.{s}" for s in "LR" for b in ("upper_arm", "forearm", "hand")],
        "IK Controls": [f"{b}.{s}" for s in "LR" for b in ("hand_ik", "elbow_pole", "foot_ik",
                                                          "knee_pole")],
        "Face": ["CTRL_face"] + [f"{b}.{s}" for s in "LR" for b in ("eye", "lid_up", "lid_low",
                                                                     "brow")],
    }
    for gname, names in groups.items():
        bcoll = arm.collections.get(gname) or arm.collections.new(gname)
        for n in names:
            bcoll.assign(arm.bones[n])


def widgets(rig):
    import bmesh
    coll = bc.sub_collection("Widgets")
    coll.hide_render = True
    coll.hide_viewport = True

    def circle(name, r=1.0):
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, segments=32, radius=r)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        return bc.new_object(name, me, coll)

    def square(name):
        bm = bmesh.new()
        vs = [bm.verts.new(v) for v in ((-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1))]
        for i in range(4):
            bm.edges.new((vs[i], vs[(i + 1) % 4]))
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        return bc.new_object(name, me, coll)

    wc = circle("WGT_circle")
    ws = square("WGT_square")
    for pb in rig.pose.bones:
        if pb.name.startswith(("hand_ik", "foot_ik", "root")):
            pb.custom_shape = wc
            pb.custom_shape_scale_xyz = (1.2, 1.2, 1.2) if pb.name != "root" else (2.5, 2.5, 2.5)
        elif pb.name.startswith(("elbow_pole", "knee_pole")):
            pb.custom_shape = wc
            pb.custom_shape_scale_xyz = (0.4, 0.4, 0.4)
        elif pb.name == "CTRL_face":
            pb.custom_shape = ws
            pb.custom_shape_scale_xyz = (0.8, 0.8, 0.8)


# ----------------------------------------------------------------------------
# Constraints (IK / FK)
# ----------------------------------------------------------------------------

def prop_driver(target_id, path, rig, var_paths, expr, index=-1):
    fc = target_id.driver_add(path, index) if index >= 0 else target_id.driver_add(path)
    d = fc.driver
    d.type = "SCRIPTED"
    for vname, dpath in var_paths.items():
        v = d.variables.new()
        v.name = vname
        v.type = "SINGLE_PROP"
        v.targets[0].id = rig
        v.targets[0].data_path = dpath
    d.expression = expr
    return fc


def setup_ik(rig):
    for s in "LR":
        rig[f"arm_ik_{s}"] = 0.0
        rig[f"leg_ik_{s}"] = 1.0
        for p in (f"arm_ik_{s}", f"leg_ik_{s}"):
            rig.id_properties_ui(p).update(min=0.0, max=1.0, description="0 = FK, 1 = IK")
        for chain, tip, ctl, pole, switch in (("forearm", "hand", "hand_ik", "elbow_pole", "arm"),
                                              ("shin", "foot", "foot_ik", "knee_pole", "leg")):
            pb = rig.pose.bones[f"{chain}.{s}"]
            ik = pb.constraints.new("IK")
            ik.name = "IK"
            ik.target = rig
            ik.subtarget = f"{ctl}.{s}"
            ik.pole_target = rig
            ik.pole_subtarget = f"{pole}.{s}"
            ik.chain_count = 2
            cr = rig.pose.bones[f"{tip}.{s}"].constraints.new("COPY_ROTATION")
            cr.name = "IK Rotation"
            cr.target = rig
            cr.subtarget = f"{ctl}.{s}"
            for con in (ik, cr):
                prop_driver(con, "influence", rig, {"ik": f'["{switch}_ik_{s}"]'}, "ik")
            # find the pole angle that keeps the rest pose
            pick_pole_angle(rig, ik, f"{chain}.{s}", switch, s)


def pick_pole_angle(rig, ik, bone_name, switch, s):
    key = f"{switch}_ik_{s}"
    old = rig[key]
    rig[key] = 1.0
    fc = rig.animation_data.drivers.find(f'pose.bones["{bone_name}"].constraints["IK"].influence')
    if fc:
        fc.mute = True
    ik.influence = 1.0
    rest_head = rig.data.bones[bone_name].head_local.copy()
    best = (1e9, 0.0)
    for deg in range(-180, 181, 5):
        ik.pole_angle = math.radians(deg)
        bpy.context.view_layer.update()
        d = (rig.pose.bones[bone_name].head - rest_head).length
        tail_d = (rig.pose.bones[bone_name].tail - rig.data.bones[bone_name].tail_local).length
        if d + tail_d < best[0]:
            best = (d + tail_d, deg)
    ik.pole_angle = math.radians(best[1])
    if fc:
        fc.mute = False
    rig[key] = old
    bpy.context.view_layer.update()
    print(f"[bob] pole angle {bone_name}: {best[1]} deg (err {best[0]:.4f})")


# ----------------------------------------------------------------------------
# Skinning
# ----------------------------------------------------------------------------

def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length


def skin(ob, rig, bones, mask=None, power=5.0, keep=2):
    me = ob.data
    mw = ob.matrix_world
    segs = {b: (rig.data.bones[b].head_local, rig.data.bones[b].tail_local) for b in bones}
    groups = {b: (ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)) for b in bones}
    for v in me.vertices:
        p = mw @ v.co
        ws = []
        for b in bones:
            d = seg_dist(p, *segs[b])
            w = 1.0 / (d ** power + 1e-7)
            if mask:
                w *= mask(b, p)
            ws.append((w, b))
        ws.sort(reverse=True)
        ws = ws[:keep]
        tot = sum(w for w, _ in ws) or 1.0
        for w, b in ws:
            if w / tot > 0.001:
                groups[b].add([v.index], w / tot, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    _move_first(ob, mod)
    world = ob.matrix_world.copy()
    ob.parent = rig
    ob.matrix_world = world


def _move_first(ob, mod):
    idx = list(ob.modifiers).index(mod)
    ob.modifiers.move(idx, 0)


def parent_to_bone(ob, rig, bone):
    world = ob.matrix_world.copy()
    ob.parent = rig
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = world


def robe_mask(b, p):
    if b.startswith("thigh"):
        return 0.7 * smoothstep(1.0, 0.62, p.z)
    if b.startswith("clavicle"):
        return smoothstep(0.17, 0.33, abs(p.x)) * smoothstep(1.40, 1.55, p.z) * 1.2
    return 1.0


def skin_all(rig):
    O = bpy.data.objects
    torso = ["hips", "spine", "chest", "clavicle.L", "clavicle.R", "thigh.L", "thigh.R"]
    for name in ("BOB_Robe", "BOB_Collar_Inner", "BOB_Collar_Outer", "BOB_Collar_Flap",
                 "BOB_Sash", "BOB_Hem_Trim", "BOB_Sash_Knot", "BOB_Sash_Tail_0",
                 "BOB_Sash_Tail_1"):
        skin(O[name], rig, torso, robe_mask)
    for s in "LR":
        arm_b = [f"clavicle.{s}", f"upper_arm.{s}", f"forearm.{s}", f"hand.{s}"]
        for name in (f"BOB_Sleeve_{s}", f"BOB_Cuff_{s}"):
            skin(O[name], rig, arm_b, power=6.0)
        skin(O[f"BOB_Leg_{s}"], rig, ["hips", f"thigh.{s}", f"shin.{s}"],
             lambda b, p: 0.3 if b == "hips" else 1.0, power=6.0)
        parent_to_bone(O[f"BOB_Shoe_{s}"], rig, f"foot.{s}")
        parent_to_bone(O[f"BOB_Hand_{s}"], rig, f"hand.{s}")
        parent_to_bone(O[f"BOB_Eye_{s}_Iris"], rig, f"eye.{s}")
        parent_to_bone(O[f"BOB_Eye_{s}_LidUp"], rig, f"lid_up.{s}")
        parent_to_bone(O[f"BOB_Eye_{s}_LidLow"], rig, f"lid_low.{s}")
        parent_to_bone(O[f"BOB_Brow_{s}"], rig, f"brow.{s}")
    skin(O["BOB_Neck"], rig, ["chest", "neck", "head"])
    rigid_head = [o for o in O if o.name.startswith(("BOB_Head", "BOB_Hair", "BOB_Nose",
                                                      "BOB_Mouth", "BOB_Teeth", "BOB_Tongue",
                                                      "BOB_Blush", "BOB_Tear", "BOB_Sweat"))
                  or (o.name.startswith("BOB_Eye_") and o.name.endswith(("_White", "_Rim",
                                                                         "_Highlight")))]
    for o in rigid_head:
        if o.parent is None and o.type == "MESH":
            parent_to_bone(o, rig, "head")


# ----------------------------------------------------------------------------
# Face drivers
# ----------------------------------------------------------------------------

def face_drivers(rig):
    ctrl = rig.pose.bones["CTRL_face"]
    for p, (dflt, lo, hi, desc) in FACE_PROPS.items():
        ctrl[p] = float(dflt)
        ctrl.id_properties_ui(p).update(min=float(lo), max=float(hi), soft_min=float(lo),
                                        soft_max=float(hi), description=desc)

    def P(name):
        return f'pose.bones["CTRL_face"]["{name}"]'

    def bone_drv(bone, path, idx, props, expr):
        pb = rig.pose.bones[bone]
        pb.rotation_mode = "XYZ"
        prop_driver(rig, f'pose.bones["{bone}"].{path}', rig, {k: P(k) for k in props}, expr, idx)

    for s, sgn in (("L", 1), ("R", -1)):
        # eyes: local X = up/down, local Z = left/right
        bone_drv(f"eye.{s}", "rotation_euler", 0, ["look_y", f"eye_{s}_y"],
                 f"0.40*(look_y + eye_{s}_y)")
        bone_drv(f"eye.{s}", "rotation_euler", 2, ["look_x", f"eye_{s}_x"],
                 f"0.48*(look_x + eye_{s}_x)")
        bl = f"blink_{s}"
        bone_drv(f"lid_up.{s}", "rotation_euler", 0,
                 [bl, "lids_sleepy", "lids_angry", "lids_sad", "lids_wide", "look_y"],
                 f"-min(2.08, 2.08*{bl} + 0.78*lids_sleepy + 0.52*lids_angry + 0.38*lids_sad)"
                 f" + 0.22*lids_wide + 0.12*look_y")
        bone_drv(f"lid_up.{s}", "rotation_euler", 1, ["lids_angry", "lids_sad", bl],
                 f"{0.40 * sgn}*(lids_angry - lids_sad)*(1 - {bl})")
        bone_drv(f"lid_low.{s}", "rotation_euler", 0, ["lids_happy", bl, "lids_angry", "lids_wide"],
                 f"0.62*lids_happy + 0.22*{bl} + 0.18*lids_angry - 0.12*lids_wide")
        # brows: local Z = up, rotation Y = tilt, local X = towards the centre line
        bone_drv(f"brow.{s}", "location", 2, [f"brow_{s}_up", "lids_wide"],
                 f"0.07*brow_{s}_up + 0.025*lids_wide")
        bone_drv(f"brow.{s}", "location", 0, ["brow_squeeze"], f"{0.022 * sgn}*brow_squeeze")
        bone_drv(f"brow.{s}", "rotation_euler", 1, [f"brow_{s}_tilt"],
                 f"{0.42 * sgn}*brow_{s}_tilt")

    def key_drv(obname, key, props, expr):
        ob = bpy.data.objects[obname]
        kb = ob.data.shape_keys.key_blocks[key]
        kb.slider_min = 0.0
        prop_driver(kb, "value", rig, {k: P(k) for k in props}, expr)

    for s in "LR":
        key_drv(f"BOB_Brow_{s}", "Arch", [f"brow_{s}_arch"], f"max(0, brow_{s}_arch)")
        key_drv(f"BOB_Brow_{s}", "Flat", [f"brow_{s}_arch"], f"max(0, -brow_{s}_arch)")
        for k, p in (("Relax", "relax"), ("Fist", "fist"), ("Point", "point")):
            key_drv(f"BOB_Hand_{s}", k, [f"hand_{s}_{p}"], f"hand_{s}_{p}")
        key_drv(f"BOB_Blush_{s}", "Show", ["blush"], "blush")
        key_drv(f"BOB_Tear_{s}", "Show", ["tears"], "tears")
    key_drv("BOB_Sweat", "Show", ["sweat"], "sweat")
    mouth_map = {"Smile": "mouth_smile", "Frown": "mouth_frown", "Open": "mouth_open",
                 "Wide": "mouth_wide", "Narrow": "mouth_narrow", "Grin": "mouth_grin",
                 "Cry": "mouth_cry", "A": "vis_A", "E": "vis_E", "O": "vis_O", "U": "vis_U",
                 "MBP": "vis_MBP", "FV": "vis_FV"}
    for obn in ("BOB_Mouth", "BOB_Teeth", "BOB_Tongue"):
        for key, p in mouth_map.items():
            key_drv(obn, key, [p], p)
        key_drv(obn, "SmirkL", ["mouth_smirk"], "max(0, mouth_smirk)")
        key_drv(obn, "SmirkR", ["mouth_smirk"], "max(0, -mouth_smirk)")


def build(M):
    coll = bc.sub_collection("Rig")
    rig = build_armature(coll)
    bone_collections(rig)
    widgets(rig)
    skin_all(rig)
    setup_ik(rig)
    face_drivers(rig)
    bpy.context.view_layer.update()
    return rig


if __name__ == "__main__":
    build(bc.get_materials())
