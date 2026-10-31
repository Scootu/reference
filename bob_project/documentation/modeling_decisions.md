# Modeling Decisions — Bob

Every piece of Bob is generated procedurally by the scripts in `scripts/`. Rebuilding always gives
exactly the same character, and any proportion can be changed in one place.

| Stage | Script | Objects |
|---|---|---|
| Head | `build_head.py` | `BOB_Head` |
| Face | `build_face.py` | eyes (white, iris + pupil, rim, highlight, upper lid, lower lid), brows, nose, mouth, teeth, tongue, blush, tears, sweat |
| Hair | `build_hair.py` | `BOB_Hair_Cap`, `BOB_Hair_Bun`, `BOB_Hair_Band` |
| Body | `build_body.py` | neck, hands, legs, shoes |
| Clothing | `build_clothing.py` | robe, collar (inner, outer, flap), sleeves, cuffs, sash + knot + tails, hem trim |
| Shared | `bob_common.py` | proportions, skeleton joints, colours, materials, geometry helpers |

## Proportions

- **Height and head size:** Bob is about 3.1 units tall including the topknot. The head is 1.28
  wide (radius 0.62 × 1.03), which makes him about 2.5 head-heights tall. This is close to the
  reference's ~1 : 2.3 head-to-body ratio.
- **No visible neck:** the head sits directly on the collar, as in the reference. A short hidden
  neck tube only fills the gap when the head turns.
- **Torso:** narrow (0.78 wide at the shoulders, about 60% of head width) so the head stays the
  hero. The robe flares to 1.0 wide at the hem.

## Head

- **Topology:** a quad sphere (subdivided cube projected to a sphere, about 10,000 even quads, no poles).
  This shades evenly from every angle, with none of the pinching a UV sphere gets at the top of
  the head.
- **Organic shaping** (`head_surface_dir`):
  - 3% wider than tall.
  - 7% shallower front to back, so it isn't a ball in profile.
  - Fuller cheeks in the lower half, to keep him cute and less geometric.
  - A softened underside.
- **No subdivision modifier:** the head is already dense. Every facial feature is placed by
  **ray-casting onto the exact render surface**, so features never float or sink.

## Eyes (the most important feature)

Each eye is layered geometry, so it reads as 3D from every angle:

1. **Eyeball:** sphere r = 0.14, sunk 68% of its radius into the head. Only a shallow cap shows,
   which avoids the "goggles" look we saw in the first profile render (QC round 3).
2. **Iris and pupil:** spherical caps on the eyeball (31° and 15°), parented to the `eye.*`
   bone. Rotating the bone slides them over the eyeball: real eye direction, independent per eye.
3. **Dark rim:** a torus exactly where the eyeball meets the skin. This is the 3D translation of
   the reference's drawn eye outline.
4. **Highlights:** two emissive caps (large upper-left, small lower-right), parented to the head
   and not the eye, so the catch-light stays consistent while the pupils move.
5. **Upper and lower lids:** skin-coloured hemispheres pivoting on the eyeball centre, with a
   dark lash line on the edge. Blinks, squints, angry and sad slants are bone rotations.
   - **Lid mask:** the lid materials are masked to the eye opening (a cone measured in the
     static eyeball's space). Without it, the lash ring showed outside the eye like a pair of
     glasses (found in the first expression sheet, fixed in QC round 4).

## Brows, nose, mouth

- **Brows:** tapered tubes that follow the face surface, each on its own bone (move, tilt,
  squeeze). Shape keys `Arch` and `Flat` change the curve.
- **Nose:** a tiny embedded ellipsoid. The reference draws no nose, but a 3D head with none looks
  unfinished in profile. This is the minimum that lets the profile read.
- **Mouth:**
  - A surface-conforming strip whose UV-based shader darkens the edges, giving an inset look
    without boolean holes in the head.
  - **15 shape keys:** expressions (smile, frown, open, wide, narrow, smirk L/R, grin, cry) and
    visemes (A, E, O, U, MBP, FV).
  - **Teeth and tongue** are separate objects with *matching* shape keys, generated from the same
    shape functions. They only appear in open shapes and always stay inside the lips.

## Hair

- **Cap:**
  - A parametric shell built in (azimuth, height) space. The hairline is a smooth function: a
    high rounded arc on the forehead, brow level at the temples, low at the nape. This was
    refined twice; the first version read as a helmet and the second as a widow's peak.
  - **Thickness:** 4 mm at the hairline, rising to 4 cm at the crown, so the hair has real volume
    yet a crisp, clean edge. A tucked row under the edge closes it.
- **Comb lines:** UV U runs around the head, so a wave-texture bump draws fine lines converging
  on the topknot. This is the stylised equivalent of the reference's comb strokes. No cones or
  spikes.
- **Topknot:** a pear-shaped bun, set slightly behind the crown so it reads in side and back
  views, with a gold band. The reference's hairpin is deliberately **not** reproduced.

## Body and clothing

- **Robe:**
  - A loft of super-ellipse rings (exponent 2.5, slightly boxy like a stitched garment) along a
    Catmull-Rom profile.
  - Soft pleats are layered into the skirt only (two frequencies), with a turned-up hem in a
    darker lining colour.
- **Trims:** every trim (crossed collar, collar flap, hem band, sash) is generated in the robe's
  own (θ, z) parameter space, so it hugs the garment exactly, pleats included. Solidify +
  subdivision gives real thickness and soft edges.
- **Sleeves:**
  - Tapered tubes along the arm joints, a little fuller at the shoulder and slightly belled at
    the wrist, with a few soft wrinkles around the elbow.
  - Gold cuffs, and a dark lining inside the cuff opening.
- **Hands:**
  - Polygonised metaballs (palm + 3 fingers + thumb + wrist stub), so the fingers blend into the
    palm organically. They were enlarged 1.32× after the first full-body review.
  - Shape keys: `Relax`, `Fist`, `Point`. Each finger curls progressively from the knuckle.
- **Legs and shoes:** thin trouser tubes and rounded shoes with flat soles and a slightly
  upturned toe.

## Materials (Cycles)

| Material | Approach |
|---|---|
| Skin | Off-white Principled with light subsurface. A layer-weight ramp darkens grazing angles slightly, which keeps the graphic outline feel without an inverted hull. |
| Hair | Near-black, roughness 0.42, no coat. Comb-line bump. Reduced from an early version that looked like plastic. |
| Eyes | Glossy white with coat. The iris and pupil have coat for wet highlights. Emissive catch-lights. |
| Cloth | Rich blue (sRGB 0.035 / 0.13 / 0.52), roughness 0.78, sheen 0.6 for a fabric edge, procedural weave + noise bump. |
| Trim | Satin gold-yellow with sheen and a light coat. |
| Band | Metallic gold. |

## QC log (render → inspect → fix)

| Round | Found | Fix |
|---|---|---|
| 1 | Every expression showing at once | New shape keys default to 1.0 in Blender 5.x; added `zero_shape_keys` |
| 1 | Back-view camera behind the cyclorama | Larger cyclorama |
| 1 | Hair read as a helmet, with a thick edge and too low | New hairline, tapered thickness |
| 2 | Hairline came to a pointed peak; hair too glossy | Rounded arc formula, rougher hair |
| 3 | Pastel blue and beige trim; tiny hands; eyes bulged in profile | Deeper colours, hands 1.32×, eyes sunk deeper |
| 4 | Lash line visible outside the eyes ("glasses") | Eye-space lid mask |
| 4 | Brow motion too subtle | Larger brow range |
| 5 | Teacup floating off the hand | Cup placed on the measured palm position and normal |
| 5 | Cinematic shot cramped; floor and wall ended in frame | Reframed, extended the set, added set dressing |
