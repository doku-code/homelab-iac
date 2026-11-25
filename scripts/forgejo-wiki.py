#!/usr/bin/env python3
"""Builds and publishes the Forgejo wiki of this repository (TASK-035).

The pages themselves come from the agent harness (`harness docs export-wiki`: one page per document, links
between documents rewritten, a refusal to export anything that looks like a secret). This script replaces what
the harness puts around them:

- Home is docs/home.md, not the README followed by a list of every page;
- the sidebar lists the maps (docs/hubs, in their `nav_order`), the entry documents and the indexes, not every
  task and decision; the full list is the page "All pages";
- every page starts with the file it is generated from;
- a link to a file of the repository that is not a page leads to that file on Forgejo.

  forgejo-wiki.py --out DIR      write the pages into DIR (emptied of its *.md first)
  forgejo-wiki.py --publish      push them to the wiki repository: HARNESS_WIKI_REMOTE, or the origin's
                                 <repository>.wiki.git; HARNESS_WIKI_TOKEN is passed to git through the
                                 environment by the harness, never in a URL or on a command line
  forgejo-wiki.py --publish --dry-run
"""
import argparse
import os
import posixpath
import re
import sys
from pathlib import Path

from harness import wiki
from harness.core import schema
from harness.core.config import load as load_config

ROOT = Path(__file__).resolve().parent.parent
SOURCE_URL = "https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/"
HOME_SOURCE = "docs/home.md"
MAPS_DIR = "docs/hubs/"
START_HERE = ["docs/handoff.md", "docs/project-overview.md", "docs/architecture/platform.md",
              "docs/reference/infrastructure-inventory.md"]
INDEXES = ["docs/dashboard.md", "docs/knowledge-map.md"]
ALL_PAGES = "All-pages"
LINK = re.compile(r"(?<!\!)\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+)((?:\s+\"[^\"]*\")?)\)")
FENCE = re.compile(r"^```.*?^```", re.S | re.M)
build_harness_pages = wiki.build_pages


def nav_order(page):
    text = (ROOT / page.source).read_text(encoding="utf-8")
    match = re.search(r"^nav_order:\s*(\d+)\s*$", text, re.M)
    return (int(match.group(1)) if match else 99, page.title)


def repository_links(page, names):
    """Links the harness left relative because their target is no page: they lead to the file on Forgejo."""
    folder = posixpath.dirname(page.source)

    def link(match):
        text, target, title = match.groups()
        clean = target.partition("#")[0]
        if not clean or target.startswith("#") or re.match(r"[a-z][a-z0-9+.-]*:", target, re.I) or clean in names:
            return match.group(0)
        resolved = posixpath.normpath(posixpath.join(folder, clean))
        if resolved.startswith("..") or not (ROOT / resolved).exists():
            return match.group(0)
        return f"[{text}]({SOURCE_URL}{resolved}{title})"

    pieces, last = [], 0
    for fence in FENCE.finditer(page.content):  # a diagram or an example is not prose: leave it alone
        pieces += [LINK.sub(link, page.content[last:fence.start()]), fence.group(0)]
        last = fence.end()
    return "".join(pieces) + LINK.sub(link, page.content[last:])


def banner(page):
    return (f"> Generated from [`{page.source}`]({SOURCE_URL}{page.source}). Edit it in Git: changes made in the wiki "
            "are overwritten.\n\n")


def all_pages(pages):
    groups = {}
    for page in pages:
        groups.setdefault(page.doc_type or "other", []).append(page)
    lines = ["# All pages", "", "Every document of the repository that is published here, by type.", ""]
    for kind in sorted(groups, key=lambda k: (schema.doc_type(k).title if schema.doc_type(k) else k).lower()):
        described = schema.doc_type(kind)
        lines += [f"## {described.title if described else kind.capitalize()}", ""]
        for page in sorted(groups[kind], key=lambda p: p.name):
            lines.append(f"- [{page.title}]({page.name})" + (f" ({page.status})" if page.status else ""))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def navigation(config, pages):
    by_source = {page.source: page for page in pages}
    if HOME_SOURCE not in by_source:
        raise wiki.WikiExportError(f"{HOME_SOURCE} is missing: it is the wiki's Home page")
    home = by_source[HOME_SOURCE]
    maps = sorted((p for p in pages if p.source.startswith(MAPS_DIR)), key=nav_order)

    def entries(sources):
        return [f"- [{by_source[s].title}]({by_source[s].name})" for s in sources if s in by_source]

    sidebar = ["- [Home](Home)", "", "**Maps**", ""] + [f"- [{p.title}]({p.name})" for p in maps]
    sidebar += ["", "**Start here**", ""] + entries(START_HERE)
    sidebar += ["", "**Indexes**", ""] + entries(INDEXES) + [f"- [All pages]({ALL_PAGES})"]
    footer = (f"_Generated from [{config.project_name}]({SOURCE_URL.split('/src/')[0]}) by `scripts/forgejo-wiki.py`. "
              "Edit the repository, never the wiki._\n")
    listing = all_pages([p for p in pages if p is not home])
    front = re.sub(r"^> \*\*ID:\*\*.*\n(?:> .*\n)*\n", "", home.content, count=1, flags=re.M)  # no metadata line on Home
    return [
        wiki.Page("Home", HOME_SOURCE, home.title, "index", None, front),
        wiki.Page(ALL_PAGES, "<generated>", "All pages", "index", None, listing),
        wiki.Page("_Sidebar", "<generated>", "Sidebar", "index", None, "\n".join(sidebar) + "\n"),
        wiki.Page("_Footer", "<generated>", "Footer", "index", None, footer),
    ]


def build_pages(config, catalog=None):
    """The harness's pages with our navigation; the same output for the same commit."""
    built, skipped = build_harness_pages(config, catalog)
    documents = [p for p in built if p.source != "<generated>"]
    names = {p.name for p in documents} | {"Home", ALL_PAGES}
    home_name = next((p.name for p in documents if p.source == HOME_SOURCE), None)
    for page in documents:
        if home_name:  # the page of docs/home.md is published as Home only
            page.content = re.sub(rf"\]\({re.escape(home_name)}(#[^)]*)?\)", r"](Home\1)", page.content)
        page.content = banner(page) + repository_links(page, names)
    pages = [p for p in documents if p.source != HOME_SOURCE] + navigation(config, documents)
    return sorted(pages, key=lambda p: p.name), skipped


wiki.build_pages = build_pages  # `wiki.export` and `wiki.publish` look the function up in their module


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--out", metavar="DIR")
    mode.add_argument("--publish", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(ROOT)
    try:
        if args.out:
            result = wiki.export(config, Path(args.out).resolve(), clean=True)
            print(f"{len(result.pages)} pages in {args.out}: {len(result.written)} written, {len(result.removed)} removed")
        else:
            token = os.environ.get(config.get("wiki.token_env") or "HARNESS_WIKI_TOKEN") or None
            print(wiki.publish(config, token=token, dry_run=args.dry_run).message)
    except (wiki.WikiExportError, wiki.WikiPublishError) as error:
        sys.exit(f"error: {error}")


if __name__ == "__main__":
    main()
