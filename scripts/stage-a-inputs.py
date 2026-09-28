"""Stage A only: explicit credential delivery, never state or profile selection."""
import argparse
import contextlib
import os
from pathlib import Path
import re
import shutil
import sys


STACK = "terraform/stacks/pve-lab-k3s"
AUTH_CONFLICTS = ("PROXMOX_VE_USERNAME", "PROXMOX_VE_PASSWORD", "PROXMOX_VE_OTP")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def provider_check(env):
    require(not any(env.get(k) for k in AUTH_CONFLICTS),
            "Stage A requires unambiguous API-token auth; unset username/password/OTP auth.")
    require(re.fullmatch(r"[^\s@!]+@[^\s!]+![^\s=]+=\S+", env.get("PROXMOX_VE_API_TOKEN", "")),
            "Supply PROXMOX_VE_API_TOKEN in the selected source (user@realm!token=value).")


def execution_check(env):
    # These can silently bypass the reviewed-plan/default-local-state contract.
    require(not any(v for k, v in env.items() if k.startswith(("TF_CLI_ARGS", "TF_LOG"))),
            "Unset TF_CLI_ARGS* and TF_LOG* for the guarded, secret-safe Stage A workflow.")
    require(env.get("TF_WORKSPACE", "default") == "default",
            "Stage A uses its existing default local state authority, not another workspace.")


def check(args, env):
    source = env.get("STAGE_A_INPUT_SOURCE")
    require(source in ("infisical", "private"),
            "Explicitly select STAGE_A_INPUT_SOURCE=infisical or private; no fallback.")
    execution_check(env)
    if source == "private":
        provider_check(env)
    else:
        require(all(env.get(k) for k in ("INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET")),
                "Set INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET in the runtime environment.")
        require(args.domain.startswith("https://") and args.project_id and args.environment,
                "Infisical requires HTTPS domain, project ID and environment.")
        require(shutil.which("infisical"), "Selected Infisical CLI is unavailable; no fallback.")
        # The pinned SDK is already part of requirements-controller.txt.
        from infisical_sdk import InfisicalSDKClient  # noqa: F401
    return source


def authenticate(args, env):
    from infisical_sdk import InfisicalSDKClient
    # Never publish server errors, request bodies or SDK diagnostics containing credentials.
    try:
        with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            client = InfisicalSDKClient(host=args.domain.rstrip("/"))
            token = client.auth.universal_auth.login(
                client_id=env["INFISICAL_CLIENT_ID"],
                client_secret=env["INFISICAL_CLIENT_SECRET"],
            ).accessToken
        require(token, "empty token")
        return token
    except Exception:
        raise ValueError("Infisical Universal Auth failed; no provider operation or fallback.") from None


def terraform(action, env):
    execution_check(env)
    provider_check(env)
    # No authentication material belongs in Terraform arguments, variables or saved plans.
    env = {k: v for k, v in env.items() if not k.startswith("INFISICAL_")}
    command = ["terraform", f"-chdir={STACK}", action, "-input=false"]
    command += ["-out=stage-a.tfplan"] if action == "plan" else ["stage-a.tfplan"]
    os.execvpe(command[0], command, env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="")
    parser.add_argument("--environment", default="")
    parser.add_argument("--project-id", default="")
    parser.add_argument("action", choices=("check", "plan", "apply", "provider-plan", "provider-apply"))
    args = parser.parse_args()
    env = os.environ.copy()
    if args.action.startswith("provider-"):
        terraform(args.action.removeprefix("provider-"), env)
        return
    source = check(args, env)
    if args.action == "check":
        return
    if source == "private":
        terraform(args.action, env)
        return
    env["INFISICAL_TOKEN"] = authenticate(args, env)
    # A missing export must not silently reuse ambient Proxmox credentials.
    for key in ("PROXMOX_VE_API_TOKEN", *AUTH_CONFLICTS, "INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET"):
        env.pop(key, None)
    command = ["infisical", "run", "--silent", "--log-level", "error",
               "--domain", args.domain, "--projectId", args.project_id,
               "--env", args.environment, "--", sys.executable,
               str(Path(__file__).resolve()), f"provider-{args.action}"]
    os.execvpe(command[0], command, env)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, ImportError, OSError):
        # Controlled validation messages only; OS/SDK errors can include private material.
        error = sys.exc_info()[1]
        print(str(error) if isinstance(error, ValueError) else
              "Stage A input tooling unavailable; run setup-controller and check required executables.", file=sys.stderr)
        sys.exit(1)
