# Style Extraction — "2D character in a 3D world" (2.5D)

Measured from the client frames `reference/ref-0001…0005` (540×960 stills). Colours are medians and
palette clusters sampled from the frames. Sizes are relative to **head width (HW)**.

## 1. Rendering model

- **Character:** unlit and flat, like a drawing composited over a 3D scene. Lighting in the set
  does **not** change the character's colours. The only "lighting" is a soft painted gradient.
- **Background:** a fully lit, painterly 3D set (warm torches against cool stone), pushed out of
  focus with strong depth of field. The character stays sharp.
- **Outline:** every shape has a thick **dark warm charcoal** contour, about **3% of HW** (6 px at
  540 px width; 12 px at 1080). The edge is slightly soft and anti-aliased, and its weight is
  constant around shapes.
- **Facial strokes** are drawn in the same charcoal, not pure black: **#3A3436**, measured
  #3b3536 – #5d5553 on anti-aliased edges.

## 2. Palette (sRGB)

| Element | Lit | Shade | Notes |
|---|---|---|---|
| Face / skin | **#F6F7F0** (measured #F8FAF3, #F4F8F2, #F7FBFA) | #E2DCCD (warm), #F1E9F4 (faint cool) | Not pure white; very slightly warm/green-cream. Shading is barely visible, just a soft darkening near the bottom and outer edge |
| Outline / ink | **#2A2324** | — | warm near-black |
| Feature strokes | **#3A3436** | — | eyes, brows, mouth |
| Robe blue | **#264080** | #1D2856 | lighter rim band on the lit side: **#4E6493** |
| Skirt blue | #22397A | #1E3265 | slightly darker than the torso |
| Sash / band | **#DCA54B** | #B9852F | yellow-orange, with outline |
| Collar strips | **#F4F8DF** | — | cream white, thin blue outline |
| Hair / topknot | **#1E203C** | — | navy-black, with thin grey-white vertical stripes **#8C8A96** |

## 3. Proportions (frontal, frame ref-0005)

- **Head:** a near-perfect circle, ≈1.05 : 1 width to height. No ears, no neck. The head
  overlaps the top of the torso.
- **Torso tube:** about 0.69 HW wide and 0.8 HW tall. Rounded-rectangle silhouette (a column with
  soft corners).
- **Sash:** about 0.14 HW tall, at the bottom of the torso tube.
- **Skirt tube:** about 0.82 HW wide, a straight column falling to the feet. It's a separate
  outlined shape, slightly wider than the torso.
- **Arms:** single ink lines, about 0.03 HW thick, starting at the torso edge.
- **Hands:** tiny (≈0.12 HW), 3 short finger strokes.
- **Feet:** tiny, mostly hidden.

## 4. Face language

| Feature | Variants seen | Size |
|---|---|---|
| **Eyes, dash (default)** | thick horizontal rounded dashes | 0.14 HW long × 0.035 HW thick; centres ±0.11 HW from the centre line, at ~52% of head height |
| **Eyes, round (surprise)** | charcoal ring (thickness ≈0.025 HW) with white inside and a small charcoal dot pupil | ring Ø ≈0.20 HW; pupil Ø ≈0.06 HW |
| **Eyes, half-lid (smug / skeptical)** | flat top line with a half-disc pupil hanging below it | 0.15 HW wide |
| **Brows** | short thick strokes with a slight curve, tapered ends, angled for emotion (inner end down = skeptical or angry) | 0.15 HW long, ≈0.10 HW above the eyes |
| **Mouth** | small "o" dot, flat dash, or "D" half-oval (flat top) when talking | 0.06 – 0.2 HW wide, ~70% of head height |
| **Extras** | blue sweat drop, motion lines | — |

There is no nose, no blush and no eyelashes. The expression comes entirely from **eye shape +
brow angle + small mouth**.

## 5. Hair

- A dark cap shows only as a crescent along the top edge of the head, behind the outline.
- A **domed topknot cover** with vertical light stripes sits on top.
- The reference has a long yellow hairpin with a green bead. **This is part of that character's
  identity and is NOT used for Bob.** Bob's topknot uses a gold band instead.

## 6. Applying this to Bob (keeping him original)

| Kept from the style | Bob's own identity |
|---|---|
| Flat unlit fills with a soft painted gradient | Gold-trimmed crossed collar (the reference uses cream strips) |
| Thick charcoal outlines | Gold hem band |
| Off-white disc face, charcoal strokes | Gold band on the topknot, no hairpin |
| Dash / round / half-lid eye vocabulary | Small dark shoes visible under the hem |
| Blue column robe + yellow sash | Robe has a soft A-line flare |
| Ink-line arms with tiny hands | |
