import unittest

from retro_pixoo.lb_export import SAMPLE_YEAR, DiaryRow, TagSummary, load_sample_diary
from retro_pixoo.ra import ImageFetcher
from retro_pixoo.render import CYAN, GOLD, GREY, LB_ORANGE, RED, WHITE
from retro_pixoo.tags_render import tag_frame, tag_frames


class TagRenderTests(unittest.TestCase):
    def setUp(self):
        self.f = ImageFetcher(offline=True)

    def test_four_frames_64_rgb(self):
        frames = tag_frames(load_sample_diary(), lambda t, y: "", self.f, SAMPLE_YEAR)
        self.assertEqual(len(frames), 4)
        for img in frames:
            self.assertEqual((img.size, img.mode), ((64, 64), "RGB"))

    def test_count_in_tag_colour(self):
        row = DiaryRow("Tomboy", 2011, 5.0, ("theater:frida",), "2026-11-23", "2026-11-24")
        img = tag_frame("FRIDA", LB_ORANGE, TagSummary(167, row), 2026, "", self.f)
        self.assertTrue(any(img.getpixel((x, y)) == LB_ORANGE for x in range(32, 64) for y in range(10, 20)))
        self.assertTrue(any(img.getpixel((x, y)) == WHITE for x in range(64) for y in range(52, 64)))

    def test_title_wraps_to_two_lines(self):
        row = DiaryRow("Godzilla Minus Zero", 2026, 5.0, (), "2026-11-15", "2026-11-16")
        img = tag_frame("REGAL", CYAN, TagSummary(35, row), 2026, "", self.f)
        self.assertTrue(any(img.getpixel((x, y)) == WHITE for x in range(64) for y in range(58, 63)))

    def test_none_yet(self):
        img = tag_frame("CAITLIN", RED, TagSummary(0, None), 2026, "", self.f)
        self.assertTrue(any(img.getpixel((x, y)) == GREY for x in range(64) for y in range(52, 58)))
        self.assertFalse(any(img.getpixel((x, y)) == GOLD for x in range(32, 64) for y in range(44, 50)))

    def test_poster_lookup_uses_title_and_year(self):
        seen = []
        tag_frames(load_sample_diary(), lambda t, y: seen.append((t, y)) or "", self.f, SAMPLE_YEAR)
        self.assertEqual(len(seen), 4)
