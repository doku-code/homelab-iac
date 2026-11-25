#!/usr/bin/env python3
"""Wiki.js (TASK-029): render the pinned official chart with our values, check the route and the wiring, run
the documentation export on this repository and the configuration tool against an in-memory wiki.

Needs `helm` and the chart download; no cluster, wiki or Forgejo access.
"""
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "services/wiki"
HOST = "wiki.doku-lab.net"
sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


export = load("wiki_export", "scripts/wiki-export.py")
maps = load("docs_maps", "scripts/docs-maps.py")
forgejo = load("forgejo_wiki", "scripts/forgejo-wiki.py")
admin = load("wiki_admin", "scripts/wiki-admin.py")


def recipe(target):
    match = re.search(rf"^{target}:.*\n((?:\t.*\n)+)", (ROOT / "Makefile").read_text(), re.M)
    assert match, target
    return match.group(1)


def chart():
    application = yaml.safe_load((ROOT / "services/argocd/apps/wiki.yaml").read_text())
    source = application["spec"]["sources"][0]
    assert re.fullmatch(r"\d+\.\d+\.\d+", source["targetRevision"]) and source["helm"]["releaseName"] == "wiki"
    assert application["spec"]["syncPolicy"]["automated"] == {"prune": False, "selfHeal": True}
    result = subprocess.run(["helm", "template", "wiki", f"oci://{source['repoURL']}/{source['chart']}", "--version", source["targetRevision"],
                             "--namespace", "wiki", "-f", str(DIR / "values.yaml")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    kinds = [d["kind"] for d in docs]
    assert "Secret" not in kinds, "every credential comes from the Secret made by `make wiki-deploy`"
    assert "StatefulSet" not in kinds and "PersistentVolumeClaim" not in kinds, "no bundled PostgreSQL, no volume: the pages come from Git"
    assert "Ingress" not in kinds and "HTTPRoute" not in kinds, "the route is in access.yaml"
    (deployment,) = [d for d in docs if d["kind"] == "Deployment"]
    assert deployment["spec"]["replicas"] == 1, "one replica per service for now"
    pod = deployment["spec"]["template"]["spec"]
    assert pod["automountServiceAccountToken"] is False, "the wiki needs no Kubernetes credentials"
    (main,) = pod["containers"]
    assert main["image"] == f"ghcr.io/requarks/wiki:{source['targetRevision']}", "image and chart are pinned together"
    assert main["securityContext"]["readOnlyRootFilesystem"] and main["securityContext"]["runAsNonRoot"]
    assert main["resources"]["requests"]["memory"] and main["resources"]["limits"]["memory"]
    assert main["readinessProbe"]["httpGet"]["path"] == "/_ready" and main["livenessProbe"]["httpGet"]["path"] == "/_live"
    references = {(e["valueFrom"]["secretKeyRef"]["name"], e["valueFrom"]["secretKeyRef"]["key"]) for e in main["env"] if "valueFrom" in e}
    assert references == {("wiki-secrets", "db-password"), ("wiki-secrets", "admin-password")}
    written = recipe("wiki-deploy")
    assert "admin-password=%s" in written and "db-password=%s" in written and 'test "$(WIKI_DEPLOY_APPROVED)" = yes' in written
    (config,) = [d for d in docs if d["kind"] == "ConfigMap"]
    settings = yaml.safe_load(config["data"]["config.yml"])
    assert settings["db"]["host"] == "192.168.0.60" and settings["db"]["db"] == "wiki" and settings["db"]["user"] == "wiki"
    assert settings["db"]["ssl"] is True, "the connection to the shared PostgreSQL is encrypted"
    assert settings["offline"] is True, "no update check and no downloads from the internet"
    assert settings["db"]["pass"] == "$(DB_PASS)", "the password is substituted from the Secret when the file is read"
    (service,) = [d for d in docs if d["kind"] == "Service"]
    return service["metadata"]["name"], service["spec"]["ports"][0]["port"]


def access_and_database(service, port):
    docs = {(d["kind"], d["metadata"]["name"]): d for d in yaml.safe_load_all((DIR / "access.yaml").read_text()) if d}
    assert ("Namespace", "wiki") in docs
    assert docs[("Middleware", "admin-lan")]["spec"]["ipAllowList"]["sourceRange"] == ["192.168.0.0/24", "10.42.0.0/16"]
    route = docs[("IngressRoute", "wiki")]["spec"]
    (rule,) = route["routes"]
    assert route["entryPoints"] == ["websecure"] and rule["match"] == f"Host(`{HOST}`)" and route["tls"] == {}
    assert rule["middlewares"] == [{"name": "admin-lan"}], "LAN only"
    assert rule["services"] == [{"name": service, "port": port}], "the route points at the chart's Service"
    apps = yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())["postgresql_apps"]
    assert "wiki" in [a["name"] for a in apps]
    legacy = (ROOT / "services/ingress/legacy-routes.yaml").read_text()
    assert HOST not in legacy and "192.168.0.22" not in legacy, "the route to the old container is gone"
    project = (ROOT / "services/argocd/access.yaml").read_text()
    assert "namespace: wiki}" in project and "ghcr.io/requarks/charts" in project
    assert "wiki-chart" in (ROOT / "services/argocd/values.yaml").read_text()


def exported_tree():
    with tempfile.TemporaryDirectory(prefix="wiki-export-test-") as first, tempfile.TemporaryDirectory(prefix="wiki-export-test-") as second:
        files = export.build(first)
        assert files == export.build(second), "same commit, same tree"
        for name in files:
            assert (Path(first) / name).read_bytes() == (Path(second) / name).read_bytes(), f"{name}: not reproducible"
        assert "README.md" in files and "docs/handoff.md" in files and "tasks.md" in files and "docs/decisions.md" in files
        assert not [f for f in files if f.startswith("docs/archive")], "the archive is not published"
        assert all(f == "README.md" or (f == f.lower() and "_" not in f) for f in files), "paths as the wiki files them"
        pages = {f[:-3] for f in files}
        for name in files:
            text = (Path(first) / name).read_text()
            match = export.FRONT_MATTER.match(text)
            assert match, name
            meta = yaml.safe_load(match.group(1))
            assert meta["editor"] == "markdown", f"{name}: without an editor the wiki keeps the front matter in the body"
            assert meta["title"] and meta["published"] is True and isinstance(meta["tags"], list) and len(meta["description"]) <= 250, name
            body = text[match.end():].lstrip("\n")
            assert body.startswith(f"# {meta['title']}\n"), f"{name}: the first heading is the page title"
            fenced = False
            for line in body.split("\n"):
                if line.lstrip().startswith(("```", "~~~")):
                    fenced = not fenced
                    continue
                if fenced:
                    continue
                for _, link, _ in export.LINK.findall(line):
                    if link.startswith("/"):
                        assert link.split("#")[0].lstrip("/") in pages, f"{name}: {link} leads to no page"
                    else:
                        relative = not re.match(r"[a-z][a-z0-9+.-]*:|#", link, re.I)
                        assert not (relative and link.split("#")[0].endswith(".md")
                                    and (ROOT / Path(name).parent / link.split("#")[0]).exists()), f"{name}: {link} was not rewritten"
    # Link rules on a made-up document.
    pages = {"docs/a.md": "docs/a", "tasks/TASK-001-x.md": "tasks/task-001-x"}
    body = "[t](../tasks/TASK-001-x.md#goal) [d](../tasks/) [s](../Makefile) [e](https://example.org/x.md) [h](#here)\n```\n[c](../tasks/TASK-001-x.md)\n```"
    out = export.rewrite_links(body, "docs/a.md", pages, {"tasks"})
    assert "[t](/tasks/task-001-x#goal)" in out and "[d](/tasks)" in out and f"[s]({export.SOURCE_URL}Makefile)" in out
    assert "[e](https://example.org/x.md)" in out and "[h](#here)" in out and "[c](../tasks/TASK-001-x.md)" in out, "code blocks are left alone"
    assert export.page_path("docs/Some_File.md") == "docs/some-file" and export.page_path("README.md") == "README"
    workflow = (ROOT / ".forgejo/workflows/harness-wiki-publish.yml").read_text()
    assert 'scripts/wiki-export.py --publish "$WIKI_EXPORT_REMOTE"' in workflow and "WIKI_EXPORT_TOKEN: ${{ forgejo.token }}" in workflow
    source = (ROOT / "scripts/wiki-export.py").read_text()
    assert "GIT_CONFIG_VALUE_0" in source and "--force" not in source, "the token travels in the environment; history is kept"


class FakeWiki(admin.Wiki):
    """Answers like the wiki's API for the calls the tool makes; records what was written."""

    def __init__(self):
        super().__init__("https://wiki.test")
        self.site = "site-1"
        self.writes = []
        self.site_settings = {"title": "Default Site", "description": ""}
        self.storage = {"localePrefix": True, "stripLeadingH1": False, "mapReadmeToHome": False, "syncInterval": "5m"}
        self.target = {"id": "git-1", "module": "git", "isEnabled": False, "config": {"authType": "ssh", "repoUrl": "", "syncMode": "sync"},
                       "contentTypes": {"activeTypes": ["pages", "images"]}}
        self.strategies = [{"id": admin.LOCAL_STRATEGY, "module": "local", "displayName": "Local Authentication", "isEnabled": True}]
        self.pages = 0
        self.security = {"trustProxy": False, "disallowIframe": True}

    def call(self, method, path, body=None, expect=(200,)):
        if method != "GET":
            self.writes.append((method, path, body))
        if path == "/_api/sites/site-1" and method == "GET":
            return dict(self.site_settings)
        if path == "/_api/sites/site-1" and method == "PUT":
            self.site_settings.update(body)
            return {"ok": True}
        if path == "/_api/sites/site-1/storage" and method == "GET":
            return {**self.storage, "targets": [dict(self.target)]}
        if path == "/_api/sites/site-1/storage" and method == "PUT":
            (patch,) = body["targets"]
            self.storage.update({k: v for k, v in body.items() if k != "targets"})
            self.target.update(patch)
            return {"ok": True}
        if path == "/_api/system/security" and method == "GET":
            return dict(self.security)
        if path == "/_api/system/security" and method == "PUT":
            self.security = dict(body)
            return {"ok": True}
        if path == "/_api/groups":
            return [{"id": "group-admin", "name": "Administrators"}, {"id": "group-users", "name": "Users"}]
        if path == "/_api/authentication/strategies" and method == "GET":
            return [dict(s, config=dict(s.get("config", {}), clientSecret="********")) for s in self.strategies]
        if path == "/_api/authentication/strategies" and method == "POST":
            self.strategies.append({"id": "oidc-1", **body})
            return {"ok": True, "id": "oidc-1"}
        if path == "/_api/authentication/strategies/oidc-1" and method == "PUT":
            self.strategies[-1].update(body)
            return {"ok": True}
        if path.endswith("/actions/sync"):
            return {"message": "taken up as it stands. Run Import Everything if needed."}
        if path.endswith("/actions/importAll"):
            self.pages = 82
            return {"message": "Imported 82 page(s) and 0 asset(s)."}
        if path == "/_api/system/info":
            return {"pagesTotal": self.pages}
        raise AssertionError(f"unexpected call {method} {path}")


def configuration():
    assert admin.GIT["syncMode"] == "pull" and admin.GIT["branch"] == export.BRANCH, "the wiki only reads, from the branch the export writes"
    assert admin.GIT["repoUrl"].startswith("https://git.doku-lab.net/") and admin.GIT["basicPassword"] == "" and admin.GIT["verifySSL"] is True
    assert admin.STORAGE == {"localePrefix": False, "stripLeadingH1": True, "mapReadmeToHome": True, "syncInterval": "5m"}
    admin.time.sleep = lambda _seconds: None
    wiki = FakeWiki()
    assert "updated" in admin.configure_site(wiki) and wiki.site_settings["title"] == "Doku Lab"
    assert "trustProxy" in admin.configure_security(wiki) and wiki.security == {"trustProxy": True, "disallowIframe": True}, "other settings kept"
    assert "pull wiki" in admin.configure_storage(wiki)
    assert wiki.target["isEnabled"] and wiki.target["config"] == admin.GIT and wiki.target["contentTypes"]["activeTypes"] == ["pages"]
    assert "created" in admin.configure_sso(wiki, "synthetic-secret")
    oidc = wiki.strategies[-1]
    assert oidc["module"] == "oidc" and oidc["autoEnrollGroups"] == ["group-admin"] and oidc["config"]["clientSecret"] == "synthetic-secret"
    assert wiki.site_settings["authStrategies"][0] == {"id": admin.LOCAL_STRATEGY, "order": 0, "isVisible": True}, "the local sign-in stays offered"
    assert "82 pages" in admin.pull(wiki)
    # A second run writes the sign-in method again (its secret cannot be read back) and nothing else.
    wiki.writes.clear()
    assert "unchanged" in admin.configure_site(wiki) and "unchanged" in admin.configure_storage(wiki) and "unchanged" in admin.configure_security(wiki)
    assert wiki.writes == []
    assert "updated" in admin.configure_sso(wiki, "synthetic-secret") and len(wiki.strategies) == 2
    assert 'test "$(WIKI_CONFIGURE_APPROVED)" = yes' in recipe("wiki-configure") and 'test "$(WIKI_PUBLISH_APPROVED)" = yes' in recipe("wiki-publish")
    text = (ROOT / "scripts/wiki-admin.py").read_text()
    assert "print(secret" not in text and "print(password" not in text


def documentation_maps():
    """docs/home.md and docs/hubs say what the repository says, and every block they hold is generated."""
    hubs = sorted((ROOT / "docs/hubs").glob("*.md"))
    assert len(hubs) >= 10 and (ROOT / "docs/home.md").exists()
    orders = []
    for path in maps.pages():
        text = path.read_text()
        assert maps.render(path) == text, f"{path.relative_to(ROOT)}: run `make docs-maps` and commit the result"
        assert text.count(":start -->") == text.count(":end -->") == len(maps.BLOCK.findall(text)), f"{path.name}: a block is not closed"
        if path in hubs:
            orders.append(maps.meta(path.relative_to(ROOT))["nav_order"])
    assert len(set(orders)) == len(orders) == len(hubs), "each map has its own place in the sidebar"
    # What the blocks are built from: a few facts that must hold whatever the repository says today.
    home = (ROOT / "docs/home.md").read_text()
    assert all(f"](hubs/{hub.name})" in home for hub in hubs), "Home lists every map"
    apps = {app["name"]: app for app in maps.applications()}
    assert set(apps) == {p.stem for p in (ROOT / "services/argocd/apps").glob("*.yaml")}
    assert apps["wiki"]["sites"] == [HOST] and apps["wiki"]["database"] and apps["wiki"]["namespace"] == "wiki"
    assert apps["ingress"]["sites"] == [], "the routes to machines outside k3s are not sites of the ingress"
    assert maps.blueprints()[HOST] == "Authentik (OpenID Connect)"
    assert maps.secret_paths()["wiki-deploy"] == ["/wiki", "/postgresql"]
    assert "/switch" in maps.secret_paths()["observability-deploy"], "paths named in a sentence count too"
    assert maps.cell("a | b\n c") == "a \\| b c" and maps.table(["A"], [("x",)]) == "| A |\n|---|\n| x |"
    diagram = maps.view_infrastructure_diagram("docs/home.md")
    assert diagram.startswith("```mermaid\nflowchart TB\n") and diagram.endswith("\n```") and 'subgraph pve_core["pve-core' in diagram
    names = maps.view_names("docs/hubs/network-map.md")
    assert f"| `{HOST}` | 192.168.0.45 | Traefik on k3s (shared address) | [`services/wiki/access.yaml`](../../services/wiki/access.yaml) |" in names
    roots = maps.view_roots("docs/hubs/deployment-map.md")
    assert "`make k3s-cluster-apply`" in roots and "`make k3s-install`" not in roots, "the root's own targets, not the retired lab's"
    for name, view in maps.VIEWS.items():  # nothing of a private file or a secret can reach a map
        assert "terraform.tfvars" not in view("docs/hubs/x.md") and ".local/" not in view("docs/hubs/x.md"), name


def forgejo_wiki():
    """The Forgejo wiki: the harness's pages with Home from docs/home.md and the maps in the sidebar."""
    with tempfile.TemporaryDirectory(prefix="forgejo-wiki-test-") as first, tempfile.TemporaryDirectory(prefix="forgejo-wiki-test-") as second:
        config = forgejo.load_config(ROOT)
        forgejo.wiki.export(config, Path(first), clean=True)
        forgejo.wiki.export(config, Path(second), clean=True)
        files = sorted(p.name for p in Path(first).glob("*.md"))
        assert files == sorted(p.name for p in Path(second).glob("*.md"))
        for name in files:
            assert (Path(first) / name).read_bytes() == (Path(second) / name).read_bytes(), f"{name}: not reproducible"
        pages = {name[:-3] for name in files}
        assert {"Home", "_Sidebar", "_Footer", "All-pages", "handoff", "hubs-infrastructure-map"} <= pages
        assert not [p for p in pages if p.lower() in ("home", "page-home") and p != "Home"], "docs/home.md is published once, as Home"
        home = (Path(first) / "Home.md").read_text()
        assert home.startswith("> Generated from [`docs/home.md`](") and "**ID:**" not in home and "```mermaid" in home
        assert "](hubs-infrastructure-map)" in home and "<!--" not in home
        sidebar = (Path(first) / "_Sidebar.md").read_text()
        hubs = sorted((ROOT / "docs/hubs").glob("*.md"), key=lambda p: maps.meta(p.relative_to(ROOT))["nav_order"])
        listed = re.findall(r"\]\((hubs-[a-z0-9-]+)\)", sidebar)
        assert listed == [f"hubs-{hub.stem}" for hub in hubs], "every map, in its order"
        assert "tasks-TASK" not in sidebar and "decisions-ADR" not in sidebar, "the sidebar is a way in, not the list of every page"
        assert sidebar.index("**Maps**") < sidebar.index("**Start here**") < sidebar.index("**Indexes**") and "](All-pages)" in sidebar
        everything = (Path(first) / "All-pages.md").read_text()
        for name in files:
            text = (Path(first) / name).read_text()
            if not name.startswith(("_", "All-pages", "Home")):
                assert text.startswith(f"> Generated from [`"), f"{name}: every page names its source"
                assert f"]({name[:-3]})" in everything, f"{name}: not in All pages"
            for _, link, _ in forgejo.LINK.findall(forgejo.FENCE.sub("", text)):
                target = link.split("#")[0]
                if target and not re.match(r"[a-z][a-z0-9+.-]*:", link, re.I):
                    assert target in pages, f"{name}: {link} leads to no page"
    # Link rules on a made-up page.
    page = forgejo.wiki.Page("hubs-x", "docs/hubs/x.md", "X", "guide", None,
                             "[p](handoff#now) [f](../../Makefile) [d](../../services/wiki) [e](https://example.org) [n](../nothing.txt)\n```\n[c](../../Makefile)\n```\n")
    out = forgejo.repository_links(page, {"handoff"})
    assert "[p](handoff#now)" in out and f"[f]({forgejo.SOURCE_URL}Makefile)" in out and f"[d]({forgejo.SOURCE_URL}services/wiki)" in out
    assert "[e](https://example.org)" in out and "[n](../nothing.txt)" in out and "```\n[c](../../Makefile)\n```" in out
    workflow = (ROOT / ".forgejo/workflows/harness-wiki-publish.yml").read_text()
    assert "scripts/forgejo-wiki.py --publish" in workflow and "docs-maps.py --check" in workflow and "harness docs publish-wiki" not in workflow
    assert workflow.index("docs-maps.py --check") < workflow.index("HARNESS_WIKI_TOKEN"), "checked before the token is in the environment"
    assert "pull_request" not in yaml.safe_load(workflow).get(True, {}), "never on a pull request"
    assert "scripts/docs-maps.py" in recipe("netbox-docs") and "--check" in recipe("docs-maps-check")


def main():
    service, port = chart()
    access_and_database(service, port)
    exported_tree()
    configuration()
    documentation_maps()
    forgejo_wiki()
    print("PASS: Wiki.js chart pinned with one replica, no volume and no bundled database, encrypted connection to the shared "
          "PostgreSQL, LAN-only route, legacy route removed, reproducible export with wiki front matter and working links, "
          "configuration tool idempotent with pull-only Git storage and the local sign-in kept; documentation maps equal to "
          "the repository; Forgejo wiki reproducible with Home from docs/home.md, the maps in the sidebar and no dead link")


if __name__ == "__main__":
    main()
