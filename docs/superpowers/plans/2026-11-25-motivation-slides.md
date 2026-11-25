# Motivation Slides Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three pixel-art motivation slides (voice, scroll, breathe) that show after each data segment of the rotation.

**Architecture:** A new `retro_pixoo/motivation.py` draws three static 64x64 frames with `ImageDraw` and the bitmap font. `update.collect_pages` appends the next slide after each segment (RA, Letterboxd, BGG) that rendered.

**Tech Stack:** Python 3, Pillow, unittest run via `uv run pytest`.

**Spec:** `docs/superpowers/specs/2026-11-25-motivation-slides-design.md`

**Reference art:** the approved mockups are drawn by `voice_a`, `scroll_a`, `breathe_a` in
`/private/tmp/claude-501/-Users-kelsin-src-pixoo--claude-worktrees-vibrant-mahavira-50b563/8bdfc91e-b89a-41c7-a5e4-4a6f55aa27cc/scratchpad/mockups.py`
(rendered in `motivation_mockups.png` next to it). Port that drawing code; it is the approved look.

## Global Constraints

- Frames are 64x64 `RGB`, black background, no header bar.
- Text uses `retro_pixoo/font.py` at scale 1, centred horizontally, first line at y=44, second at y=52.
- Colours come from `retro_pixoo/render.py` (`WHITE`, `GOLD`, `RED`, `CYAN`, `GREY`, `DIM`, `LB_GREEN`, `BG`); the two heart pinks are new module constants `PINK = (120, 30, 50)` and `SOFT = (255, 150, 170)`.
- Exact copy: voice "NEVER RAISE" (WHITE) / "YOUR VOICE" (GOLD); scroll "PUT IT DOWN" (WHITE) / "LOOK UP" (GOLD); breathe "BREATHE" (WHITE) / "FIRST" (RED).
- Slide order is fixed: voice, scroll, breathe. Only `Image.NEAREST` for any resize (none expected).
- Commits use Conventional Commits and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- Only Letterboxd renders (RA fails, no BGG): rotation is LB x4 then the voice slide, not the scroll slide — pinned in Task 2.
- No source renders: `collect_pages` returns `[]` with no slides (main must still not send) — pinned in Task 2.
- BGG token set but BGG fetch fails: BGG gets no slide, so breathe is absent — pinned in Task 2.
- The voice art must not leave the 1A mockup's empty strip above the text: art's lowest lit row is within 6 px of y=44 — pinned in Task 1.
- Text fits on the panel: every slide's lines are within x 0..63 (11 chars max = 43 px, fine) — covered by the non-blank/size test; no extra test.

---

### Task 1: Slide frames

**Files:**
- Create: `retro_pixoo/motivation.py`
- Test: `tests/test_motivation.py`

**Interfaces:**
- Produces: `voice_frame() -> Image.Image`, `scroll_frame() -> Image.Image`, `breathe_frame() -> Image.Image`, and `SLIDES: tuple[Callable[[], Image.Image], ...] = (voice_frame, scroll_frame, breathe_frame)`.

- [ ] **Step 1: Write the failing tests** in `tests/test_motivation.py` (unittest style like `tests/test_render_bgg.py`):

```python
from retro_pixoo.motivation import SLIDES, breathe_frame, scroll_frame, voice_frame
from retro_pixoo.render import BG, GOLD, RED

def test_slides_order(self):
    self.assertEqual(SLIDES, (voice_frame, scroll_frame, breathe_frame))

def test_size_mode_and_not_blank(self):
    for f in SLIDES:
        img = f()
        self.assertEqual((img.size, img.mode), ((64, 64), "RGB"))
        self.assertGreater(len(img.getcolors(4096)), 2)

def test_slides_differ(self):
    self.assertEqual(len({f().tobytes() for f in SLIDES}), 3)

def test_text_rows(self):
    # second text line colour appears in rows 52..56
    for f, color in ((voice_frame, GOLD), (scroll_frame, GOLD), (breathe_frame, RED)):
        img = f()
        self.assertTrue(any(img.getpixel((x, y)) == color for x in range(64) for y in range(52, 57)))

def test_voice_art_sits_close_to_text(self):
    img = voice_frame()
    lowest = max(y for y in range(44) for x in range(64) if img.getpixel((x, y)) != BG)
    self.assertGreaterEqual(lowest, 38)
```

- [ ] **Step 2: Run** `uv run pytest tests/test_motivation.py -v` — expect FAIL (`ModuleNotFoundError: retro_pixoo.motivation`).

- [ ] **Step 3: Implement `retro_pixoo/motivation.py`**, porting `voice_a`, `scroll_a`, `breathe_a` (plus `HEART`, `bitmap`, `centred`, `_phone`) from the reference mockup script. Change only the voice art: shift the speaker/wave/meter down so the lowest lit row is between y=38 and y=42 (the meter bottom is at 33 in the mockup; move the whole group down ~6 px). Private helpers get a leading underscore.

- [ ] **Step 4: Run** `uv run pytest tests/test_motivation.py -v` — expect all PASS.

- [ ] **Step 5: Commit**

```bash
git add retro_pixoo/motivation.py tests/test_motivation.py
git commit -m "feat: add voice, scroll and breathe motivation slides"
```

### Task 2: Slides in the rotation

**Files:**
- Modify: `retro_pixoo/update.py` (`collect_pages`)
- Modify: `tests/test_update.py`
- Modify: `README.md` (Commands table row for `retro-pixoo-update`)

**Interfaces:**
- Consumes: `SLIDES` from `retro_pixoo.motivation`.
- Produces: `collect_pages` unchanged signature; output now has one slide after each rendered segment.

- [ ] **Step 1: Update/add tests in `tests/test_update.py`.**
  - `test_both_sources_order`: expect 10 pages: RA x4, `voice_frame()`, LB x4, `scroll_frame()`.
  - `test_ra_failure_keeps_letterboxd`: expect 5 pages, `pages[4].tobytes() == voice_frame().tobytes()`.
  - New `test_three_sources_order`: with `bgg=load_sample_plays`, expect 15 pages; positions 4, 9, 14 equal `voice_frame()`, `scroll_frame()`, `breathe_frame()`.
  - New `test_bgg_failure_no_breathe`: `bgg=_boom("x")` → 10 pages, no page equals `breathe_frame()`, errors contain `"bgg: x"`.
  - `test_all_fail` stays: `pages == []`.

- [ ] **Step 2: Run** `uv run pytest tests/test_update.py -v` — expect the changed/new tests to FAIL on page counts.

- [ ] **Step 3: Modify `collect_pages`**: keep an iterator over `SLIDES`; after appending each segment's pages (RA block, LB block, BGG block when `plays is not None`), append `next(slides)()`.

- [ ] **Step 4: Update README** Commands row to mention a motivation slide (voice, scroll, breathe) after each source's pages.

- [ ] **Step 5: Run** `uv run pytest` — expect all PASS. Then `uv run retro-pixoo-update --sample --preview preview --send ""` and confirm `preview/page5_led.png`, `page10_led.png`, `page15_led.png` are the three slides.

- [ ] **Step 6: Commit**

```bash
git add retro_pixoo/update.py tests/test_update.py README.md
git commit -m "feat: show a motivation slide after each segment"
```
