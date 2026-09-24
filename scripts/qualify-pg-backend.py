#!/usr/bin/env python3
"""Disposable CT300 qualification. Never points at an existing Terraform root."""

import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import tempfile
import time


FIXTURE = '''terraform {
  required_version = "= 1.16.1"
  backend "pg" {}
}
variable "value" { type = string }
resource "terraform_data" "probe" {
  input = var.value
  triggers_replace = [var.value]
  provisioner "local-exec" {
    command = <<-EOT
      if [ -n "$TFSTATE_HOLD_DIR" ]; then
        touch "$TFSTATE_HOLD_DIR/entered"
        n=0
        while [ ! -f "$TFSTATE_HOLD_DIR/release" ]; do
          sleep 1
          n=$((n+1))
          [ "$n" -lt 120 ] || exit 1
        done
      fi
    EOT
  }
}
output "value" { value = terraform_data.probe.output }
'''


def main():
    if not __debug__:
        raise RuntimeError("Qualification assertions require Python without optimization")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--known-hosts", required=True,
                        help="File containing CT300's independently verified SSH host key")
    parser.add_argument("--scheduled-backup", action="store_true",
                        help="Restore from the real systemd logical backup service instead of an ad hoc dump")
    args = parser.parse_args()
    os.umask(0o077)
    repo = Path(__file__).resolve().parents[1]
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", f"UserKnownHostsFile={Path(args.known_hosts).resolve()}"]
    key = os.environ.get("GUEST_SSH_PRIVATE_KEY_FILE")
    if key:
        ssh += ["-i", key]
    host = "root@192.168.0.30"
    prefix = "tfq_" + secrets.token_hex(4)
    owner, user_a, user_b, user_c = [prefix + x for x in ("_owner", "_a", "_b", "_c")]
    db1, db2, restored = [prefix + x for x in ("_one", "_two", "_restore")]
    passwords = {r: secrets.token_hex(32) for r in (owner, user_a, user_b, user_c)}
    children = []
    report = {"terraform": "1.16.1", "transport": "verified SSH forwarding, loopback SCRAM"}
    created_group = False

    def run(cmd, **kwargs):
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, **kwargs)
        if result.returncode:
            # Commands never contain passwords. SQL errors can echo input: do not print them.
            if cmd[0] == "terraform":
                diagnostic = result.stderr
                for password in passwords.values():
                    diagnostic = diagnostic.replace(password, "[REDACTED]")
                raise RuntimeError(f"Terraform failed ({result.returncode}): {diagnostic[-2000:]}")
            raise RuntimeError(f"Command failed ({result.returncode}): {cmd[0]}")
        return result.stdout.strip()

    def sql(statement, db="postgres"):
        return run(ssh + [host, f"runuser -u postgres -- psql -XAt -v ON_ERROR_STOP=1 -d {db}"],
                   input=statement)

    def locks(db):
        return int(sql("SELECT count(*) FROM pg_locks WHERE locktype='advisory' "
                       f"AND granted AND database=(SELECT oid FROM pg_database WHERE datname='{db}');"))

    def wait_for(test, seconds=30):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if test():
                return
            time.sleep(0.25)
        raise RuntimeError("Timed out waiting for qualification condition")

    def stop(process):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.communicate(timeout=10)

    version = json.loads(run(["terraform", "version", "-json"]))["terraform_version"]
    if version != "1.16.1":
        raise RuntimeError("Qualification fixture requires Terraform 1.16.1")
    if sql("SELECT count(*) FROM pg_roles WHERE rolname='tfstate_qualification';") != "0":
        raise RuntimeError("Qualification role group already exists; inspect prior cleanup first")

    (repo / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pg-qualification-", dir=repo / "tmp") as workspace:
        base = Path(workspace)
        try:
            sql("CREATE ROLE tfstate_qualification NOLOGIN;")
            created_group = True
            for role, password in passwords.items():
                sql(f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    f"NOREPLICATION NOBYPASSRLS PASSWORD '{password}'; "
                    f"GRANT tfstate_qualification TO {role};")
            for db in (db1, db2):
                sql(f"CREATE DATABASE {db} OWNER {owner};")
                sql(f"REVOKE ALL ON DATABASE {db} FROM PUBLIC;")
                sql("REVOKE ALL ON SCHEMA public FROM PUBLIC;", db)

            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            tunnel = subprocess.Popen(ssh + ["-o", "ExitOnForwardFailure=yes", "-N", "-L",
                                             f"127.0.0.1:{port}:127.0.0.1:5432", host],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True, start_new_session=True)
            children.append(tunnel)

            def tunnel_ready():
                if tunnel.poll() is not None:
                    raise RuntimeError("SSH forwarding failed")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1):
                        return True
                except OSError:
                    return False

            wait_for(tunnel_ready)

            def env(db, role, value="initial", hold=None, setup=False):
                result = {k: v for k, v in os.environ.items()
                          if not k.startswith(("PG", "TF_", "TFSTATE_"))}
                result.update(PGHOST="127.0.0.1", PGPORT=str(port), PGDATABASE=db,
                              PGUSER=role, PGPASSWORD=passwords[role], PGSSLMODE="disable",
                              PGCONNECT_TIMEOUT="10", TF_IN_AUTOMATION="1", TF_VAR_value=value)
                if not setup:
                    for item in ("SCHEMA", "TABLE", "INDEX"):
                        result[f"PG_SKIP_{item}_CREATION"] = "true"
                if hold:
                    result["TFSTATE_HOLD_DIR"] = str(hold)
                return result

            dirs = {}
            for name in ("setup1", "setup2", "a", "b", "c", "restore"):
                dirs[name] = base / name
                dirs[name].mkdir()
                (dirs[name] / "main.tf").write_text(FIXTURE)

            def tf(name, arguments, environment):
                return run(["terraform", f"-chdir={dirs[name]}", *arguments], env=environment)

            for name, db in (("setup1", db1), ("setup2", db2)):
                # Let the exact Terraform binary bootstrap its own schema, then remove DDL access.
                tf(name, ["init", "-input=false", "-no-color"], env(db, owner, setup=True))
            sql(f"ALTER ROLE {owner} NOLOGIN; REVOKE tfstate_qualification FROM {owner};")
            for db, roles in ((db1, (user_a, user_b)), (db2, (user_c,))):
                sequence_schema = sql("SELECT n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                                      "WHERE c.relname='global_states_id_seq' AND c.relkind='S';", db)
                assert sequence_schema == "public", "Review changed Terraform global sequence placement"
                for role in roles:
                    sql(f"GRANT CONNECT ON DATABASE {db} TO {role};")
                    sql(f"GRANT USAGE ON SCHEMA terraform_remote_state TO {role}; "
                        f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA terraform_remote_state TO {role}; "
                        f"GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA terraform_remote_state TO {role}; "
                        f"GRANT USAGE ON SCHEMA public TO {role}; "
                        f"GRANT USAGE,SELECT ON SEQUENCE public.global_states_id_seq TO {role};", db)
            report["runtime_permissions"] = "DML only, schema USAGE and sequence USAGE/SELECT including public.global_states_id_seq; owner NOLOGIN"
            for name, db, role in (("a", db1, user_a), ("b", db1, user_b), ("c", db2, user_c)):
                tf(name, ["init", "-input=false", "-no-color"], env(db, role))

            apply = ["apply", "-auto-approve", "-input=false", "-no-color"]

            def state(db):
                return json.loads(sql("SELECT data FROM terraform_remote_state.states WHERE name='default';", db))

            def finish(process):
                output, error = process.communicate(timeout=90)
                if process.returncode:
                    raise RuntimeError("Terraform qualification apply failed (output suppressed)")

            def start(name, db, role, value, hold=None, extra=()):
                process = subprocess.Popen(["terraform", f"-chdir={dirs[name]}", *apply, *extra],
                                           env=env(db, role, value, hold), stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True, start_new_session=True)
                children.append(process)
                return process

            tf("a", apply, env(db1, user_a, "initial"))
            first = state(db1)
            assert json.loads(tf("b", ["output", "-json"], env(db1, user_b)))["value"]["value"] == "initial"
            tf("b", apply, env(db1, user_b, "updated"))
            updated = state(db1)
            assert updated["serial"] > first["serial"] and updated["lineage"] == first["lineage"]
            report["state_crud"] = "PASS: independent read and update, increasing serial, stable lineage"

            gate = base / "normal-lock"
            gate.mkdir()
            client_a = start("a", db1, user_a, "held", gate)
            wait_for(lambda: (gate / "entered").exists() and locks(db1) > 0)
            locked_state = state(db1)
            attempt = subprocess.run(["terraform", f"-chdir={dirs['b']}", *apply, "-lock-timeout=0s"],
                                     env=env(db1, user_b, "forbidden"), capture_output=True, text=True, timeout=30)
            assert attempt.returncode != 0 and "Error acquiring the state lock" in attempt.stdout + attempt.stderr
            assert state(db1) == locked_state
            report["same_state_immediate_contention"] = {"exit": attempt.returncode, "state_unchanged": True}

            # A different database must remain independently writable while A holds its lock.
            tf("c", apply, env(db2, user_c, "isolated"))
            assert state(db2)["lineage"] != state(db1)["lineage"]
            assert locks(db1) > 0
            assert sql(f"SELECT has_database_privilege('{user_a}','{db2}','CONNECT');") == "f"
            assert sql(f"SELECT has_database_privilege('{user_c}','{db1}','CONNECT');") == "f"
            report["cross_root_isolation"] = "PASS: independent apply under A's lock; cross-database CONNECT denied"

            client_b = start("b", db1, user_b, "after-wait", extra=("-lock-timeout=60s",))
            time.sleep(3)
            assert client_b.poll() is None and state(db1) == locked_state and locks(db1) > 0
            (gate / "release").touch()
            finish(client_a)
            finish(client_b)
            wait_for(lambda: locks(db1) == 0)
            assert state(db1)["outputs"]["value"]["value"] == "after-wait"
            report["normal_release_and_waiting_client"] = "PASS: B waited, then applied after A released"

            gate = base / "crash-lock"
            gate.mkdir()
            client_a = start("a", db1, user_a, "crashed", gate)
            wait_for(lambda: (gate / "entered").exists() and locks(db1) > 0)
            before_crash = state(db1)
            client_b = start("b", db1, user_b, "recovered", extra=("-lock-timeout=60s",))
            time.sleep(3)
            assert client_b.poll() is None and state(db1) == before_crash
            started = time.monotonic()
            stop(client_a)
            wait_for(lambda: sql(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{db1}' AND usename='{user_a}';") == "0")
            release_seconds = round(time.monotonic() - started, 2)
            finish(client_b)
            wait_for(lambda: locks(db1) == 0)
            final = state(db1)
            assert final["outputs"]["value"]["value"] == "recovered" and final["lineage"] == first["lineage"]
            tf("b", ["plan", "-detailed-exitcode", "-input=false", "-no-color"], env(db1, user_b, "recovered"))
            report["crash_recovery"] = {"old_session_gone_seconds": release_seconds,
                                        "waiting_client_applied": True, "final_plan_exit": 0}

            # Stream a custom-format logical dump directly to isolated restore; no dump file or secrets in Git.
            dump_command = f"runuser -u postgres -- pg_dump -Fc {db1}"
            if args.scheduled_backup:
                run(ssh + [host, "systemctl start tfstate-logical-backup.service"])
                oid = sql(f"SELECT oid FROM pg_database WHERE datname='{db1}';")
                assert oid.isdigit()
                dump_command = f"cat /var/backups/tfstate/latest/{oid}.dump"
            dump = subprocess.run(ssh + [host, dump_command],
                                  capture_output=True, timeout=60)
            if dump.returncode:
                raise RuntimeError("Logical dump failed")
            sql(f"CREATE DATABASE {restored} OWNER {owner}; REVOKE ALL ON DATABASE {restored} FROM PUBLIC;")
            restore = subprocess.run(ssh + [host, f"runuser -u postgres -- pg_restore --exit-on-error -d {restored}"],
                                     input=dump.stdout, capture_output=True, timeout=60)
            if restore.returncode:
                raise RuntimeError("Logical restore failed")
            sql(f"GRANT CONNECT ON DATABASE {restored} TO {user_b};")
            assert state(restored) == final
            tf("restore", ["init", "-input=false", "-no-color"], env(restored, user_b))
            assert json.loads(tf("restore", ["output", "-json"], env(restored, user_b)))["value"]["value"] == "recovered"
            tf("restore", ["plan", "-detailed-exitcode", "-input=false", "-no-color"], env(restored, user_b, "recovered"))
            report["logical_restore"] = "PASS: complete state identical; Terraform read and no-change plan passed"
            report["logical_backup_source"] = "systemd scheduled service" if args.scheduled_backup else "ad hoc pg_dump stream"
            report["final_state"] = {"serial": final["serial"], "resources": len(final["resources"]), "value": "recovered"}
            for file in base.rglob("*"):
                if file.is_file():
                    content = file.read_bytes()
                    assert not any(password.encode() in content for password in passwords.values())
            assert not list(base.glob("*/terraform.tfstate"))
            report["credential_files_absent"] = True
        finally:
            for process in reversed(children):
                stop(process)
            if created_group:
                for db in (restored, db2, db1):
                    sql(f"DROP DATABASE IF EXISTS {db} WITH (FORCE);")
                for role in (user_a, user_b, user_c, owner):
                    sql(f"DROP ROLE IF EXISTS {role};")
                sql("DROP ROLE tfstate_qualification;")
                assert sql(f"SELECT count(*) FROM pg_roles WHERE rolname LIKE '{prefix}%';") == "0"
                assert sql(f"SELECT count(*) FROM pg_database WHERE datname LIKE '{prefix}%';") == "0"
                report["disposable_cleanup"] = "PASS: databases and roles removed; temporary directory removed on exit"
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
