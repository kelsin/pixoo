import dataclasses
import unittest

from PIL import Image

from retro_pixoo import font
from retro_pixoo.ra import ImageFetcher, load_sample, parse_summary
from retro_pixoo.render import GREY, profile_frame

HEADER_BOX = (20, 10, 64, 16)
RANK_BOX = (2, 40, 62, 46)


def _region(img, box):
    return img.crop(box).tobytes()


def _expected(base, x, y, text, box):
    ref = base.copy()
    font.draw_text(ref, x, y, text, GREY)
    return _region(ref, box)


class ParseSummaryTests(unittest.TestCase):
    def test_member_since(self):
        p = parse_summary({"MemberSince": "2026-10-24 06:10:20"})
        self.assertEqual(p.member_since, "2026-10-24 06:10:20")

    def test_member_since_missing(self):
        self.assertEqual(parse_summary({}).member_since, "")


class ProfileFrameTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = ImageFetcher(offline=True)
        self.sample = load_sample()

    def test_sizes(self):
        softcore = dataclasses.replace(self.sample, points=0, softcore_points=140, rank=None)
        for p in (self.sample, dataclasses.replace(self.sample, member_since=""), softcore):
            self.assertEqual(profile_frame(p, self.fetcher).size, (64, 64))

    def test_since_year_drawn(self):
        img = profile_frame(self.sample, self.fetcher)
        base = profile_frame(dataclasses.replace(self.sample, member_since=""), self.fetcher)
        self.assertEqual(_region(img, HEADER_BOX), _expected(base, 20, 10, "SINCE 2014", HEADER_BOX))

    def test_no_since_when_empty_or_invalid(self):
        blank = _region(profile_frame(dataclasses.replace(self.sample, member_since=""), self.fetcher), HEADER_BOX)
        self.assertEqual(set(Image.frombytes("RGB", (44, 6), blank).getdata()), {(24, 26, 40)})
        bad = profile_frame(dataclasses.replace(self.sample, member_since="n/a"), self.fetcher)
        self.assertEqual(_region(bad, HEADER_BOX), blank)

    def _rank_case(self, **kw):
        p = dataclasses.replace(self.sample, rank=None, **kw)
        img = profile_frame(p, self.fetcher)
        ranked = profile_frame(dataclasses.replace(p, rank=1, total_ranked=None), self.fetcher)
        # Erase the rank text from a ranked frame to get a base with an empty rank line.
        base = ranked.copy()
        base.paste((0, 0, 0), RANK_BOX)
        return img, base

    def test_softcore_label(self):
        img, base = self._rank_case(points=0, softcore_points=140)
        self.assertEqual(_region(img, RANK_BOX), _expected(base, 2, 40, "SOFTCORE", RANK_BOX))

    def test_unranked_label(self):
        img, base = self._rank_case(points=500, softcore_points=140)
        self.assertEqual(_region(img, RANK_BOX), _expected(base, 2, 40, "UNRANKED", RANK_BOX))
        img, base = self._rank_case(points=0, softcore_points=0)
        self.assertEqual(_region(img, RANK_BOX), _expected(base, 2, 40, "UNRANKED", RANK_BOX))


if __name__ == "__main__":
    unittest.main()
