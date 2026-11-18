"""RetroAchievements pages for the Divoom Pixoo-64.

Typical use from your own script:

    from retro_pixoo import RAClient, ImageFetcher, Pixoo, frames

    profile = RAClient().profile("kelsin")      # reads RA_API_KEY
    Pixoo("192.168.1.50").show(frames(profile, ImageFetcher()))
"""

from .pixoo import Pixoo
from .ra import Achievement, GameProgress, ImageFetcher, Profile, RAClient, load_sample, parse_summary
from .render import frames, led_preview, profile_frame, recent_frame

__all__ = [
    "Achievement", "GameProgress", "ImageFetcher", "Pixoo", "Profile", "RAClient",
    "frames", "led_preview", "load_sample", "parse_summary", "profile_frame", "recent_frame",
]
