"""Live, disposable Garage evaluation. Never run against production state.

Uses boto3 already installed by the declared infisicalsdk dependency. Only
creates a uniquely named bucket/key on CT209 and built-in terraform_data.
Credentials stay in memory and child environments; raw subprocess logs are
deliberately not printed. Temporary client directories are removed on exit.
"""

import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import uuid

import boto3
from botocore.config import Config


HOST = "root@192.168.0.29"
ENDPOINT = "http://192.168.0.29:3900"
BUCKET = "tf-disposable-" + uuid.uuid4().hex
KEY_NAME = BUCKET
STATE = "probe/terraform.tfstate"


def garage(*args, required=True):
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST,
         shlex.join(["/usr/local/bin/garage", *args])],
        capture_output=True, text=True, timeout=60,
    )
    if required and result.returncode:
        raise RuntimeError("Garage CLI failed: " + " ".join(args[:2]))
    return result


def main():
    os.umask(0o077)
    s3 = None
    active = None
    bucket_created = False
    key_attempted = False
    cleanup_errors = []
    with tempfile.TemporaryDirectory(prefix="garage-backend-") as temporary:
        root = Path(temporary)
        try:
            garage("bucket", "create", BUCKET)
            bucket_created = True
            key_attempted = True
            response = garage("key", "create", "--expires-in", "1h", KEY_NAME)
            access = re.search(r"Key ID:\s*(\S+)", response.stdout)
            secret = re.search(r"Secret key:\s*(\S+)", response.stdout)
            if not access or not secret:
                raise RuntimeError("Unexpected key-create structure; values suppressed")
            garage("bucket", "allow", BUCKET, "--key", KEY_NAME, "--read", "--write")
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(("AWS_", "TF_"))}
            env.update(AWS_ACCESS_KEY_ID=access[1], AWS_SECRET_ACCESS_KEY=secret[1],
                       AWS_EC2_METADATA_DISABLED="true", TF_IN_AUTOMATION="1",
                       TF_INPUT="0", CHECKPOINT_DISABLE="1")
            s3 = boto3.client(
                "s3", endpoint_url=ENDPOINT, region_name="garage",
                aws_access_key_id=access[1], aws_secret_access_key=secret[1],
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
            backend = dict(bucket=BUCKET, key=STATE, region="garage",
                           endpoints={"s3": ENDPOINT}, use_path_style=True,
                           use_lockfile=True, skip_credentials_validation=True,
                           skip_region_validation=True, skip_requesting_account_id=True,
                           skip_metadata_api_check=True, skip_s3_checksum=True)
            marker, release = root / "held", root / "release"
            # This local provisioner deliberately keeps Terraform's native lock held.
            hold = root / "hold.py"
            hold.write_text(
                "from pathlib import Path\nimport time\n"
                f"Path({str(marker)!r}).touch()\n"
                f"while not Path({str(release)!r}).exists(): time.sleep(0.1)\n"
            )
            config = {
                "terraform": {"backend": {"s3": backend}},
                "variable": {"revision": {"type": "string"},
                             "hold": {"type": "bool", "default": False}},
                "output": {"revision": {"value": "${var.revision}"}},
                "resource": {"terraform_data": {"lock_holder": {
                    "count": "${var.hold ? 1 : 0}",
                    "provisioner": [{"local-exec": {
                        "command": shlex.join([sys.executable, str(hold)])}}],
                }}},
            }
            clients = [root / "a", root / "b"]
            for client in clients:
                client.mkdir()
                (client / "main.tf.json").write_text(json.dumps(config))

            def tf(client, *args, required=True):
                result = subprocess.run(
                    ["terraform", *args], cwd=client, env=env,
                    capture_output=True, text=True, timeout=90,
                )
                if required and result.returncode:
                    # Print no arbitrary provider/backend diagnostics containing credentials.
                    raise RuntimeError(f"Terraform {args[0]} failed (exit {result.returncode})")
                return result

            def state():
                return s3.get_object(Bucket=BUCKET, Key=STATE)["Body"].read()

            def lock_exists():
                keys = s3.list_objects_v2(Bucket=BUCKET).get("Contents", [])
                return any(x["Key"] == STATE + ".tflock" for x in keys)

            def start_holder():
                marker.unlink(missing_ok=True)
                release.unlink(missing_ok=True)
                process = subprocess.Popen(
                    ["terraform", "apply", "-auto-approve", "-input=false",
                     "-var=revision=held", "-var=hold=true",
                     "-replace=terraform_data.lock_holder[0]"],
                    cwd=clients[0], env=env, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True,
                )
                return process

            def wait_holder(process):
                deadline = time.monotonic() + 40
                while not marker.exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("Client A did not reach the lock-held barrier")
                    time.sleep(0.2)
                if not lock_exists():
                    raise RuntimeError("UNSUITABLE: client A runs without an S3 lock")

            def reject_competitor():
                before = state()
                result = tf(clients[1], "apply", "-auto-approve", "-input=false",
                            "-lock-timeout=0s", "-var=revision=competitor", required=False)
                changed = state() != before
                print(f"Concurrency evidence: client_b_exit={result.returncode}; "
                      f"state_changed={changed}", flush=True)
                if result.returncode == 0:
                    raise RuntimeError("UNSUITABLE: competing client was not rejected by native locking")
                if "Error acquiring the state lock" not in (result.stdout + result.stderr):
                    raise RuntimeError("INCONCLUSIVE: competing client failed for a non-lock reason")
                if changed:
                    raise RuntimeError("UNSUITABLE: competing client changed locked state")

            for client in clients:
                tf(client, "init", "-input=false", "-no-color")
            print("PASS: two independent clients initialized with use_lockfile=true", flush=True)
            for revision in ("one", "two"):
                tf(clients[0], "apply", "-auto-approve", "-input=false", f"-var=revision={revision}")
                observed = json.loads(tf(clients[1], "state", "pull").stdout)
                assert observed["outputs"]["revision"]["value"] == revision
                assert json.loads(state())["outputs"]["revision"]["value"] == revision
                assert not lock_exists()
            print("PASS: state write, independent read, update, and normal unlock", flush=True)
            active = start_holder()
            wait_holder(active)
            reject_competitor()
            print("PASS: client B rejected while client A holds lock; state unchanged", flush=True)
            release.touch()
            if active.wait(timeout=60) != 0:
                raise RuntimeError("Client A failed after releasing its test barrier")
            active = None
            assert not lock_exists()
            tf(clients[1], "apply", "-auto-approve", "-input=false", "-var=revision=after-unlock")
            print("PASS: normal unlock permits subsequent client B update", flush=True)
            active = start_holder()
            wait_holder(active)
            os.killpg(active.pid, signal.SIGKILL)
            active.wait(timeout=10)
            active = None
            assert lock_exists()
            reject_competitor()
            lock = json.loads(s3.get_object(Bucket=BUCKET, Key=STATE + ".tflock")["Body"].read())
            tf(clients[1], "force-unlock", "-force", lock["ID"])
            assert not lock_exists()
            tf(clients[1], "apply", "-auto-approve", "-input=false", "-var=revision=recovered")
            assert json.loads(state())["outputs"]["revision"]["value"] == "recovered"
            assert not lock_exists()
            print("PASS: killed client leaves blocking stale lock; force-unlock restores writes", flush=True)
        finally:
            if active is not None and active.poll() is None:
                os.killpg(active.pid, signal.SIGKILL)
                active.wait(timeout=10)
            # Delete only objects from this UUID-scoped disposable bucket.
            if s3 is not None:
                try:
                    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET):
                        for obj in page.get("Contents", []):
                            s3.delete_object(Bucket=BUCKET, Key=obj["Key"])
                except Exception:
                    cleanup_errors.append("disposable object cleanup")
            if key_attempted:
                if garage("key", "delete", "--yes", KEY_NAME, required=False).returncode:
                    cleanup_errors.append("temporary key revocation")
                else:
                    print("PASS: temporary key revoked", flush=True)
            if bucket_created:
                if garage("bucket", "delete", "--yes", BUCKET, required=False).returncode:
                    cleanup_errors.append("disposable bucket deletion")
                else:
                    print("PASS: disposable bucket deleted", flush=True)
            if cleanup_errors:
                raise RuntimeError("Cleanup needs attention: " + ", ".join(cleanup_errors))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Exceptions from SDKs can contain response details: suppress those values.
        print("FAIL:", str(error) if isinstance(error, RuntimeError) else type(error).__name__)
        sys.exit(1)
