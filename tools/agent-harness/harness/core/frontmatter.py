"""YAML frontmatter parsing and serialisation.

Frontmatter is the single machine-readable metadata surface of every
knowledge document. The format is the conventional Obsidian / Jekyll style:
a ``---`` fence on the first line, YAML, a closing ``---`` fence, then the
Markdown body.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

FENCE = "---"


class FrontmatterError(ValueError):
    """Raised when a document's frontmatter block cannot be parsed."""


@dataclass
class ParsedDocument:
    meta: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    has_frontmatter: bool = False
    # Line number (1-based) where the Markdown body starts.
    body_start_line: int = 1


def parse(text: str) -> ParsedDocument:
    """Split ``text`` into frontmatter mapping and body.

    A document without a leading fence is returned with an empty mapping
    and ``has_frontmatter=False``; callers decide whether that is an error.
    """
    # Tolerate a UTF-8 BOM, which Windows editors like to insert.
    if text.startswith("﻿"):
        text = text[1:]
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != FENCE:
        return ParsedDocument(meta={}, body=text, has_frontmatter=False)
    for idx in range(1, len(lines)):
        if lines[idx].rstrip("\r\n") == FENCE:
            raw = "".join(lines[1:idx])
            try:
                data = yaml.safe_load(raw) if raw.strip() else {}
            except yaml.YAMLError as exc:  # pragma: no cover - message passthrough
                raise FrontmatterError(f"invalid YAML frontmatter: {exc}") from exc
            if data is None:
                data = {}
            if not isinstance(data, dict):
                raise FrontmatterError("frontmatter must be a YAML mapping")
            body = "".join(lines[idx + 1 :])
            return ParsedDocument(meta=data, body=body, has_frontmatter=True, body_start_line=idx + 2)
    raise FrontmatterError("frontmatter opening fence without a closing fence")


def dump(meta: dict[str, Any], body: str) -> str:
    """Serialise ``meta`` and ``body`` back to a Markdown document.

    Keys keep insertion order so that generated documents are stable and
    diff-friendly. Output always uses ``\n`` line endings.
    """
    yaml_text = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100)
    body = body.replace("\r\n", "\n")
    if body and not body.startswith("\n"):
        body = "\n" + body
    if body and not body.endswith("\n"):
        body += "\n"
    return f"{FENCE}\n{yaml_text}{FENCE}\n{body}"
