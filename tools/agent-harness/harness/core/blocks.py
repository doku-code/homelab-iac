"""Managed blocks inside project-owned text files.

AGENTS.md, CLAUDE.md and .gitignore are project-owned files in which the
harness maintains one clearly delimited block. Everything outside the
markers belongs to the project and is never modified.
"""

from __future__ import annotations

import re

START = "<!-- harness:managed:start"
END = "<!-- harness:managed:end -->"

_BLOCK_RE = re.compile(
    r"<!-- harness:managed:start(?: v=(?P<version>[^ ]+))? -->\n(?P<body>.*?)\n?<!-- harness:managed:end -->",
    re.DOTALL,
)


def render_block(body: str, version: str) -> str:
    body = body.strip("\n")
    return f"<!-- harness:managed:start v={version} -->\n{body}\n{END}"


def find_block(text: str) -> tuple[str | None, str | None]:
    """Return (version, body) of the managed block, or (None, None)."""
    m = _BLOCK_RE.search(text)
    if not m:
        return None, None
    return m.group("version"), m.group("body")


def replace_block(text: str, body: str, version: str) -> str:
    new_block = render_block(body, version)
    if _BLOCK_RE.search(text):
        return _BLOCK_RE.sub(lambda _m: new_block, text, count=1)
    text = text.rstrip("\n")
    if text:
        return f"{text}\n\n{new_block}\n"
    return f"{new_block}\n"


# ---------------------------------------------------------------------------
# Hash-comment style block (for .gitignore and other non-Markdown files)
# ---------------------------------------------------------------------------

HASH_START = "# >>> harness managed block (do not edit inside) >>>"
HASH_END = "# <<< harness managed block <<<"
_HASH_RE = re.compile(re.escape(HASH_START) + r"\n(?P<body>.*?)\n?" + re.escape(HASH_END), re.DOTALL)


def render_hash_block(body: str) -> str:
    return f"{HASH_START}\n{body.strip()}\n{HASH_END}"


def find_hash_block(text: str) -> str | None:
    m = _HASH_RE.search(text)
    return m.group("body") if m else None


def replace_hash_block(text: str, body: str) -> str:
    new_block = render_hash_block(body)
    if _HASH_RE.search(text):
        return _HASH_RE.sub(lambda _m: new_block, text, count=1)
    text = text.rstrip("\n")
    return f"{text}\n\n{new_block}\n" if text else f"{new_block}\n"
