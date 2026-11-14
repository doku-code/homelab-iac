"""Context retrieval engine: lifecycle-aware, weighted, explainable, bounded.

Markdown documents stay the source of truth; every call rebuilds the in-memory catalog (milliseconds for a few
hundred documents), so there is no index to go stale. The engine:

1. filters candidates (security exclusions, lifecycle, structured property filters),
2. scores each candidate on up to five components, each in [0, 1]:
   query relevance, scope (component / applies_to / source paths), relations to an anchor (task or document),
   importance, and freshness (lifecycle + verification metadata),
3. combines the *active* components with centralised weights (`DEFAULT_WEIGHTS`, overridable in
   `harness.yaml` → `context.weights`) and returns the score with the reasons behind it.

Importance and freshness can only reorder documents that are already relevant; a document that matches neither the
query, the scope nor a relation is not returned. Graph expansion is breadth-first, cycle-safe and capped at depth 2.
Everything here is read-only except `verify`, which edits the verification lines of one document on explicit request.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from harness.core import gitutil, schema
from harness.core.config import Config
from harness.core.documents import Catalog, Document, build_catalog
from harness.core.util import as_list

DEFAULT_WEIGHTS: dict[str, float] = {
    "query": 0.40,       # query terms in id, title, topics/tags, summary, headings, body
    "scope": 0.25,       # component / applies_to and source-path overlap
    "relation": 0.15,    # graph distance to the anchor task or document
    "importance": 0.10,  # 1..5, missing = 3
    "freshness": 0.10,   # lifecycle and verification state
}
DEFAULT_BUDGETS: dict[str, dict[str, int]] = {
    "simple": {"documents": 1, "depth": 0},
    "standard": {"documents": 4, "depth": 1},
    "complex": {"documents": 8, "depth": 2},
}
MAX_DEPTH = 2
# How strongly a query term matching each field counts (per term, the best field wins).
FIELD_WEIGHTS = {"id": 1.0, "title": 1.0, "topic": 0.9, "summary": 0.8, "scope": 0.7, "heading": 0.6, "path": 0.5,
                 "body": 0.3}
DEFAULT_LIFECYCLES = ("active", "needs-review")
SCOPE_NAME_WEIGHT = 0.6   # component/applies_to match; an exact source-path match scores 1.0
STOPWORDS = {"a", "an", "and", "the", "of", "to", "for", "in", "on", "with", "by", "is", "it", "be", "as", "or", "at",
             "from", "into", "that", "this", "add", "fix", "use", "new", "implement", "make", "update"}
_TERM_RE = re.compile(r"[\w./-]+")
_SUFFIXES = ("ing", "ed", "es", "s")


def stem(term: str) -> str:
    """Very light suffix stripping so 'signing'/'signed'/'signs' match 'sign'; never below 4 characters."""
    for suf in _SUFFIXES:
        if term.endswith(suf) and len(term) - len(suf) >= 4:
            return term[: -len(suf)]
    return term


class ContextError(ValueError):
    """Invalid query or document request (CLI exit code 2), or a refused read (exit code 1)."""

    def __init__(self, message: str, *, usage: bool = True):
        super().__init__(message)
        self.usage = usage


# ---------------------------------------------------------------------------
# Document profile: metadata normalised for retrieval
# ---------------------------------------------------------------------------

def _date_str(value) -> str | None:
    if value in (None, ""):
        return None
    s = value.isoformat() if hasattr(value, "isoformat") else str(value)
    return s[:10] if schema.DATE_RE.match(s[:10]) else None


def _lower_list(*values) -> list[str]:
    out: list[str] = []
    for v in values:
        for x in as_list(v):
            s = str(x).strip().lower()
            if s and s not in out:
                out.append(s)
    return out


@dataclass
class Profile:
    doc: Document
    lifecycle: str
    importance: int
    importance_set: bool
    topics: list[str]
    scope: list[str]
    paths: list[str]
    last_verified: str | None
    review_after: str | None
    warnings: list[str] = field(default_factory=list)
    freshness: float = 0.5
    replacement: str | None = None


def profile(doc: Document, catalog: Catalog, today: date) -> Profile:
    meta = doc.meta
    imp = meta.get("importance")
    lo, hi = schema.IMPORTANCE_RANGE
    imp_ok = isinstance(imp, int) and not isinstance(imp, bool) and lo <= imp <= hi
    lifecycle = schema.lifecycle_of(meta.get("status"), meta.get("superseded_by"))
    p = Profile(
        doc=doc, lifecycle=lifecycle,
        importance=imp if imp_ok else schema.DEFAULT_IMPORTANCE, importance_set=imp_ok,
        topics=_lower_list(meta.get("tags"), meta.get("topics"), meta.get("technology")),
        scope=_lower_list(meta.get("component"), meta.get("applies_to")),
        paths=[str(x).replace("\\", "/").strip("/") for x in
               as_list(meta.get("source_paths")) + as_list(meta.get("related_implementations"))],
        # `verified` is the older field used by external references; `last_verified` takes precedence.
        last_verified=_date_str(meta.get("last_verified")) or _date_str(meta.get("verified")),
        review_after=_date_str(meta.get("review_after")),
    )
    overdue = p.review_after is not None and p.review_after < today.isoformat()
    if lifecycle == "superseded":
        final, _chain, problem = resolve_replacement(catalog, doc.id)
        p.replacement = final
        if problem:
            p.warnings.append(f"superseded; replacement unresolved ({problem})")
        else:
            p.warnings.append(f"superseded by {final}" if final else "superseded (no replacement recorded)")
        p.freshness = 0.0
    elif lifecycle == "archived":
        p.warnings.append(f"archived (status '{meta.get('status')}'): historical reference only")
        p.freshness = 0.0
    elif lifecycle == "needs-review":
        p.warnings.append(f"needs review (status '{meta.get('status')}'): verify before relying on it")
        p.freshness = 0.2
    elif overdue:
        p.warnings.append(f"review overdue since {p.review_after}: may be stale")
        p.freshness = 0.4
    elif p.last_verified:
        p.freshness = 1.0
    else:
        p.freshness = 0.5   # verification unknown: neither trusted nor penalised
    if overdue and lifecycle == "needs-review":
        p.warnings.append(f"review overdue since {p.review_after}")
    return p


def resolve_replacement(catalog: Catalog, doc_id: str, *, max_hops: int = 20) -> tuple[str | None, list[str], str | None]:
    """Follow `superseded_by` to the final replacement. Returns (final id, chain, problem)."""
    chain = [doc_id]
    cur = catalog.by_id.get(doc_id)
    while cur is not None and len(chain) <= max_hops:
        nxt = as_list(cur.meta.get("superseded_by"))
        if not nxt:
            return (chain[-1] if len(chain) > 1 else None), chain, None
        target = str(nxt[0])
        if target in chain:
            return None, chain + [target], f"cycle {' -> '.join(chain + [target])}"
        chain.append(target)
        cur = catalog.by_id.get(target)
        if cur is None:
            return None, chain, f"missing target {target}"
    return None, chain, "chain too long"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def neighbours(catalog: Catalog, doc_id: str) -> list[tuple[str, str]]:
    """Undirected relation edges: (other id, label). Outgoing `field`, incoming `<-field`."""
    out: list[tuple[str, str]] = []
    d = catalog.by_id.get(doc_id)
    if d is not None:
        for fld, target in d.id_references():
            if target in catalog.by_id:
                out.append((target, fld))
    for src, fld in catalog.backrefs.get(doc_id, []):
        if src in catalog.by_id:
            out.append((src, f"<-{fld}"))
    seen: set[str] = set()
    uniq = []
    for other, label in sorted(out):
        if other not in seen and other != doc_id:
            seen.add(other)
            uniq.append((other, label))
    return uniq


def distances(catalog: Catalog, anchors: list[str], depth: int) -> dict[str, tuple[int, str, str]]:
    """Breadth-first distances from anchors: id -> (distance, via id, label). Cycle-safe, bounded."""
    depth = max(0, min(depth, MAX_DEPTH))
    found: dict[str, tuple[int, str, str]] = {}
    queue: deque[tuple[str, int]] = deque((a, 0) for a in anchors if a in catalog.by_id)
    visited = {a for a in anchors}
    while queue:
        cur, dist = queue.popleft()
        if dist >= depth:
            continue
        for other, label in neighbours(catalog, cur):
            if other in visited:
                continue
            visited.add(other)
            found[other] = (dist + 1, cur, label)
            queue.append((other, dist + 1))
    return found


# ---------------------------------------------------------------------------
# Query and scoring
# ---------------------------------------------------------------------------

@dataclass
class Query:
    text: str = ""
    types: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)          # hard filter: tags ∪ topics ∪ technology
    applies_to: list[str] = field(default_factory=list)      # hard filter: component ∪ applies_to
    statuses: list[str] = field(default_factory=list)        # hard filter: raw status or lifecycle class
    importance_min: int | None = None
    scope_paths: list[str] = field(default_factory=list)     # soft signal
    scope_names: list[str] = field(default_factory=list)     # soft signal
    anchors: list[str] = field(default_factory=list)         # soft signal: relation to these ids
    depth: int = 1
    include_historical: bool = False
    include_history_records: bool = False
    limit: int = 10
    legacy_filters: object = None                            # harness.search.Filters for `docs search`

    def terms(self) -> list[str]:
        raw = [t.lower().strip(".,;:") for t in _TERM_RE.findall(self.text or "")]
        out: list[str] = []
        for t in raw:
            if t and t not in out and (t not in STOPWORDS or len(raw) == 1):
                out.append(t)
        return out


@dataclass
class Result:
    profile: Profile
    score: float
    components: dict[str, float]
    reasons: list[str]
    snippet: str = ""
    relation: str | None = None
    replacement_for: list[str] = field(default_factory=list)
    excluded: str | None = None

    @property
    def doc(self) -> Document:
        return self.profile.doc

    def to_dict(self) -> dict:
        p = self.profile
        d = p.doc
        out = {
            "id": d.id, "title": d.title, "type": d.type, "path": d.relpath,
            "summary": _safe_line(str(d.meta.get("summary") or "")) or None,
            "status": d.status, "lifecycle": p.lifecycle,
            "importance": p.importance if p.importance_set else None,
            "last_verified": p.last_verified, "review_after": p.review_after,
            "score": round(self.score, 2),
            "components": {k: round(v, 2) for k, v in self.components.items()},
            "reasons": self.reasons, "warnings": p.warnings,
            "snippet": self.snippet or None, "relation": self.relation,
        }
        if p.replacement:
            out["replacement"] = p.replacement
        if self.replacement_for:
            out["replacement_for"] = self.replacement_for
        if self.excluded:
            out["excluded"] = self.excluded
        return out


def weights(config: Config) -> dict[str, float]:
    w = dict(DEFAULT_WEIGHTS)
    override = config.get("context.weights") or {}
    if not isinstance(override, dict):
        raise ContextError("harness.yaml context.weights must be a mapping")
    for k, v in override.items():
        if k not in DEFAULT_WEIGHTS:
            raise ContextError(f"unknown context weight {k!r}; known: {', '.join(DEFAULT_WEIGHTS)}")
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            raise ContextError(f"context weight {k!r} must be a non-negative number")
        w[k] = float(v)
    return w


def budgets(config: Config) -> dict[str, dict[str, int]]:
    b = {k: dict(v) for k, v in DEFAULT_BUDGETS.items()}
    for level, vals in (config.get("context.budgets") or {}).items():
        if level in b and isinstance(vals, dict):
            for k in ("documents", "depth"):
                if isinstance(vals.get(k), int) and vals[k] >= 0:
                    b[level][k] = min(vals[k], MAX_DEPTH) if k == "depth" else vals[k]
    return b


def _searchable(p: Profile) -> str:
    d = p.doc
    return " ".join([d.title, str(d.meta.get("summary") or ""), " ".join(p.topics), " ".join(p.scope),
                     " ".join(d.headings()), d.body]).lower()


def _query_component(p: Profile, terms: list[str], idf: dict[str, float]) -> tuple[float, list[str]]:
    """Per term, the strongest field wins; terms are weighted by rarity (IDF) so 'api' counts less than 'refund'."""
    if not terms:
        return 0.0, []
    d = p.doc
    title, summary = d.title.lower(), str(d.meta.get("summary") or "").lower()
    headings = [h.lower() for h in d.headings()]
    body = d.body.lower()
    total = weight_sum = 0.0
    reasons: list[str] = []
    for term in terms:
        st = stem(term)
        best, why = 0.0, ""
        candidates = [
            ("id", d.id and d.id.lower() == term),
            ("title", st in title),
            ("topic", any(st in t for t in p.topics)),
            ("summary", st in summary),
            ("scope", any(st in s for s in p.scope)),
            ("heading", any(st in h for h in headings)),
            ("path", term in d.relpath.lower() or any(term in x.lower() for x in p.paths)),
        ]
        for name, hit in candidates:
            if hit and FIELD_WEIGHTS[name] > best:
                best, why = FIELD_WEIGHTS[name], name
        count = body.count(st)
        if count and best < FIELD_WEIGHTS["body"]:
            best, why = FIELD_WEIGHTS["body"] * min(count, 3) / 3, "body"
        if best:
            reasons.append(f"{why} '{term}'")
        w = idf.get(term, 1.0)
        total += w * best
        weight_sum += w
    return (total / weight_sum if weight_sum else 0.0), reasons


def _path_overlap(a: str, b: str) -> float:
    """1.0 when one path contains the other; 0.4 when they share a parent of at least two segments."""
    sa = [x for x in a.replace("\\", "/").lower().split("/") if x]
    sb = [x for x in b.replace("\\", "/").lower().split("/") if x]
    if not sa or not sb:
        return 0.0
    common = 0
    for x, y in zip(sa, sb):
        if x != y:
            break
        common += 1
    if common == min(len(sa), len(sb)):
        return 1.0
    return 0.4 if common >= 2 else 0.0


def _scope_component(p: Profile, q: Query) -> tuple[float, list[str]]:
    best, reasons = 0.0, []
    for name in q.scope_names:
        if name.lower() in p.scope:
            best = max(best, SCOPE_NAME_WEIGHT)   # a component name is coarser than a source path
            reasons.append(f"applies to '{name}'")
    for want in q.scope_paths:
        for have in p.paths:
            ov = _path_overlap(want, have)
            if ov > best:
                best = ov
            if ov == 1.0:
                reasons.append(f"source path '{have}'")
                break
    return best, reasons[:3]


def _snippet(doc: Document, terms: list[str]) -> str:
    from harness.validation import scan_text_for_secrets

    best, best_hits = "", 0
    for line in doc.body.splitlines():
        low = line.lower()
        if not terms or line.lstrip().startswith(("#", "|", "<!--", "---")):
            continue
        hits = sum(1 for t in terms if t in low)
        if hits > best_hits and not scan_text_for_secrets(line):
            text = re.sub(r"\s+", " ", re.sub(r"[`*_>]", "", line)).strip()
            if text:
                best, best_hits = text, hits
    return best[:160] + ("…" if len(best) > 160 else "")


def _safe_line(text: str) -> str:
    from harness.validation import scan_text_for_secrets

    return "[redacted: looks like a secret]" if text and scan_text_for_secrets(text) else text


# ---------------------------------------------------------------------------
# Candidate filtering (security first)
# ---------------------------------------------------------------------------

def _excluded_paths(config: Config, catalog: Catalog) -> set[str]:
    """Documents that must never be retrieved: local directory, Git-ignored files."""
    local = (config.get("paths.local") or ".local").strip("/") + "/"
    out = {d.relpath for d in catalog.documents if d.relpath.startswith(local)}
    if gitutil.is_repo(config.root):
        ignored = gitutil.check_ignored(config.root, [d.relpath for d in catalog.documents])
        out |= {p for p, ign in ignored.items() if ign}
    return out


def _passes_filters(p: Profile, q: Query) -> bool:
    d = p.doc
    if q.types and d.type not in q.types:
        return False
    if q.statuses and d.status not in q.statuses and p.lifecycle not in q.statuses:
        return False
    if q.topics and not {t.lower() for t in q.topics} & set(p.topics):
        return False
    if q.applies_to and not {t.lower() for t in q.applies_to} & set(p.scope):
        return False
    if q.importance_min is not None and (not p.importance_set or p.importance < q.importance_min):
        return False
    if q.legacy_filters is not None:
        from harness.search import _matches_filters

        if not _matches_filters(d, q.legacy_filters):
            return False
    return True


def validate_query(q: Query) -> None:
    if q.importance_min is not None:
        lo, hi = schema.IMPORTANCE_RANGE
        if not lo <= q.importance_min <= hi:
            raise ContextError(f"--importance-min must be between {lo} and {hi}")
    if q.depth < 0 or q.depth > MAX_DEPTH:
        raise ContextError(f"--depth must be between 0 and {MAX_DEPTH}")
    if q.limit < 1 or q.limit > 200:
        raise ContextError("--limit must be between 1 and 200")
    known_status = set().union(*(dt.statuses for dt in schema.DOC_TYPES.values())) | set(schema.LIFECYCLE_CLASSES)
    for s in q.statuses:
        if s not in known_status:
            raise ContextError(f"unknown status {s!r}")
    for t in q.types:
        if t not in schema.DOC_TYPES:
            raise ContextError(f"unknown document type {t!r}")


# ---------------------------------------------------------------------------
# Public operations
# ---------------------------------------------------------------------------

@dataclass
class Engine:
    config: Config
    catalog: Catalog
    today: date
    weights: dict[str, float]
    excluded: set[str]

    @classmethod
    def load(cls, config: Config, *, today: date | None = None, catalog: Catalog | None = None) -> "Engine":
        cat = catalog or build_catalog(config)
        return cls(config=config, catalog=cat, today=today or date.today(), weights=weights(config),
                   excluded=_excluded_paths(config, cat))

    # -- helpers -------------------------------------------------------------
    def retrievable(self, d: Document) -> bool:
        return bool(d.id and d.type and d.has_frontmatter and not d.error and d.type != "index"
                    and d.relpath not in self.excluded)

    def doc(self, doc_id: str) -> Document:
        d = self.catalog.by_id.get(doc_id)
        if d is None or not self.retrievable(d):
            raise ContextError(f"no retrievable document with id {doc_id!r}", usage=False)
        return d

    def idf(self, terms: list[str]) -> dict[str, float]:
        import math

        docs = [profile(d, self.catalog, self.today) for d in self.catalog.typed() if self.retrievable(d)]
        texts = [_searchable(p) for p in docs]
        n = len(texts) or 1
        return {t: math.log(1 + n / (1 + sum(1 for x in texts if stem(t) in x))) for t in terms}

    def score(self, p: Profile, q: Query, terms: list[str], rel: dict[str, tuple[int, str, str]],
              idf: dict[str, float] | None = None) -> Result:
        w = self.weights
        comps: dict[str, float] = {}
        reasons: list[str] = []
        if terms:
            comps["query"], r = _query_component(p, terms, idf or {})
            reasons += r
        if q.scope_names or q.scope_paths:
            comps["scope"], r = _scope_component(p, q)
            reasons += r
        relation = None
        if q.anchors:
            hit = rel.get(p.doc.id)
            comps["relation"] = 0.0
            if hit:
                dist, via, label = hit
                comps["relation"] = 1.0 if dist == 1 else 0.5
                relation = f"{via} {label}" if dist == 1 else f"{via} {label} (depth {dist})"
                reasons.append(f"related to {relation}")
        comps["importance"] = (p.importance - 1) / 4
        if p.importance_set:
            reasons.append(f"importance {p.importance}")
        comps["freshness"] = p.freshness
        if p.last_verified and p.freshness == 1.0:
            reasons.append(f"verified {p.last_verified}")
        total_w = sum(w[k] for k in comps) or 1.0
        score = sum(w[k] * v for k, v in comps.items()) / total_w
        return Result(profile=p, score=score, components=comps, reasons=reasons, snippet=_snippet(p.doc, terms),
                      relation=relation)

    def _relevant(self, res: Result, q: Query, terms: list[str]) -> bool:
        """With query terms, scope only ranks; a document must match the words, a relation, or contain the path."""
        c = res.components
        if terms:
            return c.get("query", 0.0) > 0 or c.get("relation", 0.0) > 0 or c.get("scope", 0.0) >= 1.0
        if q.anchors or q.scope_names or q.scope_paths:
            return any(c.get(k, 0.0) > 0 for k in ("scope", "relation"))
        return True   # pure property listing

    # -- search ----------------------------------------------------------------
    def search(self, q: Query) -> list[Result]:
        validate_query(q)
        terms = q.terms()
        lifecycles = set(schema.LIFECYCLE_CLASSES) if q.include_historical else set(DEFAULT_LIFECYCLES)
        rel = distances(self.catalog, q.anchors, q.depth) if q.anchors else {}
        idf = self.idf(terms) if terms else {}
        exact_ids = {d.id for d in self.catalog.typed() if d.id and d.id.lower() in terms}
        results: dict[str, Result] = {}
        superseded_hits: list[Result] = []
        for d in sorted(self.catalog.typed(), key=lambda x: x.id):
            if not self.retrievable(d) or d.id in q.anchors:
                continue
            if d.type == "commit-record" and not (q.include_history_records or "commit-record" in q.types):
                continue
            p = profile(d, self.catalog, self.today)
            if not _passes_filters(p, q):
                continue
            res = self.score(p, q, terms, rel, idf)
            if not self._relevant(res, q, terms):
                continue
            if p.lifecycle not in lifecycles and d.id not in exact_ids:
                if p.lifecycle == "superseded" and p.replacement:
                    superseded_hits.append(res)
                continue
            results[d.id] = res
        # Suggest the active replacement of a matching superseded document, ranked at least as relevant
        # (90 %) as the outdated document it replaces.
        for old in superseded_hits:
            new_id = old.profile.replacement
            if new_id in results:
                res = results[new_id]
            else:
                nd = self.catalog.by_id.get(new_id)
                if nd is None or not self.retrievable(nd):
                    continue
                np_ = profile(nd, self.catalog, self.today)
                if np_.lifecycle not in lifecycles or not _passes_filters(np_, q):
                    continue
                res = self.score(np_, q, terms, rel, idf)
                results[new_id] = res
            inherited = 0.9 * old.components.get("query", 0.0)
            if inherited > res.components.get("query", 0.0):
                res.components["query"] = inherited
                total_w = sum(self.weights[k] for k in res.components) or 1.0
                res.score = sum(self.weights[k] * v for k, v in res.components.items()) / total_w
            res.replacement_for.append(old.doc.id)
            res.reasons.append(f"replaces matching superseded {old.doc.id}")
        ordered = sorted(results.values(),
                         key=lambda r: (-round(r.score, 6), -r.profile.importance, r.doc.id))
        return ordered[: q.limit]

    def explain(self, doc_id: str, q: Query) -> Result:
        validate_query(q)
        d = self.doc(doc_id)
        p = profile(d, self.catalog, self.today)
        terms = q.terms()
        rel = distances(self.catalog, q.anchors, q.depth) if q.anchors else {}
        res = self.score(p, q, terms, rel, self.idf(terms) if terms else {})
        if not _passes_filters(p, q):
            res.excluded = "does not pass the property filters"
        elif not self._relevant(res, q, terms):
            res.excluded = "no query, scope or relation match"
        elif p.lifecycle not in (set(schema.LIFECYCLE_CLASSES) if q.include_historical else set(DEFAULT_LIFECYCLES)):
            res.excluded = f"lifecycle '{p.lifecycle}' is excluded by default (use --include-historical)"
        return res

    # -- documents -------------------------------------------------------------
    def get(self, doc_id: str) -> tuple[Profile, str]:
        from harness.validation import scan_text_for_secrets

        d = self.doc(doc_id)
        if not d.path.resolve().is_relative_to(self.config.root.resolve()):
            raise ContextError(f"{doc_id}: path outside the repository", usage=False)
        text = d.path.read_text(encoding="utf-8")
        hits = scan_text_for_secrets(text)
        if hits:
            lines = ", ".join(str(n) for _, n in hits[:5])
            raise ContextError(f"{doc_id}: refusing to print; secret-like content at line(s) {lines}", usage=False)
        return profile(d, self.catalog, self.today), text

    def related(self, doc_id: str, depth: int = 1, *, include_historical: bool = False,
                include_history_records: bool = False) -> list[dict]:
        if depth < 0 or depth > MAX_DEPTH:
            raise ContextError(f"--depth must be between 0 and {MAX_DEPTH}")
        self.doc(doc_id)
        out: list[dict] = []
        seen: set[str] = set()
        for other, (dist, via, label) in sorted(distances(self.catalog, [doc_id], depth).items(),
                                                key=lambda kv: (kv[1][0], kv[0])):
            d = self.catalog.by_id[other]
            if not self.retrievable(d) or (d.type == "commit-record" and not include_history_records):
                continue
            p = profile(d, self.catalog, self.today)
            note = None
            if p.lifecycle in ("superseded", "archived") and not include_historical:
                if p.replacement and p.replacement not in seen and p.replacement != doc_id:
                    rd = self.catalog.by_id.get(p.replacement)
                    if rd is not None and self.retrievable(rd):
                        note = f"replaces {other} ({label} via {via})"
                        d, p = rd, profile(rd, self.catalog, self.today)
                    else:
                        continue
                else:
                    continue
            if d.id in seen:
                continue
            seen.add(d.id)
            out.append({"id": d.id, "title": d.title, "type": d.type, "path": d.relpath, "distance": dist,
                        "via": via, "relation": label, "lifecycle": p.lifecycle, "warnings": p.warnings,
                        "summary": _safe_line(str(d.meta.get("summary") or "")) or None,
                        **({"note": note} if note else {})})
        return out

    def for_task(self, task_id: str, level: str = "standard", *, limit: int | None = None) -> dict:
        b = budgets(self.config)
        if level not in b:
            raise ContextError(f"--depth must be one of {', '.join(b)}")
        task = self.doc(task_id)
        meta = task.meta
        words = " ".join([task.title, str(meta.get("summary") or ""), " ".join(as_list(meta.get("tags")))])
        q = Query(text=words, anchors=[task_id], depth=b[level]["depth"],
                  scope_paths=[str(x) for x in as_list(meta.get("related_implementations")) +
                               as_list(meta.get("source_paths"))],
                  scope_names=[str(x) for x in as_list(meta.get("component")) + as_list(meta.get("applies_to"))],
                  limit=limit or max(2 * b[level]["documents"], 3))
        # Other tasks are noise for context unless directly related.
        results = [r for r in self.search(q) if r.doc.type != "task" or (r.components.get("relation", 0) == 1.0)]
        n = b[level]["documents"]
        remaining = ""
        m = re.search(r"Remaining:\s*(.+)", task.body)
        if m:
            remaining = m.group(1).strip()[:200]
        return {
            "task": {"id": task.id, "title": task.title, "status": task.status, "milestone": meta.get("milestone"),
                     "path": task.relpath, "remaining": remaining or None},
            "level": level, "budget": b[level],
            "read": [r.to_dict() for r in results[:n]],
            "more_if_needed": [r.to_dict() for r in results[n:]],
        }

    # -- maintenance -----------------------------------------------------------
    def review(self, *, check_sources: bool = True) -> list[dict]:
        """Review candidates with reasons. Signals only; nothing is rewritten."""
        out: list[dict] = []
        superseded = {d.id for d in self.catalog.typed()
                      if schema.lifecycle_of(d.meta.get("status"), d.meta.get("superseded_by")) == "superseded"}
        for d in sorted(self.catalog.typed(), key=lambda x: x.id):
            if not self.retrievable(d) or d.type in ("commit-record", "task", "milestone"):
                continue
            p = profile(d, self.catalog, self.today)
            if p.lifecycle in ("superseded", "archived"):
                continue
            reasons: list[str] = []
            if p.lifecycle == "needs-review":
                reasons.append(f"status '{d.status}'")
            if p.review_after and p.review_after < self.today.isoformat():
                reasons.append(f"review_after {p.review_after} has passed")
            stale_refs = sorted({t for _, t in d.id_references() if t in superseded})
            for t in stale_refs:
                final, _c, _p = resolve_replacement(self.catalog, t)
                reasons.append(f"references superseded {t}" + (f" (now {final})" if final else ""))
            if check_sources and p.last_verified and p.paths and gitutil.is_repo(self.config.root):
                existing = [x for x in p.paths if (self.config.root / x).exists()]
                if existing:
                    last = gitutil.run(["log", "-1", "--format=%cs", "--", *existing], self.config.root, check=False)
                    if last and last > p.last_verified:
                        reasons.append(f"source changed {last}, after last verification {p.last_verified}")
            if p.importance_set and p.importance >= 4 and not p.last_verified:
                reasons.append(f"importance {p.importance} but never verified")
            if reasons:
                out.append({"id": d.id, "title": d.title, "path": d.relpath, "reasons": reasons})
        return out


def verify(config: Config, doc_id: str, *, today: date | None = None, review_after_days: int | None = None,
           review_after: str | None = None, mark_active: bool = False) -> list[str]:
    """Record an intentional review: set last_verified (and optionally review_after / status) in place.

    Only the touched frontmatter lines change; the body and all other properties are preserved byte for byte.
    """
    today = today or date.today()
    cat = build_catalog(config)
    eng = Engine.load(config, today=today, catalog=cat)
    d = eng.doc(doc_id)
    updates: dict[str, str] = {"last_verified": today.isoformat()}
    if review_after_days is not None:
        if review_after_days < 1:
            raise ContextError("--review-after-days must be positive")
        updates["review_after"] = (today + timedelta(days=review_after_days)).isoformat()
    elif review_after is not None:
        if not schema.DATE_RE.match(review_after):
            raise ContextError("--review-after must be YYYY-MM-DD")
        updates["review_after"] = review_after
    if mark_active and str(d.status) in ("needs-review", "needs-revalidation"):
        dt = schema.doc_type(d.type)
        updates["status"] = "active" if dt and "active" in dt.statuses else "current"
    text = d.path.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)
    if not lines or lines[0].lstrip("﻿") != "---":
        raise ContextError(f"{doc_id}: no frontmatter", usage=False)
    end = next((i for i in range(1, len(lines)) if lines[i] == "---"), None)
    if end is None:
        raise ContextError(f"{doc_id}: unterminated frontmatter", usage=False)
    changes: list[str] = []
    for key, value in updates.items():
        rx = re.compile(rf"^{re.escape(key)}:(\s.*|)$")
        idx = next((i for i in range(1, end) if rx.match(lines[i])), None)
        new_line = f"{key}: {value}"
        if idx is None:
            lines.insert(end, new_line)
            end += 1
            changes.append(f"added {new_line}")
        elif lines[idx] != new_line:
            changes.append(f"{lines[idx].strip()} -> {new_line}")
            lines[idx] = new_line
    if changes:
        with d.path.open("w", encoding="utf-8", newline="") as fh:
            fh.write(newline.join(lines))
    return changes


def default_today() -> date:
    return date.today()


def task_level_names() -> tuple[str, ...]:
    return tuple(DEFAULT_BUDGETS)


__all__ = ["Engine", "Query", "Result", "Profile", "ContextError", "verify", "DEFAULT_WEIGHTS", "DEFAULT_BUDGETS",
           "MAX_DEPTH", "resolve_replacement", "distances", "Path"]
