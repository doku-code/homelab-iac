"""`harness status`: the session-resumption summary.

Everything here is derived from durable repository state (milestone and
task frontmatter, Git log, harness.yaml). Nothing is remembered between
runs, so a fresh agent session gets the same answer as the previous one.
"""

from __future__ import annotations

import json

from harness import __version__
from harness.core import gitutil
from harness.core.config import Config
from harness.core.documents import Catalog, Document, build_catalog
from harness.core.util import as_list


def _row(d: Document) -> dict:
    return {
        "id": d.id, "title": d.title, "status": d.status, "priority": d.meta.get("priority"),
        "path": d.relpath, "milestone": d.meta.get("milestone"),
        "depends_on": [str(x) for x in as_list(d.meta.get("depends_on"))],
    }


def collect(config: Config, catalog: Catalog | None = None, *, recent: int = 5) -> dict:
    catalog = catalog or build_catalog(config)
    milestones = catalog.of_type("milestone")
    tasks = catalog.of_type("task")
    active_ms = [m for m in milestones if m.status == "active"]
    blocked_ms = [m for m in milestones if m.status == "blocked"]
    planned_ms = sorted((m for m in milestones if m.status == "planned"), key=lambda d: d.id)
    in_progress = [t for t in tasks if t.status == "in-progress"]
    blocked = [t for t in tasks if t.status == "blocked"]
    active_ids = {m.id for m in active_ms}
    planned = sorted((t for t in tasks if t.status == "planned"), key=lambda d: (
        0 if str(d.meta.get("milestone")) in active_ids else 1,
        {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(str(d.meta.get("priority")), 4), d.id))
    next_tasks = []
    completed_ids = {t.id for t in tasks if t.status == "completed"}
    for t in planned:
        deps = [str(x) for x in as_list(t.meta.get("depends_on"))]
        if all(dep in completed_ids for dep in deps):
            next_tasks.append(t)
    decisions = sorted(catalog.of_type("decision"), key=lambda d: d.id, reverse=True)
    refs_needing = [d for d in catalog.typed() if d.status == "needs-revalidation"]

    git_info: dict = {"available": False}
    if gitutil.is_repo(config.root):
        git_info["available"] = True
        git_info["branch"] = gitutil.current_branch(config.root)
        git_info["recent"] = [
            {"short": c.short, "subject": c.subject, "authored": c.authored[:10]}
            for c in gitutil.log(config.root, "HEAD", limit=recent)
        ] if gitutil.has_commits(config.root) else []
        status = gitutil.run(["status", "--porcelain"], config.root, check=False)
        git_info["dirty_files"] = len([line for line in status.splitlines() if line.strip()])

    from harness.validation import check_indexes
    stale = [i.path for i in check_indexes(config, catalog) if i.level == "error"]

    return {
        "harness_version": __version__,
        "installed_version": config.installed_version,
        "project": config.project_name,
        "profile": config.profile,
        "counts": {
            "milestones": len(milestones), "tasks": len(tasks), "documents": len(catalog.typed()),
        },
        "active_milestones": [_row(m) for m in active_ms],
        "blocked_milestones": [_row(m) for m in blocked_ms],
        "next_planned_milestone": _row(planned_ms[0]) if planned_ms and not active_ms else None,
        "in_progress_tasks": [_row(t) for t in in_progress],
        "blocked_tasks": [_row(t) for t in blocked],
        "next_tasks": [_row(t) for t in next_tasks[:5]],
        "recent_decisions": [{"id": d.id, "title": d.title, "status": d.status, "path": d.relpath}
                             for d in decisions[:3]],
        "needs_revalidation": [{"id": d.id, "path": d.relpath} for d in refs_needing],
        "verification_commands": [c for c in (config.get("verification.commands") or []) if isinstance(c, dict)],
        "git": git_info,
        "stale_indexes": stale,
        "knowledge_map": config.get("paths.knowledge_map"),
    }


def render(data: dict, *, brief: bool = False) -> str:
    out: list[str] = []
    iv = data["installed_version"] or "not recorded"
    out.append(f"# {data['project']} — harness status (profile: {data['profile']}, harness v{iv})")
    if data["git"].get("available"):
        g = data["git"]
        out.append(f"Branch: {g.get('branch') or 'detached'}; uncommitted changes: {g.get('dirty_files', 0)} file(s)")
    out.append("")
    out.append("## Active milestone")
    if data["active_milestones"]:
        for m in data["active_milestones"]:
            out.append(f"- {m['id']} {m['title']} ({m['path']})")
    elif data["next_planned_milestone"]:
        m = data["next_planned_milestone"]
        out.append(f"- none active; next planned: {m['id']} {m['title']} ({m['path']})")
    else:
        out.append("- none")
    for m in data["blocked_milestones"]:
        out.append(f"- BLOCKED: {m['id']} {m['title']} ({m['path']})")
    out.append("")
    out.append("## Tasks")
    if data["in_progress_tasks"]:
        for t in data["in_progress_tasks"]:
            out.append(f"- in-progress: {t['id']} {t['title']} ({t['path']})")
    for t in data["blocked_tasks"]:
        out.append(f"- blocked: {t['id']} {t['title']} ({t['path']})")
    if data["next_tasks"]:
        for t in data["next_tasks"][: 3 if brief else 5]:
            out.append(f"- next: {t['id']} [{t['priority']}] {t['title']} ({t['path']})")
    if not (data["in_progress_tasks"] or data["blocked_tasks"] or data["next_tasks"]):
        out.append("- no open tasks")
    out.append("")
    if not brief:
        out.append("## Recent decisions")
        for d in data["recent_decisions"] or []:
            out.append(f"- {d['id']} {d['title']} ({d['status']}) — {d['path']}")
        if not data["recent_decisions"]:
            out.append("- none")
        out.append("")
    if data["git"].get("recent"):
        out.append("## Recent commits")
        for c in data["git"]["recent"][: 3 if brief else 5]:
            out.append(f"- {c['short']} {c['subject']} ({c['authored']})")
        out.append("")
    out.append("## Verification commands")
    cmds = data["verification_commands"]
    if cmds:
        for c in cmds:
            flag = "" if c.get("verified") else " (detected, not yet verified)"
            out.append(f"- {c.get('name', 'run')}: `{c.get('run')}`{flag}")
    else:
        out.append("- none configured (see harness.yaml → verification.commands)")
    out.append("")
    if data["needs_revalidation"]:
        out.append("## References needing revalidation")
        for r in data["needs_revalidation"]:
            out.append(f"- {r['id']} ({r['path']})")
        out.append("")
    if data["stale_indexes"]:
        out.append(f"Warning: stale generated index: {', '.join(data['stale_indexes'])} — run `harness docs index`.")
    out.append(f"Knowledge map: {data['knowledge_map']} · Search: `harness docs search <terms>`")
    return "\n".join(out)


def render_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)
