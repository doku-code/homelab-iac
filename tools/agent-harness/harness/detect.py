"""Repository inspection: languages, frameworks, docs, agent config, build commands.

Detection is marker-based and bounded (depth-limited walk, ignore lists) so
``harness init`` stays fast on large repositories. Nothing here executes
project code.
"""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from harness.profiles import Profile, VerificationCandidate, load_profiles

DEFAULT_IGNORE = {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", "dist", "build", "bin", "obj",
                  ".terraform", ".idea", ".vs", ".vscode", "target", ".local", ".harness", "packages", ".pytest_cache"}
MAX_DEPTH = 4
MAX_FILES = 20000

AGENT_CONFIG_MARKERS = {
    "claude": ["CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md", ".claude/settings.json", ".claude/rules",
               ".claude/skills", ".claude/agents", ".claude/commands"],
    "codex": ["AGENTS.md", "AGENTS.override.md", ".agents/skills", ".codex/config.toml"],
    "cursor": [".cursorrules", ".cursor/rules"],
    "copilot": [".github/copilot-instructions.md"],
    "gemini": ["GEMINI.md"],
}

DOC_MARKERS = ["README.md", "README.rst", "docs", "doc", "CHANGELOG.md", "CONTRIBUTING.md", "ARCHITECTURE.md",
               "wiki", "adr", "docs/adr", "docs/decisions"]


@dataclass
class Inventory:
    files: list[str] = field(default_factory=list)   # relative POSIX paths (bounded)
    dirs: set[str] = field(default_factory=set)
    truncated: bool = False

    def exists(self, relpath: str) -> bool:
        relpath = relpath.rstrip("/")
        return relpath in self.dirs or relpath in self.files

    def glob(self, pattern: str) -> list[str]:
        pattern = pattern.rstrip("/")
        if "*" not in pattern and "?" not in pattern:
            return [pattern] if self.exists(pattern) else []
        if pattern.startswith("**/"):
            tail = pattern[3:]
            return [f for f in self.files if fnmatch.fnmatch(f.rsplit("/", 1)[-1], tail) or fnmatch.fnmatch(f, pattern)]
        return [f for f in self.files if fnmatch.fnmatch(f, pattern)]


def inventory(root: Path, *, extra_ignore: set[str] | None = None) -> Inventory:
    ignore = DEFAULT_IGNORE | (extra_ignore or set())
    inv = Inventory()

    def walk(dir_path: Path, depth: int, prefix: str) -> None:
        if depth > MAX_DEPTH or inv.truncated:
            return
        try:
            entries = sorted(dir_path.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            return
        for entry in entries:
            name = entry.name
            relp = f"{prefix}{name}"
            if entry.is_dir():
                if name in ignore or name.startswith(".git"):
                    continue
                inv.dirs.add(relp)
                walk(entry, depth + 1, relp + "/")
            else:
                inv.files.append(relp)
                if len(inv.files) >= MAX_FILES:
                    inv.truncated = True
                    return

    walk(root, 0, "")
    return inv


@dataclass
class DetectionResult:
    scores: dict[str, int]
    primary: str
    detected: list[str]
    agent_configs: dict[str, list[str]]
    docs: list[str]
    verification: list[dict]
    truncated: bool = False
    languages: dict[str, int] = field(default_factory=dict)


_LANG_EXT = {
    ".py": "python", ".cs": "csharp", ".ps1": "powershell", ".psm1": "powershell", ".psd1": "powershell",
    ".ts": "typescript", ".tsx": "typescript", ".js": "javascript", ".go": "go", ".rs": "rust", ".java": "java",
    ".tf": "opentofu", ".yml": "yaml", ".yaml": "yaml", ".sh": "shell", ".rb": "ruby", ".php": "php",
}


def _marker_matches(inv: Inventory, root: Path, marker: str) -> bool:
    """Marker forms: 'path', 'glob/**', 'file:substring' (content marker)."""
    if ":" in marker and not marker.startswith("**") and "/" not in marker.split(":", 1)[0].replace("\\", "/")[:2]:
        file_part, needle = marker.split(":", 1)
        p = root / file_part
        if p.is_file():
            try:
                return needle in p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return False
        return False
    return bool(inv.glob(marker))


def detect(root: Path, *, profiles: dict[str, Profile] | None = None) -> DetectionResult:
    profiles = profiles or load_profiles()
    inv = inventory(root)
    scores: dict[str, int] = {}
    for name, prof in profiles.items():
        score = 0
        for rule in prof.detect:
            pattern = rule.get("glob") or rule.get("path")
            weight = int(rule.get("weight", 1))
            if pattern and _marker_matches(inv, root, pattern):
                score += weight
        if score:
            scores[name] = score
    detected = sorted((n for n in scores if n != "generic"), key=lambda n: (-scores[n], n))
    primary = detected[0] if detected else "generic"

    agent_configs: dict[str, list[str]] = {}
    for platform, markers in AGENT_CONFIG_MARKERS.items():
        found = [m for m in markers if (root / m).exists()]
        if found:
            agent_configs[platform] = found
    docs = [m for m in DOC_MARKERS if (root / m).exists()]

    languages: dict[str, int] = {}
    for f in inv.files:
        ext = "." + f.rsplit(".", 1)[-1].lower() if "." in f.rsplit("/", 1)[-1] else ""
        lang = _LANG_EXT.get(ext)
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    verification = detect_verification(root, inv, [profiles[n] for n in ([primary] + [d for d in detected if d != primary])
                                                   if n in profiles])
    return DetectionResult(scores=scores, primary=primary, detected=detected or ["generic"],
                           agent_configs=agent_configs, docs=docs, verification=verification,
                           truncated=inv.truncated, languages=dict(sorted(languages.items(), key=lambda kv: -kv[1])))


def detect_verification(root: Path, inv: Inventory, profiles: list[Profile]) -> list[dict]:
    """Candidate verification commands whose markers exist. Never invented, never executed."""
    found: list[dict] = []
    seen: set[str] = set()

    def add(name: str, run: str, source: str, description: str = "") -> None:
        if run in seen:
            return
        seen.add(run)
        found.append({"name": name, "run": run, "detected": True, "verified": False, "source": source,
                      **({"description": description} if description else {})})

    for prof in profiles:
        for cand in prof.verification:
            if not cand.when or any(_marker_matches(inv, root, m) for m in cand.when):
                add(cand.name, cand.run, f"profile:{prof.name}", cand.description)

    # package.json scripts
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            scripts = data.get("scripts") or {}
            for key in ("test", "lint", "build", "typecheck", "check"):
                if key in scripts:
                    add(key, f"npm run {key}", "package.json")
        except (json.JSONDecodeError, OSError):
            pass
    # Makefile targets
    mk = root / "Makefile"
    if mk.is_file():
        try:
            text = mk.read_text(encoding="utf-8", errors="replace")
            for target in ("test", "lint", "check", "build", "validate"):
                if re.search(rf"^{target}\s*:", text, re.MULTILINE):
                    add(target, f"make {target}", "Makefile")
        except OSError:
            pass
    # justfile / taskfile
    if (root / "justfile").is_file() or (root / "Justfile").is_file():
        add("just-test", "just test", "justfile")
    if (root / "Taskfile.yml").is_file():
        add("task-test", "task test", "Taskfile.yml")
    return found


def candidate_to_config(c: dict) -> dict:
    out = {"name": c["name"], "run": c["run"], "detected": True, "verified": False}
    if c.get("description"):
        out["description"] = c["description"]
    return out


__all__ = ["detect", "DetectionResult", "inventory", "Inventory", "VerificationCandidate", "candidate_to_config"]
