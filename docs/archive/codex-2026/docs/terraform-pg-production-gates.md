# PostgreSQL production-candidate gates

Updated checkpoint: 2026-09-24. PostgreSQL is NOT yet a qualified production
candidate. DNS now passes; TLS stops at the scoped credential-delivery gate.
Independent [scheduled backup work](terraform-pg-backups.md) was implemented
and qualified. No existing Terraform state was migrated.
The prior [disposable qualification](terraform-pg-backend-qualification.md)
remains valid only for its tested SSH-forwarded transport.

## Current evidence

| Gate | Status | Evidence or missing action |
| --- | --- | --- |
| Guest and PostgreSQL service | PASS | CT300 running, PostgreSQL 17 cluster active |
| Final DNS endpoint | PASS | Mac system resolver and AdGuard .20 query, CT301 and CT300 resolve tfstate.doku-lab.net directly to .30 |
| Certificate hostname | FAIL | Live certificate SAN is tfstate.home.arpa, not tfstate.doku-lab.net; openssl checkhost rejects it |
| Trusted issuance/deployment/renewal | PENDING OPERATOR ACTION | Dedicated DNS-01 certificate approved; scoped credentials and autonomous secret delivery still unavailable |
| Verified TLS and negative handshake tests | NOT TESTED | Final-endpoint verify-full, wrong-host/untrusted-chain handshakes and renewal tests await issuance |
| Current network containment | PASS | listen_addresses=127.0.0.1; peer postgres administration; qualification-group loopback SCRAM only, otherwise reject |
| Final hostssl/client restrictions | PENDING OPERATOR ACTION | Need stable operator address and verified CI job egress before exact allowlists |
| Production operator/CI identities | NOT TESTED | No production databases or logins created; prior disposable least-privilege model passed |
| Infisical production injection | PENDING OPERATOR ACTION | Neither runtime Universal Auth credential is present here; write permission unknown, not presumed denied |
| Scheduled logical backup mechanism | PASS | Ansible timer enabled at 02:00 America/Toronto; actual service ran successfully; restore from its output passed |
| External backup copy | PASS | CT300-only PBS snapshot 2026-09-24T15:02:50Z uploaded to .15/backup-store, including logical dump sets |
| Backup encryption/alerting/scheduled firing | NOT TESTED | PBS crypt-mode=none; at-rest protection unqualified; local systemd failure reporting only; next scheduled timer firing still pending |
| Logical restore | PASS | Prior isolated disposable restore matched full state and yielded no-change plan |
| PBS inclusion | PASS | Existing job still includes 300; schedule, retention, storage and other VMIDs unchanged |
| Full PBS guest restore | PENDING OPERATOR ACTION | New PostgreSQL snapshot exists alongside six preserved runner snapshots; isolated restore allocation still required |
| SSH-forwarded CRUD/locking/crash/isolation | PASS | Prior real Terraform 1.16.1 qualification, including waiting client and killed-client recovery |
| Final-endpoint CRUD/locking/crash/isolation | NOT TESTED | No rerun over native verified TLS; no CI workflow launched |
| Local bootstrap backend | PASS | Explicit local backend; no migration |
| Independent bootstrap recovery copy | NOT TESTED | No verified protected off-Mac/off-CT300 copy established |

Live PostgreSQL has `ssl=on`, but uses
`/etc/ssl/certs/ssl-cert-snakeoil.pem` and its private-key path. No private key
was read. Public metadata: issuer and subject `tfstate.home.arpa`, SAN
`tfstate.home.arpa`, valid September 24, 2026 through September 21, 2036.
Enabling SSL is not proof of trusted hostname-verified TLS.

The operator SSH source observed by CT300 is now `192.168.0.114`, compared
with `.111` during the earlier qualification. Do not hardcode either as a
durable operator reservation without confirmation. CT301's route to .30 uses
source `.31`; this establishes host routing, not a containerized job's egress.
Its resolver is `.20`. No runner registration, configuration or workflow changed.

## Certificate and DNS decision

The DNS rewrite is operator-managed; adopt it in a separate broader AdGuard
IaC milestone. No managed rewrite or PostgreSQL certificate-delivery workflow
exists here. Read-only live inspection via trusted pve-infra/pct confirmed
Caddy CT204 owns issuance and renewal through its ACME/Cloudflare modules,
local Caddyfile and `/etc/systemd/system/caddy.service.d/cloudflare.conf`.
The drop-in loads `/etc/caddy/cloudflare.env`; the running service has the
token (presence only verified). No values or private keys were output/copied,
and no Caddy settings were changed. No tfstate certificate subject is configured.

The single-name Cloudflare DNS-01 certificate is operator-approved. Selected
implementation direction: dedicated Certbot DNS-01 renewal on always-on CT300,
managed through Ansible, rather than depending on Mac uptime or adapting the
unmanaged Caddy service into a cross-host private-key distributor. This reuses
the CA/DNS-01 model, without copying Caddy's service token or certificate keys. No ACME package
or renewal service was installed because authorized runtime credentials and
a least-privilege autonomous secret-delivery path are unavailable.

Required authorization: a dedicated Cloudflare token limited to DNS Edit for
the doku-lab.net zone, stored in the existing Infisical project, with a narrowly
scoped runtime read identity and approved protected bootstrap delivery to
CT300. Do NOT copy the general controller identity or Caddy token onto CT300.
Zone scope still permits changes beyond this hostname; approve that risk or
separately approve delegation to a restricted ACME zone. The proposed secret
folder is `/terraform/backend/postgresql/tls`, key `CLOUDFLARE_API_TOKEN`;
live path/permission discovery is blocked by absent runtime Universal Auth
credentials, so check for existing conventions before creating/overwriting it.
See [Certbot's token requirements](https://certbot-dns-cloudflare.readthedocs.io/en/stable/).

After authorization, use a private runtime-only credential file retrieved from
Infisical for issuance/renewal, clean it afterward, validate the certificate
and matching key before deployment, retain previous material on failure and
reload PostgreSQL after atomic installation. This is a design, NOT a tested
renewal mechanism. Do not silently add long-lived plaintext API-token files.

DNS-01 can validate using public challenge TXT records without exposing the
database port; this does not authorize a public service A/AAAA record, ingress
or token reuse. See [Let's Encrypt challenge guidance](https://letsencrypt.org/docs/challenge-types/).

The operator already added the AdGuard rewrite; no further DNS change is
needed. There is no Caddy HTTP route or public service record to create.

Firewall discovery: CT300 has no explicit guest Proxmox firewall rules;
node/guest option responses were empty apart from digests. The cluster API
query failed with a Proxmox schema error; read-only cluster configuration
contained no enable/policy options. An active pve-firewall daemon alone does
not prove effective filtering. No host/guest firewall was changed. PostgreSQL
remains loopback-only pending verified TLS and stable approved source addresses.
CT301 has a bridge network named podman, but no running job containers were
available to observe actual egress; .31 must not be assumed for every job.

Production database secrets should not be invented before per-root identities
are provisioned. Future operator UI delivery is the existing Homelab-IaC
Infisical project/environment: distinct per-root `operator` and `ci` folders
with PGUSER/PGPASSWORD, limited identity access, and no credential values in
chat. Exact role/path provisioning awaits the security gate; absent runtime
credentials do not justify an elevated identity or another authentication path.

## Measured baseline for later Consul comparison

No Consul deployment or winner selection. Point-in-time idle observations,
not load benchmarks:

- Allocation: 1 vCPU, 2 GiB RAM, 512 MiB swap, 16 GiB disk.
- Proxmox reported CPU fraction 0 and guest memory 64,184,320 bytes (~61 MiB).
- Latest guest free reported used RAM 84,178,944 bytes (~80 MiB), swap use zero;
  different accounting from Proxmox, not a workload peak.
- Latest root filesystem used 1,087,565,824 bytes (~1.01 GiB).
- PostgreSQL data directory measured 57,180,934 bytes (~54.5 MiB).
- Native pg state and session advisory locks; one database per independent
  root. Prior real contention/crash tests passed, not yet final TLS transport.
- Native Debian PG17 service; Ansible manages installation/configuration.
  Security patch maintenance, major-version upgrade/restore qualification,
  certificate renewal, identity lifecycle and backup operations remain costs.
- Scheduled-service logical dump/isolated restore and external PBS upload now
  pass. Full PBS recovery, at-rest protection and off-host failure alerts
  remain unproven; see the backup report for actual evidence and limitations.
- Single pve-core guest/root disk: no HA or measured failover, RPO or RTO.
  Connection loss can interrupt work; killed-client release evidence is not
  a bound for silent network failure.
- Dependencies: local Terraform bootstrap state, Proxmox/template/storage,
  authorized SSH controller, Debian packages, and eventually internal DNS,
  CA/renewal, runtime Infisical and independently recoverable PBS storage.
  Keep an encrypted/versioned off-Mac recovery copy of the local bootstrap
  state and required public configuration/trust material, with separately
  protected credentials and restore instructions. Such a copy is a recovery
  artifact, never a second writable authoritative state. Destination/access
  and recovery verification remain unapproved/unverified.

Before full PBS recovery, propose a fresh operator-approved temporary VMID,
storage budget and isolated/disconnected network. Restore a verified NEW
PostgreSQL snapshot, never overwrite CT300 or boot a clone onto its .30 IP.
No additional guest was allocated or restored at this checkpoint.
