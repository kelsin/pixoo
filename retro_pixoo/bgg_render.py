"""BoardGameGeek pages: H-index, recent plays, most played games, yearly stats."""

from __future__ import annotations

from datetime import date

from PIL import Image, ImageDraw

from . import font
from .bgg import Play, _counts_with_ids, game_counts, h_index, h_next, h_targets
from .ra import ImageFetcher
from .render import BG, CYAN, DIM, GOLD, GREY, SIZE, WHITE, _bar, _header, _placeholder


def _year_plays(plays: list[Play], today: date) -> list[Play]:
    prefix = f"{today.year}-"
    return [p for p in plays if p.date.startswith(prefix)]


def recent_games(plays: list[Play], today: date, count: int = 4) -> list[tuple[int, str]]:
    plays = _year_plays(plays, today)
    recent = sorted(plays, key=lambda p: p.date, reverse=True)[:count]
    return [(p.game_id, p.game) for p in recent]


def top_games(plays: list[Play], today: date, n: int = 5) -> list[tuple[int, str]]:
    return [(gid, name) for gid, name, _ in _counts_with_ids(_year_plays(plays, today))[:n]]


def h_games(plays: list[Play], today: date, limit: int = 4) -> list[tuple[int, str]]:
    return h_targets(_year_plays(plays, today), limit)


def stats_game(plays: list[Play], today: date) -> list[tuple[int, str]]:
    return top_games(plays, today, 1)


def needed_games(
    plays: list[Play], pages: tuple[str, ...], today: date | None = None
) -> list[tuple[int, str]]:
    today = today or date.today()
    pickers = {"h": h_games, "recent": recent_games, "top": top_games, "stats": stats_game}
    seen: dict[int, str] = {}
    for page in pages:
        pick = pickers.get(page)
        for gid, name in pick(plays, today) if pick else []:
            seen.setdefault(gid, name)
    return list(seen.items())


def _blank(title: str, plays: list[Play]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    _header(img, title)
    if not plays:
        font.draw_text(img, 2, 28, "NO PLAYS", GREY)
    return img, ImageDraw.Draw(img)


def _game_icon(
    fetcher: ImageFetcher | None, thumbs: dict[int, str] | None, game_id: int, name: str, size: int
) -> Image.Image:
    """Square game thumbnail (center-cropped); identicon when there is no image."""
    url = (thumbs or {}).get(game_id)
    img = fetcher.get(url) if fetcher is not None and url else None
    if img is None:
        return _placeholder(name, size)
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    return img.resize((size, size), Image.LANCZOS)


def _wrap(text: str, width: int, max_lines: int) -> list[str]:
    """Greedy word wrap into at most max_lines; the last line is truncated to fit."""
    words = font.normalize(text).split()
    lines: list[str] = []
    cur = ""
    for i, word in enumerate(words):
        trial = f"{cur} {word}" if cur else word
        if font.text_width(trial) <= width or not cur:
            cur = trial
            continue
        lines.append(cur)
        cur = word
        if len(lines) == max_lines - 1:
            cur = " ".join(words[i:])
            break
    if cur:
        lines.append(cur)
    lines = lines[:max_lines]
    if lines:
        lines[-1] = font.fit(lines[-1], width).rstrip()
    return lines


def _pip_layout(count: int, x0: int, width: int) -> list[tuple[int, int]]:
    """(x, w) per pip, 1px gaps, spread so the row spans exactly width px."""
    gap = 1 if 2 * count - 1 <= width else 0
    count = min(count, width)
    avail = width - gap * (count - 1)
    base, extra = divmod(avail, count)
    pips, x = [], x0
    for i in range(count):
        w = base + (1 if i < extra else 0)
        pips.append((x, w))
        x += w + gap
    return pips


def bgg_h_frame(
    plays: list[Play], today: date | None = None,
    thumbs: dict[int, str] | None = None, fetcher: ImageFetcher | None = None,
) -> Image.Image:
    today = today or date.today()
    plays = _year_plays(plays, today)
    img, d = _blank(f"H-INDEX {today.year}", plays)
    if not plays:
        return img

    h, extra, first = h_next(plays)
    need = h + 1
    scale = 3 if h < 10 else 2
    font.draw_text(img, 3, 11 + (15 - 5 * scale) // 2, f"H{h}", GOLD, scale=scale)
    font.draw_text(img, 32, 13, f"NEXT H{need}", CYAN)
    font.draw_text(img, 32, 21, f"{extra} MORE", WHITE)

    done = sum(min(n, need) for _, n in game_counts(plays)[:need])
    _bar(d, 4, 32, 56, 3, done / (need * need), CYAN)

    games = h_games(plays, today)
    if games:
        gid, name = games[0]
        n = next(c for g, _, c in _counts_with_ids(plays) if g == gid)
        img.paste(_game_icon(fetcher, thumbs, gid, name, 18), (2, 38))
        lines = _wrap(name, 40, 2)
        for i, line in enumerate(lines):
            font.draw_text(img, 23, 38 + i * 7, line, WHITE)
        font.draw_text(img, 23, 38 + len(lines) * 7, f"{n}/{need}", GOLD)
        for i, (x, w) in enumerate(_pip_layout(need, 2, 60)):
            d.rectangle([x, 59, x + w - 1, 61], fill=GOLD if i < n else DIM)
    elif first:
        font.draw_text(img, 2, 40, font.fit(first, 60), GREY)
    return img


def bgg_recent_frame(
    plays: list[Play], today: date | None = None, count: int = 4,
    thumbs: dict[int, str] | None = None, fetcher: ImageFetcher | None = None,
) -> Image.Image:
    today = today or date.today()
    plays = _year_plays(plays, today)
    img, _ = _blank("RECENT PLAYS", plays)
    recent = sorted(plays, key=lambda p: p.date, reverse=True)[:count]
    for i, p in enumerate(recent):
        y = 10 + i * 13
        img.paste(_game_icon(fetcher, thumbs, p.game_id, p.game, 12), (1, y))
        suffix = f" X{p.quantity}" if p.quantity > 1 else ""
        name = font.fit(p.game, 62 - 15 - font.text_width(suffix)) + suffix
        font.draw_text(img, 15, y, name, WHITE)
        font.draw_text(img, 15, y + 6, f"{p.date[5:7]}/{p.date[8:10]}", GREY)
    return img


def bgg_top_frame(
    plays: list[Play], today: date | None = None,
    thumbs: dict[int, str] | None = None, fetcher: ImageFetcher | None = None,
) -> Image.Image:
    today = today or date.today()
    plays = _year_plays(plays, today)
    img, d = _blank("TOP PLAYED", plays)
    rows = _counts_with_ids(plays)[:5]
    if not rows:
        return img
    peak = rows[0][2]
    for i, (gid, name, n) in enumerate(rows):
        y = 9 + i * 11
        count = str(n)
        cx = 62 - font.text_width(count)
        img.paste(_game_icon(fetcher, thumbs, gid, name, 10), (1, y))
        font.draw_text(img, 12, y, str(i + 1), GOLD)
        font.draw_text(img, 17, y, font.fit(name, cx - 19), WHITE)
        font.draw_text(img, cx, y, count, CYAN)
        _bar(d, 12, y + 6, 50, 2, n / peak, GOLD if i == 0 else CYAN)
    return img


def bgg_stats_frame(
    plays: list[Play], today: date | None = None,
    thumbs: dict[int, str] | None = None, fetcher: ImageFetcher | None = None,
) -> Image.Image:
    today = today or date.today()
    plays = _year_plays(plays, today)
    img, d = _blank(f"{today.year} STATS", plays)
    if not plays:
        return img

    for gid, name in stats_game(plays, today):
        img.paste(_game_icon(fetcher, thumbs, gid, name, 20), (43, 9))
    total = sum(p.quantity for p in plays)
    games = len({p.game_id for p in plays})
    font.draw_text(img, 2, 9, f"PLAYS {total}", WHITE)
    font.draw_text(img, 2, 16, f"GAMES {games}", WHITE)
    minutes = sum(p.minutes * p.quantity for p in plays)
    if minutes > 0:
        font.draw_text(img, 2, 23, f"HOURS {round(minutes / 60)}", GOLD)

    per_month = [0] * 12
    for p in plays:
        try:
            per_month[int(p.date[5:7]) - 1] += p.quantity
        except ValueError:
            pass
    peak = max(per_month) or 1
    for i, n in enumerate(per_month):
        x = 2 + i * 5
        if n:
            h = max(1, round(28 * n / peak))
            d.rectangle([x, 60 - h + 1, x + 3, 60], fill=GOLD if i + 1 == today.month else CYAN)
        else:
            d.rectangle([x, 60, x + 3, 60], fill=DIM)
    return img
