"""Offline backup publication/retention safety tests; no database or SSH calls."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch


source = Path(__file__).resolve().parents[1] / 'ansible/roles/tfstate/files/tfstate-logical-backup.py'
spec = importlib.util.spec_from_file_location('backup', source)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


def fake_command(command, **kwargs):
    if 'psql' in command:
        return subprocess.CompletedProcess(command, 0, json.dumps([{'name': 'fixture', 'oid': 123}]))
    if 'stdout' in kwargs and hasattr(kwargs['stdout'], 'write'):
        kwargs['stdout'].write(b'synthetic fixture')
    return subprocess.CompletedProcess(command, 0)


class Backups(unittest.TestCase):
    def test_atomic_set_permissions_and_scoped_retention(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / '20200101T000000.000000Z'
            old.mkdir()
            (old / 'manifest.json').write_text('{}')
            os.utime(old, (time.time() - 9 * 86400,) * 2)
            unrelated = root / 'manual-keep'
            unrelated.mkdir()
            with patch.object(backup, 'ROOT', root), patch.object(backup.subprocess, 'run', fake_command):
                backup.backup()
            self.assertFalse(old.exists())
            self.assertTrue(unrelated.exists())
            latest = (root / 'latest').resolve()
            self.assertEqual(latest.stat().st_mode & 0o777, 0o700)
            for name in ('globals.sql', '123.dump', 'manifest.json'):
                self.assertEqual((latest / name).stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads((latest / 'manifest.json').read_text())['databases'][0]['file'], '123.dump')
            self.assertFalse(list(root.glob('.incomplete-*')))

    def test_failure_preserves_previous_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = root / '20200101T000000.000000Z'
            previous.mkdir()
            (previous / 'manifest.json').write_text('{}')
            (root / 'latest').symlink_to(previous.name)
            with patch.object(backup, 'ROOT', root), patch.object(backup.subprocess, 'run', side_effect=RuntimeError('test failure')):
                with self.assertRaises(RuntimeError):
                    backup.backup()
            self.assertEqual((root / 'latest').resolve(), previous.resolve())
            self.assertTrue(previous.exists())
            self.assertFalse(list(root.glob('.incomplete-*')))


if __name__ == '__main__':
    unittest.main()
