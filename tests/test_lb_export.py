import os
import tempfile
import unittest
from unittest import mock
import zipfile
from datetime import date
from pathlib import Path

from retro_pixoo.lb_export import (
    EXPORT_URL,
    SAMPLE_YEAR,
    PosterCache,
    TagSummary,
    export_date,
    load_export,
    load_sample_diary,
    newest_export,
    parse_diary_csv,
    request_export_if_due,
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


class RequestExportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.state = self.tmp / "sub" / "export_requested"
        self.opener = mock.Mock()

    def _request(self, today, directory=None):
        return request_export_if_due(
            directory or self.tmp, "kelsin13", today, self.state, self.opener)

    def test_due_with_no_export(self):
        self.assertTrue(self._request(date(2026, 11, 27)))
        self.opener.assert_called_once_with(EXPORT_URL)
        self.assertEqual(self.state.read_text(), "2026-11-27")

    def test_not_due_when_export_is_today(self):
        (self.tmp / "letterboxd-kelsin13-2026-11-27-01-56-utc.zip").touch()
        self.assertFalse(self._request(date(2026, 11, 27)))
        self.opener.assert_not_called()

    def test_not_due_when_already_requested_today(self):
        self.assertTrue(self._request(date(2026, 11, 27)))
        self.assertFalse(self._request(date(2026, 11, 27)))
        self.opener.assert_called_once()

    def test_due_again_next_day(self):
        self.assertTrue(self._request(date(2026, 11, 27)))
        self.assertTrue(self._request(date(2026, 11, 28)))
        self.assertEqual(self.opener.call_count, 2)
        self.assertEqual(self.state.read_text(), "2026-11-28")

    @unittest.skipIf(os.geteuid() == 0, "root ignores directory permissions")
    def test_unreadable_dir_does_not_request(self):
        d = self.tmp / "locked"
        d.mkdir()
        d.chmod(0)
        self.addCleanup(d.chmod, 0o700)
        self.assertFalse(self._request(date(2026, 11, 27), d))
        self.opener.assert_not_called()


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

    def test_newest_export_user_prefix_is_anchored(self):
        (self.tmp / "letterboxd-kelsin13-2026-11-28-01-56-utc.zip").touch()
        with self.assertRaises(FileNotFoundError):
            newest_export(self.tmp, "kelsin")

    @unittest.skipIf(os.geteuid() == 0, "root ignores directory permissions")
    def test_newest_export_unreadable_dir_raises_permission_error(self):
        d = self.tmp / "locked"
        d.mkdir()
        (d / "letterboxd-kelsin13-2026-11-28-01-56-utc.zip").touch()
        d.chmod(0)
        self.addCleanup(d.chmod, 0o700)
        with self.assertRaises(PermissionError):
            newest_export(d, "kelsin13")

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
