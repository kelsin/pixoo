import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from retro_pixoo.lb_export import (
    SAMPLE_YEAR,
    PosterCache,
    TagSummary,
    export_date,
    load_export,
    load_sample_diary,
    newest_export,
    parse_diary_csv,
    summarize,
)
from retro_pixoo.letterboxd import DiaryEntry

CSV = (
    "Date,Name,Year,Letterboxd URI,Rating,Rewatch,Tags,Watched Date\n"
    '2026-11-17,Wildwood,2026,u,5,,"people:kerrigan, theater:regal, people:caitlin",2026-11-16\n'
    "2026-11-24,Tomboy,2011,u,,,theater:frida,2026-11-23\n"
    "2026-11-25,Water Lilies,,u,4.5,Yes,theater:frida,2026-11-23\n"
    "2025-12-30,Old,1999,u,3,,theater:frida,2025-12-29\n"
)


class LbExportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def test_parse_fields(self):
        rows = parse_diary_csv(CSV)
        self.assertEqual(
            rows[0].tags, ("people:kerrigan", "theater:regal", "people:caitlin")
        )
        self.assertIsNone(rows[1].rating)
        self.assertIsNone(rows[2].year)
        self.assertEqual(
            (rows[2].rating, rows[2].watched, rows[2].logged),
            (4.5, "2026-11-23", "2026-11-25"),
        )

    def test_summarize_year_and_tiebreak(self):
        s = summarize(parse_diary_csv(CSV), "theater:frida", 2026)
        self.assertEqual(s.count, 2)
        self.assertEqual(s.latest.name, "Water Lilies")

    def test_summarize_none(self):
        self.assertEqual(
            summarize(parse_diary_csv(CSV), "people:caitlin", 2025), TagSummary(0, None)
        )

    def test_newest_export_and_date(self):
        for n in (
            "letterboxd-kelsin13-2026-11-21-01-00-utc.zip",
            "letterboxd-kelsin13-2026-11-28-01-56-utc.zip",
            "letterboxd-someoneelse-2026-12-01-00-00-utc.zip",
        ):
            (self.tmp / n).touch()
        newest = newest_export(self.tmp, "kelsin13")
        self.assertEqual(newest.name, "letterboxd-kelsin13-2026-11-28-01-56-utc.zip")
        self.assertEqual(export_date(newest), date(2026, 11, 28))

    def test_newest_export_missing(self):
        with self.assertRaises(FileNotFoundError):
            newest_export(self.tmp, "kelsin13")

    def test_load_export_reads_zip(self):
        z = self.tmp / "letterboxd-kelsin13-2026-11-28-01-56-utc.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("diary.csv", CSV.encode("utf-8"))
        self.assertEqual(len(load_export(z)), 4)

    def test_poster_cache_roundtrip(self):
        p = self.tmp / "sub" / "posters.json"
        c = PosterCache(p)
        c.update([DiaryEntry("Tomboy", 2011, None, False, False, "2026-11-23", "http://p")])
        self.assertEqual(PosterCache(p).get("Tomboy", 2011), "http://p")
        self.assertEqual(c.get("Nope", 2000), "")

    def test_poster_cache_corrupt_file(self):
        p = self.tmp / "posters.json"
        p.write_text("{not json")
        self.assertEqual(PosterCache(p).get("x", 1), "")

    def test_sample_diary_has_all_tags(self):
        rows = load_sample_diary()
        for tag in ("theater:frida", "theater:regal", "people:kerrigan", "people:caitlin"):
            self.assertGreater(summarize(rows, tag, SAMPLE_YEAR).count, 0)
