# BOB — Character Design Spec (canonical)

> This is the single source of truth for what Bob is. If anything in code, renders or other
> docs disagrees with this file, this file wins. Update this file first, then the code.
>
> Visual reference: `design/bob_model_sheet.png` (turnaround, expressions, palette).

## 1. Identity in one paragraph

Bob is a **deadpan court clerk** in *the Kingdom of Lumen*, a storybook land where real, weird
history keeps happening to him. He is a **flat, hand-drawn-looking character placed inside a
glowing 3D world (2.5D)**:
- a big off-white disc head with a thick charcoal outline;
- a charcoal stroke face, with deadpan dash eyes by default;
- a navy-black hair crescent and a striped domed topknot with a gold band;
- a royal-blue robe with a gold crossed collar, a yellow sash and a gold hem;
- ink-line arms and legs with tiny ink hands.

He rarely talks back; his **eyes and brows** do the acting.

## 2. Silhouette and proportions

Units are Blender units. HW = head width (1.29).

| Part | Spec |
|---|---|
| Total height | ≈ 3.15 (ground to top of topknot). The head is ≈ 40% of the height. |
| Head | Near-perfect disc, 1.29 wide × 1.24 tall, depth 0.80 (flattened). Centre at z = 2.32. No ears, no neck, no nose. |
| Hair | Navy-black crescent only above the face (hairline at 74% up the front, 50% at the temples, low at the back) |
| Topknot | Domed cover ≈ 0.47 wide × 0.33 tall on top of the head, thin light vertical stripes, gold band at the base |
| Torso | Column ≈ 0.78 wide (0.6 HW), z 1.08 – 1.78 |
| Sash | Yellow band, z 1.00 – 1.17, small knot and two tails at the front-left |
| Skirt | Slightly wider column (0.84 → 0.93 wide) down to z 0.30, gold hem band |
| Arms | Single ink lines (radius 0.03) from the torso edge. Shoulder (±0.33, 1.555), elbow (±0.49, 1.29), wrist (±0.60, 1.035). |
| Hands | Tiny ink hands (palm + 3 fingers + thumb), shape keys Relax, Fist, Point |
| Legs and feet | Ink lines visible below the hem, small dark rounded shoes |

## 3. Palette (sRGB, measured from the reference frames)

| Token | Hex | Use |
|---|---|---|
| skin | `#F6F7F0` | face and head (never pure white) |
| skin_shade | `#E7E4DE` | soft painted edge shade |
| ink | `#2A2324` | all outlines, arms, legs, hands |
| stroke | `#3A3436` | eyes, brows (feature strokes) |
| mouth | `#3A2D2F` | mouth fill |
| hair | `#1E203C` | hair, topknot |
| hair_stripe | `#8C8A96` | topknot stripes |
| robe | `#264080` | torso (rim highlight `#4E6493`, shade `#1D2856`) |
| skirt | `#22397A` | skirt (shade `#1E3265`) |
| sash | `#DCA54B` | sash (shade `#B9852F`) |
| trim / gold | `#EDBD4D` / `#F2C252` | collar, hem, topknot band |
| tear / sweat | `#8CCCFF` | symbols |

The colour constants in code are `scripts/bob_common.py → C`.

## 4. Rendering rules

- **Unlit painted fills:** the character's colours never change with set lighting, except for the
  optional *hue* tint via `scene["bob_scene_tint"]` (0 = exact palette, 0.5–0.7 in cinematic
  scenes).
- **Outline:** thick charcoal inverted hull, about 3% of head width, with a slight hand-drawn
  thickness wobble.
- **Engine:** EEVEE, **Standard** view transform (so the hex values render exactly). For story
  shots, apply the glassy grade (`scripts/glassy_grade.py`): moods `day`, `sunset`, `night`,
  `palace`.
- **Framing:** vertical 9:16 (1080×1920) for Shorts. Background in shallow depth of field, Bob
  sharp.

## 5. Face vocabulary (all driven from the `CTRL_face` bone)

| Look | Controls | Use |
|---|---|---|
| Deadpan dash (default) | all at 0 | neutral, bored, unimpressed |
| Round eyes + dot pupil | `lids_wide` | surprise, shock, fear |
| Half-lid "D" eyes | `lids_sleepy` | smug, skeptical, thinking |
| Happy ^ arcs | `lids_happy` | joy, laughing |
| Slanted dashes | `lids_angry`, `lids_sad` | anger, sadness |
| Closed line | `blink_L/R` | blink, crying |
| Brows | `brow_*_up / _tilt / _arch`, `brow_squeeze` | the main emotion carrier |
| Mouth | default small "o" dot; `mouth_smile/frown/open/wide/narrow/smirk/grin/cry`; visemes `vis_A/E/O/U/MBP/FV` | talking, reactions |
| Extras | `sweat`, `tears`, `blush` | comedy beats |

There are 12 preset expressions (`scripts/build_expressions.py`): Neutral, Happy, Laughing,
Surprised, Confused, Angry, Sad, Scared, Bored, Thinking, Smirking, Crying. In Blender they are
buttons in the 3D View sidebar (N → **Bob**).

## 6. Body rig

- **Armature:** `BOB_Rig`, with FK arms plus IK arms (switch with `arm_ik_L/R`) and IK legs.
- **Controls:** `hand_ik.*`, `elbow_pole.*`, `foot_ik.*`, `knee_pole.*`, `root`, and `head` for
  nod, turn and tilt.
- **Details:** `documentation/rig_documentation.md`.

## 7. Do / Don't

**Do**
- Keep the face minimal; let the brows and eye shape act.
- Hold poses, then snap to the next one.
- Keep one warm and one cool light in every set.

**Don't**
- Add a nose, ears, eyelashes, a 3D glossy eyeball or realistic shading.
- Use pure white or pure black.
- Give Bob the reference character's **yellow hairpin with a green bead** or **white crossed
  collar**. Those belong to someone else's character. Bob's own identifiers are the **gold collar,
  gold hem and gold topknot band**.
- Change the palette without updating section 3.

## 8. Where everything is

| Path | What |
|---|---|
| `blender/bob_character.blend` | Bob + rig + expression panel (link this into shot files) |
| `blender/bob_studio.blend` | Bob in the neutral studio (3-point light) |
| `blender/bob_cinematic_test.blend` | Bob in the interior set with the glassy palace grade |
| `scripts/build_all.py` | Rebuilds the character from scratch (`blender -b --python scripts/build_all.py`) |
| `scripts/render_tests.py` | Turnaround, expressions, turntable, cinematic moods |
| `scripts/glassy_grade.py` | Compositor look + lighting moods |
| `design/` | Model sheet, turnaround, expression sheet, palette |
| `documentation/story_bible_and_workflow.md` | The Bob world, episode formula, Shorts workflow |
| `documentation/style_extraction_2_5d.md` | Measurements taken from the reference frames |
| `documentation/glassy_look.md` | How the glassy colour grade works |
| `reference/` | Client reference frames |
