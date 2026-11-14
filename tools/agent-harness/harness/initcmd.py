"""`harness init`: safe, repeatable project initialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from harness import __version__
from harness.core import config as config_mod
from harness.core import gitutil
from harness.core import manifest as manifest_mod
from harness.detect import candidate_to_config, detect
from harness.index import write_indexes
from harness.installer import CONFLICT, CREATE, SKIP, TAKEOVER, UNCHANGED, UPDATE, apply, plan
from harness.profiles import get_profile


@dataclass
class InitReport:
    root: Path
    profile: str
    detected: list[str]
    agent_configs: dict[str, list[str]]
    docs: list[str]
    verification: list[dict]
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    conflicts: list[tuple[str, str]] = field(default_factory=list)
    indexes: list[str] = field(default_factory=list)
    config_written: bool = False
    git_initialized: bool = False
    dry_run: bool = False
    languages: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        out = [f"harness init — {self.root}"]
        out.append(f"profile: {self.profile} (detected: {', '.join(self.detected) or 'none'})")
        if self.languages:
            top = ", ".join(f"{k} ({v})" for k, v in list(self.languages.items())[:5])
            out.append(f"languages: {top}")
        if self.agent_configs:
            found = "; ".join(f"{k}: {', '.join(v)}" for k, v in self.agent_configs.items())
            out.append(f"existing agent configuration preserved: {found}")
        if self.docs:
            out.append(f"existing documentation: {', '.join(self.docs)}")
        if self.verification:
            out.append("detected verification commands (not yet verified):")
            for c in self.verification:
                out.append(f"  - {c['name']}: {c['run']}")
        if self.git_initialized:
            out.append("initialized empty Git repository")
        prefix = "would " if self.dry_run else ""
        out.append(f"{prefix}create: {len(self.created)}, update: {len(self.updated)}, unchanged: {len(self.unchanged)}, "
                   f"skip (project-owned): {len(self.skipped)}, conflicts: {len(self.conflicts)}")
        for p in self.created:
            out.append(f"  + {p}")
        for p in self.updated:
            out.append(f"  ~ {p}")
        for p, reason in self.conflicts:
            out.append(f"  ! {p}: {reason} (left untouched; use --force to replace, backup kept in .local/)")
        if self.indexes:
            out.append(f"{prefix}regenerate: " + ", ".join(self.indexes))
        if not self.dry_run:
            out.append("next: review harness.yaml, run `harness status`, then `harness check`.")
        return "\n".join(out)


def run(root: Path, *, profile: str | None = None, platforms: list[str] | None = None, name: str | None = None,
        description: str | None = None, git_init: bool = False, dry_run: bool = False, force: bool = False) -> InitReport:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    git_initialized = False
    if not gitutil.is_repo(root):
        if git_init:
            if not dry_run:
                gitutil.init_repo(root)
            git_initialized = True

    detection = detect(root)
    cfg = config_mod.load(root)
    existing_cfg = cfg.exists
    chosen_profile = profile or (cfg.get("harness.profile") if existing_cfg else None) or detection.primary
    get_profile(chosen_profile)  # validates

    # Fill configuration without clobbering existing values.
    cfg.set("harness.version", __version__)
    cfg.set("harness.profile", chosen_profile)
    cfg.set("harness.detected_profiles", detection.detected)
    if platforms:
        cfg.set("harness.platforms", platforms)
    elif "platforms" not in cfg.raw.get("harness", {}):
        cfg.set("harness.platforms", ["claude", "codex"])
    if name or not cfg.get("project.name"):
        cfg.set("project.name", name or root.name)
    if description or not existing_cfg:
        cfg.set("project.description", description or cfg.get("project.description") or "")
    if "harness_install" not in cfg.raw.get("harness", {}):
        cfg.set("harness.harness_install",
                f'python -m pip install "agent-harness @ git+https://<your-forge>/<owner>/agent-harness.git@v{__version__}"')
    if not cfg.get("verification.commands"):
        cfg.set("verification.commands", [candidate_to_config(c) for c in detection.verification])
    for key, default in config_mod.DEFAULTS["paths"].items():
        if key not in cfg.raw.get("paths", {}):
            cfg.set(f"paths.{key}", default)
    for section in ("history", "wiki"):
        if section not in cfg.raw:
            cfg.set(section, dict(config_mod.DEFAULTS[section]))

    report = InitReport(root=root, profile=chosen_profile, detected=detection.detected,
                        agent_configs=detection.agent_configs, docs=detection.docs,
                        verification=[c for c in detection.verification], git_initialized=git_initialized,
                        dry_run=dry_run, languages=detection.languages)

    manifest = manifest_mod.load(root)
    p = plan(cfg, manifest, force=force)
    for act in p.actions:
        if act.action == CREATE:
            report.created.append(act.path)
        elif act.action in (UPDATE, TAKEOVER):
            report.updated.append(act.path)
        elif act.action == UNCHANGED:
            report.unchanged.append(act.path)
        elif act.action == SKIP:
            report.skipped.append(act.path)
        elif act.action == CONFLICT:
            report.conflicts.append((act.path, act.reason))
    if dry_run:
        report.indexes = [cfg.get("paths.knowledge_map"), cfg.get("paths.catalog")]
        return report
    report.config_written = cfg.save()
    apply(cfg, p, manifest)
    (root / (cfg.get("paths.local") or ".local")).mkdir(parents=True, exist_ok=True)
    report.indexes = write_indexes(cfg)
    return report

