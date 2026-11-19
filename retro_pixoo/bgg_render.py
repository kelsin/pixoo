"""BoardGameGeek pages: H-index, recent plays, most played games, yearly stats."""

from __future__ import annotations

from datetime import date

from PIL import Image, ImageDraw

from . import font
from .bgg import Play, _counts_with_ids, game_counts, h_index, h_next, h_targets, top_played
from .render import BG, CYAN, DIM, GOLD, GREY, SIZE, WHITE, _bar, _header


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


def bgg_h_frame(plays: list[Play], today: date | None = None) -> Image.Image:
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
    if first:
        name = font.fit(first, 60)
        font.draw_text(img, (SIZE - font.text_width(name)) // 2, 47, name, GREY)
    return img


def bgg_recent_frame(plays: list[Play], today: date | None = None, count: int = 4) -> Image.Image:
    today = today or date.today()
    plays = _year_plays(plays, today)
    img, _ = _blank("RECENT PLAYS", plays)
    recent = sorted(plays, key=lambda p: p.date, reverse=True)[:count]
    for i, p in enumerate(recent):
        y = 10 + i * 8
        when = f"{p.date[5:7]}/{p.date[8:10]}"
        wx = 62 - font.text_width(when)
        font.draw_text(img, wx, y, when, GREY)
        suffix = f" X{p.quantity}" if p.quantity > 1 else ""
        name = font.fit(p.game, wx - 5 - font.text_width(suffix)) + suffix
        font.draw_text(img, 2, y, name, WHITE)
    return img


def bgg_top_frame(plays: list[Play], today: date | None = None) -> Image.Image:
    today = today or date.today()
    plays = _year_plays(plays, today)
    img, d = _blank("TOP PLAYED", plays)
    rows = top_played(plays, 5)
    if not rows:
        return img
    peak = rows[0][1]
    for i, (name, n) in enumerate(rows):
        y = 9 + i * 11
        count = str(n)
        cx = 62 - font.text_width(count)
        font.draw_text(img, 1, y, str(i + 1), GOLD)
        font.draw_text(img, 7, y, font.fit(name, cx - 9), WHITE)
        font.draw_text(img, cx, y, count, CYAN)
        _bar(d, 7, y + 6, 55, 2, n / peak, GOLD if i == 0 else CYAN)
    return img


def bgg_stats_frame(plays: list[Play], today: date | None = None) -> Image.Image:
    today = today or date.today()
    plays = _year_plays(plays, today)
    img, d = _blank(f"{today.year} STATS", plays)
    if not plays:
        return img

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
