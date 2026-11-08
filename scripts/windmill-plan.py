"""Initial creation only. Keep the scoped Proxmox password out of Terraform inputs."""
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT / "terraform/stacks/pve-core-windmill"
PLAN = STACK / "windmill.tfplan"
ADDRESS = "proxmox_virtual_environment_container.windmill"


def guard_plan(plan, inputs):
    changes = plan.get("resource_changes", [])
    if (len(changes) != 1 or changes[0]["address"] != ADDRESS
            or changes[0]["change"]["actions"] != ["create"] or plan.get("resource_drift")):
        raise SystemExit("Not the isolated initial one-create Windmill plan; stop.")
    after = changes[0]["change"]["after"]
    init = after["initialization"][0]
    if (after["vm_id"] != inputs["ctid"] or after["node_name"] != "pve-core"
            or init["hostname"] != "windmill"
            or init["ip_config"][0]["ipv4"][0]["address"] != "dhcp"):
        raise SystemExit("Saved plan does not match the reviewed Windmill allocation.")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("plan", "apply"):
        raise SystemExit("Expected plan or apply.")
    action = sys.argv[1]
    if action == "apply" and os.environ.get("WINDMILL_APPLY_APPROVED") != "yes":
        raise SystemExit("Review and approve the exact saved plan first.")
    if (any(k.startswith(("TF_LOG", "TF_CLI_ARGS", "TF_VAR_")) for k in os.environ)
            or os.environ.get("TF_WORKSPACE", "default") != "default"):
        raise SystemExit("Unset debug logging, injected Terraform arguments/variables and nondefault workspace.")
    inputs = STACK / "terraform.tfvars.json"
    if not inputs.is_file() or set(json.loads(inputs.read_text())) != {"ctid"}:
        raise SystemExit("Supply only the verified ctid in private terraform.tfvars.json; the network uses DHCP.")
    if set(STACK.glob("*.tfvars*")) != {inputs}:
        raise SystemExit("Remove ambiguous private inputs before proceeding.")
    if not all(os.getenv(k) for k in ("INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET")):
        raise SystemExit("Use the authenticated operator shell with Infisical Universal Auth.")
    allocation = json.loads(inputs.read_text())
    inventory = subprocess.check_output(["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                                         "root@192.168.0.11", "pvesh get /cluster/resources --type vm --output-format json"])
    if any(int(x["vmid"]) == allocation["ctid"] or x.get("name") == "windmill"
           for x in json.loads(inventory)):
        raise SystemExit("CTID/name already exists; do not adopt, replace or retry initial creation.")
    from infisical_sdk import InfisicalSDKClient
    try:
        with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            client = InfisicalSDKClient(host="https://secrets.doku-lab.net")
            client.auth.universal_auth.login(client_id=os.environ["INFISICAL_CLIENT_ID"],
                                             client_secret=os.environ["INFISICAL_CLIENT_SECRET"])
            password = client.secrets.get_secret_by_name(
                "PROXMOX_ROOT_PASSWORD", environment_slug="dev", secret_path="/proxmox",
                project_id=json.loads((ROOT / ".infisical.json").read_text())["workspaceId"],
                include_imports=False, expand_secret_references=False).secretValue
        if not password:
            raise ValueError()
    except Exception:
        raise SystemExit("Cannot read the required Proxmox password via Universal Auth.") from None
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PROXMOX_", "PM_VE_", "INFISICAL_"))}
    env.update(PROXMOX_VE_PASSWORD=password, PROXMOX_VE_USERNAME="root@pam", TF_WORKSPACE="default")
    cmd = ["terraform", f"-chdir={STACK}"]
    os.umask(0o077)

    def review(path):
        output = subprocess.check_output(cmd + ["show", "-json", str(path)], env=env)
        guard_plan(json.loads(output), allocation)

    if action == "plan":
        with tempfile.TemporaryDirectory(dir=STACK) as temp:
            path = Path(temp) / "new.tfplan"
            subprocess.run(cmd + ["plan", "-input=false", f"-out={path}"], env=env, check=True)
            review(path)
            path.replace(PLAN)
    else:
        review(PLAN)
        subprocess.run(cmd + ["apply", "-input=false", str(PLAN)], env=env, check=True)


if __name__ == "__main__":
    main()
