"""RetroAchievements Web API client, reduced to what the Pixoo pages need.

Uses one call, API_GetUserSummary, which returns the profile, the last played
games with progress, and recent unlocks. Get your Web API key from
https://retroachievements.org/settings (Authentication section) and keep it
out of source control: pass it in or set RA_API_KEY.
"""

from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from PIL import Image

API_BASE = "https://retroachievements.org/API/"
MEDIA_BASE = "https://media.retroachievements.org"
SAMPLE_PATH = Path(__file__).with_name("sample_summary.json")


@dataclass
class Achievement:
    title: str
    description: str
    points: int
    game_title: str
    badge_url: str
    hardcore: bool
    date: str


@dataclass
class GameProgress:
    game_id: int
    title: str
    console: str
    icon_url: str
    achieved: int
    possible: int


@dataclass
class Profile:
    user: str
    points: int
    softcore_points: int
    true_points: int
    rank: int | None
    total_ranked: int | None
    status: str
    avatar_url: str
    rich_presence: str
    last_game: GameProgress | None
    recent: list[Achievement] = field(default_factory=list)

    @property
    def top_percent(self) -> float | None:
        if not self.rank or not self.total_ranked:
            return None
        return 100.0 * self.rank / self.total_ranked


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _media(path: str | None) -> str:
    if not path:
        return ""
    return path if path.startswith("http") else MEDIA_BASE + path


def parse_summary(data: dict[str, Any]) -> Profile:
    """Turn an API_GetUserSummary response into a Profile."""
    awarded = data.get("Awarded") or {}
    last_game = None
    played = data.get("RecentlyPlayed") or []
    if played:
        g = played[0]
        gid = _int(g.get("GameID"))
        prog = awarded.get(str(gid)) or {}
        last_game = GameProgress(
            game_id=gid,
            title=g.get("Title", ""),
            console=g.get("ConsoleName", ""),
            icon_url=_media(g.get("ImageIcon")),
            achieved=_int(prog.get("NumAchievedHardcore")) or _int(prog.get("NumAchieved")),
            possible=_int(prog.get("NumPossibleAchievements")) or _int(g.get("AchievementsTotal")),
        )

    recent: list[Achievement] = []
    # RecentAchievements is {game_id: {achievement_id: {...}}}; flatten and sort newest first.
    for per_game in (data.get("RecentAchievements") or {}).values():
        for a in (per_game or {}).values():
            recent.append(
                Achievement(
                    title=a.get("Title", ""),
                    description=a.get("Description", ""),
                    points=_int(a.get("Points")),
                    game_title=a.get("GameTitle", ""),
                    badge_url=f"{MEDIA_BASE}/Badge/{a.get('BadgeName')}.png" if a.get("BadgeName") else "",
                    hardcore=bool(_int(a.get("HardcoreAchieved"))),
                    date=a.get("DateAwarded", ""),
                )
            )
    recent.sort(key=lambda a: a.date, reverse=True)

    rank = data.get("Rank")
    total = data.get("TotalRanked")
    return Profile(
        user=data.get("User", ""),
        points=_int(data.get("TotalPoints")),
        softcore_points=_int(data.get("TotalSoftcorePoints")),
        true_points=_int(data.get("TotalTruePoints")),
        rank=_int(rank) if rank is not None else None,
        total_ranked=_int(total) if total is not None else None,
        status=data.get("Status", "Offline"),
        avatar_url=_media(data.get("UserPic")),
        rich_presence=data.get("RichPresenceMsg", "") or "",
        last_game=last_game,
        recent=recent,
    )


class RAClient:
    def __init__(self, api_key: str | None = None, timeout: float = 10.0):
        self.api_key = api_key or os.environ.get("RA_API_KEY")
        if not self.api_key:
            raise ValueError("Set RA_API_KEY or pass api_key (from retroachievements.org/settings).")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "retro-pixoo/0.1"

    def _get(self, endpoint: str, **params: Any) -> Any:
        params["y"] = self.api_key
        r = self.session.get(API_BASE + endpoint, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def user_summary(self, user: str, games: int = 1, achievements: int = 5) -> dict[str, Any]:
        return self._get("API_GetUserSummary.php", u=user, g=games, a=achievements)

    def profile(self, user: str, achievements: int = 5) -> Profile:
        return parse_summary(self.user_summary(user, achievements=achievements))


def load_sample() -> Profile:
    """Made-up data in the API's shape, for offline layout tests."""
    return parse_summary(json.loads(SAMPLE_PATH.read_text()))


class ImageFetcher:
    """Downloads badges, icons and avatars, with a small in-memory cache.

    Returns None on any failure so rendering can fall back to placeholders.
    """

    def __init__(self, timeout: float = 10.0, offline: bool = False):
        self.timeout = timeout
        self.offline = offline
        self._cache: dict[str, Image.Image | None] = {}

    def get(self, url: str) -> Image.Image | None:
        if self.offline or not url:
            return None
        if url not in self._cache:
            try:
                r = requests.get(url, timeout=self.timeout, headers={"User-Agent": "retro-pixoo/0.1"})
                r.raise_for_status()
                self._cache[url] = Image.open(io.BytesIO(r.content)).convert("RGB")
            except Exception:
                self._cache[url] = None
        return self._cache[url]
