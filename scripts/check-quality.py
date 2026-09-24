"""Offline parsing and validation-workflow guards; no infrastructure calls."""

from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode().split("\0")
    counts = {"yaml": 0, "python": 0, "shell": 0}
    for relative in filter(None, paths):
        path = ROOT / relative
        if path.suffix in (".yml", ".yaml"):
            list(yaml.safe_load_all(path.read_text()))
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
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["validate"]
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
    print(f"PASS: {counts}; main-only activation gate and workflow configuration guards")


if __name__ == "__main__":
    main()
