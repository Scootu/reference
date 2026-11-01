We're making **Episode 1 of a vertical story Short** starring my character **Bob**. Bob already
exists; **do not invent a new character.** His full design lives in another public repo:

- Repo: `scootu/reference`, branch `ccr-1e2c8aff-i83wud`
  (clone: `git clone -b ccr-1e2c8aff-i83wud https://github.com/scootu/reference.git`)
- Read these first, they are the source of truth:
  1. `bob_project/BOB_DESIGN.md`: identity, proportions, exact palette, face vocabulary, do/don't
  2. `bob_project/design/bob_model_sheet.png`: turnaround, 12 expressions, palette swatches
  3. `bob_project/documentation/story_bible_and_workflow.md`: Bob's world, the episode formula
     and the **Episode 1 shot list** (section 3)
  4. `bob_project/documentation/style_extraction_2_5d.md` and `glassy_look.md`: the look of the
     world (glow, haze, tinted shadows, warm/cool light)
  5. `bob_project/documentation/bob_world_style_resources.md`: set and sequence ideas (HD-2D-style
     lighting, a paper-lantern flashback, a game-show ending)

## The look (summary; the files above win if anything differs)

- **2.5D:** Bob is a **flat, hand-drawn-looking character** inside a **glowing, detailed, softly
  out-of-focus 3D-looking world**.
- **Bob:**
  - an off-white `#F6F7F0` disc head (never pure white) with a thick charcoal `#2A2324` outline
    that varies slightly in weight;
  - charcoal `#3A3436` stroke features; no nose, no ears;
  - a navy `#1E203C` hair crescent and a domed topknot with thin light vertical stripes and a
    gold band;
  - a royal-blue robe `#264080` with a gold crossed collar, a yellow sash `#DCA54B` and a gold hem;
  - thin ink-line arms and legs with tiny ink hands.
- **Face acting:**
  - Default eyes are **deadpan dashes**. Use **round ring eyes with a dot pupil** for shock,
    **half-lid "D" eyes** for smug or thinking, **^ arcs** for happy, slanted dashes for angry or
    sad.
  - The brows carry the emotion. The mouth is a tiny "o" dot by default.
  - Extras: sweat drop, tears.
- **Motion:** snap between poses in 2–4 frames, then hold for 8–20 frames; nothing floaty.
- **World lighting:** one warm and one cool light per set, bloom on every light, soft full-frame
  haze, lifted and tinted shadows (never pure black), strong saturation, shallow focus with Bob
  always sharp. Moods: `day`, `palace`, `sunset`, `night`.
- **Originality:** never give Bob a yellow hairpin with a green bead or a white crossed collar.
  Those belong to a reference character; Bob's identifiers are the gold collar, gold hem and gold
  topknot band.

## Episode 1: "The Man Paid to Never Bathe"

- **Format:** 1080×1920 vertical, 30 fps, about 55 s.
- **Shots:** follow the 13-shot table in `story_bible_and_workflow.md` §3 (timing, framing, Bob's
  expression, mood and voice-over line for each shot).
- **Structure:** hook in the first 2 s, then setup → escalation → twist. End on the question
  **"So… would YOU live in a cave for seven years… for a fortune?"** with a "YES or NO? 👇"
  caption, and cut back to shot 1 so the video loops.
- **Facts:** it's the popular account of 18th-century "ornamental hermits" (Painshill Park).
  Accounts vary, so keep the narration's "the story goes…" wording. Don't present uncertain
  details as fact.
- **Cast:** Bob, plus a Guard (a Bob variant: helmet and spear, different robe colour). Use simple
  props: a fake beard, a scroll, gold coins, an hourglass, a tavern sign, a mug.
- **Sets:**
  - the garden with fountains (`day`)
  - the palace wall with the job scroll (`palace`)
  - the cave (`night` / `sunset`)
  - the tavern (`night`, warm lantern)
- **Captions:** 1–3 words at a time, white bold with a thick black outline, low-middle, timed to
  the voice's word timings.
- **Voice:** a calm narrator using an open TTS (e.g. Kokoro) or one I have rights to. Drive the
  captions (and Bob's mouth flaps on stressed syllables) from word timings.
- **Sound:** a light comedic music bed (free or properly licensed), a sound effect on every cut
  or expression change, and 0.3 s of silence before the punchline.

## How to work

1. Read the files above and your own pipeline guide.
2. **Before writing any scene code, send me a storyboard to approve:** one still or sketch per
   shot, with timing and the voice line.
3. Draw Bob in code to match the model sheet exactly (head, outline, topknot, robe, palette, the
   eye shapes). Show me a turnaround and 4 expressions (neutral, round-eyed surprise, smug
   half-lid, happy) next to `bob_model_sheet.png` before animating.
4. Build the shots, render a still of every beat, compare against the spec, fix, then render the
   film.
5. Commit and push as you go, with a README describing the one-command final render.
6. Credit in the video description if you use Lemo-Opuscar style grammar: "Style grammar adapted
   from Lemo-Opuscar by LemoLab (github.com/lemomo-ai/lemo-opuscar), CC BY 4.0."
