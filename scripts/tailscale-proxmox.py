"""Tailscale root only: Universal Auth injection and password-only provider runtime."""
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STACK = "terraform/stacks/pve-tailscale-routers"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    require(len(sys.argv) == 2 and sys.argv[1] in
            ("plan", "apply", "provider-plan", "provider-apply"), "Unsupported Tailscale operation.")
    action = sys.argv[1]
    env = os.environ.copy()
    require(not any(v for k, v in env.items() if k.startswith(("TF_LOG", "TF_CLI_ARGS"))),
            "Unset TF_LOG* and TF_CLI_ARGS* for secret-safe, saved-plan execution.")
    require(env.get("TF_WORKSPACE", "default") == "default",
            "Use the existing default local Tailscale state, not another workspace.")
    if action.endswith("apply"):
        require(env.get("TAILSCALE_APPLY_APPROVED") == "yes", "Explicit apply approval required.")
    os.chdir(ROOT)
    os.umask(0o077)
    if action.startswith("provider-"):
        password = env.get("PROXMOX_ROOT_PASSWORD", "")
        require(bool(password.strip()), "Infisical /proxmox/ must supply PROXMOX_ROOT_PASSWORD; no auth fallback.")
        action = action.removeprefix("provider-")
        # Remove both current and legacy token/ticket/password aliases. These
        # process-local changes never affect other Make targets or the shell.
        env = {k: v for k, v in env.items() if not k.startswith(
            ("PROXMOX_", "PM_VE_", "INFISICAL_", "TF_VAR_"))}
        env["PROXMOX_VE_PASSWORD"] = password
        env["PROXMOX_VE_USERNAME"] = "root@pam"
        if action == "apply":
            result = subprocess.run(["terraform", f"-chdir={STACK}", "show", "-json", "tailscale.tfplan"],
                                    env=env, capture_output=True, text=True)
            require(result.returncode == 0, "Cannot inspect saved plan; generate and review a NEW plan.")
            resources = json.loads(result.stdout)["configuration"]["root_module"]["resources"]
            require(len(resources) == 1 and resources[0]["address"] ==
                    "proxmox_virtual_environment_container.router" and
                    resources[0]["provider_config_key"] == "proxmox.root",
                    "Saved plan predates the scoped root provider; generate and review a NEW plan.")
        command = ["terraform", f"-chdir={STACK}", action, "-input=false"]
        command += ["-out=tailscale.tfplan"] if action == "plan" else ["tailscale.tfplan"]
        os.execvpe(command[0], command, env)
    require(all(env.get(k) for k in ("INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET")),
            "Set INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET in the authenticated operator shell.")
    from infisical_sdk import InfisicalSDKClient
    domain = "https://secrets.doku-lab.net"
    try:
        with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            client = InfisicalSDKClient(host=domain)
            token = client.auth.universal_auth.login(
                client_id=env["INFISICAL_CLIENT_ID"], client_secret=env["INFISICAL_CLIENT_SECRET"]
            ).accessToken
        require(bool(token), "empty token")
    except Exception:
        raise ValueError("Infisical Universal Auth failed; no fallback or provider operation.") from None
    project = json.loads((ROOT / ".infisical.json").read_text())["workspaceId"]
    # Never fall back to an ambient password if the selected secret is missing.
    for key in list(env):
        if key.startswith(("PROXMOX_", "PM_VE_", "INFISICAL_", "TF_VAR_")):
            env.pop(key)
    env["INFISICAL_TOKEN"] = token
    command = ["infisical", "run", "--silent", "--log-level", "error", "--domain", domain,
               "--projectId", project, "--env", "dev", "--path", "/proxmox/",
               "--expand=false", "--include-imports=false", "--",
               sys.executable, str(Path(__file__).resolve()), f"provider-{action}"]
    os.execvpe(command[0], command, env)


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        # Only our fixed guard messages are safe; JSON/server/OS details are not.
        print(str(error) if type(error) is ValueError else "Invalid runtime metadata or saved plan.", file=sys.stderr)
        sys.exit(1)
    except Exception:
        print("Tailscale authentication tooling failed; no credential details logged.", file=sys.stderr)
        sys.exit(1)
