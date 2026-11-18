"""A tiny 3x5 pixel font, so text on a 64x64 panel stays crisp.

Each glyph is 3 pixels wide and 5 tall; characters advance 4 pixels, so a
full 64-pixel row holds 16 characters. Text is upper-cased before drawing and
unknown characters render as '?'.
"""

from __future__ import annotations

from PIL import Image

GLYPH_W, GLYPH_H, ADVANCE = 3, 5, 4

_GLYPHS: dict[str, tuple[str, ...]] = {
    "A": (".#.", "#.#", "###", "#.#", "#.#"),
    "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": (".##", "#..", "#..", "#..", ".##"),
    "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"),
    "F": ("###", "#..", "##.", "#..", "#.."),
    "G": (".##", "#..", "#.#", "#.#", ".##"),
    "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"),
    "J": ("..#", "..#", "..#", "#.#", ".#."),
    "K": ("#.#", "#.#", "##.", "#.#", "#.#"),
    "L": ("#..", "#..", "#..", "#..", "###"),
    "M": ("#.#", "###", "###", "#.#", "#.#"),
    "N": ("##.", "#.#", "#.#", "#.#", "#.#"),
    "O": (".#.", "#.#", "#.#", "#.#", ".#."),
    "P": ("##.", "#.#", "##.", "#..", "#.."),
    "Q": (".#.", "#.#", "#.#", "##.", ".##"),
    "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "S": (".##", "#..", ".#.", "..#", "##."),
    "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "U": ("#.#", "#.#", "#.#", "#.#", "###"),
    "V": ("#.#", "#.#", "#.#", "#.#", ".#."),
    "W": ("#.#", "#.#", "###", "###", "#.#"),
    "X": ("#.#", "#.#", ".#.", "#.#", "#.#"),
    "Y": ("#.#", "#.#", ".#.", ".#.", ".#."),
    "Z": ("###", "..#", ".#.", "#..", "###"),
    "0": ("###", "#.#", "#.#", "#.#", "###"),
    "1": (".#.", "##.", ".#.", ".#.", "###"),
    "2": ("##.", "..#", ".#.", "#..", "###"),
    "3": ("##.", "..#", ".#.", "..#", "##."),
    "4": ("#.#", "#.#", "###", "..#", "..#"),
    "5": ("###", "#..", "##.", "..#", "##."),
    "6": (".##", "#..", "###", "#.#", "###"),
    "7": ("###", "..#", ".#.", ".#.", ".#."),
    "8": ("###", "#.#", "###", "#.#", "###"),
    "9": ("###", "#.#", "###", "..#", "##."),
    " ": ("...", "...", "...", "...", "..."),
    ".": ("...", "...", "...", "...", ".#."),
    ",": ("...", "...", "...", ".#.", "#.."),
    ":": ("...", ".#.", "...", ".#.", "..."),
    "-": ("...", "...", "###", "...", "..."),
    "/": ("..#", "..#", ".#.", "#..", "#.."),
    "#": ("#.#", "###", "#.#", "###", "#.#"),
    "%": ("#.#", "..#", ".#.", "#..", "#.#"),
    "!": (".#.", ".#.", ".#.", "...", ".#."),
    "?": ("##.", "..#", ".#.", "...", ".#."),
    "'": (".#.", ".#.", "...", "...", "..."),
    "+": ("...", ".#.", "###", ".#.", "..."),
    "(": ("..#", ".#.", ".#.", ".#.", "..#"),
    ")": ("#..", ".#.", ".#.", ".#.", "#.."),
    "&": (".#.", "#.#", ".#.", "#.#", ".##"),
    "_": ("...", "...", "...", "...", "###"),
    "*": ("#.#", ".#.", "#.#", "...", "..."),
}

# Common accented / typographic characters folded to something drawable.
_FOLD = str.maketrans({"’": "'", "‘": "'", "–": "-", "—": "-", "é": "E", "É": "E", "ü": "U", "ö": "O", "ä": "A"})

RGB = tuple[int, int, int]


def normalize(text: str) -> str:
    return text.translate(_FOLD).upper()


def text_width(text: str, scale: int = 1) -> int:
    n = len(text)
    return 0 if n == 0 else (n * ADVANCE - 1) * scale


def fit(text: str, max_px: int, scale: int = 1) -> str:
    """Truncate text so it fits in max_px pixels."""
    max_chars = (max_px // scale + 1) // ADVANCE
    text = normalize(text)
    return text if len(text) <= max_chars else text[: max(0, max_chars)]


def wrap(text: str, max_px: int, max_lines: int) -> list[str]:
    """Word-wrap text into at most max_lines lines of max_px width."""
    max_chars = (max_px + 1) // ADVANCE
    words = normalize(text).split()
    lines: list[str] = []
    cur = ""
    for w in words:
        cand = w if not cur else f"{cur} {w}"
        if len(cand) <= max_chars:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        cur = w[:max_chars]
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines[:max_lines]


def draw_text(img: Image.Image, x: int, y: int, text: str, color: RGB, scale: int = 1) -> int:
    """Draw text with its top-left at (x, y). Returns the x after the last glyph."""
    px = img.load()
    w, h = img.size
    for ch in normalize(text):
        glyph = _GLYPHS.get(ch, _GLYPHS["?"])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit != "#":
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        X, Y = x + gx * scale + sx, y + gy * scale + sy
                        if 0 <= X < w and 0 <= Y < h:
                            px[X, Y] = color
        x += ADVANCE * scale
    return x
