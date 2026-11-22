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


def _recent_groups(plays: list[Play], count: int) -> list[tuple[Play, int]]:
    """Newest play of each of the last `count` distinct games, with that game's play total
    since the oldest of them (so a repeat shows as one row with a count)."""
    newest: dict[int, Play] = {}
    for p in sorted(plays, key=lambda p: p.date, reverse=True):
        newest.setdefault(p.game_id, p)
    shown = list(newest.values())[:count]
    if not shown:
        return []
    cutoff = shown[-1].date
    totals: dict[int, int] = {}
    for p in plays:
        if p.date >= cutoff:
            totals[p.game_id] = totals.get(p.game_id, 0) + p.quantity
    return [(p, totals[p.game_id]) for p in shown]


def recent_games(plays: list[Play], today: date, count: int = 4) -> list[tuple[int, str]]:
    return [(p.game_id, p.game) for p, _ in _recent_groups(_year_plays(plays, today), count)]


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
    label = f"H {h}"  # the bitmap font has no "=" glyph
    font.draw_text(img, (SIZE - font.text_width(label, 3)) // 2, 11, label, GOLD, scale=3)

    need = h + 1
    done = sum(min(n, need) for _, n in game_counts(plays)[:need])
    _bar(d, 4, 30, 56, 5, done / (need * need), CYAN)

    line = f"{extra} MORE PLAYS"
    font.draw_text(img, (SIZE - font.text_width(line)) // 2, 39, line, WHITE)
    games = h_games(plays, today)
    if games:
        n = len(games)
        x0 = (SIZE - (n * 14 + (n - 1) * 2)) // 2
        for i, (gid, name) in enumerate(games):
            img.paste(_game_icon(fetcher, thumbs, gid, name, 14), (x0 + i * 16, 48))
    elif first:
        name = font.fit(first, 60)
        font.draw_text(img, (SIZE - font.text_width(name)) // 2, 47, name, GREY)
    return img


def bgg_recent_frame(
    plays: list[Play], today: date | None = None, count: int = 4,
    thumbs: dict[int, str] | None = None, fetcher: ImageFetcher | None = None,
) -> Image.Image:
    today = today or date.today()
    plays = _year_plays(plays, today)
    img, _ = _blank("RECENT PLAYS", plays)
    for i, (p, n) in enumerate(_recent_groups(plays, count)):
        y = 10 + i * 13
        img.paste(_game_icon(fetcher, thumbs, p.game_id, p.game, 12), (1, y))
        font.draw_text(img, 15, y, font.fit(p.game, 47), WHITE)
        x = font.draw_text(img, 15, y + 6, f"{p.date[5:7]}/{p.date[8:10]}", GREY)
        if n > 1:
            font.draw_text(img, x + 1, y + 6, f"{n}X", CYAN)
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
