You are connected to my PC, which has Blender installed and a graphics card. Build an original, fully rigged and animatable cartoon character named **Bob** in Blender, using Blender's Python API (bpy). Do the work yourself: write the script, run Blender from the command line, render previews, look at them and iterate until Bob looks right.

## Target style ("2D look in a 3D world")
Bob should look like a hand-drawn 2D cartoon placed in a 3D scene, the way short-form explainer shorts look:
- **Thick black outlines** around every shape: head, body, arms, clothes. The lines are clean and uniform, roughly 4–6 px at 1080x1920. Use an inverted-hull outline (a Solidify modifier with flipped normals, a black backface-culled material and an offset of about 0.02–0.03), Grease Pencil Line Art, or both. They must render in EEVEE.
- **Flat colors, almost no shading.** Use an emission or flat-toon look with at most a subtle 2-tone cel shadow. No realistic lighting on the character.
- **Head:** a large, perfectly round, pure white/off-white ball, about 40% of his total height. No ears, no nose.
- **Face:** drawn-on black shapes that sit on the head surface, built as decal meshes driven by shape keys or as Grease Pencil strokes:
  - Default eyes are short, thick horizontal dashes with a slightly heavier top edge, giving a deadpan or unimpressed look.
  - Brows are short, thick dashes above the eyes. One brow is often angled lower for a smug or suspicious look.
  - The mouth is a small filled black shape: a small oval, a flat dash, or a half-open "D".
  - Shocked eyes switch to two outlined white circles with small black pupils.
  - Closed or squinting eyes are flat lines.
- **Emotion symbols** as separate 2D cards parented to the head that pop in and out: a blue **sweat drop**, an anger vein mark, small sparkle lines and a question mark.
- **Body:** simple primitive shapes. The torso is a rounded cylinder. The lower body is a long straight skirt/robe tube. Clothes are flat solid colors with one or two graphic details, such as a sash/belt band or crossed collar lines.
- **Arms:** thin black stick/noodle arms (a bevelled curve with an outline) ending in tiny simple hands with 3–4 short stubby fingers. The hands must be able to point, hold objects and rest.
- **Hair/hat:** one simple, bold silhouette shape with an outline.

## Bob's own design (original, do NOT copy any existing YouTube character)
Make Bob clearly his own character, not a copy of anyone else's:
- He wears a **mustard-yellow tunic** with a **dark green belt band** and a simple white V collar.
- His hair is a **messy dark brown hair tuft**, 5–7 rounded spikes leaning forward.
- His one recurring accessory is a small **red scarf**.
- Put all colors in a CONFIG section at the top of the script so I can change them.

## Rig and controls
Create an empty called `Bob_CONTROLS` whose custom properties (0–1 sliders, with -1..1 for direction controls) drive everything through drivers:
- **Eyes:** `eyes_deadpan` (default), `eyes_shocked` (circle eyes), `eyes_closed`, `eyes_squint`, `blink`, `look_x`, `look_y`
- **Brows:** `brow_smug` (one brow down), `brow_angry`, `brow_worried`, `brow_raise`
- **Mouth:** `mouth_small_o`, `mouth_flat`, `mouth_open_talk`, `mouth_smile`, `mouth_frown`, `mouth_grin`
- **Symbols:** `sweat_drop`, `anger_mark`, `sparkle`
- **Head:** `head_turn`, `head_tilt`, `head_nod`

Use simple driver expressions only (e.g. `var`, `a*(1-b)`, `min(1, a+b)`) so drivers work with Python auto-run disabled.

Add an armature or hook empties for both hands (`Bob_Hand_L` and `Bob_Hand_R`), for the head and for a root, so I can pose and keyframe him easily. Make the hands switchable between "open", "point" and "fist" using shape keys or swappable meshes.

## Demo animation (24 fps, about 12 s)
Animate a short acting test with snappy, cartoony timing: quick holds, overshoot, and squash and stretch on the whole body:
1. Deadpan idle with blinks and a small breathing bob.
2. A smug look with one brow down while he reaches out with one arm and points.
3. Talking: alternate the mouth shapes and add hand gestures.
4. Shocked: circle eyes pop in, a small jump, and a finger raised.
5. Nervous: eyes go flat, a sweat drop appears and slides down, and his arms hang stiff.
6. Back to deadpan, ending with a slow blink.

## Scene
- Use a vertical 1080x1920 camera (Shorts format) framing Bob from the knees up.
- Render with EEVEE, the Standard view transform and the outline visible.
- Use a simple blurred or flat background color for now.

## Process
1. Find my Blender executable and its version. Work in a new folder called `Bob/` in this workspace.
2. Write `Bob/bob_character.py`. It must be runnable both from Blender's Scripting tab and headless via `blender -b --python Bob/bob_character.py`. Re-running it must cleanly rebuild Bob without duplicating objects.
3. Render still previews of each emotion beat with `blender -b ... -f <frame>`. Open the PNGs, look at them critically against the style above (outline thickness, face readability, proportions), and fix problems. Repeat at least 2–3 times.
4. Save `Bob/bob.blend` and render the final animation to `Bob/render/bob_demo.mp4`.
5. Give me a short summary of how to use the controls, plus the preview images.
