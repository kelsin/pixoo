"""Static motivational slides: four 64x64 frames for the page rotation."""
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


SLIDES: tuple[Callable[[], Image.Image], ...] = (voice_frame, scroll_frame, breathe_frame, handhelds_frame)
