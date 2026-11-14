"""Command-line interface for the agent harness.

Exit codes: 0 success, 1 validation errors / conflicts, 2 usage or configuration error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness import __version__
from harness.core import config as config_mod
from harness.core import schema
from harness.core.gitutil import GitError

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2


def _root(args) -> Path:
    if getattr(args, "root", None):
        return Path(args.root).resolve()
    found = config_mod.find_root(Path.cwd())
    return found or Path.cwd().resolve()


def _load(args):
    root = _root(args)
    cfg = config_mod.load(root)
    if not cfg.exists:
        print(f"error: {config_mod.CONFIG_FILENAME} not found in {root}; run `harness init`", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    return cfg


def _print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:  # pragma: no cover - console encoding fallback (Windows cp1252)
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(args) -> int:
    from harness import initcmd

    try:
        report = initcmd.run(Path(args.path).resolve() if args.path else _root(args), profile=args.profile,
                             platforms=args.platform, name=args.name, description=args.description,
                             git_init=args.git, dry_run=args.dry_run, force=args.force)
    except (KeyError, config_mod.ConfigError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    _print(report.summary())
    return EXIT_FAIL if report.conflicts and not args.force else EXIT_OK


def cmd_update(args) -> int:
    from harness import updatecmd

    try:
        report = updatecmd.run(_root(args), apply_changes=args.apply, force=args.force)
    except config_mod.ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    _print(report.summary(show_diff=args.diff))
    return EXIT_FAIL if report.conflicts else EXIT_OK


def cmd_check(args) -> int:
    from harness import validation

    cfg = _load(args)
    issues = validation.run_all(cfg, scan_tracked=not args.no_content_scan)
    if args.json:
        _print(json.dumps([i.__dict__ for i in issues], indent=2))
    else:
        for i in issues:
            if i.level == validation.WARNING and args.quiet:
                continue
            _print(str(i))
        errors = sum(1 for i in issues if i.level == validation.ERROR)
        warnings = sum(1 for i in issues if i.level == validation.WARNING)
        _print(f"harness check: {errors} error(s), {warnings} warning(s)")
    return EXIT_FAIL if validation.has_errors(issues) else EXIT_OK


def cmd_status(args) -> int:
    from harness import status

    cfg = _load(args)
    data = status.collect(cfg)
    if args.json:
        _print(status.render_json(data))
    else:
        text = status.render(data, brief=args.brief)
        if args.hook:
            # SessionStart hook output: plain text is injected as context by Claude Code.
            text = "Project state from `harness status` (durable repository state, regenerated each session):\n" + text
        _print(text)
    return EXIT_OK


def cmd_new(args) -> int:
    from harness import newdoc

    cfg = _load(args)
    variables = {}
    for kv in args.set or []:
        if "=" not in kv:
            print(f"error: --set expects key=value, got {kv!r}", file=sys.stderr)
            return EXIT_USAGE
        k, v = kv.split("=", 1)
        variables[k] = v
    if args.milestone:
        variables["milestone"] = args.milestone
    if args.priority:
        variables["priority"] = args.priority
    if args.summary:
        variables["summary"] = args.summary
    try:
        created = newdoc.create(cfg, args.type, args.title, doc_id=args.id, directory=args.dir, variables=variables)
    except newdoc.NewDocError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    _print(f"created {created.doc_id}: {created.relpath}")
    if not args.no_index:
        from harness.index import write_indexes
        write_indexes(cfg)
    return EXIT_OK


def cmd_docs_index(args) -> int:
    from harness.index import write_indexes

    cfg = _load(args)
    changed = write_indexes(cfg)
    _print("regenerated: " + (", ".join(changed) if changed else "nothing changed"))
    return EXIT_OK


def cmd_docs_search(args) -> int:
    from harness import search

    cfg = _load(args)
    filters = search.Filters(types=args.type or [], tags=args.tag or [], statuses=args.status or [],
                             component=args.component, technology=args.tech, task=args.task,
                             milestone=args.milestone, implementation=args.impl, doc_id=args.id, path=args.path)
    hits = search.search(cfg, " ".join(args.terms), filters, limit=args.limit, include_history=args.history)
    if args.json:
        _print(json.dumps([{"id": h.doc.id, "type": h.doc.type, "status": h.doc.status, "path": h.doc.relpath,
                            "title": h.doc.title, "score": h.score, "matched": h.reasons} for h in hits], indent=2))
    else:
        if not hits:
            _print("no matching documents")
        for h in hits:
            _print(search.format_hit(h) + (f"  ({', '.join(h.reasons)})" if args.verbose else ""))
    return EXIT_OK


def cmd_docs_show(args) -> int:
    import yaml

    from harness.core.documents import build_catalog

    cfg = _load(args)
    cat = build_catalog(cfg)
    doc = cat.get(args.id)
    if doc is None:
        print(f"error: no document with id {args.id!r}", file=sys.stderr)
        return EXIT_FAIL
    if args.body:
        _print(doc.path.read_text(encoding="utf-8"))
        return EXIT_OK
    _print(f"path: {doc.relpath}")
    _print(yaml.safe_dump(doc.meta, sort_keys=False, allow_unicode=True).rstrip())
    _print("sections: " + ", ".join(doc.headings()))
    refs = cat.backrefs.get(doc.id, [])
    if refs:
        _print("referenced by: " + ", ".join(f"{src} ({fld})" for src, fld in refs))
    return EXIT_OK


def cmd_docs_types(args) -> int:
    rows = []
    for name in sorted(schema.DOC_TYPES):
        dt = schema.DOC_TYPES[name]
        rows.append(f"{name:<24} id: {dt.id_prefix + '...':<10} dir: {dt.default_dir:<24} statuses: {', '.join(dt.statuses)}")
        if args.verbose:
            rows.append(f"{'':<24} {dt.purpose}")
            rows.append(f"{'':<24} create when: {dt.create_when}")
    _print("\n".join(rows))
    return EXIT_OK


def cmd_docs_export_wiki(args) -> int:
    from harness import wiki

    cfg = _load(args)
    out_dir = Path(args.out).resolve() if args.out else cfg.root / (cfg.get("paths.local") or ".local") / "wiki-export"
    try:
        result = wiki.export(cfg, out_dir, dry_run=args.dry_run, clean=args.clean)
    except wiki.WikiExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAIL
    _print(f"wiki export → {out_dir}" + (" (dry run)" if args.dry_run else ""))
    for p in result.pages:
        _print(f"  {p.name}.md  ← {p.source}")
    if args.verbose:
        for src, reason in result.skipped:
            _print(f"  skipped {src}: {reason}")
    if not args.dry_run:
        _print(f"written: {len(result.written)}, unchanged: {len(result.pages) - len(result.written)}, "
               f"removed: {len(result.removed)}")
    return EXIT_OK


def cmd_docs_publish_wiki(args) -> int:
    import os

    from harness import wiki

    cfg = _load(args)
    token = None
    if args.token_file:
        token = Path(args.token_file).read_text(encoding="utf-8").strip() or None
    else:
        token = os.environ.get(args.token_env or cfg.get("wiki.token_env") or "HARNESS_WIKI_TOKEN") or None
    try:
        result = wiki.publish(cfg, remote=args.remote, token=token, dry_run=args.dry_run,
                              bootstrap=not args.no_bootstrap, message=args.message)
    except (wiki.WikiExportError, wiki.WikiPublishError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAIL
    _print(result.message)
    if result.bootstrapped:
        _print("wiki enabled and initialised through the API")
    return EXIT_OK


def cmd_history_sync(args) -> int:
    from harness import history

    cfg = _load(args)
    try:
        result = history.sync(cfg, branch=args.branch, limit=args.limit, refresh=args.refresh, dry_run=args.dry_run,
                              scan_branches=not args.no_branch_scan)
    except GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAIL
    prefix = "would " if args.dry_run else ""
    _print(f"history sync — branch context: {result.branch}")
    for p in result.created:
        _print(f"  + {prefix}create {p}")
    for p in result.refreshed:
        _print(f"  ~ {prefix}refresh {p}")
    _print(f"created: {len(result.created)}, refreshed: {len(result.refreshed)}, existing kept: "
           f"{result.skipped_existing}, history-only commits skipped: {len(result.skipped_history_only)}")
    if result.index_path and not args.dry_run:
        _print(f"index: {result.index_path}")
    return EXIT_OK


def cmd_hooks(args) -> int:
    from harness import hooks

    cfg = _load(args)
    try:
        if args.hooks_command == "install":
            report = hooks.install(cfg, force=args.force)
            _print(report.summary())
            return EXIT_FAIL if report.conflicts else EXIT_OK
        if args.hooks_command == "uninstall":
            _print(hooks.uninstall(cfg).summary())
            return EXIT_OK
        for name, state in hooks.status(cfg).items():
            _print(f"{name}: {state}")
        return EXIT_OK
    except GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAIL


def cmd_context(args) -> int:
    from harness import context_cli

    return context_cli.run(_load(args), args)


def cmd_detect(args) -> int:
    from harness.detect import detect

    d = detect(_root(args))
    _print(json.dumps({"primary": d.primary, "detected": d.detected, "scores": d.scores, "languages": d.languages,
                       "agent_configs": d.agent_configs, "docs": d.docs, "verification": d.verification,
                       "truncated": d.truncated}, indent=2))
    return EXIT_OK


def cmd_version(args) -> int:
    _print(__version__)
    return EXIT_OK


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness", description="Documentation-first AI agent harness.")
    parser.add_argument("--root", help="project root (default: nearest directory with harness.yaml or .git)")
    parser.add_argument("--version", action="version", version=f"harness {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="initialize or re-initialize a project (safe to repeat)")
    p.add_argument("path", nargs="?", help="project directory (default: current)")
    p.add_argument("--profile", help="force a profile instead of detecting one")
    p.add_argument("--platform", action="append", choices=["claude", "codex"], help="agent platform(s) to configure")
    p.add_argument("--name", help="project name")
    p.add_argument("--description", help="one-line project description")
    p.add_argument("--git", action="store_true", help="run `git init` if the directory is not a repository")
    p.add_argument("--dry-run", action="store_true", help="show what would change without writing")
    p.add_argument("--force", action="store_true", help="replace conflicting files (backup kept in .local/)")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("update", help="preview or apply framework updates to managed files")
    p.add_argument("--apply", action="store_true", help="write changes (default is a dry run)")
    p.add_argument("--diff", action="store_true", help="show unified diffs")
    p.add_argument("--force", action="store_true", help="replace conflicting files (backup kept in .local/)")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("check", help="validate configuration, documents, indexes and sensitive-data rules")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quiet", action="store_true", help="hide warnings")
    p.add_argument("--no-content-scan", action="store_true", help="skip secret-pattern scanning of tracked files")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("status", help="project state for session start / resumption")
    p.add_argument("--brief", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--hook", action="store_true", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("new", help="create a document from a template with a valid id")
    p.add_argument("type", choices=sorted(t for t in schema.DOC_TYPES if t != "index"))
    p.add_argument("title")
    p.add_argument("--id", help="explicit id (default: next number or slug)")
    p.add_argument("--dir", help="target directory (default: type's directory)")
    p.add_argument("--milestone", help="milestone id (tasks)")
    p.add_argument("--priority", choices=schema.PRIORITIES)
    p.add_argument("--summary", help="one-line summary shown in the knowledge map, llms.txt and search results")
    p.add_argument("--set", action="append", metavar="KEY=VALUE", help="template variable")
    p.add_argument("--no-index", action="store_true", help="do not regenerate indexes")
    p.set_defaults(func=cmd_new)

    docs = sub.add_parser("docs", help="knowledge documents: index, search, show, types, export-wiki")
    dsub = docs.add_subparsers(dest="docs_command", required=True)
    p = dsub.add_parser("index", help="regenerate the knowledge map and catalog")
    p.set_defaults(func=cmd_docs_index)
    p = dsub.add_parser("search", help="ranked search over document metadata and text")
    p.add_argument("terms", nargs="*")
    p.add_argument("--type", action="append", choices=sorted(schema.DOC_TYPES))
    p.add_argument("--tag", action="append")
    p.add_argument("--status", action="append")
    p.add_argument("--component")
    p.add_argument("--tech", help="technology")
    p.add_argument("--task", help="related task id")
    p.add_argument("--milestone", help="related milestone id")
    p.add_argument("--impl", help="related implementation path substring")
    p.add_argument("--id")
    p.add_argument("--path", help="path substring")
    p.add_argument("--history", action="store_true", help="include commit records")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_docs_search)
    p = dsub.add_parser("show", help="print a document's path, metadata and sections")
    p.add_argument("id")
    p.add_argument("--body", action="store_true", help="print the full document")
    p.set_defaults(func=cmd_docs_show)
    p = dsub.add_parser("types", help="list document types, id prefixes, directories and statuses")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_docs_types)
    p = dsub.add_parser("export-wiki", help="export approved documents as Forgejo Wiki pages")
    p.add_argument("--out", help="output directory (default: .local/wiki-export)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--clean", action="store_true", help="remove stale pages from the output directory")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_docs_export_wiki)
    p = dsub.add_parser("publish-wiki", help="export and push pages to the repository wiki (bootstraps it via API)")
    p.add_argument("--remote", help="wiki git URL (default: wiki.remote, HARNESS_WIKI_REMOTE, or origin + .wiki.git)")
    p.add_argument("--token-env", help="environment variable holding an access token (default HARNESS_WIKI_TOKEN)")
    p.add_argument("--token-file", help="file holding the token (keep it under .local/)")
    p.add_argument("--no-bootstrap", action="store_true", help="do not enable/initialise the wiki through the API")
    p.add_argument("--message", help="commit message for the wiki commit")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_docs_publish_wiki)

    hist = sub.add_parser("history", help="implementation history derived from Git")
    hsub = hist.add_subparsers(dest="history_command", required=True)
    p = hsub.add_parser("sync", help="create/refresh commit records for a branch")
    p.add_argument("--branch", help="branch or revision (default: HEAD)")
    p.add_argument("--limit", type=int, help="number of commits to inspect (default from harness.yaml)")
    p.add_argument("--refresh", action="store_true", help="regenerate derived facts of existing records")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-branch-scan", action="store_true", help="skip `git branch --contains` per commit")
    p.set_defaults(func=cmd_history_sync)

    hk = sub.add_parser("hooks", help="optional Git hooks: pre-commit (index + check), post-commit (history sync)")
    hksub = hk.add_subparsers(dest="hooks_command", required=True)
    p = hksub.add_parser("install", help="install or refresh the hooks in .git/hooks")
    p.add_argument("--force", action="store_true", help="replace foreign hooks (backup kept)")
    p.set_defaults(func=cmd_hooks)
    p = hksub.add_parser("uninstall", help="remove the harness hooks (restores backups)")
    p.set_defaults(func=cmd_hooks)
    p = hksub.add_parser("status", help="show whether the hooks are installed")
    p.set_defaults(func=cmd_hooks)

    from harness import context_cli

    context_cli.add_parser(sub)
    sub.choices["context"].set_defaults(func=cmd_context)

    p = sub.add_parser("detect", help="show what init would detect (profile, commands, existing config)")
    p.set_defaults(func=cmd_detect)

    p = sub.add_parser("version", help="print the harness version")
    p.set_defaults(func=cmd_version)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # pragma: no cover
                pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except config_mod.ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
