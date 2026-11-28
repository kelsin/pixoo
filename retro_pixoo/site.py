"""Static gallery site: raw 64x64 frames plus a manifest, for GitHub Pages."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

TEMPLATE = Path(__file__).parent / "site" / "index.html"


def write_site(pages: list[Image.Image], out_dir: Path, seconds: int = 30,
               cname: str | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    names = [f"page{i + 1}.png" for i in range(len(pages))]
    for stale in out_dir.glob("page*.png"):
        if stale.name not in names:
            stale.unlink()
    for name, frame in zip(names, pages):
        frame.convert("RGB").save(out_dir / name)
    manifest = {"seconds": seconds, "pages": names,
                "generated": datetime.now(timezone.utc).isoformat()}
    (out_dir / "manifest.json").write_text(json.dumps(manifest))
    shutil.copyfile(TEMPLATE, out_dir / "index.html")
    (out_dir / ".nojekyll").touch()
    if cname:
        (out_dir / "CNAME").write_text(cname + "\n")
    else:
        (out_dir / "CNAME").unlink(missing_ok=True)
