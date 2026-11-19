import unittest
from unittest import mock

from retro_pixoo.ra import MEDIA_BASE, RAClient, load_sample, parse_summary, top_systems

SNES = "SNES/Super Famicom"
GBA = "Game Boy Advance"
N64 = "Nintendo 64"


def played(*games):
    """games: (game_id, console) tuples, newest first."""
    return [
        {"GameID": str(gid), "ConsoleName": console, "ImageIcon": f"/Images/{gid}.png",
         "LastPlayed": f"2026-11-{20 - i:02d} 12:00:00"}
        for i, (gid, console) in enumerate(games)
    ]


class TopSystemsTests(unittest.TestCase):
    def test_ranks_by_game_count(self):
        p = played((1, SNES), (2, GBA), (3, N64), (4, SNES), (5, GBA), (6, SNES))
        systems = top_systems(p, {})
        self.assertEqual([s.console for s in systems], [SNES, GBA, N64])
        self.assertEqual([s.games for s in systems], [3, 2, 1])

    def test_tie_goes_to_most_recent(self):
        p = played((1, GBA), (2, SNES), (3, SNES), (4, GBA))
        self.assertEqual([s.console for s in top_systems(p, {})], [GBA, SNES])

    def test_limit_four(self):
        p = played(*[(i, f"Console {i}") for i in range(6)])
        self.assertEqual(len(top_systems(p, {})), 4)

    def test_icon_is_latest_game(self):
        p = played((10, SNES), (11, SNES))
        self.assertEqual(top_systems(p, {})[0].icon_url, MEDIA_BASE + "/Images/10.png")

    def test_achievement_sum_hardcore_else_softcore(self):
        p = played((1, SNES), (2, SNES))
        awarded = {
            "1": {"NumAchievedHardcore": 5, "NumAchieved": 7},
            "2": {"NumAchievedHardcore": 0, "NumAchieved": 3},
        }
        self.assertEqual(top_systems(p, awarded)[0].achievements, 8)

    def test_missing_awarded_counts_zero(self):
        s = top_systems(played((1, SNES)), {})[0]
        self.assertEqual((s.games, s.achievements), (1, 0))

    def test_empty(self):
        self.assertEqual(top_systems([], {}), [])
        self.assertEqual(parse_summary({}).systems, [])

    def test_sample_has_systems(self):
        systems = load_sample().systems
        self.assertEqual(len(systems), 4)
        self.assertGreater(systems[0].games, systems[3].games)

    def test_profile_requests_100_games(self):
        client = RAClient(api_key="k")
        with mock.patch.object(RAClient, "_get", return_value={}) as get:
            client.profile("u")
        self.assertEqual(get.call_args.kwargs["g"], 100)


if __name__ == "__main__":
    unittest.main()


def test_last_game_skips_games_without_progress():
    from retro_pixoo.ra import parse_summary

    profile = parse_summary(
        {
            "RecentlyPlayed": [
                {"GameID": 1, "Title": "Empty", "AchievementsTotal": 0},
                {"GameID": 2, "Title": "Played", "AchievementsTotal": 10},
            ],
            "Awarded": {"2": {"NumAchieved": 3, "NumPossibleAchievements": 10}},
        }
    )
    assert profile.last_game.title == "Played"
    assert (profile.last_game.achieved, profile.last_game.possible) == (3, 10)
