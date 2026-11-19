# BGG game images design (addendum to 2026-11-19-bgg-pages-design.md)

## Intent
Small pixel game thumbnails on the BGG pages, like the Letterboxd/RA pages.

## Design
- Each selected page declares the games it draws: recent = last 4 played; top = top 5; h = up to 4 games needing a play to reach h+1; stats = the most-played game. `needed_games(plays, pages, today)` returns the deduplicated ordered union as `(game_id, name)`; unselected pages contribute nothing.
- One `thing` request (`/xmlapi2/thing?id=1,2,...`, Bearer `$BGG_TOKEN`, chunks of 20) returns `thumbnail` URLs: `BggClient.thumbnails(ids) -> {game_id: url}`. Images go through the shared `ImageFetcher` (cached, one download per game across pages).
- Failures (thing call or image) degrade to the identicon placeholder; no new errors, exit code unaffected.
- Images are center-cropped to a square, then resized with LANCZOS (same smooth downscale as other pages).
- Layouts: recent = 4 rows with 12px icon + name + date; top = 5 rows with 10px icon, rank, name, count, bar; h = row of up to 4 icons (14px) along the bottom for games needing a play; stats = ~20px icon of the most-played game beside the totals.
- Renderers share selection helpers with `needed_games` so what is fetched always equals what is drawn.

## Non-goals
Disk caching, new CLI flags, larger images.
