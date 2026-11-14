"""`harness new`: create a document from a template with a valid ID and metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harness.core import assets, schema
from harness.core.config import Config
from harness.core.documents import Catalog, build_catalog
from harness.core.util import slugify, today, write_text


class NewDocError(ValueError):
    pass


def yaml_scalar(value: str) -> str:
    """Quote a title for a `key: value` frontmatter line when YAML would otherwise misparse it."""
    needs_quote = (
        not value
        or value[0] in "!&*-?[]{}#|>%@`'\"" or value.strip() != value
        or ": " in value or " #" in value or value.endswith(":")
        or value.lower() in ("true", "false", "null", "yes", "no", "on", "off", "~")
        or value[0] in "0123456789+."  # numbers and dates would lose their string type
    )
    if not needs_quote:
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'



@dataclass
class Created:
    path: Path
    relpath: str
    doc_id: str


def next_numbered_id(type_name: str, catalog: Catalog) -> str:
    dt = schema.DOC_TYPES[type_name]
    highest = 0
    rx = re.compile(r"(\d+)$")
    for d in catalog.of_type(type_name):
        m = rx.search(d.id or "")
        if m:
            highest = max(highest, int(m.group(1)))
    # Also consider files whose names carry the prefix but that failed to parse.
    for d in catalog.documents:
        m = re.match(rf"^{re.escape(dt.id_prefix)}(\d+)", d.path.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return schema.format_numbered_id(type_name, highest + 1)


def create(config: Config, type_name: str, title: str, *, doc_id: str | None = None, directory: str | None = None,
           variables: dict[str, object] | None = None, catalog: Catalog | None = None) -> Created:
    dt = schema.doc_type(type_name)
    if dt is None:
        raise NewDocError(f"unknown document type {type_name!r}; known: {', '.join(sorted(schema.DOC_TYPES))}")
    if type_name == "index":
        raise NewDocError("index documents are generated; run `harness docs index`")
    catalog = catalog or build_catalog(config)

    if doc_id is None:
        if dt.numbered:
            doc_id = next_numbered_id(type_name, catalog)
        else:
            doc_id = f"{dt.id_prefix}{slugify(title)}"
    if not schema.is_valid_id(type_name, doc_id):
        raise NewDocError(f"id {doc_id!r} does not match {dt.id_pattern}")
    if doc_id in catalog.by_id:
        raise NewDocError(f"id {doc_id!r} already exists at {catalog.by_id[doc_id].relpath}")

    # Target directory: configured path for planning types, template default otherwise.
    if directory:
        target_dir = config.root / directory
    elif type_name == "milestone":
        target_dir = config.rel_path("milestones")
    elif type_name == "task":
        target_dir = config.rel_path("tasks")
    elif type_name in schema.REFERENCE_TYPES:
        target_dir = config.rel_path("references")
    else:
        target_dir = config.root / dt.default_dir
    filename = f"{doc_id}-{slugify(title)}.md" if dt.numbered else f"{slugify(title)}.md"
    path = target_dir / filename
    if path.exists():
        raise NewDocError(f"file already exists: {path}")

    default_status = {
        "milestone": "planned", "task": "planned", "decision": "proposed", "known-issue": "open",
    }.get(type_name, dt.statuses[0] if type_name not in ("overview",) else "current")
    if type_name in schema.REFERENCE_TYPES:
        default_status = "current"
    if dt.statuses == schema.DOCUMENT_STATUSES:
        default_status = "current"

    vars_: dict[str, object] = {
        "id": doc_id, "title": title, "title_yaml": yaml_scalar(title),
        "summary": "", "summary_yaml": '""', "type": type_name, "status": default_status, "priority": "medium",
        "created": today(), "updated": today(), "milestone": "", "component": "", "technology": "", "version": "",
        "source": "", "environment": "", "language": "", "entrypoint": "", "branch": "", "objective": "",
        "goal": "", "description": "",
    }
    vars_.update(variables or {})
    if vars_.get("summary"):
        vars_["summary_yaml"] = yaml_scalar(str(vars_["summary"]))
    text = assets.render_asset(vars_, "templates", "documents", f"{type_name}.md")
    # Remove template guidance comments? Keep them: they are the inline rules for agents.
    write_text(path, text)
    return Created(path=path, relpath=path.relative_to(config.root).as_posix(), doc_id=doc_id)
