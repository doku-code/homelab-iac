---
title: TASK-033 — Clean CI runner ci-runner-01 on the new cluster, replacing CT301
description: One validation runner VM built by OpenTofu and Ansible serves every repository; the hand-grown CT301 on the old host is retired
published: true
tags:
- task
- in-progress
- ci
- runner
- migration
editor: markdown
date: '2026-11-24T00:00:00.000Z'
dateCreated: '2026-11-24T00:00:00.000Z'
---

# TASK-033 — Clean CI runner ci-runner-01 on the new cluster, replacing CT301

> **ID:** TASK-033 · **Type:** task · **Status:** in-progress · **Updated:** 2026-11-24 · [Source](https://git.doku-lab.net/Homelab/homelab-iac/src/branch/main/tasks/TASK-033-clean-ci-runner-ci-runner-01-on-the-new-cluster-replacing-ct.md)

## Goal

The validation runner of every repository is a VM of the new cluster, defined by an OpenTofu root and an Ansible
playbook, so the old host can be emptied. It replaces CT301 `forgejo-runner-migration`, which had grown by hand.

## Context

- CT301 ran 250 jobs of this repository and 34 of `oss-archive-manager` in 30 days; its labels `cem` and
  `forgejo-theme` had none. Its configuration had drifted from the role (a fourth registration and a cache
  volume added by hand); its 29 GB were a 20 GB work cache and 34 unpruned job images.
- Two runners, by trust: `ci-runner-01` runs code from any branch and holds no infrastructure credentials
  (ADR-008); `deploy-runner-01` holds the Proxmox token and only runs the gated deployment (ADR-014).
- One validation runner serves every repository: one Forgejo registration per repository or organisation, its
  label names the image the job runs in. A new repository is one more entry in `ci_runner_connections` and one
  more UUID/token pair in the store path `/forgejo-runner/connections`. Two jobs at a time.
- The four registrations of CT301 are reused (the pair of `oss-archive` was read from CT301 into the store, the
  other three and the registry login were already there and equal): nothing changed in Forgejo.
- Job images unused for two weeks are removed every night; named volumes are not.

## Acceptance criteria

- [x] `ci-runner-01` (VM 303, 192.168.0.33, `pve-core`) exists from `terraform/stacks/ci-runner`.
- [x] The runner declares the four registrations to Forgejo; the service on CT301 is stopped and disabled.
- [ ] A validation job of this repository succeeds on the new runner.
- [ ] The work cache of `oss-archive` is on the new runner.
- [x] Offline tests.
- [ ] CT301 deleted from the old host (operator's word).

## Verification

```
make ci-runner-check
scripts/secrets.py run /pve-management -- make ci-runner-plan MGMT_INPUT_SOURCE=env CI_RUNNER_ALLOCATION_REVIEWED=yes
scripts/secrets.py run /forgejo-runner/connections /forgejo-runner/registry -- make ci-runner-configure CI_RUNNER_CONFIGURE_APPROVED=yes
```

## Tests

| Test file | Covers | Command | Result |
|-----------|--------|---------|--------|
| terraform/stacks/ci-runner/tests/ci-runner.tftest.hcl | Placement, size, address, LAN resolver, own image copy; the old environment and the deployment runner's allocation are refused | `make ci-runner-check` | PASS, 3 runs (2026-11-24) |
| tests/ci-runner.py | Registrations and registry login only from the environment and never logged, no infrastructure credential, the labels this repository's workflows ask for, rendered runner configuration, image clean-up, Make guards | `make ci-runner-check` | PASS (2026-11-24) |

## Evidence

| Check | Result | Reference (commit / output / doc) | Date |
|-------|--------|-----------------------------------|------|
| Plan | `2 to add, 0 to change, 0 to destroy`; `VMID 303 and 192.168.0.33/24 are free in NetBox` | `make ci-runner-plan` | 2026-11-24 |
| Apply and configure | VM created; `ok=39 changed=26 failed=0` | `.local/ci-runner-apply.log`, `.local/ci-runner-configure-1.log` | 2026-11-24 |
| Runner | four registrations `declared successfully`, runner v13.0.0 (same as CT301), poller launched | `journalctl -u forgejo-runner` on the VM | 2026-11-24 |
| Old runner | no job was running; `forgejo-runner` stopped and disabled in CT301 | `systemctl is-active` → `inactive` | 2026-11-24 |
| Job on the new runner | not verified yet | | |
| Work cache copy | in progress | `.local/ci-runner-cache-copy.log` | |

## Completion summary

In progress. Remaining: see a validation job of this repository succeed on `ci-runner-01`; finish the copy of the
`oss-archive-cache` volume (20 GB, tar from CT301 into the new runner's volume) before the daily job of
`oss-archive-manager` (08:00 UTC); then CT301 can be deleted on the operator's word. Way back until then:
`systemctl enable --now forgejo-runner` in CT301 and stop the service on `ci-runner-01` (same registrations:
never both at once).
