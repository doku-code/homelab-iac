"""State of the NAS for the monitoring stack (TASK-037): what TrueNAS does not push in its Graphite stream.

Asks TrueNAS's own API (JSON-RPC over a WebSocket, the one that replaces the deprecated REST API) for the pools,
the datasets, the disks and their temperatures, the apps and the alerts, and serves them as metrics on :9110/metrics.
Read-only: it only calls query methods. Standard library only, so it runs from a ConfigMap on a stock image.

Environment: TRUENAS_URL (wss://host:port/api/current), TRUENAS_API_KEY, TRUENAS_VERIFY=false for the
self-signed certificate TrueNAS ships with.
"""
import base64
import json
import os
import socket
import ssl
import struct
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

URL = os.environ.get("TRUENAS_URL", "wss://192.168.0.13:444/api/current")
VERIFY = os.environ.get("TRUENAS_VERIFY", "true").lower() != "false"
CACHE_SECONDS = 30


class Session:
    """One WebSocket connection: just enough of RFC 6455 for request and answer in text frames."""

    def __init__(self, url, verify=True, timeout=30):
        parts = urllib.parse.urlsplit(url)
        raw = socket.create_connection((parts.hostname, parts.port or 443), timeout=timeout)
        context = ssl.create_default_context()
        if not verify:
            context.check_hostname, context.verify_mode = False, ssl.CERT_NONE
        self.sock = context.wrap_socket(raw, server_hostname=parts.hostname)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {parts.path or '/'} HTTP/1.1\r\nHost: {parts.hostname}:{parts.port or 443}\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        self.buffer = b""
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("closed during the handshake")
            head += chunk
        head, self.buffer = head.split(b"\r\n\r\n", 1)
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError("no WebSocket here: " + head.split(b"\r\n", 1)[0].decode("latin-1"))
        self.number = 0

    def _read(self, count):
        while len(self.buffer) < count:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("closed")
            self.buffer += chunk
        data, self.buffer = self.buffer[:count], self.buffer[count:]
        return data

    def _send(self, opcode, payload):
        mask = os.urandom(4)
        size = len(payload)
        head = bytes([0x80 | opcode]) + (bytes([0x80 | size]) if size < 126 else
                                         bytes([0x80 | 126]) + struct.pack(">H", size) if size < 65536 else
                                         bytes([0x80 | 127]) + struct.pack(">Q", size))
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def _receive(self):
        message = b""
        while True:
            first, second = self._read(2)
            opcode, size = first & 0x0F, second & 0x7F
            if size == 126:
                (size,) = struct.unpack(">H", self._read(2))
            elif size == 127:
                (size,) = struct.unpack(">Q", self._read(8))
            payload = self._read(size)
            if opcode == 0x9:
                self._send(0xA, payload)
            elif opcode == 0x8:
                raise ConnectionError("closed by TrueNAS")
            elif opcode in (0x0, 0x1, 0x2):
                message += payload
                if first & 0x80:
                    return message.decode()

    def call(self, method, *params):
        self.number += 1
        self._send(0x1, json.dumps({"jsonrpc": "2.0", "id": self.number, "method": method, "params": list(params)}).encode())
        while True:
            answer = json.loads(self._receive())
            if answer.get("id") != self.number:
                continue  # a notification
            if "error" in answer:
                error = answer["error"]
                raise RuntimeError(f"{method}: {(error.get('data') or {}).get('reason') or error.get('message')}")
            return answer["result"]

    def close(self):
        try:
            self._send(0x8, b"")
            self.sock.close()
        except OSError:
            pass


def connect():
    session = Session(URL, VERIFY)
    if not session.call("auth.login_with_api_key", os.environ["TRUENAS_API_KEY"]):
        session.close()
        raise RuntimeError("TrueNAS refused the API key")
    return session


def label(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def collect():
    lines = []

    def metric(name, text, samples):
        lines.append(f"# HELP {name} {text}")
        lines.append(f"# TYPE {name} gauge")
        for labels, value in samples:
            inside = ",".join(f'{key}="{label(item)}"' for key, item in labels.items())
            lines.append(f"{name}{{{inside}}} {float(value)}" if inside else f"{name} {float(value)}")

    session = connect()
    try:
        info = session.call("system.info")
        metric("truenas_info", "Version of TrueNAS.", [({"version": info["version"]}, 1)])
        pools = session.call("pool.query")
        metric("truenas_pool_healthy", "1 when ZFS reports the pool healthy.", [({"pool": p["name"]}, p["healthy"]) for p in pools])
        metric("truenas_pool_status", "Status of the pool, as a label.", [({"pool": p["name"], "status": p["status"]}, 1) for p in pools])
        sized = [p for p in pools if p.get("size")]
        metric("truenas_pool_size_bytes", "Raw size of the pool.", [({"pool": p["name"]}, p["size"]) for p in sized])
        metric("truenas_pool_allocated_bytes", "Space written in the pool.", [({"pool": p["name"]}, p["allocated"]) for p in sized])
        metric("truenas_pool_free_bytes", "Space left in the pool.", [({"pool": p["name"]}, p["free"]) for p in sized])
        datasets = [d for d in session.call("pool.dataset.query", [], {"extra": {"flat": True, "properties": ["used", "available"]}})
                    if d["id"].count("/") <= 1 and d.get("used")]
        metric("truenas_dataset_used_bytes", "Space used by the dataset and what is under it (pools and their first level).",
               [({"dataset": d["id"]}, d["used"]["parsed"]) for d in datasets])
        metric("truenas_dataset_available_bytes", "Space the dataset can still take.",
               [({"dataset": d["id"]}, d["available"]["parsed"]) for d in datasets])
        disks = session.call("disk.query", [], {"extra": {"pools": True}})
        metric("truenas_disk_info", "Which device name and pool a disk identifier (WWN) of the Graphite metrics is.",
               [({"disk": d["name"], "disk_id": d.get("lunid") or "", "pool": d.get("pool") or ""}, 1) for d in disks])
        temperatures = session.call("disk.temperatures", [], False)
        metric("truenas_disk_temperature_celsius", "Temperature the disk reports.",
               [({"disk": name}, value) for name, value in sorted(temperatures.items()) if value is not None])
        apps = session.call("app.query")
        metric("truenas_app_running", "1 when the app is in the state RUNNING.", [({"app": a["name"]}, a["state"] == "RUNNING") for a in apps])
        metric("truenas_app_upgrade_available", "1 when the catalog has a newer version of the app.",
               [({"app": a["name"]}, bool(a.get("upgrade_available"))) for a in apps])
        alerts = [a for a in session.call("alert.list") if not a.get("dismissed")]
        metric("truenas_alerts", "Alerts TrueNAS shows that nobody dismissed, by level.",
               [({"level": level}, sum(a["level"] == level for a in alerts)) for level in ("INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL", "ALERT", "EMERGENCY")])
    finally:
        session.close()
    return lines


class State:
    lock, at, lines = threading.Lock(), 0.0, []


def metrics():
    with State.lock:
        if time.time() - State.at > CACHE_SECONDS:
            try:
                State.lines = collect() + ["# TYPE truenas_exporter_up gauge", "truenas_exporter_up 1"]
            except Exception as error:  # the NAS is away or refuses: say so in a metric and in the log, never crash
                print(f"collect failed: {type(error).__name__}: {error}", flush=True)
                State.lines = ["# TYPE truenas_exporter_up gauge", "truenas_exporter_up 0"]
            State.at = time.time()
        return "\n".join(State.lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (metrics() if self.path == "/metrics" else "ok\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("", 9110), Handler).serve_forever()
