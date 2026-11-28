import os
import tempfile
import unittest
from unittest import mock
import zipfile
import contextlib
import io
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from retro_pixoo.lb_export import (
    EXPORT_URL,
    SAMPLE_YEAR,
    PosterCache,
    TagSummary,
    export_time,
    ingest_exports,
    load_export,
    load_latest,
    load_saved,
    load_sample_diary,
    newest_export,
    parse_diary_csv,
    request_export_if_due,
    save_export,
    summarize,
    wait_for_new_export,
)
from retro_pixoo.letterboxd import DiaryEntry

CSV = (
    "Date,Name,Year,Letterboxd URI,Rating,Rewatch,Tags,Watched Date\n"
    '2026-11-17,Wildwood,2026,u,5,,"people:kerrigan, theater:regal, people:caitlin",2026-11-16\n'
    "2026-11-24,Tomboy,2011,u,,,theater:frida,2026-11-23\n"
    "2026-11-25,Water Lilies,,u,4.5,Yes,theater:frida,2026-11-23\n"
    "2025-12-30,Old,1999,u,3,,theater:frida,2025-12-29\n"
)


PST = timezone(timedelta(hours=-8))
NEWEST = "letterboxd-kelsin13-2026-11-28-01-56-utc.zip"


def _at(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute, tzinfo=PST)


def _real_zip(path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("diary.csv", CSV)


class RequestExportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.state = self.tmp / "sub" / "export_requested"
        self.data = self.tmp / "data" / "letterboxd-diary.json"
        self.opener = mock.Mock()

    def _request(self, now, directory=None):
        return request_export_if_due(
            directory or self.tmp, "kelsin13", now, self.state, self.data, self.opener)

    def test_not_due_before_six(self):
        self.assertFalse(self._request(_at(27, 5, 59)))
        self.opener.assert_not_called()

    def test_due_at_six_with_no_export(self):
        self.assertTrue(self._request(_at(27, 6)))
        self.opener.assert_called_once_with(EXPORT_URL)
        self.assertEqual(self.state.read_text(), "2026-11-27")

    def test_not_due_when_export_is_from_today_local(self):
        # 2026-11-28 01:56 UTC is 2026-11-27 17:56 -08:00
        (self.tmp / NEWEST).touch()
        self.assertFalse(self._request(_at(27, 18)))
        self.opener.assert_not_called()

    def test_export_downloaded_before_six_counts(self):
        (self.tmp / "letterboxd-kelsin13-2026-11-27-14-00-utc.zip").touch()  # 06:00 -08:00
        (self.tmp / "letterboxd-kelsin13-2026-11-28-12-00-utc.zip").touch()  # 04:00 on the 28th
        self.assertFalse(self._request(_at(28, 7)))

    def test_due_next_local_morning(self):
        (self.tmp / NEWEST).touch()
        self.assertFalse(self._request(_at(27, 18)))
        self.assertTrue(self._request(_at(28, 6)))
        self.opener.assert_called_once_with(EXPORT_URL)

    def test_not_due_when_already_requested_today(self):
        self.assertTrue(self._request(_at(27, 6)))
        self.assertFalse(self._request(_at(27, 7)))
        self.opener.assert_called_once()

    def test_due_again_next_day(self):
        self.assertTrue(self._request(_at(27, 6)))
        self.assertTrue(self._request(_at(28, 6)))
        self.assertEqual(self.opener.call_count, 2)
        self.assertEqual(self.state.read_text(), "2026-11-28")

    def test_not_due_when_saved_data_is_from_today_and_downloads_empty(self):
        # 2026-11-28 01:56 UTC is 2026-11-27 17:56 -08:00
        save_export(self.data, self.tmp / NEWEST, CSV)
        self.assertFalse(self._request(_at(27, 18)))
        self.opener.assert_not_called()
        self.assertTrue(self._request(_at(28, 6)))

    @unittest.skipIf(os.geteuid() == 0, "root ignores directory permissions")
    def test_unreadable_dir_does_not_request(self):
        d = self.tmp / "locked"
        d.mkdir()
        d.chmod(0)
        self.addCleanup(d.chmod, 0o700)
        self.assertFalse(self._request(_at(27, 6), d))
        self.opener.assert_not_called()


class WaitForNewExportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.now = 0.0
        self.sleeps = []

    def _clock(self):
        return self.now

    def _sleeper(self, action=None):
        def sleep(s):
            self.sleeps.append(s)
            self.now += s
            if action:
                action(len(self.sleeps))
        return sleep

    def _wait(self, previous, action=None, timeout=10, poll=2):
        return wait_for_new_export(self.tmp, "kelsin13", previous, timeout, poll,
                                   sleep=self._sleeper(action), clock=self._clock)

    def test_returns_file_appearing_after_polls(self):
        old = self.tmp / "letterboxd-kelsin13-2026-11-26-01-00-utc.zip"
        _real_zip(old)
        new = self.tmp / NEWEST
        got = self._wait(old.name, lambda n: _real_zip(new) if n == 2 else None)
        self.assertEqual(got, new)
        self.assertEqual(self.sleeps, [2, 2])

    def test_empty_directory_is_not_yet(self):
        new = self.tmp / NEWEST
        self.assertEqual(self._wait(None, lambda n: _real_zip(new) if n == 1 else None), new)

    def test_zero_byte_placeholder_ignored_until_replaced(self):
        new = self.tmp / NEWEST
        new.touch()

        def action(n):
            if n == 2:
                _real_zip(new)
        self.assertEqual(self._wait(None, action), new)
        self.assertEqual(len(self.sleeps), 2)

    def test_zip_without_diary_is_incomplete(self):
        new = self.tmp / NEWEST
        with zipfile.ZipFile(new, "w") as zf:
            zf.writestr("other.csv", "x")
        self.assertIsNone(self._wait(None))

    def test_unchanged_previous_times_out_without_real_sleep(self):
        old = self.tmp / NEWEST
        _real_zip(old)
        self.assertIsNone(self._wait(old.name))
        self.assertEqual(sum(self.sleeps), 10)


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

    def test_newest_export_and_time(self):
        for n in (
            "letterboxd-kelsin13-2026-11-21-01-00-utc.zip",
            "letterboxd-kelsin13-2026-11-28-01-56-utc.zip",
            "letterboxd-someoneelse-2026-12-01-00-00-utc.zip",
        ):
            (self.tmp / n).touch()
        newest = newest_export(self.tmp, "kelsin13")
        self.assertEqual(newest.name, "letterboxd-kelsin13-2026-11-28-01-56-utc.zip")
        self.assertEqual(export_time(newest), datetime(2026, 11, 28, 1, 56, tzinfo=timezone.utc))

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


OLD = "letterboxd-kelsin13-2026-11-20-12-00-utc.zip"
MID = "letterboxd-kelsin13-2026-11-24-12-00-utc.zip"
OTHER = "letterboxd-someoneelse-2026-11-29-01-00-utc.zip"
ONE_ROW_CSV = (
    "Date,Name,Year,Letterboxd URI,Rating,Rewatch,Tags,Watched Date\n"
    "2026-11-17,Wildwood,2026,u,5,,theater:frida,2026-11-16\n"
)


def _zip_with(path, csv_text):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("diary.csv", csv_text)


class _TmpCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.dl = self.tmp / "dl"
        self.dl.mkdir()
        self.data = self.tmp / "support" / "letterboxd-diary.json"

    def names(self):
        return sorted(p.name for p in self.dl.iterdir())


class SavedDataTests(_TmpCase):
    def test_roundtrip(self):
        save_export(self.data, self.dl / NEWEST, CSV)
        at, rows = load_saved(self.data)
        self.assertEqual(at, datetime(2026, 11, 28, 1, 56, tzinfo=timezone.utc))
        self.assertEqual(rows, parse_diary_csv(CSV))
        self.assertEqual(
            json.loads(self.data.read_text()),
            {"export": NEWEST, "exported_at": "2026-11-28T01:56:00+00:00", "diary_csv": CSV})

    def test_save_is_atomic_and_leaves_no_temp_files(self):
        save_export(self.data, self.dl / NEWEST, CSV)
        save_export(self.data, self.dl / NEWEST, ONE_ROW_CSV)
        self.assertEqual([p.name for p in self.data.parent.iterdir()], [self.data.name])
        self.assertEqual(len(load_saved(self.data)[1]), 1)

    def test_missing_is_none(self):
        self.assertIsNone(load_saved(self.data))

    def test_corrupt_is_none(self):
        self.data.parent.mkdir(parents=True)
        for text in ("{not json", "[]", '{"export": "x"}',
                     '{"export": "x", "exported_at": "nope", "diary_csv": "a"}'):
            self.data.write_text(text)
            self.assertIsNone(load_saved(self.data), text)


class IngestTests(_TmpCase):
    def _ingest(self):
        return ingest_exports(self.dl, "kelsin13", self.data)

    def test_newest_complete_saved_and_it_plus_older_deleted(self):
        _zip_with(self.dl / OLD, ONE_ROW_CSV)
        _zip_with(self.dl / NEWEST, CSV)
        _zip_with(self.dl / OTHER, ONE_ROW_CSV)
        (self.dl / "notes.txt").write_text("keep")
        (self.dl / "letterboxd-kelsin13-notes.zip").write_text("keep")
        self.assertEqual(self._ingest(), NEWEST)
        self.assertEqual(self.names(), ["letterboxd-kelsin13-notes.zip", OTHER, "notes.txt"])
        self.assertEqual(load_saved(self.data)[1], parse_diary_csv(CSV))

    def test_partial_newer_zip_left_and_older_complete_ingested(self):
        _zip_with(self.dl / OLD, ONE_ROW_CSV)
        (self.dl / NEWEST).touch()
        self.assertEqual(self._ingest(), OLD)
        self.assertEqual(self.names(), [NEWEST])
        self.assertEqual(len(load_saved(self.data)[1]), 1)

    def test_zip_older_than_saved_deleted_without_overwriting(self):
        save_export(self.data, self.dl / NEWEST, CSV)
        _zip_with(self.dl / OLD, ONE_ROW_CSV)
        _zip_with(self.dl / MID, ONE_ROW_CSV)
        self.assertIsNone(self._ingest())
        self.assertEqual(self.names(), [])
        self.assertEqual(len(load_saved(self.data)[1]), 4)

    def test_same_export_as_saved_is_deleted_not_resaved(self):
        save_export(self.data, self.dl / NEWEST, CSV)
        _zip_with(self.dl / NEWEST, ONE_ROW_CSV)
        self.assertIsNone(self._ingest())
        self.assertEqual(self.names(), [])
        self.assertEqual(len(load_saved(self.data)[1]), 4)

    def test_incomplete_only_changes_nothing(self):
        (self.dl / NEWEST).touch()
        self.assertIsNone(self._ingest())
        self.assertEqual(self.names(), [NEWEST])
        self.assertFalse(self.data.exists())

    def test_broken_csv_raises_and_deletes_nothing(self):
        _zip_with(self.dl / OLD, ONE_ROW_CSV)
        _zip_with(self.dl / NEWEST, "Name\nonly a name\n")
        with self.assertRaises(KeyError):
            self._ingest()
        self.assertEqual(self.names(), [OLD, NEWEST])
        self.assertFalse(self.data.exists())

    @unittest.skipIf(os.geteuid() == 0, "root ignores directory permissions")
    def test_unreadable_dir_raises_permission_error(self):
        self.dl.chmod(0)
        self.addCleanup(self.dl.chmod, 0o700)
        with self.assertRaises(PermissionError):
            self._ingest()


class LoadLatestTests(_TmpCase):
    def _load(self, today=date(2026, 11, 28), directory=None):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rows = load_latest(directory or self.dl, "kelsin13", self.data, today)
        return rows, err.getvalue()

    def test_zip_is_ingested_and_deleted(self):
        _zip_with(self.dl / NEWEST, CSV)
        rows, err = self._load()
        self.assertEqual(rows, parse_diary_csv(CSV))
        self.assertEqual(self.names(), [])
        self.assertEqual(err, "")

    def test_no_zip_but_saved_data_keeps_pages(self):
        save_export(self.data, self.dl / NEWEST, CSV)
        rows, _ = self._load()
        self.assertEqual(rows, parse_diary_csv(CSV))

    def test_no_zip_and_nothing_saved_raises(self):
        with self.assertRaises(FileNotFoundError) as cm:
            self._load()
        self.assertEqual(
            str(cm.exception),
            f"no saved Letterboxd export and no letterboxd-kelsin13-*.zip in {self.dl}")

    @unittest.skipIf(os.geteuid() == 0, "root ignores directory permissions")
    def test_unreadable_dir_with_saved_data_warns_and_uses_it(self):
        save_export(self.data, self.dl / NEWEST, CSV)
        self.dl.chmod(0)
        self.addCleanup(self.dl.chmod, 0o700)
        rows, err = self._load()
        self.assertEqual(rows, parse_diary_csv(CSV))
        self.assertIn("letterboxd export: export update failed: ", err)
        self.assertTrue(err.rstrip().endswith("; using saved data"))

    def test_broken_csv_in_newest_zip_uses_saved_data_and_keeps_zip(self):
        save_export(self.data, self.dl / OLD, ONE_ROW_CSV)
        _zip_with(self.dl / NEWEST, "Name\nonly a name\n")
        rows, err = self._load()
        self.assertEqual(rows, parse_diary_csv(ONE_ROW_CSV))
        self.assertEqual(self.names(), [NEWEST])
        self.assertIn(f"letterboxd export: skipping unreadable export {NEWEST}: ", err)
        self.assertTrue(err.rstrip().endswith("; using saved data"))

    def test_odd_name_uses_saved_data_and_keeps_zip(self):
        odd = "letterboxd-kelsin13-2026-oops.zip"
        save_export(self.data, self.dl / OLD, ONE_ROW_CSV)
        _zip_with(self.dl / odd, CSV)
        rows, err = self._load()
        self.assertEqual(rows, parse_diary_csv(ONE_ROW_CSV))
        self.assertEqual(self.names(), [odd])
        self.assertIn(f"no -HH-MM-utc timestamp in {odd}", err)
        self.assertIn("; using saved data", err)

    def test_broken_csv_with_nothing_saved_raises(self):
        _zip_with(self.dl / NEWEST, "Name\nonly a name\n")
        with self.assertRaises(FileNotFoundError):
            self._load()
        self.assertEqual(self.names(), [NEWEST])

    def test_export_time_without_timestamp_is_clear_value_error(self):
        with self.assertRaisesRegex(ValueError, "no -HH-MM-utc timestamp in bad.zip"):
            export_time(Path("bad.zip"))

    def test_save_fsyncs_file_and_directory(self):
        with mock.patch("os.fsync") as fsync:
            save_export(self.data, self.dl / NEWEST, CSV)
        self.assertEqual(fsync.call_count, 2)

    def test_stale_warning_from_saved_exported_at(self):
        save_export(self.data, self.dl / OLD, CSV)
        _, err = self._load(today=date(2026, 11, 30))
        self.assertIn(f"letterboxd export: export is 10 days old ({OLD})", err)
        _, err = self._load(today=date(2026, 11, 25))
        self.assertEqual(err, "")
