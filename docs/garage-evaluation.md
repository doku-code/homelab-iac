# Garage evaluation: rejected as a Terraform backend

## Decision (2026-09-23)

Garage **2.4.1** with Terraform **1.16.1** failed the required native S3 locking
gate. While client A was inside a blocking local provisioner with its
`.tflock` object present, a separate client B applied to the same state with
`use_lockfile = true` and `-lock-timeout=0s`. Client B exited **0** and changed
the remote state. A second disposable run confirmed this result.

This is a measured concurrency failure, not merely an unsupported-error
message or a documentation inference. No custom locking workaround was added.
No existing Terraform state was migrated, and no existing backend was edited.
Do not migrate even a canary state to this deployment.

## Deployment

- CT209, pve-core, system hostname `garage`, `192.168.0.29/24`.
  The Proxmox hostname field still needs the Terraform correction below.
- Gateway `192.168.0.1`, DNS `192.168.0.20`, local-lvm 16 GiB.
- One CPU, 1024 MiB RAM, 512 MiB swap; unprivileged Debian 13, no nesting.
- Infrastructure creation was applied by the authenticated operator from the
  approved isolated plan (one create, no changes or destroys).
- Garage's own Terraform root keeps local state permanently.
- `make garage-configure` converged only CT209: final recap `ok=15 changed=7
  unreachable=0 failed=0`. An initial Python quoting error was corrected in
  the role before the successful run; no mount-unit changes were needed.
- Service `garage.service` is enabled and active, running as `garage:garage`.
- S3 listens only on `192.168.0.29:3900`; RPC only on `127.0.0.1:3901`.
  No admin API, website endpoint, reverse proxy, or public route was configured.
- Existing failed `dev-mqueue.mount`, `run-lock.mount`, and `tmp.mount` units
  were left untouched. Garage demonstrated no need for nesting or host changes.

The Ansible role installs the official static amd64 binary from:

`https://garagehq.deuxfleurs.fr/_releases/v2.4.1/x86_64-unknown-linux-musl/garage`

SHA256: `ae49f8de4aaee6b5ca305f7cbdccc8cd8a29b2804aac074649f18bfb83d0a2b6`.
This digest was calculated from the upstream HTTPS download and pinned; it
is not a claim of independently verified release signing.

Configuration: `/etc/garage.toml` (`root:garage`, 0640). Local RPC secret:
`/etc/garage/rpc-secret` (`garage:garage`, 0600), generated once on CT209 and
never returned to the controller. It is not an S3 credential. SQLite metadata
is in `/var/lib/garage/meta`; objects are in `/var/lib/garage/data`. Both are
owned by `garage:garage`, mode 0700. Metadata and data fsync are enabled.

## PBS and recovery

Live PBS job `backup-94190086-c727` had include list
`200,207,202,206,204` at this evaluation. Only `209` was appended. Schedule
`3:00`, storage `pbs`, snapshot mode, `keep-all=1`, and other existing fields
were preserved and verified after the update. VMID205 was already absent in
the live job; this task did not remove or re-add it.

This confirms scheduled inclusion, **not a completed backup or tested restore**.
The root disk contains the configuration, RPC secret, metadata and object data.
A future restore drill must restore these consistently. There is no S3 object
versioning, single-node redundancy, or HA. PBS snapshot coverage does not
establish application-consistent recovery on its own.

## Disposable test

`tests/garage-backend.py` is preserved as engineering evidence, not an offline
CI check. The result is final; do not rerun it or continue stale-lock testing
without new explicit authorization. The convenience Make target was removed
at close-out to avoid presenting further testing as a normal workflow.
It uses the controller's existing boto3 dependency (via infisicalsdk), SSH to
CT209, temporary client directories, and Terraform's built-in `terraform_data`.
It never provisions infrastructure or reads another stack's state.

Each run created one UUID-named `tf-disposable-*` bucket and one temporary key
with a one-hour expiration and read/write permissions only on that bucket.
The key had no owner permission or general bucket-creation permission.
Credentials stayed in memory and child environments, not backend files/logs.
Each run revoked its key and removed its objects and bucket in cleanup.
Post-test Garage key and bucket lists were empty. No production bucket or
Infisical secret was created.

Exact backend options (with a generated disposable bucket name):

```hcl
bucket                      = "tf-disposable-<uuid>"
key                         = "probe/terraform.tfstate"
region                      = "garage"
endpoints                   = { s3 = "http://192.168.0.29:3900" }
use_path_style              = true
use_lockfile                = true
skip_credentials_validation = true
skip_region_validation      = true
skip_requesting_account_id  = true
skip_metadata_api_check     = true
skip_s3_checksum            = true
```

Results:

- Independent client A and B initialization: passed.
- Initial state write, independent state pull and S3 read: passed.
- Normal state update and ordinary lock removal: passed.
- Actual simultaneous clients: **failed**, B exited 0 and changed locked state.
- Successful-holder normal unlock after contention: not reached.
- Stale-lock force-unlock recovery: not reached; stopped at the hard gate.

Client A's test process group was terminated during cleanup. No live service
was stopped or restarted for the concurrency test. All test objects were
removed, including any remaining lock object, before deleting the bucket.

## Close-out and operator boundaries

The deployment/evaluation milestone is complete, with backend qualification
REJECTED. Garage remains deployed as a general internal S3-compatible object
store for future uses, not as an authoritative Terraform backend. Basic S3
write/read/update/delete and single-client Terraform operations succeeded.
No production backend credentials, custom locking mechanism or replacement
backend were configured. No production Terraform state was migrated.

Read-only close-out verification found:

- `hostname` returns `garage`; IP, gateway, resolver and search domain match
  the desired configuration. Proxmox's separate hostname field still contains
  `garage.home.arpa`. The Terraform model now uses `garage`.
- API credentials are absent from the agent runtime. Generate a fresh plan
  with `make garage-plan` in the authenticated operator shell. Apply with
  `make garage-apply` ONLY if the new plan shows an in-place hostname correction
  and no replacement, destroy, network or storage changes. No such plan/apply
  was executed during close-out; do not reuse the previous creation plan.
- Garage 2.4.1 remains active and healthy. Its actual configured S3 listener
  is `192.168.0.29:3900`.
- AdGuard has no internal answer for `s3.doku-lab.net`. An HTTPS probe forced
  to Caddy's LAN IP failed the TLS handshake; HTTPS is not validated yet.

### Intended internal service endpoint

`https://s3.doku-lab.net` is the intended service URL. `home.arpa` remains the
LAN search domain only, not the primary service URL namespace.

Desired path: LAN client -> AdGuard `192.168.0.20` -> internal rewrite to
Caddy `192.168.0.24` -> Garage `192.168.0.29:3900`.

No safe repository-managed AdGuard/Caddy configuration flow exists here.
Read-only service discovery found AdGuard's local service unit at
`/etc/systemd/system/AdGuardHome.service`; Caddy uses
`/usr/lib/systemd/system/caddy.service`, a local `/etc/caddy/Caddyfile`, and
`/etc/systemd/system/caddy.service.d/cloudflare.conf`. The Caddyfile has existing
Cloudflare DNS-01 directives using `{env.CLOUDFLARE_API_TOKEN}`, no imports and
no `s3.doku-lab.net` site. Credential values were not inspected or printed.
Direct Caddy SSH lacked a trusted host key; read-only inspection used the
already trusted Proxmox node and `pct exec 204` instead, without disabling
host-key verification. Neither service was modified.

Exact narrow operator changes in their existing local management flow:

1. In AdGuard Home's DNS rewrites, add `s3.doku-lab.net` -> `192.168.0.24`.
2. Add this site to the existing Caddyfile, reusing its existing service
   environment rather than reading/copying its token:

   ```caddyfile
   s3.doku-lab.net {
       tls {
           dns cloudflare {env.CLOUDFLARE_API_TOKEN}
       }
       reverse_proxy 192.168.0.29:3900
   }
   ```

3. Validate the Caddyfile in its existing credential-bearing service context
   and reload through the established operator procedure. Keep it LAN-only;
   do not add a public A/AAAA/proxied record, tunnel, port forward or public
   ingress. DNS-01 TXT validation is not public service exposure.
4. From a LAN client, verify `dig @192.168.0.20 s3.doku-lab.net +short` returns
   `192.168.0.24`, then `curl -v https://s3.doku-lab.net/` succeeds with normal
   certificate verification. An unauthenticated Garage S3 error response is
   sufficient; do not create credentials just for this check.

No DNS, Caddy, Cloudflare or ingress changes were made by this milestone;
no public exposure was introduced. Endpoint completion and its validation are
operator follow-ups, not claimed successes. Backup/restore verification also
remains pending. No replacement backend evaluation was started.

Separate backlog only: Grafana should later receive its own internal AdGuard
rewrite and Caddy HTTPS endpoint using the `doku-lab.net` service convention.
No Grafana investigation or changes were performed for this close-out.

References: [Garage downloads](https://garagehq.deuxfleurs.fr/download/),
[Garage configuration](https://garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/),
[Garage S3 compatibility](https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/),
[Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3).
