# pixoo

Python scripts that customize the screen of a **Divoom Pixoo-64** (64x64 RGB LED display) over its local HTTP API.

## Device

- Pixoo-64, controlled on the LAN by POSTing JSON to `http://<ip>/post`. The user's device uses `/post` (the default); don't use `/divoom_api`.
- Responses carry `error_code`; non-zero means the command failed.
- Images go up as base64 raw RGB bytes (64*64*3) via `Draw/ResetHttpGifId` then one `Draw/SendHttpGif` per frame. The device loops the frames; keep it to about 40 frames max.
- The client lives in `retro_pixoo/pixoo.py` (`Pixoo.show(frames, ms_per_frame)`, `set_brightness`, `get_config`). Reuse it for new scripts instead of writing another one.

## Conventions

- Every commit message uses [Conventional Commits](https://www.conventionalcommits.org): `<type>[optional scope]: <description>`, with `type` one of `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`, `revert`.
- Python 3 with `requests` and `pillow`, managed with uv (`pyproject.toml`, `uv.lock`, `.python-version`). Add dependencies with `uv add`, dev tools with `uv add --dev`; run tests with `uv run pytest`.
- Build each screen as a 64x64 `PIL.Image` in RGB, then hand a list of them to `Pixoo.show()`.
- Every script should support a local preview (write PNGs, scaled up) so layouts can be checked without the device.
- Pixel-art rendering: use `Image.NEAREST` for any resize, and the bitmap font in `retro_pixoo/font.py` for text.

## Existing scripts

- `retro_pixoo/`: RetroAchievements profile + recent unlocks pages, plus Letterboxd tag pages read from the data export in `~/Downloads` (a weekly launchd agent triggers the export). Run `uv run retro-pixoo --sample --preview preview` to preview offline. See `README.md`.
