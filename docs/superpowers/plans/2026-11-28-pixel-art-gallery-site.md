# Pixel-art gallery site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the Pixoo pages as a static fullscreen pixel-art slideshow on GitHub Pages, rebuilt and pushed by the hourly launchd job.

**Architecture:** `update.py --site DIR` writes `index.html`, `page{N}.png`, `manifest.json` (and optional `CNAME`) via a new `retro_pixoo/site.py`. `scripts/publish-site.sh` force-pushes that directory as a single orphan commit to `gh-pages`, skipping when unchanged. The launchd command runs the publish after the update.

**Tech Stack:** Python 3 / Pillow / unittest-style pytest, vanilla HTML+JS+CSS, bash, git.

**Spec:** `docs/superpowers/specs/2026-11-28-pixel-art-gallery-site-design.md`

## Global Constraints

- 30 seconds per image; images drawn with `image-rendering: pixelated`, black background, largest square fitting the viewport.
- Use the raw 64x64 frames (`page{N}_64.png` equivalents), not the LED previews.
- No JS libraries or build tooling; `index.html` is a single file with inline JS/CSS.
- Conventional Commits; run tests with `uv run pytest`.
- Force-pushed `gh-pages` must be one orphan commit (no history growth) and must keep a `CNAME` file when a domain is configured (a Pages custom domain set in the UI is stored as `CNAME` in the branch and would be wiped otherwise).

## Review Focus

- Zero pages: `write_site` must still produce a valid manifest (empty list) and the page must not crash / divide by zero.
- Stale files: a run with fewer pages than the last must delete old `page{N}.png` files from the site dir.
- Single page: Left/Right/auto-advance must stay on page 1 without errors.
- Manifest changing under an open tab (fewer pages than current index): the current index must clamp.
- Publish with unchanged images must not push; publish with a missing site dir must exit 0 without pushing.

---

### Task 1: Site writer and `--site` flag

**Files:**
- Create: `retro_pixoo/site.py`, `tests/test_site.py`
- Create: `retro_pixoo/site/index.html` (placeholder `<!doctype html><title>pixoo</title>`; Task 2 replaces it)
- Modify: `retro_pixoo/update.py` (`main`, near the `--no-preview` handling)
- Test: `tests/test_site.py`, `tests/test_update.py`

**Interfaces:**
- Produces: `write_site(pages: list[Image.Image], out_dir: Path, seconds: int = 30, cname: str | None = None) -> None`. Writes `index.html` (copied from `retro_pixoo/site/index.html`), `page1.png`..`pageN.png` (the raw RGB frames, unscaled), `manifest.json` = `{"seconds": int, "pages": ["page1.png", ...], "generated": "<ISO UTC timestamp>"}`, `.nojekyll`, and `CNAME` (contents = `cname`) only when `cname` is given. Deletes any existing `page*.png` in `out_dir` not in the new set, and removes a stale `CNAME` when `cname` is None.
- CLI: `--site DIR` (Path, default None) and `--site-cname HOST` (default env `SITE_CNAME`); when `--site` is set and pages exist, call `write_site(pages, args.site, args.seconds, args.site_cname)` and print `wrote site to DIR`.

- [ ] **Step 1: Write failing tests** in `tests/test_site.py`: `test_writes_pages_and_manifest_in_order` (3 distinct-color frames; manifest `pages == ["page1.png","page2.png","page3.png"]`, `seconds == 30`, each PNG is 64x64 and pixel-equal to its frame), `test_removes_stale_pages` (write 3 then 1; `page2.png`/`page3.png` gone), `test_empty_pages_writes_empty_manifest`, `test_cname_written_and_removed`, `test_nojekyll_and_index_present`. In `tests/test_update.py` add `test_main_sample_site` using `main(["--sample","--no-preview","--site",tmp])` in the existing sample-run style and assert `manifest.json` lists the same number of pages as the sample run produces.
- [ ] **Step 2:** `uv run pytest tests/test_site.py tests/test_update.py -q` → FAIL (no `retro_pixoo.site`).
- [ ] **Step 3:** Implement `write_site` in `retro_pixoo/site.py` (copy template via `Path(__file__).parent / "site" / "index.html"`; convert frames with `.convert("RGB")` before saving). Add the two flags and call in `update.py`.
- [ ] **Step 4:** Run the same pytest command → PASS; then `uv run pytest -q` → all pass.
- [ ] **Step 5:** Commit `feat(site): write static gallery site from the rendered pages`.

### Task 2: The gallery page

**Files:**
- Modify: `retro_pixoo/site/index.html` (replace placeholder)

**Interfaces:**
- Consumes: `manifest.json` shape from Task 1 (`seconds`, `pages`), fetched relative to the page with `cache: "no-store"`.

Behavior to implement (single file, inline CSS/JS, no libraries):
- Body black, no scrollbars. **Fullscreen mode:** current image in a square sized `min(100vw, 100vh)` (leave room so the 6px timer bar at the bottom overlays rather than shrinks it), `image-rendering: pixelated`, centered.
- **Timer bar:** fixed to the bottom, full-width track, fill animates 0→100% over `seconds`; when it completes, advance to next page (wrap). Manual navigation restarts it. Driven by `requestAnimationFrame` timestamps (not CSS-only) so grid-pause/resume is exact.
- Keys: `ArrowRight`/`ArrowLeft` = next/previous (wrap) in fullscreen; `ArrowUp` enters grid mode; in grid mode Left/Right move selection (wrap), Up/Down move by one row, `ArrowDown` (or Enter) returns to fullscreen on the selected page. Slideshow and timer are paused while in grid; timer restarts on return. Clicking/tapping a grid cell selects and returns to fullscreen; tapping elsewhere in fullscreen does nothing.
- **Grid mode:** all pages as pixelated thumbnails in a responsive CSS grid (square cells, ~12px gap, selected cell has a white 3px outline), scrolls the selected cell into view.
- Re-fetch `manifest.json` every hour; when it changes, replace the page list, clamp the current index, and cache-bust image URLs with `?v=<generated>`.
- Edge cases: empty `pages` shows nothing and does not throw; a single page stays put on every navigation.

- [ ] **Step 1:** Generate sample site: `uv run retro-pixoo-update --sample --no-preview --site /tmp-free scratchpad dir` (use the session scratchpad), then serve it with `python3 -m http.server` from that dir.
- [ ] **Step 2:** Write the page. Open in the browser pane, verify at desktop and mobile (390x844) sizes: fullscreen fit, ArrowRight/Left wrap, timer bar fills and auto-advances (temporarily check with a manifest `seconds` of 3), ArrowUp grid shows all pages with selection, arrows move selection, ArrowDown returns to the selected page, click-to-select works, an empty-pages manifest does not throw (check console), one-page manifest navigation is stable.
- [ ] **Step 3:** `uv run pytest -q` → pass (Task 1 tests must still pass with the real template).
- [ ] **Step 4:** Commit `feat(site): fullscreen pixel-art slideshow with grid view and timer bar`.

### Task 3: Publish script, launchd wiring, setup guide

**Files:**
- Create: `scripts/publish-site.sh` (executable), `docs/pages-setup.md`
- Modify: `launchd/com.retro-pixoo.hourly.plist.in`, `Makefile` (new `site` and `publish` targets, add to `.PHONY`/help), `README.md` (short Site section linking the guide), `.gitignore` (add `site/`)

**Interfaces:**
- Consumes: site dir produced by Task 1 (`update.py --site`).
- Produces: `scripts/publish-site.sh SITE_DIR` — exits 0 with a message if `SITE_DIR` is missing/empty; computes a hash over all files in SITE_DIR except `manifest.json` (e.g. `find ... -type f ! -name manifest.json | sort | xargs shasum | shasum`) and compares to `~/Library/Application Support/retro-pixoo/site-hash`, exiting 0 "unchanged" on a match; otherwise copies SITE_DIR to a mktemp dir, `git init`, commits all with message `site: update gallery` (author from existing git config), and `git push --force <remote-url of the repo at $PWD's origin> HEAD:gh-pages`, then writes the new hash. Fails (non-zero) if the push fails, without writing the hash. Cleans up the temp dir.

- [ ] **Step 1:** Write the script; test it against a throwaway bare repo: set up `git init --bare` in the scratchpad, point the script at it via an optional `PUBLISH_REMOTE` env override (default: `git remote get-url origin`) and `HASH_FILE` env override (default path above). Verify: first run pushes a single-commit `gh-pages`; second run with same images prints unchanged and doesn't push; changing a PNG pushes a new orphan commit (branch still has exactly 1 commit); missing dir exits 0 without pushing.
- [ ] **Step 2:** Update the plist command to: run the existing update with `--site "$HOME/Library/Application Support/retro-pixoo/site"` appended, then `; scripts/publish-site.sh "$HOME/Library/Application Support/retro-pixoo/site"` (use `;` so a partial-error exit 1 from the update still publishes). Pass `SITE_CNAME` through from a new `SITE_CNAME ?=` Makefile variable (`@SITE_CNAME@` placeholder in the plist, substituted like the others; empty = no CNAME). Add `make site` (sample site into `preview-site/`) and `make publish`. Run `make plist` into a temp location or `plutil -lint` the substituted output to verify it parses.
- [ ] **Step 3:** Write `docs/pages-setup.md`: (a) one-time `make reload PIXOO_IP=... SITE_CNAME=pixoo.kelsin.net` and run once with `make run`, confirm `gh-pages` branch exists; (b) GitHub repo Settings → Pages → Source "Deploy from a branch", branch `gh-pages`, folder `/ (root)`; (c) Custom domain `pixoo.kelsin.net` in that same page — note the CNAME file is already supplied by the job so force-pushes keep it; (d) DNS at the kelsin.net provider: a `CNAME` record `pixoo` → `kelsin.github.io` (no trailing path, not the repo name); wait for the DNS check, then tick "Enforce HTTPS" once the certificate is issued (can take up to ~1 hour); (e) verification: `dig pixoo.kelsin.net +short`, load the URL; (f) troubleshooting: 404 (branch/folder wrong), domain reset after publish (CNAME missing: check `SITE_CNAME` made it into the plist), HTTPS option greyed out (DNS not propagated), and the hourly push cadence/log location (`~/Library/Logs/retro-pixoo.log`).
- [ ] **Step 4:** `uv run pytest -q` → all pass. Commit `feat(site): publish the gallery to gh-pages from the hourly job`.
