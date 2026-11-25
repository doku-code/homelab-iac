#!/usr/bin/env python3
"""Writes this repository's documentation as the tree the wiki pulls (TASK-029).

The wiki (Wiki.js, services/wiki) takes its pages from the branch `wiki` of this repository through its Git
storage, in pull-only mode: the repository is the source, the wiki is a reader's view of it. This script
builds that branch's content from README.md, AGENTS.md, docs/ (without the archive), milestones/, tasks/ and
history/:

- every page gets the front matter the wiki reads (title, description, tags, `editor: markdown`: without an
  editor the wiki keeps the front matter in the page body);
- the body starts with the title as its first heading (the wiki takes it as page title), followed by one line
  with the document's status, type, dates and a link to the source file;
- links between documents become wiki paths, links to anything else in the repository become links to the
  file on Forgejo;
- each folder gets an index page listing its documents.

The output is the same for the same commit: no clock, no random order.

  wiki-export.py --out DIR                 write the tree into DIR (emptied first, except .git)
  wiki-export.py --publish REMOTE          write it and push it to the branch `wiki` of REMOTE, as one commit on
                                           top of the previous export; nothing is pushed when nothing changed
The push uses git's own credentials; when WIKI_EXPORT_TOKEN is set it is sent as a header from the environment
(never on a command line, never in a URL).
"""
import argparse
import base64
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE_URL = "https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/"
BRANCH = "wiki"
SINGLE = ["README.md", "AGENTS.md"]
TREES = ["docs", "milestones", "tasks", "history"]
EXCLUDED = ("docs/archive/",)
INDEX_TITLES = {
    "docs": "Documentation", "docs/architecture": "Architecture", "docs/decisions": "Decisions",
    "docs/investigations": "Investigations", "docs/hubs": "Maps", "docs/reference": "Reference", "docs/reference/external": "External references",
    "milestones": "Milestones", "tasks": "Tasks", "history": "History",
}
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
LEADING_COMMENT = re.compile(r"\A\s*<!--.*?-->\s*", re.S)
LINK = re.compile(r"(?<!\!)\[([^\]\n]*)\]\(([^)\s]+)((?:\s+\"[^\"]*\")?)\)")
H1 = re.compile(r"\A#[ \t]+(.+?)[ \t]*\n")


def page_path(source):
    """The wiki files a page under its lowercased path, underscores as hyphens, without the extension."""
    if source == "README.md":
        return "README"
    return re.sub(r"\.md$", "", source).lower().replace("_", "-")


def sources():
    found = [name for name in SINGLE if (ROOT / name).is_file()]
    for tree in TREES:
        for path in sorted((ROOT / tree).rglob("*.md")) if (ROOT / tree).is_dir() else []:
            relative = path.relative_to(ROOT).as_posix()
            if not relative.startswith(EXCLUDED):
                found.append(relative)
    return found


def read(source):
    text = (ROOT / source).read_text()
    meta = {}
    match = FRONT_MATTER.match(text)
    if match:
        loaded = yaml.safe_load(match.group(1))
        meta = loaded if isinstance(loaded, dict) else {}
        text = text[match.end():]
    while LEADING_COMMENT.match(text):
        text = LEADING_COMMENT.sub("", text, count=1)
    text = text.lstrip("\n")
    heading = H1.match(text)
    title = (heading.group(1) if heading else None) or str(meta.get("title") or Path(source).stem)
    body = text[heading.end():] if heading else text
    # Tasks, milestones and decisions are known by their number: it leads the title, so lists sort by it.
    number = str(meta.get("id") or "")
    if re.fullmatch(r"(TASK|ADR)-\d+|M\d+", number) and not title.startswith(number):
        title = f"{number} — {title.strip()}"
    return meta, title.strip(), body.strip("\n")


def one_line(value, limit=250):
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def tags_of(meta):
    tags = []
    for value in [meta.get("type"), meta.get("status"), *(meta.get("tags") if isinstance(meta.get("tags"), list) else [])]:
        tag = str(value).strip().lower() if value else ""
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def rewrite_links(body, source, pages, folders):
    """Links to exported documents become wiki paths; links to other files of the repository go to Forgejo."""
    base = posixpath.dirname(source)

    def target(match):
        label, link, title = match.groups()
        if re.match(r"[a-z][a-z0-9+.-]*:|#|//", link, re.I):
            return match.group(0)
        path, _, anchor = link.partition("#")
        resolved = posixpath.normpath(posixpath.join(base, path)) if not path.startswith("/") else path.lstrip("/")
        anchor = f"#{anchor}" if anchor else ""
        if resolved in pages:
            return f"[{label}](/{pages[resolved]}{anchor}{title})"
        if resolved.rstrip("/") in folders:
            return f"[{label}](/{resolved.rstrip('/').lower()}{title})"
        if resolved != "." and not resolved.startswith("..") and (ROOT / resolved).exists():
            kind = "" if (ROOT / resolved).is_file() else "/"
            return f"[{label}]({SOURCE_URL}{resolved.rstrip('/')}{kind}{anchor}{title})"
        return match.group(0)

    out, fenced = [], False
    for line in body.split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        out.append(line if fenced else LINK.sub(target, line))
    return "\n".join(out)


def front_matter(title, description, tags, meta):
    data = {"title": title, "description": description, "published": True, "tags": tags, "editor": "markdown"}
    for key, name in (("updated", "date"), ("created", "dateCreated")):
        if meta.get(key):
            data[name] = f"{meta[key]}T00:00:00.000Z"
    return "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000) + "---\n\n"


def info_line(meta, source):
    parts = [f"**{label}:** {meta[key]}" for key, label in (("id", "ID"), ("type", "Type"), ("status", "Status"), ("updated", "Updated")) if meta.get(key)]
    parts.append(f"[Source]({SOURCE_URL}{source})")
    return "> " + " · ".join(parts)


def render(source, pages, folders):
    meta, title, body = read(source)
    body = rewrite_links(body, source, pages, folders)
    description = one_line(meta.get("summary") or meta.get("description"))
    return front_matter(title, description, tags_of(meta), meta) + f"# {title}\n\n{info_line(meta, source)}\n\n{body}\n"


def index(folder, documents, pages, folders):
    """One page per folder: its sub-folders and its documents with status and summary."""
    title = INDEX_TITLES.get(folder, folder.rsplit("/", 1)[-1].replace("-", " ").capitalize())
    lines = [f"# {title}", "", f"> Generated from the repository: [{folder}/]({SOURCE_URL}{folder}/)", ""]
    children = sorted(f for f in folders if posixpath.dirname(f) == folder)
    if children:
        lines += ["## Sections", ""] + [f"- [{INDEX_TITLES.get(c, c.rsplit('/', 1)[-1])}](/{c.lower()})" for c in children] + [""]
    here = [d for d in documents if posixpath.dirname(d) == folder]
    if here:
        lines += ["## Documents", "", "| Document | Status | Summary |", "|----------|--------|---------|"]
        for source in here:
            meta, doc_title, _ = read(source)
            cells = [f"[{doc_title}](/{pages[source]})", str(meta.get("status") or ""), one_line(meta.get("summary"), 200)]
            lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
        lines.append("")
    description = f"{title}: index of {folder}/ in the homelab-iac repository"
    return front_matter(title, description, ["index"], {}) + "\n".join(lines)


def build(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for entry in out.iterdir():
        if entry.name != ".git":
            shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    documents = sources()
    pages = {source: page_path(source) for source in documents}
    assert len(set(pages.values())) == len(pages), "two documents would land on the same wiki path"
    folders = sorted({posixpath.dirname(s) for s in documents if "/" in s}
                     | {posixpath.dirname(posixpath.dirname(s)) for s in documents if s.count("/") > 1})
    folders = [f for f in folders if f]
    # A folder's index lives beside the folder; a document already filed there keeps the path.
    indexed = [f for f in folders if f.lower() not in pages.values()]
    written = {}
    for source in documents:
        written[f"{pages[source]}.md"] = render(source, pages, set(indexed))
    for folder in indexed:
        written[f"{folder.lower()}.md"] = index(folder, documents, pages, indexed)
    for name, text in sorted(written.items()):
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return sorted(written)


def git(directory, *args, env=None, capture=False):
    return subprocess.run(["git", "-C", str(directory), *args], check=True, env=env, text=True, capture_output=capture)


def publish(remote):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    token = os.environ.get("WIKI_EXPORT_TOKEN")
    if token:
        header = "Authorization: Basic " + base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.extraheader", GIT_CONFIG_VALUE_0=header)
    commit = git(ROOT, "rev-parse", "HEAD", capture=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="wiki-export-") as directory:
        work = Path(directory) / "tree"
        exists = subprocess.run(["git", "ls-remote", "--exit-code", "--heads", remote, BRANCH], env=env, capture_output=True).returncode == 0
        if exists:
            subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--branch", BRANCH, remote, str(work)], check=True, env=env)
        else:
            work.mkdir()
            git(work, "init", "--quiet", "--initial-branch", BRANCH)
        files = build(work)
        git(work, "add", "--all")
        if not git(work, "status", "--porcelain", capture=True).stdout.strip():
            print(f"wiki-export: {len(files)} pages, nothing changed since the last export")
            return
        identity = ["-c", "user.name=homelab-iac wiki export", "-c", "user.email=wiki-export@doku-lab.net"]
        git(work, *identity, "commit", "--quiet", "-m", f"docs: export of {commit}")
        git(work, "push", "--quiet", remote, f"HEAD:refs/heads/{BRANCH}", env=env)
        print(f"wiki-export: {len(files)} pages pushed to the branch {BRANCH} (export of {commit[:12]})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out")
    group.add_argument("--publish")
    args = parser.parse_args()
    if args.publish:
        publish(args.publish)
    else:
        files = build(args.out)
        print(f"wiki-export: {len(files)} pages written to {args.out}")


if __name__ == "__main__":
    sys.exit(main())
