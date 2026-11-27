#!/usr/bin/env python3
"""Offline tests for the media services (TASK-036): one container per service, pinned native installs, firewall,
protection of the NAS, connections, routes, Make guards. No container, no network."""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/media_service"
SECRETS = {name: f"synthetic-{name.lower()}-" + "x" * 32 for name in (
    "MEDIA_ADMIN_PASSWORD", "RADARR_API_KEY", "SONARR_API_KEY", "PROWLARR_API_KEY", "SEERR_API_KEY",
    "PG_APP_SEERR_PASSWORD", "PG_APP_RADARR_PASSWORD", "PG_APP_SONARR_PASSWORD", "PG_APP_PROWLARR_PASSWORD")}
SERVICES = {"jellyfin": "192.168.0.81", "seerr": "192.168.0.82", "radarr": "192.168.0.83", "sonarr": "192.168.0.84", "prowlarr": "192.168.0.85"}
VARS = yaml.safe_load((ROOT / "ansible/vars/media.yml").read_text())
DEFAULTS = (ROLE / "defaults/main.yml").read_text()


def render(template, service):
    """Renders one template of the role for one container, with the inventory the OpenTofu root gives."""
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "out"
        inventory = Path(directory) / "inventory.json"
        inventory.write_text(json.dumps({"all": {"children": {"media": {"hosts": {
            name: {"ansible_host": address, "ansible_connection": "local", "media_service": name} for name, address in SERVICES.items()}}}}}))
        play = Path(directory) / "render.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": service, "gather_facts": False,
            "vars_files": [str(ROLE / "defaults/main.yml"), str(ROOT / "ansible/vars/media.yml")],
            "tasks": [{"ansible.builtin.template": {"src": str(ROLE / "templates" / template), "dest": str(out)}}]}]))
        result = subprocess.run([str(ROOT / ".venv/bin/ansible-playbook"), "-i", str(inventory), str(play)],
                                capture_output=True, text=True, env={**os.environ, "ANSIBLE_NOCOLOR": "1", **SECRETS})
        assert result.returncode == 0, result.stdout + result.stderr
        return out.read_text()


def test_pinned_native_installs():
    assert set(VARS["media_versions"]) == set(SERVICES) | {"node"}
    assert set(VARS["media_checksums"]) == {"seerr", "node", "radarr", "sonarr", "prowlarr"}, "every download has its checksum"
    assert all(re.fullmatch(r"[0-9a-f]{64}", value) for value in VARS["media_checksums"].values())
    assert not any("latest" in str(value) for value in VARS["media_versions"].values())
    tasks = {name: (ROLE / f"tasks/{name}.yml").read_text() for name in ("arr", "jellyfin", "seerr")}
    assert tasks["arr"].count("checksum:") == 1 and tasks["seerr"].count("checksum:") == 2
    assert 'name: "jellyfin={{ media_versions.jellyfin }}"' in tasks["jellyfin"] and "selection: hold" in tasks["jellyfin"]
    assert "docker" not in "".join(tasks.values()).lower(), "no container runtime inside the containers"
    assert "qbittorrent" not in DEFAULTS.split("\n", 3)[3] and "qbittorrent" not in "".join(tasks.values()), "qBittorrent is the NAS's own"
    for name in ("radarr", "sonarr", "prowlarr"):
        unit = render("arr.service.j2", name)
        assert "User=media" in unit and "NoNewPrivileges=true" in unit and f"-data=/var/lib/{name}" in unit
    assert "runuser -u {{ media_user }}" in tasks["seerr"] and "become" not in tasks["seerr"], "the containers have no sudo"


def test_settings_and_secrets():
    for name in ("radarr", "sonarr", "prowlarr"):
        text = render("arr.env.j2", name)
        prefix = name.upper()
        settings = dict(line.split("=", 1) for line in text.splitlines() if "=" in line and not line.startswith("#"))
        assert settings[f"{prefix}__POSTGRES__HOST"] == "192.168.0.60" and settings[f"{prefix}__POSTGRES__MAINDB"] == name
        assert settings[f"{prefix}__POSTGRES__LOGDB"] == f"{name}_log" and settings[f"{prefix}__POSTGRES__USER"] == name
        assert settings[f"{prefix}__POSTGRES__PASSWORD"] == SECRETS[f"PG_APP_{prefix}_PASSWORD"]
        assert settings[f"{prefix}__AUTH__APIKEY"] == SECRETS[f"{prefix}_API_KEY"][:32], "exactly 32 characters"
        assert settings[f"{prefix}__AUTH__METHOD"] == "Forms" and settings[f"{prefix}__SERVER__URLBASE"] == f"/{name}"
        assert settings[f"{prefix}__UPDATE__AUTOMATICALLY"] == "False", "versions change in Git"
    seerr = dict(line.split("=", 1) for line in render("seerr.env.j2", "seerr").splitlines() if "=" in line and not line.startswith("#"))
    assert seerr["DB_TYPE"] == "postgres" and seerr["DB_HOST"] == "192.168.0.60" and seerr["DB_USE_SSL"] == "true"
    assert seerr["DB_PASS"] == SECRETS["PG_APP_SEERR_PASSWORD"] and seerr["CONFIG_DIRECTORY"] == "/var/lib/seerr"
    # No secret has a value in Git: the role reads them from the environment and writes them root-only.
    assert DEFAULTS.count("lookup('ansible.builtin.env'") == 9
    for tasks in ("arr", "seerr"):
        text = (ROLE / f"tasks/{tasks}.yml").read_text()
        block = text[text.index("- name: Write the settings"):text.index("- name: Write the unit")]
        assert 'mode: "0600"' in block and "no_log: true" in block


def test_firewall():
    lan, tools = "192.168.0.0/24", {"radarr": 7878, "sonarr": 8989, "prowlarr": 9696}
    for name, port in {"jellyfin": 8096, "seerr": 5055}.items():
        text = render("firewall.nft.j2", name)
        assert "policy drop" in text and f"ip saddr {lan} tcp dport {port} accept" in text, "their own sign-in, for the LAN"
    for name, port in tools.items():
        text = render("firewall.nft.j2", name)
        (rule,) = [line for line in text.splitlines() if f"tcp dport {port} accept" in line]
        sources = set(re.search(r"\{ (.+) \}", rule).group(1).split(", "))
        assert sources == {"192.168.0.40/29", "192.168.0.48/31", "192.168.0.39/32"} | {f"{a}/32" for a in SERVICES.values()}, sources
        assert lan not in rule, "the tools answer Traefik (after Authentik), each other and the workstation only"
        assert f"ip saddr {lan} tcp dport 22 accept" in text and "8080" not in text


def test_the_nas_is_never_writable():
    script = (ROOT / "scripts/pve-media-mounts.sh").read_text()
    lines = [line for line in script.splitlines() if not line.lstrip().startswith("#")]
    fstab = next(line for line in lines if " nfs " in line)
    assert " nfs ro," in fstab and "nofail" in fstab, "mounted read-only on the node, which boots without the NAS"
    assert 'grep -qx ro || { echo "$point is not read-only"' in script, "refuses a share that came up writable"
    assert "chattr +i" in script, "nothing is written under an absent share"
    nas_mounts = re.findall(r'-mp\d "\$(library|downloads),mp=[^"]+"', script)
    assert sorted(nas_mounts) == ["downloads", "library"]
    assert all(",ro=1" in m for m in re.findall(r'-mp\d "\$(?:library|downloads)[^"]+"', script)), "bound read-only into the containers"
    jellyfin = next(line for line in lines if line.startswith('configure "$jellyfin"'))
    assert '"$area,mp=/data/media,ro=1"' in jellyfin and "-dev0" in jellyfin and "$downloads" not in jellyfin, "Jellyfin only reads"
    tools = next(line for line in lines if '-mp1 "$area,mp=/data/media"' in line)
    assert "$library" not in tools, "Radarr and Sonarr never see the Plex library"
    assert not re.search(r"\b(pct destroy|qm destroy|rm -rf|pveum)\b", script)
    # Jellyfin refuses to start on an empty library instead of dropping it from its database.
    jellyfin_tasks = (ROLE / "tasks/jellyfin.yml").read_text()
    assert "ExecStartPre=" in jellyfin_tasks and "is empty: the NAS share is not mounted" in jellyfin_tasks
    assert [library["path"] for library in VARS["media_nas_libraries"]] == ["Movies", "Series", "Animes"]


def test_connections():
    script = (ROOT / "scripts/media-connect.py").read_text()
    assert '"removeCompletedDownloads": False, "removeFailedDownloads": False' in script, "nothing is removed from the operator's qBittorrent"
    assert "SECRETS = [PASSWORD, QBIT_PASSWORD, *KEYS.values()]" in script and "redact(text)" in script
    assert 'os.environ["MEDIA_QBIT_URL"]' in script and "127.0.0.1:8080" not in script
    assert '"inside": "http://radarr:7878/radarr"' in script, "the applications reach each other by container name"
    hosts = (ROLE / "tasks/main.yml").read_text()
    assert "path: /etc/hosts" in hosts and "/etc/.pve-ignore.hosts" in hosts
    compiled = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "py_compile", str(ROOT / "scripts/media-connect.py")], capture_output=True)
    assert compiled.returncode == 0


def test_databases_routes_and_names():
    patroni = yaml.safe_load((ROOT / "ansible/roles/patroni_postgresql/defaults/main.yml").read_text())
    assert {"192.168.0.82/31", "192.168.0.84/31"} <= set(patroni["patroni_clients"]), "the four containers with a database, not the range"
    assert "192.168.0.80/32" not in patroni["patroni_clients"], "the retired VM is no client any more"
    apps = yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())
    names = json.dumps(apps)
    assert all(name in names for name in ("seerr", "radarr_log", "sonarr_log", "prowlarr_log")) and "jellyfin" not in names
    documents = list(yaml.safe_load_all((ROOT / "services/media/access.yaml").read_text()))
    slices = {d["metadata"]["name"]: d["endpoints"][0]["addresses"] for d in documents if d["kind"] == "EndpointSlice"}
    assert slices == {name: [address] for name, address in SERVICES.items()}, slices
    assert not any("qbittorrent" in json.dumps(d) for d in documents), "qBittorrent has no route here"
    routes = [route for d in documents if d["kind"] == "IngressRoute" for route in d["spec"]["routes"]]
    assert all({"name": "admin-lan"} in route["middlewares"] for route in routes), "LAN only"
    tools = [route for route in routes if "media.doku-lab.net" in route["match"]]
    assert len(tools) == 4 and all({"name": "authentik"} in route["middlewares"] for route in tools), "the tools ask Authentik"
    open_names = {re.search(r"Host\(`([^`]+)`\)", r["match"]).group(1) for r in routes if {"name": "authentik"} not in r["middlewares"]}
    assert open_names == {"jellyfin.doku-lab.net", "seerr.doku-lab.net"}
    dns = (ROOT / "ansible/vars/dns.yml").read_text()
    assert all(f"domain: {name}.doku-lab.net, answer: 192.168.0.45" in dns for name in ("jellyfin", "seerr", "media"))


def test_make_guards():
    makefile = (ROOT / "Makefile").read_text()
    for gate in ("MEDIA_APPLY_APPROVED", "MEDIA_CONFIGURE_APPROVED", "MEDIA_MOUNTS_APPROVED", "MEDIA_CONNECT_APPROVED", "MEDIA_SECRETS_APPROVED"):
        assert f'test "$({gate})" = yes' in makefile, gate
    env = {key: value for key, value in os.environ.items() if not key.startswith("MEDIA_")}
    for target in ("media-apply", "media-configure", "media-mounts", "media-connect"):
        result = subprocess.run(["make", "-C", str(ROOT), target], capture_output=True, text=True, env=env)
        assert result.returncode != 0 and "APPROVED=yes" in result.stderr, target
    backup = (ROOT / "scripts/media-backup.sh").read_text()
    assert backup.count("pg_dump") == 2 and "sqlite3" in backup and "PGSSLMODE=require" in backup
    assert not (ROOT / "ansible/roles/media_stack").exists(), "the Compose role is gone with the VM's stack"


def main():
    tests = [test_pinned_native_installs, test_settings_and_secrets, test_firewall, test_the_nas_is_never_writable,
             test_connections, test_databases_routes_and_names, test_make_guards]
    for test in tests:
        test()
    print(f"PASS: {len(tests)} tests: pinned native installs, settings without secrets in Git, firewall per container, "
          "NAS read-only at every layer, connections, databases and routes, Make guards")


if __name__ == "__main__":
    main()
