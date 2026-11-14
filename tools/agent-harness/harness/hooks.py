"""`harness hooks`: an optional, explicitly installed pre-commit hook.

The hook regenerates the generated indexes, stages *only those generated files*, then runs `harness check`;
a red check aborts the commit with the check's exit code. Nothing else is staged, no commit is amended, and
there is no post-commit step: history records are produced on demand (`harness history sync`) for commits
worth annotating, not for every commit (ADR-003). CI stays the authoritative validation layer.

The script lives in `.git/hooks/`, is never committed, and exits immediately in a repository without
`harness.yaml` (so a shared `core.hooksPath` cannot break other repositories).
"""

from __future__ import annotations

import os
import shlex
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path

from harness import __version__
from harness.core import gitutil
from harness.core.config import Config

MARKER = "# agent-harness hook"
HOOK_NAMES = ("pre-commit",)


def generated_paths(config: Config) -> list[str]:
    paths = [config.get("paths.knowledge_map"), config.get("paths.catalog"),
             f"{config.get('paths.docs')}/dashboard.md", f"{config.get('paths.history')}/README.md"]
    if config.get("documents.llms_txt"):
        paths.append(config.get("paths.llms"))
    return paths


def render_hook(name: str, config: Config) -> str:
    if name != "pre-commit":
        raise ValueError(name)
    interpreter = Path(sys.executable).as_posix()
    generated = " ".join(shlex.quote(p) for p in generated_paths(config))
    return (
        "#!/bin/sh\n"
        f"{MARKER} v{__version__} ({name}) — installed by `harness hooks install`; remove with `harness hooks uninstall`.\n"
        "# Repository guard: core.hooksPath may be shared; do nothing where there is no harness.yaml.\n"
        "[ -f harness.yaml ] || exit 0\n"
        f"HARNESS={shlex.quote(interpreter + ' -m harness')}\n"
        "# Prefer the interpreter used at install time; fall back to a `harness` on PATH only if it is gone.\n"
        f"if [ ! -x {shlex.quote(interpreter)} ] && command -v harness >/dev/null 2>&1; then HARNESS=harness; fi\n"
        "run() { if [ \"$HARNESS\" = harness ]; then harness \"$@\"; else eval \"$HARNESS\" '\"$@\"'; fi; }\n"
        "# Regenerate the generated indexes and stage only those files (never user changes).\n"
        "run docs index >/dev/null || { echo 'harness: index regeneration failed' >&2; exit 1; }\n"
        f"for f in {generated}; do [ -f \"$f\" ] && git add -- \"$f\"; done\n"
        "# A red check aborts the commit with the check's exit code; output is shown only on failure.\n"
        "out=$(run check --quiet 2>&1); rc=$?\n"
        "if [ $rc -ne 0 ]; then printf '%s\\n' \"$out\" >&2; echo 'harness: check failed; commit aborted' >&2; exit $rc; fi\n"
        "exit 0\n"
    )


@dataclass
class HookReport:
    installed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    hooks_dir: Path | None = None

    def summary(self) -> str:
        out = [f"hooks directory: {self.hooks_dir}"]
        for n in self.installed:
            out.append(f"  + installed {n}")
        for n in self.unchanged:
            out.append(f"  = unchanged {n}")
        for n in self.conflicts:
            out.append(f"  ! {n}: an existing hook that is not ours; use --force to replace (backup kept as {n}.harness-backup)")
        for n in self.removed:
            out.append(f"  - removed {n}")
        return "\n".join(out)


def hooks_dir(root: Path) -> Path | None:
    if not gitutil.is_repo(root):
        return None
    common = gitutil.run(["rev-parse", "--git-path", "hooks"], root, check=False)
    p = Path(common) if common else root / ".git" / "hooks"
    return p if p.is_absolute() else (root / p)


def _is_ours(path: Path) -> bool:
    try:
        return MARKER in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def install(config: Config, *, force: bool = False) -> HookReport:
    report = HookReport(hooks_dir=hooks_dir(config.root))
    if report.hooks_dir is None:
        raise gitutil.GitError("not a Git repository")
    try:
        report.hooks_dir.resolve().relative_to(config.root.resolve())
    except ValueError:
        if not force:
            raise gitutil.GitError(
                f"hooks directory {report.hooks_dir} is outside the repository (core.hooksPath); refusing to write there. "
                "Use `git config core.hooksPath .git/hooks` for this repository, or --force to install anyway "
                "(the script exits immediately in repositories without harness.yaml)."
            )
    report.hooks_dir.mkdir(parents=True, exist_ok=True)
    for name in HOOK_NAMES:
        target = report.hooks_dir / name
        content = render_hook(name, config)
        if target.exists():
            current = target.read_text(encoding="utf-8", errors="replace")
            if current == content:
                report.unchanged.append(name)
                continue
            if not _is_ours(target) and not force:
                report.conflicts.append(name)
                continue
            if not _is_ours(target):
                target.with_name(name + ".harness-backup").write_bytes(target.read_bytes())  # byte-exact
        with target.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        report.installed.append(name)
    return report


def uninstall(config: Config) -> HookReport:
    report = HookReport(hooks_dir=hooks_dir(config.root))
    if report.hooks_dir is None:
        raise gitutil.GitError("not a Git repository")
    for name in HOOK_NAMES + ("post-commit",):  # post-commit: remove hooks left by earlier harness versions
        target = report.hooks_dir / name
        if target.exists() and _is_ours(target):
            target.unlink()
            backup = target.with_name(name + ".harness-backup")
            if backup.exists():
                os.replace(backup, target)
            report.removed.append(name)
    return report


def status(config: Config) -> dict[str, str]:
    d = hooks_dir(config.root)
    out: dict[str, str] = {}
    for name in HOOK_NAMES:
        target = (d / name) if d else None
        if target is None or not target.exists():
            out[name] = "absent"
        elif _is_ours(target):
            out[name] = "installed" if target.read_text(encoding="utf-8", errors="replace") == render_hook(name, config) else "outdated"
        else:
            out[name] = "foreign"
    return out
