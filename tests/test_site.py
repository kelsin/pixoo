import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from retro_pixoo.site import write_site

COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]


def _frames(n=3):
    return [Image.new("RGB", (64, 64), COLORS[i]) for i in range(n)]


class WriteSiteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = Path(self._tmp.name) / "site"

    def test_writes_pages_and_manifest_in_order(self):
        frames = _frames()
        write_site(frames, self.out)
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(manifest["pages"], ["page1.png", "page2.png", "page3.png"])
        self.assertEqual(manifest["seconds"], 30)
        self.assertIn("generated", manifest)
        for name, frame in zip(manifest["pages"], frames):
            img = Image.open(self.out / name)
            self.assertEqual(img.size, (64, 64))
            self.assertEqual(img.convert("RGB").tobytes(), frame.tobytes())

    def test_removes_stale_pages(self):
        write_site(_frames(3), self.out)
        write_site(_frames(1), self.out)
        self.assertTrue((self.out / "page1.png").exists())
        self.assertFalse((self.out / "page2.png").exists())
        self.assertFalse((self.out / "page3.png").exists())

    def test_empty_pages_writes_empty_manifest(self):
        write_site([], self.out)
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(manifest["pages"], [])

    def test_cname_written_and_removed(self):
        write_site(_frames(1), self.out, cname="pixoo.example.com")
        self.assertEqual((self.out / "CNAME").read_text().strip(), "pixoo.example.com")
        write_site(_frames(1), self.out)
        self.assertFalse((self.out / "CNAME").exists())

    def test_nojekyll_and_index_present(self):
        write_site(_frames(1), self.out)
        self.assertTrue((self.out / ".nojekyll").exists())
        self.assertTrue((self.out / "index.html").read_text().strip())
