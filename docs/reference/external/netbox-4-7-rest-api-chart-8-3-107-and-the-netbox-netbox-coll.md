---
id: REF-netbox-4-7-rest-api-chart-8-3-107-and-the-netbox-netbox-coll
title: NetBox 4.7 REST API, chart 8.3.107 and the netbox.netbox collection
summary: "What the NetBox deployment and reconciliation rely on: chart values, superuser and v2 tokens, filters used by the sync, nb_inventory behaviour."
type: api-reference
status: current
importance: 3
technology: NetBox
version: "NetBox 4.7.5, chart netbox 8.3.107, netbox.netbox 3.24.0"
source: https://github.com/netbox-community/netbox-chart
source_authority: official
verified: 2026-11-18
created: 2026-11-18
updated: 2026-11-18
tags: [reference, external, netbox]
related_tasks: [TASK-023]
related_milestones: [M013]
related_implementations: [services/netbox/values.yaml, scripts/netbox-sync.py, ansible/inventories/netbox.yml]
---

# NetBox 4.7 REST API, chart 8.3.107 and the netbox.netbox collection

Sources: <https://github.com/netbox-community/netbox-chart> (chart, read from the pulled archive),
<https://github.com/netbox-community/netbox/releases> (4.7 notes), the running instance.

## Purpose

What `services/netbox/`, `scripts/netbox-sync.py` and `ansible/inventories/netbox.yml` rely on, so the next
version bump can be checked against it.

## Endpoint or function

- Chart `oci://ghcr.io/netbox-community/netbox-chart/netbox` 8.3.107: app version v4.7.5, Kubernetes
  >= 1.25. [verified: Chart.yaml]
- REST API under `/api/`: `dcim/{sites,manufacturers,device-types,device-roles,platforms,devices,interfaces}`,
  `virtualization/{cluster-types,clusters,virtual-machines,interfaces}`, `ipam/{prefixes,ip-ranges,ip-addresses}`,
  `extras/{tags,custom-fields}`, `users/{users,permissions,tokens}`, `users/tokens/provision`,
  `core/object-types`, `status`. [observed: project]
- Inventory plugin `netbox.netbox.nb_inventory` from the collection `netbox.netbox` 3.24.0. [observed: project]

## Parameters

Chart values and Secret keys:

- Sub-charts `postgresql` and `valkey` come from Bitnami and are on by default. The Valkey one uses the
  image `bitnami/valkey:latest` and `architecture: replication`. [verified: sub-chart values] Both are
  disabled here.
- With `existingSecret`, the Secret must hold `secret_key` and `email_password`; `api_token_peppers` (JSON
  object, e.g. `{"1": "<50+ characters>"}`) is optional, but without it no API token can exist.
  `superuser.existingSecret` must hold `username`, `email`, `password`, `api_token`. Database and key-value
  passwords are read from `externalDatabase.existingSecretName/Key` and
  `tasksDatabase` / `cachingDatabase.existingSecretName/Key`. [verified: templates]
- `loginRequired` defaults to `false` (anonymous read). [verified: values]
- Web workers: the image starts Granian with `GRANIAN_WORKERS` (default 4). [verified: container script]

API filters used by the reconciliation: `slug`, `name`, `site_id`, `device_id`, `cluster_id`,
`virtual_machine_id`, `address` (with prefix length), `start_address` + `end_address`, `prefix`, `tag`, and
custom fields as `cf_<name>`. [observed: project]

## Request

- v2 token: `Authorization: Bearer nbt_<key>.<token>`. A v1 token would be `Authorization: Token <key>`.
  [observed: project]
- `POST /api/users/tokens/provision/` with `username`, `password` and optionally `expires`,
  `write_enabled`, `description` creates a token for that user; used to get a ten-minute superuser token.
  [observed: project]
- Permissions (`POST /api/users/permissions/`): `object_types` as `app.model` strings, `actions` from
  `view|add|change|delete`, `users`. Object types are listed at `/api/core/object-types/?app_label=…`.
  [observed: project]
- Clusters and prefixes are scoped with `scope_type: dcim.site` + `scope_id`. VM `memory` and `disk` are in
  MB. [observed: project]

## Response

- Creating a token returns `version`, `key` and `token`; the `token` value is shown only in that response.
  [observed: project]
- Lists are paginated (`results`, `next`); related objects come back nested (`{"id": …, "name": …}`),
  choices as `{"value": …, "label": …}`, tags as objects. [observed: project]
- A user sees only its own entries under `/api/users/tokens/`. [observed: project]

## Usage example

```
scripts/secrets.py run /netbox -- make netbox-plan        # reads with the write account, writes nothing
scripts/secrets.py run /netbox -- make netbox-inventory   # nb_inventory with the read-only account
```

`nb_inventory`: the token is read from `NETBOX_TOKEN` (a v2 token works as is). `compose` expressions see
the record as the API returns it (`platform.slug`, `device.name`, `custom_fields.proxmox_vmid`); `groups`
conditions see the extracted variables (`role == 'dns'` with `plurals: false`). [observed: project]

## Known limitations

- **The superuser gets no API token from the chart.** The image creates one only when both a token and a
  key are given; the chart passes only the token. [observed: container script and log]
- An address must be assigned to an interface of a machine before it can be that machine's `primary_ip4`.
  [observed: project]
- PostgreSQL 15 or later with the `ltree` extension (created by the migrations; it is a trusted extension,
  so the database owner can create it); Redis/Valkey 6 or later. [verified: release notes; observed on 17.12]
- Changed in 4.7, not used here but easy to trip over: services use `port_mappings`; the `housekeeping`
  command is gone (the chart's housekeeping CronJob stays disabled). [verified: release notes]
- `ansible` 14.4.0 bundles `netbox.netbox` 3.23.0; 3.24.0 is installed from `collections/requirements.yml`.
  The plugin needs the Python package `pytz` and emits `serial` and `tags`, names Ansible reserves
  (`rename_variables` removes the warnings). [observed: project]
- Not used and not tested: the OpenTofu/Terraform provider `e-breuninger/netbox` 6.0.1 (2026-11-13), and
  the Proxmox plugins `netbox-proxbox` (0.0.24: NetBox 4.7 support labelled experimental, needs a separate
  backend service) and `proxmox2netbox` (4.7 not confirmed). [verified: registry and project pages]

## Verification

- `make netbox-check` renders the chart and runs the reconciliation against an in-memory NetBox.
- Observed on 2026-11-18: first start ran all migrations in about five minutes; four web workers used about
  1.5 GiB, two about 0.6 GiB; apply followed by plan reported nothing to change.
