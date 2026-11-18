# Letterboxd Rotation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two Letterboxd pages and a one-shot `python -m retro_pixoo.update` command that sends RA + Letterboxd pages (30s each) to the Pixoo, intended to run hourly.

**Architecture:** `letterboxd.py` parses the user's RSS feed into `DiaryEntry` objects; `render.py` gains two frame functions; `update.py` fetches both sources independently, interleaves pages, and sends them in one `Pixoo.show()` call.

**Tech Stack:** Python 3.14, Pillow, requests, stdlib `xml.etree`, stdlib `unittest` (pytest is not installed — don't add it).

**Spec:** `docs/superpowers/specs/2026-11-18-letterboxd-rotation-design.md`

## Global Constraints

- No new dependencies (requirements.txt stays `requests`, `pillow`).
- All frames are 64x64 RGB `PIL.Image`; text via `retro_pixoo.font` (3x5 font, 4px advance, `font.fit`/`font.wrap`/`font.draw_text`).
- Reuse colors/helpers in `render.py` (`BG, WHITE, GREY, DIM, GOLD, HEADER`, `_placeholder`, `ImageFetcher`). Header bar style matches `recent_frame` (rows 0-6, `HEADER` fill, gold title at y=1).
- Page order: RA profile → LB last watched → RA recent → LB diary. Default 30 s per page.
- Defaults: `--ra-user kelsin`, `--lb-user kelsin13`, `--endpoint /post`, `--seconds 30`.
- Tests run with: `python3 -m unittest discover -s tests -v` from repo root.
- Bundled fixture `retro_pixoo/sample_feed.xml` already exists (8 diary items, all rated 4.0/5.0, plus 1 list item "Preordered" at position 5). Don't modify it.

## Review Focus

1. Unrated diary entry (no `letterboxd:memberRating`) → rating `None`, renders with no stars, no crash.
2. Half-star ratings (e.g. 3.5, 0.5) → drawn as 3 full + 1 half star.
3. Very long titles (e.g. "Dr. Strangelove or: How I Learned to Stop Worrying...") and non-ASCII (é, ō) → wrapped/fitted, no overflow beyond x=63, no crash (`font.normalize` handles unknown chars).
4. Fewer than 5 diary entries (e.g. 1) → diary page shows what exists or "NO MORE FILMS"; empty list → both LB pages render "NO FILMS".
5. One source raises (RA key missing, network down) → other source's pages still sent, exit code 1.

---

### Task 1: Letterboxd feed parser

**Files:**
- Create: `retro_pixoo/letterboxd.py`
- Create: `tests/__init__.py` (empty), `tests/test_letterboxd.py`

**Interfaces:**
- Produces:
  - `@dataclass DiaryEntry: title: str; year: int | None; rating: float | None; liked: bool; rewatch: bool; watched_date: str; poster_url: str`
  - `parse_feed(xml_text: str) -> list[DiaryEntry]` — feed order (newest first), only `<item>`s containing `letterboxd:filmTitle`.
  - `class LetterboxdClient(timeout: float = 10.0)` with `.diary(user: str) -> list[DiaryEntry]` (GET `https://letterboxd.com/{user}/rss/`, User-Agent `retro-pixoo/0.1`, `raise_for_status`).
  - `load_sample_feed() -> list[DiaryEntry]` reading `retro_pixoo/sample_feed.xml`.

- [ ] **Step 1: Write failing tests** in `tests/test_letterboxd.py`:
  - `test_sample_feed_skips_lists`: `load_sample_feed()` has 8 entries; titles don't include "Preordered".
  - `test_first_entry_fields`: entry 0 == `DiaryEntry("Wildwood", 2026, 5.0, True, False, "2026-11-16", <url starting "https://a.ltrbxd.com/resized/film-poster/7/0/9/4/6/0/709460-wildwood-2026">)` (check poster with `startswith`). Entry 1 ("Minority Report") has `rewatch is True`.
  - `test_unrated_and_half_star`: inline minimal RSS string with the same namespaces as the fixture, two items: one with no `memberRating`, no `memberLike`, no `<img>` → `rating is None, liked is False, poster_url == ""`; one with `memberRating` `3.5` → `rating == 3.5`.
- [ ] **Step 2:** `python3 -m unittest tests.test_letterboxd -v` → FAIL (ImportError).
- [ ] **Step 3: Implement** with `xml.etree.ElementTree`; namespace `letterboxd = "https://letterboxd.com"`. Poster: regex `<img src="([^"]+)"` over the `description` text.
- [ ] **Step 4:** rerun → PASS.
- [ ] **Step 5: Commit** `git add retro_pixoo/letterboxd.py retro_pixoo/sample_feed.xml tests && git commit -m "Add Letterboxd RSS diary parser"`

### Task 2: Letterboxd frames

**Files:**
- Modify: `retro_pixoo/render.py` (add after `recent_frame`; update module docstring page list)
- Create: `tests/test_render_letterboxd.py`

**Interfaces:**
- Consumes: `DiaryEntry`, `load_sample_feed` (Task 1); `ImageFetcher(offline=True)` returns `None` for all URLs.
- Produces:
  - `last_watched_frame(entries: list[DiaryEntry], fetcher: ImageFetcher) -> Image.Image` — uses `entries[0]`.
  - `diary_frame(entries: list[DiaryEntry], fetcher: ImageFetcher, count: int = 4) -> Image.Image` — uses `entries[1:1 + count]`.
  - `_stars(img, x: int, y: int, rating: float | None, color=GOLD) -> int` — returns width drawn; 0 for `None`.

Layout (exact pixels inside these bounds are your call):
- Last watched: header "LAST WATCHED"; poster resized to 28x42 at about (1, 9) (placeholder from `_placeholder(title, ...)` resized to 28x42 when missing — use `fetcher.get` directly, not `_icon`, since posters aren't square); right column x≈32-63: `font.wrap(title, 31, 4)` white, year grey, stars gold, red heart (e.g. `(230, 60, 80)`) if liked, small "RE" marker in grey/cyan if rewatch. Empty list → "NO FILMS" grey.
- Diary: header "RECENT DIARY"; up to 4 posters 15x22 at x = 0,16,32,48 (y≈9); stars below each poster must fit 15 px width for 5 stars → use a tiny star (e.g. 2x2 or 3x3 pixel with no gap issue; half star = left half). If entries[1:] empty → "NO MORE FILMS". Empty list → "NO FILMS".
- Star glyph: design your own pixel star; full stars for `int(rating)`, half star if `rating % 1 >= 0.5`.

- [ ] **Step 1: Write failing tests** in `tests/test_render_letterboxd.py` (offline fetcher):
  - `test_frames_are_64x64` for both functions with `load_sample_feed()`.
  - `test_empty_entries`: both render 64x64 with `[]`.
  - `test_single_entry_diary`: `diary_frame(entries[:1], ...)` renders.
  - `test_unrated_long_title`: a `DiaryEntry("Dr. Strangelove or: How I Learned to Stop Worrying and Love the Bomb Pokémon", None, None, False, True, "2026-01-01", "")` renders in both frames without error.
  - `test_stars_width`: `_stars(img,0,0,None) == 0`; `_stars(img,0,0,3.5) > _stars(img,0,0,3.0) > 0`.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** run → PASS. Also render previews to eyeball: `python3 -c "from retro_pixoo.letterboxd import load_sample_feed; from retro_pixoo.ra import ImageFetcher; from retro_pixoo.render import *; e=load_sample_feed(); f=ImageFetcher(); led_preview(last_watched_frame(e,f)).save('preview/lb1_led.png'); led_preview(diary_frame(e,f)).save('preview/lb2_led.png')"` (real posters via network) and look at the PNGs with the Read tool; fix overlaps/clipping.
- [ ] **Step 5: Commit** `git add retro_pixoo/render.py tests/test_render_letterboxd.py && git commit -m "Add Letterboxd last-watched and diary pages"`

### Task 3: Update command, exports, README

**Files:**
- Create: `retro_pixoo/update.py`
- Modify: `retro_pixoo/__init__.py` (export `DiaryEntry, LetterboxdClient, parse_feed, load_sample_feed, last_watched_frame, diary_frame`)
- Modify: `README.md` (new "Letterboxd + hourly update" section with usage and crontab line)
- Create: `tests/test_update.py`

**Interfaces:**
- Consumes: Tasks 1–2, `RAClient().profile(user)`, `load_sample()`, `profile_frame`, `recent_frame`, `led_preview`, `Pixoo(ip, endpoint).show(frames, ms_per_frame)`.
- Produces:
  - `collect_pages(ra: Callable[[], Profile], lb: Callable[[], list[DiaryEntry]], fetcher: ImageFetcher) -> tuple[list[Image.Image], list[str]]` — calls each loader in its own try/except (exception → message `"retroachievements: <err>"` / `"letterboxd: <err>"` in errors). Both ok → `[profile, last_watched, recent, diary]`; only one ok → that source's two pages; none → `[]`.
  - `main(argv: list[str] | None = None) -> int` — args `--ra-user kelsin --lb-user kelsin13 --sample --preview DIR --send IP --endpoint /post --seconds 30`. Prints each error to stderr. No pages → return 1 without sending. Otherwise preview (same file naming as `__main__`: `page{n}_64.png`, `page{n}_led.png`, `preview.gif`) and/or send, print `sent N pages to IP`; return 1 if any errors else 0. `if __name__ == "__main__": sys.exit(main())`.
  - `--sample` uses `load_sample`, `load_sample_feed`, `ImageFetcher(offline=True)`.

- [ ] **Step 1: Write failing tests** in `tests/test_update.py`:
  - `test_both_sources_order`: with `load_sample`/`load_sample_feed` and offline fetcher → 4 pages, no errors; page 0 pixel-equal (`tobytes()`) to `profile_frame(...)`, page 1 to `last_watched_frame(...)`, page 2 to `recent_frame(...)`, page 3 to `diary_frame(...)`.
  - `test_ra_failure_keeps_letterboxd`: ra loader raises `RuntimeError("no key")` → 2 pages, errors == `["retroachievements: no key"]`.
  - `test_all_fail`: both raise → `([], 2 errors)`.
  - `test_main_sample_preview`: `main(["--sample", "--preview", tmpdir])` returns 0 and writes `preview.gif` and `page4_led.png`.
  - `test_main_no_pages_does_not_send`: patch `retro_pixoo.update.RAClient` and `retro_pixoo.update.LetterboxdClient` to raise, patch `retro_pixoo.update.Pixoo` with a `MagicMock`; `main(["--send","1.2.3.4"]) == 1` and `Pixoo` not called.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Implement**, exports, README (crontab example: `0 * * * * cd /path/to/pixoo && RA_API_KEY=... /path/to/python3 -m retro_pixoo.update --send 192.168.1.50 >> /tmp/pixoo.log 2>&1`; note RA key, explain 30s pages, exit codes).
- [ ] **Step 4:** `python3 -m unittest discover -s tests -v` → all PASS; `python3 -m retro_pixoo.update --sample --preview preview` → exit 0.
- [ ] **Step 5: Commit** `git add retro_pixoo tests README.md && git commit -m "Add hourly update command combining RA and Letterboxd pages"`
