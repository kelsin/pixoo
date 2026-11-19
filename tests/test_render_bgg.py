import unittest
from datetime import date

from retro_pixoo.bgg import Play, load_sample_plays
from PIL import Image

from retro_pixoo.bgg_render import (
    bgg_h_frame, bgg_recent_frame, bgg_stats_frame, bgg_top_frame, needed_games,
)

TODAY = date(2026, 11, 19)
FRAMES = [bgg_h_frame, bgg_recent_frame, bgg_top_frame, bgg_stats_frame]


def P(game="Wingspan", when="2026-11-10", gid=1, qty=1, minutes=0):
    return Play(date=when, game=game, game_id=gid, quantity=qty, minutes=minutes)


class BggRenderTests(unittest.TestCase):
    def test_size_and_mode(self):
        plays = load_sample_plays()
        for f in FRAMES:
            img = f(plays, TODAY)
            self.assertEqual(img.size, (64, 64))
            self.assertEqual(img.mode, "RGB")

    def test_empty_differs_from_sample(self):
        plays = load_sample_plays()
        for f in FRAMES:
            self.assertNotEqual(f([], TODAY).tobytes(), f(plays, TODAY).tobytes())

    def test_other_year_excluded(self):
        old = [P(when="2025-06-01")]
        for f in FRAMES:
            self.assertEqual(f(old, TODAY).tobytes(), f([], TODAY).tobytes())

    def test_long_name_renders(self):
        plays = [P(game="X" * 60)]
        for f in FRAMES:
            img = f(plays, TODAY)
            self.assertEqual(img.size, (64, 64))

    def test_hours_only_with_minutes(self):
        without = bgg_stats_frame([P(minutes=0)], TODAY)
        with_min = bgg_stats_frame([P(minutes=90)], TODAY)
        self.assertNotEqual(without.tobytes(), with_min.tobytes())


class _Fetcher:
    def __init__(self):
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        return Image.new("RGB", (40, 30), (200, 30, 30))


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.plays = load_sample_plays()
        ids = [g for g, _ in needed_games(self.plays, ("h", "recent", "top", "stats"), TODAY)]
        self.thumbs = {g: f"http://img/{g}" for g in ids}

    def test_images_change_frames(self):
        for f in FRAMES:
            plain = f(self.plays, TODAY)
            img = f(self.plays, TODAY, thumbs=self.thumbs, fetcher=_Fetcher())
            self.assertEqual(img.size, (64, 64))
            self.assertNotEqual(plain.tobytes(), img.tobytes())

    def test_icon_size_and_urls_from_thumbs(self):
        from retro_pixoo.bgg_render import _game_icon

        fetcher = _Fetcher()
        icon = _game_icon(fetcher, {1: "u1"}, 1, "X", 12)
        self.assertEqual(icon.size, (12, 12))
        self.assertEqual(fetcher.calls, ["u1"])

    def test_real_fetcher_dedupes(self):
        from unittest import mock
        from retro_pixoo.ra import ImageFetcher

        f = ImageFetcher()
        seen = []

        def fake_get(url, **kw):
            seen.append(url)
            import io
            buf = io.BytesIO()
            Image.new("RGB", (8, 8)).save(buf, "PNG")
            return mock.Mock(content=buf.getvalue(), raise_for_status=lambda: None)

        with mock.patch("retro_pixoo.ra.requests.get", fake_get):
            for fr in FRAMES:
                fr(self.plays, TODAY, thumbs=self.thumbs, fetcher=f)
        self.assertEqual(len(seen), len(set(seen)))

    def test_missing_thumbs_use_identicon(self):
        for f in FRAMES:
            img = f(self.plays, TODAY, thumbs={}, fetcher=_Fetcher())
            self.assertEqual(img.size, (64, 64))

    def test_long_names_with_images(self):
        plays = [P(game="X" * 60, gid=7)]
        for f in FRAMES:
            img = f(plays, TODAY, thumbs={7: "u"}, fetcher=_Fetcher())
            self.assertEqual(img.size, (64, 64))


if __name__ == "__main__":
    unittest.main()


class NeededGamesTests(unittest.TestCase):
    def setUp(self):
        from retro_pixoo.bgg_render import needed_games

        self.needed = needed_games
        self.plays = load_sample_plays()

    def test_all_pages_unique_and_bounded(self):
        out = self.needed(self.plays, ("h", "recent", "top", "stats"), TODAY)
        ids = [g for g, _ in out]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertLessEqual(len(ids), 10)

    def test_top_is_five(self):
        self.assertEqual(len(self.needed(self.plays, ("top",), TODAY)), 5)

    def test_recent_matches_newest(self):
        year = [p for p in self.plays if p.date.startswith("2026-")]
        newest = sorted(year, key=lambda p: p.date, reverse=True)[:4]
        self.assertEqual(
            self.needed(self.plays, ("recent",), TODAY), [(p.game_id, p.game) for p in newest]
        )

    def test_other_year_and_empty(self):
        self.assertEqual(self.needed([], ("recent", "top"), TODAY), [])
        self.assertEqual(self.needed([P(when="2025-06-01")], ("recent", "top", "h", "stats"), TODAY), [])
