#!/usr/bin/env python3
"""Hardware facts of the machine it runs on, as one JSON document on standard output (M013).

Run as root on a Proxmox host by `make netbox-discover-hardware` (piped over SSH: nothing is installed or
left on the host). Read-only: it reads /sys, /proc, dmidecode, lsblk, ethtool and listens (never sends) for
the neighbour announcement (LLDP) a managed switch repeats on each wired port, which tells the switch's
name, model and the port this machine is plugged into. Standard library only.

  host-facts.py [--lldp-seconds N]     N=0 skips the listening (default 35: switches announce every 30 s)
"""
import json
import os
import re
import socket
import subprocess
import sys
import time

LLDP = 0x88CC


def run(*argv):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def read(path):
    try:
        with open(path) as handle:
            return handle.read().strip()
    except OSError:
        return None


def dmi():
    keys = {"manufacturer": "system-manufacturer", "product": "system-product-name", "version": "system-version",
            "serial": "system-serial-number", "sku": "system-sku-number", "family": "system-family",
            "board_manufacturer": "baseboard-manufacturer", "board_product": "baseboard-product-name",
            "board_serial": "baseboard-serial-number", "bios_version": "bios-version", "bios_date": "bios-release-date",
            "chassis_type": "chassis-type"}
    placeholder = re.compile(r"^(|default string|to be filled by o\.e\.m\.|system (product name|version|manufacturer|serial number)|"
                             r"not (specified|applicable)|none|sku|o\.e\.m\.|0+|x+)$", re.I)
    out = {}
    for name, key in keys.items():
        value = run("dmidecode", "-s", key).strip().splitlines()
        value = value[-1].strip() if value else ""
        out[name] = None if placeholder.match(value) else value
    return out


def memory_modules():
    modules = []
    for block in run("dmidecode", "-t", "17").split("\n\n"):
        fields = dict(line.strip().split(": ", 1) for line in block.splitlines() if ": " in line)
        size = fields.get("Size", "")
        match = re.match(r"(\d+) (MB|GB)", size)
        if not match:
            continue  # empty slot
        modules.append({"slot": fields.get("Locator"), "size_mb": int(match.group(1)) * (1024 if match.group(2) == "GB" else 1),
                        "type": fields.get("Type"), "speed": fields.get("Speed"), "manufacturer": fields.get("Manufacturer"),
                        "part_number": (fields.get("Part Number") or "").strip() or None,
                        "serial": (fields.get("Serial Number") or "").strip() or None})
    return modules


def cpu():
    info = read("/proc/cpuinfo") or ""
    models = re.findall(r"^model name\s*: (.+)$", info, re.M)
    sockets = len(set(re.findall(r"^physical id\s*: (\d+)$", info, re.M))) or 1
    cores = {(p, c) for p, c in re.findall(r"^physical id\s*: (\d+)$.*?^core id\s*: (\d+)$", info, re.M | re.S)}
    return {"model": models[0] if models else None, "sockets": sockets, "cores": len(cores) or None, "threads": len(models)}


def disks():
    try:
        devices = json.loads(run("lsblk", "-J", "-d", "-b", "-o", "NAME,MODEL,SERIAL,SIZE,TRAN,ROTA,TYPE"))["blockdevices"]
    except ValueError:
        return []
    return [{"name": d["name"], "model": (d.get("model") or "").strip() or None, "serial": (d.get("serial") or "").strip() or None,
             "size_gb": round(int(d["size"]) / 1e9), "transport": d.get("tran"), "rotational": bool(d.get("rota"))}
            for d in devices if d.get("type") == "disk" and int(d.get("size") or 0) > 0 and not d["name"].startswith(("zd", "loop", "ram"))]


def pci_name(device_path):
    slot = os.path.basename(os.path.realpath(device_path))
    text = run("lspci", "-s", slot)
    return text.split(": ", 1)[1].strip() if ": " in text else None


def interfaces():
    found = []
    for name in sorted(os.listdir("/sys/class/net")):
        base = f"/sys/class/net/{name}"
        physical = os.path.exists(f"{base}/device")
        bridge = os.path.isdir(f"{base}/bridge")
        if not (physical or bridge) or name.startswith(("veth", "tap", "fwbr", "fwpr", "fwln")):
            continue
        permanent = run("ethtool", "-P", name).split("address: ")[-1].strip() if physical else None
        speed = read(f"{base}/speed")
        master = os.path.basename(os.path.realpath(f"{base}/master")) if os.path.exists(f"{base}/master") else None
        supported = re.findall(r"(\d+)base", run("ethtool", name).split("Advertised", 1)[0]) if physical else []
        entry = {"name": name, "kind": "bridge" if bridge else ("wireless" if os.path.isdir(f"{base}/wireless") else "physical"),
                 "mac": (permanent if permanent and permanent != "00:00:00:00:00:00" else read(f"{base}/address") or "").upper() or None,
                 "up": read(f"{base}/operstate") == "up", "carrier": read(f"{base}/carrier") == "1",
                 "speed_mbps": int(speed) if speed and speed.lstrip("-").isdigit() and int(speed) > 0 else None,
                 "max_speed_mbps": max(map(int, supported)) if supported else None,
                 "mtu": int(read(f"{base}/mtu") or 0) or None, "master": master,
                 "driver": os.path.basename(os.path.realpath(f"{base}/device/driver")) if physical else None,
                 "model": pci_name(f"{base}/device") if physical else None,
                 "addresses": re.findall(r"inet (\S+)", run("ip", "-4", "-o", "addr", "show", "dev", name))}
        if bridge:
            entry["ports"] = sorted(p for p in os.listdir(f"{base}/brif") if not p.startswith(("veth", "tap", "fwpr", "fwln")))
        found.append(entry)
    return found


def decode_lldp(frame):
    """The few announcements that identify the neighbour and its port (IEEE 802.1AB)."""
    out, data = {}, frame[14:]
    while len(data) >= 2:
        header = int.from_bytes(data[:2], "big")
        kind, length = header >> 9, header & 0x1FF
        value, data = data[2:2 + length], data[2 + length:]
        if kind == 0:
            break
        text = lambda raw: raw.decode(errors="replace").strip("\x00 ")  # noqa: E731
        mac = lambda raw: ":".join(f"{b:02X}" for b in raw)  # noqa: E731
        if kind == 1 and value:
            out["chassis_id"] = mac(value[1:]) if value[0] == 4 else text(value[1:])
        elif kind == 2 and value:
            out["port_id"] = mac(value[1:]) if value[0] == 3 else text(value[1:])
        elif kind == 4:
            out["port_description"] = text(value)
        elif kind == 5:
            out["system_name"] = text(value)
        elif kind == 6:
            out["system_description"] = text(value)
        elif kind == 8 and len(value) > 5 and value[1] == 1:  # management address, IPv4
            out["management_address"] = ".".join(str(b) for b in value[2:6])
    return out


def lldp(names, seconds):
    """Listens on every named port at once; returns the first announcement seen on each."""
    sockets, seen = {}, {}
    for name in names:
        try:
            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(LLDP))
            sock.bind((name, LLDP))
            sock.settimeout(0.5)
            sockets[name] = sock
        except OSError:
            continue
    deadline = time.monotonic() + seconds
    while sockets and time.monotonic() < deadline and len(seen) < len(sockets):
        for name, sock in sockets.items():
            if name in seen:
                continue
            try:
                frame, address = sock.recvfrom(4096)
            except OSError:
                continue
            if address[2] != socket.PACKET_OUTGOING:
                seen[name] = decode_lldp(frame)
    for sock in sockets.values():
        sock.close()
    return seen


def main(argv):
    seconds = int(argv[argv.index("--lldp-seconds") + 1]) if "--lldp-seconds" in argv else 35
    nics = interfaces()
    wired = [n["name"] for n in nics if n["kind"] == "physical" and n["carrier"]]
    facts = {"hostname": socket.gethostname(), "taken": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
             "system": dmi(), "cpu": cpu(), "memory_mb": int(re.search(r"MemTotal:\s+(\d+)", read("/proc/meminfo")).group(1)) // 1024,
             "memory_modules": memory_modules(), "disks": disks(), "interfaces": nics,
             "neighbours": lldp(wired, seconds) if seconds > 0 else {},
             "os": {"kernel": os.uname().release, "pve": (run("pveversion").strip().split("/") + [None, None])[1]}}
    json.dump(facts, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main(sys.argv[1:])
