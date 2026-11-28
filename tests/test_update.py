import contextlib
import io
import tempfile
import zipfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from retro_pixoo.bgg import load_sample_plays
from retro_pixoo.bgg_render import (
    bgg_h_frame, bgg_recent_frame, bgg_stats_frame, bgg_top_frame,
)
from retro_pixoo.lb_export import SAMPLE_YEAR, PosterCache, load_latest, load_sample_diary
from retro_pixoo.letterboxd import load_sample_feed
from retro_pixoo.motivation import breathe_frame, handhelds_frame, scroll_frame, voice_frame
from retro_pixoo.ra import ImageFetcher, load_sample
from retro_pixoo.render import (
    diary_frame, last_watched_frame, month_stats_frame, profile_frame, recent_frame, recent_games_frame,
    systems_frame, watch_calendar_frame,
)
from retro_pixoo.tags_render import tag_frames
from retro_pixoo import render
from retro_pixoo.update import collect_pages, main


def _boom(msg):
    def f():
        raise RuntimeError(msg)
    return f


SAMPLE_CSV = Path(__file__).parent.parent / "retro_pixoo" / "sample_diary.csv"


def _write_export(directory, day):
    """Write a Letterboxd export zip dated `day` holding the sample diary.csv; return its name."""
    name = f"letterboxd-kelsin13-{day}-00-00-utc.zip"
    with zipfile.ZipFile(Path(directory) / name, "w") as zf:
        zf.writestr("diary.csv", SAMPLE_CSV.read_text(encoding="utf-8"))
    return name


class _TempPosterCache(unittest.TestCase):
    """Live-mode main() builds PosterCache(CACHE_PATH); keep it off the real cache file."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch("retro_pixoo.update.CACHE_PATH", Path(tmp.name) / "posters.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch("retro_pixoo.update.REQUEST_PATH", Path(tmp.name) / "export_requested")
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch("retro_pixoo.update.open_in_browser")
        self.open_in_browser = patcher.start()
        self.addCleanup(patcher.stop)


class UpdateTests(_TempPosterCache):
    def setUp(self):
        super().setUp()
        self.fetcher = ImageFetcher(offline=True)

    def test_both_sources_order(self):
        p, e = load_sample(), load_sample_feed()
        pages, errors = collect_pages(lambda: p, lambda: e, self.fetcher)
        self.assertEqual(errors, [])
        self.assertEqual(len(pages), 10)
        expected = [
            profile_frame(p, self.fetcher), recent_frame(p, self.fetcher),
            recent_games_frame(p, self.fetcher), systems_frame(p, self.fetcher),
            voice_frame(),
            last_watched_frame(e, self.fetcher), diary_frame(e, self.fetcher),
            month_stats_frame(e), watch_calendar_frame(e),
            scroll_frame(),
        ]
        for got, want in zip(pages, expected):
            self.assertEqual(got.tobytes(), want.tobytes())

    def test_frames_has_four_ra_pages(self):
        self.assertEqual(len(render.frames(load_sample(), self.fetcher)), 4)

    def test_ra_failure_keeps_letterboxd(self):
        e = load_sample_feed()
        pages, errors = collect_pages(_boom("no key"), lambda: e, self.fetcher)
        self.assertEqual(len(pages), 5)
        self.assertEqual(pages[4].tobytes(), voice_frame().tobytes())
        self.assertEqual(errors, ["retroachievements: no key"])

    def test_all_fail(self):
        pages, errors = collect_pages(_boom("a"), _boom("b"), self.fetcher)
        self.assertEqual(pages, [])
        self.assertEqual(len(errors), 2)

    def test_main_sample_preview(self):
        with tempfile.TemporaryDirectory() as d, \
             mock.patch("retro_pixoo.update.Pixoo") as pixoo:
            self.assertEqual(main(["--sample", "--preview", d, "--send", ""]), 0)
            pixoo.assert_not_called()
            self.assertTrue((Path(d) / "preview.gif").exists())
            self.assertTrue((Path(d) / "page5_led.png").exists())

    def test_main_no_pages_does_not_send(self):
        with mock.patch("retro_pixoo.update.RAClient", side_effect=RuntimeError("x")), \
             mock.patch("retro_pixoo.update.LetterboxdClient", side_effect=RuntimeError("y")), \
             mock.patch("retro_pixoo.update.Pixoo") as pixoo, \
             tempfile.TemporaryDirectory() as empty:
            self.assertEqual(main(["--send", "1.2.3.4", "--no-preview", "--lb-export-dir", empty]), 1)
            pixoo.assert_not_called()

    def test_main_send_failure_returns_1(self):
        pixoo = mock.MagicMock()
        pixoo.return_value.show.side_effect = OSError("down")
        with mock.patch("retro_pixoo.update.Pixoo", pixoo), \
             mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(main(["--sample", "--send", "1.2.3.4"]), 1)
        self.assertIn("pixoo: down", err.getvalue())

    def test_main_send_defaults_to_pixoo_ip_env(self):
        with mock.patch.dict("os.environ", {"PIXOO_IP": "5.6.7.8"}), \
             mock.patch("retro_pixoo.update.Pixoo") as pixoo:
            self.assertEqual(main(["--sample"]), 0)
        pixoo.assert_called_once_with("5.6.7.8", "/post")

    def test_empty_exception_message_uses_type_name(self):
        def lb():
            raise TimeoutError()
        _, errors = collect_pages(load_sample, lb, self.fetcher)
        self.assertEqual(errors, ["letterboxd: TimeoutError"])


class BggUpdateTests(_TempPosterCache):
    def setUp(self):
        super().setUp()
        self.fetcher = ImageFetcher(offline=True)
        self.p, self.e = load_sample(), load_sample_feed()
        self.plays = load_sample_plays()

    def test_bgg_pages_after_letterboxd(self):
        pages, errors = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher, bgg=lambda: self.plays)
        self.assertEqual(errors, [])
        self.assertEqual(len(pages), 15)
        expected = [bgg_h_frame(self.plays), bgg_recent_frame(self.plays),
                    bgg_top_frame(self.plays), bgg_stats_frame(self.plays)]
        for got, want in zip(pages[10:14], expected):
            self.assertEqual(got.tobytes(), want.tobytes())

    def test_three_sources_order(self):
        pages, _ = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher, bgg=lambda: self.plays)
        self.assertEqual(len(pages), 15)
        for i, want in ((4, voice_frame()), (9, scroll_frame()), (14, breathe_frame())):
            self.assertEqual(pages[i].tobytes(), want.tobytes())

    def test_bgg_empty_pages_no_breathe(self):
        pages, _ = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher,
            bgg=lambda: self.plays, bgg_pages=())
        self.assertEqual(len(pages), 10)
        self.assertNotIn(breathe_frame().tobytes(), [pg.tobytes() for pg in pages])

    def test_bgg_failure_no_breathe(self):
        pages, errors = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher, bgg=_boom("x"))
        self.assertEqual(len(pages), 10)
        self.assertNotIn(breathe_frame().tobytes(), [pg.tobytes() for pg in pages])
        self.assertIn("bgg: x", errors)

    def test_bgg_pages_selection(self):
        pages, _ = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher,
            bgg=lambda: self.plays, bgg_pages=("h",))
        self.assertEqual(len(pages), 12)

    def test_bgg_failure_keeps_others(self):
        pages, errors = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher, bgg=_boom("nope"))
        self.assertEqual(len(pages), 10)
        self.assertEqual(errors, ["bgg: nope"])

    def test_bgg_thumbs_called_once_with_needed(self):
        from retro_pixoo.bgg_render import needed_games

        calls = []

        def thumbs(ids):
            calls.append(list(ids))
            return {}

        collect_pages(lambda: self.p, lambda: self.e, self.fetcher,
                      bgg=lambda: self.plays, bgg_thumbs=thumbs)
        want = [g for g, _ in needed_games(self.plays, ("h", "recent", "top", "stats"))]
        self.assertEqual(calls, [want])

    def test_bgg_thumbs_failure_not_an_error(self):
        pages, errors = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher,
            bgg=lambda: self.plays, bgg_thumbs=lambda ids: 1 / 0)
        self.assertEqual(errors, [])
        self.assertEqual(len(pages), 15)

    def test_main_sample_writes_twenty_pages(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main(["--sample", "--preview", d, "--send", ""]), 0)
            self.assertEqual(len(list(Path(d).glob("page*_64.png"))), 20)

    def test_main_bgg_pages_subset(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                main(["--sample", "--bgg-pages", "top,h", "--preview", d, "--send", ""]), 0)
            self.assertEqual(len(list(Path(d).glob("page*_64.png"))), 18)

    def test_main_unknown_bgg_page(self):
        with mock.patch("sys.stderr", new_callable=io.StringIO), \
             self.assertRaises(SystemExit):
            main(["--sample", "--bgg-pages", "nope"])

    def test_main_live_without_token(self):
        with mock.patch.dict("os.environ", {}, clear=False) as env, \
             mock.patch("retro_pixoo.update.RAClient") as ra, \
             mock.patch("retro_pixoo.update.LetterboxdClient") as lb, \
             mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            env.pop("BGG_TOKEN", None)
            ra.return_value.profile.return_value = load_sample()
            lb.return_value.diary.return_value = load_sample_feed()
            with tempfile.TemporaryDirectory() as d:
                _write_export(d, f"{date.today():%Y-%m-%d}")
                self.assertEqual(main(["--send", "", "--no-preview", "--lb-export-dir", d]), 0)
        self.assertEqual(err.getvalue(), "")


class TagUpdateTests(_TempPosterCache):
    def setUp(self):
        super().setUp()
        self.fetcher = ImageFetcher(offline=True)
        self.p, self.e = load_sample(), load_sample_feed()
        self.plays = load_sample_plays()

    def _collect(self, **kw):
        return collect_pages(lambda: self.p, lambda: self.e, self.fetcher, bgg=lambda: self.plays,
                             posters=PosterCache(None), year=SAMPLE_YEAR, **kw)

    def test_tag_pages_after_bgg(self):
        pages, errors = self._collect(tags=load_sample_diary)
        self.assertEqual(errors, [])
        self.assertEqual(len(pages), 20)
        want = tag_frames(load_sample_diary(), PosterCache(None).get, self.fetcher, SAMPLE_YEAR)
        for got, w in zip(pages[15:19], want):
            self.assertEqual(got.tobytes(), w.tobytes())
        self.assertEqual(pages[19].tobytes(), handhelds_frame().tobytes())

    def test_tags_failure_reported(self):
        pages, errors = self._collect(tags=_boom("no export"))
        self.assertEqual(len(pages), 15)
        self.assertIn("letterboxd export: no export", errors)

    def test_rss_posters_feed_the_cache(self):
        cache = PosterCache(None)
        collect_pages(_boom("x"), lambda: self.e, self.fetcher,
                      tags=load_sample_diary, posters=cache, year=SAMPLE_YEAR)
        self.assertEqual(cache.get(self.e[0].title, self.e[0].year), self.e[0].poster_url)

    def test_poster_cache_failure_is_ignored(self):
        cache = mock.Mock(wraps=PosterCache(None))
        cache.update.side_effect = OSError("read-only")
        pages, errors = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher, bgg=lambda: self.plays,
            tags=load_sample_diary, posters=cache, year=SAMPLE_YEAR)
        self.assertEqual(errors, [])
        self.assertEqual(len(pages), 20)

    def test_live_main_requests_export_when_none(self):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as d, \
             mock.patch("retro_pixoo.update.RAClient", side_effect=RuntimeError("x")), \
             mock.patch("retro_pixoo.update.LetterboxdClient", side_effect=RuntimeError("y")), \
             mock.patch("sys.stderr", new_callable=io.StringIO), \
             contextlib.redirect_stdout(out):
            main(["--send", "", "--no-preview", "--lb-export-dir", d])
        self.open_in_browser.assert_called_once_with("https://letterboxd.com/data/export/")
        self.assertIn("letterboxd export: requested a new export", out.getvalue())

    def test_live_main_request_failure_is_not_an_error(self):
        self.open_in_browser.side_effect = OSError("no open")
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as d, \
             mock.patch("retro_pixoo.update.RAClient", side_effect=RuntimeError("x")), \
             mock.patch("retro_pixoo.update.LetterboxdClient", side_effect=RuntimeError("y")), \
             mock.patch("sys.stderr", err):
            main(["--send", "", "--no-preview", "--lb-export-dir", d])
        self.assertIn("letterboxd export: request failed: no open", err.getvalue())

    def test_sample_main_never_requests_export(self):
        main(["--sample", "--send", "", "--no-preview"])
        self.open_in_browser.assert_not_called()

    def test_load_latest_stale_export_warns(self):
        with tempfile.TemporaryDirectory() as d:
            name = _write_export(d, "2026-11-01")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rows = load_latest(Path(d), "kelsin13", date(2026, 11, 27))
            self.assertEqual(len(rows), len(load_sample_diary()))
            self.assertIn(f"letterboxd export: export is 26 days old ({name})", err.getvalue())
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                load_latest(Path(d), "kelsin13", date(2026, 11, 5))
            self.assertEqual(err.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
