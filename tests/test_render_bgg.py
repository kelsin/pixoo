import unittest
from datetime import date

from retro_pixoo.bgg import Play, load_sample_plays
from PIL import Image

from retro_pixoo.bgg_render import (
    _pip_layout, _wrap, bgg_h_frame, bgg_recent_frame, bgg_stats_frame, bgg_top_frame,
    needed_games,
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


class HLayoutTests(unittest.TestCase):
    def test_pip_layout_fills_row(self):
        for need in (4, 16, 25):
            pips = _pip_layout(need, 2, 60)
            self.assertEqual(len(pips), need)
            self.assertEqual(pips[0][0], 2)
            self.assertEqual(pips[-1][0] + pips[-1][1], 62)
            for (x, w), (nx, _) in zip(pips, pips[1:]):
                self.assertEqual(nx - (x + w), 1)
            self.assertEqual(sum(w for _, w in pips) + need - 1, 60)

    def test_pip_layout_huge_need_clamps(self):
        pips = _pip_layout(80, 2, 60)
        self.assertTrue(all(w == 1 for _, w in pips))
        self.assertLessEqual(pips[-1][0] + pips[-1][1], 62)

    def test_wrap_two_lines_truncates_last(self):
        self.assertEqual(_wrap("WINGSPAN", 40, 2), ["WINGSPAN"])
        lines = _wrap("TWILIGHT IMPERIUM FOURTH EDITION", 40, 2)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "TWILIGHT")
        self.assertLessEqual(len(lines[1]) * 4, 41)

    def test_h_frame_pips_and_bar(self):
        plays = [P(game="A", gid=1, qty=3), P(game="B", gid=2, qty=2)]
        img = bgg_h_frame(plays, TODAY)  # h=2, need=3; target B with 2/3
        row = [img.getpixel((x, 60)) for x in range(2, 62)]
        from retro_pixoo.render import DIM, GOLD
        self.assertEqual(row[0], GOLD)
        self.assertEqual(row[-1], DIM)
        self.assertEqual(img.getpixel((1, 60)), (0, 0, 0))
        self.assertNotEqual(img.getpixel((2, 59)), (0, 0, 0))

    def test_h_frame_double_digit_h(self):
        plays = [P(game=f"G{i}", gid=i, qty=15) for i in range(1, 16)]
        img = bgg_h_frame(plays, TODAY)
        self.assertEqual(img.size, (64, 64))


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

    def test_recent_collapses_repeats(self):
        plays = [P("A", "2026-11-10", 1), P("A", "2026-11-09", 1, qty=2), P("B", "2026-11-08", 2),
                 P("C", "2026-11-07", 3), P("D", "2026-11-06", 4), P("E", "2026-11-05", 5)]
        from retro_pixoo.bgg_render import _recent_groups

        got = [(p.game, n) for p, n in _recent_groups(plays, 4)]
        self.assertEqual(got, [("A", 3), ("B", 1), ("C", 1), ("D", 1)])

    def test_other_year_and_empty(self):
        self.assertEqual(self.needed([], ("recent", "top"), TODAY), [])
        self.assertEqual(self.needed([P(when="2025-06-01")], ("recent", "top", "h", "stats"), TODAY), [])
