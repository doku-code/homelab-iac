# PostgreSQL backend host bootstrap

Authoritative operator allocation: CT300 on pve-core, `192.168.0.30/24`,
hostname `tfstate`, gateway `192.168.0.1`, resolver `192.168.0.20`, search
domain `home.arpa`. The former CT300 Forgejo runner is permanently retired;
the active runner remains CT301. VMID210 is not allocated by this root.

This is a NEW isolated root and NEW CT identity, not an import, move or reuse
of the historical runner Terraform state. Keep its backend LOCAL permanently.
Never copy the old runner state or backend metadata here. Never migrate this
root into the PostgreSQL service it creates.

Sizing: one CPU, 2048 MiB RAM, 512 MiB swap, 16 GiB local-lvm, unprivileged
Debian 13 without nesting. Preflight discovery found VMID300 absent, no live
guest network configuration using .30, and the canonical Debian 13 template
available on pve-core. The operator completed the approved initial apply on
2026-09-24: one added, zero changed, zero destroyed. CT300 now exists and is
managed by this root; do not expect its VMID to remain absent after creation.

## Plan and reviewed apply

From the repository root in the existing authenticated operator shell:

```sh
make tfstate-plan
```

The target uses the shared Universal Auth wrapper, formats/checks/initializes/
validates this root and saves `tfstate.tfplan` inside it. It never plans an
existing stack. The approved initial plan contained exactly one create,
`proxmox_virtual_environment_container.tfstate`, on pve-core/300 with the
allocation above; zero changes and zero destroys. Now that creation is complete,
an unchanged host configuration should produce a no-change plan. Any further
change requires fresh review; never recreate the deployed CT to repeat setup.

Only after operator review, run `make tfstate-apply`. This applies exactly
the saved plan without replanning or supplying different variable values.
Saved-plan apply does not prompt again. No automatic Ansible or other stack
apply follows it. Credentials, state, private inputs and saved plans remain
outside Git. Missing runtime credentials are an operator execution boundary,
not permission to invent another authentication mechanism.

## PostgreSQL deployment and qualification

This root alone does not install PostgreSQL. `make tfstate-configure` converges
only this CT through the dedicated Ansible inventory/role. PostgreSQL 17.11
is deployed and loopback-only; `make tfstate-check` validates playbook syntax.
`make tfstate-qualify` runs disposable tests through verified SSH forwarding,
not a production backend or a Forgejo workflow. No production state databases
have been created.

Passed gates: remote state CRUD, native two-client mutual exclusion, observed
advisory locks, crashed-session lock release, cross-root database isolation,
narrow PBS inclusion, and isolated logical backup/restore. Temporary databases
and credentials were removed. No existing state migration is authorized.
See the [qualification report](../../../docs/terraform-pg-backend-qualification.md)
for measured results, historical runner/PBS ambiguity and remaining limits.

The eventual endpoint is `tfstate.doku-lab.net:5432` with native PostgreSQL TLS,
not an HTTP reverse proxy. Direct-IP trusted-LAN disposable qualification is
permitted with restricted clients; final DNS/TLS is required for production.
See [the backend design](../../../docs/terraform-pg-backend-design.md).
