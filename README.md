# retro_pixoo

Shows your RetroAchievements profile on a Divoom Pixoo-64 as two looping pages:

1. **Profile**: avatar, username, online status, points, rank and top %, and progress in your last played game.
2. **Recent unlocks**: your three newest achievements with badges. Hardcore unlocks get a gold frame.

## Setup

```bash
pip install requests pillow
```

Get your Web API key from https://retroachievements.org/settings (the Keys / Authentication section). Keep it secret.

```bash
export RA_API_KEY=your_key_here
```

## Run

Preview with bundled sample data (no network, no device needed):

```bash
python -m retro_pixoo --sample --preview preview
```

Live data, preview only:

```bash
python -m retro_pixoo --user kelsin --preview preview
```

Push to the Pixoo, refreshing every 10 minutes:

```bash
python -m retro_pixoo --user kelsin --send 192.168.1.50 --loop 10
```

Add `--endpoint /divoom_api` if your firmware doesn't answer on `/post`.

## Use from your own script

```python
from retro_pixoo import RAClient, ImageFetcher, Pixoo, frames, profile_frame

profile = RAClient().profile("kelsin")
pages = frames(profile, ImageFetcher())          # list of 64x64 PIL images
Pixoo("192.168.1.50").show(pages, ms_per_frame=6000)
```

Each page is a plain 64x64 `PIL.Image`, so you can mix these pages with your own frames in one `show()` call (up to about 40 frames).

## Notes

- One API call per refresh (`API_GetUserSummary`). RetroAchievements asks clients to cache and rate-limits fast polling, so the loop refuses intervals under 5 minutes.
- If a badge or avatar fails to download, a generated pixel placeholder is drawn instead.
- `retro_pixoo/sample_summary.json` is made-up data in the API's shape, for layout testing only.
