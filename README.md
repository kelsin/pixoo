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

## Letterboxd + hourly update

`retro_pixoo.update` is a one-shot command that builds four pages (RetroAchievements profile, last watched film, recent unlocks, recent diary) and pushes them to the Pixoo. Each page shows for 30 seconds by default (`--seconds`). Letterboxd data comes from the public RSS feed (user `kelsin13` by default, `--lb-user`); RetroAchievements needs `RA_API_KEY` set.

```bash
python -m retro_pixoo.update --sample --preview preview     # no network, no device
python -m retro_pixoo.update --send 192.168.1.50
```

If one source fails (for example `RA_API_KEY` is missing), its pages are skipped and the other source's two pages are still shown. Exit codes: 0 all good, 1 if any source failed or no pages could be built (nothing is sent when there are no pages).

To run it every hour, see the next section.

## Run every hour on a Mac

Run `retro_pixoo.update` from a launchd agent rather than cron or `--loop`: launchd starts it at login, catches up after sleep, and each run is a fresh process, so one failure can't wedge the next hour.

**1. Make a virtualenv** in the repo (`.venv/` is gitignored), so the job doesn't depend on your shell's Python or pyenv shims:

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

**2. Store the API key in the login Keychain.** launchd doesn't read your shell profile, and this keeps the key out of the plist. The command prompts for the key, so it doesn't land in shell history:

```bash
security add-generic-password -s retro_pixoo -a "$USER" -w
```

**3. Give the Pixoo a fixed IP** with a DHCP reservation on your router, so the job doesn't lose it after a router reboot.

**4. Write the agent.** Set `REPO` to your checkout, `PIXOO_IP` to the device, and the two usernames, then paste the whole block:

```bash
REPO="$HOME/src/pixoo"
PIXOO_IP=192.168.1.50
RA_USER=kelsin
LB_USER=kelsin13
cat > ~/Library/LaunchAgents/com.retro-pixoo.hourly.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.retro-pixoo.hourly</string>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-c</string>
    <string>RA_API_KEY="\$(security find-generic-password -s retro_pixoo -a \$USER -w)" exec .venv/bin/python -u -m retro_pixoo.update --ra-user $RA_USER --lb-user $LB_USER --send $PIXOO_IP</string>
  </array>
  <key>StartInterval</key><integer>3600</integer>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/retro-pixoo.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/retro-pixoo.log</string>
</dict>
</plist>
EOF
plutil -lint ~/Library/LaunchAgents/com.retro-pixoo.hourly.plist
```

**5. Load it.** It runs once right away (`RunAtLoad`), then every hour:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.retro-pixoo.hourly.plist
```

```bash
tail -f ~/Library/Logs/retro-pixoo.log
```

A good run logs `sent 4 pages to <ip>`; a failing source logs its error and the job exits 1, which `launchctl print` shows as the last exit code. If macOS shows a Keychain prompt for `security` on the first run, choose **Always Allow**.

**Manage it:**

| What | Command |
| --- | --- |
| Run now | `launchctl kickstart -k gui/$(id -u)/com.retro-pixoo.hourly` |
| Status and last exit code | `launchctl print gui/$(id -u)/com.retro-pixoo.hourly` |
| Stop and unload | `launchctl bootout gui/$(id -u)/com.retro-pixoo.hourly` |

After editing the plist, run `bootout` then `bootstrap` again to pick up the change.

**Notes:**

- The agent only runs while you're logged in, which is what you want for a desk display. If the Mac is asleep, launchd runs one catch-up update on wake instead of one per missed hour.
- Keep the repo out of `~/Documents`, `~/Desktop` and `~/Downloads`. macOS privacy protection blocks background jobs from reading those folders, and the job fails with `Operation not permitted`.
- If you move the repo or recreate `.venv`, rerun step 4 and reload.

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
