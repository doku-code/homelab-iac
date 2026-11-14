"""Locate and render packaged assets (templates, profiles, skills, workflows).

Assets ship inside the ``harness`` package so that ``pip install`` from a Git
tag gives a consumer everything it needs without copying the framework
repository. Rendering uses a deliberately tiny ``{{name}}`` substitution so
templates stay readable Markdown and need no template engine.
"""

from __future__ import annotations

import re
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}")


def asset_path(*parts: str) -> Path:
    return ASSETS_DIR.joinpath(*parts)


def read_asset(*parts: str) -> str:
    return asset_path(*parts).read_text(encoding="utf-8")


def render(text: str, variables: dict[str, object], *, strict: bool = False) -> str:
    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key in variables:
            v = variables[key]
            return "" if v is None else str(v)
        if strict:
            raise KeyError(f"template variable not provided: {key}")
        return m.group(0)

    return _VAR_RE.sub(sub, text)


def render_asset(variables: dict[str, object], *parts: str, strict: bool = False) -> str:
    return render(read_asset(*parts), variables, strict=strict)


def list_assets(*parts: str, pattern: str = "**/*") -> list[Path]:
    base = asset_path(*parts)
    if not base.exists():
        return []
    return sorted(p for p in base.glob(pattern) if p.is_file())
