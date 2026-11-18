# RA "Top Systems" page

## Intent
A third RetroAchievements page that shows which four consoles you've been playing most lately. It goes right after recent unlocks, in both `retro-pixoo` and `retro-pixoo-update`.

## Goals
- Page title "TOP SYSTEMS". A 2x2 grid, one square per system, in rank order (top-left, top-right, bottom-left, bottom-right).
- Each square has:
  - a 16x16 icon of the game you played most recently on that system,
  - the number of games played at 2x scale (white), centered to the right of the icon, with no label,
  - a colored system tag (short name in black on the system's color) below the icon,
  - the number of achievements unlocked (gold) to the right of the tag.
- Ranking: count games per `ConsoleName` among your last 100 recently played games. A tie goes to the system you played more recently.

## Non-goals
- Time windows, or ranking by achievements.
- Real console logos.

## Approaches
- **2x2 grid with game icons (chosen by Kelsin)**: livelier, and shows what you're playing on each system.
- Ranked list with bars: easier to read from across the room. Not chosen.
- Data: **reuse `API_GetUserSummary` with `g=100` (chosen)**. It's still one API call, and `RecentlyPlayed` comes newest first. A separate `API_GetUserRecentlyPlayedGames` call would be a second request for the same data, so no.

## Design
- `ra.py`
  - `RAClient.profile()` asks for `games=100`. The profile page still uses `RecentlyPlayed[0]`, so nothing changes there.
  - `parse_summary` fills a new `Profile.systems: list[SystemStat]`, top 4. `SystemStat` holds console, game count, achievement count, and the latest game's icon URL.
  - The achievement count adds up each game's hardcore unlocks from `Awarded` (softcore if a game has no hardcore unlocks, the same rule the profile page uses). It is your total unlocks on those games, not just recent ones.
- `render.py`: `systems_frame(p, fetcher)`, laid out like the approved mockup. A small table maps `ConsoleName` to a short tag and color (SNES, GBA, PS1, N64, NES, GB, GBC, GEN, PS2, ...). An unknown console uses its first 4 letters on grey. If there are fewer than 4 systems, the extra squares stay empty. If there are none, the page says "NO GAMES". A count of 100 or more drops to 1x.
- Wiring: `render.frames()` (`retro-pixoo`) and `update.collect_pages()` (`retro-pixoo-update`) add the page after `recent_frame`.
- Sample data: add RecentlyPlayed and Awarded entries across about 5 consoles to `sample_summary.json`, so the page shows real ranking and an empty square never appears.
- Tests: ranking, tie-break, achievement sums, fewer than 4 systems, and that the page count in `test_update` grows by one.

## Left to the builder
The colors and the full list in the console table. `g=100` is the API maximum (the server clamps larger values to 100); users with fewer games get fewer.
