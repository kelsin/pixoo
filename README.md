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
export PIXOO_IP=192.168.1.50
uv run retro-pixoo-update
```

## BoardGameGeek pages

Set `BGG_TOKEN` to a BoardGameGeek API token to add four board-game pages after the Letterboxd ones: `h` (your play h-index), `recent` (latest plays), `top` (most played this year) and `stats` (year totals). Without the token the pages are skipped, `bgg: BGG_TOKEN not set` goes to stderr and the run exits 1 like any failed source.

```bash
export BGG_TOKEN=your_token_here
uv run retro-pixoo-update --bgg-user Kelsin --bgg-pages h,top
```

`--bgg-pages` takes a comma list (default `h,recent,top,stats`) and sets the order. Plays are read from BGG's plays API, so they only show up once logged there; Geek Group and BG Stats plays appear after their sync to BGG.

## Commands

| Command | What it does |
| --- | --- |
| `retro-pixoo-update` | One shot: RA profile, recent unlocks, top systems, Letterboxd last watched film, recent diary, this month's stats. 30s per page (`--seconds`). |
| `retro-pixoo` | RA profile, recent unlocks and top systems only. `--loop MIN` keeps refreshing (minimum 5). |

Common flags: `--sample`, `--preview DIR`, `--send IP` (defaults to `$PIXOO_IP`), `--endpoint /divoom_api` (if your firmware doesn't answer on `/post`). Users: `--ra-user` and `--lb-user` for `retro-pixoo-update`, `--user` for `retro-pixoo`.

If one source fails, `retro-pixoo-update` still shows the other source's pages and exits 1.

## Run every hour on a Mac

Run `retro-pixoo-update` from a launchd agent rather than cron or `--loop`: launchd starts it at login, catches up after sleep, and each run is a fresh process, so one failure can't wedge the next hour.

**1. Install into the repo's `.venv/`** (gitignored), so the job doesn't depend on your shell's Python or pyenv shims:

```bash
uv sync
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
    <string>RA_API_KEY="\$(security find-generic-password -s retro_pixoo -a \$USER -w)" PIXOO_IP=$PIXOO_IP exec .venv/bin/python -u -m retro_pixoo.update --ra-user $RA_USER --lb-user $LB_USER</string>
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

A good run logs `sent 6 pages to <ip>`; a failing source logs its error and the job exits 1, which `launchctl print` shows as the last exit code. If macOS shows a Keychain prompt for `security` on the first run, choose **Always Allow**.

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
- If you move the repo or delete `.venv`, rerun step 4 and reload.

## Development

```bash
uv run pytest
```

Every page is a 64x64 `PIL.Image`, so you can build your own frames and send them with `Pixoo("192.168.1.50").show(pages)`. The sample files in `retro_pixoo/` are made-up data for layout testing.
