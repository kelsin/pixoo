import unittest
from unittest import mock

from retro_pixoo.bgg import (
    BggClient,
    Play,
    game_counts,
    h_index,
    h_next,
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
