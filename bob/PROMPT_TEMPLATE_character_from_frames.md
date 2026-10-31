# Prompt template: build a Blender character from reference frames

Copy everything below the line. Fill in the `[BRACKETS]`, attach your frames (screenshots or a short video clip), and send it to a Claude session that can run Blender: a session on your PC, or a cloud session.

---

I'm attaching [NUMBER] reference frames / a video clip. Use them as a **style reference** to build a new, original cartoon character in Blender with Python (bpy). Do all the work yourself: write the script, run Blender, render previews, look at them and fix problems.

## Step 1: Analyse the references first
Before writing any code, study the frames and write me a short **style sheet** covering:
- **Line work:** outline thickness, color, and whether inner lines are drawn.
- **Shading:** flat, 2-tone cel, or soft? How much lighting shows on the character?
- **Proportions:** head size versus body, body shape, and arm/leg style (stick, noodle, full).
- **Face:** how the eyes, brows and mouth are drawn, and how each expression changes them.
- **Expressions and symbols:** every emotion you can see (sweat drops, anger marks, sparkles and so on).
- **Hands:** finger count and the poses they use (point, hold, fist).
- **Clothing language:** simple shapes, color blocks and graphic details.
- **Animation feel:** snappy or smooth, squash and stretch, holds, how much the head moves.

Then list the elements that make the reference character **specifically recognisable**, such as his exact hairstyle, outfit, accessories and colors. My character must NOT reuse these together. Keep the style, but change the identity.

## Step 2: My character
- **Name:** [NAME]
- **Personality:** [e.g. lazy but clever, nervous, overconfident]
- **Outfit:** [e.g. mustard tunic with green belt; or "you design it"]
- **Hair/headwear:** [e.g. messy brown tuft; or "you design it"]
- **Signature accessory:** [e.g. red scarf, glasses, backpack; or "none"]
- **Colors:** [palette, or "pick a palette that fits the style"]
- **Anything to keep from the reference style:** [e.g. thick outlines, deadpan dash eyes, round shocked eyes]
- **Anything to avoid:** [e.g. no realistic shading, no ears or nose]

## Step 3: Build it
- Write one script, `[NAME]/[name]_character.py`. Put every color and size in a CONFIG section at the top.
- The script must work from the Scripting tab and headless (`blender -b --python ...`), and re-running it must rebuild the character cleanly with no duplicates.
- **Outlines:** use an inverted hull (Solidify with flipped normals and a backface-culled black material) and/or Line Art. They must render in EEVEE.
- **Face:** drawn-on shapes on the head, built as decal meshes with shape keys or as Grease Pencil, so expressions morph smoothly.
- **Controls:** add an empty called `[NAME]_CONTROLS` with custom-property sliders that drive every expression through drivers (simple expressions only, so they work with Python auto-run disabled):
  - Eyes: default, shocked, closed, squint, blink, look_x, look_y
  - Brows: smug, angry, worried, raise
  - Mouth: small_o, flat, talk, smile, frown, grin
  - Symbols: [list, e.g. sweat_drop, anger_mark, sparkle, question]
  - Head: turn, tilt, nod
  - Hands: point and fist, for each hand
- **Posing:** add hand controllers (hooks or bones) and a root, so I can pose and keyframe easily.
- **Demo animation:** [LENGTH, e.g. 12 s at 24 fps] showing [LIST OF BEATS, e.g. idle → smug point → talking → shocked jump → nervous sweat → idle]. Use snappy timing, overshoot and squash and stretch.
- **Camera:** [1080x1920 vertical Shorts / 1920x1080 landscape], framing [knees up / full body / close-up]. Use the Standard view transform and a [flat color / blurred] background.

## Step 4: Iterate
1. Render a still of each beat. Put each one side by side with the reference frames and list what differs in **style**: line weight, flatness, proportions, how readable the face is, and timing.
2. Fix it and re-render. Do at least 3 rounds.
3. Save the `.blend` file, render the animation to `[NAME]/render/[name]_demo.mp4`, and send me the preview images plus a short guide to the controls.
