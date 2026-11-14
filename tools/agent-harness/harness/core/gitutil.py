"""Thin, defensive wrapper around the ``git`` CLI.

Only plumbing-style, read-mostly operations are exposed. The harness never
rewrites history, never force-pushes and never configures remotes.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class GitError(RuntimeError):
    pass


@dataclass
class Commit:
    sha: str
    short: str
    subject: str
    body: str
    author_name: str
    author_email: str
    authored: str  # ISO-8601 strict
    committed: str
    parents: list[str]
    files: list[str] = field(default_factory=list)

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1


def run(args: list[str], cwd: Path, check: bool = True, *, strip: bool = True) -> str:
    """Run a git command and return stdout (text, stripped unless ``strip=False``).

    Note: ``str.strip()`` removes ASCII control separators such as ``\x1e``/``\x1f`` too, so callers
    that parse delimited output must pass ``strip=False``.
    """
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
    except FileNotFoundError as exc:  # pragma: no cover - environment dependent
        raise GitError("git executable not found on PATH") from exc
    if check and proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout.strip() if strip else proc.stdout


def is_repo(path: Path) -> bool:
    try:
        return run(["rev-parse", "--is-inside-work-tree"], path) == "true"
    except GitError:
        return False


def toplevel(path: Path) -> Path | None:
    try:
        return Path(run(["rev-parse", "--show-toplevel"], path))
    except GitError:
        return None


def has_commits(path: Path) -> bool:
    try:
        run(["rev-parse", "--verify", "HEAD"], path)
        return True
    except GitError:
        return False


def current_branch(path: Path) -> str | None:
    try:
        name = run(["rev-parse", "--abbrev-ref", "HEAD"], path)
    except GitError:
        return None
    return None if name == "HEAD" else name


def local_branches(path: Path) -> list[str]:
    out = run(["for-each-ref", "--format=%(refname:short)", "refs/heads/"], path, check=False)
    return [line for line in out.splitlines() if line]


def branches_containing(path: Path, sha: str) -> list[str]:
    out = run(["branch", "--format=%(refname:short)", "--contains", sha], path, check=False)
    return [line.strip() for line in out.splitlines() if line.strip()]


_FORMAT = "%H%x1f%h%x1f%s%x1f%b%x1f%an%x1f%ae%x1f%aI%x1f%cI%x1f%P%x1e"


def log(path: Path, rev: str = "HEAD", limit: int | None = 50, paths: list[str] | None = None) -> list[Commit]:
    args = ["log", f"--format={_FORMAT}", "--no-color"]
    if limit:
        args.append(f"-n{limit}")
    args.append(rev)
    if paths:
        args += ["--", *paths]
    raw = run(args, path, check=False, strip=False)
    commits: list[Commit] = []
    for record in raw.split("\x1e"):
        record = record.strip("\n\r ")
        if not record:
            continue
        parts = record.split("\x1f")
        if len(parts) < 8:
            continue
        parts += [""] * (9 - len(parts))  # root commits have an empty %P
        sha, short, subject, body, an, ae, aI, cI, parents = parts[:9]
        commits.append(Commit(
            sha=sha, short=short, subject=subject.strip(), body=body.strip(), author_name=an, author_email=ae,
            authored=aI, committed=cI, parents=[p for p in parents.split() if p],
        ))
    return commits


def commit_files(path: Path, sha: str) -> list[str]:
    """Files changed by ``sha`` relative to its first parent (or all for root)."""
    out = run(["show", "--format=", "--name-only", "--no-renames", "-m", "--first-parent", sha], path, check=False)
    files = [line.strip() for line in out.splitlines() if line.strip()]
    # preserve order, remove dups
    seen: list[str] = []
    for f in files:
        if f not in seen:
            seen.append(f)
    return seen


def staged_files(path: Path) -> list[str]:
    out = run(["diff", "--cached", "--name-only", "--diff-filter=ACMR"], path, check=False)
    return [line for line in out.splitlines() if line]


def tracked_files(path: Path) -> list[str]:
    out = run(["ls-files", "-z"], path, check=False)
    return [f for f in out.split("\0") if f]


def check_ignored(path: Path, rel_paths: list[str]) -> dict[str, bool]:
    """Return {path: ignored?} using ``git check-ignore``."""
    if not rel_paths:
        return {}
    proc = subprocess.run(
        ["git", "check-ignore", "--no-index", "-z", "--stdin"],
        cwd=str(path), capture_output=True, text=True, encoding="utf-8", errors="replace",
        input="\0".join(rel_paths) + "\0",
    )
    ignored = {p for p in proc.stdout.split("\0") if p}
    return {p: (p in ignored) for p in rel_paths}


def init_repo(path: Path, initial_branch: str = "main") -> None:
    run(["init", "-q", "-b", initial_branch], path)
