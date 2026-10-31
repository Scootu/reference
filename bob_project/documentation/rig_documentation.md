# Rig Documentation — Bob

Armature object: **`BOB_Rig`** (bone collections: Body, Arms FK, IK Controls, Face).

## Body bones

```
root
└─ hips ─ spine ─ chest ─ neck ─ head ─ (eye / lid_up / lid_low / brow .L/.R, CTRL_face)
   │                └─ clavicle.L/R ─ upper_arm ─ forearm ─ hand
   └─ thigh.L/R ─ shin ─ foot
controls (children of root): hand_ik.L/R, elbow_pole.L/R, foot_ik.L/R, knee_pole.L/R
```

| Control | What it does |
|---|---|
| `root` | Moves or turns the whole character (circle widget on the floor) |
| `hips` | Torso master: moves the upper body and the robe |
| `spine`, `chest` | Torso bend and twist; the robe follows through generated weights |
| `neck`, `head` | Head rotation. The whole face is rigid to the head bone. |
| `clavicle.*` | Shoulder shrug and raise |
| `upper_arm.*`, `forearm.*`, `hand.*` | FK arm (elbow bend on the forearm, wrist rotation on the hand) |
| `hand_ik.*` + `elbow_pole.*` | IK arm (move the hand control; the pole aims the elbow) |
| `foot_ik.*` + `knee_pole.*` | IK legs (on by default) |

**IK/FK switching** uses custom properties on the `BOB_Rig` object, which also appear in the
**Bob** sidebar tab:

- `arm_ik_L`, `arm_ik_R`: 0 = FK (default), 1 = IK. The value blends, so it can be animated for
  seamless switches.
- `leg_ik_L`, `leg_ik_R`: default 1.

The IK pole angles are computed automatically at build time so the IK rest pose matches the FK
rest pose. The measured error was below 0.5 mm.

## Skinning

- **Robe, collar, sash and hem:** weighted to hips, spine, chest, clavicles and thighs. Thighs
  only influence below the waist, and clavicles only the shoulder area, so leg poses swing the
  skirt without dragging the chest.
- **Sleeves and cuffs:** clavicle, upper_arm, forearm, hand. Weights come from distance to each
  bone with a power-6 falloff and the top 2 bones per vertex, giving smooth elbow bends.
- **Legs:** hips / thigh / shin.
- **Rigid parts (bone-parented):**
  - head bone: head, hair, nose, mouth layers, eyeballs, rims, highlights
  - `eye.*`: iris and pupil
  - `lid_*`: lids
  - `brow.*`: brows
  - `hand.*`: hands
  - `foot.*`: shoes

## Face controls

All facial sliders are custom properties on the **`CTRL_face`** pose bone (the square widget
floating in front of the head). They're also in the sidebar: 3D View → N → **Bob**. Every value
can be keyframed.

| Group | Sliders | Implementation |
|---|---|---|
| Blink | `blink_L`, `blink_R` | `lid_up` bone rotation (lower lid rises slightly) |
| Lid shapes | `lids_sleepy`, `lids_happy`, `lids_angry`, `lids_sad`, `lids_wide` | lid bone rotation and roll |
| Eye direction | `look_x`, `look_y` (both eyes), `eye_L_x/y`, `eye_R_x/y` (per eye) | `eye.*` bone rotation |
| Brows | `brow_L/R_up`, `brow_L/R_tilt` (+ angry, − worried), `brow_L/R_arch`, `brow_squeeze` | brow bones + `Arch`/`Flat` shape keys |
| Mouth | `mouth_smile`, `mouth_frown`, `mouth_open`, `mouth_wide`, `mouth_narrow`, `mouth_smirk` (±), `mouth_grin`, `mouth_cry` | shape keys on mouth, teeth and tongue |
| Visemes | `vis_A`, `vis_E`, `vis_O`, `vis_U`, `vis_MBP`, `vis_FV` | shape keys (for lip-sync) |
| Extras | `blush`, `tears`, `sweat` | shape keys (grow from nothing) |
| Hands | `hand_L/R_relax`, `hand_L/R_fist`, `hand_L/R_point` | finger-curl shape keys |

All drivers use simple expressions only (`var`, `a*(1-b)`, `min(...)`, `max(...)`), so they keep
working when Blender's "Auto Run Python Scripts" is disabled.

## Expression library

`scripts/build_expressions.py` defines 12 expressions as slider combinations plus a head pose:

Neutral, Happy, Laughing, Surprised, Confused, Angry, Sad, Scared, Bored, Thinking, Smirking,
Crying.

- **Sidebar panel:** the `.blend` contains a text block, `bob_expressions_ui.py`, that adds a
  button for each expression to the sidebar. Enable **Keyframe on click** to key the face and head
  at the current frame. If the panel doesn't appear when you open the file, allow scripts to run,
  or open the text block and press Run Script once.
- **From Python:**
  ```python
  import build_expressions
  build_expressions.apply_expression("Surprised", keyframe=True, frame=24)
  ```

## Rebuilding

```bash
# from bob_project/
blender -b --python scripts/build_all.py                       # rebuild bob_character.blend
blender -b blender/bob_character.blend --python scripts/render_tests.py -- --all --save-envs
```

The second command renders every test and writes `bob_studio.blend` and
`bob_cinematic_test.blend`.
