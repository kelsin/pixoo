"""Command line: python -m retro_pixoo --user kelsin [--sample] [--preview DIR] [--send IP] [--loop MIN]"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .pixoo import Pixoo
from .ra import ImageFetcher, RAClient, load_sample
from .render import frames, led_preview


def main() -> None:
    ap = argparse.ArgumentParser(prog="retro_pixoo")
    ap.add_argument("--user", default="kelsin")
    ap.add_argument("--sample", action="store_true", help="use bundled sample data, no network")
    ap.add_argument("--preview", type=Path, help="write PNG/GIF previews to this directory")
    ap.add_argument("--send", metavar="IP", help="push frames to the Pixoo at this IP")
    ap.add_argument("--endpoint", default="/post", help="/post (default) or /divoom_api")
    ap.add_argument("--seconds", type=int, default=6, help="seconds per page on the device")
    ap.add_argument("--loop", type=float, metavar="MIN", help="refresh every MIN minutes (keep >= 5)")
    args = ap.parse_args()

    def run_once() -> None:
        if args.sample:
            profile, fetcher = load_sample(), ImageFetcher(offline=True)
        else:
            profile, fetcher = RAClient().profile(args.user), ImageFetcher()
        pages = frames(profile, fetcher)
        if args.preview:
            args.preview.mkdir(parents=True, exist_ok=True)
            leds = [led_preview(f) for f in pages]
            for i, (raw, led) in enumerate(zip(pages, leds)):
                raw.save(args.preview / f"page{i + 1}_64.png")
                led.save(args.preview / f"page{i + 1}_led.png")
            leds[0].save(args.preview / "preview.gif", save_all=True, append_images=leds[1:],
                         duration=args.seconds * 1000, loop=0)
            print(f"wrote previews to {args.preview}")
        if args.send:
            Pixoo(args.send, args.endpoint).show(pages, ms_per_frame=args.seconds * 1000)
            print(f"sent {len(pages)} pages to {args.send}")

    if args.loop:
        interval = max(5.0, args.loop) * 60  # RA asks API users to cache; don't poll fast
        while True:
            try:
                run_once()
            except Exception as e:  # keep the loop alive through network blips
                print(f"update failed: {e}")
            time.sleep(interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
