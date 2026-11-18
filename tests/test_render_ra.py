import dataclasses
import unittest
from datetime import datetime, timedelta, timezone

from PIL import Image

from retro_pixoo import font
from retro_pixoo.ra import ImageFetcher, load_sample, parse_summary
from retro_pixoo.render import GREY, _played_ago, profile_frame

HEADER_BOX = (20, 10, 64, 16)
RANK_BOX = (2, 40, 62, 46)


def _region(img, box):
    return img.crop(box).tobytes()


def _expected(base, x, y, text, box):
    ref = base.copy()
    font.draw_text(ref, x, y, text, GREY)
    return _region(ref, box)


NOW = datetime(2026, 11, 17, 23, 4, 11, tzinfo=timezone.utc)  # 2h after the sample's LastPlayed


class ParseSummaryTests(unittest.TestCase):
    def test_last_played(self):
        p = parse_summary({"RecentlyPlayed": [{"GameID": "1", "LastPlayed": "2026-11-17 21:04:11"}]})
        self.assertEqual(p.last_played, "2026-11-17 21:04:11")

    def test_last_played_missing(self):
        self.assertEqual(parse_summary({}).last_played, "")
        self.assertEqual(parse_summary({"RecentlyPlayed": [{"GameID": "1"}]}).last_played, "")


class PlayedAgoTests(unittest.TestCase):
    def ago(self, delta):
        return _played_ago((NOW - delta).strftime("%Y-%m-%d %H:%M:%S"), NOW)

    def test_boundaries(self):
        for delta, want in [
            (timedelta(seconds=59), "JUST NOW"),
            (timedelta(seconds=60), "1M AGO"),
            (timedelta(minutes=59, seconds=59), "59M AGO"),
            (timedelta(hours=1), "1H AGO"),
            (timedelta(hours=23, minutes=59), "23H AGO"),
            (timedelta(hours=24), "1D AGO"),
            (timedelta(days=40), "40D AGO"),
            (timedelta(minutes=-5), "JUST NOW"),
        ]:
            self.assertEqual(self.ago(delta), want, delta)

    def test_unparseable(self):
        self.assertIsNone(_played_ago("", NOW))
        self.assertIsNone(_played_ago("garbage", NOW))


class ProfileFrameTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = ImageFetcher(offline=True)
        self.sample = load_sample()

    def test_sizes(self):
        softcore = dataclasses.replace(self.sample, points=0, softcore_points=140, rank=None)
        for p in (self.sample, dataclasses.replace(self.sample, last_played=""), softcore):
            self.assertEqual(profile_frame(p, self.fetcher).size, (64, 64))
        self.assertEqual(profile_frame(self.sample, self.fetcher, now=NOW).size, (64, 64))

    def test_played_ago_drawn(self):
        img = profile_frame(self.sample, self.fetcher, now=NOW)
        base = profile_frame(dataclasses.replace(self.sample, last_played=""), self.fetcher, now=NOW)
        self.assertEqual(_region(img, HEADER_BOX), _expected(base, 20, 10, "2H AGO", HEADER_BOX))

    def test_nothing_drawn_when_empty_or_invalid(self):
        blank = _region(profile_frame(dataclasses.replace(self.sample, last_played=""), self.fetcher, now=NOW), HEADER_BOX)
        self.assertEqual(set(Image.frombytes("RGB", (44, 6), blank).getdata()), {(24, 26, 40)})
        bad = profile_frame(dataclasses.replace(self.sample, last_played="n/a"), self.fetcher, now=NOW)
        self.assertEqual(_region(bad, HEADER_BOX), blank)

    def _rank_case(self, **kw):
        p = dataclasses.replace(self.sample, rank=None, **kw)
        img = profile_frame(p, self.fetcher)
        ranked = profile_frame(dataclasses.replace(p, rank=1, total_ranked=None), self.fetcher)
        # Erase the rank text from a ranked frame to get a base with an empty rank line.
        base = ranked.copy()
        base.paste((0, 0, 0), RANK_BOX)
        return img, base

    def test_unranked_label(self):
        img, base = self._rank_case(points=500, softcore_points=140)
        self.assertEqual(_region(img, RANK_BOX), _expected(base, 2, 40, "UNRANKED", RANK_BOX))
        img, base = self._rank_case(points=0, softcore_points=140)
        self.assertEqual(_region(img, RANK_BOX), _expected(base, 2, 40, "UNRANKED", RANK_BOX))


if __name__ == "__main__":
    unittest.main()
