import unittest

from retro_pixoo.letterboxd import DiaryEntry, load_sample_feed, parse_feed

NS = (
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:letterboxd="https://letterboxd.com" '
    'xmlns:tmdb="https://themoviedb.org"'
)


class LetterboxdTests(unittest.TestCase):
    def test_sample_feed_skips_lists(self):
        entries = load_sample_feed()
        self.assertEqual(len(entries), 8)
        self.assertNotIn("Preordered", [e.title for e in entries])

    def test_first_entry_fields(self):
        entries = load_sample_feed()
        e = entries[0]
        self.assertEqual(
            (e.title, e.year, e.rating, e.liked, e.rewatch, e.watched_date),
            ("Wildwood", 2026, 5.0, True, False, "2026-11-16"),
        )
        self.assertTrue(
            e.poster_url.startswith(
                "https://a.ltrbxd.com/resized/film-poster/7/0/9/4/6/0/709460-wildwood-2026"
            )
        )
        self.assertIsInstance(e, DiaryEntry)
        self.assertEqual(entries[1].title, "Minority Report")
        self.assertIs(entries[1].rewatch, True)

    def test_unrated_and_half_star(self):
        xml = f"""<?xml version="1.0"?>
<rss version="2.0" {NS}><channel>
<item><title>A, 2000</title>
<letterboxd:watchedDate>2026-01-01</letterboxd:watchedDate>
<letterboxd:rewatch>No</letterboxd:rewatch>
<letterboxd:filmTitle>A</letterboxd:filmTitle>
<letterboxd:filmYear>2000</letterboxd:filmYear>
<description>no image</description></item>
<item><title>B, 2001 - ★★★½</title>
<letterboxd:watchedDate>2026-01-02</letterboxd:watchedDate>
<letterboxd:rewatch>No</letterboxd:rewatch>
<letterboxd:filmTitle>B</letterboxd:filmTitle>
<letterboxd:filmYear>2001</letterboxd:filmYear>
<letterboxd:memberRating>3.5</letterboxd:memberRating>
<description>x</description></item>
</channel></rss>"""
        a, b = parse_feed(xml)
        self.assertIsNone(a.rating)
        self.assertIs(a.liked, False)
        self.assertEqual(a.poster_url, "")
        self.assertEqual(b.rating, 3.5)

    def test_parse_feed_bytes_uses_declared_encoding(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<rss {NS}><channel><item><letterboxd:filmTitle>Amélie</letterboxd:filmTitle>'
            '</item></channel></rss>'
        ).encode("utf-8")
        self.assertEqual(parse_feed(xml)[0].title, "Amélie")


if __name__ == "__main__":
    unittest.main()
