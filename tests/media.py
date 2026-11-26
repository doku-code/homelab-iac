#!/usr/bin/env python3
"""Offline tests for the media stack (TASK-036): Compose project, firewall, protection of the NAS library,
databases, routes, Make guards. No VM, no network."""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/media_stack"
SECRETS = {name: f"synthetic-{name.lower()}-" + "x" * 32 for name in (
    "MEDIA_ADMIN_PASSWORD", "RADARR_API_KEY", "SONARR_API_KEY", "PROWLARR_API_KEY", "SEERR_API_KEY",
    "PG_APP_SEERR_PASSWORD", "PG_APP_RADARR_PASSWORD", "PG_APP_SONARR_PASSWORD", "PG_APP_PROWLARR_PASSWORD")}
APPLICATIONS = {"jellyfin", "seerr", "radarr", "sonarr", "prowlarr", "qbittorrent"}


def render(template, **extra):
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "out"
        play = Path(directory) / "render.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "gather_facts": False,
            "vars_files": [str(ROLE / "defaults/main.yml"), str(ROOT / "ansible/vars/media.yml")],
            "tasks": [{"ansible.builtin.template": {"src": str(ROLE / "templates" / template), "dest": str(out)}}]}]))
        result = subprocess.run(
            [str(ROOT / ".venv/bin/ansible-playbook"), "-i", "localhost,", "-c", "local", "-e", json.dumps(extra), str(play)],
            capture_output=True, text=True, env={**os.environ, "ANSIBLE_NOCOLOR": "1", **SECRETS})
        assert result.returncode == 0, result.stdout + result.stderr
        return out.read_text()


def test_compose():
    text = render("compose.yml.j2")
    assert not [value for value in SECRETS.values() if value in text], "secrets are read from .env, never written into the project"
    compose = yaml.safe_load(text)
    services = compose["services"]
    assert set(services) == APPLICATIONS and "volumes" not in compose, "no NAS share until its export is set"
    images = yaml.safe_load((ROOT / "ansible/vars/media.yml").read_text())["media_images"]
    for name, service in services.items():
        assert service["image"] == images[name] and re.search(r":v?\d+\.\d+", service["image"]), f"{name}: pinned image"
        assert service["restart"] == "unless-stopped" and service["security_opt"] == ["no-new-privileges:true"]
        assert "privileged" not in service and "network_mode" not in service
    # One tree under one path: imports are hard links. The torrent client sees downloads only.
    assert "/srv/media/data:/data" in services["radarr"]["volumes"] and "/srv/media/data:/data" in services["sonarr"]["volumes"]
    assert services["qbittorrent"]["volumes"][1] == "/srv/media/data/torrents:/data/torrents"
    assert not [v for v in services["prowlarr"]["volumes"] if "/data" in v.split(":")[1]], "Prowlarr needs no media"
    # Jellyfin only plays: the test area is read-only for it, and it has no device without the graphics adapter.
    assert "/srv/media/data/media:/data/media:ro" in services["jellyfin"]["volumes"] and "devices" not in services["jellyfin"]
    assert services["jellyfin"]["user"] == "2000:2000" == services["seerr"]["user"] and services["seerr"]["init"] is True
    # Shared PostgreSQL for the four applications that support it, over TLS; Jellyfin keeps SQLite on the VM.
    seerr = services["seerr"]["environment"]
    assert seerr["DB_TYPE"] == "postgres" and seerr["DB_HOST"] == "192.168.0.60" and seerr["DB_USE_SSL"] == "true"
    assert seerr["DB_PASS"] == "${PG_APP_SEERR_PASSWORD}" and seerr["API_KEY"] == "${SEERR_API_KEY}"
    for name in ("radarr", "sonarr", "prowlarr"):
        environment, prefix = services[name]["environment"], name.upper()
        assert environment[f"{prefix}__POSTGRES__HOST"] == "192.168.0.60" and environment[f"{prefix}__POSTGRES__USER"] == name
        assert environment[f"{prefix}__POSTGRES__MAINDB"] == name and environment[f"{prefix}__POSTGRES__LOGDB"] == f"{name}_log"
        assert environment[f"{prefix}__POSTGRES__PASSWORD"] == f"${{PG_APP_{prefix}_PASSWORD}}"
        assert environment[f"{prefix}__AUTH__APIKEY"] == f"${{{prefix}_API_KEY}}" and environment[f"{prefix}__AUTH__METHOD"] == "Forms"
        assert environment[f"{prefix}__SERVER__URLBASE"] == f"/{name}" and environment["PUID"] == "2000" and environment["UMASK"] == "002"
    assert not [k for k in services["jellyfin"]["environment"] if "POSTGRES" in k or k.startswith("DB_")]


def test_nas_library_is_read_only_and_for_jellyfin_alone():
    compose = yaml.safe_load(render("compose.yml.j2", media_nas_export="/mnt/tank/media"))
    volume = compose["volumes"]["nas-library"]
    options = volume["driver_opts"]["o"].split(",")
    assert volume["driver"] == "local" and volume["driver_opts"]["type"] == "nfs" and volume["driver_opts"]["device"] == ":/mnt/tank/media"
    assert "addr=192.168.0.13" in options and "ro" in options and "rw" not in options, "the share is mounted read-only"
    users = {name for name, service in compose["services"].items() if any(str(v).startswith("nas-library:") for v in service["volumes"])}
    assert users == {"jellyfin"} and "nas-library:/data/nas:ro" in compose["services"]["jellyfin"]["volumes"]
    # A Docker volume, not a directory of the VM: an absent NAS stops Jellyfin instead of showing an empty folder.
    assert not [v for service in compose["services"].values() for v in service["volumes"] if str(v).startswith("/mnt")]
    for name in ("radarr", "sonarr", "qbittorrent", "prowlarr", "seerr"):
        assert not [v for v in compose["services"][name]["volumes"] if "nas" in str(v)], f"{name} has no path to the NAS"


def test_graphics_adapter():
    compose = yaml.safe_load(render("compose.yml.j2", media_gpu=True, media_render_gid=993))
    jellyfin = compose["services"]["jellyfin"]
    assert jellyfin["devices"] == ["/dev/dri/renderD128:/dev/dri/renderD128"] and jellyfin["group_add"] == ["993"]
    assert "privileged" not in jellyfin
    assert not [name for name, service in compose["services"].items() if name != "jellyfin" and "devices" in service]
    tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
    by_name = {task["name"]: task for task in tasks}
    assert by_name["Refuse to continue without the render device"]["when"] == "media_gpu | bool"
    assert "enable_guc=2" in by_name["Load the GuC and HuC firmware"]["ansible.builtin.copy"]["content"], "low-power encoding needs HuC"


def test_firewall_and_disk():
    firewall = render("firewall.nft.j2", media_lan_interface="eth0")
    rules = "\n".join(line for line in firewall.splitlines() if not line.startswith("#"))
    assert "flush ruleset" not in rules, "Docker's rules are left alone"
    assert 'iifname "eth0" ip saddr != { 192.168.0.40/29, 192.168.0.48/31 } tcp dport { 7878, 8989, 9696, 8080 } drop' in firewall
    assert "8096" not in firewall.split("table inet media_stack {")[1] and "5055" not in firewall.split("table inet media_stack {")[1]
    handlers = {h["name"]: h for h in yaml.safe_load((ROLE / "handlers/main.yml").read_text())}
    assert handlers["Reload media firewall"]["ansible.builtin.command"]["argv"] == ["/usr/sbin/nft", "-f", "/etc/nftables.conf"]
    tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
    names = [task["name"] for task in tasks]
    by_name = {task["name"]: task for task in tasks}
    filesystem = by_name["Create or grow the data filesystem"]["community.general.filesystem"]
    assert filesystem["force"] is False and filesystem["resizefs"] is True, "never re-format existing data"
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    assert "scsi1" in defaults["media_data_device"], "the data disk, never the system disk"
    # No data disk, no Docker; and nothing is written below the mount point before it is mounted.
    assert "ConditionPathIsMountPoint={{ media_root }}" in by_name["Tie Docker to the data filesystem"]["ansible.builtin.copy"]["content"]
    assert names.index("Mount the data filesystem") < names.index("Create the configuration and cache directories") < names.index("Start the applications")
    assert names.index("Refuse to continue without the data disk") < names.index("Create or grow the data filesystem")
    for name in ("Write the secrets of the project", "Derive qBittorrent's password line", "Give qBittorrent its first configuration"):
        assert by_name[name].get("no_log") is True, name
    assert by_name["Give qBittorrent its first configuration"]["ansible.builtin.template"]["force"] is False


def test_connections_script():
    text = (ROLE / "files/media-configure.py").read_text()
    compile(text, "media-configure.py", "exec")
    assert '"DELETE"' not in text, "the script creates and connects, it never removes"
    assert "print(PASSWORD" not in text and "print(KEYS" not in text and "redact(text)" in text
    assert 'TEST_MOVIES = os.environ["MEDIA_TEST_MOVIES"]' in text and "/data/nas/" in text
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    assert defaults["media_test_movies"] == "/data/media/test-movies" and defaults["media_test_series"] == "/data/media/test-series"
    assert not [d for d in defaults["media_test_dirs"] if "nas" in d]
    backup = render("media-backup.j2")
    assert "pg_dump" in backup and ".backup" in backup and "umask 077" in backup
    for database in ("seerr", "radarr", "radarr_log", "sonarr", "sonarr_log", "prowlarr", "prowlarr_log"):
        assert f":{database} " in backup + " " or f":{database}" in backup, database


def test_databases_routes_and_names():
    apps = {a["name"]: a for a in yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())["postgresql_apps"]}
    assert {"seerr", "radarr", "sonarr", "prowlarr"} <= set(apps) and "jellyfin" not in apps, "Jellyfin supports SQLite only"
    for name in ("radarr", "sonarr", "prowlarr"):
        assert apps[name]["extra_databases"] == [f"{name}_log"]
    patroni = yaml.safe_load((ROOT / "ansible/roles/patroni_postgresql/defaults/main.yml").read_text())
    assert "192.168.0.80/32" in patroni["patroni_clients"], "media-01 alone, not its range"
    documents = [d for d in yaml.safe_load_all((ROOT / "services/media/access.yaml").read_text()) if d]
    assert all(d["metadata"].get("namespace", "media-edge") == "media-edge" for d in documents if d["kind"] != "Namespace")
    slices = [d for d in documents if d["kind"] == "EndpointSlice"]
    assert {d["metadata"]["name"] for d in slices} == APPLICATIONS and all(d["endpoints"] == [{"addresses": ["192.168.0.80"]}] for d in slices)
    routes = [r for d in documents if d["kind"] == "IngressRoute" for r in d["spec"]["routes"]]
    assert all({"name": "admin-lan"} in r["middlewares"] for r in routes), "LAN only"
    tools = [r for r in routes if "media.doku-lab.net" in r["match"]]
    assert len(tools) == 5 and all({"name": "authentik"} in r["middlewares"] for r in tools), "the tools ask Authentik"
    open_names = {re.search(r"Host\(`([^`]+)`\)", r["match"]).group(1) for r in routes if {"name": "authentik"} not in r["middlewares"]}
    assert open_names == {"jellyfin.doku-lab.net", "seerr.doku-lab.net"}, "only the two applications with their own sign-in"
    rewrites = {r["domain"]: r["answer"] for r in yaml.safe_load((ROOT / "ansible/vars/dns.yml").read_text())["adguard_rewrites"]}
    for name in ("jellyfin", "seerr", "media"):
        assert rewrites[f"{name}.doku-lab.net"] == "192.168.0.45"
    ingress = yaml.safe_load((ROOT / "services/argocd/apps/ingress.yaml").read_text())
    assert {"path": "services/media", "directory": {"include": "access.yaml"}}.items() <= [s for s in ingress["spec"]["sources"] if s.get("path") == "services/media"][0].items()


def test_make_guards():
    makefile = (ROOT / "Makefile").read_text()
    for target, guard in (("media-plan", "MEDIA_ALLOCATION_REVIEWED"), ("media-apply", "MEDIA_APPLY_APPROVED"),
                          ("media-configure", "MEDIA_CONFIGURE_APPROVED"), ("media-gpu-mapping", "MEDIA_GPU_MAPPING_APPROVED"),
                          ("media-secrets", "MEDIA_SECRETS_APPROVED")):
        recipe = re.search(rf"^{target}:\n((?:\t.*\n)+)", makefile, re.M).group(1)
        assert f'test "$({guard})" = yes' in recipe.splitlines()[0], target
    for target in ("media-plan", "media-apply", "media-configure", "media-gpu-mapping", "media-secrets"):
        result = subprocess.run(["make", "-C", str(ROOT), target], capture_output=True, text=True)
        assert result.returncode != 0 and ("pprov" in result.stderr or "Confirm" in result.stderr), target
    mapping = (ROOT / "scripts/pve-gpu-mapping-add.sh").read_text()
    assert "pveum" not in mapping and "shares its IOMMU group" in mapping, "no permission is created; a shared group is refused"
    example = (ROOT / "terraform/stacks/media/terraform.tfvars.example").read_text()
    assert 'node         = "pve-infra"' in example and "192.168.0.80/24" in example and "generic-amd64" in example


def main():
    for test in (test_compose, test_nas_library_is_read_only_and_for_jellyfin_alone, test_graphics_adapter, test_firewall_and_disk,
                 test_connections_script, test_databases_routes_and_names, test_make_guards):
        test()
    print("PASS: six pinned applications, one data tree for hard links, NAS read-only and for Jellyfin alone through a Docker volume, "
          "shared PostgreSQL over TLS for four applications, tools behind Authentik and the firewall, no data disk no Docker, Make guards")


if __name__ == "__main__":
    main()
