"""BoardGameGeek plays client, parser and H-index helpers for the Pixoo pages."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import requests

SAMPLE_PATH = Path(__file__).with_name("sample_plays.xml")
API = "https://boardgamegeek.com/xmlapi2/plays"
PAGE_SIZE = 100


@dataclass
class Play:
    date: str
    game: str
    game_id: int
    quantity: int
    minutes: int


def _int(v: str | None, default: int) -> int:
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default


def parse_total(xml_text: str | bytes) -> int:
    return _int(ET.fromstring(xml_text).get("total"), 0)


def parse_plays(xml_text: str | bytes) -> list[Play]:
    plays: list[Play] = []
    for el in ET.fromstring(xml_text).iter("play"):
        item = el.find("item")
        if item is None or not item.get("name"):
            continue
        plays.append(
            Play(
                date=el.get("date", ""),
                game=item.get("name"),
                game_id=_int(item.get("objectid"), 0),
                quantity=max(1, _int(el.get("quantity"), 1)),
                minutes=max(0, _int(el.get("length"), 0)),
            )
        )
    return plays


class BggClient:
    def __init__(self, token: str | None = None, timeout: float = 10.0):
        self.token = token
        self.timeout = timeout

    def plays(self, user: str, year: int) -> list[Play]:
        token = self.token or os.environ.get("BGG_TOKEN")
        if not token:
            raise RuntimeError("BGG_TOKEN not set")
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "retro-pixoo/0.1"}
        plays: list[Play] = []
        page = 1
        while True:
            r = requests.get(
                API,
                headers=headers,
                params={
                    "username": user,
                    "mindate": f"{year}-01-01",
                    "maxdate": f"{year}-12-31",
                    "page": page,
                },
                timeout=self.timeout,
            )
            if r.status_code != 200:
                raise RuntimeError(f"BGG returned HTTP {r.status_code}")
            batch = parse_plays(r.content)
            plays.extend(batch)
            total = parse_total(r.content)
            if not batch or len(plays) >= total or len(batch) < PAGE_SIZE:
                return plays
            page += 1


def load_sample_plays() -> list[Play]:
    return parse_plays(SAMPLE_PATH.read_text(encoding="utf-8"))


def game_counts(plays: list[Play]) -> list[tuple[str, int]]:
    c: Counter[tuple[int, str]] = Counter()
    for p in plays:
        c[(p.game_id, p.game)] += p.quantity
    rows = [(name, n) for (_, name), n in c.items()]
    rows.sort(key=lambda r: (-r[1], r[0]))
    return rows


def h_index(plays: list[Play]) -> int:
    return sum(1 for i, (_, n) in enumerate(game_counts(plays), 1) if n >= i)


def h_next(plays: list[Play]) -> tuple[int, int, str | None]:
    """(h, extra plays needed to reach h+1, first game that needs a play)."""
    h = h_index(plays)
    counts = game_counts(plays)[: h + 1]
    need = h + 1
    extra, first = 0, None
    for name, n in counts:
        short = max(0, need - n)
        if short and first is None:
            first = name
        extra += short
    extra += need * (need - len(counts))
    return h, extra, first


def top_played(plays: list[Play], n: int = 5) -> list[tuple[str, int]]:
    return game_counts(plays)[:n]
