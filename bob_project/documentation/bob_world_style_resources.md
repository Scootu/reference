# Bob World — Style Resources from Lemo-Opuscar

**Source:** [github.com/lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) by
LemoLab / Lemomo.

- It is a library of **66 film styles made in code** (HTML canvas/WebGL, TTS voice, generated
  music). Each style has a `STYLE.md` prompt (look, colour, type, motion, camera grammar) and a demo
  film.
- **Licence:** code MIT; demo films and stills CC BY 4.0. You may adapt them commercially if you
  credit **LemoLab** with a link to the repo and say what you changed. Three demo voice tracks are
  excluded from that licence; don't reuse any of their audio.
- Their own rule applies to us too: borrow the **grammar** of a style, never its characters, places,
  logos or music.

Bob's base look stays **2.5D**: a flat drawn character inside a glowing 3D Blender set (see
`BOB_DESIGN.md`). The styles below are what fits *around* Bob, as set designs, special sequences and
episode formats.

## 1. Closest match to Bob's look

| Opuscar style | Why it fits | What to take for Bob |
|---|---|---|
| **`hd-2d`** (2D sprites in a lit, fogged 3D diorama) | The same idea as Bob: flat characters standing in real 3D light. | **Two-temperature lighting** (cold ambient against warm practical lamps); **a glow sprite on every light** so bloom has something to grab; **"lights breathe"** (flames flicker ±20 % from summed sines); the darkest value is a warm ink, never black; **the hero wears the one saturated colour no set uses** (Bob's blue + gold); a high ¾ camera with focus recomputed each frame. Optional: a framed **dialogue box** for characters who speak on screen. |
| **`tilt-shift`** (the real world shot as a tabletop model) | Establishing shots of the Kingdom of Lumen. | A high oblique **establishing shot** with a narrow focus band and saturated "model-railway" colour; time-lapse crowds; **cheat the sun direction per shot** so the façades are always front-lit. |
| **`lowpoly-island`** / **`memphis-diorama`** | Cute "whole world" map shots. | A floating island or diorama of the kingdom for "where are we" openers. |

## 2. Special sequences inside an episode

Switch style for a few seconds when the story changes mode, then cut back to Bob.

| Story moment | Opuscar style | How |
|---|---|---|
| **Legend, flashback or "long ago…"** | `paper-lantern` (layered paper-cut lightbox), `papercut-red`, `shadow-puppet` | A backlit layered paper stack: back layers bright and cool, front layers dark, warm light through holes. Bob appears as a jointed silhouette. Ideal for night or legend moods. |
| **Palace history, kings, religion** | `stained-glass` | A stained-glass panel that lights up to tell the backstory. |
| **The fact or "rule" explainer** | `isometric-picture-book`, `iso-infographic` | A clean isometric cutaway where tiny figures act out the rule and **one key word lies on the floor**. Great for "the rules were: no talking, no haircuts…". |
| **Numbers and money** | `data-physical`, `caption-news` | Stack coins or bars physically; big number captions. |
| **The ending question** | `game-show` | A quiz-show sting for **"YES or NO? Comment below"**, perfect for the comment-bait ending. |
| **Old documents and evidence** | `archive-lighttable`, `engraving` | The source scroll or letter on a light table, for credibility beats. |
| **Kids' or storybook episodes** | `crayon-book`, `watercolor`, `ukiyoe` | A whole-episode alternate look for special series. |

## 3. Workflow ideas to adopt (from `DIRECTOR.md` / `TECHNIQUE.md`)

1. **Find a benchmark first.** Before writing, pick 1–2 reference shorts and note their pace and
   hook.
2. **The music grid comes first.** Choose the track, mark its beats, then cut shots and expression
   changes on the beat.
3. **One timeline drives everything.** Keep a single timing sheet (voice line → shot →
   expression → caption); captions and cuts are generated from it, never retimed by hand.
4. **Voice:**
   - Kokoro TTS (open, offline) or ElevenLabs for the narrator.
   - If you record yourself, run **faster-whisper** to get word timings and drive the
     word-by-word captions and the `vis_*` visemes from them.
5. **Sound is half the film.** A sound effect on every cut, a short silence before the punchline,
   and the music ducked under the voice.
6. **Every camera move needs a reason** (their camera grammar tables are a good checklist).
7. **Review loop.** Render stills of every beat, check them against the spec, fix, then render
   the film.

## 4. Quick start: pulling a style into a Bob episode

```text
1. Read styles/<name>/STYLE.md in lemo-opuscar (look, colour, motion, camera sections).
2. Keep Bob in his 2.5D design; build the set or insert sequence in Blender following the
   style's colour logic and lighting.
3. Credit in the video description:
   "Style grammar adapted from Lemo-Opuscar by LemoLab (github.com/lemomo-ai/lemo-opuscar), CC BY 4.0."
```

## 5. Recommended set list for the Kingdom of Lumen

| Set | Mood (`glassy_grade`) | Style grammar |
|---|---|---|
| Throne hall | `palace` | hd-2d lighting: gold practicals, cool stone ambient, braziers that breathe |
| Castle town and market | `day` | tilt-shift establishing shot, then ground-level shots |
| Rooftops at night | `night` | hd-2d: blue fog, amber windows |
| The hermit's cave | `night` / `sunset` | a single warm practical, dust in the light shafts |
| The legend scroll | — | a paper-lantern flashback |
| Ending quiz | — | game-show sting |
