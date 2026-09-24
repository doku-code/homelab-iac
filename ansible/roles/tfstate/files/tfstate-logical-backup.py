#!/usr/bin/python3
"""Private, atomic PG17 logical snapshots; PBS protects completed sets off-guest."""

import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


ROOT = Path('/var/backups/tfstate')
RETENTION_DAYS = 7


def backup():
    os.umask(0o077)
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (ROOT / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        stage = Path(tempfile.mkdtemp(prefix='.incomplete-', dir=ROOT))
        try:
            command = ['runuser', '-u', 'postgres', '--']
            query = "SELECT coalesce(json_agg(json_build_object('name',datname,'oid',oid)), '[]') FROM pg_database WHERE NOT datistemplate AND datallowconn;"
            result = subprocess.run(command + ['psql', '-XAt', '-v', 'ON_ERROR_STOP=1', '-c', query],
                                    capture_output=True, text=True, check=True)
            databases = json.loads(result.stdout)
            with (stage / 'globals.sql').open('wb') as output:
                # Role hashes are recovery secrets too: the whole set stays root-only.
                subprocess.run(command + ['pg_dumpall', '--globals-only'], stdout=output,
                               stderr=subprocess.PIPE, check=True)
            for database in databases:
                filename = str(int(database['oid'])) + '.dump'
                database['file'] = filename
                environment = dict(os.environ, PGDATABASE=database['name'])
                with (stage / filename).open('wb') as output:
                    subprocess.run(command + ['pg_dump', '--format=custom'], env=environment,
                                   stdout=output, stderr=subprocess.PIPE, check=True)
                with (stage / filename).open('rb') as archive:
                    subprocess.run(command + ['pg_restore', '--list'], stdin=archive,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            (stage / 'manifest.json').write_text(json.dumps({'created_utc': stamp, 'databases': databases}))
            complete = ROOT / stamp
            stage.rename(complete)
            link = ROOT / '.latest-new'
            link.unlink(missing_ok=True)
            link.symlink_to(stamp)
            link.replace(ROOT / 'latest')
            cutoff = time.time() - RETENTION_DAYS * 86400
            for old in ROOT.iterdir():
                if old.is_symlink() or not old.is_dir() or old == complete:
                    continue
                try:
                    datetime.datetime.strptime(old.name, '%Y%m%dT%H%M%S.%fZ')
                except ValueError:
                    continue
                if (old / 'manifest.json').is_file() and old.stat().st_mtime < cutoff:
                    shutil.rmtree(old)
            print(f'Completed PostgreSQL logical backup: {len(databases)} databases; retention {RETENTION_DAYS} days')
        finally:
            if stage.exists():
                shutil.rmtree(stage)


if __name__ == '__main__':
    try:
        backup()
    except Exception:
        # Never send SQL diagnostics or credential-bearing metadata to journald.
        raise SystemExit('PostgreSQL logical backup FAILED; inspect service and storage locally')
