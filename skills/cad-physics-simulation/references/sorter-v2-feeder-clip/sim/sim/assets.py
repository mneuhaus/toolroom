"""Where the asset set lives. Never in git: see AGENTS.md."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def asset_root() -> Path:
    return Path(os.environ.get("SIM_ASSETS", ROOT / "assets"))


def out_root() -> Path:
    p = Path(os.environ.get("SIM_OUT", ROOT / "out"))
    p.mkdir(parents=True, exist_ok=True)
    return p
