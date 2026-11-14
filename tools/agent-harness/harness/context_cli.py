"""`harness context ...`: read-only, structured context retrieval for agents (plus explicit `verify`).

stdout carries results (JSON when `--format json`), stderr carries diagnostics and warnings.
Exit codes: 0 success (including an empty result), 1 not found / refused, 2 invalid arguments.
"""

from __future__ import annotations

import argparse
import json
import sys

from harness import context as ctx
from harness.core import schema

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2


def _out(text: str) -> None:
    sys.stdout.write(text + ("\n" if not text.endswith("\n") else ""))


def _err(text: str) -> None:
    sys.stderr.write(text + "\n")


def _query_from(args) -> ctx.Query:
    return ctx.Query(
        text=args.query or "", types=args.type or [], topics=args.topic or [], applies_to=args.applies_to or [],
        statuses=args.status or [], importance_min=args.importance_min, scope_paths=args.path or [],
        anchors=([args.related_to] if getattr(args, "related_to", None) else []) + (
            [args.task] if getattr(args, "task", None) else []),
        depth=getattr(args, "graph_depth", 1), include_historical=args.include_historical,
        include_history_records=args.history, limit=args.limit,
    )


def _fmt_result(i: int, r: dict) -> list[str]:
    imp = f", imp {r['importance']}" if r.get("importance") else ""
    lines = [f"{i}. {r['id']} ({r['type']}, {r['status']}{imp}) {r['score']:.2f}  {r['path']}", f"   {r['title']}"]
    if r.get("summary"):
        lines.append(f"   {r['summary']}")
    elif r.get("snippet"):
        lines.append(f"   … {r['snippet']}")
    if r.get("reasons"):
        lines.append("   why: " + "; ".join(r["reasons"][:6]))
    for w in r.get("warnings") or []:
        lines.append(f"   ! {w}")
    if r.get("replacement_for"):
        lines.append("   replaces: " + ", ".join(r["replacement_for"]))
    return lines


def cmd_search(cfg, args) -> int:
    eng = ctx.Engine.load(cfg)
    results = [r.to_dict() for r in eng.search(_query_from(args))]
    if args.format == "json":
        _out(json.dumps(results, indent=2, ensure_ascii=False))
        return EXIT_OK
    if not results:
        _err("no matching documents (superseded/archived are excluded unless --include-historical)")
        return EXIT_OK
    lines: list[str] = []
    for i, r in enumerate(results, 1):
        lines += _fmt_result(i, r)
    _out("\n".join(lines))
    return EXIT_OK


def cmd_get(cfg, args) -> int:
    eng = ctx.Engine.load(cfg)
    prof, text = eng.get(args.id)
    d = prof.doc
    meta = {"id": d.id, "title": d.title, "type": d.type, "path": d.relpath, "status": d.status,
            "lifecycle": prof.lifecycle, "importance": prof.importance if prof.importance_set else None,
            "last_verified": prof.last_verified, "review_after": prof.review_after, "warnings": prof.warnings,
            "replacement": prof.replacement}
    if args.format == "json":
        if not args.meta:
            meta["content"] = text
        _out(json.dumps(meta, indent=2, ensure_ascii=False))
        return EXIT_OK
    for w in prof.warnings:
        _err(f"warning: {d.id}: {w}")
    if args.meta:
        _out("\n".join(f"{k}: {v}" for k, v in meta.items() if v not in (None, [], "")))
    else:
        _out(text)
    return EXIT_OK


def cmd_related(cfg, args) -> int:
    eng = ctx.Engine.load(cfg)
    rows = eng.related(args.id, args.depth, include_historical=args.include_historical,
                       include_history_records=args.history)
    if args.format == "json":
        _out(json.dumps(rows, indent=2, ensure_ascii=False))
        return EXIT_OK
    if not rows:
        _err(f"{args.id}: no related documents within depth {args.depth}")
        return EXIT_OK
    lines = []
    for r in rows:
        lines.append(f"[{r['distance']}] {r['id']} ({r['type']}, {r['lifecycle']}) via {r['via']} {r['relation']} — "
                     f"{r['title']}  {r['path']}")
        if r.get("note"):
            lines.append(f"    {r['note']}")
        for w in r.get("warnings") or []:
            lines.append(f"    ! {w}")
    _out("\n".join(lines))
    return EXIT_OK


def cmd_explain(cfg, args) -> int:
    eng = ctx.Engine.load(cfg)
    res = eng.explain(args.id, _query_from(args))
    data = res.to_dict()
    data["weights"] = eng.weights
    if args.format == "json":
        _out(json.dumps(data, indent=2, ensure_ascii=False))
        return EXIT_OK
    lines = [f"{data['id']} — {data['title']} ({data['type']}, {data['status']}, lifecycle {data['lifecycle']})",
             f"score {data['score']:.2f} = weighted mean of the active components:"]
    for k, v in data["components"].items():
        lines.append(f"  {k:<10} {v:.2f} × weight {eng.weights[k]:.2f}")
    lines.append("reasons: " + ("; ".join(data["reasons"]) or "none"))
    for w in data["warnings"]:
        lines.append(f"! {w}")
    if data.get("excluded"):
        lines.append(f"excluded from results: {data['excluded']}")
    _out("\n".join(lines))
    return EXIT_OK


def cmd_for_task(cfg, args) -> int:
    eng = ctx.Engine.load(cfg)
    data = eng.for_task(args.task_id, args.depth, limit=args.limit)
    if args.format == "json":
        _out(json.dumps(data, indent=2, ensure_ascii=False))
        return EXIT_OK
    t = data["task"]
    lines = [f"{t['id']} — {t['title']} ({t['status']}, milestone {t['milestone'] or '-'})"]
    if t.get("remaining"):
        lines.append(f"Remaining: {t['remaining']}")
    b = data["budget"]
    lines.append(f"Read first ({args.depth}: up to {b['documents']} document(s), relation depth {b['depth']}):")
    for i, r in enumerate(data["read"], 1):
        lines += _fmt_result(i, r)
    if not data["read"]:
        lines.append("  none: implement from the code; retrieve more only if blocked")
    if data["more_if_needed"]:
        lines.append("Only if needed:")
        for r in data["more_if_needed"]:
            lines.append(f"  - {r['id']} {r['score']:.2f} {r['path']} — {r['title']}")
    _out("\n".join(lines))
    return EXIT_OK


def cmd_review(cfg, args) -> int:
    eng = ctx.Engine.load(cfg)
    rows = eng.review(check_sources=not args.no_source_check)
    if args.format == "json":
        _out(json.dumps(rows, indent=2, ensure_ascii=False))
    elif not rows:
        _out("no review candidates")
    else:
        _out("\n".join(f"{r['id']}  {r['path']}\n   " + "; ".join(r["reasons"]) for r in rows))
    return EXIT_OK


def cmd_verify(cfg, args) -> int:
    changes = ctx.verify(cfg, args.id, review_after_days=args.review_after_days, review_after=args.review_after,
                         mark_active=args.mark_active)
    _out(f"{args.id}: " + ("; ".join(changes) if changes else "already up to date"))
    _err("note: verification records that you reviewed the content; it does not change the document text")
    return EXIT_OK


def add_parser(sub) -> None:
    cp = sub.add_parser("context", help="task-aware context retrieval: search, get, related, explain, for-task, "
                                        "review, verify")
    csub = cp.add_subparsers(dest="context_command", required=True)

    def common_filters(p, *, query=True):
        if query:
            p.add_argument("--query", "-q", default="", help="free-text query")
        p.add_argument("--type", action="append", choices=sorted(schema.DOC_TYPES))
        p.add_argument("--topic", action="append", help="tags/topics/technology contains (repeatable)")
        p.add_argument("--applies-to", action="append", dest="applies_to", help="component/applies_to contains")
        p.add_argument("--status", action="append", help="raw status or lifecycle (active, needs-review, ...)")
        p.add_argument("--importance-min", type=int, dest="importance_min")
        p.add_argument("--path", action="append", help="scope: source path the work touches (ranking signal)")
        p.add_argument("--task", help="rank documents related to this task higher")
        p.add_argument("--related-to", dest="related_to", help="rank documents related to this id higher")
        p.add_argument("--graph-depth", type=int, default=1, dest="graph_depth", help="relation depth 0-2 (default 1)")
        p.add_argument("--include-historical", action="store_true", help="include superseded and archived documents")
        p.add_argument("--history", action="store_true", help="include commit records")
        p.add_argument("--limit", type=int, default=10)
        p.add_argument("--format", choices=["text", "json"], default="text")

    p = csub.add_parser("search", help="ranked metadata search (snippets only, never full documents)")
    common_filters(p)
    p.set_defaults(context_func=cmd_search)

    p = csub.add_parser("get", help="print one document by id, with lifecycle warnings")
    p.add_argument("id")
    p.add_argument("--meta", action="store_true", help="metadata only")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.set_defaults(context_func=cmd_get)

    p = csub.add_parser("related", help="documents linked to an id (breadth-first, depth 0-2)")
    p.add_argument("id")
    p.add_argument("--depth", type=int, default=1)
    p.add_argument("--include-historical", action="store_true")
    p.add_argument("--history", action="store_true", help="include commit records")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.set_defaults(context_func=cmd_related)

    p = csub.add_parser("explain", help="show how a document scores for a query")
    p.add_argument("id")
    common_filters(p)
    p.set_defaults(context_func=cmd_explain)

    p = csub.add_parser("for-task", help="the few documents a task needs, sized by task complexity")
    p.add_argument("task_id")
    p.add_argument("--depth", choices=list(ctx.DEFAULT_BUDGETS), default="standard",
                   help="simple | standard | complex (document budget and relation depth)")
    p.add_argument("--limit", type=int)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.set_defaults(context_func=cmd_for_task)

    p = csub.add_parser("review", help="documents that may be stale (signals only, nothing rewritten)")
    p.add_argument("--no-source-check", action="store_true", help="skip the git check of source_paths")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.set_defaults(context_func=cmd_review)

    p = csub.add_parser("verify", help="record that you reviewed a document (sets last_verified)")
    p.add_argument("id")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--review-after-days", type=int, dest="review_after_days")
    g.add_argument("--review-after", dest="review_after", help="YYYY-MM-DD")
    p.add_argument("--mark-active", action="store_true", help="also clear a needs-review status")
    p.set_defaults(context_func=cmd_verify)


def run(cfg, args) -> int:
    try:
        return int(args.context_func(cfg, args))
    except ctx.ContextError as exc:
        _err(f"error: {exc}")
        return EXIT_USAGE if exc.usage else EXIT_FAIL
