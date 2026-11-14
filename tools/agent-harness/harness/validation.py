"""`harness check`: deterministic validation of configuration, documents and safety.

Every check returns a list of :class:`Issue`. Errors make the command exit
non-zero; warnings are informational. Checks are pure functions of repository
state so they are cheap to run in CI and in tests.
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from harness.core import blocks, gitutil, schema
from harness.core.config import Config
from harness.core.documents import Catalog, Document, build_catalog
from harness.core.util import as_list

ERROR = "error"
WARNING = "warning"


@dataclass
class Issue:
    level: str
    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.code} {self.path}: {self.message}"


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

_EXTERNAL_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


def check_documents(config: Config, catalog: Catalog | None = None) -> list[Issue]:
    catalog = catalog or build_catalog(config)
    issues: list[Issue] = []
    for doc in catalog.documents:
        issues.extend(_check_document(doc, catalog, config))
    issues.extend(check_supersession_cycles(catalog))
    for doc_id, docs in catalog.duplicates.items():
        paths = ", ".join(d.relpath for d in docs)
        issues.append(Issue(ERROR, "DOC-DUP-ID", docs[0].relpath, f"duplicate id {doc_id!r} in: {paths}"))
    return issues


def _check_document(doc: Document, catalog: Catalog, config: Config) -> list[Issue]:
    issues: list[Issue] = []
    p = doc.relpath
    if doc.error:
        return [Issue(ERROR, "DOC-PARSE", p, doc.error)]
    if not doc.has_frontmatter:
        # README/index files without frontmatter are tolerated but reported.
        if doc.path.name.lower() in ("readme.md", "index.md", "home.md"):
            return []
        return [Issue(WARNING, "DOC-NO-FRONTMATTER", p, "markdown document has no YAML frontmatter")]

    meta = doc.meta
    type_name = str(meta.get("type") or "")
    dt = schema.doc_type(type_name)
    if not type_name:
        issues.append(Issue(ERROR, "DOC-NO-TYPE", p, "missing required field 'type'"))
        return issues
    if dt is None:
        issues.append(Issue(ERROR, "DOC-BAD-TYPE", p, f"unknown document type {type_name!r}; "
                                                       f"known: {', '.join(sorted(schema.DOC_TYPES))}"))
        return issues

    for fld in dt.required_fields:
        if fld not in meta or meta[fld] in (None, ""):
            issues.append(Issue(ERROR, "DOC-MISSING-FIELD", p, f"missing required field {fld!r} for type {type_name}"))

    doc_id = meta.get("id")
    if doc_id is not None and not schema.is_valid_id(type_name, str(doc_id)):
        issues.append(Issue(ERROR, "DOC-BAD-ID", p, f"id {doc_id!r} does not match pattern {dt.id_pattern} "
                                                     f"for type {type_name}"))

    status = meta.get("status")
    if status is not None and str(status) not in dt.statuses:
        issues.append(Issue(ERROR, "DOC-BAD-STATUS", p, f"status {status!r} not in {list(dt.statuses)} "
                                                         f"for type {type_name}"))

    priority = meta.get("priority")
    if priority is not None and str(priority) not in schema.PRIORITIES:
        issues.append(Issue(ERROR, "DOC-BAD-PRIORITY", p, f"priority {priority!r} not in {list(schema.PRIORITIES)}"))

    for fld in ("created", "updated", "verified", "last_verified", "review_after"):
        val = meta.get(fld)
        if val is None:
            continue
        sval = val.isoformat() if hasattr(val, "isoformat") else str(val)
        if not schema.DATE_RE.match(sval[:10]):
            issues.append(Issue(ERROR, "DOC-BAD-DATE", p, f"field {fld!r} must be YYYY-MM-DD, got {val!r}"))

    summary = meta.get("summary")
    if summary is not None and (not isinstance(summary, str) or len(summary) > 200 or "\n" in summary):
        issues.append(Issue(WARNING, "DOC-BAD-SUMMARY", p, "'summary' should be one line of at most 200 characters"))

    tags = meta.get("tags")
    if tags is not None and not isinstance(tags, list):
        issues.append(Issue(ERROR, "DOC-BAD-TAGS", p, "'tags' must be a list"))

    issues.extend(_check_retrieval_fields(doc, p))

    # Relationship integrity
    for fld, target in doc.id_references():
        if target not in catalog.by_id:
            code = "DOC-MISSING-TASK" if target.startswith("TASK-") else (
                "DOC-MISSING-MILESTONE" if re.match(r"^M\d+$", target) else "DOC-BROKEN-REF")
            issues.append(Issue(ERROR, code, p, f"{fld} references unknown document id {target!r}"))
    for fld in schema.PATH_RELATION_FIELDS:
        for target in as_list(meta.get(fld)):
            tgt = config.root / str(target)
            if not tgt.exists():
                code = {"related_tests": "DOC-MISSING-TEST", "source_paths": "DOC-MISSING-SOURCE"}.get(fld, "DOC-MISSING-IMPL")
                issues.append(Issue(WARNING, code, p, f"{fld} path not found: {target}"))

    # Task-specific: milestone must be a milestone
    if type_name == "task":
        ms = meta.get("milestone")
        if ms and ms in catalog.by_id and catalog.by_id[str(ms)].type != "milestone":
            issues.append(Issue(ERROR, "DOC-BAD-MILESTONE", p, f"milestone {ms!r} is not a milestone document"))
        if status == "completed":
            impls = as_list(meta.get("related_implementations"))
            tests = as_list(meta.get("related_tests"))
            justification = str(meta.get("tests_justification") or "").strip()
            if impls and not tests and not justification:
                issues.append(Issue(ERROR, "TASK-NO-TESTS", p,
                                    "completed task has related_implementations but no related_tests and no tests_justification"))
            body_lower = doc.body.lower()
            if "## completion summary" in body_lower and "_not completed._" in body_lower:
                issues.append(Issue(ERROR, "TASK-NO-SUMMARY", p, "task is completed but Completion summary is empty"))
            if not as_list(meta.get("evidence")) and "not verified" in body_lower and "| not verified |" in body_lower:
                issues.append(Issue(WARNING, "TASK-NO-EVIDENCE", p,
                                    "task is completed but evidence table still says 'not verified'"))
    if type_name == "milestone" and status == "completed":
        if "_not completed._" in doc.body.lower():
            issues.append(Issue(ERROR, "MS-NO-SUMMARY", p, "milestone is completed but Completion summary is empty"))

    # Required sections (warning only: documents may legitimately be terse)
    if dt.required_sections:
        headings = {h.lower() for h in doc.headings()}
        for sec in dt.required_sections:
            if sec.lower() not in headings:
                issues.append(Issue(WARNING, "DOC-MISSING-SECTION", p, f"section '## {sec}' not found"))

    # Markdown links
    issues.extend(_check_links(doc, catalog, config))
    return issues


def _check_retrieval_fields(doc: Document, p: str) -> list[Issue]:
    """Optional context-retrieval metadata: importance, topics, applies_to, source_paths, supersession."""
    issues: list[Issue] = []
    meta = doc.meta
    imp = meta.get("importance")
    if imp is not None:
        lo, hi = schema.IMPORTANCE_RANGE
        if isinstance(imp, bool) or not isinstance(imp, int) or not lo <= imp <= hi:
            issues.append(Issue(ERROR, "DOC-BAD-IMPORTANCE", p, f"importance must be an integer {lo}-{hi}, got {imp!r}"))
    for fld in ("topics", "applies_to", "source_paths"):
        val = meta.get(fld)
        if val is not None and (not isinstance(val, list) or not all(isinstance(v, str) for v in val)):
            issues.append(Issue(ERROR, "DOC-BAD-LIST", p, f"'{fld}' must be a list of strings"))
    for fld in ("last_verified", "review_after"):
        val = meta.get(fld)
        if val is not None and not hasattr(val, "isoformat") and not isinstance(val, str):
            issues.append(Issue(ERROR, "DOC-BAD-DATE", p, f"field {fld!r} must be YYYY-MM-DD, got {val!r}"))
    lv, ra = meta.get("last_verified"), meta.get("review_after")
    if lv is not None and ra is not None and str(ra)[:10] < str(lv)[:10]:
        issues.append(Issue(WARNING, "DOC-REVIEW-BEFORE-VERIFIED", p, "review_after is earlier than last_verified"))
    if str(meta.get("status") or "") == "superseded" and not as_list(meta.get("superseded_by")):
        issues.append(Issue(WARNING, "DOC-SUPERSEDED-NO-TARGET", p, "status superseded without superseded_by"))
    for target in as_list(meta.get("superseded_by")):
        if str(target) == doc.id:
            issues.append(Issue(ERROR, "DOC-SUPERSESSION-CYCLE", p, "document supersedes itself"))
    return issues


def check_supersession_cycles(catalog: Catalog) -> list[Issue]:
    """Each document follows its superseded_by chain; revisiting a document is a cycle (reported once per cycle)."""
    issues: list[Issue] = []
    reported: set[frozenset[str]] = set()
    for d in catalog.typed():
        seen: list[str] = []
        cur = d
        while cur is not None:
            if cur.id in seen:
                cycle = frozenset(seen[seen.index(cur.id):])
                if cycle not in reported and len(cycle) > 1:
                    reported.add(cycle)
                    issues.append(Issue(ERROR, "DOC-SUPERSESSION-CYCLE", d.relpath,
                                        "superseded_by forms a cycle: " + " -> ".join(sorted(cycle))))
                break
            seen.append(cur.id)
            nxt = as_list(cur.meta.get("superseded_by"))
            cur = catalog.by_id.get(str(nxt[0])) if nxt else None
    return issues


def _check_links(doc: Document, catalog: Catalog, config: Config) -> list[Issue]:
    issues: list[Issue] = []
    for _text, target in doc.markdown_links():
        if target.startswith("#") or _EXTERNAL_RE.match(target):
            continue
        clean = unquote(target.split("#", 1)[0])
        if not clean:
            continue
        if clean.startswith("/"):
            resolved = config.root / clean.lstrip("/")
        else:
            resolved = doc.path.parent / clean
        # Normalise `..` segments: an un-normalised path can exceed Windows MAX_PATH and make exists() lie.
        resolved = Path(os.path.normpath(resolved))
        if not resolved.exists():
            issues.append(Issue(ERROR, "DOC-BROKEN-LINK", doc.relpath, f"broken link target: {target}"))
    for target in doc.wiki_links():
        t = target.strip()
        if t in catalog.by_id:
            continue
        # Obsidian resolves [[Title]] and [[filename]]; accept both.
        if any(d.title == t or d.path.stem == t for d in catalog.documents):
            continue
        issues.append(Issue(WARNING, "DOC-BROKEN-WIKILINK", doc.relpath, f"wikilink does not resolve: [[{t}]]"))
    return issues


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def check_config(config: Config) -> list[Issue]:
    issues: list[Issue] = []
    if not config.exists:
        return [Issue(ERROR, "CFG-MISSING", "harness.yaml", "harness.yaml not found; run `harness init`")]
    from harness.profiles import available_profiles

    if config.profile not in available_profiles():
        issues.append(Issue(ERROR, "CFG-PROFILE", "harness.yaml", f"unknown profile {config.profile!r}"))
    for platform in config.platforms:
        if platform not in ("claude", "codex"):
            issues.append(Issue(ERROR, "CFG-PLATFORM", "harness.yaml", f"unknown platform {platform!r}"))
    for key in ("docs", "milestones", "tasks", "history", "local"):
        if not config.get(f"paths.{key}"):
            issues.append(Issue(ERROR, "CFG-PATH", "harness.yaml", f"paths.{key} must be set"))
    for cmd in config.get("verification.commands") or []:
        if not isinstance(cmd, dict) or "run" not in cmd:
            issues.append(Issue(ERROR, "CFG-VERIFY", "harness.yaml", f"verification command must have 'run': {cmd!r}"))
    if not config.installed_version:
        issues.append(Issue(WARNING, "CFG-VERSION", "harness.yaml", "harness.version is not recorded"))
    return issues


# ---------------------------------------------------------------------------
# Agent entrypoints
# ---------------------------------------------------------------------------

def check_entrypoints(config: Config) -> list[Issue]:
    issues: list[Issue] = []
    root = config.root
    platforms = config.platforms
    agents = root / "AGENTS.md"
    if not agents.exists():
        issues.append(Issue(ERROR, "ENTRY-MISSING", "AGENTS.md", "canonical agent entrypoint missing"))
    else:
        version, body = blocks.find_block(agents.read_text(encoding="utf-8"))
        if body is None:
            issues.append(Issue(ERROR, "ENTRY-NO-BLOCK", "AGENTS.md", "managed block missing; run `harness update`"))
        elif version and config.installed_version and version != config.installed_version:
            issues.append(Issue(WARNING, "ENTRY-VERSION", "AGENTS.md",
                                f"managed block is v{version}, installed harness is v{config.installed_version}"))
        text = agents.read_text(encoding="utf-8")
        if len(text.encode("utf-8")) > 32 * 1024:
            issues.append(Issue(WARNING, "ENTRY-SIZE", "AGENTS.md", "larger than 32 KiB (Codex default project_doc_max_bytes)"))
    if "claude" in platforms:
        claude = root / "CLAUDE.md"
        if not claude.exists():
            issues.append(Issue(ERROR, "ENTRY-MISSING", "CLAUDE.md", "Claude Code entrypoint missing"))
        else:
            text = claude.read_text(encoding="utf-8")
            if "@AGENTS.md" not in text:
                issues.append(Issue(WARNING, "ENTRY-NO-IMPORT", "CLAUDE.md", "does not import @AGENTS.md; content may drift"))
        issues.extend(_check_skill_sync(root))
    return issues


def _check_skill_sync(root: Path) -> list[Issue]:
    """Claude and Codex skill copies installed by the harness must be identical."""
    issues: list[Issue] = []
    from harness.core import manifest as manifest_mod

    m = manifest_mod.load(root)
    if not m:
        return issues
    for entry in m.entries.values():
        if not entry.path.startswith(".claude/skills/"):
            continue
        twin = ".agents/skills/" + entry.path[len(".claude/skills/"):]
        a, b = root / entry.path, root / twin
        if a.exists() and b.exists() and a.read_bytes() != b.read_bytes():
            issues.append(Issue(WARNING, "SKILL-DRIFT", entry.path, f"differs from {twin}; run `harness update`"))
    return issues


# ---------------------------------------------------------------------------
# Generated indexes
# ---------------------------------------------------------------------------

def check_indexes(config: Config, catalog: Catalog | None = None) -> list[Issue]:
    from harness.index import render_catalog_json, render_knowledge_map, render_llms_txt

    catalog = catalog or build_catalog(config)
    issues: list[Issue] = []
    km = config.rel_path("knowledge_map")
    cj = config.rel_path("catalog")
    if not km.exists():
        issues.append(Issue(ERROR, "INDEX-MISSING", config.get("paths.knowledge_map"), "run `harness docs index`"))
    elif km.read_text(encoding="utf-8").replace("\r\n", "\n") != render_knowledge_map(config, catalog):
        issues.append(Issue(ERROR, "INDEX-STALE", config.get("paths.knowledge_map"), "stale; run `harness docs index`"))
    if cj.exists() and cj.read_text(encoding="utf-8").replace("\r\n", "\n") != render_catalog_json(config, catalog):
        issues.append(Issue(ERROR, "INDEX-STALE", config.get("paths.catalog"), "stale; run `harness docs index`"))
    llms = config.rel_path("llms")
    if not config.get("documents.llms_txt"):
        pass
    elif not llms.exists():
        issues.append(Issue(WARNING, "INDEX-MISSING", config.get("paths.llms"), "not generated yet; run `harness docs index`"))
    elif llms.read_text(encoding="utf-8").replace("\r\n", "\n") != render_llms_txt(config, catalog):
        issues.append(Issue(ERROR, "INDEX-STALE", config.get("paths.llms"), "stale; run `harness docs index`"))
    hist_index = config.rel_path("history") / "README.md"
    if (config.rel_path("history") / "branches").exists():
        from harness.history import render_index

        current = hist_index.read_text(encoding="utf-8").replace("\r\n", "\n") if hist_index.exists() else None
        if current != render_index(config):
            issues.append(Issue(ERROR, "INDEX-STALE", f"{config.get('paths.history')}/README.md",
                                "stale; run `harness docs index` or `harness history sync`"))
    return issues


# ---------------------------------------------------------------------------
# Sensitive data
# ---------------------------------------------------------------------------

SENSITIVE_NAME_PATTERNS = [
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore", "id_rsa", "id_ed25519", "id_ecdsa",
    "*.ovpn", "*secrets*.yaml", "*secrets*.yml", "*secrets*.json", "*.credentials", "credentials.json",
    "*.tfstate", "*.tfstate.backup", "*.tfvars", "terraform.tfvars", "vault.yml", "*.vault", ".netrc", "_netrc",
    ".npmrc", ".pypirc", "*.kdbx", "*.sqlite", "*.db",
]
# Sanitized examples are explicitly allowed.
SENSITIVE_NAME_ALLOW = ["*.example", "*.example.*", "*example*.yaml", "*example*.yml", "*.sample", "*.template", "*.dist"]

SECRET_CONTENT_PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?-----")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("Forgejo/Gitea token", re.compile(r"\b[0-9a-f]{40}\b(?=.*(?:token|TOKEN))")),
    ("password assignment", re.compile(
        r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|token)\b\s*[:=]\s*['\"]?(?!\s*(?:<|\$\{|\{\{|\*\*\*|xxx|changeme|example|placeholder|redacted|dummy|your[-_]|none|null|''|\"\")) (?P<value>[^\s'\"]{8,})")),
]
_PLACEHOLDER_RE = re.compile(r"(?i)(example|placeholder|dummy|redacted|changeme|xxx+|<[^>]+>|\$\{[^}]+\}|\{\{[^}]+\}\})")

_TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".toml", ".txt", ".ini", ".cfg", ".env", ".py", ".ps1", ".sh",
                  ".ts", ".js", ".cs", ".tf", ".xml", ".conf", ".properties", ".pem", ".key", ".crt", ".pub"}


def _name_is_sensitive(relpath: str, extra: list[str]) -> bool:
    name = relpath.rsplit("/", 1)[-1]
    if any(fnmatch.fnmatch(name, pat) for pat in SENSITIVE_NAME_ALLOW):
        return False
    for pat in SENSITIVE_NAME_PATTERNS:
        if fnmatch.fnmatch(name, pat):
            return True
    for pat in extra:
        if fnmatch.fnmatch(relpath, pat) or fnmatch.fnmatch(name, pat):
            return True
    return False


def scan_text_for_secrets(text: str) -> list[tuple[str, int]]:
    """Return (pattern name, line number) for every suspicious line."""
    hits: list[tuple[str, int]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if "harness:allow-secret-pattern" in line:
            continue
        for name, rx in SECRET_CONTENT_PATTERNS:
            m = rx.search(line)
            if not m:
                continue
            if name == "password assignment":
                value = m.group("value")
                # Code expressions (calls, attribute lookups) are not literal secrets.
                if _PLACEHOLDER_RE.search(line) or "(" in value or value.startswith(("os.", "self.", "args.", "cfg.", "config.")):
                    continue
            hits.append((name, lineno))
            break
    return hits


def check_sensitive(config: Config, *, scan_tracked: bool = True) -> list[Issue]:
    issues: list[Issue] = []
    root = config.root
    local_dir = config.get("paths.local") or ".local"
    extra = list(config.get("sensitive.patterns") or [])

    gi = root / ".gitignore"
    if not gi.exists():
        issues.append(Issue(ERROR, "SEC-NO-GITIGNORE", ".gitignore", "missing; .local/ would be committed"))
    if gitutil.is_repo(root):
        probe = [f"{local_dir}/probe.txt", f"{local_dir}/nested/probe.txt"]
        ignored = gitutil.check_ignored(root, probe)
        if not all(ignored.get(p) for p in probe):
            issues.append(Issue(ERROR, "SEC-LOCAL-NOT-IGNORED", local_dir, f"{local_dir}/ is not ignored by Git"))
        # staged sensitive files
        for f in gitutil.staged_files(root):
            if f.startswith(local_dir.rstrip("/") + "/"):
                issues.append(Issue(ERROR, "SEC-STAGED-LOCAL", f, "file under .local/ is staged"))
            elif _name_is_sensitive(f, extra):
                issues.append(Issue(ERROR, "SEC-STAGED-SENSITIVE", f, "staged file matches a sensitive pattern"))
        if scan_tracked:
            candidates = gitutil.tracked_files(root) + gitutil.staged_files(root)
            seen: set[str] = set()
            for f in candidates:
                if f in seen:
                    continue
                seen.add(f)
                if f.startswith(local_dir.rstrip("/") + "/"):
                    issues.append(Issue(ERROR, "SEC-TRACKED-LOCAL", f, "file under .local/ is tracked by Git"))
                    continue
                if _name_is_sensitive(f, extra):
                    issues.append(Issue(ERROR, "SEC-TRACKED-SENSITIVE", f, "tracked file matches a sensitive pattern"))
                p = root / f
                if p.suffix.lower() in _TEXT_SUFFIXES and p.exists() and p.stat().st_size < 2_000_000:
                    try:
                        text = p.read_text(encoding="utf-8")
                    except (OSError, UnicodeDecodeError):
                        continue
                    for name, lineno in scan_text_for_secrets(text):
                        issues.append(Issue(ERROR, "SEC-CONTENT", f"{f}:{lineno}", f"looks like a {name}"))
    else:
        issues.append(Issue(WARNING, "SEC-NO-GIT", ".", "not a Git repository; staging checks skipped"))
    return issues


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

def check_dashboard(config: Config, catalog: Catalog | None = None) -> list[Issue]:
    """Separate from check_indexes: rendering the dashboard itself calls check_indexes (no recursion)."""
    from harness.dashboard import render_dashboard

    catalog = catalog or build_catalog(config)
    path = config.rel_path("docs") / "dashboard.md"
    if not path.exists() or path.read_text(encoding="utf-8").replace("\r\n", "\n") != render_dashboard(config, catalog):
        return [Issue(ERROR, "INDEX-STALE", f"{config.get('paths.docs')}/dashboard.md", "stale or missing; run `harness docs index`")]
    return []


def run_all(config: Config, *, scan_tracked: bool = True) -> list[Issue]:
    issues = check_config(config)
    if any(i.code == "CFG-MISSING" for i in issues):
        return issues
    catalog = build_catalog(config)
    issues += check_documents(config, catalog)
    issues += check_entrypoints(config)
    issues += check_indexes(config, catalog)
    issues += check_dashboard(config, catalog)
    issues += check_sensitive(config, scan_tracked=scan_tracked)
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(i.level == ERROR for i in issues)
