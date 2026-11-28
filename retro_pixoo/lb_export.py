"""Read a Letterboxd data export (diary.csv) and cache poster URLs."""

import csv
import io
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .letterboxd import DiaryEntry

CACHE_PATH = Path.home() / "Library/Caches/retro-pixoo/posters.json"
SAMPLE_YEAR = 2026
SAMPLE_PATH = Path(__file__).parent / "sample_diary.csv"


@dataclass
class DiaryRow:
    name: str
    year: int | None
    rating: float | None
    tags: tuple[str, ...]
    watched: str
    logged: str


@dataclass
class TagSummary:
    count: int
    latest: DiaryRow | None


def parse_diary_csv(text: str) -> list[DiaryRow]:
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        rows.append(
            DiaryRow(
                name=r["Name"],
                year=int(r["Year"]) if r["Year"] else None,
                rating=float(r["Rating"]) if r["Rating"] else None,
                tags=tuple(t.strip() for t in r["Tags"].split(",") if t.strip()),
                watched=r["Watched Date"],
                logged=r["Date"],
            )
        )
    return rows


def newest_export(directory: Path, user: str) -> Path:
    found = sorted(Path(directory).glob(f"letterboxd-{user}-*.zip"))
    if not found:
        raise FileNotFoundError(f"no letterboxd-{user}-*.zip in {directory}")
    return found[-1]


def export_date(path: Path) -> date:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", Path(path).name)
    return date(int(m[1]), int(m[2]), int(m[3]))


def load_export(path: Path) -> list[DiaryRow]:
    with zipfile.ZipFile(path) as zf:
        return parse_diary_csv(zf.read("diary.csv").decode("utf-8"))


def load_latest(directory: Path, user: str, today: date) -> list[DiaryRow]:
    path = newest_export(directory, user)
    age = (today - export_date(path)).days
    if age > 8:
        print(f"letterboxd export: export is {age} days old ({path.name})", file=sys.stderr)
    return load_export(path)


def summarize(rows: list[DiaryRow], tag: str, year: int) -> TagSummary:
    hits = [r for r in rows if tag in r.tags and r.watched.startswith(f"{year}-")]
    latest = max(hits, key=lambda r: (r.watched, r.logged)) if hits else None
    return TagSummary(len(hits), latest)


def load_sample_diary() -> list[DiaryRow]:
    return parse_diary_csv(SAMPLE_PATH.read_text(encoding="utf-8"))


class PosterCache:
    def __init__(self, path: Path | None):
        self.path = path
        try:
            self._data: dict[str, str] = json.loads(Path(path).read_text()) if path else {}
            if not isinstance(self._data, dict):
                self._data = {}
        except Exception:
            self._data = {}

    @staticmethod
    def _key(title: str, year: int | None) -> str:
        return f"{title}|{year if year is not None else ''}"

    def update(self, entries: list[DiaryEntry]) -> None:
        changed = False
        for e in entries:
            if e.poster_url and self._data.get(self._key(e.title, e.year)) != e.poster_url:
                self._data[self._key(e.title, e.year)] = e.poster_url
                changed = True
        if changed and self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data))

    def get(self, title: str, year: int | None) -> str:
        return self._data.get(self._key(title, year), "")
