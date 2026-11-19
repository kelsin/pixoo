import unittest
from unittest import mock

import requests

from retro_pixoo.bgg import (
    BggClient,
    Play,
    game_counts,
    h_index,
    h_next,
    h_targets,
    parse_thumbnails,
    load_sample_plays,
    parse_plays,
    parse_total,
    top_played,
)

XML = """<plays username="k" userid="1" total="2" page="1">
<play id="1" date="2026-01-05" quantity="2" length="60"><item name="Wingspan" objecttype="thing" objectid="10"/></play>
<play id="2" date="2026-01-06"><item name="Heat" objecttype="thing" objectid="11"/></play>
</plays>"""


def P(game, n=1, gid=None, minutes=0, date="2026-03-01"):
    return Play(date, game, gid if gid is not None else abs(hash(game)) % 10000, n, minutes)


def plays_for(counts):
    return [P(name, n) for name, n in counts.items()]


class ParseTests(unittest.TestCase):
    def test_parse_plays(self):
        ps = parse_plays(XML)
        self.assertEqual(ps[0], Play("2026-01-05", "Wingspan", 10, 2, 60))
        self.assertEqual(ps[1].quantity, 1)
        self.assertEqual(ps[1].minutes, 0)
        self.assertEqual(parse_total(XML), 2)


class HIndexTests(unittest.TestCase):
    def setUp(self):
        self.plays = plays_for({"A": 5, "B": 4, "C": 3, "D": 3, "E": 1})

    def test_h_index(self):
        self.assertEqual(h_index(self.plays), 3)
        self.assertEqual(h_index([]), 0)

    def test_quantity_summed_across_plays(self):
        ps = [P("A", 2, gid=1), P("A", 1, gid=1), P("B", 3, gid=2), P("C", 3, gid=3)]
        self.assertEqual(h_index(ps), 3)

    def test_h_next(self):
        self.assertEqual(h_next(self.plays), (3, 2, "C"))
        self.assertEqual(h_next([]), (0, 1, None))

    def test_h_next_missing_games(self):
        self.assertEqual(h_next(plays_for({"A": 1})), (1, 3, "A"))

    def test_top_played(self):
        self.assertEqual(top_played(self.plays, 3), [("A", 5), ("B", 4), ("C", 3)])
        self.assertEqual(game_counts(self.plays)[3], ("D", 3))


class ClientTests(unittest.TestCase):
    def _resp(self, status, n, total):
        body = "".join(
            f'<play id="{i}" date="2026-02-01"><item name="G{i}" objectid="{i}"/></play>' for i in range(n)
        )
        r = mock.Mock(status_code=status, content=f'<plays total="{total}">{body}</plays>'.encode())
        r.raise_for_status.side_effect = None
        return r

    def test_pages_merged_and_params(self):
        with mock.patch("requests.get", side_effect=[self._resp(200, 100, 150), self._resp(200, 50, 150)]) as g:
            ps = BggClient(token="abc").plays("Kelsin", 2026)
        self.assertEqual(len(ps), 150)
        first = g.call_args_list[0]
        self.assertEqual(first.kwargs["headers"]["Authorization"], "Bearer abc")
        self.assertEqual(first.kwargs["params"]["username"], "Kelsin")
        self.assertEqual(first.kwargs["params"]["mindate"], "2026-01-01")
        self.assertEqual(first.kwargs["params"]["maxdate"], "2026-12-31")
        self.assertEqual(first.kwargs["params"]["page"], 1)
        self.assertEqual(g.call_args_list[1].kwargs["params"]["page"], 2)

    def test_error_status_raises(self):
        with mock.patch("requests.get", return_value=self._resp(401, 0, 0)):
            with self.assertRaises(RuntimeError) as cm:
                BggClient(token="abc").plays("k", 2026)
        self.assertIn("401", str(cm.exception))

    def test_no_token_raises(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError) as cm:
                BggClient().plays("k", 2026)
        self.assertEqual(str(cm.exception), "BGG_TOKEN not set")


class SampleTests(unittest.TestCase):
    def test_sample(self):
        ps = load_sample_plays()
        self.assertGreaterEqual(len(ps), 20)
        self.assertGreaterEqual(h_index([p for p in ps if p.date.startswith("2026")]), 3)


if __name__ == "__main__":
    unittest.main()


THING_XML = """<items>
<item type="boardgame" id="10"><thumbnail>http://x/10.jpg</thumbnail></item>
<item type="boardgame" id="11"><thumbnail>  </thumbnail></item>
<item type="boardgame" id="12"/>
<item type="boardgame" id="13"><thumbnail> http://x/13.jpg </thumbnail></item>
</items>"""


def _resp(status=200, text="<items/>"):
    m = mock.Mock()
    m.status_code = status
    m.content = text.encode()
    return m


class ThumbnailTests(unittest.TestCase):
    def test_parse_thumbnails(self):
        self.assertEqual(parse_thumbnails(THING_XML), {10: "http://x/10.jpg", 13: "http://x/13.jpg"})

    def test_empty_ids_no_request(self):
        with mock.patch("retro_pixoo.bgg.requests.get") as g:
            self.assertEqual(BggClient("tok").thumbnails([]), {})
            g.assert_not_called()

    def test_chunks_and_merge(self):
        def xml(ids):
            return "<items>" + "".join(
                f'<item id="{i}"><thumbnail>http://x/{i}</thumbnail></item>' for i in ids
            ) + "</items>"

        ids = list(range(1, 26))
        with mock.patch(
            "retro_pixoo.bgg.requests.get",
            side_effect=[_resp(text=xml(ids[:20])), _resp(text=xml(ids[20:]))],
        ) as g:
            out = BggClient("tok").thumbnails(ids)
        self.assertEqual(set(out), set(ids))
        self.assertEqual(g.call_count, 2)
        first, second = g.call_args_list
        self.assertEqual(first.kwargs["params"]["id"], ",".join(map(str, ids[:20])))
        self.assertEqual(second.kwargs["params"]["id"], ",".join(map(str, ids[20:])))
        self.assertEqual(first.kwargs["headers"]["Authorization"], "Bearer tok")

    def test_failure_returns_partial(self):
        first = _resp(text='<items><item id="1"><thumbnail>http://x/1</thumbnail></item></items>')
        for bad in (_resp(status=429), requests.RequestException("boom")):
            with mock.patch("retro_pixoo.bgg.requests.get", side_effect=[first, bad]):
                self.assertEqual(BggClient("tok").thumbnails(list(range(1, 26))), {1: "http://x/1"})


class HTargetsTests(unittest.TestCase):
    def test_targets_match_h_next(self):
        ps = [P("A", 3, 1), P("B", 3, 2), P("C", 1, 3), P("D", 1, 4)]
        # h=2, need 3; scanned top 3: A(3), B(3), C(1) -> only C short
        self.assertEqual(h_targets(ps), [(3, "C")])
        self.assertEqual(h_next(ps)[2], "C")

    def test_limit_and_empty(self):
        ps = [P(f"G{i}", 1, i) for i in range(1, 8)]
        self.assertEqual(len(h_targets(ps, limit=2)), 2)
        self.assertEqual(h_targets([]), [])
