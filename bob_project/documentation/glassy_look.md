# The "Glassy" Cinematic Look

Measured on the 130 frames in `frames.zip`:

- **Black level:** the darkest 1% of pixels averages about 26/255, never true black.
- **Shadow colour:** shadows are tinted violet, blue or brown.
- **Saturation:** mean ≈ 0.41, which is strong.
- **Highlights:** they bloom over their surroundings, and the whole frame carries a soft
  diffusion haze.

None of this comes from the character. It comes from the **set lighting + post grade**.

| Ingredient in the frames | Blender implementation (`scripts/glassy_grade.py`) |
|---|---|
| Highlights glow (sun, windows, gold, torches) | Compositor **Glare → Bloom** (threshold ~0.7) |
| Dreamy full-frame haze | **60 px blur** screened back over the image (diffusion 18–28%) |
| Milky, coloured shadows | **Color Balance → Lift**, tinted per mood |
| Warm or cool highlights | **Color Balance → Gain** |
| Rich colour | **Hue/Saturation** ×1.10 – 1.20 |
| Soft edges, slight lens fringe | **Lens Distortion** dispersion 0.012 + blurred **ellipse vignette** |
| Warm vs cool scene light | `apply_mood()` sets the sun, sky card, lantern, rim and world colours |
| Characters take on the scene hue (blue at night) | `scene["bob_scene_tint"]` drives Bob's flat shader |
| Shallow focus on the background | camera DOF f/2.2 focused on Bob |

## Moods

| Preset | Shadows | Highlights | Use |
|---|---|---|---|
| `day` | soft violet | neutral-warm | exteriors, markets |
| `sunset` | purple-magenta | orange | golden hour, emotional beats |
| `night` | deep blue | cool blue-white, with warm lanterns | moonlit scenes |
| `palace` | plum | warm gold | interiors with torches and gold |

## Use it on your PC

From the command line:
```powershell
blender -b blender/bob_character.blend --python scripts/render_tests.py -- --only cinematic --samples 64
```
This renders `renders/cinematic_tests/10_cinematic_{palace,sunset,night}.png`.

Inside Blender, on any scene, from the Scripting tab:
```python
import sys; sys.path.insert(0, r"E:\reference\bob_project\scripts")
import glassy_grade as gg, bpy
gg.apply_grade(bpy.context.scene, "sunset")   # adds the compositor look
gg.apply_mood("sunset")                       # relights the ENV_Cinematic set + tints Bob
gg.clear_grade(bpy.context.scene)             # back to the exact palette
```

The compositor runs on the GPU, and the Compositor tab in Blender lets you preview and tweak
every node. Supported versions are Blender 4.2+ and 5.x; the script detects which compositor API
is available.

## Tips for building new sets in this style

- Put a bright source **in frame or just behind the subject**, such as a window, the sun, the
  moon or torches. The bloom needs something to glow.
- Use saturated, painted-PBR materials: red banners, gold trims, blue carpets. Use metallic gold
  with low roughness so it catches bloom.
- Keep one warm and one cool light in every shot.
- Add a light World volume (density 0.005–0.02) for depth haze and god-rays through windows.
