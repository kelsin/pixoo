# Letterboxd tag pages

## Intent

Show, for four Letterboxd diary tags, how many films were logged with that tag this year and which one was the most recent. The four tags are `theater:frida`, `theater:regal`, `people:kerrigan` and `people:caitlin`. Letterboxd has no public API, the RSS feed carries no tags, and the tag pages sit behind a Cloudflare bot check, so the data comes from Letterboxd's own data export. A weekly job downloads the export through the user's real browser.

## Goals / non-goals

- Goals: one page per tag in the rotation, followed by a new "PLAY MORE VIDEO GAMES" motivation slide. The export download is automated weekly.
- Non-goals: configurable tags (they're constants in code), counts newer than the latest export, deleting old exports from `~/Downloads`.
- Anti-goals: anything that gets around Letterboxd's bot check (headless login, browser impersonation, storing the Letterboxd password).

## Approaches

1. **Data export + weekly browser download** (picked). `open https://letterboxd.com/data/export/` downloads the ZIP straight away using the browser's existing login. The hourly job reads `diary.csv` from the newest ZIP. Counts can lag by up to a week.
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

## Weekly export job

- New template `launchd/com.retro-pixoo.lb-export.plist.in`. It runs `/usr/bin/open https://letterboxd.com/data/export/` with `StartCalendarInterval` Sunday 09:00. launchd runs a missed interval on wake.
- Makefile: `plist`, `install`, `uninstall` and `reload` handle both agents.
- README documents it, including one manual step. The hourly job's Python needs **Files and Folders → Downloads** access, because macOS blocks background jobs from reading `~/Downloads`. This is the same kind of one-time grant as the existing Local Network permission.

## CLI

`--lb-export-dir PATH` (default `~/Downloads`). `--sample` uses a bundled `retro_pixoo/sample_diary.csv` (a trimmed real export) with no network access.

## Calls made by Claude (user can override)

- The weekly time is Sunday 09:00.
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
