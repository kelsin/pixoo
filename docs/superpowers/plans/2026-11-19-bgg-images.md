# BGG Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add game thumbnails to the four BGG pages with a single up-front fetch.

**Architecture:** Selection helpers decide which games each page draws; `needed_games` unions them; one `thing` call resolves thumbnail URLs; frames paste cached, square-cropped icons.

**Tech Stack:** Python 3.10+, requests, Pillow, unittest via `uv run pytest`.

**Spec:** `docs/superpowers/specs/2026-11-19-bgg-images-design.md`

## Global Constraints

- Frames stay 64x64 RGB; text via `retro_pixoo/font.py`; offline/failed images use `render._placeholder`/`render._icon` style fallbacks.
- Token only from `$BGG_TOKEN`; never printed. Commits: Conventional Commits, NO attribution trailers of any kind.
- Existing public signatures keep working: `bgg_*_frame(plays, today=None)` must still render (no images -> identicons) when `thumbs`/`fetcher` are omitted; `collect_pages(ra, lb, fetcher, bgg=None, bgg_pages=...)` stays compatible.

## Review Focus

- Zero plays / fewer than 4 or 5 games: no crash, no empty-id request.
- `thing` returns missing/blank thumbnail for a game: that game gets the identicon.
- `thing` request fails (HTTP error, 429, bad XML): pages still render with identicons, no error added, exit 0.
- Same game on several pages: its image is downloaded once.
- >20 ids: chunked requests, merged result.

---

### Task 1: Thumbnail lookup and game selection

**Files:**
- Modify: `retro_pixoo/bgg.py`, `retro_pixoo/bgg_render.py`
- Test: `tests/test_bgg.py`, `tests/test_render_bgg.py`

**Interfaces:**
- Produces in `bgg.py`: `parse_thumbnails(xml_text) -> dict[int, str]` (`<item id=…><thumbnail>url</thumbnail>`; blank/missing skipped); `BggClient.thumbnails(ids: list[int]) -> dict[int, str]` (empty list -> `{}` with no request; 20 ids per request to `https://boardgamegeek.com/xmlapi2/thing` with `id=<comma list>`, Bearer header; any failure returns what was gathered so far and never raises); `h_targets(plays, limit=4) -> list[tuple[int, str]]` = `(game_id, name)` of games needing a play to reach h+1, same ordering as `h_next`'s `first` (fewest short first? keep `game_counts` order).
- Produces in `bgg_render.py`: selection helpers `recent_games(plays, today, count=4)`, `top_games(plays, today, n=5)`, `h_games(plays, today, limit=4)`, `stats_game(plays, today)` each returning `list[tuple[int, str]]`; `needed_games(plays, pages: tuple[str, ...], today=None) -> list[tuple[int, str]]` (pages from `"h","recent","top","stats"`; deduplicated by game_id, first-seen order, year-filtered).

- [ ] **Step 1: Write failing tests**: `parse_thumbnails` on inline XML incl. a blank thumbnail; `BggClient.thumbnails` with `requests.get` mocked (25 ids -> two calls with 20 and 5 comma-joined ids, Bearer header, merged dict; `[]` -> no call; HTTP 429 or `requests.RequestException` on the second call -> first chunk's result returned, no raise); `needed_games` on `load_sample_plays()` with `today=date(2026,11,19)`: all four pages -> <= 10 unique ids and no duplicate ids; `("top",)` -> exactly 5; `("recent",)` -> 4 and equals the 4 newest plays' games; unknown games not in plays excluded; `[]` plays -> `[]`.
- [ ] **Step 2: Run** `uv run pytest tests/test_bgg.py tests/test_render_bgg.py -q` — expect new tests FAIL.
- [ ] **Step 3: Implement** the interfaces above.
- [ ] **Step 4: Run** the same command — expect PASS; run `uv run pytest -q` too.
- [ ] **Step 5: Commit** `feat(bgg): look up game thumbnails and select needed games`.

### Task 2: Image-aware renderers and wiring

**Files:**
- Modify: `retro_pixoo/bgg_render.py`, `retro_pixoo/update.py`, `README.md`
- Test: `tests/test_render_bgg.py`, `tests/test_update.py`

**Interfaces:**
- Consumes: Task 1 helpers; `render._icon`/`_placeholder`; `ra.ImageFetcher`.
- Produces: `bgg_*_frame(plays, today=None, thumbs: dict[int,str] | None = None, fetcher: ImageFetcher | None = None)`; new private `_game_icon(fetcher, thumbs, game_id, name, size)` center-crops to a square then `LANCZOS` resize, identicon (keyed on name) when no url/fetch failure. Layouts per the spec (recent 12px rows; top 10px rows; h icon row of up to 4 at 14px along the bottom replacing the single name line; stats ~20px icon of the most-played game top-right beside the totals), no text overlaps/clips with long names.
- `update.py`: `collect_pages` calls `needed_games`, then `BggClient().thumbnails` once (injected as an optional `bgg_thumbs: Callable[[list[int]], dict[int,str]] | None = None` kwarg so tests can stub; `--sample` passes none), then passes `thumbs` + the shared `fetcher` to each selected BGG frame. A thumbnails failure never adds to `errors`.

- [ ] **Step 1: Write failing tests**: each frame with a stubbed fetcher returning a solid-colour image differs from the no-image frame and keeps size 64x64; a counting fake fetcher shows each URL fetched once when all four pages render with shared games; thumbs missing for a game -> frame still renders (identicon); `collect_pages` with `bgg_thumbs` stub receives the exact `needed_games` ids once; a raising `bgg_thumbs` stub -> pages present, `errors` empty; `main(["--sample", "--preview", tmp, "--send", ""])` still writes 10 pages.
- [ ] **Step 2: Run** `uv run pytest tests/test_render_bgg.py tests/test_update.py -q` — expect new tests FAIL.
- [ ] **Step 3: Implement** renderers and wiring; update README (images note, one thumbnails request per run).
- [ ] **Step 4: Run** `uv run pytest -q` (all pass); render sample frames with a fake coloured-image fetcher to the scratchpad via `render.led_preview`, view the PNGs, and fix any clipping/overlap.
- [ ] **Step 5: Commit** `feat(bgg): show game thumbnails on the BGG pages`.
