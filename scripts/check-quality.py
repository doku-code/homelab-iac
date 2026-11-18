"""Offline parsing and validation-workflow guards; no infrastructure calls."""

from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
# Vendored harness templates contain {{placeholders}}; they are rendered, not parsed, as YAML.
TEMPLATE_DIRS = ("tools/agent-harness/harness/assets/workflows/",)


BLUEPRINT_DIR = "services/authentik/blueprints/"


class BlueprintLoader(yaml.SafeLoader):
    """SafeLoader that accepts any application tag and builds the plain value under it."""


def _plain(loader, _suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    return loader.construct_mapping(node, deep=True)


BlueprintLoader.add_multi_constructor("!", _plain)


def main():
    paths = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode().split("\0")
    counts = {"yaml": 0, "python": 0, "shell": 0}
    for relative in filter(None, paths):
        path = ROOT / relative
        if path.suffix in (".yml", ".yaml"):
            if relative.startswith(TEMPLATE_DIRS):
                continue
            # Authentik blueprints use their own tags (!Env, !Find, !KeyOf); tests/authentik.py checks their content.
            loader = BlueprintLoader if relative.startswith(BLUEPRINT_DIR) else yaml.SafeLoader
            list(yaml.load_all(path.read_text(), Loader=loader))  # noqa: S506 - both loaders are safe loaders
            counts["yaml"] += 1
        elif path.suffix == ".py":
            compile(path.read_text(), relative, "exec")
            counts["python"] += 1
        elif path.suffix == ".sh":
            subprocess.run(["bash", "-n", str(path)], check=True)
            counts["shell"] += 1

    # BaseLoader preserves the workflow key 'on' instead of YAML 1.1's boolean.
    for path in sorted((ROOT / ".forgejo/workflows").glob("*.yml")):
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        for job in workflow["jobs"].values():
            for step in job["steps"]:
                if "run" in step:
                    subprocess.run(["bash", "-n"], input=step["run"], text=True, check=True)
                    counts["shell"] += 1

    source = (ROOT / ".forgejo/workflows/validate.yml").read_text()
    workflow = yaml.load(source, Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"push", "workflow_dispatch"}
    assert workflow["on"]["push"]["branches"] == ["main"]
    # Installed Forgejo ignores GitHub-style permissions; do not imply isolation.
    assert "permissions" not in workflow
    job = workflow["jobs"]["validate"]
    assert "permissions" not in job
    assert job["if"] == "forgejo.ref == 'refs/heads/main' && vars.CI_QUALITY_APPROVED == 'true'"
    assert job["runs-on"] == "homelab-iac"
    assert "container" not in job and "services" not in job
    assert "secrets." not in source and "podman.sock" not in source
    assert "docker.sock" not in source
    checkout = job["steps"][0]
    assert checkout["with"] == {"persist-credentials": "false", "fetch-depth": "0"}
    assert "-backend=false -input=false -lockfile=readonly" in source
    for root in sorted((ROOT / "terraform").glob("*/*/versions.tf")):
        assert str(root.parent.relative_to(ROOT)) in source, root.parent
    assert "tests/tfstate-backups.py" in source
    assert "tests/runner-connections.py" in source

    # Wiki publication: same main-only gate and runner; only the job's own token, only in the publish step.
    source = (ROOT / ".forgejo/workflows/harness-wiki-publish.yml").read_text()
    workflow = yaml.load(source, Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"push", "workflow_dispatch"}
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert "permissions" not in workflow
    job = workflow["jobs"]["publish"]
    assert job["if"] == "forgejo.ref == 'refs/heads/main' && vars.CI_QUALITY_APPROVED == 'true'"
    assert job["runs-on"] == "homelab-iac"
    assert "container" not in job and "services" not in job
    assert "secrets." not in source and "PROXMOX" not in source and "homelab-deploy" not in source
    assert job["steps"][0]["with"] == {"persist-credentials": "false", "fetch-depth": "0"}
    assert "-r requirements-agents.txt" in source
    token_steps = [s for s in job["steps"] if "forgejo.token" in str(s)]
    assert len(token_steps) == 1 and "forgejo.token" not in token_steps[0]["run"]
    assert token_steps[0]["env"]["HARNESS_WIKI_TOKEN"] == "${{ forgejo.token }}"
    print(f"PASS: {counts}; main-only activation gate and workflow configuration guards")


if __name__ == "__main__":
    main()
