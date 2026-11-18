import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from retro_pixoo.letterboxd import load_sample_feed
from retro_pixoo.ra import ImageFetcher, load_sample
from retro_pixoo.render import diary_frame, last_watched_frame, profile_frame, recent_frame
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
        self.assertEqual(len(pages), 4)
        expected = [
            profile_frame(p, self.fetcher), recent_frame(p, self.fetcher),
            last_watched_frame(e, self.fetcher), diary_frame(e, self.fetcher),
        ]
        for got, want in zip(pages, expected):
            self.assertEqual(got.tobytes(), want.tobytes())

    def test_ra_failure_keeps_letterboxd(self):
        e = load_sample_feed()
        pages, errors = collect_pages(_boom("no key"), lambda: e, self.fetcher)
        self.assertEqual(len(pages), 2)
        self.assertEqual(errors, ["retroachievements: no key"])

    def test_all_fail(self):
        pages, errors = collect_pages(_boom("a"), _boom("b"), self.fetcher)
        self.assertEqual(pages, [])
        self.assertEqual(len(errors), 2)

    def test_main_sample_preview(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main(["--sample", "--preview", d]), 0)
            self.assertTrue((Path(d) / "preview.gif").exists())
            self.assertTrue((Path(d) / "page4_led.png").exists())

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

    def test_empty_exception_message_uses_type_name(self):
        def lb():
            raise TimeoutError()
        _, errors = collect_pages(load_sample, lb, self.fetcher)
        self.assertEqual(errors, ["letterboxd: TimeoutError"])


if __name__ == "__main__":
    unittest.main()
