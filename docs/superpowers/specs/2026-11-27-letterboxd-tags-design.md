# Letterboxd tag pages

## Intent

Show, for four Letterboxd diary tags, how many films were logged with that tag this year and which one was the most recent. The four tags are `theater:frida`, `theater:regal`, `people:kerrigan` and `people:caitlin`. Letterboxd has no public API, the RSS feed carries no tags, and the tag pages sit behind a Cloudflare bot check, so the data comes from Letterboxd's own data export. The hourly job asks the user's real browser to download a fresh export once a day.

## Goals / non-goals

- Goals: one page per tag in the rotation, followed by a new "PLAY MORE VIDEO GAMES" motivation slide. The export download is requested automatically once a day.
- Non-goals: configurable tags (they're constants in code), counts newer than the latest export, deleting old exports from `~/Downloads`.
- Anti-goals: anything that gets around Letterboxd's bot check (headless login, browser impersonation, storing the Letterboxd password).

## Approaches

1. **Data export + daily browser download** (picked). `open https://letterboxd.com/data/export/` downloads the ZIP straight away using the browser's existing login. The hourly job reads `diary.csv` from the newest ZIP. Counts can lag by up to a day.
2. Scrape the tag pages: blocked by Cloudflare (403 "Just a moment"). Getting past that is bot-detection evasion, so it's ruled out.
3. Official API: supports tag filters but needs approval Letterboxd rarely gives individuals.

## Data

- Export ZIP: newest `letterboxd-<lb_user>-*.zip` in `--lb-export-dir` (default `~/Downloads`). Newest is by file name, which embeds a UTC timestamp. `diary.csv` columns: `Date` (logged), `Name`, `Year`, `Letterboxd URI`, `Rating` (blank or `0.5`–`5`), `Rewatch`, `Tags` (comma + space separated), `Watched Date`.
- Count = diary rows whose tag list contains the tag and whose `Watched Date` falls in the current year. Rewatches count; each diary entry is one.
- Most recent = the matching row with the greatest (`Watched Date`, `Date`).
- Posters: the export has none. Match title + year against the RSS diary entries the rotation already fetches. Every RSS poster seen is saved to a JSON cache at `~/Library/Caches/retro-pixoo/posters.json`, keyed `"<title>|<year>"`. That way a tag that's been idle for a while keeps its poster after the film drops out of the 50-entry feed. If no poster is found, the page uses the existing `_placeholder`.
- Stale export: if the newest ZIP is more than 8 days old, print a warning to stderr. That isn't an error and doesn't change the exit code.
- No ZIP found, or the ZIP can't be read: report the error like the other sources (`letterboxd export: ...`). The tag segment and its slide are skipped, and the job exits 1.

## Pages (approved mockups)

Tags, in order, with header name and colour: FRIDA `LB_ORANGE`, REGAL `CYAN`, KERRIGAN `LB_GREEN`, CAITLIN `RED`.

Each tag page:

- `_header(img, NAME)`.
- Poster 28x42 at (1, 9), the same as `last_watched_frame`.
- The count at scale 2 in the tag colour at (32, 10), and `IN <year>` in `GREY` at (32, 22).
- The watched date, for example `NOV 23` (`_watched_date`), in `WHITE` at (32, 37).
- `_stars(img, 32, 44, rating)`.
- The title wrapped to 62 px, max 2 lines, `WHITE`, starting at (1, 52), 6 px line pitch. This is the original position the user picked.
- No matches this year: count `0`, a placeholder poster, title `NONE YET` in `GREY`, and no date or stars.

Slide `handhelds_frame` (in `motivation.py`):

- A red TrimUI Brick tilted +10° on the left, in front.
- A clear-purple Retroid Pocket Nova tilted -9° on the right, behind. It has white D-pad and X/Y buttons, a green A (right), a red B (bottom), a dark left stick and a yellow right stick.
- `PLAY MORE` in `WHITE` at row 44 and `VIDEO GAMES` in `GOLD` at row 52, centred.
- Tilting works like this: upscale 8x with NEAREST, rotate with BICUBIC (expand), `reduce(8)`, then harden alpha at 128. The exact drawing code is the approved mockup script.

## Rotation

After the BGG segment: four tag pages, then the next motivation slide. `SLIDES` gains `handhelds_frame` as its 4th entry, so with every source up the order is RA, voice, LB, scroll, BGG, breathe, tags, handhelds. As before, if a segment fails its slide is skipped and later slides shift up.

## Daily export request

- No separate agent. `main` (live mode only) calls `request_export_if_due` before collecting pages. It opens `https://letterboxd.com/data/export/` with `/usr/bin/open` from 06:00 local time, when the newest export isn't from today (its file-name UTC time converted to local) and `~/Library/Caches/retro-pixoo/export_requested` doesn't already hold today's date. The launchd job has a 06:00 `StartCalendarInterval` so a run happens at 06:00, and any later run that day catches up. A missing Downloads permission means no request (the tags source reports the real error). After requesting, the run waits up to 2 minutes for a new, complete export (a ZIP containing `diary.csv`) and uses it in the same run; if none arrives it prints `letterboxd export: no new export after 120s; using the previous one` to stderr and uses the previous export. A successful pickup prints `letterboxd export: got <name>`.
- A failed request prints `letterboxd export: request failed: ...` to stderr and is not an error. A successful one prints `letterboxd export: requested a new export`.
- `make export` opens the page manually; `make uninstall` and `make reload` also remove the old weekly `com.retro-pixoo.lb-export` agent if present.
- README documents the manual steps: the browser stays signed in to Letterboxd and saves downloads to `~/Downloads`, plus a one-time **Files and Folders → Downloads** grant for the hourly job's Python (macOS blocks background jobs from reading `~/Downloads`; same kind of grant as Local Network).

## CLI

`--lb-export-dir PATH` (default `~/Downloads`). `--sample` uses a bundled `retro_pixoo/sample_diary.csv` (a trimmed real export) with no network access.

## Calls made by Claude (user can override)

- The export is requested at most once per local day, from 06:00.
- The cache location is `~/Library/Caches/retro-pixoo/`.
- The stale threshold is 8 days.
- A tag with no films this year shows `NONE YET`.
- The Nova's A is on the right and B at the bottom.

## Left to the builder

Module split. Tests:
- CSV parsing and counting, covering the year filter, multiple tags per row, blank ratings and tie-breaks.
- Picking the newest ZIP.
- Poster cache round-trip and fallback.
- Each frame is 64x64 RGB.
- `collect_pages` ordering when the export fails.
