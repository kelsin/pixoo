"""RetroAchievements pages for the Divoom Pixoo-64.

Typical use from your own script:

    from retro_pixoo import RAClient, ImageFetcher, Pixoo, frames

    profile = RAClient().profile("kelsin")      # reads RA_API_KEY
    Pixoo("192.168.1.50").show(frames(profile, ImageFetcher()))
"""

from .pixoo import Pixoo
from .ra import Achievement, GameProgress, ImageFetcher, Profile, RAClient, load_sample, parse_summary
from .letterboxd import DiaryEntry, LetterboxdClient, load_sample_feed, parse_feed
from .render import diary_frame, frames, last_watched_frame, led_preview, profile_frame, recent_frame

__all__ = [
    "Achievement", "DiaryEntry", "GameProgress", "ImageFetcher", "LetterboxdClient", "Pixoo",
    "Profile", "RAClient", "diary_frame", "frames", "last_watched_frame", "led_preview",
    "load_sample", "load_sample_feed", "parse_feed", "parse_summary", "profile_frame",
    "recent_frame",
]
