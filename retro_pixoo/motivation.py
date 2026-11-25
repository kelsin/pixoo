"""Static motivational slides: three 64x64 frames for the page rotation."""
from __future__ import annotations

from typing import Callable

from PIL import Image, ImageDraw

from . import font
from .render import BG, CYAN, DIM, GOLD, GREY, LB_GREEN, RED, WHITE

PINK = (120, 30, 50)
SOFT = (255, 150, 170)

HEART = (
    "..###...###..",
    ".#####.#####.",
    "#############",
    "#############",
    "#############",
    ".###########.",
    "..#########..",
    "...#######...",
    "....#####....",
    ".....###.....",
    "......#......",
)


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (64, 64), BG)
    return img, ImageDraw.Draw(img)


def _centred(img: Image.Image, y: int, text: str, color) -> None:
    font.draw_text(img, (64 - font.text_width(font.normalize(text), 1)) // 2, y, text, color, 1)


def _bitmap(img: Image.Image, x: int, y: int, rows: tuple[str, ...], color, scale: int = 1) -> None:
    d = ImageDraw.Draw(img)
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                d.rectangle([x + c * scale, y + r * scale, x + c * scale + scale - 1, y + r * scale + scale - 1], fill=color)


def _phone(d: ImageDraw.ImageDraw, screen=DIM) -> None:
    d.rounded_rectangle([22, 4, 41, 38], radius=3, fill=GREY)
    d.rectangle([24, 7, 39, 33], fill=screen)
    d.rectangle([30, 35, 33, 36], fill=DIM)


def voice_frame() -> Image.Image:
    """Speaker with a tiny wave and a volume meter turned almost all the way down."""
    img, d = _canvas()
    s = 6  # art sits lower, close to the text
    d.rectangle([8, 15 + s, 13, 26 + s], fill=GREY)
    d.polygon([(14, 15 + s), (22, 8 + s), (22, 33 + s), (14, 26 + s)], fill=WHITE)
    d.arc([18, 15 + s, 28, 26 + s], -50, 50, fill=CYAN)
    for i in range(5):
        h = 4 + i * 4
        d.rectangle([33 + i * 5, 33 + s - h, 35 + i * 5, 33 + s], fill=LB_GREEN if i == 0 else DIM)
    _centred(img, 44, "NEVER RAISE", WHITE)
    _centred(img, 52, "YOUR VOICE", GOLD)
    return img


def scroll_frame() -> Image.Image:
    """Phone with an endless feed and a down arrow, struck through in red."""
    img, d = _canvas()
    _phone(d)
    for y in (9, 14, 19):
        d.rectangle([26, y, 37, y + 2], fill=GREY)
    d.polygon([(27, 25), (36, 25), (31, 31)], fill=WHITE)
    d.line([(17, 37), (46, 5)], fill=RED, width=3)
    _centred(img, 44, "PUT IT DOWN", WHITE)
    _centred(img, 52, "LOOK UP", GOLD)
    return img


def breathe_frame() -> Image.Image:
    """Heart inside a soft larger heart, like an inhale."""
    img, _ = _canvas()
    _bitmap(img, 12, 2, HEART, PINK, 3)
    _bitmap(img, 19, 9, HEART, RED, 2)
    _bitmap(img, 23, 13, ("##", "#."), SOFT)
    _centred(img, 44, "BREATHE", WHITE)
    _centred(img, 52, "FIRST", RED)
    return img


SLIDES: tuple[Callable[[], Image.Image], ...] = (voice_frame, scroll_frame, breathe_frame)
