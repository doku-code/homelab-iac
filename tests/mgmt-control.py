"""Offline tests for the pve-management bootstrap: auth guard, discovery logic and Make guards.

No credentials, no network: Make targets run in a temporary copy with fake terraform/tofu
binaries that only record how they were called.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True  # loading scripts/ must not leave __pycache__ in the repository
TOKEN = "tofu@pve!mgmt=00000000-0000-0000-0000-000000000000"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_auth_guard():
    guard = load("pve_auth_guard", "scripts/pve-auth-guard.py")
    assert guard.check({"PROXMOX_VE_API_TOKEN": TOKEN}) == []
    assert guard.check({}), "missing token must be refused"
    assert guard.check({"PROXMOX_VE_API_TOKEN": "root@pam!x=1"}), "root@pam token must be refused"
    assert guard.check({"PROXMOX_VE_API_TOKEN": "not-a-token"})
    assert guard.check({"PROXMOX_VE_API_TOKEN": TOKEN, "PROXMOX_VE_PASSWORD": "x"}), "password auth must be refused"
    assert guard.check({"PROXMOX_VE_API_TOKEN": TOKEN, "PROXMOX_VE_INSECURE": "true"}), "insecure TLS must be refused"
    assert guard.check({"PROXMOX_VE_API_TOKEN": TOKEN, "TF_LOG": "DEBUG"}), "debug logging must be refused"
    env = guard.child_env({"PROXMOX_VE_API_TOKEN": TOKEN, "INFISICAL_CLIENT_SECRET": "x", "PATH": "/bin"})
    assert "INFISICAL_CLIENT_SECRET" not in env and env["PROXMOX_VE_API_TOKEN"] == TOKEN
    # Problems never echo the secret part of a token.
    for problem in guard.check({"PROXMOX_VE_API_TOKEN": "root@pam!x=SUPERSECRETVALUE"}):
        assert "SUPERSECRETVALUE" not in problem


def test_discovery_logic():
    discover = load("pve_discover", "scripts/pve-discover.py")
    required = discover.required_privileges("pve-management", "local", "local-lvm", "vmbr0")
    assert set(required) == {"/vms", "/nodes/pve-management", "/storage/local", "/storage/local-lvm",
                             "/sdn/zones/localnetwork/vmbr0"}
    assert "Sys.AccessNetwork" in required["/nodes/pve-management"]
    assert "Sys.Modify" not in sum(required.values(), []), "download-url must not require Sys.Modify on /"
    full = {path: {priv: 1 for priv in privs} for path, privs in required.items()}
    assert discover.missing_privileges(required, full) == {}
    partial = dict(full, **{"/vms": {"VM.Audit": 1}})
    assert "VM.Allocate" in discover.missing_privileges(required, partial)["/vms"]
    report = discover.summarize(
        {"version": "9.1.1"}, [{"node": "pve-management", "status": "online"}],
        [{"storage": "local", "type": "dir", "content": "iso,import,vztmpl", "active": 1, "avail": 1},
         {"storage": "local-lvm", "type": "lvmthin", "content": "images,rootdir", "active": 1, "avail": 1}],
        [{"iface": "vmbr0"}], [{"vmid": 101}], "100")
    assert report["standalone"] and report["storages_with_import"] == ["local"] and report["bridges"] == ["vmbr0"]
    assert not discover.summarize({}, [{"node": "pve-core"}, {"node": "pve-lab"}], [], [], [], "100")["standalone"]
    test_discovery_main(discover, required)


def test_discovery_main(discover, required):
    """Drive main() against a mocked API: query parameters, refused endpoints and exit codes."""
    import io
    import json
    import urllib.error
    import urllib.parse
    from unittest import mock

    full = {path: {priv: 1 for priv in privs} for path, privs in required.items()}
    seen = []

    def fake_urlopen(request, context=None, timeout=None):
        assert context is not None and context.verify_mode != 0, "TLS verification must stay enabled"
        assert request.headers["Authorization"] == f"PVEAPIToken={TOKEN}"
        url = urllib.parse.urlparse(request.full_url)
        query = dict(urllib.parse.parse_qsl(url.query))
        api = url.path.split("/api2/json", 1)[1]
        seen.append((api, query))
        if api == "/cluster/status":
            raise urllib.error.HTTPError(request.full_url, 403, "Permission check failed", {}, None)
        data = {
            "/version": {"version": "9.2.26"},
            "/nodes": [{"node": "pve-management"}],
            "/nodes/pve-management/storage": [{"storage": "local", "content": "import,iso"}],
            "/nodes/pve-management/network": [{"iface": "vmbr0"}],
            "/cluster/resources": [],
            "/cluster/nextid": "100",
            "/nodes/pve-management/status": {"cpuinfo": {"model": "Mock CPU", "sockets": 1, "cores": 8, "cpus": 16},
                                             "memory": {"total": 32 * 1024 ** 3, "free": 30 * 1024 ** 3}},
            "/access/permissions": {query.get("path"): full.get(query.get("path"), {})},
        }[api]
        return io.BytesIO(json.dumps({"data": data}).encode())

    argv = ["pve-discover.py", "--endpoint", "https://pve.invalid:8006/", "--image-datastore", "local",
            "--disk-datastore", "local-lvm", "--bridge", "vmbr0"]
    out = io.StringIO()
    with mock.patch.object(sys, "argv", argv), mock.patch.dict(os.environ, {"PROXMOX_VE_API_TOKEN": TOKEN}), \
            mock.patch("urllib.request.urlopen", fake_urlopen), mock.patch("sys.stdout", out):
        assert discover.main() == 0, out.getvalue()
    report = json.loads(out.getvalue())
    assert report["standalone"] and report["missing_privileges"] == {} and report["refused_requests"] == {}
    assert ("/access/permissions", {"path": "/vms"}) in seen
    assert ("/cluster/status", {}) not in seen, "standalone check must not need Sys.Audit on /"
    assert report["host"]["cpu_threads"] == 16 and report["host"]["memory_total_gib"] == 32.0
    assert TOKEN not in out.getvalue()


def make_sandbox(base):
    shutil.copyfile(ROOT / "Makefile", base / "Makefile")
    (base / "services/windmill").mkdir(parents=True)
    shutil.copyfile(ROOT / "services/windmill/targets.mk", base / "services/windmill/targets.mk")
    (base / "scripts").mkdir()
    shutil.copyfile(ROOT / "scripts/pve-auth-guard.py", base / "scripts/pve-auth-guard.py")
    (base / ".venv/bin").mkdir(parents=True)
    (base / ".venv/bin/python").symlink_to(sys.executable)
    (base / ".infisical.json").write_text('{"workspaceId": "offline"}')
    fake = base / "fake-bin"
    fake.mkdir()
    for tool in ("terraform", "tofu"):
        script = fake / tool
        script.write_text(f'#!/bin/sh\necho "{tool} $*" >> "{base}/calls.log"\n')
        script.chmod(0o755)
    for stack in ("pve-lab-controller", "pve-compute-forgejo-runner", "pve-management-control"):
        (base / "terraform/stacks" / stack).mkdir(parents=True)
    return fake


def run_make(base, fake, *args, extra_env=None):
    env = {"PATH": f"{fake}:/usr/bin:/bin", "HOME": str(base)}
    env.update(extra_env or {})
    return subprocess.run(["make", "--no-print-directory", *args], cwd=base, env=env,
                          capture_output=True, text=True)


def calls(base):
    log = base / "calls.log"
    return log.read_text() if log.exists() else ""


def test_make_guards():
    with tempfile.TemporaryDirectory(prefix="mgmt-control-") as directory:
        base = Path(directory)
        fake = make_sandbox(base)

        # A legacy root still pointed at 192.168.0.10 (now pve-management) is refused before Terraform runs.
        (base / "terraform/stacks/pve-lab-controller/terraform.tfvars").write_text(
            'proxmox_endpoint = "https://192.168.0.10:8006/"\n')
        result = run_make(base, fake, "controller-plan", "CONTROLLER_ALLOCATION_REVIEWED=yes")
        assert result.returncode != 0 and "retired host address" in result.stderr, result.stderr
        assert calls(base) == ""

        # The JSON tfvars form is covered too (pve-core-windmill uses terraform.tfvars.json).
        (base / "terraform/stacks/pve-core-windmill").mkdir(parents=True)
        (base / "terraform/stacks/pve-core-windmill/terraform.tfvars.json").write_text(
            '{"proxmox_endpoint": "https://192.168.0.10:8006/"}')
        result = run_make(base, fake, "windmill-plan")
        assert result.returncode != 0 and "retired host address" in result.stderr, result.stderr
        assert calls(base) == ""
        # A legacy root on the current cluster API is not blocked by the guard.
        (base / "terraform/stacks/pve-core-windmill/terraform.tfvars.json").write_text(
            '{"proxmox_endpoint": "https://192.168.0.11:8006/"}')
        run_make(base, fake, "windmill-plan")
        assert "terraform -chdir=terraform/stacks/pve-core-windmill init" in calls(base)
        (base / "calls.log").unlink()

        # Roots recorded on retired pve-compute refuse live operations outright.
        result = run_make(base, fake, "runner-live-plan")
        assert result.returncode != 0 and "retired pve-compute" in result.stderr
        assert calls(base) == ""

        mgmt = base / "terraform/stacks/pve-management-control"
        (mgmt / "terraform.tfvars").write_text('proxmox_endpoint = "https://192.168.0.10:8006/"\n')

        # Plan requires reviewed allocation and an explicit credential source.
        assert run_make(base, fake, "mgmt-plan").returncode != 0
        result = run_make(base, fake, "mgmt-plan", "MGMT_ALLOCATION_REVIEWED=yes")
        assert result.returncode != 0 and "MGMT_INPUT_SOURCE" in result.stderr
        assert calls(base) == ""

        # Without the local state, planning refuses: VM 100 exists, an empty state would recreate it.
        result = run_make(base, fake, "mgmt-plan", "MGMT_ALLOCATION_REVIEWED=yes", "MGMT_INPUT_SOURCE=env",
                          extra_env={"PROXMOX_VE_API_TOKEN": TOKEN})
        assert result.returncode != 0 and "terraform.tfstate" in result.stderr and calls(base) == ""
        (mgmt / "terraform.tfstate").write_text('{"version": 4, "resources": []}\n')

        # A root@pam token is refused by the guard: tofu init may run, tofu plan never does.
        result = run_make(base, fake, "mgmt-plan", "MGMT_ALLOCATION_REVIEWED=yes", "MGMT_INPUT_SOURCE=env",
                          extra_env={"PROXMOX_VE_API_TOKEN": "root@pam!x=1"})
        assert result.returncode != 0 and "dedicated automation identity" in result.stderr, result.stderr
        assert " plan " not in calls(base)

        # With a dedicated token, the plan is saved to a file for exact-plan approval.
        result = run_make(base, fake, "mgmt-plan", "MGMT_ALLOCATION_REVIEWED=yes", "MGMT_INPUT_SOURCE=env",
                          extra_env={"PROXMOX_VE_API_TOKEN": TOKEN})
        assert f"-chdir=terraform/stacks/pve-management-control plan -input=false -out=mgmt.tfplan" in calls(base)
        assert "PROXMOX_VE_API_TOKEN" not in result.stdout + result.stderr and TOKEN not in result.stdout + result.stderr

        # Apply needs explicit approval and the matching plan hash; nothing reaches tofu apply otherwise.
        assert run_make(base, fake, "mgmt-apply", "MGMT_INPUT_SOURCE=env").returncode != 0
        (mgmt / "mgmt.tfplan").write_text("synthetic plan")
        result = run_make(base, fake, "mgmt-apply", "MGMT_APPLY_APPROVED=yes", "MGMT_PLAN_SHA256=" + "0" * 64,
                          "MGMT_INPUT_SOURCE=env", extra_env={"PROXMOX_VE_API_TOKEN": TOKEN})
        assert result.returncode != 0 and " apply " not in calls(base)

        # The state backup refuses without an off-machine destination and recipients.
        assert run_make(base, fake, "mgmt-state-backup").returncode != 0


# `grdctl --system status` output when stdout is not a TTY (gnome-remote-desktop 50.2, src/grd-ctl.c).
GRD_FRESH = """Overall:
\tUnit status: inactive
RDP:
\tStatus: disabled
\tPort: 3389
\tAuthentication methods: credentials
\tTLS certificate: (null)
\tTLS fingerprint: (null)
\tTLS key: (null)
\tKerberos keytab: (null)
\tUsername: (empty)
\tPassword: (empty)
"""
GRD_CONFIGURED = """Overall:
\tUnit status: active
RDP:
\tStatus: enabled
\tPort: 3389
\tAuthentication methods: credentials
\tTLS certificate: /var/lib/gnome-remote-desktop/rdp-tls.crt
\tTLS fingerprint: 00:11:22:33
\tTLS key: /var/lib/gnome-remote-desktop/rdp-tls.key
\tKerberos keytab: (null)
\tUsername: (hidden)
\tPassword: (hidden)
"""


def run_role_playbook(directory, plays, *extra):
    import yaml

    playbook = Path(directory) / "role.yml"
    playbook.write_text(yaml.safe_dump(plays, sort_keys=False))
    env = dict(os.environ, ANSIBLE_ROLES_PATH=str(ROOT / "ansible/roles"), ANSIBLE_LOCALHOST_WARNING="false",
               ANSIBLE_INVENTORY_UNPARSED_WARNING="false", ANSIBLE_NOCOLOR="1")
    return subprocess.run([str(ROOT / ".venv/bin/ansible-playbook"), "-i", "localhost,", "-c", "local", *extra, str(playbook)],
                          env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def test_admin_workstation_role():
    """Catalog sanity, secret handling, idempotency guards, and the RDP status logic evaluated by
    Ansible itself against the real grdctl output format (local asserts only, nothing is changed)."""
    import re
    import yaml

    role = ROOT / "ansible/roles/admin_workstation"
    catalog = yaml.safe_load((role / "defaults/main.yml").read_text())
    assert all(re.fullmatch(r"[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+){2,}", app) for app in catalog["admin_workstation_flatpaks"])
    assert re.fullmatch(r"[0-9a-f]{64}", catalog["admin_workstation_mise_signing_sha256"]), "mise key must be pinned"
    assert len(set(catalog["admin_workstation_apt"])) == len(catalog["admin_workstation_apt"]), "duplicate apt package"
    assert not any(tool.startswith("npm:") for tool in catalog["admin_workstation_mise_tools"]), "use native backends"
    assert catalog["admin_workstation_rdp_allowed_networks"], "RDP must be restricted to listed networks"
    text = (role / "tasks/main.yml").read_text()
    assert not re.search(r"curl[^\n]*\|\s*(ba)?sh", text), "no piped installers"
    tasks = yaml.safe_load(text)
    by_name = {task["name"]: task for task in tasks}

    for task in tasks:
        body = yaml.safe_dump(task)
        if "mgmt_desktop_password" in body or "mgmt_rdp_password" in body:
            command = task.get("ansible.builtin.command")
            if task["name"].startswith(("Set ", "Install ")):
                assert task.get("no_log") is True, task["name"]
            if isinstance(command, dict):
                assert "password" not in yaml.safe_dump(command.get("argv", [])), f"secret in argv: {task['name']}"
        command = task.get("ansible.builtin.command")
        if command is not None:
            assert "changed_when" in task or (isinstance(command, dict) and "creates" in command), task["name"]
            argv = command.get("argv", []) if isinstance(command, dict) else []
            if argv[:1] == ["grdctl"]:
                assert argv[1] == "--system", f"remote login must use system mode: {task['name']}"

    names = [task["name"] for task in tasks]
    assert names.index("Keep SSH reachable independently of RDP") < names.index("Deny other incoming traffic and enable the firewall")
    rdp_rule = by_name["Allow RDP from the trusted management networks only"]["community.general.ufw"]
    assert rdp_rule["port"] == "3389" and "from_ip" in rdp_rule
    playbook = yaml.safe_load((ROOT / "ansible/playbooks/configure-mgmt-control.yml").read_text())[0]
    assert playbook.get("force_handlers") is True, "a rerun must not lose notified handlers"

    def condition(name):
        when = by_name[name].get("when")
        parts = when if isinstance(when, list) else [when]
        return " and ".join(f"({part})" for part in parts)

    def status(output):
        return {"stdout": output, "stdout_lines": output.splitlines(), "rc": 0}

    cert_task = by_name["Point remote login at the TLS certificate and key"]
    checks = []
    for label, output, configured in (("fresh", GRD_FRESH, False), ("configured", GRD_CONFIGURED, True)):
        expect = (lambda expr: f"not ({expr})") if configured else (lambda expr: f"({expr})")
        facts = {"admin_workstation_rdp_status": status(output), "admin_workstation_rdp_final": status(output)}
        for item in cert_task["loop"]:
            checks.append({"name": f"{label}: TLS {item['action']}", "vars": {**facts, "item": item},
                           "ansible.builtin.assert": {"that": [expect(condition(cert_task["name"]))]}})
        for name in ("Set the remote login credentials once", "Enable remote login over RDP"):
            checks.append({"name": f"{label}: {name}", "vars": {**facts, "mgmt_rdp_password": "synthetic-test-only"},
                           "ansible.builtin.assert": {"that": [expect(condition(name))]}})
        checks.append({"name": f"{label}: final verification", "vars": facts, "ansible.builtin.assert": {
            "that": [expect(by_name["Verify the remote login configuration"]["failed_when"])]}})
        # A non-interactive run never sets credentials, and reports the missing ones instead.
        checks.append({"name": f"{label}: no RDP password given", "vars": {**facts, "mgmt_rdp_password": ""},
                       "ansible.builtin.assert": {"that": [f"not ({condition('Set the remote login credentials once')})"]}})
        password = {"stdout": "ubuntu P 2026-11-14 0 99999 7 -1" if configured else "ubuntu L 2026-11-14 0 99999 7 -1"}
        report = by_name["Report credentials that are still unset"]["when"]
        checks.append({"name": f"{label}: report unset credentials", "vars": {**facts,
                       "admin_workstation_password_final": password},
                       "ansible.builtin.assert": {"that": [expect(report)]}})
        # The report names the RDP command whenever the RDP credentials are unset.
        checks.append({"name": f"{label}: report text", "vars": {**facts, "admin_workstation_password_final": password,
                       "admin_workstation_user": "ubuntu", "report_msg": by_name["Report credentials that are still unset"]["ansible.builtin.debug"]["msg"]},
                       "ansible.builtin.assert": {"that": [expect("report_msg is search('rdp set-credentials')")]}})
    defaults = {k: v for k, v in catalog.items() if not k.startswith("admin_workstation_user")}
    with tempfile.TemporaryDirectory(prefix="role-syntax-") as directory:
        # The role itself is only syntax-checked, never executed here.
        syntax = run_role_playbook(directory, [{"hosts": "localhost", "gather_facts": False, "roles": ["admin_workstation"]}],
                                   "--syntax-check")
        assert syntax.returncode == 0, syntax.stdout + syntax.stderr
        logic = run_role_playbook(directory, [{"hosts": "localhost", "gather_facts": False, "vars": defaults, "tasks": checks}])
        assert logic.returncode == 0, logic.stdout + logic.stderr


def main():
    test_auth_guard()
    test_discovery_logic()
    test_make_guards()
    test_admin_workstation_role()
    print("PASS: pve-management auth guard, discovery logic, Make guards and admin workstation role")


if __name__ == "__main__":
    main()
