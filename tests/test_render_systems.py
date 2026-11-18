import unittest

from retro_pixoo.ra import ImageFetcher, SystemStat, load_sample
from retro_pixoo.render import BG, GREY, system_tag, systems_frame


def _profile(systems):
    p = load_sample()
    p.systems = systems
    return p


class SystemsRenderTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = ImageFetcher(offline=True)

    def test_known_tags(self):
        self.assertEqual(system_tag("SNES/Super Famicom")[0], "SNES")
        self.assertEqual(system_tag("Game Boy Advance")[0], "GBA")
        self.assertEqual(system_tag("PlayStation")[0], "PS1")
        self.assertEqual(system_tag("Nintendo 64")[0], "N64")

    def test_unknown_tag_is_grey_first_four(self):
        self.assertEqual(system_tag("Pokemon Mini"), ("POKE", GREY))

    def test_unknown_tag_skips_punctuation(self):
        self.assertEqual(system_tag("Neo-Geo CD"), ("NEOG", GREY))

    def test_empty_console_renders(self):
        frame = systems_frame(_profile([SystemStat("", 1, 2, "")]), self.fetcher)
        self.assertEqual(frame.size, (64, 64))

    def test_frame_size_sample(self):
        self.assertEqual(systems_frame(load_sample(), self.fetcher).size, (64, 64))

    def test_empty_differs_from_sample(self):
        empty = systems_frame(_profile([]), self.fetcher)
        self.assertEqual(empty.size, (64, 64))
        self.assertNotEqual(empty.tobytes(), systems_frame(load_sample(), self.fetcher).tobytes())

    def test_partial_grid_leaves_cells_blank(self):
        frame = systems_frame(_profile([SystemStat("Nintendo 64", 5, 50, "")]), self.fetcher)
        region = frame.crop((32, 36, 64, 64))
        self.assertEqual(set(region.getdata()), {BG})

    def test_big_numbers_stay_in_cell(self):
        frame = systems_frame(_profile([SystemStat("Nintendo 64", 123, 12345, "")]), self.fetcher)
        region = frame.crop((32, 7, 64, 64))
        self.assertEqual(set(region.getdata()), {BG})


if __name__ == "__main__":
    unittest.main()
