#!/usr/bin/env python3
"""Offline checks of the CI runner ci-runner-01 (TASK-033): one validation runner for every repository, its
registrations only from the environment, no infrastructure credentials, the labels this repository's
workflows ask for, guarded Make targets."""
import os
import re
import subprocess
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "ansible/playbooks/configure-ci-runner.yml"
ROLE = ROOT / "ansible/roles/forgejo_runner"
SECRETS = ["REGISTRY_USERNAME", "REGISTRY_READ_TOKEN"] + [f"{p}_CONNECTION_{f}" for p in ("HOMELAB_IAC", "CEM", "CUSTOM_THEME", "OSS_ARCHIVE")
                                                         for f in ("UUID", "TOKEN")]


def main():
    text = PLAYBOOK.read_text()
    (play,) = yaml.safe_load(text)
    assert play["hosts"] == "ci_runner" and play["roles"] == ["headless_baseline", "forgejo_runner"]
    variables = play["vars"]
    connections = variables["ci_runner_connections"]
    labels = {label.split(":", 1)[0]: label for _, label in connections.values()}
    assert len(labels) == len(connections), "one label per registration"
    for label in labels.values():
        assert re.fullmatch(r"[a-z-]+:docker://git\.doku-lab\.net/[a-z-]+/[a-z-]+:\d+\.\d+\.\d+", label), f"pinned job image: {label}"

    # The runner executes code from any branch: no infrastructure credential may reach it (ADR-008).
    for word in ("PROXMOX", "DEPLOY_", "KUBECONFIG", "PHASE_", "NETBOX"):
        assert word not in text, f"{word} must never reach the validation runner"
    assert "homelab-deploy" not in labels, "deployments stay on deploy-runner-01 (ADR-014)"
    (instance,) = variables["forgejo_runner_instances"]
    assert instance["user"] == "runner" and instance["capacity"] == 2
    assert instance["valid_volumes"] == ["/run/podman/podman.sock", "oss-archive-cache"]
    assert variables["forgejo_runner_registry_auth_required"] is True

    # Registrations and the registry login come from the environment, are never logged, never written in Git.
    tasks = {task["name"]: task for task in play["pre_tasks"]}
    for name in ("Require every registration and the registry login in the environment", "Map the registrations in memory",
                 "Require one distinct registration per connection"):
        assert tasks[name]["no_log"] is True, name
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text), "no registration identity in Git"
    wanted = {f"{prefix}_CONNECTION_{field}" for prefix, _ in connections.values() for field in ("UUID", "TOKEN")}
    assert wanted | {"REGISTRY_USERNAME", "REGISTRY_READ_TOKEN"} == set(SECRETS)
    makefile = (ROOT / "Makefile").read_text()
    assert set(re.search(r"^CI_RUNNER_SECRETS := (.*)$", makefile, re.M).group(1).split()) == set(SECRETS)

    # Every label this repository's validation workflows ask for is served; the deploy label is not.
    asked = set()
    for workflow in (ROOT / ".forgejo/workflows").glob("*.yml"):
        asked |= set(re.findall(r"^\s+runs-on: (\S+)$", workflow.read_text(), re.M))
    assert asked - {"homelab-deploy"} <= set(labels), asked - set(labels)

    # The rendered runner configuration: capacity from the instance, tokens from the map, sockets never automatic.
    template = Environment(undefined=StrictUndefined, keep_trailing_newline=True)
    template.filters["to_json"] = __import__("json").dumps
    template.filters["dict2items"] = lambda d: [{"key": k, "value": v} for k, v in d.items()]
    template.filters["bool"] = bool
    source = (ROLE / "templates/config.yml.j2").read_text()
    names = {name: {"url": "https://git.example.invalid/", "uuid": f"00000000-0000-0000-0000-00000000000{i}", "labels": [connections[name][1]]}
             for i, name in enumerate(connections)}
    rendered = yaml.safe_load(template.from_string(source).render(
        forgejo_runner_container_network="", forgejo_runner_container_privileged=False,
        runner_instance={**instance, "connections": names},
        forgejo_runner_connection_tokens={"main": {name: f"synthetic-{name}" for name in names}}))
    assert rendered["runner"]["capacity"] == 2 and rendered["container"]["docker_host"] == "-"
    assert rendered["container"]["privileged"] is False
    assert {name: c["token"] for name, c in rendered["server"]["connections"].items()} == {name: f"synthetic-{name}" for name in names}
    default = yaml.safe_load(template.from_string(source).render(
        forgejo_runner_container_network="", forgejo_runner_container_privileged=False,
        runner_instance={"name": "main", "container_options": "", "valid_volumes": [], "connections": {}}, forgejo_runner_connection_tokens={}))
    assert default["runner"]["capacity"] == 1, "other users of the role keep one job at a time"

    # Old images are removed by a timer; named volumes (work caches) are not.
    prune = next(t for t in play["tasks"] if t["name"].startswith("Install the nightly clean-up"))["vars"]["ci_runner_prune_units"]
    assert "podman image prune" in prune["service"] and "volume" not in prune["service"].split("ExecStart=")[1]

    clean = {k: v for k, v in os.environ.items() if k not in SECRETS}
    assert subprocess.run(["make", "ci-runner-configure"], cwd=ROOT, capture_output=True, text=True, env=clean).returncode != 0
    refused = subprocess.run(["make", "ci-runner-configure", "CI_RUNNER_CONFIGURE_APPROVED=yes"], cwd=ROOT, capture_output=True, text=True, env=clean)
    assert refused.returncode != 0 and "REGISTRY_USERNAME" in refused.stderr
    for target, variable in (("ci-runner-plan", "CI_RUNNER_ALLOCATION_REVIEWED"), ("ci-runner-apply", "CI_RUNNER_APPLY_APPROVED")):
        result = subprocess.run(["make", target], cwd=ROOT, capture_output=True, text=True, env=clean)
        assert result.returncode != 0 and variable in result.stderr, target
    print("PASS: one validation runner, registrations from the environment only, no infrastructure credentials, "
          "workflow labels served, image clean-up, Make guards")


if __name__ == "__main__":
    main()
