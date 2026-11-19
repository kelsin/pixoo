"""Letterboxd RSS diary parser and client for the Pixoo pages."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import requests

LB = "{https://letterboxd.com}"
SAMPLE_PATH = Path(__file__).with_name("sample_feed.xml")
_IMG = re.compile(r'<img src="([^"]+)"')


@dataclass
class DiaryEntry:
    title: str
    year: int | None
    rating: float | None
    liked: bool
    rewatch: bool
    watched_date: str
    poster_url: str


def _text(item: ET.Element, tag: str) -> str | None:
    el = item.find(LB + tag)
    return el.text.strip() if el is not None and el.text else None


def _num(v: str | None, cast):
    try:
        return cast(v) if v is not None else None
    except ValueError:
        return None


def parse_feed(xml_text: str | bytes) -> list[DiaryEntry]:
    root = ET.fromstring(xml_text)
    entries: list[DiaryEntry] = []
    for item in root.iter("item"):
        title = _text(item, "filmTitle")
        if title is None:
            continue
        desc = item.findtext("description") or ""
        m = _IMG.search(desc)
        entries.append(
            DiaryEntry(
                title=title,
                year=_num(_text(item, "filmYear"), int),
                rating=_num(_text(item, "memberRating"), float),
                liked=_text(item, "memberLike") == "Yes",
                rewatch=_text(item, "rewatch") == "Yes",
                watched_date=_text(item, "watchedDate") or "",
                poster_url=m.group(1) if m else "",
            )
        )
    # The feed is in log order; show films in watch order. The sort is stable,
    # so same-day watches keep the feed's newest-logged-first order.
    entries.sort(key=lambda e: e.watched_date, reverse=True)
    return entries


class LetterboxdClient:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def diary(self, user: str) -> list[DiaryEntry]:
        r = requests.get(
            f"https://letterboxd.com/{user}/rss/",
            headers={"User-Agent": "retro-pixoo/0.1"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return parse_feed(r.content)


def load_sample_feed() -> list[DiaryEntry]:
    return parse_feed(SAMPLE_PATH.read_text(encoding="utf-8"))
