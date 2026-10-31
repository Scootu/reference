"""Bob - "Glassy" cinematic look (see documentation/glassy_look.md).

What makes the reference frames look glassy, and how each part is rebuilt here:
  1. bloom on every highlight             -> Glare (Bloom / Fog Glow)
  2. full-frame soft diffusion            -> big blur screened back at ~25%
  3. lifted, tinted blacks + warm highs   -> Color Balance (lift / gain)
  4. strong saturation                    -> Hue/Saturation
  5. subtle lens fringe + vignette        -> Lens Distortion dispersion, ellipse mask
  6. warm-vs-cool lighting moods          -> apply_mood(): sun / world / lantern colours,
                                             scene["bob_scene_tint"] so Bob picks up the hue

Usage inside Blender (Scripting tab), with the scripts folder on sys.path:
    import glassy_grade as gg
    gg.apply_grade(bpy.context.scene, "sunset")      # compositor look
    gg.apply_mood("sunset")                          # relight ENV_Cinematic + tint Bob
Presets: "day", "sunset", "night", "palace".
Works with Blender 4.2+ (scene.node_tree compositor) and 5.x (compositing node group).
"""

import bpy
import math

PRESETS = {
    #            lift (shadow tint)     gain (highlight tint)   sat   bloom thr/str  diffusion  tint
    "day":    dict(lift=(0.030, 0.026, 0.050), gain=(1.03, 1.00, 0.95), sat=1.12,
                   thr=0.80, bloom=0.55, diff=0.18, tint=0.35,
                   sun=(1.0, 0.93, 0.80), sun_e=4.0, sun_elev=40, world=(0.55, 0.65, 0.85),
                   world_e=0.45, lamp=(1.0, 0.70, 0.40), lamp_e=60),
    "sunset": dict(lift=(0.065, 0.025, 0.075), gain=(1.10, 0.95, 0.80), sat=1.20,
                   thr=0.70, bloom=0.85, diff=0.28, tint=0.65,
                   sun=(1.0, 0.55, 0.28), sun_e=5.0, sun_elev=8, world=(0.55, 0.35, 0.55),
                   world_e=0.40, lamp=(1.0, 0.60, 0.30), lamp_e=90),
    "night":  dict(lift=(0.030, 0.035, 0.090), gain=(0.90, 0.96, 1.12), sat=1.10,
                   thr=0.60, bloom=0.90, diff=0.25, tint=0.70,
                   sun=(0.55, 0.68, 1.0), sun_e=1.6, sun_elev=35, world=(0.10, 0.13, 0.32),
                   world_e=0.35, lamp=(1.0, 0.58, 0.28), lamp_e=180),
    "palace": dict(lift=(0.055, 0.028, 0.050), gain=(1.08, 0.97, 0.88), sat=1.16,
                   thr=0.72, bloom=0.70, diff=0.22, tint=0.50,
                   sun=(1.0, 0.82, 0.60), sun_e=3.0, sun_elev=30, world=(0.45, 0.32, 0.40),
                   world_e=0.35, lamp=(1.0, 0.62, 0.32), lamp_e=140),
}


# ----------------------------------------------------------------------------
# helpers that work across the 4.x and 5.x compositor APIs
# ----------------------------------------------------------------------------

def _inp(node, *names):
    for n in names:
        for s in node.inputs:
            if s.identifier == n or s.name == n:
                return s
    return None


def _set(node, value, *names, prop=None):
    """Set a socket default (5.x style) or fall back to a node property (4.x style)."""
    s = _inp(node, *names)
    if s is not None and hasattr(s, "default_value"):
        try:
            s.default_value = value
            return True
        except Exception:
            pass
    if prop and hasattr(node, prop):
        try:
            setattr(node, prop, value)
            return True
        except Exception:
            pass
    return False


def _tree(scene):
    """Return (tree, output_socket_callable) for the scene compositor."""
    if hasattr(scene, "compositing_node_group"):            # Blender 5.x
        ng = bpy.data.node_groups.get("BOB_GlassyGrade")
        if ng is None:
            ng = bpy.data.node_groups.new("BOB_GlassyGrade", "CompositorNodeTree")
        ng.nodes.clear()
        if not any(i.in_out == "OUTPUT" for i in ng.interface.items_tree):
            ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        scene.compositing_node_group = ng
        out = ng.nodes.new("NodeGroupOutput")
        return ng, out.inputs[0]
    scene.use_nodes = True                                  # Blender 4.x
    nt = scene.node_tree
    nt.nodes.clear()
    comp = nt.nodes.new("CompositorNodeComposite")
    return nt, comp.inputs[0]


def _mix(tree, blend, fac, clamp=False):
    """Colour mix node: returns (node, input_A, input_B, output)."""
    try:
        n = tree.nodes.new("CompositorNodeMixRGB")          # 4.x
        n.blend_type = blend
        n.use_clamp = clamp
        n.inputs[0].default_value = fac
        return n, n.inputs[1], n.inputs[2], n.outputs[0]
    except RuntimeError:
        n = tree.nodes.new("ShaderNodeMix")                 # 5.x
        n.data_type = "RGBA"
        n.blend_type = blend
        n.clamp_result = clamp
        by_id = lambda col, ident: next(x for x in col if x.identifier == ident)
        by_id(n.inputs, "Factor_Float").default_value = fac
        return (n, by_id(n.inputs, "A_Color"), by_id(n.inputs, "B_Color"),
                by_id(n.outputs, "Result_Color"))


# ----------------------------------------------------------------------------
# public API
# ----------------------------------------------------------------------------

def apply_grade(scene, preset="palace"):
    p = PRESETS[preset]
    tree, final = _tree(scene)
    L = tree.links.new
    rl = tree.nodes.new("CompositorNodeRLayers")
    rl.scene = scene
    img = rl.outputs["Image"]

    # 1. bloom on highlights
    glare = tree.nodes.new("CompositorNodeGlare")
    ok = _set(glare, "Bloom", "Type") or _set(glare, "Fog Glow", "Type")
    if not ok:
        for gt in ("BLOOM", "FOG_GLOW"):
            if _set(glare, gt, prop="glare_type"):
                break
    _set(glare, "High", "Quality", prop="quality")
    _set(glare, p["thr"], "Highlights Threshold", "Threshold", prop="threshold")
    _set(glare, p["bloom"], "Strength")
    _set(glare, 0.75, "Size")
    _set(glare, 8, prop="size")
    _set(glare, p["bloom"] - 1.0, prop="mix")       # 4.x: -1 = only image, 0 = 50/50
    L(img, glare.inputs[0])
    img = glare.outputs[0]

    # clamp to display range first: Screen blending of HDR (>1) values inverts them
    _, a, b, clamped = _mix(tree, "MIX", 0.0, clamp=True)
    L(img, a)
    L(img, b)
    img = clamped

    # 2. diffusion: blurred copy screened back on top
    blur = tree.nodes.new("CompositorNodeBlur")
    if not _set(blur, (60.0, 60.0), "Size"):
        blur.size_x, blur.size_y = 60, 60
        blur.use_relative = False
    L(img, blur.inputs[0])
    _, a, b, mixed = _mix(tree, "SCREEN", p["diff"], clamp=True)
    L(img, a)
    L(blur.outputs[0], b)
    img = mixed

    # 3. lifted, tinted blacks and warm/cool highlights
    cb = tree.nodes.new("CompositorNodeColorBalance")
    if hasattr(cb, "correction_method"):
        cb.correction_method = "LIFT_GAMMA_GAIN"
        cb.lift = tuple(1.0 + 0.9 * c for c in p["lift"])
        cb.gain = p["gain"]
    else:
        _set(cb, "Lift/Gamma/Gain", "Type")
        # neutral lift is white (1,1,1); values above 1 raise and tint the blacks
        _set(cb, (*[1.0 + 0.9 * c for c in p["lift"]], 1.0), "Color Lift")
        _set(cb, (*p["gain"], 1.0), "Color Gain")
    L(img, cb.inputs["Image"])
    img = cb.outputs[0]
    # keep the saturation stage in display range (HSV maths flips hues above 1.0)
    _, a, b, clamped = _mix(tree, "MIX", 0.0, clamp=True)
    L(img, a)
    L(img, b)
    img = clamped

    # 4. saturation
    hs = tree.nodes.new("CompositorNodeHueSat")
    _set(hs, p["sat"], "Saturation")
    L(img, hs.inputs["Image"])
    img = hs.outputs[0]

    # 5. subtle chromatic fringe + vignette
    lens = tree.nodes.new("CompositorNodeLensdist")
    _set(lens, 0.012, "Dispersion")
    L(img, lens.inputs["Image"])
    img = lens.outputs[0]
    ell = tree.nodes.new("CompositorNodeEllipseMask")
    if not _set(ell, (1.15, 1.15), "Size"):
        ell.width, ell.height = 1.15, 1.15
    vblur = tree.nodes.new("CompositorNodeBlur")
    if not _set(vblur, (220.0, 220.0), "Size"):
        vblur.size_x, vblur.size_y = 220, 220
    L(ell.outputs[0], vblur.inputs[0])
    _, a, b, vig = _mix(tree, "MULTIPLY", 0.30)
    L(img, a)
    L(vblur.outputs[0], b)
    L(vig, final)
    scene["bob_grade"] = preset
    return tree


def apply_mood(preset="palace"):
    """Relight the cinematic set for a mood and tint Bob to match."""
    p = PRESETS[preset]
    scn = bpy.context.scene
    scn["bob_scene_tint"] = p["tint"]
    O = bpy.data.objects
    sun = O.get("ENV_WindowSun")
    if sun:
        sun.data.color = p["sun"]
        sun.data.energy = p["sun_e"]
        sun.rotation_euler = (math.radians(-90 + p["sun_elev"]), math.radians(-12),
                              math.radians(200))
    lamp = O.get("ENV_LanternLight")
    if lamp:
        lamp.data.color = p["lamp"]
        lamp.data.energy = p["lamp_e"]
    w = scn.world
    if w and w.use_nodes:
        bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
        ramp = next((n for n in w.node_tree.nodes if n.type == "VALTORGB"), None)
        if ramp:
            ramp.color_ramp.elements[0].color = (*[c * 0.5 for c in p["world"]], 1)
            ramp.color_ramp.elements[1].color = (*p["world"], 1)
        if bg:
            bg.inputs["Strength"].default_value = p["world_e"]
    sky = bpy.data.materials.get("ENV_Sky")
    if sky:
        bsdf = sky.node_tree.nodes.get("Principled BSDF")
        if bsdf and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*p["sun"], 1)
    for name, col in (("ENV_CineWarm", p["lamp"]), ("ENV_CineRim", p["sun"])):
        ob = O.get(name)
        if ob:
            ob.data.color = col
    return p


def clear_grade(scene):
    """Turn the grade off again (studio renders use the exact palette)."""
    if hasattr(scene, "compositing_node_group"):
        scene.compositing_node_group = None
    else:
        scene.use_nodes = False
    scene["bob_grade"] = ""
