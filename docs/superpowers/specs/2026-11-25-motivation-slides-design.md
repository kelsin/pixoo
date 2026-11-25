# Motivation slides

## Intent

Three self-motivation slides that show between the data segments of the hourly rotation, as gentle reminders: never raise your voice, don't doom scroll, breathe first.

## Goals / non-goals

- Goals: each slide pairs a pixel-art graphic with two lines of text, in the same pixel style as the rest of the rotation.
- Non-goals: animation (each page is one still frame held for `--seconds`), configurable text, a flag to turn them off.
- Anti-goal: slides that look like data pages or are hard to read at a glance.

## Approaches

1. **Pixel art drawn in code** (picked): a new `retro_pixoo/motivation.py` with one frame function per slide, drawn with `ImageDraw` primitives and string bitmaps like `_STAR`/`_HEART` in `render.py`, text in `retro_pixoo/font.py`. Consistent with every other page; no asset files.
2. PNG art loaded from disk: more freedom, but needs hand-made assets and wouldn't match the house style.
3. Text only: simplest, but the user asked for graphic + text.

## Design

The approved mockups (all "A" options) are in `motivation_mockups.png`, rendered by the throwaway script that drew them.

| Slide | Art (top ~40 rows) | Text (rows 44 and 52, centred) |
|---|---|---|
| `voice_frame` | Speaker (grey body, white cone), small cyan wave, 5-bar volume meter with only the first bar lit green, rest `DIM` | "NEVER RAISE" white / "YOUR VOICE" gold |
| `scroll_frame` | Grey phone, feed lines and white down arrow on a dim screen, red diagonal slash across it | "PUT IT DOWN" white / "LOOK UP" gold |
| `breathe_frame` | Red heart (13x11 bitmap at 2x) centred inside the same heart at 3x in dark pink, small pink highlight | "BREATHE" white / "FIRST" red |

- No header bar, black background.
- 1A had a gap between the art and the text: move the art down or enlarge it so it sits closer to the text.
- Placement in `update.collect_pages`: after each segment that rendered (RA, Letterboxd, BGG), in that order, append the next slide in `voice, scroll, breathe` order. With all three sources the rotation is RA x4, voice, LB x4, scroll, BGG x4, breathe, then loops. If a source fails, it gets no slide, and the slides that follow shift up (two segments → voice and scroll).
- Same seconds per page as other pages. Previews pick them up automatically.

## Left to the builder

Exact pixel coordinates, and the closer spacing for the voice art. Tests: each frame is 64x64 RGB and non-blank; `collect_pages` puts slides in the expected positions, including when a source fails.
