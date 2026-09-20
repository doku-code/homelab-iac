"""Offline regression checks using production tasks and synthetic secrets only."""

import copy
import os
from pathlib import Path
import subprocess
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
play = yaml.safe_load(
    (ROOT / "ansible/playbooks/configure-forgejo-runner-migration.yml").read_text()
)[0]
names = {
    "Require complete CT301 connection pairs from Infisical",
    "Map clean runner connection secrets in memory",
    "Require three distinct connection identities",
}
tasks = [task for task in play["pre_tasks"] if task["name"] in names]
assert len(tasks) == 3
defaults = yaml.safe_load(
    (ROOT / "ansible/roles/forgejo_runner/defaults/main.yml").read_text()
)
prefixes = ["HOMELAB_IAC", "CEM", "CUSTOM_THEME"]
valid = {}
for number, prefix in enumerate(prefixes, 1):
    valid[prefix + "_CONNECTION_TOKEN"] = "synthetic-token-" + prefix
    valid[prefix + "_CONNECTION_UUID"] = f"{number:08d}-1111-4111-8111-111111111111"

cases = [("complete pairs", valid, True)]
for key in valid:
    missing = dict(valid)
    del missing[key]
    cases.append(("missing " + key, missing, False))
    cases.append(("blank " + key, dict(valid, **{key: ""}), False))
cases.extend([
    ("malformed UUID", dict(valid, CEM_CONNECTION_UUID="not-a-uuid"), False),
    ("nil UUID", dict(valid, CEM_CONNECTION_UUID="00000000-0000-0000-0000-000000000000"), False),
    ("duplicate UUID", dict(valid, CEM_CONNECTION_UUID=valid["HOMELAB_IAC_CONNECTION_UUID"]), False),
    ("whitespace token", dict(valid, CEM_CONNECTION_TOKEN="   "), False),
    ("null token", dict(valid, CEM_CONNECTION_TOKEN=None), False),
    ("null UUID", dict(valid, CEM_CONNECTION_UUID=None), False),
    ("legacy tokens with empty UUIDs", {
        "CEM_CONNECTION_TOKEN": "synthetic-old-cem",
        "CUSTOM_THEME_CONNECTION_TOKEN": "synthetic-old-theme",
        "HOMELAB_IAC_CONNECTION_TOKEN": "",
        **{prefix + "_CONNECTION_UUID": "" for prefix in prefixes},
    }, False),
])

template = str(ROOT / "ansible/roles/forgejo_runner/templates/config.yml.j2")
render_checks = {
    "name": "Check rendered identities, images, and isolation",
    "vars": {
        "runner_instance": "{{ forgejo_runner_instances[0] }}",
        "rendered": "{{ lookup('template', '" + template + "') | from_yaml }}",
    },
    "ansible.builtin.assert": {"that": [
        "forgejo_runner_instances | length == 1",
        "rendered.server.connections.keys() | list | sort == ['cem', 'forgejo-custom-theme', 'homelab-iac']",
        "rendered.server.connections.cem.url == 'https://git.doku-lab.net/CEM/'",
        "rendered.server.connections.cem.labels == ['cem:docker://git.doku-lab.net/cem/cem-ci:1.0.1']",
        "rendered.server.connections['homelab-iac'].labels == ['homelab-iac:docker://git.doku-lab.net/doku-code/ci-base:1.0.0']",
        "rendered.server.connections['forgejo-custom-theme'].labels == ['forgejo-theme:docker://git.doku-lab.net/doku-code/ci-base:1.0.0']",
        "rendered.server.connections.cem.uuid == infisical_runner_secrets.secrets.CEM_CONNECTION_UUID",
        "rendered.server.connections.cem.token == infisical_runner_secrets.secrets.CEM_CONNECTION_TOKEN",
        "rendered.container.docker_host == '-'",
        "not rendered.container.privileged",
        "rendered.container.options == ''",
    ]},
}
for connection, prefix in zip(["homelab-iac", "cem", "forgejo-custom-theme"], prefixes):
    for attribute, suffix in [("uuid", "UUID"), ("token", "TOKEN")]:
        render_checks["ansible.builtin.assert"]["that"].append(
            f"rendered.server.connections['{connection}'].{attribute} == "
            f"infisical_runner_secrets.secrets.{prefix}_CONNECTION_{suffix}"
        )

# Only generated localhost plays execute; neither the production play nor role runs.
(ROOT / "tmp").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="runner-tests-", dir=ROOT / "tmp") as directory:
    for label, secrets, should_pass in cases:
        variables = copy.deepcopy(defaults)
        variables["infisical_runner_secrets"] = {"secrets": secrets}
        fixture = [{
            "hosts": "localhost", "connection": "local", "gather_facts": False,
            "vars": variables, "tasks": tasks + [render_checks],
        }]
        path = Path(directory) / "test.yml"
        path.write_text(yaml.safe_dump(fixture, sort_keys=False))
        result = subprocess.run(
            [str(ROOT / ".venv/bin/ansible-playbook"), "-i", "localhost,", str(path)],
            cwd=ROOT, env={**os.environ, "ANSIBLE_LOCAL_TEMP": directory, "TMPDIR": directory},
            text=True, capture_output=True,
        )
        if (result.returncode == 0) != should_pass:
            raise AssertionError(f"Unexpected result for {label}:\n{result.stdout}\n{result.stderr}")
        print(f"PASS: {label}")
