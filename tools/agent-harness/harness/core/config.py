"""harness.yaml: the per-project configuration file.

Only project-specific settings live here. Framework defaults are code, so a
consumer repository carries the smallest possible configuration surface.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILENAME = "harness.yaml"
STATE_DIR = ".harness"
MANIFEST_FILENAME = "manifest.json"

DEFAULTS: dict[str, Any] = {
    "harness": {
        "version": None,          # installed framework version, written by init/update
        "profile": "generic",
        "detected_profiles": [],
        "platforms": ["claude", "codex"],
    },
    "project": {
        "name": None,
        "description": "",
    },
    "paths": {
        "docs": "docs",
        "milestones": "milestones",
        "tasks": "tasks",
        "history": "history",
        "references": "docs/reference/external",
        "local": ".local",
        "knowledge_map": "docs/knowledge-map.md",
        "catalog": "docs/knowledge-map.json",
        "llms": "docs/llms.txt",
    },
    "documents": {
        # Additional directories (relative) scanned for knowledge documents.
        "extra_roots": [],
        # Optional llms.txt-shaped export (one line per document); off until it proves useful (TASK-018).
        "llms_txt": False,
        # Directories (relative) that are never scanned.
        "ignore": [".local", ".venv", "node_modules", ".git", ".harness"],
    },
    "verification": {
        # List of {name, run, detected, verified, description}
        "commands": [],
    },
    "history": {
        "branches": ["HEAD"],
        "limit": 50,
        "skip_history_only_commits": True,
    },
    "wiki": {
        "home_title": None,
        "include": ["docs/**/*.md", "milestones/*.md", "tasks/*.md", "history/**/*.md"],
        "exclude": ["docs/knowledge-map.json", "**/README.md"],
        "include_readme": True,
        "home_from_readme": True,     # README.md becomes the top of the wiki Home page
        "remote": None,               # wiki git URL; default derives from the origin remote
        "token_env": "HARNESS_WIKI_TOKEN",
    },
    "sensitive": {
        # Extra glob patterns (relative) that must never be committed.
        "patterns": [],
    },
    "toolbox": {
        # Optional path or URL of a toolbox repository (future extension point).
        "sources": [],
    },
}


class ConfigError(ValueError):
    pass


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


@dataclass
class Config:
    root: Path
    data: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)  # what is actually on disk

    # -- accessors ---------------------------------------------------------
    @property
    def path(self) -> Path:
        return self.root / CONFIG_FILENAME

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def get(self, dotted: str, default=None):
        node: Any = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted: str, value) -> None:
        parts = dotted.split(".")
        for target in (self.data, self.raw):
            node = target
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value

    def rel_path(self, key: str) -> Path:
        return self.root / self.get(f"paths.{key}")

    @property
    def profile(self) -> str:
        return self.get("harness.profile") or "generic"

    @property
    def platforms(self) -> list[str]:
        return list(self.get("harness.platforms") or [])

    @property
    def installed_version(self) -> str | None:
        return self.get("harness.version")

    @property
    def project_name(self) -> str:
        return self.get("project.name") or self.root.name

    def document_roots(self) -> list[Path]:
        roots = [self.rel_path("docs"), self.rel_path("milestones"), self.rel_path("tasks"), self.rel_path("history")]
        for extra in self.get("documents.extra_roots") or []:
            roots.append(self.root / extra)
        # de-duplicate while preserving order
        seen: list[Path] = []
        for r in roots:
            if r not in seen:
                seen.append(r)
        return seen

    # -- persistence ---------------------------------------------------------
    def save(self) -> bool:
        from harness.core.util import write_text

        text = yaml.safe_dump(self.raw, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100)
        header = (
            "# harness.yaml — project configuration for the agent harness.\n"
            "# Project-owned: edit freely. Framework updates never rewrite this file.\n"
        )
        return write_text(self.path, header + text)


def load(root: Path) -> Config:
    path = root / CONFIG_FILENAME
    raw: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"{CONFIG_FILENAME}: invalid YAML: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ConfigError(f"{CONFIG_FILENAME}: top level must be a mapping")
        raw = loaded
    return Config(root=root, data=_deep_merge(DEFAULTS, raw), raw=raw)


def find_root(start: Path | None = None) -> Path | None:
    """Walk upwards from ``start`` looking for harness.yaml (or a .git dir)."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / CONFIG_FILENAME).exists():
            return candidate
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None
