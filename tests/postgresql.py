#!/usr/bin/env python3
"""Offline tests for the shared PostgreSQL platform (M007): Patroni role templates, access rules, Make guards.

No infrastructure calls: templates render on localhost, Make runs in a sandbox with a fake tofu.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/patroni_postgresql"
MEMBERS = {"pg-01": "192.168.0.61", "pg-02": "192.168.0.62", "pg-03": "192.168.0.63"}
SYNTHETIC = {name: f"synthetic-{name}-" + "x" * 32 for name in ("SUPERUSER", "REPLICATION", "REWIND", "RESTAPI")}


def render(template, host="pg-02"):
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        # Role defaults go in at the lowest precedence (group "all"), as in a real run.
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        (base / "inventory.json").write_text(json.dumps({"all": {"vars": defaults, "children": {"postgresql": {
            "vars": {"patroni_virtual_ip": "192.168.0.60", "ansible_connection": "local"},
            "hosts": {name: {"ansible_host": ip, "patroni_failover_priority": 1 if name == "pg-03" else 2}
                      for name, ip in MEMBERS.items()}}}}}))
        (base / "render.yml").write_text(yaml.safe_dump([{
            "hosts": host, "gather_facts": False,
            "tasks": [{"ansible.builtin.template": {"src": str(ROLE / "templates" / template), "dest": str(base / "out")}}]}]))
        facts = {"ansible_facts": {"memtotal_mb": 3916, "default_ipv4": {"interface": "eth0"}}}
        result = subprocess.run(
            [str(ROOT / ".venv/bin/ansible-playbook"), "-i", str(base / "inventory.json"), "-e", json.dumps(facts),
             str(base / "render.yml")], capture_output=True, text=True,
            env={**os.environ, "ANSIBLE_NOCOLOR": "1", **{f"PG_{k}_PASSWORD": v for k, v in SYNTHETIC.items()}})
        assert result.returncode == 0, result.stdout + result.stderr
        return (base / "out").read_text()


def test_templates():
    etcd = dict(line.split("=", 1) for line in render("etcd.default.j2").splitlines() if not line.startswith("#"))
    assert etcd["ETCD_NAME"] == "pg-02" and etcd["ETCD_DATA_DIR"] == "/var/lib/etcd/doku-pg"
    assert etcd["ETCD_INITIAL_CLUSTER"] == ",".join(f"{n}=http://{ip}:2380" for n, ip in MEMBERS.items())
    assert etcd["ETCD_LISTEN_CLIENT_URLS"] == "http://192.168.0.62:2379,http://127.0.0.1:2379"

    vip = dict(line.split("=", 1) for line in render("vip-manager.default.j2").splitlines() if not line.startswith("#"))
    assert vip["VIP_IP"] == "192.168.0.60" and vip["VIP_IFACE"] == "eth0" and vip["VIP_HOST"] == "pg-02"
    assert vip["VIP_KEY"] == "/service/doku-pg/leader", "must match Patroni's namespace/scope"
    assert vip["VIP_ENDPOINT"] == ",".join(f"http://{ip}:2379" for ip in MEMBERS.values())

    firewall = render("firewall.nft.j2")
    members = ", ".join(MEMBERS.values())
    assert f"ip saddr {{ {members} }} tcp dport {{ 2379, 2380, 5432, 8008 }} accept" in firewall
    assert "ip saddr { 192.168.0.40/29, 192.168.0.48/31 } tcp dport 5432 accept" in firewall
    assert "tcp dport { 2379, 2380, 5432, 8008 } drop" in firewall and "flush ruleset" not in firewall

    patroni = yaml.safe_load(render("patroni.yml.j2"))
    assert patroni["scope"] == "doku-pg" and patroni["namespace"] == "/service/" and patroni["name"] == "pg-02"
    assert patroni["etcd3"]["hosts"] == [f"{ip}:2379" for ip in MEMBERS.values()]
    assert patroni["restapi"]["listen"] == "192.168.0.62:8008"
    assert patroni["restapi"]["authentication"]["password"] == SYNTHETIC["RESTAPI"]
    pg = patroni["postgresql"]
    assert pg["data_dir"] == "/var/lib/postgresql/17/doku-pg" and pg["bin_dir"] == "/usr/lib/postgresql/17/bin"
    assert pg["authentication"]["superuser"]["password"] == SYNTHETIC["SUPERUSER"]
    assert pg["authentication"]["rewind"]["username"] == "rewinder"
    assert pg["parameters"]["shared_buffers"] == "979MB", "a quarter of the member's memory"
    hba = pg["pg_hba"]
    assert hba[0] == "local all all peer"
    network = hba[1:]
    assert all(rule.startswith("hostssl ") and rule.endswith(" scram-sha-256") for rule in network), "TLS and SCRAM only"
    for ip in MEMBERS.values():
        assert f"hostssl replication replicator {ip}/32 scram-sha-256" in network
    # Applications reach only the database named like their role; the superuser has no network rule at all.
    clients = [rule for rule in network if "192.168.0.4" in rule]
    assert clients == ["hostssl sameuser +app 192.168.0.40/29 scram-sha-256", "hostssl sameuser +app 192.168.0.48/31 scram-sha-256"]
    assert {tuple(rule.split()[1:3]) for rule in network} == {
        ("replication", "replicator"), ("postgres", "rewinder"), ("sameuser", "+app")}
    dcs = patroni["bootstrap"]["dcs"]
    assert dcs == yaml.safe_load(render("dcs.yml.j2")), "bootstrap settings and the applied settings are one source"
    assert dcs["synchronous_mode"] == "quorum" and dcs["failsafe_mode"] is True
    assert dcs["postgresql"]["parameters"]["ssl"] == "on" and dcs["postgresql"]["use_pg_rewind"] is True
    assert patroni["tags"]["failover_priority"] == 2
    assert yaml.safe_load(render("patroni.yml.j2", "pg-03"))["tags"]["failover_priority"] == 1


def test_role():
    tasks = {t["name"]: t for t in yaml.safe_load((ROLE / "tasks/main.yml").read_text())}
    for name in ("Require the cluster credentials from the environment", "Write the Patroni configuration (credentials)"):
        assert tasks[name].get("no_log") is True, name
    config = tasks["Write the Patroni configuration (credentials)"]["ansible.builtin.template"]
    assert config["mode"] == "0600" and config["owner"] == "postgres"
    filesystem = tasks["Create or grow the data filesystem"]["community.general.filesystem"]
    assert filesystem["force"] is False and filesystem["resizefs"] is True, "never re-format existing data"
    assert "Refuse to continue without the data disk" in tasks
    order = list(tasks)
    assert order.index("Keep the Debian package from creating its own database cluster") < order.index(
        "Install PostgreSQL, Patroni, etcd and vip-manager from Debian") > order.index("Mount the data filesystem")
    handlers = {h["name"]: h for h in yaml.safe_load((ROLE / "handlers/main.yml").read_text())}
    assert handlers["Restart etcd"]["throttle"] == 1, "never restart the whole consensus store at once"
    assert handlers["Reload Patroni"]["ansible.builtin.systemd_service"]["state"] == "reloaded", "no restart, no failover"

    apps_text = (ROLE / "tasks/apps.yml").read_text()
    apps = {t["name"]: t for t in yaml.safe_load(apps_text)}
    assert "postgresql_db" in apps_text and "state: absent" in apps_text
    for task in apps.values():
        module = next((k for k in task if k.startswith("community.postgresql.")), None)
        if module and task[module].get("state") == "absent":
            assert module.endswith("postgresql_privs") and task[module]["roles"] == "PUBLIC", "only PUBLIC privileges are removed"
    role = apps["Create the application roles"]
    assert role.get("no_log") is True
    assert "NOSUPERUSER" in role["community.postgresql.postgresql_user"]["role_attr_flags"]
    assert "PG_APP_" in role["community.postgresql.postgresql_user"]["password"]
    listed = yaml.safe_load((ROOT / "ansible/vars/postgresql-apps.yml").read_text())["postgresql_apps"]
    assert all(set(app) == {"name"} for app in listed), "the application list holds names only, never credentials"

    playbook = yaml.safe_load((ROOT / "ansible/playbooks/configure-postgresql.yml").read_text())[0]
    assert playbook["hosts"] == "postgresql" and playbook["roles"] == ["headless_baseline", "patroni_postgresql"]
    assert "serial" not in playbook, "etcd forms only when all members start together"
    main_tf = (ROOT / "terraform/stacks/postgresql/main.tf").read_text()
    assert "prevent_destroy = true" in main_tf, "the members hold data"


def test_make_guards():
    with tempfile.TemporaryDirectory(prefix="postgresql-make-") as directory:
        base = Path(directory)
        shutil.copyfile(ROOT / "Makefile", base / "Makefile")
        (base / "services/windmill").mkdir(parents=True)
        shutil.copyfile(ROOT / "services/windmill/targets.mk", base / "services/windmill/targets.mk")
        (base / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/pve-auth-guard.py", base / "scripts/pve-auth-guard.py")
        (base / ".venv/bin").mkdir(parents=True)
        (base / ".venv/bin/python").symlink_to(sys.executable)
        (base / ".venv/bin/ansible-playbook").write_text(f'#!/bin/sh\necho "ansible $*" >> "{base}/calls.log"\n')
        (base / ".venv/bin/ansible-playbook").chmod(0o755)
        (base / ".infisical.json").write_text('{"workspaceId": "offline"}')
        fake = base / "fake-bin"
        fake.mkdir()
        (fake / "tofu").write_text(f'#!/bin/sh\necho "tofu $*" >> "{base}/calls.log"\necho "{{}}"\n')
        (fake / "tofu").chmod(0o755)
        (base / "terraform/stacks/postgresql").mkdir(parents=True)

        def make(*args, env=None):
            return subprocess.run(["make", "--no-print-directory", *args], cwd=base, capture_output=True, text=True,
                                  env={"PATH": f"{fake}:/usr/bin:/bin", "HOME": str(base), **(env or {})})

        def calls():
            log = base / "calls.log"
            return log.read_text() if log.exists() else ""

        workstation = {"PROXMOX_VE_API_TOKEN": "tofu@pve!mgmt=00000000-0000-0000-0000-000000000000"}
        reviewed = ("postgresql-plan", "POSTGRESQL_ALLOCATION_REVIEWED=yes", "MGMT_INPUT_SOURCE=env")
        assert make("postgresql-plan").returncode != 0
        (base / "terraform/stacks/postgresql/terraform.tfvars").write_text('proxmox_endpoint = "https://192.168.0.10:8006/"\n')
        result = make(*reviewed, env=workstation)
        assert result.returncode != 0 and "POSTGRESQL_NEW_STATE=yes" in result.stderr and calls() == ""
        make(*reviewed, "POSTGRESQL_NEW_STATE=yes", env=workstation)
        assert "-chdir=terraform/stacks/postgresql plan -input=false -out=postgresql.tfplan" in calls()
        assert "-replace" not in calls() and "destroy" not in calls()
        assert "POSTGRESQL_APPLY_APPROVED" in make("postgresql-apply").stderr
        assert "POSTGRESQL_PLAN_SHA256" in make("postgresql-apply", "POSTGRESQL_APPLY_APPROVED=yes").stderr
        assert "apply" not in calls().split("plan")[-1]

        assert "POSTGRESQL_CONFIGURE_APPROVED" in make("postgresql-configure").stderr
        result = make("postgresql-configure", "POSTGRESQL_CONFIGURE_APPROVED=yes")
        assert result.returncode != 0 and "PG_SUPERUSER_PASSWORD" in result.stderr and "ansible" not in calls()
        result = make("postgresql-configure", "POSTGRESQL_CONFIGURE_APPROVED=yes",
                      env={"PG_SUPERUSER_PASSWORD": SYNTHETIC["SUPERUSER"]})
        assert "ansible -i" in calls() and "configure-postgresql.yml" in calls(), result.stderr
        assert SYNTHETIC["SUPERUSER"] not in result.stdout + result.stderr


def main():
    test_templates()
    test_role()
    test_make_guards()
    print("PASS: etcd/vip/firewall/Patroni templates, TLS+SCRAM app-only access, no superuser on the network, "
          "no re-format, nothing dropped, Make guards")


if __name__ == "__main__":
    main()
