"""Scanning knowledge documents and building the in-memory catalog.

The catalog is deliberately simple: a list of documents with their metadata,
their outgoing references and the computed back-references. It is rebuilt
from the Markdown files every time (fast for any repository that a single
developer can keep in their head), so it can never go stale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from harness.core import frontmatter, schema
from harness.core.config import Config
from harness.core.util import as_list, rel

MD_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$", re.MULTILINE)


@dataclass
class Document:
    path: Path
    relpath: str
    meta: dict
    body: str
    has_frontmatter: bool
    error: str | None = None

    @property
    def id(self) -> str | None:
        v = self.meta.get("id")
        return str(v) if v is not None else None

    @property
    def type(self) -> str | None:
        v = self.meta.get("type")
        return str(v) if v is not None else None

    @property
    def title(self) -> str:
        return str(self.meta.get("title") or self.path.stem)

    @property
    def status(self) -> str | None:
        v = self.meta.get("status")
        return str(v) if v is not None else None

    @property
    def tags(self) -> list[str]:
        return [str(t) for t in as_list(self.meta.get("tags"))]

    def id_references(self) -> list[tuple[str, str]]:
        """(field, referenced_id) pairs for every ID-valued relationship."""
        out: list[tuple[str, str]] = []
        for f in schema.ID_RELATION_FIELDS:
            for v in as_list(self.meta.get(f)):
                out.append((f, str(v)))
        for f in schema.SCALAR_ID_FIELDS:
            v = self.meta.get(f)
            if v:
                out.append((f, str(v)))
        return out

    def path_references(self) -> list[str]:
        out: list[str] = []
        for f in schema.PATH_RELATION_FIELDS:
            out.extend(str(v) for v in as_list(self.meta.get(f)))
        return out

    def headings(self) -> list[str]:
        return [m.group(2).strip() for m in HEADING_RE.finditer(self.body)]

    def markdown_links(self) -> list[tuple[str, str]]:
        """(text, target) for every inline Markdown link in the body."""
        links = [(m.group(1), m.group(2)) for m in MD_LINK_RE.finditer(self.body)]
        return links

    def wiki_links(self) -> list[str]:
        return [m.group(1).strip() for m in WIKI_LINK_RE.finditer(self.body)]


def load_document(path: Path, root: Path) -> Document:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return Document(path=path, relpath=rel(path, root), meta={}, body="", has_frontmatter=False,
                        error=f"unreadable: {exc}")
    try:
        parsed = frontmatter.parse(text)
    except frontmatter.FrontmatterError as exc:
        return Document(path=path, relpath=rel(path, root), meta={}, body=text, has_frontmatter=True, error=str(exc))
    return Document(path=path, relpath=rel(path, root), meta=parsed.meta, body=parsed.body,
                    has_frontmatter=parsed.has_frontmatter)


def iter_markdown(roots: Iterable[Path], ignore_dirs: Iterable[str], project_root: Path) -> Iterable[Path]:
    ignore = {d.strip("/").lower() for d in ignore_dirs}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            relative = rel(path, project_root)
            parts = relative.split("/")
            if any(p.lower() in ignore for p in parts[:-1]):
                continue
            if any(p.startswith(".") and p not in (".",) for p in parts[:-1]):
                continue
            if not _inside(path, project_root):
                continue   # a symlink (file or directory) pointing outside the repository is never read
            yield path


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


@dataclass
class Catalog:
    root: Path
    documents: list[Document] = field(default_factory=list)
    by_id: dict[str, Document] = field(default_factory=dict)
    duplicates: dict[str, list[Document]] = field(default_factory=dict)
    backrefs: dict[str, list[tuple[str, str]]] = field(default_factory=dict)  # id -> [(from_id, field)]

    def typed(self) -> list[Document]:
        return [d for d in self.documents if d.has_frontmatter and d.id and d.type]

    def of_type(self, *types: str) -> list[Document]:
        return [d for d in self.typed() if d.type in types]

    def get(self, doc_id: str) -> Document | None:
        return self.by_id.get(doc_id)

    def resolve_path(self, relpath: str) -> Document | None:
        for d in self.documents:
            if d.relpath == relpath:
                return d
        return None


def build_catalog(config: Config, roots: Iterable[Path] | None = None) -> Catalog:
    roots = list(roots) if roots is not None else config.document_roots()
    ignore = config.get("documents.ignore") or []
    cat = Catalog(root=config.root)
    for path in iter_markdown(roots, ignore, config.root):
        cat.documents.append(load_document(path, config.root))
    # Also include the root README/AGENTS/CLAUDE only if they carry frontmatter (optional).
    for name in ("README.md",):
        p = config.root / name
        if p.exists():
            d = load_document(p, config.root)
            if d.has_frontmatter and d.id:
                cat.documents.append(d)
    for d in cat.documents:
        if not d.id:
            continue
        if d.id in cat.by_id:
            cat.duplicates.setdefault(d.id, [cat.by_id[d.id]]).append(d)
        else:
            cat.by_id[d.id] = d
    for d in cat.typed():
        for fld, target in d.id_references():
            cat.backrefs.setdefault(target, []).append((d.id, fld))
    return cat
