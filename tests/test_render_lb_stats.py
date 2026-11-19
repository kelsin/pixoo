import unittest
from datetime import date

from retro_pixoo.letterboxd import DiaryEntry, load_sample_feed
from retro_pixoo.ra import ImageFetcher
from retro_pixoo.render import (
    decade_counts,
    decades_frame,
    month_entries,
    month_stats_frame,
    rating_histogram,
    top_rated,
    top_rated_frame,
    watch_calendar_frame,
)

TODAY = date(2026, 11, 18)


def E(title, year=2000, rating=None, when="2026-11-10", liked=False, rewatch=False):
    return DiaryEntry(title, year, rating, liked, rewatch, when, "")


class HelperTests(unittest.TestCase):
    def test_month_entries(self):
        es = [E("a", when="2026-11-01"), E("b", when="2026-10-31"), E("c", when="2025-11-05"),
              E("d", when="bad"), E("e", when="")]
        self.assertEqual([e.title for _, e in month_entries(es, TODAY)], ["a"])

    def test_rating_histogram(self):
        es = [E("a", rating=0.5), E("b", rating=1.0), E("c", rating=1.0), E("d", rating=5.0), E("e")]
        self.assertEqual(rating_histogram(es), [1, 2, 0, 0, 0, 0, 0, 0, 0, 1])

    def test_decade_counts(self):
        es = [E("a", 1985), E("b", 1989), E("c", 2003), E("d", None), E("e", 2021)]
        self.assertEqual(decade_counts(es), [(1980, 2), (2000, 1), (2020, 1)])

    def test_decade_counts_drops_least_common(self):
        es = [E("a", 1930), E("b", 1940), E("c", 1950, ), E("d", 1950), E("e", 1960), E("f", 1960)]
        self.assertEqual(decade_counts(es, max_rows=2), [(1950, 2), (1960, 2)])

    def test_top_rated(self):
        es = [E("a", 2000, 4.0), E("b", 2001, 5.0), E("a", 2000, 5.0), E("c", 2002, 4.0), E("d", 2003)]
        # a keeps its first (4.0) entry; ties stay newest first
        self.assertEqual([e.title for e in top_rated(es)], ["b", "a", "c"])
        self.assertEqual(len(top_rated([E(str(i), rating=3.0) for i in range(12)])), 8)


class FrameTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = ImageFetcher(offline=True)

    def check(self, entries):
        for img in (
            month_stats_frame(entries, TODAY),
            watch_calendar_frame(entries, TODAY),
            decades_frame(entries),
            top_rated_frame(entries, self.fetcher),
        ):
            self.assertEqual(img.size, (64, 64))

    def test_sample(self):
        self.check(load_sample_feed())

    def test_empty(self):
        self.check([])

    def test_missing_fields(self):
        self.check([E("a", None, None, "bad"), E("b", None, None, ""), E("c", None, None, "2026-11-18")])

    def test_calendar_month_lengths(self):
        es = [E("a", when="2026-02-28")]
        self.assertEqual(watch_calendar_frame(es, date(2026, 2, 28)).size, (64, 64))
        self.assertEqual(watch_calendar_frame(es, date(2026, 8, 31)).size, (64, 64))


if __name__ == "__main__":
    unittest.main()
