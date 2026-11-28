"""Read a Letterboxd data export (diary.csv) and cache poster URLs."""

import csv
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from .letterboxd import DiaryEntry

CACHE_PATH = Path.home() / "Library/Caches/retro-pixoo/posters.json"
EXPORT_URL = "https://letterboxd.com/data/export/"
DATA_PATH = Path.home() / "Library/Application Support/retro-pixoo/letterboxd-diary.json"
REQUEST_PATH = CACHE_PATH.parent / "export_requested"
REQUEST_HOUR = 6
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
    os.listdir(directory)  # Path.glob swallows PermissionError; let it propagate
    found = sorted(Path(directory).glob(f"letterboxd-{user}-[0-9][0-9][0-9][0-9]-*.zip"))
    if not found:
        raise FileNotFoundError(f"no letterboxd-{user}-*.zip in {directory}")
    return found[-1]


def export_time(path: Path) -> datetime:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-utc", Path(path).name)
    return datetime(*(int(g) for g in m.groups()), tzinfo=timezone.utc)


def open_in_browser(url: str) -> None:
    subprocess.run(["/usr/bin/open", url], check=False)


def request_export_if_due(
    directory: Path,
    user: str,
    now: datetime,
    state_path: Path,
    data_path: Path,
    opener: Callable[[str], None],
    hour: int = REQUEST_HOUR,
) -> bool:
    """Open the export page from `hour` local time, once a day, unless today's export is saved or in `directory`."""
    if now.hour < hour:
        return False
    try:
        if state_path.read_text().strip() == now.date().isoformat():
            return False
    except FileNotFoundError:
        pass
    saved = load_saved(data_path)
    if saved and saved[0].astimezone(now.tzinfo).date() >= now.date():
        return False
    try:
        if export_time(newest_export(directory, user)).astimezone(now.tzinfo).date() >= now.date():
            return False
    except FileNotFoundError:
        pass
    except PermissionError:
        return False
    opener(EXPORT_URL)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(now.date().isoformat())
    return True


def _is_complete_export(path: Path) -> bool:
    if not zipfile.is_zipfile(path):
        return False
    with zipfile.ZipFile(path) as zf:
        return "diary.csv" in zf.namelist()


def wait_for_new_export(
    directory: Path,
    user: str,
    previous: str | None,
    timeout: float = 120,
    poll: float = 2,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Path | None:
    """Poll for a complete export other than `previous`; None if none shows up in `timeout`."""
    deadline = clock() + timeout
    while True:
        try:
            path = newest_export(directory, user)
            if path.name != previous and _is_complete_export(path):
                return path
        except (FileNotFoundError, zipfile.BadZipFile, OSError):
            pass
        if clock() >= deadline:
            return None
        sleep(poll)


def load_export(path: Path) -> list[DiaryRow]:
    with zipfile.ZipFile(path) as zf:
        return parse_diary_csv(zf.read("diary.csv").decode("utf-8"))


def save_export(data_path: Path, path: Path, csv_text: str) -> None:
    record = {
        "export": Path(path).name,
        "exported_at": export_time(path).isoformat(),
        "diary_csv": csv_text,
    }
    data_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=data_path.parent, prefix=".diary-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f)
        os.replace(tmp, data_path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _read_saved(data_path: Path) -> tuple[str, datetime, list[DiaryRow]] | None:
    try:
        rec = json.loads(Path(data_path).read_text(encoding="utf-8"))
        return (rec["export"], datetime.fromisoformat(rec["exported_at"]),
                parse_diary_csv(rec["diary_csv"]))
    except Exception:
        return None


def load_saved(data_path: Path) -> tuple[datetime, list[DiaryRow]] | None:
    saved = _read_saved(data_path)
    return (saved[1], saved[2]) if saved else None


def ingest_exports(directory: Path, user: str, data_path: Path) -> str | None:
    """Save the newest complete export if it's newer than the saved data, then delete it and older ones."""
    os.listdir(directory)  # Path.glob swallows PermissionError; let it propagate
    found = sorted(Path(directory).glob(f"letterboxd-{user}-[0-9][0-9][0-9][0-9]-*.zip"))
    newest = next((p for p in reversed(found) if _is_complete_export(p)), None)
    if newest is None:
        return None
    saved = load_saved(data_path)
    took = None
    if saved is None or export_time(newest) > saved[0]:
        with zipfile.ZipFile(newest) as zf:
            text = zf.read("diary.csv").decode("utf-8")
        parse_diary_csv(text)  # a broken CSV raises before anything is deleted
        save_export(data_path, newest, text)
        took = newest.name
    for p in found:
        if p.name <= newest.name:
            p.unlink(missing_ok=True)
    return took


def load_latest(directory: Path, user: str, data_path: Path, today: date) -> list[DiaryRow]:
    try:
        ingest_exports(directory, user, data_path)
    except OSError as e:
        print(f"letterboxd export: can't read {directory}: {e}; using saved data", file=sys.stderr)
    saved = _read_saved(data_path)
    if saved is None:
        raise FileNotFoundError(
            f"no saved Letterboxd export and no letterboxd-{user}-*.zip in {directory}")
    name, exported_at, rows = saved
    age = (today - exported_at.astimezone().date()).days
    if age > 8:
        print(f"letterboxd export: export is {age} days old ({name})", file=sys.stderr)
    return rows


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
