# PostgreSQL production-candidate gates

Read-only checkpoint: 2026-09-24. PostgreSQL is NOT yet a qualified production
candidate. This checkpoint stops at the DNS/operator and TLS issuance gates;
no live configuration was changed. No existing Terraform state was migrated.
The prior [disposable qualification](terraform-pg-backend-qualification.md)
remains valid only for its tested SSH-forwarded transport.

## Current evidence

| Gate | Status | Evidence or missing action |
| --- | --- | --- |
| Guest and PostgreSQL service | PASS | CT300 running, PostgreSQL 17 cluster active |
| Final DNS endpoint | PENDING OPERATOR ACTION | AdGuard .20 returns NXDOMAIN for tfstate.doku-lab.net; Mac system lookup and CT301 getent also fail |
| Certificate hostname | FAIL | Live certificate SAN is tfstate.home.arpa, not tfstate.doku-lab.net; openssl checkhost rejects it |
| Trusted issuance/deployment/renewal | PENDING OPERATOR ACTION | Only Debian snakeoil certificate configured; no approved external certificate delivery/renewal owner |
| Verified TLS and negative handshake tests | NOT TESTED | Final-endpoint verify-full, wrong-host/untrusted-chain handshakes and renewal tests await issuance |
| Current network containment | PASS | listen_addresses=127.0.0.1; peer postgres administration; qualification-group loopback SCRAM only, otherwise reject |
| Final hostssl/client restrictions | PENDING OPERATOR ACTION | Need stable operator address and verified CI job egress before exact allowlists |
| Production operator/CI identities | NOT TESTED | No production databases or logins created; prior disposable least-privilege model passed |
| Infisical production injection | PENDING OPERATOR ACTION | Neither runtime Universal Auth credential is present here; write permission unknown, not presumed denied |
| Scheduled logical backups/off-host copy | NOT TESTED | No PostgreSQL backup timer observed; no scheduled mechanism or protected export implemented |
| Logical restore | PASS | Prior isolated disposable restore matched full state and yielded no-change plan |
| PBS inclusion | PASS | Existing job still includes 300; schedule, retention, storage and other VMIDs unchanged |
| New PostgreSQL PBS snapshot/full restore | NOT TESTED | Only six pre-deployment runner snapshots listed; no isolated restore allocation approved |
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

Repository inspection found no managed AdGuard rewrite workflow and no native
PostgreSQL certificate issuance/deployment mechanism. Existing documentation
records Caddy Cloudflare DNS-01, a local Caddyfile and a credential-bearing
service drop-in. These are not authorization to read/copy its credential,
private keys or shared wildcard certificate. Caddy was not modified or accessed.

Proposed decision for operator approval: a dedicated single-name certificate
from Let's Encrypt using Cloudflare DNS-01, with issuance/renewal on an
operator-approved controller and narrowly scoped credentials kept outside
CT300. Deploy only the certificate chain and private key through Ansible,
validate before atomic replacement, then reload PostgreSQL. Controller
availability, unattended credential access, expiry alerting and renewal
ownership must be agreed before implementing this proposal. An existing
approved internal CA is an alternative if its trust distribution and renewal
are already operated. No new CA or ACME service was installed.

DNS-01 can validate using public challenge TXT records without exposing the
database port; this does not authorize a public service A/AAAA record, ingress
or token reuse. See [Let's Encrypt challenge guidance](https://letsencrypt.org/docs/challenge-types/).

Exact DNS operator action: in the existing AdGuard Home UI, open **Filters >
DNS rewrites**, add domain `tfstate.doku-lab.net` with answer `192.168.0.30`,
and save. Do not point it at Caddy. This UI area is documented in the
[AdGuard Home FAQ](https://github.com/AdguardTeam/AdGuardHome/wiki/FAQ).
After confirmation, recheck both clients before changing PostgreSQL listening.

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
- Guest free reported used RAM 77,062,144 bytes (~73 MiB), swap use zero;
  different accounting from Proxmox, not a workload peak.
- Root filesystem used 1,087,492,096 bytes (~1.01 GiB).
- PostgreSQL data directory measured 57,180,934 bytes (~54.5 MiB).
- Native pg state and session advisory locks; one database per independent
  root. Prior real contention/crash tests passed, not yet final TLS transport.
- Native Debian PG17 service; Ansible manages installation/configuration.
  Security patch maintenance, major-version upgrade/restore qualification,
  certificate renewal, identity lifecycle and backup operations remain costs.
- Logical dump/restore is proven on disposable data; scheduled logical export,
  protected external copy and full PBS recovery are not proven.
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
