"""Shared install/update engine with explicit file ownership.

Used by both ``harness init`` and ``harness update``. For every artifact the
engine decides one of: create, update, unchanged, skip (seed exists),
conflict (local modification or foreign file). Nothing is ever overwritten
silently; conflicts are reported and left untouched unless ``force`` is set,
in which case the previous content is backed up under ``.local/``.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

from harness import __version__
from harness.adapters import (Artifact, agents_block, claude_artifacts, claude_block, gitignore_block,
                              merged_claude_settings, seed_artifacts, skill_artifacts, workflow_artifacts)
from harness.core import blocks, manifest as manifest_mod
from harness.core.config import Config
from harness.core.manifest import BLOCK, GENERATED, MANAGED, SEED, Manifest
from harness.core.util import sha256_text, write_text

CREATE, UPDATE, UNCHANGED, SKIP, CONFLICT, TAKEOVER = "create", "update", "unchanged", "skip", "conflict", "takeover"


@dataclass
class Action:
    path: str
    kind: str
    action: str
    reason: str = ""
    old: str | None = None
    new: str | None = None

    def diff(self) -> str:
        if self.old is None and self.new is None:
            return ""
        a = (self.old or "").splitlines(keepends=True)
        b = (self.new or "").splitlines(keepends=True)
        return "".join(difflib.unified_diff(a, b, fromfile=f"a/{self.path}", tofile=f"b/{self.path}"))


@dataclass
class Plan:
    actions: list[Action] = field(default_factory=list)

    def by_action(self, *names: str) -> list[Action]:
        return [a for a in self.actions if a.action in names]

    @property
    def conflicts(self) -> list[Action]:
        return self.by_action(CONFLICT)

    @property
    def changes(self) -> list[Action]:
        return self.by_action(CREATE, UPDATE, TAKEOVER)


def all_artifacts(config: Config) -> list[Artifact]:
    arts: list[Artifact] = []
    arts.extend(skill_artifacts(config))
    arts.extend(claude_artifacts(config))
    arts.extend(workflow_artifacts(config))
    arts.extend(seed_artifacts(config))
    return arts


def _read(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def plan(config: Config, manifest: Manifest | None, *, force: bool = False) -> Plan:
    root = config.root
    manifest = manifest or Manifest(harness_version="0.0.0")
    p = Plan()

    # Whole files and seeds
    for art in all_artifacts(config):
        target = root / art.path
        current = _read(target)
        entry = manifest.get(art.path)
        if art.kind == SEED:
            if current is None and entry is None:
                p.actions.append(Action(art.path, SEED, CREATE, new=art.content))
            elif current is None:
                p.actions.append(Action(art.path, SEED, SKIP, reason="seed was removed by the project; not recreated"))
            else:
                p.actions.append(Action(art.path, SEED, SKIP, reason="seed exists; project-owned"))
            continue
        if current is None:
            p.actions.append(Action(art.path, MANAGED, CREATE, new=art.content))
        elif current == art.content.replace("\r\n", "\n"):
            p.actions.append(Action(art.path, MANAGED, UNCHANGED))
        elif entry is None:
            act = TAKEOVER if force else CONFLICT
            p.actions.append(Action(art.path, MANAGED, act, reason="file exists but is not managed by the harness",
                                    old=current, new=art.content))
        elif sha256_text(current) == entry.hash:
            p.actions.append(Action(art.path, MANAGED, UPDATE, reason=f"upstream changed (installed v{entry.version})",
                                    old=current, new=art.content))
        else:
            act = TAKEOVER if force else CONFLICT
            p.actions.append(Action(art.path, MANAGED, act, reason="locally modified since install",
                                    old=current, new=art.content))

    # Managed blocks
    for path, body in (("AGENTS.md", agents_block(config)),):
        _plan_block(p, root, path, body, kind=BLOCK)
    if "claude" in config.platforms:
        _plan_block(p, root, "CLAUDE.md", claude_block(config), kind=BLOCK, preamble="@AGENTS.md\n")
        new_settings, changed = merged_claude_settings(root)
        current = _read(root / ".claude/settings.json")
        if current is None:
            p.actions.append(Action(".claude/settings.json", BLOCK, CREATE, new=new_settings))
        elif changed:
            p.actions.append(Action(".claude/settings.json", BLOCK, UPDATE, reason="add SessionStart hook",
                                    old=current, new=new_settings))
        else:
            p.actions.append(Action(".claude/settings.json", BLOCK, UNCHANGED))
    _plan_hash_block(p, root, ".gitignore", gitignore_block(config))

    # Manifest file itself and generated indexes are handled by the caller.
    return p


def _plan_block(p: Plan, root: Path, path: str, body: str, *, kind: str, preamble: str = "") -> None:
    target = root / path
    current = _read(target)
    if current is None:
        text = preamble + ("\n" if preamble else "") + blocks.render_block(body, __version__) + "\n"
        p.actions.append(Action(path, kind, CREATE, new=text))
        return
    _version, existing_body = blocks.find_block(current)
    new_text = blocks.replace_block(current, body, __version__)
    if preamble and preamble.strip() not in current:
        new_text = preamble + "\n" + new_text
    if new_text == current:
        p.actions.append(Action(path, kind, UNCHANGED))
    elif existing_body is None:
        p.actions.append(Action(path, kind, UPDATE, reason="append managed block to existing file", old=current, new=new_text))
    else:
        p.actions.append(Action(path, kind, UPDATE, reason="refresh managed block", old=current, new=new_text))


def _plan_hash_block(p: Plan, root: Path, path: str, body: str) -> None:
    target = root / path
    current = _read(target)
    if current is None:
        p.actions.append(Action(path, BLOCK, CREATE, new=blocks.render_hash_block(body) + "\n"))
        return
    new_text = blocks.replace_hash_block(current, body)
    if new_text == current:
        p.actions.append(Action(path, BLOCK, UNCHANGED))
    else:
        p.actions.append(Action(path, BLOCK, UPDATE, reason="refresh managed block", old=current, new=new_text))


def apply(config: Config, p: Plan, manifest: Manifest | None) -> Manifest:
    """Write every create/update/takeover action and return the refreshed manifest."""
    root = config.root
    new_manifest = Manifest(harness_version=__version__)
    old = manifest or Manifest(harness_version="0.0.0")
    backup_dir = root / (config.get("paths.local") or ".local") / "harness-backup"
    for act in p.actions:
        target = root / act.path
        if act.action in (CREATE, UPDATE, TAKEOVER):
            if act.action == TAKEOVER and act.old is not None:
                bpath = backup_dir / act.path
                write_text(bpath, act.old)
            write_text(target, act.new or "")
            content = act.new or ""
        elif act.action in (UNCHANGED, CONFLICT):
            content = _read(target) or ""
        else:  # SKIP (seed exists)
            content = _read(target) or ""
        # Record ownership. Conflicting files keep their previous manifest entry (if any) so a later
        # update can still recognise them; foreign files are not recorded.
        if act.kind == SEED:
            prev = old.get(act.path)
            if act.action == SKIP and not target.exists() and prev:
                new_manifest.entries[act.path] = prev  # remember the removed seed so it is never recreated
            else:
                new_manifest.record(act.path, SEED, content, prev.version if prev else __version__)
        elif act.kind == BLOCK:
            if act.path.endswith(".gitignore"):
                body = blocks.find_hash_block(content) or ""
            elif act.path.endswith(".json"):
                body = content
            else:
                _v, body = blocks.find_block(content)
                body = body or ""
            new_manifest.record(act.path, BLOCK, body, __version__)
        elif act.action == CONFLICT:
            prev = old.get(act.path)
            if prev:
                new_manifest.entries[act.path] = prev
        else:
            new_manifest.record(act.path, MANAGED, content, __version__)
    manifest_mod.save(root, new_manifest)
    return new_manifest
