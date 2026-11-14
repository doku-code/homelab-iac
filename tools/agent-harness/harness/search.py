"""`harness docs search`: legacy filters and output on top of the context engine (`harness.context`).

The filter set below is shared with `harness context search`; ranking lives only in the context engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from harness.core.config import Config
from harness.core.documents import Catalog, Document
from harness.core.util import as_list


@dataclass
class Hit:
    doc: Document
    score: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class Filters:
    types: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    component: str | None = None
    technology: str | None = None
    task: str | None = None
    milestone: str | None = None
    implementation: str | None = None
    doc_id: str | None = None
    path: str | None = None


def _matches_filters(d: Document, f: Filters) -> bool:
    if f.types and d.type not in f.types:
        return False
    if f.statuses and d.status not in f.statuses:
        return False
    if f.tags and not set(t.lower() for t in d.tags) & set(t.lower() for t in f.tags):
        return False
    if f.component and f.component.lower() not in [str(c).lower() for c in as_list(d.meta.get("component"))]:
        return False
    if f.technology and f.technology.lower() not in [str(c).lower() for c in as_list(d.meta.get("technology"))]:
        return False
    if f.doc_id and d.id != f.doc_id:
        return False
    if f.path and f.path.lower() not in d.relpath.lower():
        return False
    refs = {t for _, t in d.id_references()}
    if f.task and f.task not in refs and d.id != f.task:
        return False
    if f.milestone and f.milestone not in refs and d.id != f.milestone:
        return False
    if f.implementation:
        impls = [p.lower() for p in d.path_references()]
        if not any(f.implementation.lower() in p for p in impls):
            return False
    return True


def search(config: Config, query: str = "", filters: Filters | None = None, *, limit: int = 20,
           catalog: Catalog | None = None, include_history: bool = False) -> list[Hit]:
    """Compatibility wrapper: `docs search` keeps its filters and output but ranks with the context engine.

    Unlike `harness context search`, historical documents (superseded, archived) stay included, ranked lower by
    their freshness component, as `docs search` always did.
    """
    from harness.context import Engine, Query

    engine = Engine.load(config, catalog=catalog)
    q = Query(text=query, legacy_filters=filters or Filters(), include_historical=True,
              include_history_records=include_history, limit=max(1, min(limit, 200)))
    return [Hit(doc=r.doc, score=round(r.score, 4), reasons=r.reasons) for r in engine.search(q)]


def format_hit(h: Hit) -> str:
    d = h.doc
    tags = f" [{', '.join(d.tags)}]" if d.tags else ""
    line = f"{d.id:<22} {d.type:<22} {d.status or '-':<12} {d.relpath} — {d.title}{tags}"
    summ = str(d.meta.get("summary") or "").strip()
    return line + (f"\n{'':<22} {summ}" if summ else "")
