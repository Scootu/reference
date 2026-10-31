# Style Analysis — Bob

## Sources

`reference/ref-0002.jpg` was not in the repository when the project started. The analysis uses the
five vertical frames the client supplied (1080x1920 short-form video stills), stored as
`reference/ref-0001.jpg` … `ref-0005.jpg`. One more frame was shown in chat (the "bronze" frame:
a round-eyed surprised expression, arm extended), but it was not available as a file. It is
described here from viewing only.

All five frames show the same character and the same front or near-front angle. **No side, back or
three-quarter view exists in the references.** Every side and back design decision below is
*designed*, not observed, and is marked **[designed]**.

## Important difference between the reference and the brief

The reference character is a **2D-drawn figure composited into a 3D-rendered set**. He has thick
black hand-drawn outlines, flat fills, stick arms drawn as single lines, and a face drawn as
strokes. The brief asks for a **fully 3D, cinematically rendered** character that keeps the
reference's visual identity. So the job is to *translate* the drawn character into volumes:

| Drawn trait in reference | 3D translation used for Bob |
|---|---|
| Thick black outline around the head | Dark rim/edge falloff in the skin shader and a strong silhouette; no inverted hull |
| Single-line stick arms | Thin tube arms in fitted sleeves, with small modeled 4-finger hands |
| Circle eyes, drawn as an outline ring with a dot pupil | Layered 3D eyes: dark rim ring, white eyeball, iris, pupil, highlight |
| Dash eyes (deadpan) | Same 3D eyes with eyelids half-closed (upper and lower lids) |
| Stroke brows | Separate black brow meshes on bones |
| Mouth as a small filled stroke | Small inset mouth with shape keys, teeth and tongue |
| Flat colour fills | Soft PBR materials (subtle subsurface on skin, fabric sheen on cloth) |

## Measurements (taken from ref-0004 / ref-0005, the most frontal frames)

- **Head-to-body ratio:** about **1 : 2.3**. The head (white disc only, hair excluded) is about
  210 px wide in a frame where the visible body runs from the chin (y≈570) to the robe hem
  (y≈930+, cropped). The full figure is about 3 head-heights tall with the hair bun.
- **Head silhouette:** a very slightly wide circle, wider than it is tall (≈1.04 : 1). It is
  fullest just below the eye line, with no jaw, chin, ears or neck taper. There is no visible neck:
  the head sits directly on the collar.
- **Face proportions** (as a fraction of head width, centred):
  - The eyes sit at **≈48% of head height from the top** and are spaced so that the eye centres
    are ≈0.17 head-widths from the centre line.
  - Round "shocked" eyes are ≈0.17 head-widths in diameter (large). Each has a dark rim ring, a
    white fill and a small dark pupil.
  - The brows are short, thick, slightly curved dashes about 0.08 head-heights above the eyes.
    They are angled to sell the emotion: inner ends down for skeptical or angry, both raised for
    surprised.
  - **Nose:** none drawn. Bob gets a tiny, barely-there bump **[designed]** so that profile views
    read.
  - **Mouth:** small, at ≈72% of head height. Its shapes are a dot or small oval (neutral or
    unsure), a flattened "D" (talking), and a flat dash.
- **Hair:** black/near-black, combed **straight back** with fine parallel comb lines. It forms a
  **tight cap** with a hairline across the upper third of the head and a small **topknot** on the
  crown. The hairline is a clean arc, high on the forehead, and comes down at the temples.
- **Body:** a straight, compact torso tube about as wide as the head. The robe falls almost
  straight (a column silhouette) to near the ground. A wide contrasting **sash** sits at the waist.
- **Arms:** extremely thin, flexible "noodle" arms with tiny 3-finger hands. They bend smoothly
  with no visible elbow.
- **Legs:** hidden by the robe; tiny feet are just visible in one frame.

## Clothing silhouette and palette

- **Garment:** a long robe in saturated **royal blue**, a **crossed collar** in pale blue/white,
  and a **yellow-gold waist band**.
- **Bob's original outfit** (per the brief: blue and yellow palette, no unnecessary copying):
  - A blue tunic-robe with **yellow-gold trim** on the collar edge, the hem and the cuffs.
  - A **dark navy sash** instead of a solid yellow one.
  - A slightly **A-line flared hem** instead of a straight column.
  - Fitted sleeves with gold cuffs.
  - **No hairpin.** The reference's hair accessory is omitted; Bob's topknot uses a simple gold
    band.
  - Bob's default eyes are **large and round**, where the reference defaults to dash eyes. This
    makes Bob read as his own character within the shared style.

## Materials and lighting (from the reference environment)

- The set is a polished stylized 3D game look: soft global illumination, warm practical lights
  (torches and braziers) against cool ambient light, gentle bloom, and shallow depth of field on
  backgrounds.
- The character itself is unlit and flat in the reference. For Bob, materials stay **soft and
  low-contrast** so he still feels "graphic":
  - **Skin:** off-white, roughness ≈0.5, light subsurface.
  - **Hair:** near-black, roughness ≈0.35, fine directional bump for comb lines.
  - **Cloth:** rich blue, roughness ≈0.8, sheen, subtle weave.
  - **Trim:** satin gold.
  - **Eyes:** glossy, with emissive catch-lights.

## Expression vocabulary seen in the reference

| Frame | Expression | How it's drawn |
|---|---|---|
| ref-0001 | Skeptical / smug | Brows angled down, eyes half-lidded, small "o" mouth |
| (bronze) | Surprised curiosity | Round eyes, brows raised, small mouth |
| ref-0002 | Bored / unimpressed | Eyes as flat dashes, flat mouth |
| ref-0003 | Unimpressed and nervous | Flat eyes, sweat drop |
| ref-0004 | Shocked | Round outlined eyes, pointing |
| ref-0005 | Determined / skeptical talk | Angled brows, flat eyes, half-open "D" mouth |

**Key takeaway:** the identity lives in the **round white head, the dark hair cap with a topknot,
brow angle and eyelid height**. The mouth stays small. Bob's rig is built around lids, brows and a
small mouth for exactly this reason.

## Side / back views [designed]

- **Head:** a sphere that is slightly shallower front to back (depth ≈0.93 × width) so the profile
  still reads round.
- **Hair:** the cap wraps the back of the skull down to the nape with a clean scalloped edge. The
  comb lines converge into the topknot. The topknot sits slightly **behind** the crown so it reads
  in profile.
- **Robe:** the crossed collar overlaps left over right at the front and continues as a plain band
  around the back of the neck. The back of the robe is plain with soft vertical folds.
