"""Platform adapters: render Claude Code and Codex artifacts from shared sources.

Canonical content lives once (AGENTS.md managed block, the skills under
``harness/assets/skills``). Adapters only decide *where* each artifact goes
and add the few platform-specific lines that cannot be shared.
"""

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass
from pathlib import Path

from harness import __version__
from harness.core import assets
from harness.core.config import Config
from harness.core.manifest import BLOCK, MANAGED, SEED
from harness.core.util import today
from harness.profiles import get_profile

CLAUDE_SETTINGS = ".claude/settings.json"
SUBAGENT_ENV = {
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "3",
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
}
HOOK_COMMAND = ("harness status --brief --hook 2>/dev/null || "
                "python -m harness status --brief --hook 2>/dev/null || true")


@dataclass
class Artifact:
    path: str            # relative POSIX path in the consumer repository
    content: str
    kind: str            # MANAGED | BLOCK | SEED
    template: str | None = None


def _variables(config: Config) -> dict[str, object]:
    profile = get_profile(config.profile)
    cmds = [c for c in (config.get("verification.commands") or []) if isinstance(c, dict) and c.get("run")]
    if cmds:
        lines = []
        for c in cmds:
            flag = "" if c.get("verified") else " _(detected; confirm before relying on it)_"
            lines.append(f"- `{c['run']}` — {c.get('name', 'check')}{flag}")
        verification = "\n".join(lines)
    else:
        verification = "- none recorded yet: find the real command, run it, then add it to `harness.yaml` → `verification.commands`."
    guidance = profile.guidance or "- No profile-specific guidance."
    return {
        "project_name": config.project_name,
        "project_description": config.get("project.description") or "",
        "profile": profile.name,
        "profile_title": profile.title,
        "profile_guidance": guidance,
        "profile_testing": profile.testing or "- Use the project's existing test framework; add tests with every feature or fix.",
        "verification_commands": verification,
        "docs_dir": config.get("paths.docs"),
        "milestones_dir": config.get("paths.milestones"),
        "tasks_dir": config.get("paths.tasks"),
        "history_dir": config.get("paths.history"),
        "references_dir": config.get("paths.references"),
        "local_dir": config.get("paths.local"),
        "knowledge_map": config.get("paths.knowledge_map"),
        "llms_txt": config.get("paths.llms"),
        "harness_version": __version__,
        "harness_install": config.get("harness.harness_install") or (
            f'python -m pip install "agent-harness @ git+https://<your-forge>/<owner>/agent-harness.git@v{__version__}"'),
        "created": today(),
        "knowledge_map_from_docs": posixpath.relpath(config.get("paths.knowledge_map"), config.get("paths.docs")),
    }


def agents_block(config: Config) -> str:
    return assets.render_asset(_variables(config), "project", "agents-block.md").strip("\n")


def claude_block(config: Config) -> str:
    return assets.render_asset(_variables(config), "project", "claude-block.md").strip("\n")


def gitignore_block(config: Config) -> str:
    return assets.render_asset(_variables(config), "project", "gitignore-block.txt").strip("\n")


def skill_artifacts(config: Config) -> list[Artifact]:
    """Each packaged skill is installed identically for Claude (.claude/skills) and Codex (.agents/skills)."""
    out: list[Artifact] = []
    platforms = config.platforms
    targets = []
    if "claude" in platforms:
        targets.append(".claude/skills")
    if "codex" in platforms:
        targets.append(".agents/skills")
    variables = _variables(config)
    for skill_dir in sorted(p for p in assets.asset_path("skills").iterdir() if p.is_dir()):
        for file in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
            relative = file.relative_to(skill_dir).as_posix()
            content = assets.render(file.read_text(encoding="utf-8"), variables)
            for target in targets:
                out.append(Artifact(path=f"{target}/{skill_dir.name}/{relative}", content=content, kind=MANAGED,
                                    template=f"skills/{skill_dir.name}/{relative}"))
    return out


def claude_artifacts(config: Config) -> list[Artifact]:
    if "claude" not in config.platforms:
        return []
    variables = _variables(config)
    out: list[Artifact] = []
    for file in assets.list_assets("claude", "rules", pattern="*.md"):
        out.append(Artifact(path=f".claude/rules/{file.name}", content=assets.render(file.read_text(encoding='utf-8'), variables),
                            kind=MANAGED, template=f"claude/rules/{file.name}"))
    for file in assets.list_assets("claude", "agents", pattern="*.md"):
        out.append(Artifact(path=f".claude/agents/{file.name}", content=assets.render(file.read_text(encoding='utf-8'), variables),
                            kind=MANAGED, template=f"claude/agents/{file.name}"))
    return out


def workflow_artifacts(config: Config) -> list[Artifact]:
    variables = _variables(config)
    out: list[Artifact] = []
    for file in assets.list_assets("workflows", pattern="*.yml"):
        out.append(Artifact(path=f".forgejo/workflows/{file.name}", content=assets.render(file.read_text(encoding='utf-8'), variables),
                            kind=MANAGED, template=f"workflows/{file.name}"))
    return out


def seed_artifacts(config: Config) -> list[Artifact]:
    """Created once at init, project-owned afterwards."""
    variables = _variables(config)
    out: list[Artifact] = []
    for file in assets.list_assets("project", "seed", pattern="**/*"):
        relative = file.relative_to(assets.asset_path("project", "seed")).as_posix()
        # Allow configured directory names.
        # `_local/` in the seed tree stands for the ignored local directory (a real `.local/` would be
        # excluded from the framework repository by its own .gitignore rules).
        if relative.startswith("_local/"):
            relative = (config.get("paths.local") or ".local") + relative[len("_local"):]
        relative = (relative.replace("docs/", config.get("paths.docs") + "/", 1)
                    .replace("milestones/", config.get("paths.milestones") + "/", 1)
                    .replace("tasks/", config.get("paths.tasks") + "/", 1)
                    .replace("history/", config.get("paths.history") + "/", 1))
        out.append(Artifact(path=relative, content=assets.render(file.read_text(encoding="utf-8"), variables),
                            kind=SEED, template=f"project/seed/{file.relative_to(assets.asset_path('project', 'seed')).as_posix()}"))
    return out


# ---------------------------------------------------------------------------
# Claude settings.json hook (merge, never overwrite)
# ---------------------------------------------------------------------------

def merged_claude_settings(root: Path) -> tuple[str, bool]:
    """Return (new_json_text, changed) with the harness SessionStart hook ensured."""
    path = root / CLAUDE_SETTINGS
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            # Never clobber a file we cannot parse.
            return path.read_text(encoding="utf-8"), False
    changed = False
    hooks = data.setdefault("hooks", {})
    session = hooks.setdefault("SessionStart", [])
    if not any("harness status" in str(h.get("command", "")) for group in session for h in group.get("hooks", [])):
        session.append({"matcher": "startup|resume|clear|compact",
                        "hooks": [{"type": "command", "command": HOOK_COMMAND, "timeout": 20}]})
        changed = True
    # Native subagent limits (documented Claude Code env vars); existing values are never overridden.
    env = data.setdefault("env", {})
    for key, value in SUBAGENT_ENV.items():
        if key not in env:
            env[key] = value
            changed = True
    return json.dumps(data, indent=2) + "\n", changed
