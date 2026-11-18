# retro_pixoo

Puts your RetroAchievements profile and Letterboxd diary on a Divoom Pixoo-64.

## Quick start

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (`brew install uv`).

```bash
git clone git@github.com:kelsin/pixoo.git && cd pixoo
uv sync
uv run retro-pixoo-update --sample --preview preview
```

That renders every page from bundled sample data into `preview/`, with no network or device needed.

## Live data

Get a Web API key from https://retroachievements.org/settings (Keys / Authentication), then push to your Pixoo:

```bash
export RA_API_KEY=your_key_here
uv run retro-pixoo-update --send 192.168.1.50
```

## Commands

| Command | What it does |
| --- | --- |
| `retro-pixoo-update` | One shot: RA profile, last watched film, recent unlocks, recent diary. 30s per page (`--seconds`). |
| `retro-pixoo` | RA profile and recent unlocks only. `--loop MIN` keeps refreshing (minimum 5). |

Common flags: `--sample`, `--preview DIR`, `--send IP`, `--endpoint /divoom_api` (if your firmware doesn't answer on `/post`). Users: `--ra-user` and `--lb-user` for `retro-pixoo-update`, `--user` for `retro-pixoo`.

If one source fails, `retro-pixoo-update` still shows the other source's pages and exits 1.

Hourly from cron:

```cron
0 * * * * cd /path/to/pixoo && RA_API_KEY=... /path/to/uv run retro-pixoo-update --send 192.168.1.50 >> /tmp/pixoo.log 2>&1
```

## Development

```bash
uv run pytest
```

Every page is a 64x64 `PIL.Image`, so you can build your own frames and send them with `Pixoo("192.168.1.50").show(pages)`. The sample files in `retro_pixoo/` are made-up data for layout testing.
