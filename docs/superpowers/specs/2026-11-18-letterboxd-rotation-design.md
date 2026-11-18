# Letterboxd pages + hourly update script

## Intent
Show Letterboxd diary activity on the Pixoo-64 alongside the existing two RetroAchievements pages, 30 seconds per page, refreshed by a script run hourly (cron/launchd).

## Goals
- `python -m retro_pixoo.update` — one-shot: fetch RA summary + Letterboxd RSS, render 4 pages, send to device, exit.
- Page order (interleaved): RA profile → Letterboxd last watched → RA recent unlocks → Letterboxd recent diary. 30s each (`PicSpeed`), device loops them itself.

## Non-goals
- Installing the cron/launchd job (documented in README only).
- Stats pages (counts, averages) — the feed has no totals.

## Approaches
- **One-shot command run by cron (chosen):** simple, survives reboots, no long-lived process.
- Long-running loop (`--loop`, as existing `__main__` has): needs process supervision; rejected.

## Design
- `retro_pixoo/letterboxd.py`
  - `DiaryEntry` dataclass: title, year, rating (float|None), liked, rewatch, watched_date (str), poster_url.
  - `parse_feed(xml: str) -> list[DiaryEntry]`: only items with `letterboxd:filmTitle` (watches and reviews); list items skipped. Poster = first `<img src>` in description CDATA. Order as in feed (newest first).
  - `LetterboxdClient(timeout).diary(user)` fetches `https://letterboxd.com/<user>/rss/`.
  - `load_sample_feed()` reads bundled `retro_pixoo/sample_feed.xml` (trimmed real feed, ~8 diary items + 1 list item).
- `render.py` additions
  - `last_watched_frame(entries, fetcher)`: header "LAST WATCHED"; poster ~28x42 left; right: wrapped title (white), year (grey), pixel stars incl. half stars (gold), heart icon if liked, rewatch marker if rewatch. Placeholder when poster missing; "NO FILMS" when empty.
  - `diary_frame(entries, fetcher, count=4)`: header "RECENT DIARY"; next 4 entries after the newest as ~15x22 posters in a row with stars below.
  - Stars drawn as small pixel glyphs (font has no star).
- `retro_pixoo/update.py` CLI: `--ra-user kelsin --lb-user kelsin13 --send IP --endpoint /post --seconds 30 --preview DIR --sample`.
  - Each source fetched independently; a failing source's pages are dropped and the error printed to stderr. If no pages, don't send, exit 1. Exit 1 also if any source failed (so cron logs it), after sending what succeeded.
- Tests: stdlib unittest (pytest isn't installed) for `parse_feed` (fields, rating none, lists skipped) and page assembly / failure handling in update.
- README: usage + hourly crontab line.

## Left to the builder
Exact pixel layout within the stated sizes; star glyph design.
