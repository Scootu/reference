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
