"""Synthetic fixtures only: no real state, service, key or network access."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "verifier", Path(__file__).resolve().parents[1] / "scripts/verify-recovery-kit.py"
)
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)
COMMIT = "a" * 40


class KitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.manifest = {"schema_version": 1, "generation": "synthetic",
                         "git_commit": COMMIT, "files": []}
        for root in sorted(VERIFIER.ROOTS):
            state = {"version": 4, "lineage": "synthetic-" + root, "serial": 1}
            self.add(f"states/{root}.tfstate", json.dumps(state), "state",
                     root=root, lineage=state["lineage"], serial=1, recovery_only=True)
        self.add("code.bundle", "synthetic code, not a real bundle", "code")
        self.add("catalogue.json", "{}", "catalogue")
        self.save()

    def add(self, path, data, kind, **extra):
        target = self.directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data)
        self.manifest["files"].append(dict(path=path, bytes=len(data.encode()),
            sha256=hashlib.sha256(data.encode()).hexdigest(), kind=kind, **extra))

    def save(self):
        (self.directory / "manifest.json").write_text(json.dumps(self.manifest))

    def check(self):
        VERIFIER.verify(self.directory, COMMIT)

    def test_valid(self):
        self.check()

    def test_missing(self):
        (self.directory / "code.bundle").unlink()
        with self.assertRaises(ValueError):
            self.check()

    def test_corrupt(self):
        (self.directory / "code.bundle").write_text("corrupt")
        with self.assertRaises(ValueError):
            self.check()

    def test_mismatched_lineage(self):
        self.manifest["files"][0]["lineage"] = "wrong"
        self.save()
        with self.assertRaises(ValueError):
            self.check()

    def test_wrong_commit(self):
        with self.assertRaises(ValueError):
            VERIFIER.verify(self.directory, "b" * 40)

    def test_wrong_root(self):
        self.manifest["files"][0]["root"] = "unknown"
        self.save()
        with self.assertRaises(ValueError):
            self.check()

    def test_traversal(self):
        self.manifest["files"][0]["path"] = "../outside"
        self.save()
        with self.assertRaises(ValueError):
            self.check()

    def test_symlink(self):
        (self.directory / "link").symlink_to(self.directory / "code.bundle")
        with self.assertRaises(ValueError):
            self.check()

    def test_extra(self):
        (self.directory / "unexpected").write_text("synthetic")
        with self.assertRaises(ValueError):
            self.check()

    def test_duplicate(self):
        self.manifest["files"].append(self.manifest["files"][0])
        self.save()
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
