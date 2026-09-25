"""Verify a private, already-decrypted kit; never extract, export or contact services."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


ROOTS = {
    "deb13-monitoring", "pve-lab-workstations",
    "pve-compute-forgejo-runner-migration", "pve-compute-forgejo-runner",
    "pve-core-garage", "pve-core-tfstate",
}


def require(condition):
    if not condition:
        raise ValueError("Invalid kit")


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique)


def verify(directory, expected_commit):
    require(re.fullmatch(r"[0-9a-f]{40}", expected_commit) is not None)
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink())
    # Reject all links, including directory links, before reading any payload.
    entries = list(directory.rglob("*"))
    require(all(not p.is_symlink() and (p.is_dir() or p.is_file()) for p in entries))
    manifest = read_json(directory / "manifest.json")
    require(set(manifest) == {"schema_version", "generation", "git_commit", "files"})
    require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1)
    require(manifest["git_commit"] == expected_commit)
    require(isinstance(manifest["generation"], str)
            and re.fullmatch(r"[A-Za-z0-9_-]{1,120}", manifest["generation"]))
    require(isinstance(manifest["files"], list) and manifest["files"])
    paths, roots, kinds = set(), set(), set()
    for item in manifest["files"]:
        require(isinstance(item, dict))
        common = {"path", "sha256", "bytes", "kind"}
        is_state = item.get("kind") == "state"
        require(set(item) == common | ({"root", "lineage", "serial", "recovery_only"} if is_state else set()))
        relative = item["path"]
        require(isinstance(relative, str) and relative and "\\" not in relative)
        path = PurePosixPath(relative)
        require(not path.is_absolute() and ".." not in path.parts
                and str(path) == relative and relative != "manifest.json"
                and relative not in paths)
        require(type(item["bytes"]) is int and item["bytes"] >= 0)
        require(isinstance(item["sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]))
        require(item["kind"] in {"state", "code", "catalogue", "payload"})
        target = directory / relative
        require(target.is_file() and target.stat().st_size == item["bytes"])
        with target.open("rb") as stream:
            require(hashlib.file_digest(stream, "sha256").hexdigest() == item["sha256"])
        if is_state:
            root = item["root"]
            require(root in ROOTS and root not in roots
                    and relative == f"states/{root}.tfstate"
                    and item["recovery_only"] is True)
            require(isinstance(item["lineage"], str) and item["lineage"]
                    and type(item["serial"]) is int and item["serial"] >= 0)
            state = read_json(target)
            require(state.get("version") == 4 and type(state.get("serial")) is int
                    and state.get("lineage") == item["lineage"]
                    and state["serial"] == item["serial"])
            roots.add(root)
        paths.add(relative)
        kinds.add(item["kind"])
    require(roots == ROOTS and {"code", "catalogue"} <= kinds)
    require({str(p.relative_to(directory)) for p in entries if p.is_file()}
            == paths | {"manifest.json"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    try:
        verify(args.directory, args.expected_commit)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        # Even filenames, parser errors and lineage values can reveal private data.
        print("FAIL: kit structure/integrity mismatch; review privately. No payload displayed.")
        return 1
    print("PASS: structural integrity only; not proof of authenticity, freshness or recovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
