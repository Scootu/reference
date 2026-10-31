# Project Bob

Bob is a stylised 3D animated character, built entirely from Python scripts for Blender 4.2+
(tested with Blender 5.2). This project contains everything needed to rebuild, rig, render and
reuse him.

```
reference/       source frames (ref-0001 … ref-0005)
blender/         bob_character.blend   character + rig + expression panel
                 bob_studio.blend      character in the inspection studio (3-point light)
                 bob_cinematic_test.blend  character in a stylised interior set
scripts/         build_all.py (runs every stage) + one script per stage + render_tests.py
documentation/   style_analysis.md, modeling_decisions.md, rig_documentation.md
renders/         portraits/, expressions/, turntable/, cinematic_tests/
```

## Quick start

1. Open `blender/bob_studio.blend`.
2. Press **N** in the 3D view and open the **Bob** tab:
   - Click an expression to apply it.
   - Toggle "Keyframe on click" to animate.
3. Pose the body with the `BOB_Rig` bones. Switch the arms between FK and IK with the
   `arm_ik_L`/`arm_ik_R` sliders, which are in the same tab.

## Rebuild from scratch

```bash
cd bob_project
blender -b --python scripts/build_all.py
blender -b blender/bob_character.blend --python scripts/render_tests.py -- --all --save-envs
```

Renders use Cycles with OpenImageDenoise. On a GPU, set
*Preferences → System → Cycles Render Devices* and change `cy.device` in
`render_tests.setup_cycles` to `"GPU"`.

## Look controls (final pass)

- **Scene light tint:** the scene custom property `bob_scene_tint` (Scene Properties → Custom
  Properties) makes Bob pick up the *hue* of the set lighting (blue moonlight, orange sunset)
  while staying flat, as the reference characters do.
  - `0.0` = exact reference palette (studio)
  - `0.5` – `0.7` = cinematic scenes
  - EEVEE only.
- **Brush-like strokes:**
  - Eyes, brows and mouth have slightly soft edges. The round "surprised" eye stays crisp.
  - Outlines vary smoothly in weight (vertex group `outline_weight` + Solidify factor), like a
    hand-drawn line.
- **Render on your GPU with EEVEE:** set Preferences → System → GPU backend. Raise
  Render → Sampling to 64 or more for the cleanest soft edges.
