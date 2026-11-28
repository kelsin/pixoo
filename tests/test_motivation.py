import unittest
from pathlib import Path

from PIL import Image

from retro_pixoo.motivation import SLIDES, breathe_frame, handhelds_frame, scroll_frame, voice_frame
from retro_pixoo.render import BG, GOLD, RED


class MotivationTests(unittest.TestCase):
    def test_slides_order(self):
        self.assertEqual(SLIDES, (voice_frame, scroll_frame, breathe_frame, handhelds_frame))

    def test_handhelds_matches_approved_mockup(self):
        want = Image.open(Path(__file__).parent / "fixtures" / "handhelds_64.png").convert("RGB")
        self.assertEqual(handhelds_frame().tobytes(), want.tobytes())

    def test_size_mode_and_not_blank(self):
        for f in SLIDES:
            img = f()
            self.assertEqual((img.size, img.mode), ((64, 64), "RGB"))
            self.assertGreater(len(img.getcolors(4096)), 2)

    def test_slides_differ(self):
        self.assertEqual(len({f().tobytes() for f in SLIDES}), 4)

    def test_text_rows(self):
        # second text line colour appears in rows 52..56
        for f, color in ((voice_frame, GOLD), (scroll_frame, GOLD), (breathe_frame, RED), (handhelds_frame, GOLD)):
            img = f()
            self.assertTrue(any(img.getpixel((x, y)) == color for x in range(64) for y in range(52, 57)))

    def test_voice_art_sits_close_to_text(self):
        img = voice_frame()
        lowest = max(y for y in range(44) for x in range(64) if img.getpixel((x, y)) != BG)
        self.assertGreaterEqual(lowest, 38)
        self.assertLessEqual(lowest, 42)


if __name__ == "__main__":
    unittest.main()
