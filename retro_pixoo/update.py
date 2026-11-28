"""One-shot update: python -m retro_pixoo.update [--sample] [--preview DIR | --no-preview] [--send IP]

Meant for cron. Pages from a failing source are skipped; exit code 1 if anything failed.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from PIL import Image

from .bgg import BggClient, Play, load_sample_plays
from .bgg_render import (
    bgg_h_frame, bgg_recent_frame, bgg_stats_frame, bgg_top_frame, needed_games,
)
from .lb_export import (
    CACHE_PATH, DATA_PATH, REQUEST_PATH, SAMPLE_YEAR, DiaryRow, PosterCache, load_latest,
    load_sample_diary, newest_export, open_in_browser, request_export_if_due, wait_for_new_export,
)
from .letterboxd import DiaryEntry, LetterboxdClient, load_sample_feed
from .motivation import SLIDES
from .pixoo import Pixoo
from .ra import ImageFetcher, Profile, RAClient, load_sample
from .tags_render import tag_frames
from .render import (
    diary_frame, last_watched_frame, led_preview, month_stats_frame, profile_frame, recent_frame,
    recent_games_frame, systems_frame, watch_calendar_frame,
)

BGG_PAGES = {
    "h": bgg_h_frame,
    "recent": bgg_recent_frame,
    "top": bgg_top_frame,
    "stats": bgg_stats_frame,
}


def collect_pages(
    ra: Callable[[], Profile],
    lb: Callable[[], list[DiaryEntry]],
    fetcher: ImageFetcher,
    bgg: Callable[[], list[Play]] | None = None,
    bgg_pages: tuple[str, ...] = tuple(BGG_PAGES),
    bgg_thumbs: Callable[[list[int]], dict[int, str]] | None = None,
    tags: Callable[[], list[DiaryRow]] | None = None,
    posters: PosterCache | None = None,
    year: int | None = None,
) -> tuple[list[Image.Image], list[str]]:
    errors: list[str] = []
    profile = entries = None
    try:
        profile = ra()
    except Exception as e:
        errors.append(f"retroachievements: {str(e) or type(e).__name__}")
    try:
        entries = lb()
    except Exception as e:
        errors.append(f"letterboxd: {str(e) or type(e).__name__}")
    if posters is not None and entries:
        try:
            posters.update(entries)
        except Exception:
            pass  # the poster cache is optional
    plays = None
    if bgg is not None:
        try:
            plays = bgg()
        except Exception as e:
            errors.append(f"bgg: {str(e) or type(e).__name__}")
    pages: list[Image.Image] = []
    slides = iter(SLIDES)
    if profile is not None:
        pages.append(profile_frame(profile, fetcher))
        pages.append(recent_frame(profile, fetcher))
        pages.append(recent_games_frame(profile, fetcher))
        pages.append(systems_frame(profile, fetcher))
        pages.append(next(slides)())
    if entries is not None:
        pages.append(last_watched_frame(entries, fetcher))
        pages.append(diary_frame(entries, fetcher))
        pages.append(month_stats_frame(entries))
        pages.append(watch_calendar_frame(entries))
        pages.append(next(slides)())
    if plays is not None and bgg_pages:
        thumbs: dict[int, str] = {}
        if bgg_thumbs is not None:
            ids = [gid for gid, _ in needed_games(plays, bgg_pages)]
            try:
                thumbs = bgg_thumbs(ids) if ids else {}
            except Exception:
                thumbs = {}  # images are optional; identicons fill in
        pages.extend(BGG_PAGES[name](plays, thumbs=thumbs, fetcher=fetcher) for name in bgg_pages)
        pages.append(next(slides)())
    if tags is not None:
        try:
            rows = tags()
        except Exception as e:
            errors.append(f"letterboxd export: {str(e) or type(e).__name__}")
        else:
            poster_for = posters.get if posters else (lambda t, y: "")
            pages.extend(tag_frames(rows, poster_for, fetcher, year or date.today().year))
            pages.append(next(slides)())
    return pages, errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="retro_pixoo.update")
    ap.add_argument("--ra-user", default="kelsin")
    ap.add_argument("--lb-user", default="kelsin13")
    ap.add_argument("--bgg-user", default="Kelsin")
    ap.add_argument("--bgg-pages", default=",".join(BGG_PAGES),
                    help="comma list of BGG pages: " + ",".join(BGG_PAGES))
    ap.add_argument("--lb-export-dir", type=Path, default=Path.home() / "Downloads",
                    help="folder holding the Letterboxd data export zip (default: ~/Downloads)")
    ap.add_argument("--sample", action="store_true", help="use bundled sample data, no network")
    ap.add_argument("--preview", type=Path, default=Path("preview"),
                    help="write PNG/GIF previews to this directory (default: preview)")
    ap.add_argument("--no-preview", action="store_true", help="skip writing local previews")
    ap.add_argument("--send", metavar="IP", default=os.environ.get("PIXOO_IP"),
                    help="push frames to the Pixoo at this IP (default: $PIXOO_IP)")
    ap.add_argument("--endpoint", default="/post", help="/post (default) or /divoom_api")
    ap.add_argument("--seconds", type=int, default=30, help="seconds per page on the device")
    args = ap.parse_args(argv)
    bgg_pages = tuple(n.strip() for n in args.bgg_pages.split(",") if n.strip())
    unknown = [n for n in bgg_pages if n not in BGG_PAGES]
    if unknown:
        ap.error(f"unknown --bgg-pages: {', '.join(unknown)} (choose from {', '.join(BGG_PAGES)})")

    if args.sample:
        fetcher = ImageFetcher(offline=True)
        ra, lb = load_sample, load_sample_feed
        bgg = load_sample_plays
        tags, posters, year = load_sample_diary, PosterCache(None), SAMPLE_YEAR
    else:
        fetcher = ImageFetcher()
        ra = lambda: RAClient().profile(args.ra_user)  # noqa: E731
        lb = lambda: LetterboxdClient().diary(args.lb_user)  # noqa: E731
        bgg = None
        tags = lambda: load_latest(args.lb_export_dir, args.lb_user, DATA_PATH, date.today())  # noqa: E731
        posters, year = PosterCache(CACHE_PATH), None
        try:
            now = datetime.now().astimezone()
            try:
                previous = newest_export(args.lb_export_dir, args.lb_user).name
            except Exception:
                previous = None
            if request_export_if_due(args.lb_export_dir, args.lb_user, now, REQUEST_PATH,
                                     DATA_PATH, open_in_browser):
                print("letterboxd export: requested a new export")
                got = wait_for_new_export(args.lb_export_dir, args.lb_user, previous)
                if got:
                    print(f"letterboxd export: got {got.name}")
                else:
                    print("letterboxd export: no new export after 120s; using the previous one",
                          file=sys.stderr)
        except Exception as e:
            print(f"letterboxd export: request failed: {str(e) or type(e).__name__}",
                  file=sys.stderr)
        if os.environ.get("BGG_TOKEN"):
            bgg = lambda: BggClient().plays(args.bgg_user, date.today().year)  # noqa: E731

    bgg_thumbs = None if args.sample else BggClient().thumbnails
    pages, errors = collect_pages(ra, lb, fetcher, bgg, bgg_pages, bgg_thumbs, tags, posters, year)
    for err in errors:
        print(err, file=sys.stderr)
    if not pages:
        return 1

    if not args.no_preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        leds = [led_preview(f) for f in pages]
        for i, (raw, led) in enumerate(zip(pages, leds)):
            raw.save(args.preview / f"page{i + 1}_64.png")
            led.save(args.preview / f"page{i + 1}_led.png")
        leds[0].save(args.preview / "preview.gif", save_all=True, append_images=leds[1:],
                     duration=args.seconds * 1000, loop=0)
        print(f"wrote previews to {args.preview}")
    if args.send:
        try:
            Pixoo(args.send, args.endpoint).show(pages, ms_per_frame=args.seconds * 1000)
        except Exception as e:
            print(f"pixoo: {str(e) or type(e).__name__}", file=sys.stderr)
            return 1
        print(f"sent {len(pages)} pages to {args.send}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
