"""`harness update`: reviewable, conflict-aware framework upgrade for a consumer repository."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from harness import __version__
from harness.core import config as config_mod
from harness.core import manifest as manifest_mod
from harness.index import write_indexes
from harness.installer import CONFLICT, CREATE, SKIP, TAKEOVER, UNCHANGED, UPDATE, Action, apply, plan


@dataclass
class UpdateReport:
    installed_version: str | None
    target_version: str
    actions: list[Action] = field(default_factory=list)
    dry_run: bool = True
    indexes: list[str] = field(default_factory=list)
    applied: bool = False

    @property
    def conflicts(self) -> list[Action]:
        return [a for a in self.actions if a.action == CONFLICT]

    @property
    def changes(self) -> list[Action]:
        return [a for a in self.actions if a.action in (CREATE, UPDATE, TAKEOVER)]

    def summary(self, *, show_diff: bool = False) -> str:
        out = [f"harness update — installed v{self.installed_version or 'unknown'} → v{self.target_version}"
               + (" (dry run)" if self.dry_run else "")]
        counts = {}
        for a in self.actions:
            counts[a.action] = counts.get(a.action, 0) + 1
        out.append("plan: " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
        for a in self.actions:
            if a.action == UNCHANGED or a.action == SKIP:
                continue
            marker = {CREATE: "+", UPDATE: "~", TAKEOVER: "!", CONFLICT: "!"}.get(a.action, "?")
            out.append(f"  {marker} {a.path}: {a.action}{(' — ' + a.reason) if a.reason else ''}")
            if show_diff and a.action in (UPDATE, CONFLICT, TAKEOVER):
                d = a.diff()
                if d:
                    out.append(d.rstrip("\n"))
        if self.conflicts:
            out.append("conflicts are left untouched. Resolve by editing the file, or re-run with --force to replace "
                       "(previous content is backed up under .local/harness-backup/).")
        if self.indexes:
            out.append("regenerated: " + ", ".join(self.indexes))
        if self.dry_run:
            out.append("nothing written (dry run). Re-run with --apply to write.")
        return "\n".join(out)


def run(root: Path, *, apply_changes: bool = False, force: bool = False) -> UpdateReport:
    cfg = config_mod.load(root)
    if not cfg.exists:
        raise config_mod.ConfigError("harness.yaml not found; run `harness init` first")
    manifest = manifest_mod.load(root)
    report = UpdateReport(installed_version=cfg.installed_version or (manifest.harness_version if manifest else None),
                          target_version=__version__, dry_run=not apply_changes)
    p = plan(cfg, manifest, force=force)
    report.actions = p.actions
    if not apply_changes:
        return report
    cfg.set("harness.version", __version__)
    cfg.save()
    apply(cfg, p, manifest)
    report.indexes = write_indexes(cfg)
    report.applied = True
    return report
