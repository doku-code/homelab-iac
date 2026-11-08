"""Run on the dedicated CT. Read the desired admin password as JSON on stdin."""
import json
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID

BASE = "http://127.0.0.1:8000"
EMAIL = "admin@windmill.dev"


def request(path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(BASE + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
    with urlopen(req, timeout=15) as response:
        return response.read().decode()


def login(password):
    try:
        return request("/api/auth/login", {"email": EMAIL, "password": password}).strip()
    except HTTPError as error:
        if error.code not in (400, 401):
            raise
        return None


def main():
    password = json.load(sys.stdin)
    if not isinstance(password, str) or len(password) < 24:
        raise ValueError("Strong private admin input required")
    if "<html" not in request("/").lower() or "1.864.1" not in request("/api/version"):
        raise RuntimeError("UI or pinned API version did not respond")
    token = login(password)
    if not token:
        # The upstream factory account is reachable only on CT loopback.
        factory = login("changeme")
        if not factory:
            raise RuntimeError("Unknown existing admin identity; refusing to reset it")
        request("/api/users/setpassword", {"password": password}, factory)
        token = login(password)
        if not token or login("changeme"):
            raise RuntimeError("Admin initialization not verified")
    payload = {"language": "bash", "tag": "bash", "args": {},
               "content": "printf '%s\\n' windmill-smoke-ok", "path": "u/admin/infra_smoke"}
    workspace = "/api/w/admins"
    job = str(UUID(request(workspace + "/jobs/run/preview", payload, token).strip('" \r\n')))
    for _ in range(60):
        try:
            result = json.loads(request(workspace + "/jobs_u/completed/get/" + job, token=token))
        except HTTPError as error:
            if error.code != 404:
                raise
        else:
            if not result.get("success") or result.get("result") != "windmill-smoke-ok":
                raise RuntimeError("Worker returned unexpected result")
            workers = json.loads(request("/api/workers/list", token=token))
            if not any(w["worker"] == result.get("worker") and w.get("worker_group") == "default"
                       for w in workers):
                raise RuntimeError("Could not attribute completed job to a default worker")
            print("PASS: UI, API, private admin and completed default-worker job", job)
            return
        time.sleep(2)
    raise RuntimeError("No completed worker job within two minutes")


if __name__ == "__main__":
    main()
