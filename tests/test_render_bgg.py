import unittest
from datetime import date

from retro_pixoo.bgg import Play, load_sample_plays
from retro_pixoo.bgg_render import bgg_h_frame, bgg_recent_frame, bgg_stats_frame, bgg_top_frame

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


if __name__ == "__main__":
    unittest.main()
