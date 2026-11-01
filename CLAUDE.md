# Repository guide for Claude sessions

## Bob (the main project)

This repo contains **Bob**, an original 2.5D cartoon character for vertical story Shorts, built
procedurally in Blender (Python, Blender 5.1+). **Do not redesign or rebuild Bob from scratch.**
Everything already exists:

- **Who Bob is (canonical spec):** `bob_project/BOB_DESIGN.md`. Read this first.
- **What he looks like:** `bob_project/design/bob_model_sheet.png`
- **Story world and Shorts workflow:** `bob_project/documentation/story_bible_and_workflow.md`
- **Ready-to-use files:** `bob_project/blender/*.blend`
- **Source of truth for the geometry:** `bob_project/scripts/` (rebuild with
  `blender -b --python scripts/build_all.py` from `bob_project/`)

### Key facts

- **Look:** flat, hand-drawn character (off-white `#F6F7F0` disc head, thick charcoal outline,
  charcoal stroke face) inside a glowing 3D world.
- **Outfit:** royal-blue robe `#264080`, gold crossed collar, yellow sash `#DCA54B`, gold hem.
- **Hair:** navy crescent, striped domed topknot with a gold band.
- **Face:** deadpan dash eyes by default. All expressions are driven from the `CTRL_face` bone
  (12 presets in `build_expressions.py`).
- **Rendering:** EEVEE, Standard view transform. Optional glassy grade and moods in
  `glassy_grade.py`. `scene["bob_scene_tint"]` tints Bob to the set's light hue.
- **Originality:** Bob is original. Never add the reference character's yellow hairpin with a
  green bead or white crossed collar.

### Working conventions

- Change the design in `BOB_DESIGN.md` **and** the scripts together. Rebuild and re-render the
  model sheet (`design/`) after visual changes.
- Generated `.blend` files are rebuilt by the scripts; `*.blend1`, `__pycache__/` and
  `renders/wip/` are ignored.
- The user renders on their own Windows PC (Blender at `E:\programs\blender\blender.exe`, repo
  at `E:\reference`).

## Legacy

`bob/` holds early prototypes (a first 3D Bob and an outline-style test). It is kept for history
only; `bob_project/` is the current character.
