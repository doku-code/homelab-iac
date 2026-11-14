"""Knowledge map generation (`harness docs index`).

Two generated artifacts, both derived purely from document frontmatter:

* ``docs/knowledge-map.md``   – human/agent navigation index (Markdown, Obsidian-friendly links)
* ``docs/knowledge-map.json`` – machine-readable catalog with relationships and back-references

Neither duplicates document content; they are navigation structures only.
Output contains no timestamps so that regeneration is idempotent and
staleness can be detected by simple comparison.
"""

from __future__ import annotations

import json
import posixpath
from collections import defaultdict

from harness.core import schema
from harness.core.config import Config
from harness.core.documents import Catalog, Document, build_catalog
from harness.core.util import as_list, write_text

TYPE_ORDER = [
    "milestone", "task", "decision", "overview", "architecture", "api-reference", "library-reference",
    "cli-reference", "implementation-report", "task-report", "testing-report", "investigation",
    "failed-implementation", "known-issue", "deployment", "migration", "runbook", "troubleshooting", "tool",
    "guide", "reference", "branch-summary", "commit-record",
]

STATUS_ORDER = {"active": 0, "in-progress": 0, "blocked": 1, "planned": 2, "proposed": 2, "accepted": 3,
                "current": 3, "needs-revalidation": 1, "completed": 8, "cancelled": 9, "superseded": 9,
                "deprecated": 9, "rejected": 9}


def _link(doc: Document, from_dir: str) -> str:
    target = posixpath.relpath(doc.relpath, from_dir) if from_dir else doc.relpath
    return f"[{doc.title}]({target})"


def _summary(d: Document) -> str:
    v = d.meta.get("summary")
    return str(v).strip() if v else ""


def _sort_key(d: Document):
    return (STATUS_ORDER.get(d.status or "", 5), d.id or "")


def _meta_str(d: Document, key: str) -> str:
    v = d.meta.get(key)
    return "" if v is None else str(v)


def render_knowledge_map(config: Config, catalog: Catalog | None = None) -> str:
    catalog = catalog or build_catalog(config)
    km_rel = config.get("paths.knowledge_map")
    from_dir = posixpath.dirname(km_rel)
    docs = [d for d in catalog.typed() if d.type != "index"]
    by_type: dict[str, list[Document]] = defaultdict(list)
    for d in docs:
        by_type[d.type].append(d)

    out: list[str] = []
    out.append("---")
    out.append("id: INDEX-knowledge-map")
    out.append("title: Knowledge map")
    out.append("type: index")
    out.append("status: generated")
    out.append("generated: true")
    out.append("generator: harness docs index")
    out.append("tags: [index]")
    out.append("---")
    out.append("")
    out.append("# Knowledge map")
    out.append("")
    out.append("Generated navigation index. Do not edit; regenerate with `harness docs index`.")
    out.append("Documents are the source of truth; this map only lists them.")
    out.append("")
    out.append("How to use: find the row that matches your task (by type, tag, component or ID), "
               "open only that document, then follow its `related*` links. "
               "Use `harness docs search <terms>` for anything not visible here.")
    out.append("")

    # Milestones
    ms = sorted(by_type.get("milestone", []), key=_sort_key)
    out.append("## Milestones")
    out.append("")
    if ms:
        out.append("| ID | Status | Priority | Title | Tasks | Summary |")
        out.append("|----|--------|----------|-------|-------|---------|")
        for d in ms:
            tasks = [t for t in by_type.get("task", []) if str(t.meta.get("milestone")) == d.id]
            counts = defaultdict(int)
            for t in tasks:
                counts[t.status or "?"] += 1
            summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "none"
            out.append(f"| {d.id} | {d.status} | {_meta_str(d, 'priority')} | {_link(d, from_dir)} | {summary} | {_summary(d)} |")
    else:
        out.append("_No milestones._")
    out.append("")

    # Tasks (open first)
    tasks = sorted(by_type.get("task", []), key=_sort_key)
    out.append("## Tasks")
    out.append("")
    if tasks:
        out.append("| ID | Status | Priority | Milestone | Title | Summary |")
        out.append("|----|--------|----------|-----------|-------|---------|")
        for d in tasks:
            out.append(f"| {d.id} | {d.status} | {_meta_str(d, 'priority')} | {_meta_str(d, 'milestone')} | "
                       f"{_link(d, from_dir)} | {_summary(d)} |")
    else:
        out.append("_No tasks._")
    out.append("")

    # Decisions
    decisions = sorted(by_type.get("decision", []), key=lambda d: d.id or "")
    out.append("## Decisions")
    out.append("")
    if decisions:
        out.append("| ID | Status | Title | Component | Summary |")
        out.append("|----|--------|-------|-----------|---------|")
        for d in decisions:
            out.append(f"| {d.id} | {d.status} | {_link(d, from_dir)} | {_meta_str(d, 'component')} | {_summary(d)} |")
    else:
        out.append("_No decisions recorded._")
    out.append("")

    # External references grouped by technology
    refs = [d for t in schema.REFERENCE_TYPES for d in by_type.get(t, [])]
    out.append("## External references")
    out.append("")
    if refs:
        by_tech: dict[str, list[Document]] = defaultdict(list)
        for d in refs:
            by_tech[_meta_str(d, "technology") or "unspecified"].append(d)
        for tech in sorted(by_tech):
            out.append(f"### {tech}")
            out.append("")
            out.append("| ID | Type | Status | Version | Title |")
            out.append("|----|------|--------|---------|-------|")
            for d in sorted(by_tech[tech], key=lambda d: d.id or ""):
                out.append(f"| {d.id} | {d.type} | {d.status} | {_meta_str(d, 'version')} | {_link(d, from_dir)} |")
            out.append("")
    else:
        out.append("_No external references captured yet. Create one with `harness new api-reference`._")
        out.append("")

    # Other document types
    other_types = [t for t in TYPE_ORDER if t not in ("milestone", "task", "decision", *schema.REFERENCE_TYPES,
                                                       "commit-record")]
    out.append("## Documents by type")
    out.append("")
    any_other = False
    for t in other_types:
        items = sorted(by_type.get(t, []), key=lambda d: d.id or "")
        if not items:
            continue
        any_other = True
        dt = schema.doc_type(t)
        out.append(f"### {dt.title if dt else t}")
        out.append("")
        for d in items:
            comp = _meta_str(d, "component")
            extra = f" — {comp}" if comp else ""
            tags = ", ".join(d.tags)
            tag_s = f" `{tags}`" if tags else ""
            summ = f" — {_summary(d)}" if _summary(d) else ""
            out.append(f"- **{d.id}** {_link(d, from_dir)} ({d.status}){extra}{tag_s}{summ}")
        out.append("")
    if not any_other:
        out.append("_No other documents._")
        out.append("")

    # Implementation history (summarised, never one line per commit)
    records = by_type.get("commit-record", [])
    out.append("## Implementation history")
    out.append("")
    if records:
        by_branch: dict[str, int] = defaultdict(int)
        for d in records:
            by_branch[_meta_str(d, "branch") or "unknown"] += 1
        hist_rel = config.get("paths.history")
        hist_link = posixpath.relpath(hist_rel, from_dir) if from_dir else hist_rel
        out.append(f"{len(records)} commit records under [{hist_rel}/]({hist_link}/README.md). "
                   f"Branches: " + ", ".join(f"{b} ({n})" for b, n in sorted(by_branch.items())) + ".")
    else:
        out.append("_No commit records. Generate with `harness history sync`._")
    out.append("")

    # Indexes: tags, components, technologies
    def _index(label: str, key_fn) -> None:
        groups: dict[str, list[str]] = defaultdict(list)
        for d in docs:
            for k in key_fn(d):
                groups[str(k)].append(d.id)
        out.append(f"## By {label}")
        out.append("")
        if groups:
            for k in sorted(groups):
                out.append(f"- **{k}**: " + ", ".join(sorted(groups[k])))
        else:
            out.append(f"_No {label} recorded._")
        out.append("")

    _index("tag", lambda d: d.tags)
    _index("component", lambda d: as_list(d.meta.get("component")))
    _index("technology", lambda d: as_list(d.meta.get("technology")))

    # Broken references
    broken = _broken_references(catalog)
    out.append("## Broken references")
    out.append("")
    if broken:
        for src, fld, target in broken:
            out.append(f"- {src}: `{fld}` → unknown `{target}`")
    else:
        out.append("_None._")
    out.append("")
    return "\n".join(out)


def _broken_references(catalog: Catalog) -> list[tuple[str, str, str]]:
    broken: list[tuple[str, str, str]] = []
    for d in catalog.typed():
        for fld, target in d.id_references():
            if target not in catalog.by_id:
                broken.append((d.id, fld, target))
    return broken


def render_catalog_json(config: Config, catalog: Catalog | None = None) -> str:
    catalog = catalog or build_catalog(config)
    entries = []
    for d in sorted(catalog.typed(), key=lambda d: d.id or ""):
        if d.type == "index":
            continue
        relations = {}
        for fld in schema.RELATION_FIELDS:
            v = d.meta.get(fld)
            if v:
                relations[fld] = [str(x) for x in as_list(v)]
        entry = {
            "id": d.id,
            "title": d.title,
            "summary": _summary(d) or None,
            "importance": d.meta.get("importance"),
            "lifecycle": schema.lifecycle_of(d.meta.get("status"), d.meta.get("superseded_by")),
            "topics": [str(t) for t in as_list(d.meta.get("topics"))],
            "applies_to": [str(t) for t in as_list(d.meta.get("applies_to"))],
            "source_paths": [str(t) for t in as_list(d.meta.get("source_paths"))],
            "last_verified": None if d.meta.get("last_verified") is None else str(d.meta.get("last_verified")),
            "review_after": None if d.meta.get("review_after") is None else str(d.meta.get("review_after")),
            "type": d.type,
            "status": d.status,
            "path": d.relpath,
            "tags": d.tags,
            "component": d.meta.get("component"),
            "technology": d.meta.get("technology"),
            "priority": d.meta.get("priority"),
            "milestone": d.meta.get("milestone"),
            "source": d.meta.get("source"),
            "version": None if d.meta.get("version") is None else str(d.meta.get("version")),
            "headings": d.headings(),
            "relations": relations,
            "backrefs": [{"from": src, "field": fld} for src, fld in sorted(catalog.backrefs.get(d.id, []))],
        }
        entries.append(entry)
    by_tag: dict[str, list[str]] = defaultdict(list)
    by_type: dict[str, list[str]] = defaultdict(list)
    for e in entries:
        by_type[e["type"]].append(e["id"])
        for t in e["tags"]:
            by_tag[t].append(e["id"])
    data = {
        "generator": "harness docs index",
        "schema_version": 1,
        "documents": entries,
        "by_type": dict(sorted(by_type.items())),
        "by_tag": dict(sorted(by_tag.items())),
        "broken_references": [{"from": s, "field": f, "target": t} for s, f, t in _broken_references(catalog)],
    }
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def render_llms_txt(config: Config, catalog: Catalog | None = None) -> str:
    """llms.txt-shaped index: H1, blockquote summary, H2 sections of `- [title](path): summary` lines."""
    catalog = catalog or build_catalog(config)
    llms_rel = config.get("paths.llms")
    from_dir = posixpath.dirname(llms_rel)
    docs = [d for d in catalog.typed() if d.type not in ("index", "commit-record")]
    out = [f"# {config.project_name}", ""]
    desc = (config.get("project.description") or "").strip()
    out.append(f"> {desc}" if desc else "> Project knowledge index generated by the agent harness.")
    out.append("")
    out.append("Generated by `harness docs index`; one line per document. Open a document only when its line matches the task.")
    out.append("")
    by_type: dict[str, list[Document]] = defaultdict(list)
    for d in docs:
        by_type[d.type].append(d)
    for t in TYPE_ORDER:
        items = by_type.get(t)
        if not items:
            continue
        dt = schema.doc_type(t)
        out.append(f"## {dt.title if dt else t}")
        out.append("")
        for d in sorted(items, key=_sort_key):
            target = posixpath.relpath(d.relpath, from_dir) if from_dir else d.relpath
            line = f"- [{d.title}]({target})"
            summ = _summary(d)
            status = f" [{d.status}]" if d.status else ""
            out.append(line + (f": {summ}" if summ else "") + status)
        out.append("")
    hist = config.get("paths.history")
    out.append("## Optional")
    out.append("")
    out.append(f"- [Knowledge map]({posixpath.relpath(config.get('paths.knowledge_map'), from_dir) if from_dir else config.get('paths.knowledge_map')}): full navigation index with tags, components and back-references")
    out.append(f"- [Implementation history]({posixpath.relpath(hist + '/README.md', from_dir) if from_dir else hist + '/README.md'}): commit records derived from Git")
    out.append("")
    return "\n".join(out)


def write_indexes(config: Config, catalog: Catalog | None = None) -> list[str]:
    """Write both indexes; return the relative paths that changed."""
    catalog = catalog or build_catalog(config)
    changed: list[str] = []
    if write_text(config.rel_path("knowledge_map"), render_knowledge_map(config, catalog)):
        changed.append(config.get("paths.knowledge_map"))
    if write_text(config.rel_path("catalog"), render_catalog_json(config, catalog)):
        changed.append(config.get("paths.catalog"))
    if config.get("documents.llms_txt") and write_text(config.rel_path("llms"), render_llms_txt(config, catalog)):
        changed.append(config.get("paths.llms"))
    from harness.dashboard import write_dashboard

    if write_dashboard(config, catalog):
        changed.append(f"{config.get('paths.docs')}/dashboard.md")
    history_index = config.rel_path("history") / "README.md"
    if (config.rel_path("history") / "branches").exists():
        from harness.history import render_index

        if write_text(history_index, render_index(config)):
            changed.append(f"{config.get('paths.history')}/README.md")
    return changed
