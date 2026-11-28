"""Pages showing this year's count and latest film for a Letterboxd diary tag."""

from __future__ import annotations

from typing import Callable

from PIL import Image

from . import font
from .lb_export import DiaryRow, TagSummary, summarize
from .ra import ImageFetcher
from .render import (
    BG,
    CYAN,
    GREY,
    LB_GREEN,
    LB_ORANGE,
    RED,
    SIZE,
    WHITE,
    _header,
    _placeholder,
    _stars,
    _watched_date,
)

TAGS = (
    ("FRIDA", "theater:frida", LB_ORANGE),
    ("REGAL", "theater:regal", CYAN),
    ("KERRIGAN", "people:kerrigan", LB_GREEN),
    ("CAITLIN", "people:caitlin", RED),
)


def _poster(fetcher: ImageFetcher, url: str, key: str) -> Image.Image:
    img = fetcher.get(url) if url else None
    if img is None:
        return _placeholder(key, 28).resize((28, 42), Image.NEAREST)
    return img.resize((28, 42), Image.LANCZOS)


def tag_frame(
    name: str, color, summary: TagSummary, year: int, poster_url: str, fetcher: ImageFetcher
) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    _header(img, name)
    latest = summary.latest
    key = latest.name if latest else name
    img.paste(_poster(fetcher, poster_url, key), (1, 9))
    font.draw_text(img, 32, 10, str(summary.count), color, scale=2)
    font.draw_text(img, 32, 22, f"IN {year}", GREY)
    if latest is None:
        font.draw_text(img, 1, 52, "NONE YET", GREY)
        return img
    when = _watched_date(latest.watched)
    if when:
        font.draw_text(img, 32, 37, when, WHITE)
    _stars(img, 32, 44, latest.rating)
    y = 52
    for line in font.wrap(latest.name, 62, 2):
        font.draw_text(img, 1, y, line, WHITE)
        y += 6
    return img


def tag_frames(
    rows: list[DiaryRow],
    poster_for: Callable[[str, int | None], str],
    fetcher: ImageFetcher,
    year: int,
) -> list[Image.Image]:
    out = []
    for name, tag, color in TAGS:
        s = summarize(rows, tag, year)
        url = poster_for(s.latest.name, s.latest.year) if s.latest else ""
        out.append(tag_frame(name, color, s, year, url, fetcher))
    return out
