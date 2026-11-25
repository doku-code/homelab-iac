#!/usr/bin/env python3
"""Writes the generated parts of the documentation maps (docs/home.md, docs/hubs/*.md; TASK-035).

A map answers one question about the platform (what runs where, what deploys what, which name answers where).
Its tables and diagrams are not typed by hand: each block between

    <!-- map:NAME:start -->
    <!-- map:NAME:end -->

is rewritten from the files that own the facts: the Argo CD applications, the Makefile, the workflows, the DNS
answers, the Authentik blueprints, the front matter of decisions, milestones and tasks, and the inventory page
that `make netbox-docs` writes from NetBox. Nothing is read from a machine, so the result is the same for the
same commit and CI can check it.

  docs-maps.py            rewrite the blocks
  docs-maps.py --check    exit 1 when a block is not what the repository says (nothing is written)
  docs-maps.py --list     the names of the blocks
"""
import argparse
import posixpath
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["docs/home.md", "docs/hubs"]
BLOCK = re.compile(r"(<!-- map:([a-z0-9-]+):start -->\n)(.*?)(<!-- map:\2:end -->)", re.S)
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
HOST_RULE = re.compile(r"Host\(`([a-z0-9.-]+)`\)")
SECRETS_RUN = re.compile(r"^#\s+scripts/secrets\.py run ((?:/\S* )+)-- make ([a-z0-9-]+)", re.M)
HOST_VALUE = re.compile(r"^\s*-? ?host: \"?([a-z0-9.-]+\.[a-z]+)\"?\s*$", re.M)
INVENTORY_PAGE = "docs/reference/infrastructure-inventory.md"
POSTGRESQL_ADDRESS = "192.168.0.60"  # the virtual IP of the Patroni members (ansible/roles/patroni_postgresql)


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def meta(path):
    match = FRONT_MATTER.match(read(path))
    return yaml.safe_load(match.group(1)) if match else {}


def documents(folder, kind=None):
    found = []
    for path in sorted((ROOT / folder).glob("*.md")):
        data = meta(path.relative_to(ROOT))
        if data and (kind is None or data.get("type") == kind):
            found.append((path.relative_to(ROOT).as_posix(), data))
    return found


def cell(value):
    return re.sub(r"\s+", " ", str(value if value is not None else "")).replace("|", "\\|").strip()


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]
    return "\n".join(lines)


def link(text, target, page):
    """A relative link from the page that holds the block to a file of the repository."""
    return f"[{text}]({posixpath.relpath(target, posixpath.dirname(page))})"


def md_tables(path):
    """Every table of a Markdown page as (nearest heading, [row as dict])."""
    heading, header, tables = "", None, []
    for line in read(path).splitlines():
        if line.startswith("#"):
            heading, header = line.lstrip("# ").strip(), None
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header is None:
                header = cells
                tables.append((heading, []))
            elif not set(line) <= set("|-: "):
                tables[-1][1].append(dict(zip(header, cells)))
        else:
            header = None
    return tables


def makefile():
    return read("Makefile")


def make_targets():
    return set(re.findall(r"^([a-z0-9][a-z0-9-]*):", makefile(), re.M))


def secret_paths():
    """Make target -> the paths of the secret store it reads, as the comment above the target says: either the
    command to type (`scripts/secrets.py run /a /b -- make target`) or the sentence "store paths /a, /b and /c"."""
    found = {target: paths.split() for paths, target in SECRETS_RUN.findall(makefile())}
    for comment, target in re.findall(r"((?:^#.*\n)+)([a-z0-9][a-z0-9-]*):", makefile(), re.M):
        prose = re.search(r"store paths? ([^)]*?)\)", comment.replace("\n# ", " "))
        if prose and target not in found:
            found[target] = re.findall(r"/[a-z0-9/-]*", prose.group(1))
    return found


def recipes():
    return {target: body for target, body in re.findall(r"^([a-z0-9][a-z0-9-]*):[^\n]*\n((?:\t[^\n]*\n)*)", makefile(), re.M)}


def make_list(name):
    match = re.search(rf"^{name} := (.*)$", makefile(), re.M)
    return match.group(1).split() if match else []


# --- inventory ----------------------------------------------------------------------------------------------

def inventory():
    devices, guests, cables = [], [], []
    for heading, rows in md_tables(INVENTORY_PAGE):
        if heading == "Devices":
            devices = rows
        elif heading == "Cabling":
            cables = rows
        elif heading.startswith("Cluster "):
            guests += [dict(row, Cluster=heading[len("Cluster "):]) for row in rows]
    return devices, guests, cables


def node_id(name):
    return re.sub(r"[^A-Za-z0-9]", "_", name)


def view_infrastructure_diagram(page):
    devices, guests, cables = inventory()
    by_host = {}
    for guest in guests:
        by_host.setdefault(guest["Host"], []).append(guest)
    lines = ["```mermaid", "flowchart TB"]
    for device in devices:
        name, label = device["Device"], f"{device['Device']} · {device['Address'].split('/')[0]}"
        if device["Role"] == "Hypervisor" or name in by_host:
            lines.append(f'  subgraph {node_id(name)}["{label}"]')
            for guest in by_host.get(name, []):
                lines.append(f'    {node_id(guest["Name"])}["{guest["Name"]}<br/>{guest["Role"]}"]')
            if not by_host.get(name):
                lines.append(f'    {node_id(name)}_empty["no guest of the platform"]')
            lines.append("  end")
        else:
            lines.append(f'  {node_id(name)}["{label}<br/>{device["Role"]}"]')
    for cable in cables:
        ends = [cable["From"].split()[0], cable["To"].split()[0]]
        other = next((end for end in ends if end != "switch"), None)
        if "switch" in ends and other:
            lines.append(f"  switch --- {node_id(other)}")
    lines.append("```")
    return "\n".join(lines)


def view_hosts(page):
    devices, guests, _ = inventory()
    rows = []
    for device in devices:
        own = [g["Name"] for g in guests if g["Host"] == device["Device"]]
        rows.append((f"`{device['Device']}`", device["Role"], device["Model"], device["Address"].split("/")[0],
                     ", ".join(own), device["Description"]))
    return table(["Device", "Role", "Model", "Address", "Guests of the platform", "Notes"], rows)


def view_guests(page):
    _, guests, _ = inventory()
    rows = []
    for guest in guests:
        source = guest["Description"]
        if re.fullmatch(r"terraform/stacks/[a-z0-9-]+", source):
            source = link(f"`{source}`", source, page)
        rows.append((f"`{guest['Name']}`", guest["VMID"], guest["Host"], guest["Role"], guest["Address"].split("/")[0],
                     guest["vCPU"], guest["Memory"], guest["Disk"], guest["Status"], source))
    return table(["Guest", "VMID", "Host", "Role", "Address", "vCPU", "Memory", "Disk", "Status", "Defined by"], rows)


# --- services -----------------------------------------------------------------------------------------------

def applications():
    apps = []
    for path in sorted((ROOT / "services/argocd/apps").glob("*.yaml")):
        app = yaml.safe_load(path.read_text())
        sources = app["spec"].get("sources") or [app["spec"]["source"]]
        folders = []
        for source in sources:
            if source.get("path"):
                folders.append(source["path"])
            for values in (source.get("helm") or {}).get("valueFiles") or []:
                folders.append(values.replace("$values/", "").rsplit("/", 1)[0])
        folder = sorted(set(folders))[0] if folders else None
        sites, database = [], False
        if folder:
            for file in sorted((ROOT / folder).rglob("*.yaml")):
                text = file.read_text()
                database = database or (POSTGRESQL_ADDRESS in text and file.name != "inventory.yaml")
                if file.name.endswith("-routes.yaml"):  # names of machines outside k3s, not sites of this application
                    continue
                sites += HOST_RULE.findall(text) + HOST_VALUE.findall(text)
        apps.append({
            "name": app["metadata"]["name"], "file": path.relative_to(ROOT).as_posix(), "folder": folder,
            "namespace": app["spec"]["destination"]["namespace"],
            "charts": [f"{s['chart']} {s['targetRevision']}" for s in sources if s.get("chart")],
            "sites": list(dict.fromkeys(site for site in sites if not site.endswith("sslip.io"))),
            "database": database,
        })
    return apps


def blueprints():
    """Site -> how Authentik signs people in there."""
    forward = {name.lower() for name in make_list("AUTHENTIK_FORWARD_AUTH")}
    modes = {}
    for path in sorted((ROOT / "services/authentik/blueprints").glob("homelab-*.yaml")):
        name = path.stem[len("homelab-"):]
        for url in re.findall(r"meta_launch_url: https://([a-z0-9.-]+)", path.read_text()):
            modes[url] = "Authentik, in front of the service" if name in forward else "Authentik (OpenID Connect)"
    return modes


def deploy_target(app):
    targets, folder = make_targets(), (app["folder"] or "").rsplit("/", 1)[-1]
    for candidate in (f"{app['name']}-deploy", f"{folder}-deploy"):
        if candidate in targets:
            return candidate
    return None


def view_services(page):
    modes, paths, rows = blueprints(), secret_paths(), []
    for app in applications():
        target = deploy_target(app)
        sign_in = sorted({modes[site] for site in app["sites"] if site in modes})
        database = "shared PostgreSQL" if app["database"] or "/postgresql" in paths.get(target, []) else ""
        rows.append((link(app["name"], app["folder"], page) if app["folder"] else app["name"],
                     ", ".join(f"<https://{site}>" for site in app["sites"]), f"`{app['namespace']}`",
                     ", ".join(app["charts"]) or "manifests of this repository",
                     ", ".join(sign_in) or ("" if not app["sites"] else "its own"), database))
    return table(["Service", "Site", "Namespace", "Chart", "Sign-in", "Database"], rows)


def view_applications(page):
    paths, rows = secret_paths(), []
    for app in applications():
        target = deploy_target(app)
        rows.append((link(app["name"], app["file"], page), link(f"`{app['folder']}`", app["folder"], page) if app["folder"] else "",
                     f"`make {target}`" if target else "nothing: Argo CD needs no Secret for it",
                     ", ".join(f"`{p}`" for p in paths.get(target, []))))
    return table(["Argo CD application", "Values and manifests", "Writes the Secrets, hands over to Argo CD", "Secret store paths"], rows)


def view_roots(page):
    data, targets, bodies = yaml.safe_load(read("services/netbox/inventory.yaml")), make_targets(), recipes()
    _, guests, _ = inventory()
    rows = []
    for root in data["iac_roots"]:
        name = root["root"]
        path = f"terraform/stacks/{name}"
        own = [g["Name"] for g in guests if g["Description"] == path]
        prefix = next((p for p in (f"{name}-cluster", name, name.replace("pve-management-control", "mgmt")) if f"{p}-plan" in targets), None)
        steps = [f"`make {prefix}-{step}`" for step in ("check", "plan", "apply", "configure") if prefix and f"{prefix}-{step}" in targets]
        playbook = re.search(r"ansible/playbooks/([a-z0-9-]+\.yml)", bodies.get(f"{prefix}-configure", ""))
        rows.append((link(f"`{path}`", path, page), ", ".join(own), ", ".join(steps),
                     link(f"`{playbook.group(1)}`", playbook.group(0), page) if playbook else ""))
    return table(["OpenTofu root", "Guests", "Make targets, in order", "Configured by"], rows)


# --- names, identity, secrets -------------------------------------------------------------------------------

def route_files():
    found = {}
    for folder in ("services", "ansible"):
        for file in sorted((ROOT / folder).rglob("*.y*ml")):
            text = file.read_text(errors="ignore")
            for name in HOST_RULE.findall(text) + HOST_VALUE.findall(text):
                found.setdefault(name, file.relative_to(ROOT).as_posix())
    return found


def view_names(page):
    dns = yaml.safe_load(read("ansible/vars/dns.yml"))
    vip = yaml.safe_load(read("ansible/roles/k3s/defaults/main.yml")).get("k3s_vip")
    devices, guests, _ = inventory()
    owners = {d["Address"].split("/")[0]: d["Device"] for d in devices} | {g["Address"].split("/")[0]: g["Name"] for g in guests}
    owners[dns.get("adguard_service_address")] = "dns-01 (AdGuard Home)"
    routes, rows = route_files(), []
    for entry in sorted(dns["adguard_rewrites"], key=lambda e: e["domain"]):
        name, answer = entry["domain"], entry["answer"]
        served = "Traefik on k3s (shared address)" if answer == vip else owners.get(answer, "")
        route = link(f"`{routes[name]}`", routes[name], page) if name in routes else ""
        rows.append((f"`{name}`", answer, served, route))
    return table(["Name", "LAN answer", "Answered by", "Route"], rows)


def view_sign_in(page):
    clients, forward = make_list("AUTHENTIK_CLIENTS"), make_list("AUTHENTIK_FORWARD_AUTH")
    rows = []
    for path in sorted((ROOT / "services/authentik/blueprints").glob("homelab-*.yaml")):
        name = path.stem[len("homelab-"):]
        urls = re.findall(r"meta_launch_url: (https://[a-z0-9.-]+)", path.read_text())
        if name.upper() in clients:
            mode = "OpenID Connect client"
        elif name.upper() in forward:
            mode = "Authentik in front of the service (forward auth)"
        else:
            mode = "shared: groups, outpost"
        rows.append((link(f"`{path.name}`", path.relative_to(ROOT).as_posix(), page), ", ".join(f"<{u}>" for u in urls), mode))
    return table(["Blueprint", "Application", "How"], rows)


def view_secret_paths(page):
    by_path = {}
    for target, paths in secret_paths().items():
        for path in paths:
            by_path.setdefault(path, []).append(target)
    rows = [(f"`{path}`", ", ".join(f"`make {t}`" for t in sorted(set(targets)))) for path, targets in sorted(by_path.items())]
    return table(["Path in the secret store", "Read by"], rows)


# --- CI -----------------------------------------------------------------------------------------------------

def view_workflows(page):
    rows = []
    for path in sorted((ROOT / ".forgejo/workflows").glob("*.yml")):
        flow = yaml.safe_load(path.read_text())
        triggers = flow.get(True, flow.get("on")) or {}  # YAML reads the key `on` as the boolean true
        events = []
        for event, detail in (triggers.items() if isinstance(triggers, dict) else [(t, None) for t in triggers]):
            branches = (detail or {}).get("branches") if isinstance(detail, dict) else None
            events.append(event + (f" to {', '.join(branches)}" if branches else ""))
        jobs = flow.get("jobs", {})
        runners = sorted({str(job.get("runs-on")) for job in jobs.values()})
        gates = sorted(set(re.findall(r"vars\.([A-Z_]+)", path.read_text())))
        rows.append((link(flow.get("name", path.stem), path.relative_to(ROOT).as_posix(), page), ", ".join(events),
                     ", ".join(f"`{r}`" for r in runners), ", ".join(f"`{g}`" for g in gates), ", ".join(jobs)))
    return table(["Workflow", "Runs on", "Runner", "Repository variables that gate it", "Jobs"], rows)


def view_checks(page):
    commands = yaml.safe_load(read("harness.yaml"))["verification"]["commands"]
    rows = [(f"`{c['name']}`", c.get("description", "")) for c in commands]
    return table(["Check", "What it proves"], rows)


# --- decisions, milestones, tasks ---------------------------------------------------------------------------

def view_decisions(page):
    rows = []
    for path, data in documents("docs/decisions", "decision"):
        replaces = ", ".join(data.get("supersedes") or [])
        replaced = ", ".join(data.get("superseded_by") or []) if isinstance(data.get("superseded_by"), list) else (data.get("superseded_by") or "")
        note = "; ".join(x for x in (f"replaces {replaces}" if replaces else "", f"replaced by {replaced}" if replaced else "") if x)
        rows.append((data["id"], link(data["title"], path, page), data.get("status"), data.get("created"), note))
    return table(["ID", "Decision", "Status", "Date", "Notes"], rows)


def view_milestones(page):
    tasks = {data["id"]: (path, data) for path, data in documents("tasks", "task")}
    rows = []
    for path, data in documents("milestones", "milestone"):
        own = [f"{link(t, tasks[t][0], page)} ({tasks[t][1].get('status')})" for t in data.get("related_tasks") or [] if t in tasks]
        rows.append((data["id"], link(data["title"], path, page), data.get("status"), ", ".join(data.get("depends_on") or []), ", ".join(own)))
    return table(["ID", "Milestone", "Status", "After", "Tasks"], rows)


def view_milestone_graph(page):
    lines, classes = ["```mermaid", "flowchart LR"], {}
    found = documents("milestones", "milestone")
    for _, data in found:
        title = data["title"].replace('"', "'")
        lines.append(f'  {data["id"]}["{data["id"]}<br/>{title}"]')
        classes.setdefault(str(data.get("status")), []).append(data["id"])
    for _, data in found:
        for before in data.get("depends_on") or []:
            lines.append(f"  {before} --> {data['id']}")
    styles = {"completed": "fill:#1f5f3a,stroke:#2ea043,color:#fff", "active": "fill:#1f4b7a,stroke:#388bfd,color:#fff"}
    for status, style in styles.items():
        if classes.get(status):
            lines.append(f"  classDef {status} {style}")
            lines.append(f"  class {','.join(classes[status])} {status}")
    lines.append("```")
    return "\n".join(lines)


def view_tasks(page):
    rows = []
    for path, data in documents("tasks", "task"):
        if data.get("status") not in ("completed", "cancelled", "superseded"):
            rows.append((data["id"], link(data["title"], path, page), data.get("status"), data.get("milestone") or "", data.get("updated")))
    return table(["ID", "Task", "Status", "Milestone", "Updated"], rows)


def view_issues(page):
    rows = [(link(data["title"], path, page), data.get("status"), data.get("summary", "")) for path, data in documents("docs/issues")]
    return table(["Known issue", "Status", "Summary"], rows)


def view_maps(page):
    hubs = sorted(documents("docs/hubs"), key=lambda item: (item[1].get("nav_order", 99), item[0]))
    return table(["Map", "Answers"], [(link(data["title"], path, page), data.get("summary", "")) for path, data in hubs])


VIEWS = {name[len("view_"):].replace("_", "-"): function for name, function in sorted(globals().items()) if name.startswith("view_")}


def pages():
    found = []
    for entry in PAGES:
        path = ROOT / entry
        found += sorted(path.glob("*.md")) if path.is_dir() else [path]
    return [p for p in found if p.exists()]


def render(path):
    page = path.relative_to(ROOT).as_posix()

    def block(match):
        name = match.group(2)
        if name not in VIEWS:
            sys.exit(f"{page}: no map block is named {name!r} (known: {', '.join(VIEWS)})")
        return match.group(1) + VIEWS[name](page) + "\n" + match.group(4)

    return BLOCK.sub(block, path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        print("\n".join(VIEWS))
        return
    stale = []
    for path in pages():
        new = render(path)
        if new != path.read_text(encoding="utf-8"):
            stale.append(path.relative_to(ROOT).as_posix())
            if not args.check:
                path.write_text(new, encoding="utf-8")
    if args.check and stale:
        sys.exit("Not what the repository says: " + ", ".join(stale) + ". Run `make docs-maps` and commit the result.")
    print(("stale: " if args.check else "rewritten: ") + (", ".join(stale) or "nothing"))


if __name__ == "__main__":
    main()
