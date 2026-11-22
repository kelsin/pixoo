"""Render RetroAchievements and Letterboxd data into 64x64 frames for the Pixoo-64.

Pages:
  profile_frame      - avatar, name, time since last played, points, rank, last game progress
  recent_frame       - the four most recent unlocks: badge, title, points and game
  last_watched_frame - latest Letterboxd diary film: poster, title, year, rating
  diary_frame        - the next four diary films as small posters with ratings
  month_stats_frame  - this month's film count, days watched, likes, rewatches, average rating, films-per-day chart
  watch_calendar_frame - this month as a calendar grid, lit on the days films were watched
  decades_frame      - films per release decade as horizontal bars
  top_rated_frame    - the highest rated diary films as small posters
  recent_games_frame - the four most recently played games with their completion
  systems_frame      - top four RetroAchievements systems by recently played games
"""

from __future__ import annotations

import calendar
import hashlib
from collections import Counter
from datetime import date, datetime, timezone

from PIL import Image, ImageDraw

from . import font
from .letterboxd import DiaryEntry
from .ra import ImageFetcher, Profile

SIZE = 64

BG = (0, 0, 0)
WHITE = (235, 235, 235)
GREY = (110, 115, 125)
DIM = (45, 48, 56)
GOLD = (255, 196, 40)
CYAN = (60, 200, 240)
HEADER = (24, 26, 40)
BAR_BG = (40, 40, 50)
RED = (230, 60, 80)
DIM_GOLD = (90, 68, 14)
LB_GREEN = (0, 224, 84)
LB_ORANGE = (255, 128, 0)
LB_BLUE = (64, 188, 244)
DAY_COLORS = {1: CYAN, 2: LB_GREEN, 3: GOLD, 4: LB_ORANGE, 5: RED}  # films per day, 5 = 5+

_STAR = ("..#..", "#.#.#", ".###.", "#.#.#", "..#..")
_HEART = (".#.#.", "#####", "#####", ".###.", "..#..")
_REWATCH = (".###.#", "#...##", "#..###", "#.....", ".####.")


def _placeholder(key: str, size: int) -> Image.Image:
    """A symmetric pixel 'identicon' used when an image can't be downloaded."""
    h = hashlib.md5(key.encode()).digest()
    color = (80 + h[0] % 176, 80 + h[1] % 176, 80 + h[2] % 176)
    cells = 5
    small = Image.new("RGB", (cells, cells), (20, 20, 28))
    px = small.load()
    for y in range(cells):
        for x in range(3):
            if (h[3 + y] >> x) & 1:
                px[x, y] = color
                px[cells - 1 - x, y] = color
    return small.resize((size, size), Image.NEAREST)


def _icon(fetcher: ImageFetcher, url: str, size: int) -> Image.Image:
    img = fetcher.get(url)
    if img is None:
        return _placeholder(url or "none", size)
    # Downscale with a smooth filter: badges are 64x64 art, avatars 128x128.
    return img.resize((size, size), Image.LANCZOS)


def _bar(d: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, frac: float, color) -> None:
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=BAR_BG)
    fill = round(w * max(0.0, min(1.0, frac)))
    if fill:
        d.rectangle([x, y, x + fill - 1, y + h - 1], fill=color)


def _compact(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 100_000:
        return f"{n // 1000}K"
    return str(n)


def _played_ago(ts: str, now: datetime) -> str | None:
    """'2026-11-17 21:04:11' (UTC) -> '2H AGO'; None if it can't be parsed."""
    try:
        then = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    secs = int((now - then).total_seconds())
    if secs < 60:
        return "JUST NOW"
    if secs < 3600:
        return f"{secs // 60}M AGO"
    if secs < 86400:
        return f"{secs // 3600}H AGO"
    return f"{secs // 86400}D AGO"


def profile_frame(p: Profile, fetcher: ImageFetcher, now: datetime | None = None) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)

    # Header: 16x16 avatar, name, time since last played
    d.rectangle([0, 0, 63, 17], fill=HEADER)
    img.paste(_icon(fetcher, p.avatar_url, 16), (1, 1))
    font.draw_text(img, 20, 3, font.fit(p.user, 43), WHITE)
    ago = _played_ago(p.last_played, now or datetime.now(timezone.utc))
    if ago:
        font.draw_text(img, 20, 10, ago, GREY)

    # Points, large
    font.draw_text(img, 2, 21, "POINTS", GREY)
    pts = _compact(p.points or p.softcore_points)  # hardcore, else softcore
    scale = 2 if font.text_width(pts, 2) <= 60 else 1
    font.draw_text(img, 2, 28, pts, GOLD, scale=scale)

    # Rank
    if p.rank:
        rank_txt = f"#{p.rank}"
        font.draw_text(img, 2, 40, font.fit(rank_txt, 34), WHITE)
        top = p.top_percent
        if top is not None:
            pct = f"TOP {top:.0f}%" if top >= 10 else f"TOP {top:.1f}%"
            font.draw_text(img, 62 - font.text_width(pct), 40, pct, CYAN)
    else:
        font.draw_text(img, 2, 40, "UNRANKED", GREY)

    # Last game: icon, title, progress bar
    d.line([0, 47, 63, 47], fill=DIM)
    g = p.last_game
    if g:
        img.paste(_icon(fetcher, g.icon_url, 14), (1, 49))
        font.draw_text(img, 17, 50, font.fit(g.title, 46), WHITE)
        frac = g.achieved / g.possible if g.possible else 0
        _bar(d, 17, 56, 46, 2, frac, GOLD if frac >= 1 else CYAN)
        font.draw_text(img, 17, 59, f"{g.achieved}/{g.possible}", GREY)
        pct = f"{frac * 100:.0f}%"
        font.draw_text(img, 63 - font.text_width(pct), 59, pct, GOLD if frac >= 1 else CYAN)
    else:
        font.draw_text(img, 2, 52, "NO RECENT GAME", GREY)
    return img


def recent_frame(p: Profile, fetcher: ImageFetcher, count: int = 4) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    _header(img, "RECENT UNLOCKS")

    if not p.recent:
        font.draw_text(img, 2, 28, "NONE YET", GREY)
        return img

    for i, a in enumerate(p.recent[:count]):
        y = 8 + i * 14
        img.paste(_icon(fetcher, a.badge_url, 12), (1, y))
        font.draw_text(img, 15, y, font.fit(a.title, 48), WHITE)
        # points in gold for hardcore, grey for softcore, then the game name
        pts = str(a.points)
        font.draw_text(img, 15, y + 6, pts, GOLD if a.hardcore else GREY)
        gx = 15 + font.text_width(pts) + 3
        font.draw_text(img, gx, y + 6, font.fit(a.game_title, 64 - gx), GREY)
    return img


def _glyph(img: Image.Image, x: int, y: int, rows: tuple[str, ...], color, cols: int | None = None) -> None:
    px = img.load()
    for gy, row in enumerate(rows):
        for gx, bit in enumerate(row[:cols]):
            if bit == "#" and 0 <= x + gx < SIZE and 0 <= y + gy < SIZE:
                px[x + gx, y + gy] = color


def _stars(img: Image.Image, x: int, y: int, rating: float | None, color=GOLD, small: bool = False) -> int:
    """Draw a star rating; returns the width drawn (0 when unrated).

    Large stars are 5x5 glyphs on a 6px advance; small ones are 2x2 dots on a
    3px advance so five fit in 14px. A small half star is the dot's left column;
    a large one is a dim star with its left three columns lit.
    """
    if rating is None:
        return 0
    full, half = int(rating), rating % 1 >= 0.5
    adv, half_w = (3, 1) if small else (6, 5)
    d = ImageDraw.Draw(img)
    for i in range(full + half):
        sx = x + i * adv
        if small:
            d.rectangle([sx, y, sx + (half_w - 1 if i == full else 1), y + 1], fill=color)
        elif i == full:
            _glyph(img, sx, y, _STAR, DIM_GOLD)
            _glyph(img, sx, y, _STAR, color, cols=3)
        else:
            _glyph(img, sx, y, _STAR, color)
    if full + half == 0:
        return 0
    return full * adv + half_w if half else full * adv - 1


def _poster(fetcher: ImageFetcher, e: DiaryEntry, w: int, h: int) -> Image.Image:
    img = fetcher.get(e.poster_url)
    if img is None:
        return _placeholder(e.title, w).resize((w, h), Image.NEAREST)
    return img.resize((w, h), Image.LANCZOS)


def _watched_date(s: str) -> str | None:
    """'2026-11-16' -> 'NOV 16'; None if it can't be parsed."""
    try:
        d = date.fromisoformat(s)
    except ValueError:
        return None
    return f"{d.strftime('%b').upper()} {d.day}"


def _header(img: Image.Image, title: str) -> None:
    ImageDraw.Draw(img).rectangle([0, 0, 63, 6], fill=HEADER)
    font.draw_text(img, 2, 1, title, GOLD)


def last_watched_frame(entries: list[DiaryEntry], fetcher: ImageFetcher) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    _header(img, "LAST WATCHED")
    if not entries:
        font.draw_text(img, 2, 28, "NO FILMS", GREY)
        return img

    e = entries[0]
    img.paste(_poster(fetcher, e, 28, 42), (1, 9))
    y = 9
    for line in font.wrap(e.title, 31, 4):
        font.draw_text(img, 32, y, line, WHITE)
        y += 6
    if e.year:
        font.draw_text(img, 32, y + 1, str(e.year), GREY)
        y += 7
    if _stars(img, 32, y + 1, e.rating):
        y += 7
    x = 32
    if e.liked:
        _glyph(img, x, y + 1, _HEART, RED)
        x += 7
    if e.rewatch:
        _glyph(img, x, y + 1, _REWATCH, CYAN)
    when = _watched_date(e.watched_date)
    if when:
        font.draw_text(img, 1, 56, f"WATCHED {when}", GREY)
    return img


def diary_frame(entries: list[DiaryEntry], fetcher: ImageFetcher, count: int = 4) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    _header(img, "RECENT DIARY")
    if not entries:
        font.draw_text(img, 2, 28, "NO FILMS", GREY)
        return img
    films = entries[1 : 1 + count]
    if not films:
        font.draw_text(img, 2, 28, "NO MORE FILMS", GREY)
        return img

    for i, e in enumerate(films):
        x = i * 16
        img.paste(_poster(fetcher, e, 15, 22), (x, 9))
        _stars(img, x, 33, e.rating, small=True)
        # Numbered title list below the posters, counting on from the last watched film (#1).
        ty = 37 + i * 6
        font.draw_text(img, 1, ty, str(i + 2), GOLD)
        font.draw_text(img, 7, ty, font.fit(e.title, 57), WHITE)
    return img


def _parse_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def month_entries(entries: list[DiaryEntry], today: date) -> list[tuple[date, DiaryEntry]]:
    """Entries watched in today's year and month, paired with their parsed date."""
    out = []
    for e in entries:
        d = _parse_date(e.watched_date)
        if d and (d.year, d.month) == (today.year, today.month):
            out.append((d, e))
    return out


def films_per_day(entries: list[DiaryEntry], today: date) -> list[int]:
    """Films watched on each day of today's month, index 0 = the 1st."""
    counts = [0] * calendar.monthrange(today.year, today.month)[1]
    for d, _ in month_entries(entries, today):
        counts[d.day - 1] += 1
    return counts


def decade_counts(entries: list[DiaryEntry], max_rows: int = 9) -> list[tuple[int, int]]:
    """(decade, films) in chronological order, keeping only the max_rows most common decades."""
    counts = Counter(e.year // 10 * 10 for e in entries if e.year)
    top = sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0]))[:max_rows]
    return sorted(top)


def top_rated(entries: list[DiaryEntry], limit: int = 8) -> list[DiaryEntry]:
    """Rated films, one per (title, year), best first; ties stay newest first."""
    seen: set[tuple[str, int | None]] = set()
    rated = []
    for e in entries:
        key = (e.title, e.year)
        if e.rating is None or key in seen:
            continue
        seen.add(key)
        rated.append(e)
    rated.sort(key=lambda e: -e.rating)
    return rated[:limit]


def day_colors(per_day: list[int]) -> list[tuple[int, int, int] | None]:
    """Colour per day by absolute film count (1-4, 5+); None for empty days. Within a run of
    consecutive same-colour days every second one is darker."""
    out, prev, run = [], 0, 0
    for n in per_day:
        key = min(n, 5)
        run = run + 1 if key and key == prev else 0
        prev = key
        if not key:
            out.append(None)
        else:
            base = DAY_COLORS[key]
            out.append(base if run % 2 == 0 else tuple(c * 6 // 10 for c in base))
    return out


def month_stats_frame(entries: list[DiaryEntry], today: date | None = None) -> Image.Image:
    today = today or date.today()
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    _header(img, today.strftime("%B").upper())
    films = [e for _, e in month_entries(entries, today)]
    if not films:
        font.draw_text(img, 2, 28, "NO FILMS", GREY)
        return img

    days = sum(1 for n in films_per_day(entries, today) if n)
    total = calendar.monthrange(today.year, today.month)[1]
    font.draw_text(img, 2, 9, f"{len(films)} FILMS", WHITE)
    span = f"{days}/{total}D"
    font.draw_text(img, 62 - font.text_width(span), 9, span, LB_GREEN)
    liked = sum(e.liked for e in films)
    rewatched = sum(e.rewatch for e in films)
    _glyph(img, 2, 16, _HEART, RED)
    font.draw_text(img, 9, 16, str(liked), WHITE)
    _glyph(img, 24, 16, _REWATCH, CYAN)
    font.draw_text(img, 32, 16, str(rewatched), WHITE)
    rated = [e.rating for e in films if e.rating is not None]
    if rated:
        avg = f"{sum(rated) / len(rated):.1f}"
        _glyph(img, 57, 16, _STAR, GOLD)
        font.draw_text(img, 55 - font.text_width(avg), 16, avg, GOLD)

    # Films per day: 2px bars centred in the 64px width, tallest day fills the chart.
    per_day = films_per_day(entries, today)
    peak = max(per_day) or 1
    x0 = (SIZE - 2 * len(per_day)) // 2
    for i, (n, color) in enumerate(zip(per_day, day_colors(per_day))):
        x = x0 + i * 2
        if n:
            h = max(1, round(33 * n / peak))
            d.rectangle([x, 57 - h + 1, x + 1, 57], fill=color)
        else:
            d.rectangle([x, 57, x + 1, 57], fill=DIM)
    font.draw_text(img, x0, 59, "1", GREY)
    last = str(len(per_day))
    font.draw_text(img, x0 + len(per_day) * 2 - font.text_width(last), 59, last, GREY)
    return img


def watch_calendar_frame(entries: list[DiaryEntry], today: date | None = None) -> Image.Image:
    today = today or date.today()
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    watched = month_entries(entries, today)
    _header(img, today.strftime("%b").upper())
    n = str(len(watched))
    font.draw_text(img, 62 - font.text_width(n), 1, n, WHITE)
    if not watched:
        font.draw_text(img, 2, 28, "NO FILMS", GREY)
        return img

    for c, letter in enumerate("SMTWTFS"):
        font.draw_text(img, c * 9 + 2, 8, letter, GREY)
    colors = day_colors(films_per_day(entries, today))
    first_col = (today.replace(day=1).weekday() + 1) % 7  # Sunday first
    for day in range(1, calendar.monthrange(today.year, today.month)[1] + 1):
        row, col = divmod(first_col + day - 1, 7)
        x, y = col * 9, 14 + row * 8
        label = str(day)
        tx = x + (8 - font.text_width(label)) // 2
        if day > today.day:
            font.draw_text(img, tx, y + 1, label, DIM)
            continue
        fill = colors[day - 1]
        fill, ink = (DIM, GREY) if fill is None else (fill, BG)
        d.rectangle([x, y, x + 7, y + 6], fill=fill)
        font.draw_text(img, tx, y + 1, label, ink)
        if day == today.day:
            d.line([x, y + 7, x + 7, y + 7], fill=WHITE)  # underline: the row below the cell is free
    return img


def decades_frame(entries: list[DiaryEntry]) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    _header(img, "DECADES")
    rows = decade_counts(entries)
    if not rows:
        font.draw_text(img, 2, 28, "NO FILMS", GREY)
        return img

    peak = max(n for _, n in rows)
    for i, (decade, n) in enumerate(rows):
        y = 9 + i * 6
        font.draw_text(img, 1, y, f"{decade % 100:02d}S", GREY)
        w = max(1, round(40 * n / peak))
        d.rectangle([14, y, 14 + w - 1, y + 4], fill=LB_BLUE if n == peak else LB_ORANGE)
        font.draw_text(img, 14 + w + 2, y, str(n), WHITE)
    return img


def top_rated_frame(entries: list[DiaryEntry], fetcher: ImageFetcher) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    _header(img, "TOP RATED")
    films = top_rated(entries)
    if not films:
        font.draw_text(img, 2, 28, "NO FILMS", GREY)
        return img

    for i, e in enumerate(films):
        x, y = (i % 4) * 16, 9 if i < 4 else 35
        img.paste(_poster(fetcher, e, 15, 22), (x, y))
        _stars(img, x, y + 24, e.rating, small=True)
    return img


_SYSTEM_TAGS: dict[str, tuple[str, tuple[int, int, int]]] = {
    "NES/Famicom": ("NES", (230, 70, 70)),
    "SNES/Super Famicom": ("SNES", (170, 140, 230)),
    "Nintendo 64": ("N64", (80, 200, 110)),
    "GameCube": ("GC", (150, 120, 240)),
    "Game Boy": ("GB", (150, 200, 90)),
    "Game Boy Color": ("GBC", (240, 130, 200)),
    "Game Boy Advance": ("GBA", (110, 140, 240)),
    "Nintendo DS": ("DS", (200, 205, 215)),
    "Genesis/Mega Drive": ("GEN", (70, 130, 240)),
    "Master System": ("SMS", (240, 90, 90)),
    "Saturn": ("SAT", (90, 190, 220)),
    "Dreamcast": ("DC", (240, 150, 60)),
    "Game Gear": ("GG", (80, 120, 220)),
    "PlayStation": ("PS1", (200, 205, 215)),
    "PlayStation 2": ("PS2", (90, 150, 240)),
    "PlayStation Portable": ("PSP", (130, 140, 230)),
    "PC Engine/TurboGrafx-16": ("PCE", (240, 170, 60)),
    "Atari 2600": ("2600", (230, 140, 70)),
    "Arcade": ("ARC", (240, 210, 70)),
    "Sega CD": ("SCD", (120, 170, 240)),
    "32X": ("32X", (240, 120, 120)),
    "PC Engine CD/TurboGrafx-CD": ("PCCD", (240, 190, 90)),
    "Atari 7800": ("7800", (230, 150, 100)),
    "Atari Lynx": ("LYNX", (240, 180, 80)),
    "Atari Jaguar": ("JAG", (230, 90, 90)),
    "Virtual Boy": ("VB", (240, 80, 80)),
    "Nintendo DSi": ("DSI", (110, 210, 230)),
    "Neo Geo Pocket": ("NGP", (200, 160, 240)),
    "WonderSwan": ("WS", (120, 200, 200)),
    "MSX": ("MSX", (150, 210, 130)),
}


def system_tag(console: str) -> tuple[str, tuple[int, int, int]]:
    """Short label and color for an RA console name; unknown consoles get grey and the first 4 letters/digits."""
    return _SYSTEM_TAGS.get(console) or ("".join(c for c in console if c.isalnum())[:4].upper(), GREY)


def systems_frame(p: Profile, fetcher: ImageFetcher) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    _header(img, "TOP SYSTEMS")
    if not p.systems:
        font.draw_text(img, 2, 28, "NO GAMES", GREY)
        return img

    for i, s in enumerate(p.systems[:4]):
        x, y = (i % 2) * 32, 8 + (i // 2) * 28
        img.paste(_icon(fetcher, s.icon_url, 16), (x + 1, y + 1))

        n = str(s.games)
        scale, ny = (2, y + 4) if font.text_width(n, 2) <= 14 else (1, y + 7)
        font.draw_text(img, x + 18 + (14 - font.text_width(n, scale)) // 2, ny, n, WHITE, scale=scale)

        tag, color = system_tag(s.console)
        d.rectangle([x + 1, y + 19, x + 16, y + 25], fill=color)
        font.draw_text(img, x + 1 + (16 - font.text_width(tag)) // 2 + 1, y + 20, tag, BG)

        ach = str(s.achievements) if s.achievements < 1000 else f"{s.achievements // 1000}K"
        font.draw_text(img, x + 19, y + 20, ach, GOLD)
    return img


def recent_games_frame(p: Profile, fetcher: ImageFetcher) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    _header(img, "RECENT GAMES")
    if not p.games:
        font.draw_text(img, 2, 28, "NO GAMES", GREY)
        return img

    for i, g in enumerate(p.games[:4]):
        y = 8 + i * 14
        frac = g.achieved / g.possible if g.possible else 0
        color = GOLD if frac >= 1 else CYAN
        img.paste(_icon(fetcher, g.icon_url, 12), (1, y))
        font.draw_text(img, 15, y, font.fit(g.title, 48), WHITE)
        _bar(d, 15, y + 7, 30, 3, frac, color)
        pct = f"{frac * 100:.0f}%"
        font.draw_text(img, 63 - font.text_width(pct), y + 6, pct, color)
    return img


def frames(p: Profile, fetcher: ImageFetcher) -> list[Image.Image]:
    return [profile_frame(p, fetcher), recent_frame(p, fetcher), recent_games_frame(p, fetcher),
            systems_frame(p, fetcher)]


def led_preview(frame: Image.Image, scale: int = 8, gap: int = 1) -> Image.Image:
    """Upscale a 64x64 frame with dark gaps between pixels so it looks like the LED panel."""
    big = frame.resize((SIZE * scale, SIZE * scale), Image.NEAREST)
    d = ImageDraw.Draw(big)
    for i in range(0, SIZE * scale, scale):
        d.rectangle([i, 0, i + gap - 1, SIZE * scale], fill=(8, 8, 10))
        d.rectangle([0, i, SIZE * scale, i + gap - 1], fill=(8, 8, 10))
    return big
