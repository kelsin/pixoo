# RA Top Systems Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third RetroAchievements page, "TOP SYSTEMS": a 2x2 grid of the 4 consoles with the most games among your last 100 played.

**Architecture:** `ra.parse_summary` computes `Profile.systems` from the `RecentlyPlayed` and `Awarded` data that `API_GetUserSummary` already returns (we just ask for `g=100`). `render.systems_frame` draws the grid. Both CLIs insert the page after `recent_frame`.

**Tech Stack:** Python 3, pillow, requests, stdlib `unittest` run via `uv run pytest`.

**Spec:** `docs/superpowers/specs/2026-11-18-ra-top-systems-design.md`

## Global Constraints

- 64x64 RGB `PIL.Image`; use `Image.NEAREST` for any pixel-art resize; text only through `retro_pixoo/font.py`.
- Reuse existing helpers in `render.py` (`_header`, `_icon`, colors `WHITE`, `GREY`, `GOLD`, `BG`) rather than adding new ones.
- Conventional Commits; no AI attribution in commit messages.
- No new dependencies.

## Review Focus

- `RecentlyPlayed` game with no entry in `Awarded` → counts as a game with 0 achievements, no crash.
- `RecentlyPlayed` empty or missing → `systems == []`, page shows "NO GAMES".
- Console not in the tag table (e.g. "Arcade", "Atari Jaguar") → first 4 letters upper-cased on grey.
- Game count ≥ 100 → drawn at 1x so it stays inside its 32px cell.
- Achievement count ≥ 1000 (e.g. 1234) → must not overrun into the next cell; shown as `12K`-style so it fits the 13px right of the tag.

---

### Task 1: Compute top systems in `ra.py`

**Files:**
- Modify: `retro_pixoo/ra.py`
- Modify: `retro_pixoo/sample_summary.json`
- Test: `tests/test_ra_systems.py` (new)

**Interfaces:**
- Produces:
  - `@dataclass class SystemStat: console: str; games: int; achievements: int; icon_url: str`
  - `Profile.systems: list[SystemStat] = field(default_factory=list)` (add after `recent`)
  - `top_systems(played: list[dict], awarded: dict, limit: int = 4) -> list[SystemStat]` (module-level, called by `parse_summary`)
  - `RAClient.profile()` calls `user_summary(user, games=100, achievements=achievements)`

- [ ] **Step 1: Write failing tests** in `tests/test_ra_systems.py` (unittest style, like `tests/test_update.py`). Helper builds `RecentlyPlayed` dicts `{"GameID": str, "ConsoleName": ..., "ImageIcon": "/Images/<id>.png", "LastPlayed": ...}` listed newest first.
  - `test_ranks_by_game_count`: 3 SNES, 2 GBA, 1 N64 → consoles `["SNES/Super Famicom", "Game Boy Advance", "Nintendo 64"]`, games `[3, 2, 1]`.
  - `test_tie_goes_to_most_recent`: played order GBA, SNES, SNES, GBA → `["Game Boy Advance", "SNES/Super Famicom"]`.
  - `test_limit_four`: 6 consoles → `len == 4`.
  - `test_icon_is_latest_game`: SNES games 10 then 11 (10 is newer) → `icon_url == MEDIA_BASE + "/Images/10.png"`.
  - `test_achievement_sum_hardcore_else_softcore`: game A awarded `{"NumAchievedHardcore": 5, "NumAchieved": 7}`, game B `{"NumAchievedHardcore": 0, "NumAchieved": 3}`, same console → `achievements == 8`.
  - `test_missing_awarded_counts_zero`: game with no `Awarded` entry → `games == 1, achievements == 0`.
  - `test_empty`: `top_systems([], {}) == []`; `parse_summary({}).systems == []`.
  - `test_sample_has_systems`: `load_sample().systems` has 4 entries and `systems[0].games > systems[3].games`.
  - `test_profile_requests_100_games`: patch `RAClient._get` (construct with `api_key="k"`), call `profile("u")`, assert `_get` called with `g=100`.

- [ ] **Step 2: Run** `uv run pytest tests/test_ra_systems.py -v` → FAIL (`ImportError: SystemStat`/`top_systems`).

- [ ] **Step 3: Implement.** Group with a dict preserving first-seen order (that's newest-first, so first-seen game gives `icon_url` and the tie-break), then `sorted(..., key=lambda s: -s.games)` — stable sort keeps recency order on ties. Achievements per game: `_int(NumAchievedHardcore) or _int(NumAchieved)` from `awarded.get(str(gid))`. Wire into `parse_summary` and change `profile()` to `games=100`. 100 is the server-side cap (RAWeb `public/API/API_GetUserSummary.php` clamps `g` to 100); users with fewer games just get fewer entries.

- [ ] **Step 4: Extend `sample_summary.json`.** Keep Super Metroid first. Add ~11 more `RecentlyPlayed` entries (real-looking titles, made-up IDs/icons, descending `LastPlayed`) spanning 5 consoles with counts like SNES 4, GBA 3, PlayStation 3, N64 2, Genesis/Mega Drive 1, plus matching `Awarded` entries (one game left without an `Awarded` entry). Leave `_note` saying it is sample data.

- [ ] **Step 5: Run** `uv run pytest -q` → all pass (existing tests unaffected; profile page still uses `RecentlyPlayed[0]`).

- [ ] **Step 6: Commit** `feat(ra): compute top systems from recently played games`

---

### Task 2: `systems_frame` in `render.py`

**Files:**
- Modify: `retro_pixoo/render.py`
- Test: `tests/test_render_systems.py` (new)

**Interfaces:**
- Consumes: `Profile.systems: list[SystemStat]` from Task 1.
- Produces: `systems_frame(p: Profile, fetcher: ImageFetcher) -> Image.Image`; `system_tag(console: str) -> tuple[str, tuple[int, int, int]]`.

Layout (matches the approved mockup; cell `i` at `x = (i % 2) * 32`, `y = 8 + (i // 2) * 28`):
- `_header(img, "TOP SYSTEMS")`.
- 16x16 icon at `(x+1, y+1)` via `_icon(fetcher, s.icon_url, 16)`.
- Game count, `WHITE`, scale 2, centered in the 14px span starting at `x+18`, at `y+4`. If `font.text_width(n, 2) > 14`, draw at scale 1, centered the same way, at `y+7`.
- Tag: 16x7 rect at `(x+1, y+19)` filled with the tag color, short name in black centered: `x+1 + (16 - text_width)//2 + 1`, `y+20`.
- Achievements, `GOLD`, at `(x+19, y+20)`: `str(n)` if `n < 1000`, else `f"{n // 1000}K"` (3 chars max = 11px, fits the 13px span).

- [ ] **Step 1: Write failing tests** in `tests/test_render_systems.py`:
  - `test_known_tags`: `system_tag("SNES/Super Famicom")[0] == "SNES"`, `"Game Boy Advance" → "GBA"`, `"PlayStation" → "PS1"`, `"Nintendo 64" → "N64"`.
  - `test_unknown_tag_is_grey_first_four`: `system_tag("Atari Jaguar") == ("ATAR", GREY)`.
  - `test_frame_size_sample`: `systems_frame(load_sample(), fetcher).size == (64, 64)`.
  - `test_empty_differs_from_sample`: frame for a `Profile` with `systems=[]` is 64x64 and its bytes differ from the sample frame (it shows "NO GAMES").
  - `test_partial_grid_leaves_cells_blank`: one system → pixels in cell 3 region (`x 32..63, y 36..63`) all `BG`.
  - `test_big_numbers_stay_in_cell`: one system with `games=123, achievements=12345` (drawn as `12K`) → all pixels with `x >= 32` are `BG`.

- [ ] **Step 2: Run** `uv run pytest tests/test_render_systems.py -v` → FAIL (`ImportError`).

- [ ] **Step 3: Implement** `system_tag` with a module-level `_SYSTEM_TAGS: dict[str, tuple[str, RGB]]` keyed by RA `ConsoleName`. Cover at least: NES/Famicom, SNES/Super Famicom, Nintendo 64, GameCube, Game Boy, Game Boy Color, Game Boy Advance, Nintendo DS, Genesis/Mega Drive, Master System, Saturn, Dreamcast, Game Gear, PlayStation, PlayStation 2, PlayStation Portable, PC Engine/TurboGrafx-16, Atari 2600, Arcade. Tags ≤ 4 chars; colors are the builder's call but must be bright enough for black text. Then `systems_frame` per the layout above; empty → `font.draw_text(img, 2, 28, "NO GAMES", GREY)`. Add `systems_frame` to the module docstring's page list.

- [ ] **Step 4: Run** `uv run pytest -q` → all pass.

- [ ] **Step 5: Commit** `feat(render): add top systems page`

---

### Task 3: Wire page 3 into both commands

**Files:**
- Modify: `retro_pixoo/render.py` (`frames()`), `retro_pixoo/update.py` (`collect_pages`), `README.md`
- Test: `tests/test_update.py`

**Interfaces:**
- Consumes: `systems_frame` from Task 2.

- [ ] **Step 1: Update tests** in `tests/test_update.py`: `test_both_sources_order` expects 5 pages with `systems_frame(p, ...)` third; `test_ra_failure_keeps_letterboxd` unchanged (2); `test_main_sample_preview` asserts `page5_led.png` exists. Add `test_frames_has_three_ra_pages`: `len(render.frames(load_sample(), fetcher)) == 3`.

- [ ] **Step 2: Run** `uv run pytest tests/test_update.py -v` → FAIL.

- [ ] **Step 3: Implement**: append `systems_frame` after `recent_frame` in `frames()` and in `collect_pages`.

- [ ] **Step 4: README**: commands table lists the top systems page for both commands; "sent 4 pages" → "sent 5 pages".

- [ ] **Step 5: Verify** `uv run pytest -q` → all pass; `uv run retro-pixoo-update --sample --preview preview` writes `page3_led.png` showing the grid (inspect it).

- [ ] **Step 6: Commit** `feat: show top systems as the third RA page`
