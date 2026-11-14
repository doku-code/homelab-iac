"""`harness history sync`: implementation-history records derived from real Git commits.

Design constraints (see ADR-003):

* A commit cannot contain its own SHA, so records are produced *after* the
  commit exists and staged for a later commit. The sync is on-demand (or
  from a post-commit hook the user installs deliberately).
* Commits whose only changes are under the history directory are skipped
  by default, which prevents sync → commit → sync loops.
* Derived facts (between ``harness:derived`` markers and in frontmatter) are
  regenerated; authored sections are preserved verbatim.
* Branch attribution is observed context at sync time: the record stores the
  branch the sync ran against plus every local branch containing the commit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from harness.core import assets, frontmatter, gitutil
from harness.core.config import Config
from harness.core.util import short_hash, slugify, today, write_text

DERIVED_START = "<!-- harness:derived:start -->"
DERIVED_END = "<!-- harness:derived:end -->"
_DERIVED_RE = re.compile(re.escape(DERIVED_START) + r".*?" + re.escape(DERIVED_END), re.DOTALL)

MAX_FILES_LISTED = 40


def encode_branch(name: str) -> str:
    """Filesystem-safe, case-insensitive-collision-resistant directory name for a branch."""
    base = name.replace("/", "--")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-.")
    lowered = safe.lower() or "branch"
    # The plain mapping is reversible only for lower-case names without '--' and without unsafe
    # characters; anything else gets a short hash suffix so distinct branches never share a directory
    # (also on case-insensitive filesystems).
    lossy = safe != base or lowered != safe or "--" in name or len(lowered) > 80
    if len(lowered) > 80:
        lowered = lowered[:80].rstrip("-.")
    if lossy:
        lowered = f"{lowered}-{short_hash(name)}"
    return lowered


def record_dirname(commit: gitutil.Commit) -> str:
    return f"{commit.short}-{slugify(commit.subject, max_len=48)}"


@dataclass
class SyncResult:
    created: list[str] = field(default_factory=list)
    refreshed: list[str] = field(default_factory=list)
    skipped_existing: int = 0
    skipped_history_only: list[str] = field(default_factory=list)
    index_path: str | None = None
    branch: str | None = None

    @property
    def changed(self) -> bool:
        return bool(self.created or self.refreshed)


def _files_table(files: list[str]) -> str:
    if not files:
        return "_No file changes (empty or merge commit without first-parent changes)._"
    lines = ["| File |", "|------|"]
    for f in files[:MAX_FILES_LISTED]:
        lines.append(f"| `{f}` |")
    if len(files) > MAX_FILES_LISTED:
        lines.append(f"| … {len(files) - MAX_FILES_LISTED} more (see `git show --stat {files and ''}`) |")
    return "\n".join(lines)


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(f'"{i}"' for i in items) + "]"


def render_record(commit: gitutil.Commit, branch: str, branches: list[str]) -> str:
    vars_ = {
        "id": f"HIST-{commit.sha}",
        "title": f"{commit.short} {commit.subject}",
        "title_yaml": _yaml_quote(f"{commit.short} {commit.subject}"),
        "summary_yaml": _yaml_quote(commit.subject),
        "commit": commit.sha,
        "short": commit.short,
        "subject": commit.subject.replace('"', "'"),
        "branch": branch,
        "branches": _yaml_list(branches),
        "branches_text": ", ".join(branches) if branches else "none observed",
        "author": commit.author_name,
        "authored": commit.authored,
        "parents": _yaml_list(commit.parents),
        "parents_text": ", ".join(f"`{p[:10]}`" for p in commit.parents) or "none (root commit)",
        "created": today(),
        "updated": today(),
        "files_table": _files_table(commit.files),
    }
    text = assets.render_asset(vars_, "templates", "documents", "commit-record.md")
    # YAML-quote the subject/title lines to survive colons and quotes.
    text = text.replace(f"subject: {vars_['subject']}", f"subject: {_yaml_quote(vars_['subject'])}", 1)
    text = text.replace(f"author: {vars_['author']}", f"author: {_yaml_quote(vars_['author'])}", 1)
    text = text.replace(f"authored: {vars_['authored']}", f"authored: \"{vars_['authored']}\"", 1)
    return text


def _yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def refresh_record(existing: str, commit: gitutil.Commit, branch: str, branches: list[str]) -> str:
    """Regenerate frontmatter facts and the derived block, keep authored sections."""
    fresh = render_record(commit, branch, branches)
    fresh_parsed = frontmatter.parse(fresh)
    old_parsed = frontmatter.parse(existing)
    meta = dict(old_parsed.meta)
    for key in ("commit", "subject", "branch", "branches", "author", "authored", "parents"):
        meta[key] = fresh_parsed.meta.get(key)
    meta["updated"] = today()
    m_new = _DERIVED_RE.search(fresh_parsed.body)
    body = old_parsed.body
    if m_new and _DERIVED_RE.search(body):
        body = _DERIVED_RE.sub(lambda _m: m_new.group(0), body, count=1)
    return frontmatter.dump(meta, body)


def _is_history_only(files: list[str], history_dir: str, generated: tuple[str, ...] = ()) -> bool:
    """True when a commit only carries history records and/or regenerated indexes.

    Such commits are the *output* of a sync; recording them would make every sync→commit cycle
    produce another commit to record (see ADR-003).
    """
    prefix = history_dir.rstrip("/") + "/"
    return bool(files) and all(f.startswith(prefix) or f in generated for f in files)


def sync(config: Config, *, branch: str | None = None, limit: int | None = None, refresh: bool = False,
         dry_run: bool = False, scan_branches: bool = True) -> SyncResult:
    root = config.root
    result = SyncResult()
    if not gitutil.is_repo(root) or not gitutil.has_commits(root):
        raise gitutil.GitError("not a Git repository with commits")
    rev = branch or "HEAD"
    branch_name = branch or gitutil.current_branch(root) or "detached"
    result.branch = branch_name
    history_dir = config.get("paths.history")
    history_root = root / history_dir
    limit = limit if limit is not None else int(config.get("history.limit") or 50)
    skip_history_only = bool(config.get("history.skip_history_only_commits", True))
    generated = (config.get("paths.knowledge_map"), config.get("paths.catalog"), config.get("paths.llms"),
                 f"{config.get('paths.docs')}/dashboard.md", f"{history_dir}/README.md")

    commits = gitutil.log(root, rev, limit=limit)
    branch_dir = history_root / "branches" / encode_branch(branch_name) / "commits"
    for commit in commits:
        commit.files = gitutil.commit_files(root, commit.sha)
        if skip_history_only and _is_history_only(commit.files, history_dir, generated):
            result.skipped_history_only.append(commit.short)
            continue
        rec_dir = branch_dir / record_dirname(commit)
        rec_path = rec_dir / "README.md"
        relp = rec_path.relative_to(root).as_posix()
        if rec_path.exists() and not refresh:
            result.skipped_existing += 1
            continue
        branches = gitutil.branches_containing(root, commit.sha) if scan_branches else [branch_name]
        if rec_path.exists():
            text = refresh_record(rec_path.read_text(encoding="utf-8"), commit, branch_name, branches)
            if not dry_run:
                if write_text(rec_path, text):
                    result.refreshed.append(relp)
            else:
                result.refreshed.append(relp)
        else:
            text = render_record(commit, branch_name, branches)
            if not dry_run:
                write_text(rec_path, text)
            result.created.append(relp)
    index_rel = f"{history_dir}/README.md"
    result.index_path = index_rel
    if not dry_run:
        write_text(history_root / "README.md", render_index(config))
    return result


def render_index(config: Config) -> str:
    """Generated index of history records: one line per record, grouped by branch directory."""
    root = config.root
    history_root = root / config.get("paths.history")
    out = ["# Implementation history", "",
           "Generated by `harness history sync`. Do not edit. Records derive from real Git commits; branch",
           "attribution is the context observed at sync time. Each record keeps derived facts separate from",
           "agent-authored explanation.", ""]
    branches_root = history_root / "branches"
    if not branches_root.exists():
        out.append("_No records yet._")
        return "\n".join(out) + "\n"
    for bdir in sorted(p for p in branches_root.iterdir() if p.is_dir()):
        commits_dir = bdir / "commits"
        records = sorted(p for p in commits_dir.glob("*/README.md")) if commits_dir.exists() else []
        if not records:
            continue
        out.append(f"## {bdir.name}")
        out.append("")
        out.append("| Commit | Subject | Status | Record |")
        out.append("|--------|---------|--------|--------|")
        rows = []
        for rec in records:
            parsed = frontmatter.parse(rec.read_text(encoding="utf-8"))
            meta = parsed.meta
            authored = str(meta.get("authored") or "")
            rows.append((authored, meta.get("commit", "")[:7] if meta.get("commit") else rec.parent.name[:7],
                         str(meta.get("subject") or rec.parent.name), str(meta.get("status") or "derived"),
                         rec.relative_to(history_root).as_posix()))
        for _authored, short, subject, status, relp in sorted(rows, reverse=True):
            out.append(f"| `{short}` | {subject} | {status} | [{relp.split('/')[-2]}]({relp}) |")
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"
