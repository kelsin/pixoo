# Letterboxd Tag Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Four Letterboxd tag pages (this year's count + most recent film per tag) from the weekly data export, followed by a new handheld motivation slide, plus a weekly launchd job that downloads the export.

**Architecture:** `retro_pixoo/lb_export.py` finds and parses the newest export ZIP and keeps a JSON poster cache fed from the RSS diary. `retro_pixoo/tags_render.py` draws one page per tag. `motivation.handhelds_frame` is the new slide. `update.collect_pages` gains an export source that renders after BGG.

**Tech Stack:** Python 3, Pillow, `zipfile`/`csv` stdlib, unittest via `uv run pytest`, launchd.

**Spec:** `docs/superpowers/specs/2026-11-27-letterboxd-tags-design.md`

## Global Constraints

- Tags and order: `("FRIDA", "theater:frida", LB_ORANGE)`, `("REGAL", "theater:regal", CYAN)`, `("KERRIGAN", "people:kerrigan", LB_GREEN)`, `("CAITLIN", "people:caitlin", RED)` (colours from `retro_pixoo/render.py`).
- Export file glob: `letterboxd-<lb_user>-*.zip`; newest = greatest file name. Name format `letterboxd-kelsin13-2026-11-28-01-56-utc.zip`.
- Default export dir `~/Downloads`; poster cache `~/Library/Caches/retro-pixoo/posters.json`, keys `"<title>|<year>"`.
- Stale threshold: warn on stderr when the export is more than 8 days old (not an error).
- Error label for export failures: `letterboxd export: <msg>` (same `str(e) or type(e).__name__` rule as other sources).
- Weekly job: `open https://letterboxd.com/data/export/`, Sunday 09:00.
- Pixel art: `Image.NEAREST` for poster placeholders, bitmap font from `retro_pixoo/font.py`.
- Commits use Conventional Commits and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- Tags with odd spacing/case in the CSV (`"people:kerrigan, theater:regal"`): split on `,` and strip; matching is exact after strip.
- Rows with blank `Rating` or blank `Year`: parse to `None`, never crash.
- A tag with no rows this year: page shows `0` and `NONE YET`, not an exception.
- Poster cache file missing or corrupt JSON: treated as empty, then rewritten.
- Export dir with no matching ZIP (or other users' exports): `FileNotFoundError` with the dir and pattern in the message → reported as `letterboxd export: ...`, other pages still render.

---

### Task 1: Export reader and poster cache

**Files:**
- Create: `retro_pixoo/lb_export.py`
- Create: `retro_pixoo/sample_diary.csv`
- Test: `tests/test_lb_export.py`

**Interfaces:**
- Produces:
  - `@dataclass DiaryRow: name: str; year: int | None; rating: float | None; tags: tuple[str, ...]; watched: str; logged: str`
  - `parse_diary_csv(text: str) -> list[DiaryRow]`
  - `newest_export(directory: Path, user: str) -> Path` (raises `FileNotFoundError`)
  - `export_date(path: Path) -> date` (from the name's `YYYY-MM-DD`)
  - `load_export(path: Path) -> list[DiaryRow]` (reads `diary.csv` inside the ZIP, UTF-8)
  - `@dataclass TagSummary: count: int; latest: DiaryRow | None`
  - `summarize(rows: list[DiaryRow], tag: str, year: int) -> TagSummary`
  - `class PosterCache: __init__(self, path: Path | None)`; `update(self, entries: list[DiaryEntry]) -> None` (adds every entry with a `poster_url`, saves if `path`); `get(self, title: str, year: int | None) -> str` (`""` when unknown)
  - `CACHE_PATH = Path.home() / "Library/Caches/retro-pixoo/posters.json"`, `SAMPLE_YEAR = 2026`, `load_sample_diary() -> list[DiaryRow]`

- [ ] **Step 1: Build the sample CSV.** From the real export at `/private/tmp/claude-501/-Users-kelsin-src-pixoo--claude-worktrees-divoom-pixoo-python-0a791f/029aa107-e838-4cbc-8528-43f50ecd8b25/scratchpad/export/diary.csv` (if gone, unzip the newest `~/Downloads/letterboxd-kelsin13-*.zip` into the scratchpad), write `retro_pixoo/sample_diary.csv` with the same header and: the last 5 rows of 2026 for each of the four tags (dedupe), 3 untagged 2026 rows, and 2 rows tagged `theater:frida` from 2025. Use `uv run python -I`.

- [ ] **Step 2: Write failing tests** in `tests/test_lb_export.py` (unittest style like `tests/test_letterboxd.py`):

```python
CSV = ("Date,Name,Year,Letterboxd URI,Rating,Rewatch,Tags,Watched Date\n"
       "2026-11-17,Wildwood,2026,u,5,,\"people:kerrigan, theater:regal, people:caitlin\",2026-11-16\n"
       "2026-11-24,Tomboy,2011,u,,,theater:frida,2026-11-23\n"
       "2026-11-25,Water Lilies,,u,4.5,Yes,theater:frida,2026-11-23\n"
       "2025-12-30,Old,1999,u,3,,theater:frida,2025-12-29\n")

def test_parse_fields(self):
    rows = parse_diary_csv(CSV)
    self.assertEqual(rows[0].tags, ("people:kerrigan", "theater:regal", "people:caitlin"))
    self.assertIsNone(rows[1].rating); self.assertIsNone(rows[2].year)
    self.assertEqual((rows[2].rating, rows[2].watched, rows[2].logged), (4.5, "2026-11-23", "2026-11-25"))

def test_summarize_year_and_tiebreak(self):
    s = summarize(parse_diary_csv(CSV), "theater:frida", 2026)
    self.assertEqual(s.count, 2)
    self.assertEqual(s.latest.name, "Water Lilies")   # same watched day, logged later

def test_summarize_none(self):
    self.assertEqual(summarize(parse_diary_csv(CSV), "people:caitlin", 2025), TagSummary(0, None))

def test_newest_export_and_date(self):  # tempdir with
    # letterboxd-kelsin13-2026-11-21-01-00-utc.zip, letterboxd-kelsin13-2026-11-28-01-56-utc.zip,
    # letterboxd-someoneelse-2026-12-01-00-00-utc.zip
    self.assertEqual(newest_export(d, "kelsin13").name, "letterboxd-kelsin13-2026-11-28-01-56-utc.zip")
    self.assertEqual(export_date(newest_export(d, "kelsin13")), date(2026, 11, 28))

def test_newest_export_missing(self):
    with self.assertRaises(FileNotFoundError): newest_export(empty_dir, "kelsin13")

def test_load_export_reads_zip(self):  # write a zip containing diary.csv = CSV
    self.assertEqual(len(load_export(zip_path)), 4)

def test_poster_cache_roundtrip(self):
    c = PosterCache(tmp / "sub" / "posters.json")
    c.update([DiaryEntry("Tomboy", 2011, None, False, False, "2026-11-23", "http://p")])
    self.assertEqual(PosterCache(tmp / "sub" / "posters.json").get("Tomboy", 2011), "http://p")
    self.assertEqual(c.get("Nope", 2000), "")

def test_poster_cache_corrupt_file(self):
    p.write_text("{not json"); self.assertEqual(PosterCache(p).get("x", 1), "")

def test_sample_diary_has_all_tags(self):
    rows = load_sample_diary()
    for tag in ("theater:frida", "theater:regal", "people:kerrigan", "people:caitlin"):
        self.assertGreater(summarize(rows, tag, SAMPLE_YEAR).count, 0)
```

- [ ] **Step 3: Run** `uv run pytest tests/test_lb_export.py -q` → FAIL (module missing).

- [ ] **Step 4: Implement `retro_pixoo/lb_export.py`.** `csv.DictReader`; tags `tuple(t.strip() for t in s.split(",") if t.strip())`; `summarize` filters `tag in row.tags and row.watched.startswith(f"{year}-")`, latest = `max(key=lambda r: (r.watched, r.logged))`. `PosterCache` loads JSON on init (any exception → `{}`), `update` creates parent dirs and writes only when something changed.

- [ ] **Step 5: Run** `uv run pytest tests/test_lb_export.py -q` → PASS.

- [ ] **Step 6: Commit** `feat(letterboxd): read tag counts from the data export`.

### Task 2: Tag pages

**Files:**
- Create: `retro_pixoo/tags_render.py`
- Test: `tests/test_render_tags.py`

**Interfaces:**
- Consumes: Task 1 `DiaryRow`, `TagSummary`, `summarize`; `render._header`, `render._placeholder`, `render._stars`, `render._watched_date`, `render.SIZE/BG/WHITE/GREY`, `ra.ImageFetcher`.
- Produces:
  - `TAGS: tuple[tuple[str, str, RGB], ...]` (Global Constraints order)
  - `tag_frame(name: str, color, summary: TagSummary, year: int, poster_url: str, fetcher: ImageFetcher) -> Image.Image`
  - `tag_frames(rows: list[DiaryRow], poster_for: Callable[[str, int | None], str], fetcher: ImageFetcher, year: int) -> list[Image.Image]` (four frames, `TAGS` order)

- [ ] **Step 1: Write failing tests** (offline `ImageFetcher(offline=True)`):

```python
def test_four_frames_64_rgb(self):
    frames = tag_frames(load_sample_diary(), lambda t, y: "", self.f, SAMPLE_YEAR)
    self.assertEqual(len(frames), 4)
    for img in frames: self.assertEqual((img.size, img.mode), ((64, 64), "RGB"))

def test_count_in_tag_colour(self):   # count drawn at scale 2 from (32, 10)
    row = DiaryRow("Tomboy", 2011, 5.0, ("theater:frida",), "2026-11-23", "2026-11-24")
    img = tag_frame("FRIDA", LB_ORANGE, TagSummary(167, row), 2026, "", self.f)
    self.assertTrue(any(img.getpixel((x, y)) == LB_ORANGE for x in range(32, 64) for y in range(10, 20)))
    self.assertTrue(any(img.getpixel((x, y)) == WHITE for x in range(64) for y in range(52, 64)))  # title rows

def test_title_wraps_to_two_lines(self):
    row = DiaryRow("Godzilla Minus Zero", 2026, 5.0, (), "2026-11-15", "2026-11-16")
    img = tag_frame("REGAL", CYAN, TagSummary(35, row), 2026, "", self.f)
    self.assertTrue(any(img.getpixel((x, y)) == WHITE for x in range(64) for y in range(58, 63)))

def test_none_yet(self):
    img = tag_frame("CAITLIN", RED, TagSummary(0, None), 2026, "", self.f)
    self.assertTrue(any(img.getpixel((x, y)) == GREY for x in range(64) for y in range(52, 58)))
    self.assertFalse(any(img.getpixel((x, y)) == GOLD for x in range(32, 64) for y in range(44, 50)))  # no stars

def test_poster_lookup_uses_title_and_year(self):
    seen = []
    tag_frames(load_sample_diary(), lambda t, y: seen.append((t, y)) or "", self.f, SAMPLE_YEAR)
    self.assertEqual(len(seen), 4)
```

- [ ] **Step 2: Run** `uv run pytest tests/test_render_tags.py -q` → FAIL.

- [ ] **Step 3: Implement** per the spec's "Pages" section: header name; poster 28x42 at (1, 9) (fetched image resized `LANCZOS` like `render._poster`, else `_placeholder(title, 28)` resized NEAREST; for `NONE YET` use `_placeholder(name, 28)`); count `font.draw_text(img, 32, 10, str(n), color, scale=2)`; `IN <year>` GREY at (32, 22); `_watched_date` WHITE at (32, 37); `_stars(img, 32, 44, rating)`; title `font.wrap(title, 62, 2)` WHITE from (1, 52), 6 px pitch. Empty: `0`, `IN <year>`, `NONE YET` GREY at (1, 52), no date/stars.

- [ ] **Step 4: Run** `uv run pytest tests/test_render_tags.py -q` → PASS.

- [ ] **Step 5: Commit** `feat(letterboxd): tag count pages`.

### Task 3: Handheld motivation slide

**Files:**
- Modify: `retro_pixoo/motivation.py` (add `handhelds_frame`, append to `SLIDES`)
- Create: `tests/fixtures/handhelds_64.png` (copy of the approved mockup `/private/tmp/claude-501/-Users-kelsin-src-pixoo--claude-worktrees-divoom-pixoo-python-0a791f/029aa107-e838-4cbc-8528-43f50ecd8b25/scratchpad/mock/duo_64.png`)
- Modify: `tests/test_motivation.py`

**Interfaces:**
- Produces: `handhelds_frame() -> Image.Image`; `SLIDES == (voice_frame, scroll_frame, breathe_frame, handhelds_frame)`.

- [ ] **Step 1: Update tests:** `test_slides_order` expects the 4-tuple; `test_slides_differ` expects 4; `test_text_rows` adds `(handhelds_frame, GOLD)`; new test:

```python
def test_handhelds_matches_approved_mockup(self):
    want = Image.open(Path(__file__).parent / "fixtures" / "handhelds_64.png").convert("RGB")
    self.assertEqual(handhelds_frame().tobytes(), want.tobytes())
```

- [ ] **Step 2: Run** `uv run pytest tests/test_motivation.py -q` → FAIL.

- [ ] **Step 3: Implement** by porting the approved mockup verbatim — this is exact art, so copy these bodies (module-private helpers, `_canvas`/`_centred` already exist):

```python
_T = (0, 0, 0, 0)

def _screen(w, h, sky, hill):
    im = Image.new("RGBA", (w, h), sky); d = ImageDraw.Draw(im)
    d.ellipse([-4, h // 2, w // 2 + 3, h + 6], fill=hill)
    d.ellipse([w // 3, h // 2 - 2, w + 5, h + 8], fill=tuple(c * 3 // 4 for c in hill[:3]) + (255,))
    d.rectangle([w - 5, 1, w - 3, 3], fill=GOLD + (255,))
    return im

def _brick():  # red TrimUI Brick
    im = Image.new("RGBA", (22, 30), _T); d = ImageDraw.Draw(im)
    red, dark, key = (205, 35, 45, 255), (130, 18, 28, 255), (40, 20, 24, 255)
    d.rounded_rectangle([0, 0, 21, 29], radius=2, fill=red)
    d.line([(1, 29), (20, 29)], fill=dark); d.line([(21, 2), (21, 27)], fill=dark)
    d.rectangle([2, 2, 19, 15], fill=(20, 20, 24, 255))
    im.paste(_screen(16, 12, (90, 160, 240, 255), (60, 190, 90, 255)), (3, 3))
    d.rectangle([4, 19, 6, 25], fill=key); d.rectangle([2, 21, 8, 23], fill=key)
    for x, y in ((15, 18), (18, 21), (12, 21), (15, 24)):
        d.rectangle([x, y, x + 1, y + 1], fill=key)
    d.rectangle([9, 27, 10, 27], fill=(60, 140, 255, 255)); d.rectangle([12, 27, 13, 27], fill=key)
    return im

def _nova():  # clear-purple Retroid Pocket Nova
    im = Image.new("RGBA", (38, 21), _T); d = ImageDraw.Draw(im)
    body, light, deep = (130, 75, 200, 255), (185, 140, 240, 255), (60, 25, 110, 255)
    d.rounded_rectangle([0, 0, 37, 20], radius=6, fill=body)
    d.line([(5, 1), (32, 1)], fill=light)
    d.rounded_rectangle([4, 14, 12, 20], radius=3, fill=deep); d.rounded_rectangle([25, 14, 33, 20], radius=3, fill=deep)
    d.rectangle([10, 2, 27, 16], fill=(15, 12, 22, 255))
    im.paste(_screen(16, 13, (255, 150, 90, 255), (120, 60, 170, 255)), (11, 3))
    btn = (235, 225, 255, 255)
    d.rectangle([4, 3, 5, 10], fill=btn); d.rectangle([1, 6, 8, 7], fill=btn)
    d.ellipse([3, 11, 6, 14], fill=deep)
    for (x, y), c in zip(((31, 2), (34, 5), (29, 5), (31, 8)),
                         (btn, (40, 210, 90, 255), btn, (235, 50, 60, 255))):
        d.rectangle([x, y, x + 1, y + 1], fill=c)
    d.ellipse([31, 11, 34, 14], fill=(255, 205, 40, 255))
    return im

def _tilt(im, deg, k=8):
    """Rotate pixel art cleanly: upscale, rotate smoothly, box-downsample, harden alpha."""
    big = im.resize((im.width * k, im.height * k), Image.NEAREST).rotate(deg, resample=Image.BICUBIC, expand=True)
    out = big.reduce(k)
    out.putalpha(out.getchannel("A").point(lambda v: 255 if v >= 128 else 0))
    return out

def handhelds_frame() -> Image.Image:
    """A red TrimUI Brick and a purple Retroid Pocket Nova, tilted and overlapping."""
    img, _ = _canvas()
    b, n = _tilt(_brick(), 10), _tilt(_nova(), -9)
    img.paste(n, (64 - n.width, 10), n)
    img.paste(b, (2, 3), b)
    _centred(img, 44, "PLAY MORE", WHITE)
    _centred(img, 52, "VIDEO GAMES", GOLD)
    return img
```

- [ ] **Step 4: Run** `uv run pytest tests/test_motivation.py -q` → PASS (the module docstring "three" → "four").

- [ ] **Step 5: Commit** `feat(motivation): play more video games slide`.

### Task 4: Wire into the rotation and CLI

**Files:**
- Modify: `retro_pixoo/update.py`
- Modify: `tests/test_update.py`

**Interfaces:**
- Consumes: Task 1 (`newest_export`, `export_date`, `load_export`, `PosterCache`, `CACHE_PATH`, `SAMPLE_YEAR`, `load_sample_diary`), Task 2 `tag_frames`, Task 3 `SLIDES`.
- Produces: `collect_pages(..., tags: Callable[[], list[DiaryRow]] | None = None, posters: PosterCache | None = None, year: int | None = None)` — new keyword args after `bgg_thumbs`.

- [ ] **Step 1: Write failing tests:**

```python
def test_tag_pages_after_bgg(self):
    pages, errors = collect_pages(lambda: self.p, lambda: self.e, self.fetcher, bgg=lambda: self.plays,
                                  tags=load_sample_diary, posters=PosterCache(None), year=SAMPLE_YEAR)
    self.assertEqual(errors, []); self.assertEqual(len(pages), 20)
    want = tag_frames(load_sample_diary(), PosterCache(None).get, self.fetcher, SAMPLE_YEAR)
    for got, w in zip(pages[15:19], want): self.assertEqual(got.tobytes(), w.tobytes())
    self.assertEqual(pages[19].tobytes(), handhelds_frame().tobytes())

def test_tags_failure_reported(self):
    pages, errors = collect_pages(lambda: self.p, lambda: self.e, self.fetcher, bgg=lambda: self.plays,
                                  tags=_boom("no export"), posters=PosterCache(None), year=SAMPLE_YEAR)
    self.assertEqual(len(pages), 15); self.assertIn("letterboxd export: no export", errors)

def test_rss_posters_feed_the_cache(self):
    cache = PosterCache(None)
    collect_pages(_boom("x"), lambda: self.e, self.fetcher, tags=load_sample_diary, posters=cache, year=SAMPLE_YEAR)
    self.assertEqual(cache.get(self.e[0].title, self.e[0].year), self.e[0].poster_url)

def test_main_stale_export_warns(self):  # tempdir with letterboxd-kelsin13-2026-11-01-00-00-utc.zip (diary.csv inside),
    # patch update.date.today -> 2026-11-27, RA/BGG/RSS patched to samples; stderr contains "export is 26 days old"
```

- [ ] **Step 2: Run** `uv run pytest tests/test_update.py -q` → FAIL.

- [ ] **Step 3: Implement.** In `collect_pages`: if `posters` and `entries` → `posters.update(entries)`; after the BGG block, if `tags` is given, call it in try/except (`letterboxd export: ...`), and on success extend with `tag_frames(rows, posters.get if posters else (lambda t, y: ""), fetcher, year or date.today().year)` then `next(slides)()`. In `main`: add `--lb-export-dir` (`type=Path`, default `Path.home() / "Downloads"`). Sample mode → `tags=load_sample_diary`, `posters=PosterCache(None)`, `year=SAMPLE_YEAR`. Live mode → `posters=PosterCache(CACHE_PATH)`, `year=None`, and a `tags` closure that runs `newest_export`, computes `age = (date.today() - export_date(path)).days`, prints `letterboxd export: export is {age} days old (<name>)` to stderr when `age > 8`, and returns `load_export(path)`.

- [ ] **Step 4: Run** `uv run pytest -q` → all PASS; `uv run retro-pixoo-update --sample --preview preview` writes 20 pages.

- [ ] **Step 5: Commit** `feat(letterboxd): tag pages and handheld slide in the rotation`.

### Task 5: Weekly export agent and docs

**Files:**
- Create: `launchd/com.retro-pixoo.lb-export.plist.in`
- Modify: `Makefile`, `README.md`, `CLAUDE.md` ("Existing scripts" line mentions tag pages + export)

- [ ] **Step 1: Template.** Label `@EXPORT_LABEL@`, `ProgramArguments` `/usr/bin/open`, `https://letterboxd.com/data/export/`; `StartCalendarInterval` dict `Weekday 0, Hour 9, Minute 0`; no `RunAtLoad`; log to `@LOG@`.
- [ ] **Step 2: Makefile.** `EXPORT_LABEL := com.retro-pixoo.lb-export`, `EXPORT_PLIST := $(HOME)/Library/LaunchAgents/$(EXPORT_LABEL).plist`. `plist` also writes and lints it; `install` bootstraps both; `uninstall`/`reload` handle both (`-launchctl bootout` for each). New target `export: ## Download a Letterboxd export now` → `open https://letterboxd.com/data/export/`.
- [ ] **Step 3: README.** Under the launchd section: what the weekly job does, that the browser must stay logged in to Letterboxd, and the one-time **System Settings → Privacy & Security → Files and Folders → python3.13 → Downloads Folder** grant (background jobs can't read `~/Downloads` otherwise — update the existing note that says to keep the repo out of `~/Downloads`, which still holds for the repo itself). Mention the tag pages in the page list.
- [ ] **Step 4: Verify** without touching the user's installed agents: `make -n plist` shows both seds, and `make plist HOME=$(mktemp -d)` → both `plutil -lint` OK. Never run `make plist`/`install`/`reload`/`uninstall` with the real `HOME`.
- [ ] **Step 5: Commit** `feat(letterboxd): weekly export launchd agent`.
