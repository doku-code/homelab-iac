"""`harness docs export-wiki`: deterministic Forgejo Wiki export.

The repository remains the source of truth; the export is a derived view
written to a directory that a workflow (or a human) pushes to the wiki Git
repository. The exporter:

* selects documents by configurable include/exclude globs and per-document ``wiki: false``
* flattens paths to wiki page names (``docs/architecture/core.md`` → ``architecture-core``)
* strips YAML frontmatter and renders a compact metadata line instead
* rewrites relative Markdown links and Obsidian ``[[wikilinks]]`` to page links
* generates ``Home.md``, ``_Sidebar.md`` and ``_Footer.md``
* refuses to export anything under the local directory or anything that looks like a secret
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

from harness.core import schema
from harness.core.config import Config
from harness.core.documents import MD_LINK_RE, WIKI_LINK_RE, Catalog, Document, build_catalog, load_document
from harness.core.util import write_text
from harness.validation import scan_text_for_secrets


class WikiExportError(RuntimeError):
    pass


@dataclass
class Page:
    name: str
    source: str
    title: str
    doc_type: str | None
    status: str | None
    content: str


@dataclass
class ExportResult:
    pages: list[Page] = field(default_factory=list)
    written: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)


def glob_to_regex(pattern: str) -> re.Pattern:
    out = "^"
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
            continue
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
            continue
        if c == "*":
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        else:
            out += re.escape(c)
        i += 1
    return re.compile(out + "$")


def page_name(relpath: str, config: Config) -> str:
    docs_dir = (config.get("paths.docs") or "docs").rstrip("/") + "/"
    name = relpath
    if name.startswith(docs_dir):
        name = name[len(docs_dir):]
    if name.lower().endswith(".md"):
        name = name[:-3]
    if name.lower().endswith("/readme"):
        name = name[: -len("/readme")]
    if name.lower() == "readme":
        name = "readme"
    name = name.replace("/", "-")
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    name = re.sub(r"-{2,}", "-", name)
    if name.lower() in ("home", "_sidebar", "_footer"):
        name = f"page-{name.lower()}"
    return name or "page"


def select_documents(config: Config, catalog: Catalog) -> tuple[list[Document], list[tuple[str, str]]]:
    include = [glob_to_regex(g) for g in (config.get("wiki.include") or [])]
    exclude = [glob_to_regex(g) for g in (config.get("wiki.exclude") or [])]
    local_dir = (config.get("paths.local") or ".local").rstrip("/") + "/"
    chosen: list[Document] = []
    skipped: list[tuple[str, str]] = []
    for d in catalog.documents:
        rp = d.relpath
        if rp.startswith(local_dir):
            skipped.append((rp, "local directory"))
            continue
        if not any(rx.match(rp) for rx in include):
            continue
        if any(rx.match(rp) for rx in exclude) and not (config.get("wiki.include_readme") and rp.endswith("README.md")
                                                        and not rp.startswith(local_dir)):
            skipped.append((rp, "excluded by pattern"))
            continue
        if d.error:
            skipped.append((rp, f"parse error: {d.error}"))
            continue
        if d.meta.get("wiki") is False:
            skipped.append((rp, "wiki: false"))
            continue
        if d.type == "index" and rp.endswith(".json"):
            continue
        chosen.append(d)
    return chosen, skipped


def _metadata_line(d: Document) -> str:
    parts = []
    if d.id:
        parts.append(f"**ID:** {d.id}")
    if d.type:
        parts.append(f"**Type:** {d.type}")
    if d.status:
        parts.append(f"**Status:** {d.status}")
    for key in ("priority", "milestone", "technology", "version", "updated"):
        v = d.meta.get(key)
        if v not in (None, "", []):
            parts.append(f"**{key.capitalize()}:** {v}")
    if d.tags:
        parts.append("**Tags:** " + ", ".join(d.tags))
    rel = []
    for fld in schema.ID_RELATION_FIELDS + schema.SCALAR_ID_FIELDS:
        v = d.meta.get(fld)
        if v and fld != "milestone":
            vals = v if isinstance(v, list) else [v]
            rel.append(f"{fld}: " + ", ".join(str(x) for x in vals))
    line = "> " + " · ".join(parts)
    if rel:
        line += "\n> " + " · ".join(rel)
    return line


def _rewrite_links(body: str, doc: Document, name_by_path: dict[str, str], name_by_id: dict[str, str],
                   name_by_title: dict[str, str]) -> str:
    def md_sub(m: re.Match) -> str:
        text, target = m.group(1), m.group(2)
        if target.startswith("#") or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
            return m.group(0)
        clean, _, anchor = unquote(target).partition("#")
        if not clean:
            return m.group(0)
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(doc.relpath), clean)) if not clean.startswith("/") \
            else clean.lstrip("/")
        page = name_by_path.get(resolved)
        if page:
            return f"[{text}]({page}{('#' + anchor) if anchor else ''})"
        if resolved.lower().endswith(".md"):
            return f"{text} _(not published)_"
        return m.group(0)

    def wiki_sub(m: re.Match) -> str:
        target = m.group(1).strip()
        page = name_by_id.get(target) or name_by_title.get(target) or name_by_path.get(target + ".md")
        label = target
        full = m.group(0)
        if "|" in full:
            label = full.rsplit("|", 1)[1].rstrip("]").strip()
        if page:
            return f"[{label}]({page})"
        return label

    body = MD_LINK_RE.sub(md_sub, body)
    body = WIKI_LINK_RE.sub(wiki_sub, body)
    # Strip template guidance comments and derived markers; keep normal HTML comments out of the wiki.
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip() + "\n"


def build_pages(config: Config, catalog: Catalog | None = None) -> tuple[list[Page], list[tuple[str, str]]]:
    catalog = catalog or build_catalog(config)
    chosen, skipped = select_documents(config, catalog)
    name_by_path: dict[str, str] = {}
    used: dict[str, str] = {}
    for d in chosen:
        name = page_name(d.relpath, config)
        if name in used and used[name] != d.relpath:
            name = f"{name}-{abs(hash(d.relpath)) % 10000:04d}"
        used[name] = d.relpath
        name_by_path[d.relpath] = name
    name_by_id = {d.id: name_by_path[d.relpath] for d in chosen if d.id}
    name_by_title = {d.title: name_by_path[d.relpath] for d in chosen}
    pages: list[Page] = []
    for d in chosen:
        if d.has_frontmatter:
            content = _metadata_line(d) + "\n\n" + _rewrite_links(d.body, d, name_by_path, name_by_id, name_by_title)
            if not re.search(r"^# ", content, re.MULTILINE):
                content = f"# {d.title}\n\n" + content
        else:
            content = _rewrite_links(d.body, d, name_by_path, name_by_id, name_by_title)
        hits = scan_text_for_secrets(content)
        if hits:
            raise WikiExportError(f"{d.relpath}: refusing to export; looks like a {hits[0][0]} at line {hits[0][1]}")
        pages.append(Page(name=name_by_path[d.relpath], source=d.relpath, title=d.title, doc_type=d.type,
                          status=d.status, content=content))
    pages.sort(key=lambda p: p.name)
    readme_body = _readme_home_body(config, name_by_path, name_by_id, name_by_title)
    pages.extend(_navigation_pages(config, pages, readme_body))
    return pages, skipped


def _readme_home_body(config: Config, name_by_path, name_by_id, name_by_title) -> str | None:
    """The repository README becomes the top of the Home page (wiki.home_from_readme, default true)."""
    if not config.get("wiki.home_from_readme", True):
        return None
    readme = config.root / "README.md"
    if not readme.exists():
        return None
    doc = load_document(readme, config.root)
    if doc.error:
        return None
    body = _rewrite_links(doc.body, doc, name_by_path, name_by_id, name_by_title)
    if scan_text_for_secrets(body):
        raise WikiExportError("README.md: refusing to export; looks like it contains a secret")
    return body


def _navigation_pages(config: Config, pages: list[Page], readme_body: str | None = None) -> list[Page]:
    title = config.get("wiki.home_title") or f"{config.project_name} documentation"
    groups: dict[str, list[Page]] = {}
    for p in pages:
        groups.setdefault(p.doc_type or "other", []).append(p)
    order = ["overview", "milestone", "task", "decision", "architecture", *schema.REFERENCE_TYPES, "guide", "reference",
             "implementation-report", "testing-report", "investigation", "failed-implementation", "known-issue",
             "deployment", "runbook", "migration", "troubleshooting", "tool", "branch-summary", "commit-record", "index",
             "other"]
    if readme_body:
        home = [readme_body.rstrip("\n"), "", "---", "", f"## {title}: pages", "",
                "Published automatically from the repository by the agent harness. Edit the source",
                "documents in the repository, not this wiki.", ""]
    else:
        home = [f"# {title}", "", "Published automatically from the repository by the agent harness. Edit the source",
                "documents in the repository, not this wiki.", ""]
    sidebar = [f"**{title}**", "", "[Home](Home)", ""]
    for t in order:
        items = groups.get(t)
        if not items:
            continue
        dt = schema.doc_type(t)
        label = (dt.title if dt else t.capitalize()) + ("s" if dt and t in ("milestone", "task", "decision") else "")
        home.append(f"{'###' if readme_body else '##'} {label}")
        home.append("")
        sidebar.append(f"**{label}**")
        for p in sorted(items, key=lambda p: p.name):
            status = f" — {p.status}" if p.status else ""
            home.append(f"- [{p.title}]({p.name}){status}")
            if t != "commit-record":
                sidebar.append(f"- [{p.title}]({p.name})")
        home.append("")
        sidebar.append("")
    footer = "_Generated by `harness docs export-wiki` from the repository. Do not edit wiki pages directly._\n"
    return [
        Page("Home", "<generated>", title, "index", None, "\n".join(home).rstrip("\n") + "\n"),
        Page("_Sidebar", "<generated>", "Sidebar", "index", None, "\n".join(sidebar).rstrip("\n") + "\n"),
        Page("_Footer", "<generated>", "Footer", "index", None, footer),
    ]


def export(config: Config, out_dir: Path, *, dry_run: bool = False, clean: bool = False) -> ExportResult:
    pages, skipped = build_pages(config)
    result = ExportResult(pages=pages, skipped=skipped)
    if dry_run:
        return result
    out_dir.mkdir(parents=True, exist_ok=True)
    produced = set()
    for p in pages:
        target = out_dir / f"{p.name}.md"
        produced.add(target.name)
        if write_text(target, p.content):
            result.written.append(target.name)
    if clean:
        for existing in out_dir.glob("*.md"):
            if existing.name not in produced:
                existing.unlink()
                result.removed.append(existing.name)
    return result


# ---------------------------------------------------------------------------
# Publication (local or CI): git push to the wiki repository, with optional API bootstrap
# ---------------------------------------------------------------------------

import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit


class WikiPublishError(RuntimeError):
    pass


@dataclass
class PublishResult:
    remote: str
    exported: int = 0
    bootstrapped: bool = False
    pushed: bool = False
    changed: bool = False
    dry_run: bool = False
    message: str = ""


def derive_wiki_remote(config: Config) -> str | None:
    """``<origin url without .git>.wiki.git``, or ``wiki.remote`` from configuration."""
    configured = config.get("wiki.remote")
    if configured:
        return str(configured)
    try:
        origin = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(config.root), capture_output=True,
                                text=True, encoding="utf-8").stdout.strip()
    except OSError:
        return None
    if not origin:
        return None
    base = origin[:-4] if origin.endswith(".git") else origin
    return base + ".wiki.git"


def _split_remote(remote: str) -> tuple[str, str, str] | None:
    """(api_base, owner, repo) for an https remote like https://host/owner/repo.wiki.git."""
    parts = urlsplit(remote)
    if parts.scheme not in ("http", "https"):
        return None
    path = parts.path.strip("/")
    if path.endswith(".wiki.git"):
        path = path[: -len(".wiki.git")]
    elif path.endswith(".git"):
        path = path[: -len(".git")]
    segs = path.split("/")
    if len(segs) < 2:
        return None
    owner, repo = segs[-2], segs[-1]
    api_base = urlunsplit((parts.scheme, parts.netloc, "/api/v1", "", ""))
    return api_base, owner, repo


def _git_env(remote: str, token: str | None) -> dict[str, str]:
    """Pass the token to git through the environment, never on the command line or in a URL."""
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if token:
        parts = urlsplit(remote)
        basic = base64.b64encode(f"oauth2:{token}".encode()).decode()
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = f"http.{parts.scheme}://{parts.netloc}/.extraheader"
        env["GIT_CONFIG_VALUE_0"] = f"Authorization: Basic {basic}"
    return env


def _rmtree(path: Path) -> None:
    """Remove a directory tree, clearing the read-only bits Git sets on object files (Windows)."""
    import stat

    def _onerror(func, target, _exc):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:
            pass

    if path.exists():
        shutil.rmtree(path, onerror=_onerror)


def _git(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)


def _api(method: str, url: str, token: str, payload: dict | None = None) -> tuple[int, object]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/json")
    # Reverse proxies in front of Forgejo commonly reject the default "Python-urllib" agent with 403.
    from harness import __version__

    req.add_header("User-Agent", f"agent-harness/{__version__}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, (json.loads(body) if body.strip() else None)
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise WikiPublishError(f"API request failed: {reason}") from exc


def bootstrap_wiki(remote: str, token: str, home_content: str) -> bool:
    """Enable the wiki unit and create the Home page through the Forgejo/Gitea API.

    Returns True when the wiki was initialised, False when it already had pages.
    Verified against Forgejo 17 / Gitea 1.22 API (see REF-forgejo-wiki-api).
    """
    split = _split_remote(remote)
    if split is None:
        raise WikiPublishError(f"cannot derive the API endpoint from remote {remote!r} (https remote required)")
    api_base, owner, repo = split
    repo_url = f"{api_base}/repos/{owner}/{repo}"
    status, info = _api("GET", repo_url, token)
    if status != 200:
        raise WikiPublishError(f"cannot read repository {owner}/{repo} through the API (HTTP {status}); check the token")
    if not (isinstance(info, dict) and info.get("has_wiki")):
        # Enabling the unit needs repository-admin rights (a job token cannot do it).
        status, _ = _api("PATCH", repo_url, token, {"has_wiki": True})
        if status not in (200, 201):
            raise WikiPublishError(f"the wiki is disabled and could not be enabled (HTTP {status}); enable it in the "
                                   "repository settings or use a token with admin rights")
    status, pages = _api("GET", f"{repo_url}/wiki/pages", token)
    if status == 200 and pages:
        return False
    status, _ = _api("POST", f"{repo_url}/wiki/new", token, {
        "title": "Home",
        "content_base64": base64.b64encode(home_content.encode()).decode(),
        "message": "docs: initialise wiki (agent harness)",
    })
    if status not in (200, 201):
        raise WikiPublishError(f"could not create the Home page (HTTP {status})")
    return True


def publish(config: Config, *, remote: str | None = None, token: str | None = None, dry_run: bool = False,
            bootstrap: bool = True, message: str | None = None, work_dir: Path | None = None) -> PublishResult:
    remote = remote or os.environ.get("HARNESS_WIKI_REMOTE") or derive_wiki_remote(config)
    if not remote:
        raise WikiPublishError("no wiki remote: set wiki.remote in harness.yaml, HARNESS_WIKI_REMOTE, or an origin remote")
    result = PublishResult(remote=remote, dry_run=dry_run)
    local = config.root / (config.get("paths.local") or ".local")
    export_dir = local / "wiki-export"
    exported = export(config, export_dir, dry_run=dry_run, clean=True)
    result.exported = len(exported.pages)
    if dry_run:
        result.message = f"would publish {result.exported} pages to {remote}"
        return result

    work = work_dir or (local / "wiki-repo")
    _rmtree(work)
    env = _git_env(remote, token)
    clone = _git(["clone", "--quiet", "--depth", "1", remote, str(work)], config.root, env)
    if clone.returncode != 0:
        if not (bootstrap and token):
            raise WikiPublishError(
                "could not clone the wiki repository. Either the wiki is disabled/uninitialised (provide a token so the "
                "harness can bootstrap it, or create the Home page once in the UI) or the credentials lack access.\n"
                + clone.stderr.strip())
        home = next((p.content for p in exported.pages if p.name == "Home"), "# Home\n")
        result.bootstrapped = bootstrap_wiki(remote, token, home)
        clone = _git(["clone", "--quiet", "--depth", "1", remote, str(work)], config.root, env)
        if clone.returncode != 0:
            raise WikiPublishError("wiki bootstrapped through the API but cloning still fails:\n" + clone.stderr.strip())

    for existing in work.glob("*.md"):
        existing.unlink()
    for page in export_dir.glob("*.md"):
        shutil.copyfile(page, work / page.name)
    _git(["add", "-A"], work, env)
    diff = _git(["diff", "--cached", "--quiet"], work, env)
    if diff.returncode == 0:
        result.message = "wiki already up to date; nothing to publish"
        _rmtree(work)
        return result
    result.changed = True
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(config.root), capture_output=True,
                          text=True, encoding="utf-8").stdout.strip() or "working tree"
    msg = message or f"docs: publish wiki from {head}"
    commit = _git(["-c", "user.name=harness-wiki", "-c", "user.email=harness-wiki@users.noreply.local",
                   "commit", "--quiet", "-m", msg], work, env)
    if commit.returncode != 0:
        raise WikiPublishError("commit in wiki clone failed:\n" + commit.stderr.strip())
    push = _git(["push", "--quiet", "origin", "HEAD"], work, env)
    if push.returncode != 0:
        raise WikiPublishError("push to the wiki repository failed:\n" + push.stderr.strip())
    result.pushed = True
    result.message = f"published {result.exported} pages to {remote}"
    _rmtree(work)
    return result
