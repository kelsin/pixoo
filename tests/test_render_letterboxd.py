import unittest

from PIL import Image

from retro_pixoo.letterboxd import DiaryEntry, load_sample_feed
from retro_pixoo.ra import ImageFetcher
from retro_pixoo.render import _stars, _watched_date, diary_frame, last_watched_frame

LONG = DiaryEntry(
    "Dr. Strangelove or: How I Learned to Stop Worrying and Love the Bomb Pokémon",
    None, None, False, True, "2026-01-01", "",
)


class LetterboxdRenderTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = ImageFetcher(offline=True)
        self.entries = load_sample_feed()

    def test_frames_are_64x64(self):
        self.assertEqual(last_watched_frame(self.entries, self.fetcher).size, (64, 64))
        self.assertEqual(diary_frame(self.entries, self.fetcher).size, (64, 64))

    def test_empty_entries(self):
        self.assertEqual(last_watched_frame([], self.fetcher).size, (64, 64))
        self.assertEqual(diary_frame([], self.fetcher).size, (64, 64))

    def test_single_entry_diary(self):
        self.assertEqual(diary_frame(self.entries[:1], self.fetcher).size, (64, 64))

    def test_unrated_long_title(self):
        self.assertEqual(last_watched_frame([LONG], self.fetcher).size, (64, 64))
        self.assertEqual(diary_frame([LONG, LONG], self.fetcher).size, (64, 64))

    def test_stars_width(self):
        img = Image.new("RGB", (64, 64))
        self.assertEqual(_stars(img, 0, 0, None), 0)
        self.assertGreater(_stars(img, 0, 0, 3.5), _stars(img, 0, 0, 3.0))
        self.assertGreater(_stars(img, 0, 0, 3.0), 0)

    def test_watched_date(self):
        self.assertEqual(_watched_date("2026-11-16"), "NOV 16")
        self.assertEqual(_watched_date("2026-01-05"), "JAN 5")
        self.assertIsNone(_watched_date(""))
        self.assertIsNone(_watched_date("garbage"))


if __name__ == "__main__":
    unittest.main()
