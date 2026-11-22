import copy
import unittest

from retro_pixoo.ra import ImageFetcher, load_sample
from retro_pixoo.render import recent_frame, recent_games_frame


class RecentGamesTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = ImageFetcher(offline=True)

    def test_sample_has_four_newest_games_with_progress(self):
        p = load_sample()
        self.assertEqual(len(p.games), 4)
        self.assertEqual(p.games[0], p.last_game)
        self.assertTrue(all(g.achieved for g in p.games))

    def test_frame_size_and_empty_differs(self):
        p = load_sample()
        full = recent_games_frame(p, self.fetcher)
        p.games = []
        empty = recent_games_frame(p, self.fetcher)
        self.assertEqual((full.size, empty.size), ((64, 64), (64, 64)))
        self.assertNotEqual(full.tobytes(), empty.tobytes())

    def test_recent_unlocks_draws_fourth_row(self):
        p = load_sample()
        p.recent.append(copy.copy(p.recent[0]))
        three = recent_frame(p, self.fetcher, count=3)
        four = recent_frame(p, self.fetcher)
        self.assertNotEqual(three.tobytes(), four.tobytes())
        self.assertEqual(four.size, (64, 64))


if __name__ == "__main__":
    unittest.main()
