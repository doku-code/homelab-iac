# 155 - Retire physical workstation passthrough

- Status: remote conversion LIVE VERIFIED; repository delivery in progress.
  Physical POST acceptance remains separate and pending.
- Scope: pve-lab and existing VM501/502/503/601/602 only; VM401 interruption and
  one normal host reboot with temporary quorum loss explicitly accepted.
- Owner/runbook: [headless workstations](../docs/workstations-headless.md).
- No QDevice, quorum-vote change, VM recreation or unrelated infrastructure work.

## Acceptance

- [x] Identify live affected guests, state ownership and host boot overrides.
- [x] Virtual-only Terraform profile preserves resource identities and disks.
- [x] Guarded Ansible conversion removes effective passthrough and obsolete hook.
- [x] Remove only workstation-owned VFIO/boot overrides; preserve IOMMU/iGPU.
- [x] One controlled reboot; management/quorum and normal GPU ownership recover.
- [x] Sequential boot/console/network checks; report guest-specific limitations.
- [x] Restore original guest power policy; unrelated guests remain unchanged.
- [ ] Local tests, reviewed commit/push, exact Forgejo CI and mirror verification.
- [ ] Operator physical power+Ethernet-only POST test (separate from remote work).

Provider authentication is unavailable to this execution environment. The
approved Proxmox CLI path is used; local Terraform state is not rewritten.
Authenticated refresh-only review remains an operator follow-up, not a second
state authority. Physical verification must not be claimed from remote tests.

Evidence: five graphical login/lock screens, virtual input events accepted,
four functioning agents (Fedora's disabled setting preserved), all guests
gracefully stopped after tests. VM401 restored. VM501 required disabling its
legacy software virtual display adapter; no driver uninstall. VM501/503 both
reported .51 during separate tests: do not run concurrently until addressing is
reviewed. This task did not change network identities or resolve that overlap.
