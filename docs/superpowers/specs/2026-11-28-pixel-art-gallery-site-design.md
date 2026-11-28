# Pixel-art gallery site (GitHub Pages) — design

## Intent
Show the Pixoo pages on the web: pixel art on black, full-viewport, cycling like the device. Data is public by the owner's choice (repo is public too).

## Goals
- Static site: `index.html` (inline JS/CSS) + `manifest.json` + raw `page{N}_64.png` files.
- Image drawn with `image-rendering: pixelated`, largest square that fits the viewport, black background.
- Slideshow: advances every 30s, loops. Left/Right go back/forward; any manual move restarts the 30s timer.
- Thin timer bar along the bottom fills over 30s.
- Up arrow: zoomed-out grid of all pages (slideshow paused). Arrows move selection; Down returns to the selected page fullscreen. Clicks/taps also work (builder's call). Manifest re-fetched hourly so open tabs pick up new art.
- `update.py --site DIR` writes the site (template in `retro_pixoo/site/`).
- `scripts/publish-site.sh`: copy site into a temp git repo, single orphan commit, force-push to `gh-pages`; skip if images unchanged since last push. launchd job runs it after the update.
- A guide for enabling Pages with a custom domain (e.g. pixoo.kelsin.net).

## Non-goals / anti-goals
- No build tooling, frameworks, or per-hour commits piling up in history.
- No private hosting or auth.

## Approaches
GitHub Pages from an orphan `gh-pages` branch (chosen). Alternatives (private bucket, local server) dropped because data is public and Pages is free and simplest.

## Left to the builder
Template details, manifest shape, change-detection method, test layout (pytest for manifest order and files written; page behavior checked manually in a browser).
