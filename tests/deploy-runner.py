"""Offline tests for the bootstrap deployment runner (ADR-014, M003).

Covers the main-only wrapper end to end against a local Git "Forgejo" and a fake tofu, the deploy_runner
role's credential handling, the workflow trust boundary (validation never reaches the deploy label or
its credentials) and the deploy-runner-* Make guards. No credentials, no network.
"""

import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
ROLE = ROOT / "ansible/roles/deploy_runner"
WRAPPER = ROLE / "files/homelab-deploy"
TOKEN = "deploy-runner@pve!ci=00000000-0000-0000-0000-000000000000"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}


def load_wrapper():
    loader = importlib.machinery.SourceFileLoader("homelab_deploy", str(WRAPPER))
    spec = importlib.util.spec_from_loader("homelab_deploy", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def expect_refused(wrapper, function, *args):
    try:
        function(*args)
    except wrapper.Refused as error:
        return str(error)
    raise AssertionError(f"{function.__name__}{args} was not refused")


def test_wrapper_validation(wrapper):
    roots = {"ci-disposable": {}}
    commit, sha = "a" * 40, "b" * 64
    assert wrapper.parse_request(["ci-disposable", "plan", commit], roots) == ("ci-disposable", "plan", commit)
    assert wrapper.parse_request(["ci-disposable", "plan-destroy", commit], roots)[1] == "plan-destroy"
    assert wrapper.parse_request(["ci-disposable", "apply", sha], roots)[2] == sha
    assert wrapper.parse_request(["ci-disposable", "show"], roots) == ("ci-disposable", "show", None)
    for argv in (["deploy-runner", "plan", commit],            # not on the allowlist (workstation-only root)
                 ["../ci-disposable", "plan", commit],          # path tricks
                 ["ci-disposable", "destroy", commit],          # no direct destroy
                 ["ci-disposable", "plan", "main"],             # refs are not accepted, only full commits
                 ["ci-disposable", "plan", commit[:12]],
                 ["ci-disposable", "apply", commit],            # apply takes a plan hash, not a commit
                 ["ci-disposable", "show", sha], ["ci-disposable", "plan"],
                 ["ci-disposable", "plan", commit, "extra"], []):
        expect_refused(wrapper, wrapper.parse_request, argv, roots)

    with tempfile.TemporaryDirectory() as directory:
        env_file = Path(directory) / "proxmox.env"
        env_file.write_text(f"# scoped\nPROXMOX_VE_API_TOKEN={TOKEN}\n")
        assert wrapper.load_credentials(env_file) == {"PROXMOX_VE_API_TOKEN": TOKEN}
        env_file.write_text(f"PROXMOX_VE_API_TOKEN={TOKEN}\nTF_LOG=TRACE\n")
        expect_refused(wrapper, wrapper.load_credentials, env_file)
        env_file.write_text("\n")
        expect_refused(wrapper, wrapper.load_credentials, env_file)
        expect_refused(wrapper, wrapper.load_credentials, Path(directory) / "missing.env")

    now = datetime.now(timezone.utc)
    meta = {"operation": "plan", "sha256": sha, "commit": commit, "created": now.isoformat()}
    assert wrapper.check_plan(meta, sha, sha, now, 24) == commit
    expect_refused(wrapper, wrapper.check_plan, None, sha, sha, now, 24)
    expect_refused(wrapper, wrapper.check_plan, meta, "c" * 64, sha, now, 24)       # another plan requested
    expect_refused(wrapper, wrapper.check_plan, meta, sha, "c" * 64, now, 24)       # plan file changed after review
    expect_refused(wrapper, wrapper.check_plan, {**meta, "operation": "applied"}, sha, sha, now, 24)  # no replay
    expect_refused(wrapper, wrapper.check_plan, meta, sha, sha, now + timedelta(hours=25), 24)      # expired

    env = wrapper.tofu_env(Path("/b"), "ci-disposable", Path("/h"), "/etc/homelab-deploy/tofurc", {})
    assert set(env) == {"PATH", "HOME", "TMPDIR", "LANG", "TF_IN_AUTOMATION", "TF_INPUT", "TF_CLI_CONFIG_FILE",
                        "TF_DATA_DIR", "TF_PLUGIN_CACHE_DIR"}
    assert WRAPPER.read_text().startswith("#!/usr/bin/python3 -I\n"), "isolated mode: no user site, no PYTHON* env"


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, env={**os.environ, **GIT_ENV}, check=True,
                          capture_output=True, text=True).stdout.strip()


def test_wrapper_end_to_end(wrapper):
    """plan -> review -> operator approval -> apply, from the main tip; everything else is refused."""
    with tempfile.TemporaryDirectory(prefix="deploy-runner-") as directory:
        tmp = Path(directory)
        forgejo = tmp / "forgejo"
        (forgejo / "terraform/stacks/ci-disposable").mkdir(parents=True)
        (forgejo / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/pve-auth-guard.py", forgejo / "scripts/pve-auth-guard.py")
        (forgejo / "terraform/stacks/ci-disposable/main.tf").write_text("# probe\n")
        git(forgejo, "init", "--quiet", "--initial-branch=main")
        git(forgejo, "add", "-A")
        git(forgejo, "commit", "--quiet", "-m", "first")
        old_main = git(forgejo, "rev-parse", "HEAD")
        (forgejo / "terraform/stacks/ci-disposable/main.tf").write_text("# probe v2\n")
        git(forgejo, "commit", "--quiet", "-am", "second")
        main_commit = git(forgejo, "rev-parse", "HEAD")
        git(forgejo, "checkout", "--quiet", "-b", "feature")
        (forgejo / "terraform/stacks/ci-disposable/main.tf").write_text("# unreviewed change\n")
        git(forgejo, "commit", "--quiet", "-am", "feature")
        branch_commit = git(forgejo, "rev-parse", "HEAD")
        git(forgejo, "checkout", "--quiet", "main")

        log = tmp / "tofu.log"
        fake_tofu = tmp / "tofu"
        fake_tofu.write_text(
            "#!/bin/sh\n"
            f'echo "$* token=${{PROXMOX_VE_API_TOKEN:+set}} home=$HOME cli=$TF_CLI_CONFIG_FILE" >> "{log}"\n'
            'for a in "$@"; do case "$a" in -out=*) echo "plan for $(pwd) $*" > "${a#-out=}";; esac; done\n')
        fake_tofu.chmod(0o755)
        creds = tmp / "proxmox.env"
        creds.write_text(f"PROXMOX_VE_API_TOKEN={TOKEN}\n")
        approvals = tmp / "approvals"
        approvals.mkdir(mode=0o755)
        approvals.chmod(0o755)
        base = tmp / "base"
        base.mkdir()
        config = {"repository": str(forgejo), "branch": "main", "base": str(base), "credentials": str(creds),
                  "approvals": str(approvals), "approval_owner_uid": os.getuid(), "tofu_cli_config": "/dev/null",
                  "tofu": str(fake_tofu), "roots": {"ci-disposable": {"var_file": "/etc/homelab-deploy/roots/x.tfvars"}}}

        def calls():
            return log.read_text() if log.exists() else ""

        def applies():
            return len([line for line in calls().splitlines() if " apply " in line])

        def approve(sha, mode=0o644):
            path = approvals / "ci-disposable.sha256"
            path.write_text(sha + "\n")
            path.chmod(mode)

        # A branch commit, or an older main commit (e.g. one later reverted), never plans.
        for commit in (branch_commit, old_main):
            message = expect_refused(wrapper, wrapper.run, config, ["ci-disposable", "plan", commit])
            assert "not the current tip of main" in message and calls() == "", message
        # A held lock refuses a second deployment.
        with open(base / "lock", "a") as held:
            import fcntl
            fcntl.flock(held, fcntl.LOCK_EX)
            assert "another deployment" in expect_refused(wrapper, wrapper.run, config, ["ci-disposable", "plan", main_commit])

        # The main tip plans; credentials reach plan, not init; HOME is a fresh, removed per-run directory.
        assert wrapper.run(config, ["ci-disposable", "plan", main_commit]) == 0
        plan_line = [line for line in calls().splitlines() if " plan " in line][0]
        assert "-out=" in plan_line and "-var-file=/etc/homelab-deploy/roots/x.tfvars" in plan_line
        assert "token=set" in plan_line and "cli=/dev/null" in plan_line
        init_line = [line for line in calls().splitlines() if " init " in line][0]
        assert "token=set" not in init_line and f"-backend-config=path={base}/state/ci-disposable.tfstate" in init_line
        assert list((base / "tmp").iterdir()) == [], "per-run HOME and clone must be removed"
        meta = json.loads((base / "plans/ci-disposable.json").read_text())
        assert meta["commit"] == main_commit and meta["operation"] == "plan"
        sha = meta["sha256"]

        # show needs no credentials; the job can trigger apply, but without the operator's approval it is refused.
        assert wrapper.run(config, ["ci-disposable", "show"]) == 0
        assert "token=set" not in [line for line in calls().splitlines() if " show " in line][0]
        assert "no operator approval" in expect_refused(wrapper, wrapper.run, config, ["ci-disposable", "apply", sha])
        approve("f" * 64)
        assert "different plan" in expect_refused(wrapper, wrapper.run, config, ["ci-disposable", "apply", sha])
        approve(sha, mode=0o666)
        assert "not writable" in expect_refused(wrapper, wrapper.run, config, ["ci-disposable", "apply", sha])
        approve(sha)
        expect_refused(wrapper, wrapper.run, config, ["ci-disposable", "apply", "0" * 64])
        later = datetime.now(timezone.utc) + timedelta(hours=25)
        assert "older than" in expect_refused(wrapper, wrapper.run, config, ["ci-disposable", "apply", sha], later)
        assert applies() == 0
        assert wrapper.run(config, ["ci-disposable", "apply", sha]) == 0
        assert applies() == 1
        expect_refused(wrapper, wrapper.run, config, ["ci-disposable", "apply", sha])  # no replay
        assert applies() == 1

        # A plan whose commit leaves main (force-push) is not applied, even if approved.
        assert wrapper.run(config, ["ci-disposable", "plan-destroy", main_commit]) == 0
        assert [line for line in calls().splitlines() if " plan " in line][-1].count("-destroy") == 1
        destroy_sha = json.loads((base / "plans/ci-disposable.json").read_text())["sha256"]
        approve(destroy_sha)
        git(forgejo, "reset", "--quiet", "--hard", old_main)
        (forgejo / "README").write_text("rewritten\n")
        git(forgejo, "add", "README")
        git(forgejo, "commit", "--quiet", "-m", "rewritten history")
        assert "not on main" in expect_refused(wrapper, wrapper.run, config, ["ci-disposable", "apply", destroy_sha])
        assert applies() == 1


def test_config_template():
    """config.json.j2 renders to the shape the wrapper reads."""
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "config.json"
        play = Path(directory) / "render.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "gather_facts": False, "vars_files": [str(ROLE / "defaults/main.yml")],
            "tasks": [{"ansible.builtin.template": {"src": str(ROLE / "templates/config.json.j2"), "dest": str(out)}}]}]))
        result = subprocess.run([str(ROOT / ".venv/bin/ansible-playbook"), "-i", "localhost,", "-c", "local", str(play)],
                                capture_output=True, text=True, env={**os.environ, "ANSIBLE_NOCOLOR": "1"})
        assert result.returncode == 0, result.stdout + result.stderr
        config = json.loads(out.read_text())
    assert config["roots"] == {"ci-disposable": {"var_file": "/etc/homelab-deploy/roots/ci-disposable.tfvars"}}
    assert config["approvals"] == "/etc/homelab-deploy/approvals" and config["tofu_cli_config"] == "/etc/homelab-deploy/tofurc"
    assert config["credentials"] == "/etc/homelab-deploy/proxmox.env" and config["max_plan_age_hours"] == 24
    assert "tofu" not in config and "approval_owner_uid" not in config, "production uses the safe defaults"


def tasks():
    return yaml.safe_load((ROLE / "tasks/main.yml").read_text())


def test_role():
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    ct301 = yaml.safe_load((ROOT / "ansible/roles/forgejo_runner/defaults/main.yml").read_text())
    assert defaults["deploy_runner_version"] == ct301["forgejo_runner_version"]
    assert defaults["deploy_runner_checksum"] == ct301["forgejo_runner_checksum"]
    assert re.fullmatch(r"[0-9a-f]{64}", defaults["opentofu_sha256"])
    assert defaults["deploy_runner_proxmox_user"] == "deploy-runner@pve"
    assert all(re.fullmatch(r"https://192\.168\.0\.(10|11):8006/", r["proxmox_endpoint"])
               for r in defaults["deploy_runner_roots"].values()), "runner roots must target the new cluster by IP"
    for root in defaults["deploy_runner_roots"]:
        assert (ROOT / "terraform/stacks" / root).is_dir(), root
    assert "deploy-runner" not in defaults["deploy_runner_roots"], "the runner must never apply its own VM"

    secret_markers = ("deploy_runner_connection_token", "deploy_runner_proxmox_token", "config.yml.j2")
    for task in tasks():
        body = yaml.safe_dump(task)
        if any(marker in body for marker in secret_markers):
            assert task.get("no_log") is True, f"task handling secrets must use no_log: {task['name']}"
    by_name = {task["name"]: task for task in tasks()}
    token_task = by_name["Install the scoped Proxmox token, readable only by the deployment user"]["ansible.builtin.copy"]
    assert (token_task["owner"], token_task["group"], token_task["mode"]) == ("root", "deploy", "0640")
    sudo = by_name["Allow the job user to run only the wrapper, as the deployment user"]["ansible.builtin.template"]
    assert sudo["validate"].startswith("/usr/sbin/visudo -cf")

    dirs = {item["path"]: item for item in by_name["Create runner, deployment and configuration directories"]["loop"]}
    approvals = dirs["{{ deploy_runner_etc }}/approvals"]
    assert (approvals["owner"], approvals["group"], approvals["mode"]) == ("root", "root", "0755"), "jobs/deploy never write approvals"
    tofurc = by_name["Install an empty, root-owned OpenTofu CLI configuration (no dev_overrides, no mirrors)"]["ansible.builtin.copy"]
    assert tofurc["owner"] == "root" and tofurc["mode"] == "0644"
    (handler,) = yaml.safe_load((ROLE / "handlers/main.yml").read_text())
    assert handler["ansible.builtin.command"]["argv"][:2] == ["flock", "--nonblock"], "no restart under a running deployment"
    rules = [line for line in (ROLE / "templates/sudoers.j2").read_text().splitlines()
             if line.strip() and not line.startswith(("#", "Defaults"))]
    assert rules == ["runner ALL=(deploy) NOPASSWD: /usr/local/sbin/homelab-deploy"], rules
    service = (ROLE / "templates/forgejo-runner.service.j2").read_text()
    assert "User=runner" in service and "NoNewPrivileges" not in service.replace("No NoNewPrivileges", "")
    config = (ROLE / "templates/config.yml.j2").read_text()
    assert "capacity: 1" in config and "':host'" in config and "docker" not in config
    assert os.access(WRAPPER, os.X_OK), "the wrapper is committed executable (Ansible also sets 0755)"


def workflow_triggers(document):
    return document.get("on", document.get(True)) or {}


def test_workflows():
    workflows = {path.name: yaml.safe_load(path.read_text()) for path in (ROOT / ".forgejo/workflows").glob("*.yml")}
    assert "deploy.yml" in workflows
    for name, document in workflows.items():
        triggers = workflow_triggers(document)
        assert not {"pull_request", "pull_request_target"} & set(triggers), f"{name}: no pull_request triggers"
        text = (ROOT / ".forgejo/workflows" / name).read_text()
        labels = {job.get("runs-on") for job in document["jobs"].values()}
        if name == "deploy.yml":
            continue
        assert "homelab-deploy" not in labels and "homelab-deploy" not in text, f"{name} must not use the deploy runner"
        assert "PROXMOX" not in text and "DEPLOY_RUNNER" not in text, f"{name}: validation gets no deploy credentials"

    deploy = workflows["deploy.yml"]
    text = (ROOT / ".forgejo/workflows/deploy.yml").read_text()
    assert set(workflow_triggers(deploy)) == {"workflow_dispatch"}
    (job,) = deploy["jobs"].values()
    assert job["runs-on"] == "homelab-deploy"
    assert "forgejo.ref == 'refs/heads/main'" in job["if"] and "vars.DEPLOY_RUNNER_APPROVED == 'true'" in job["if"]
    assert "secrets." not in text and all("uses" not in step for step in job["steps"])
    (step,) = job["steps"]
    assert "${{" not in step["run"], "inputs reach the shell only through env, never interpolated"
    assert "sudo -n -u deploy /usr/local/sbin/homelab-deploy" in step["run"]
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    options = workflow_triggers(deploy)["workflow_dispatch"]["inputs"]["root"]["options"]
    assert set(options) == set(defaults["deploy_runner_roots"])


def test_make_guards():
    with tempfile.TemporaryDirectory(prefix="deploy-runner-make-") as directory:
        base = Path(directory)
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
        (fake / "tofu").write_text(f'#!/bin/sh\necho "tofu $*" >> "{base}/calls.log"\n')
        (fake / "tofu").chmod(0o755)
        root = base / "terraform/stacks/deploy-runner"
        root.mkdir(parents=True)

        def make(*args, env=None):
            return subprocess.run(["make", "--no-print-directory", *args], cwd=base, capture_output=True, text=True,
                                  env={"PATH": f"{fake}:/usr/bin:/bin", "HOME": str(base), **(env or {})})

        def calls():
            log = base / "calls.log"
            return log.read_text() if log.exists() else ""

        reviewed = ("deploy-runner-plan", "DEPLOY_RUNNER_ALLOCATION_REVIEWED=yes", "MGMT_INPUT_SOURCE=env")
        workstation = {"PROXMOX_VE_API_TOKEN": "tofu@pve!mgmt=00000000-0000-0000-0000-000000000000"}
        assert make("deploy-runner-plan").returncode != 0
        assert "MGMT_INPUT_SOURCE" in make("deploy-runner-plan", "DEPLOY_RUNNER_ALLOCATION_REVIEWED=yes").stderr
        assert "terraform.tfvars" in make(*reviewed, env=workstation).stderr
        (root / "terraform.tfvars").write_text('proxmox_endpoint = "https://192.168.0.10:8006/"\n')
        # No state: refused unless the first creation is declared explicitly.
        result = make(*reviewed, env=workstation)
        assert result.returncode != 0 and "DEPLOY_RUNNER_NEW_STATE=yes" in result.stderr and calls() == ""
        result = make(*reviewed, "DEPLOY_RUNNER_NEW_STATE=yes", env=workstation)
        assert "-chdir=terraform/stacks/deploy-runner plan -input=false -out=deploy-runner.tfplan" in calls(), result.stderr
        assert "00000000-0000" not in result.stdout + result.stderr

        # Apply needs approval and the reviewed hash.
        (root / "deploy-runner.tfplan").write_text("synthetic plan")
        assert make("deploy-runner-apply", "MGMT_INPUT_SOURCE=env", env=workstation).returncode != 0
        result = make("deploy-runner-apply", "DEPLOY_RUNNER_APPLY_APPROVED=yes", "DEPLOY_RUNNER_PLAN_SHA256=" + "0" * 64,
                      "MGMT_INPUT_SOURCE=env", env=workstation)
        assert result.returncode != 0 and " apply " not in calls()

        # Configuration needs approval and all three runner secrets in the environment.
        assert make("deploy-runner-configure").returncode != 0
        result = make("deploy-runner-configure", "DEPLOY_RUNNER_CONFIGURE_APPROVED=yes",
                      env={"FORGEJO_RUNNER_UUID": "x", "FORGEJO_RUNNER_TOKEN": "y"})
        assert result.returncode != 0 and "DEPLOY_PROXMOX_VE_API_TOKEN" in result.stderr

        # Approval is explicit, validated, and the only path writes over SSH (fake ssh records the call).
        (fake / "ssh").write_text(f'#!/bin/sh\necho "ssh $*" >> "{base}/ssh.log"\ncat >> "{base}/ssh.log"\n')
        (fake / "ssh").chmod(0o755)
        sha = "a" * 64
        assert make("deploy-runner-approve", "DEPLOY_ROOT=ci-disposable", f"DEPLOY_PLAN_SHA256={sha}").returncode != 0
        for bad in (["DEPLOY_ROOT=../etc", f"DEPLOY_PLAN_SHA256={sha}"], ["DEPLOY_ROOT=ci-disposable", "DEPLOY_PLAN_SHA256=abc"]):
            assert make("deploy-runner-approve", "DEPLOY_RUNNER_APPROVE=yes", *bad).returncode != 0
        assert not (base / "ssh.log").exists()
        assert make("deploy-runner-review").returncode != 0 and not (base / "ssh.log").exists()
        result = make("deploy-runner-approve", "DEPLOY_RUNNER_APPROVE=yes", "DEPLOY_ROOT=ci-disposable", f"DEPLOY_PLAN_SHA256={sha}")
        ssh_log = (base / "ssh.log").read_text()
        assert result.returncode == 0, result.stderr
        assert "StrictHostKeyChecking=yes" in ssh_log and "/etc/homelab-deploy/approvals/ci-disposable.sha256" in ssh_log
        assert ssh_log.rstrip().endswith(sha)


def main():
    wrapper = load_wrapper()
    test_wrapper_validation(wrapper)
    test_wrapper_end_to_end(wrapper)
    test_config_template()
    test_role()
    test_workflows()
    test_make_guards()
    print("PASS: deploy runner wrapper (main-only, exact plan), role credentials, workflow boundary, Make guards")


if __name__ == "__main__":
    main()
