"""Run a command only with a dedicated, verified-TLS Proxmox API token in the environment.

Usage: pve-auth-guard.py -- <command...>
Refuses password/ticket authentication, root@pam tokens, disabled TLS verification and
debug logging that could print credentials. Infisical bootstrap credentials are removed from
the child environment so OpenTofu never sees them. Prints no secret values.
"""

import os
import re
import sys

TOKEN_RE = re.compile(r"^(?P<user>[^\s@!]+@[^\s!]+)!(?P<id>[A-Za-z0-9._-]+)=(?P<secret>\S+)$")
FORBIDDEN = ("PROXMOX_VE_USERNAME", "PROXMOX_VE_PASSWORD", "PROXMOX_VE_OTP", "PROXMOX_VE_AUTH_TICKET",
             "PROXMOX_VE_CSRF_PREVENTION_TOKEN", "PM_VE_PASSWORD")
TRUTHY = {"1", "true", "yes", "on"}


def check(env):
    """Return a list of problems; empty means the environment is acceptable."""
    problems = []
    match = TOKEN_RE.match(env.get("PROXMOX_VE_API_TOKEN", ""))
    if not match:
        problems.append("PROXMOX_VE_API_TOKEN must be set as user@realm!tokenid=secret.")
    elif match.group("user") == "root@pam":
        problems.append("Use the dedicated automation identity, not a root@pam token.")
    for name in FORBIDDEN:
        if env.get(name):
            problems.append(f"Unset {name}: only API-token authentication is allowed.")
    if env.get("PROXMOX_VE_INSECURE", "").strip().lower() in TRUTHY:
        problems.append("PROXMOX_VE_INSECURE must not disable TLS verification.")
    for name in env:
        if name.startswith(("TF_LOG", "TF_CLI_ARGS")):
            problems.append(f"Unset {name}: debug logging or injected arguments can leak credentials.")
    return problems


def child_env(env):
    return {k: v for k, v in env.items() if not k.startswith("INFISICAL_")}


def main(argv):
    if "--" not in argv or argv.index("--") == len(argv) - 1:
        print("usage: pve-auth-guard.py -- <command...>", file=sys.stderr)
        return 2
    command = argv[argv.index("--") + 1:]
    problems = check(os.environ)
    if problems:
        for problem in problems:
            print(f"pve-auth-guard: {problem}", file=sys.stderr)
        return 1
    os.execvpe(command[0], command, child_env(os.environ))
    return 0  # not reached


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
