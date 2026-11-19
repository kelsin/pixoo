# BGG pages design

## Intent
Show board-gaming habits on the Pixoo-64 from BoardGameGeek plays (BG Stats auto-posts to BGG; Geek Group is a viewer over the same data and has no public API). Headline feature: the current-year H-index.

## Goals / non-goals
- Goals: four pages (H-index, recent plays, top played, year stats) the user can pick from for their rotation; offline preview via sample data.
- Non-goals: box art, collection data, BG Stats export, Geek Group scraping.

## Approach
BGG XML API2 `/xmlapi2/plays?username=&mindate=&maxdate=` (paged, 100/page), Bearer `$BGG_TOKEN`. Chosen over scraping Geek Group (login via geekmail code, no API) and BG Stats export (format unknown).

## Design
- `retro_pixoo/bgg.py`: `Play(date, game, game_id, quantity, minutes)`, `parse_plays`, `BggClient.plays(user, year)`, `load_sample_plays`, `h_index`, `top_played`; `sample_plays.xml`.
- `render.py`: `bgg_h_frame`, `bgg_recent_frame`, `bgg_top_frame`, `bgg_stats_frame` (text + bars, existing header/font style).
- `update.py`: third source; `--bgg-user` (default `Kelsin`), `BGG_TOKEN` env, `--bgg-pages h,recent,top,stats` (default all). A BGG failure skips only BGG pages.
- H-index: sum quantity per game; largest h with h games >= h plays. Progress page shows the game needing fewest extra plays to reach h+1. Year = current calendar year. Expansions count as their own games.
- Tests follow existing pattern: parser, h_index, render smoke, update wiring.
