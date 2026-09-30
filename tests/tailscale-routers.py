"""Offline router contract tests and disposable mocked Terraform plans only."""
from pathlib import Path
import copy
import os
import shutil
import subprocess
import sys
import tempfile

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/tailscale_subnet_router"


def main():
    tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
    registration = yaml.safe_load((ROLE / "tasks/register.yml").read_text())
    play = yaml.safe_load((ROOT / "ansible/playbooks/configure-tailscale-routers.yml").read_text())[0]
    assert play["serial"] == 1 and play["any_errors_fatal"]
    assert play["vars"]["ansible_ssh_pipelining"] is True
    assert play["vars"]["ansible_connection"] == "ssh"
    assert "StrictHostKeyChecking=yes" in play["vars"]["ansible_ssh_common_args"]
    assert "DEFAULT_KEEP_REMOTE_FILES" in str(play["pre_tasks"])
    assert "tailscale_configure_approved" in str(play["pre_tasks"])
    env = Environment(undefined=StrictUndefined)
    include = next(t for t in tasks if "ansible.builtin.include_tasks" in t)
    condition = env.compile_expression(include["when"])
    assert condition(tailscale_backend_state="NeedsLogin")
    for state in ["Running", "Stopped", "NeedsMachineAuth", "Starting", "NoState"]:
        assert not condition(tailscale_backend_state=state), state
    auth_guard = next(t for t in tasks if t["name"].startswith("Stop for"))
    accepted = env.compile_expression(auth_guard["ansible.builtin.assert"]["that"])
    for state in ["Stopped", "NeedsMachineAuth", "Starting", "NoState"]:
        assert not accepted(tailscale_backend_state=state)
    assert all(t.get("no_log") is True for t in registration)
    reads = [t for t in registration if "infisical.vault.login" in t or "infisical.vault.read_secrets" in t]
    assert len(reads) == 2
    assert all(t["delegate_to"] == "localhost" and t["vars"]["ansible_connection"] == "local" for t in reads)
    login = registration[-1]["ansible.builtin.command"]
    assert "--auth-key=file:/dev/stdin" in login["argv"]
    assert login["stdin"] == "{{ tailscale_bootstrap_secrets.secrets.TS_AUTH_KEY_SUBNET_ROUTER }}"
    assert login["stdin_add_newline"] is False
    assert not any("TS_AUTH_KEY" in arg for arg in login["argv"])
    require_key = env.compile_expression(registration[-2]["ansible.builtin.assert"]["that"][0])
    assert not require_key(tailscale_bootstrap_secrets={"secrets": {}})
    assert not require_key(tailscale_bootstrap_secrets={"secrets": {"TS_AUTH_KEY_SUBNET_ROUTER": ""}})
    assert require_key(tailscale_bootstrap_secrets={"secrets": {"TS_AUTH_KEY_SUBNET_ROUTER": "synthetic-not-a-key"}})
    settings = next(t for t in tasks if t["name"].startswith("Converge subnet"))
    argv = settings["ansible.builtin.command"]["argv"]
    assert argv[:2] == ["/usr/bin/tailscale", "set"]
    assert not any("auth-key" in arg or "force-reauth" in arg for arg in argv)
    required = {"--advertise-routes=192.168.0.0/24", "--accept-routes=false", "--ssh=false", "--snat-subnet-routes=true", "--advertise-exit-node=false"}
    assert required.issubset(argv) and required.issubset(login["argv"])
    desired = dict(AdvertiseRoutes=["192.168.0.0/24"], RouteAll=False, CorpDNS=False,
                   RunSSH=False, NoSNAT=False, ExitNodeID="", ExitNodeIP="", Hostname="ts-router-01", NetfilterMode=2)
    drift = env.compile_expression(settings["when"])
    assert not drift(tailscale_prefs=desired, inventory_hostname="ts-router-01")
    for key, value in dict(AdvertiseRoutes=["0.0.0.0/0"], RouteAll=True, CorpDNS=True,
                          RunSSH=True, NoSNAT=True, ExitNodeID="synthetic", ExitNodeIP="100.64.0.1", Hostname="wrong", NetfilterMode=0).items():
        changed = copy.deepcopy(desired)
        changed[key] = value
        assert drift(tailscale_prefs=changed, inventory_hostname="ts-router-01"), key
    role_source = "\n".join(p.read_text() for p in ROLE.rglob("*.yml"))
    for forbidden in ["tailscaled.state", "force-reauth", "logout", "cacheable: true", "--reset"]:
        assert forbidden not in role_source
    for target in ["tailscale-apply", "tailscale-configure"]:
        result = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True,
                                env={"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]})
        assert result.returncode != 0 and "approve" in result.stdout.lower(), result.stdout
    with tempfile.TemporaryDirectory(prefix="tailscale-offline-") as directory:
        base = Path(directory)
        bin_dir = base / "bin"
        bin_dir.mkdir()
        fake_terraform = bin_dir / "terraform"
        fake_terraform.write_text(f'#!{sys.executable}\n' + '''import json,sys
assert sys.argv[2:] == ["output", "-json", "ansible_inventory"]
json.dump({"tailscale_routers": {"hosts": {
    "ts-router-01": {"ansible_host": "192.168.0.251"},
    "ts-router-02": {"ansible_host": "192.168.0.252"}}}}, sys.stdout)
''')
        fake_terraform.chmod(0o755)
        inspect_inventory = bin_dir / "inspect-inventory"
        inspect_inventory.write_text(f'#!{sys.executable}\n' + f'''import json,os,subprocess,sys
from pathlib import Path
path = Path(sys.argv[sys.argv.index("-i") + 1])
assert path.suffix == ".json" and path.stat().st_mode & 0o077 == 0
assert os.environ["ANSIBLE_HOST_KEY_CHECKING"] == "True"
assert os.environ["ANSIBLE_KEEP_REMOTE_FILES"] == "False"
data = json.loads(subprocess.check_output([{str(ROOT / '.venv/bin/ansible-inventory')!r}, "-i", str(path), "--list"], text=True))
assert set(data["tailscale_routers"]["hosts"]) == {{"ts-router-01", "ts-router-02"}}
assert data["_meta"]["hostvars"]["ts-router-02"]["ansible_host"] == "192.168.0.252"
''')
        inspect_inventory.chmod(0o755)
        subprocess.run(["make", "tailscale-configure", "TAILSCALE_CONFIGURE_APPROVED=yes",
                        f"ANSIBLE={inspect_inventory}"], cwd=ROOT, check=True,
                       env={"PATH": f"{bin_dir}:{os.environ['PATH']}", "HOME": str(base)})
        (base / "keys").mkdir()
        shutil.copyfile(ROOT / "keys/doku-lab-admin.pub", base / "keys/doku-lab-admin.pub")
        src = ROOT / "terraform/stacks/pve-tailscale-routers"
        dst = base / "terraform/stacks/pve-tailscale-routers"
        dst.mkdir(parents=True)
        for path in [*src.glob("*.tf"), src / ".terraform.lock.hcl"]:
            shutil.copyfile(path, dst / path.name)
        shutil.copytree(src / "tests", dst / "tests")
        # Deliberately no operator environment, credentials, backend or private inputs.
        clean = {"PATH": os.environ["PATH"], "HOME": str(base), "TF_IN_AUTOMATION": "1"}
        for args in [["init", "-backend=false", "-input=false", "-lockfile=readonly"], ["validate"], ["test", "-no-color"]]:
            subprocess.run(["terraform", f"-chdir={dst}", *args], env=clean, check=True)
    print("PASS: two-router mock plans, allocation rejection, first-registration/secret guards and idempotent preferences")


if __name__ == "__main__":
    main()
