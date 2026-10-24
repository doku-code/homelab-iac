"""Bounded existing-VM conversion; no disk, identity, power or state operations."""
import json
from pathlib import Path
import re
import subprocess
import sys

GPU = "pve-lab-workstation-gpu"
USB = {"pve-lab-workstation-" + n for n in ("logitech", "keyboard", "brio", "scarlett")}
HOOK = "local:snippets/pve-workstation-exclusive.sh"


def read(path):
    return json.loads(subprocess.check_output(["pvesh", "get", path, "--output-format", "json"]))


def changes(config):
    remove = []
    for key, value in config.items():
        if re.fullmatch(r"hostpci\d+", key):
            if key != "hostpci0" or value.split(",")[0] != "mapping=" + GPU:
                raise ValueError("Unexpected PCI assignment; review before conversion")
            remove.append(key)
        if re.fullmatch(r"usb\d+", key):
            if value.split(",")[0].removeprefix("mapping=") not in USB:
                raise ValueError("Unexpected USB assignment; review before conversion")
            remove.append(key)
    if config.get("hookscript"):
        if config["hookscript"] != HOOK:
            raise ValueError("Unrelated hook must not be removed")
        remove.append("hookscript")
    options = {}
    if config.get("vga") != "std,memory=32":
        options["vga"] = "std,memory=32"
    if config.get("tablet") != 1:
        options["tablet"] = "1"
    return sorted(remove), options


def main():
    mode, names = sys.argv[1], json.loads(sys.argv[2])
    assert mode in ("--check", "--apply")
    assert subprocess.check_output(["hostname", "-s"], text=True).strip() == "pve-lab"
    prepared = []
    # Validate every guest and mapping consumer before the first change.
    for vmid, name in names.items():
        assert vmid.isdecimal()
        base = f"/nodes/pve-lab/qemu/{vmid}"
        config = read(base + "/config")
        assert config["name"] == name, "Guest identity mismatch"
        pending = read(base + "/pending")
        assert not any("pending" in p or p.get("delete") for p in pending), "Pending VM changes"
        remove, options = changes(config)
        if remove or options:
            assert read(base + "/status/current")["status"] == "stopped", "Stop affected VM gracefully first"
        prepared.append((vmid, base, config, remove, options))
    retired = USB | {GPU, "pve-lab-workstation-kvm", HOOK}
    for path in Path("/etc/pve/nodes").glob("*/qemu-server/*.conf"):
        if path.parent.parent.name == "pve-lab" and path.stem in names:
            continue
        assert not any(value in path.read_text() for value in retired), "Other mapping/hook consumer remains"
    mappings = []
    for kind, selected in (("usb", USB), ("pci", {GPU, "pve-lab-workstation-kvm"})):
        for item in read(f"/cluster/mapping/{kind}"):
            if item["id"] in selected:
                assert all(m.startswith("node=pve-lab,") for m in item["map"]), "Mapping shared with another host"
                mappings.append((kind, item["id"]))
    for vmid, base, before, remove, options in prepared:
        if not remove and not options:
            print(f"OK VM{vmid}: already virtual-only")
            continue
        print(f"CHANGED VM{vmid}: remove {','.join(remove)}; set {','.join(options)}")
        if mode == "--check":
            continue
        command = ["qm", "set", vmid, "--digest", before["digest"]]
        if remove:
            command += ["--delete", ",".join(remove)]
        for key, value in options.items():
            command += ["--" + key, value]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        after = read(base + "/config")
        allowed = set(remove) | set(options) | {"digest"}
        assert {k:v for k,v in before.items() if k not in allowed} == {
            k:v for k,v in after.items() if k not in allowed}, "Unexpected non-console configuration change"
        assert changes(after) == ([], {}), "Conversion readback mismatch"
    for kind, name in mappings:
        print(f"CHANGED retire {kind} mapping {name}")
        if mode == "--apply":
            subprocess.run(["pvesh", "delete", f"/cluster/mapping/{kind}/{name}"], check=True)


if __name__ == "__main__":
    main()
