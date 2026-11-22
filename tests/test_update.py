import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from retro_pixoo.bgg import load_sample_plays
from retro_pixoo.bgg_render import (
    bgg_h_frame, bgg_recent_frame, bgg_stats_frame, bgg_top_frame,
)
from retro_pixoo.letterboxd import load_sample_feed
from retro_pixoo.ra import ImageFetcher, load_sample
from retro_pixoo.render import (
    diary_frame, last_watched_frame, month_stats_frame, profile_frame, recent_frame, recent_games_frame,
    systems_frame, watch_calendar_frame,
)
from retro_pixoo import render
from retro_pixoo.update import collect_pages, main


def _boom(msg):
    def f():
        raise RuntimeError(msg)
    return f


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = ImageFetcher(offline=True)

    def test_both_sources_order(self):
        p, e = load_sample(), load_sample_feed()
        pages, errors = collect_pages(lambda: p, lambda: e, self.fetcher)
        self.assertEqual(errors, [])
        self.assertEqual(len(pages), 8)
        expected = [
            profile_frame(p, self.fetcher), recent_frame(p, self.fetcher),
            recent_games_frame(p, self.fetcher), systems_frame(p, self.fetcher),
            last_watched_frame(e, self.fetcher), diary_frame(e, self.fetcher),
            month_stats_frame(e), watch_calendar_frame(e),
        ]
        for got, want in zip(pages, expected):
            self.assertEqual(got.tobytes(), want.tobytes())

    def test_frames_has_four_ra_pages(self):
        self.assertEqual(len(render.frames(load_sample(), self.fetcher)), 4)

    def test_ra_failure_keeps_letterboxd(self):
        e = load_sample_feed()
        pages, errors = collect_pages(_boom("no key"), lambda: e, self.fetcher)
        self.assertEqual(len(pages), 4)
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
             mock.patch("retro_pixoo.update.Pixoo") as pixoo:
            self.assertEqual(main(["--send", "1.2.3.4"]), 1)
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


class BggUpdateTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = ImageFetcher(offline=True)
        self.p, self.e = load_sample(), load_sample_feed()
        self.plays = load_sample_plays()

    def test_bgg_pages_after_letterboxd(self):
        pages, errors = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher, bgg=lambda: self.plays)
        self.assertEqual(errors, [])
        self.assertEqual(len(pages), 12)
        expected = [bgg_h_frame(self.plays), bgg_recent_frame(self.plays),
                    bgg_top_frame(self.plays), bgg_stats_frame(self.plays)]
        for got, want in zip(pages[8:], expected):
            self.assertEqual(got.tobytes(), want.tobytes())

    def test_bgg_pages_selection(self):
        pages, _ = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher,
            bgg=lambda: self.plays, bgg_pages=("h",))
        self.assertEqual(len(pages), 9)

    def test_bgg_failure_keeps_others(self):
        pages, errors = collect_pages(
            lambda: self.p, lambda: self.e, self.fetcher, bgg=_boom("nope"))
        self.assertEqual(len(pages), 8)
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
        self.assertEqual(len(pages), 12)

    def test_main_sample_writes_twelve_pages(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main(["--sample", "--preview", d, "--send", ""]), 0)
            self.assertEqual(len(list(Path(d).glob("page*_64.png"))), 12)

    def test_main_bgg_pages_subset(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                main(["--sample", "--bgg-pages", "top,h", "--preview", d, "--send", ""]), 0)
            self.assertEqual(len(list(Path(d).glob("page*_64.png"))), 10)

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
            self.assertEqual(main(["--send", ""]), 0)
        self.assertEqual(err.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
