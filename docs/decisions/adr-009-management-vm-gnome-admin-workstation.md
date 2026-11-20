---
title: 'ADR-009: Management VM as a GNOME admin workstation'
description: mgmt-control-01 is a GNOME admin workstation (Ubuntu 26.04, 8 vCPU host type, 10 GiB, 120 GiB) with RDP remote login, the IaC toolchain, Claude Code and Codex.
published: true
tags:
- decision
- accepted
- management
- workstation
- desktop
- pve-management
editor: markdown
date: '2026-11-14T00:00:00.000Z'
dateCreated: '2026-11-14T00:00:00.000Z'
---

# ADR-009: Management VM as a GNOME admin workstation

> **ID:** ADR-009 · **Type:** decision · **Status:** accepted · **Updated:** 2026-11-14 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/docs/decisions/ADR-009-management-vm-gnome-admin-workstation.md)

## Context

ADR-002 planned an Ubuntu Server management VM. The operator wants to manage and deploy the homelab
from that VM interactively: a desktop session plus AI coding agents (Claude Code, Codex) next to the
IaC toolchain. `pve-management` has 6 cores / 12 threads and 15.3 GiB RAM (discovery, 2026-11-14).

## Decision

- `mgmt-control-01` is a regular **Ubuntu Desktop 26.04.1 LTS** installed from the official ISO (operator,
  2026-11-14: a genuine Desktop install, not Server plus a desktop), unattended by autoinstall: the
  installer finds its NoCloud seed over HTTP from the operator workstation through the SMBIOS serial and
  asks for one confirmation on the Proxmox console. Std VGA so the Proxmox console shows GDM and the
  desktop; NetworkManager with the static `192.168.0.39/24`; 8 vCPU, 10 GiB RAM, 120 GiB thin disk with
  discard. Ansible (`admin_workstation`) then adds the tooling and remote login.
  CPU type `host`: the VM has no GPU, so GNOME, the RDP encoder and Zed render in software (llvmpipe /
  lavapipe), which needs AVX2; `x86-64-v2-AES` hides it, and a standalone host never live-migrates.
- It is still built reproducibly by the same OpenTofu root and Ansible playbook, provisioned from the
  existing infrastructure on a minimal hypervisor (`pve-management`, founding node of the new cluster,
  ADR-010).
- The desktop login and RDP passwords are entered interactively at configuration time and never stored.
- Its tooling is a declarative catalog in `ansible/roles/admin_workstation/defaults/main.yml`: apt for
  system and CLI tools (incl. Docker), Flathub for GUI apps (Zed, Obsidian, Sublime Merge — SourceTree
  has no Linux build), mise for runtimes and versioned CLIs (Node.js, Python, Go, uv, Terraform 1.16.1,
  kubectl, Infisical CLI, Claude Code and Codex as native checksummed binaries). OpenTofu stays the
  infrastructure tool; Terraform is only for the legacy roots. No piped installers; the mise apt key is
  pinned by SHA256. Flatpak apps are installed system-wide; mise tools as the admin user.
- Daily access is **GNOME Remote Login** (`grdctl --system`: the system daemon serving the GDM login
  screen, not per-user desktop sharing) over RDP from the operator's Thincast client, self-signed TLS.
  Login has two stages: (1) the RDP credentials (`ubuntu` + RDP password) open the remote GDM greeter;
  (2) the Linux account (`ubuntu` + desktop password) starts a headless GNOME session, to which the
  client is redirected automatically (RDP server redirection).
- `ufw` allows RDP (3389/tcp) only from `admin_workstation_rdp_allowed_networks` (default
  `192.168.0.0/24`) and keeps SSH open; everything else incoming is denied.
- Access paths are independent: SSH (key-only, never passwords), the Proxmox console (VGA: GDM or a
  TTY with the Linux password) and RDP. Losing RDP never removes SSH or the console.

## Consequences

- About 5 GiB remain, ~3.5 GiB after hypervisor overhead, for later management VMs; Phase and Windmill
  (M002/M003) need either a RAM upgrade or placement elsewhere, decided in those milestones. Memory can
  be lowered back to 8 GiB by a reviewed plan (in-place change, one reboot).
- GDM allows one graphical session per user: log out of a console desktop session before using RDP.
- Ports published by Docker containers bypass `ufw` (Docker writes its own rules); bind development
  containers to `127.0.0.1` when they must not be reachable from the LAN.
- The workstation holds operator credentials (Proxmox token, AI agent logins): it is a high-value
  machine; recovery still works from any administrator workstation (ADR-008).
