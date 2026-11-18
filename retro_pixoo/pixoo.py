"""Minimal Pixoo-64 local HTTP client: push one or more 64x64 frames."""

from __future__ import annotations

import base64

import requests
from PIL import Image


class Pixoo:
    def __init__(self, ip: str, endpoint: str = "/post", timeout: float = 5.0):
        # Older firmware answers on /post; some newer firmware is reported to use /divoom_api.
        self.url = f"http://{ip}{endpoint}"
        self.timeout = timeout

    def command(self, payload: dict) -> dict:
        r = requests.post(self.url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        if data.get("error_code", 0) != 0:
            raise RuntimeError(f"Pixoo error for {payload.get('Command')}: {data}")
        return data

    def get_config(self) -> dict:
        return self.command({"Command": "Channel/GetAllConf"})

    def set_brightness(self, value: int) -> None:
        self.command({"Command": "Channel/SetBrightness", "Brightness": max(0, min(100, value))})

    def show(self, frames: list[Image.Image], ms_per_frame: int = 6000) -> None:
        """Send frames as one looping animation. Max ~40 frames on the device."""
        if not frames:
            raise ValueError("no frames")
        self.command({"Command": "Draw/ResetHttpGifId"})
        for i, f in enumerate(frames):
            f = f.convert("RGB")
            if f.size != (64, 64):
                f = f.resize((64, 64), Image.NEAREST)
            self.command({
                "Command": "Draw/SendHttpGif",
                "PicNum": len(frames),
                "PicWidth": 64,
                "PicOffset": i,
                "PicID": 1,
                "PicSpeed": ms_per_frame,
                "PicData": base64.b64encode(f.tobytes()).decode(),
            })
