SHELL := /bin/bash

# ─────────────────────────────────────────────
# Controller
# ─────────────────────────────────────────────

VENV := .venv
# CI supplies an explicit standalone interpreter; local setup keeps its default.
CONTROLLER_PYTHON ?= python3
ANSIBLE := $(VENV)/bin/ansible-playbook
INFISICAL_ENV ?= dev
INFISICAL_DOMAIN ?= https://secrets.doku-lab.net
INFISICAL_PROJECT_ID ?= $(shell python3 -c 'import json; print(json.load(open(".infisical.json"))["workspaceId"])')

define INFISICAL_RUN
	@set -euo pipefail; \
	: "$${INFISICAL_CLIENT_ID:?Set INFISICAL_CLIENT_ID in the runtime environment}"; \
	: "$${INFISICAL_CLIENT_SECRET:?Set INFISICAL_CLIENT_SECRET in the runtime environment}"; \
	token="$$(infisical login --silent --plain --domain "$(INFISICAL_DOMAIN)" \
		--method universal-auth \
		--client-id "$$INFISICAL_CLIENT_ID" \
		--client-secret "$$INFISICAL_CLIENT_SECRET")"; \
	infisical run --silent --domain "$(INFISICAL_DOMAIN)" \
		--token "$$token" \
		--projectId "$(INFISICAL_PROJECT_ID)" \
		--env "$(INFISICAL_ENV)" -- $(1)
endef

# Legacy roots must never reach the NEW cluster (2026-11-16): pve-management .10, pve-core .11,
# pve-infra .12 and the new pve-lab .16 are fresh installs that reuse old names and addresses. The old,
# independent environment is reachable only at 192.168.0.14 (old pve-lab).
RETIRED_ENDPOINT_RE := //192\.168\.0\.(10|11|12|16)[:/]
define LEGACY_ENDPOINT_GUARD
	@if cat "$(1)/terraform.tfvars" "$(1)/terraform.tfvars.json" 2>/dev/null | grep -Eq '"?proxmox_endpoint"?[[:space:]]*[=:].*$(RETIRED_ENDPOINT_RE)'; then \
		echo "$(1): proxmox_endpoint targets a new-cluster address (192.168.0.10/.11/.12/.16), not a retired host address it once was. Legacy roots may only use the old environment at 192.168.0.14." >&2; exit 1; fi
endef
define RETIRED_ROOT
	@echo "$(1) records resources on the retired pve-compute host; its local state is stale and under review (docs/investigations/legacy-inventory.md). Live Terraform operations are refused." >&2; exit 1
endef

.PHONY: \
	setup-controller \
	workstations-check \
	workstations-bootstrap \
	workstations-plan \
	workstations-apply \
	workstations-verify \
	guests-check \
	guests-inventory \
	guests-apply \
	runner-check \
	runner-live-check \
	runner-bootstrap-access \
	runner-plan \
	runner-import \
	runner-live-plan \
	runner-configure \
	runner-migration-plan \
	runner-migration-apply \
	runner-migration-bootstrap \
	runner-migration-configure \
	deploy-monitoring

setup-controller:
	"$(CONTROLLER_PYTHON)" -m venv --clear $(VENV)
	$(VENV)/bin/python -m pip install -r requirements-controller.txt
	$(VENV)/bin/ansible-galaxy collection install -r collections/requirements.yml

TAILSCALE_DIR := terraform/stacks/pve-tailscale-routers
TAILSCALE_AUTH := $(VENV)/bin/python scripts/tailscale-proxmox.py
.PHONY: tailscale-check tailscale-plan tailscale-apply tailscale-configure
tailscale-check:
	$(VENV)/bin/python tests/tailscale-routers.py
	$(ANSIBLE) --syntax-check ansible/playbooks/configure-tailscale-routers.yml

tailscale-plan:
	$(call LEGACY_ENDPOINT_GUARD,$(TAILSCALE_DIR))
	@test -f "$(TAILSCALE_DIR)/terraform.tfvars" || (echo "Supply the two approved allocations in private terraform.tfvars; see docs/archive/codex-2026/docs/tailscale-routers.md"; exit 1)
	rm -f "$(TAILSCALE_DIR)/tailscale.tfplan"
	terraform -chdir=$(TAILSCALE_DIR) fmt -check
	terraform -chdir=$(TAILSCALE_DIR) init -input=false -lockfile=readonly
	terraform -chdir=$(TAILSCALE_DIR) validate
	@$(TAILSCALE_AUTH) plan

tailscale-apply:
	$(call LEGACY_ENDPOINT_GUARD,$(TAILSCALE_DIR))
	@test "$(TAILSCALE_APPLY_APPROVED)" = yes || (echo "Review the saved two-router plan; set TAILSCALE_APPLY_APPROVED=yes only after approval"; exit 1)
	@test -f "$(TAILSCALE_DIR)/tailscale.tfplan" || (echo "Missing reviewed tailscale.tfplan"; exit 1)
	@TAILSCALE_APPLY_APPROVED="$(TAILSCALE_APPLY_APPROVED)" $(TAILSCALE_AUTH) apply

tailscale-configure:
	@test "$(TAILSCALE_CONFIGURE_APPROVED)" = yes || (echo "Approve only the two new guests with TAILSCALE_CONFIGURE_APPROVED=yes"; exit 1)
	@set -euo pipefail; umask 077; work="$$(mktemp -d)"; inventory="$$work/inventory.json"; \
	trap 'rm -f "$$inventory"; rmdir "$$work"' EXIT; \
	terraform -chdir=$(TAILSCALE_DIR) output -json ansible_inventory > "$$inventory"; \
	ANSIBLE_HOST_KEY_CHECKING=True ANSIBLE_KEEP_REMOTE_FILES=False \
	$(ANSIBLE) -i "$$inventory" ansible/playbooks/configure-tailscale-routers.yml \
	-e tailscale_configure_approved=true

# New isolated ownership; never invokes workstation host configuration.
CONTROLLER_DIR := terraform/stacks/pve-lab-controller
.PHONY: controller-check controller-plan controller-apply
controller-check:
	$(VENV)/bin/python tests/vm-profiles.py
	$(ANSIBLE) ansible/playbooks/configure-recovery-controller.yml --syntax-check -i ansible/inventories/homelab.yml

controller-plan:
	$(call LEGACY_ENDPOINT_GUARD,$(CONTROLLER_DIR))
	@test "$(CONTROLLER_ALLOCATION_REVIEWED)" = yes || (echo "Review live VMID/IP, image, storage and network allocation first"; exit 1)
	@test -f "$(CONTROLLER_DIR)/terraform.tfvars" || (echo "Missing private reviewed profile"; exit 1)
	terraform -chdir=$(CONTROLLER_DIR) init -input=false -lockfile=readonly
	$(call INFISICAL_RUN,terraform -chdir=$(CONTROLLER_DIR) plan -input=false -out=controller.tfplan)

controller-apply:
	$(call LEGACY_ENDPOINT_GUARD,$(CONTROLLER_DIR))
	@test "$(CONTROLLER_APPLY_APPROVED)" = yes || (echo "Explicit approval of the exact saved plan required"; exit 1)
	@test -f "$(CONTROLLER_DIR)/controller.tfplan" || (echo "Missing reviewed saved plan"; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(CONTROLLER_DIR) apply -input=false controller.tfplan)

# Stage A has a separate local authority and no default live allocations.
STAGE_A_DIR := terraform/stacks/pve-lab-k3s
export STAGE_A_INPUT_SOURCE
STAGE_A_INPUTS = $(VENV)/bin/python scripts/stage-a-inputs.py $(if $(filter infisical,$(STAGE_A_INPUT_SOURCE)),--domain "$(INFISICAL_DOMAIN)" --environment "$(INFISICAL_ENV)" --project-id "$(INFISICAL_PROJECT_ID)")
.PHONY: stage-a-check stage-a-plan stage-a-apply stage-a-start stage-a-configure
stage-a-check:
	$(VENV)/bin/python tests/vm-profiles.py
	$(VENV)/bin/python tests/stage-a.py
	$(VENV)/bin/python tests/stage-a-inputs.py
	$(ANSIBLE) ansible/playbooks/configure-k3s-lab.yml --syntax-check -i ansible/inventories/homelab.yml
	$(ANSIBLE) ansible/playbooks/start-k3s-lab.yml --syntax-check -i ansible/inventories/homelab.yml

stage-a-plan:
	$(call LEGACY_ENDPOINT_GUARD,$(STAGE_A_DIR))
	@test "$(STAGE_A_ALLOCATION_REVIEWED)" = yes || (echo "Review allocation, stopped workstations, local storage and host capacity first"; exit 1)
	rm -f "$(STAGE_A_DIR)/stage-a.tfplan"
	@test -f "$(STAGE_A_DIR)/terraform.tfvars" || (echo "Missing private reviewed Stage A inputs"; exit 1)
	@$(STAGE_A_INPUTS) check
	terraform -chdir=$(STAGE_A_DIR) init -input=false -lockfile=readonly
	@$(STAGE_A_INPUTS) plan || { rm -f "$(STAGE_A_DIR)/stage-a.tfplan"; exit 1; }
	shasum -a 256 "$(STAGE_A_DIR)/stage-a.tfplan"

stage-a-apply:
	$(call LEGACY_ENDPOINT_GUARD,$(STAGE_A_DIR))
	@test "$(STAGE_A_APPLY_APPROVED)" = yes || (echo "Explicit exact-plan approval required"; exit 1)
	@test -n "$(STAGE_A_PLAN_SHA256)" || (echo "Supply the reviewed plan SHA256"; exit 1)
	@printf '%s  %s\n' '$(STAGE_A_PLAN_SHA256)' '$(STAGE_A_DIR)/stage-a.tfplan' | shasum -a 256 -c
	@$(STAGE_A_INPUTS) apply
	rm -f "$(STAGE_A_DIR)/stage-a.tfplan"

stage-a-start:
	@test "$(STAGE_A_START_APPROVED)" = yes || (echo "Separate start and SSH trust approval required"; exit 1)
	@set -eu; umask 077; work="$$(mktemp -d)"; inventory="$$work/inventory.json"; trap 'rm -f "$$inventory"; rmdir "$$work"' EXIT; \
	  test -f "$(STAGE_A_DIR)/terraform.tfstate"; \
	  terraform -chdir=$(STAGE_A_DIR) output -json ansible_inventory > "$$inventory"; \
	  $(ANSIBLE) ansible/playbooks/start-k3s-lab.yml -i ansible/inventories/homelab.yml -i "$$inventory" -e stage_a_start_approved=true

stage-a-configure:
	@test "$(STAGE_A_CONFIGURE_APPROVED)" = yes || (echo "Separate guest OS convergence and SSH trust approval required"; exit 1)
	@set -eu; umask 077; work="$$(mktemp -d)"; inventory="$$work/inventory.json"; trap 'rm -f "$$inventory"; rmdir "$$work"' EXIT; \
	  test -f "$(STAGE_A_DIR)/terraform.tfstate"; \
	  terraform -chdir=$(STAGE_A_DIR) output -json ansible_inventory > "$$inventory"; \
	  $(ANSIBLE) ansible/playbooks/configure-k3s-lab.yml -i "$$inventory" -e stage_a_configure_approved=true --diff

# K3s uses applied Stage A inventory; no production credentials or Terraform writes.
export K3S_PRIVATE_DIR
.PHONY: k3s-check k3s-token-init k3s-install k3s-snapshot
k3s-check:
	$(VENV)/bin/python tests/k3s-bootstrap.py
	$(ANSIBLE) ansible/playbooks/bootstrap-k3s.yml --syntax-check -i ansible/inventories/homelab.yml
	$(ANSIBLE) ansible/playbooks/snapshot-k3s.yml --syntax-check -i ansible/inventories/homelab.yml

k3s-token-init:
	@test "$(K3S_TOKEN_APPROVED)" = yes || (echo "Separate lab-token generation approval required"; exit 1)
	@K3S_TOKEN_APPROVED=yes $(VENV)/bin/python scripts/k3s-lab.py token-init

k3s-install:
	@test "$(K3S_INSTALL_APPROVED)" = yes || (echo "Review K3s version, network/firewall and token procedure first"; exit 1)
	@K3S_TOKEN_APPROVED=yes $(VENV)/bin/python scripts/k3s-lab.py token-check
	@set -euo pipefail; umask 077; work="$$(mktemp -d)"; trap 'rm -f "$$work/inventory.json"; rmdir "$$work"' EXIT; \
	  test -f "$(STAGE_A_DIR)/terraform.tfstate"; \
	  terraform -chdir=$(STAGE_A_DIR) output -json ansible_inventory | $(VENV)/bin/python scripts/k3s-lab.py inventory > "$$work/inventory.json"; \
	  ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) ansible/playbooks/bootstrap-k3s.yml -i "$$work/inventory.json" -e k3s_install_approved=true

k3s-snapshot:
	@test "$(K3S_SNAPSHOT_APPROVED)" = yes || (echo "Separate snapshot and private recovery export approval required"; exit 1)
	@K3S_TOKEN_APPROVED=yes $(VENV)/bin/python scripts/k3s-lab.py token-check
	@set -euo pipefail; umask 077; work="$$(mktemp -d)"; trap 'rm -f "$$work/inventory.json"; rmdir "$$work"' EXIT; \
	  test -f "$(STAGE_A_DIR)/terraform.tfstate"; \
	  terraform -chdir=$(STAGE_A_DIR) output -json ansible_inventory | $(VENV)/bin/python scripts/k3s-lab.py inventory > "$$work/inventory.json"; \
	  ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) ansible/playbooks/snapshot-k3s.yml -i "$$work/inventory.json" -e k3s_snapshot_approved=true

.PHONY: flux-check flux-install
flux-check:
	$(VENV)/bin/python tests/flux-demo.py
	$(ANSIBLE) ansible/playbooks/bootstrap-flux.yml --syntax-check -i ansible/inventories/homelab.yml

flux-install:
	@test "$(FLUX_INSTALL_APPROVED)" = yes || (echo "Separate Stage A Flux/demo installation approval required"; exit 1)
	@set -euo pipefail; umask 077; work="$$(mktemp -d)"; trap 'rm -f "$$work/inventory.json"; rmdir "$$work"' EXIT; \
	  test -f "$(STAGE_A_DIR)/terraform.tfstate"; \
	  terraform -chdir=$(STAGE_A_DIR) output -json ansible_inventory | $(VENV)/bin/python scripts/k3s-lab.py inventory > "$$work/inventory.json"; \
	  ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) ansible/playbooks/bootstrap-flux.yml -i "$$work/inventory.json" -e flux_install_approved=true

.PHONY: homepage-check homepage-install
homepage-check:
	$(VENV)/bin/python tests/homepage.py
	$(ANSIBLE) ansible/playbooks/bootstrap-homepage.yml --syntax-check -i ansible/inventories/homelab.yml

homepage-install:
	@test "$(HOMEPAGE_INSTALL_APPROVED)" = yes || (echo "Explicit fresh Homepage installation approval required"; exit 1)
	@set -euo pipefail; umask 077; work="$$(mktemp -d)"; trap 'rm -f "$$work/inventory.json"; rmdir "$$work"' EXIT; \
	  test -f "$(STAGE_A_DIR)/terraform.tfstate"; \
	  terraform -chdir=$(STAGE_A_DIR) output -json ansible_inventory | $(VENV)/bin/python scripts/k3s-lab.py inventory > "$$work/inventory.json"; \
	  ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) ansible/playbooks/bootstrap-homepage.yml -i "$$work/inventory.json" -e homepage_install_approved=true

# PostgreSQL host bootstrap state stays local; apply only the reviewed saved plan.
TFSTATE_DIR := terraform/stacks/pve-core-tfstate
TFSTATE_SSH_PUBLIC_KEY_FILE ?= $(HOME)/.ssh/id_ed25519.pub

.PHONY: tfstate-plan tfstate-apply
tfstate-plan:
	$(call LEGACY_ENDPOINT_GUARD,$(TFSTATE_DIR))
	@test -r "$(TFSTATE_SSH_PUBLIC_KEY_FILE)" || (echo "Missing controller public SSH key"; exit 1)
	rm -f "$(TFSTATE_DIR)/tfstate.tfplan"
	terraform -chdir=$(TFSTATE_DIR) fmt -check
	terraform -chdir=$(TFSTATE_DIR) init -input=false
	terraform -chdir=$(TFSTATE_DIR) validate
	$(call INFISICAL_RUN,env TF_VAR_management_ssh_public_key="$$(cat "$(TFSTATE_SSH_PUBLIC_KEY_FILE)")" terraform -chdir=$(TFSTATE_DIR) plan -input=false -out=tfstate.tfplan)

tfstate-apply:
	$(call LEGACY_ENDPOINT_GUARD,$(TFSTATE_DIR))
	@test -f "$(TFSTATE_DIR)/tfstate.tfplan" || (echo "Missing reviewed tfstate plan; run make tfstate-plan first"; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(TFSTATE_DIR) apply -input=false tfstate.tfplan)

TFSTATE_KNOWN_HOSTS ?= $(HOME)/.ssh/known_hosts

.PHONY: tfstate-check tfstate-configure tfstate-qualify
tfstate-check:
	$(ANSIBLE) ansible/playbooks/configure-tfstate.yml -i ansible/inventories/tfstate.yml --syntax-check

tfstate-configure:
	$(ANSIBLE) ansible/playbooks/configure-tfstate.yml -i ansible/inventories/tfstate.yml --limit tfstate

tfstate-qualify:
	$(VENV)/bin/python scripts/qualify-pg-backend.py --known-hosts "$(TFSTATE_KNOWN_HOSTS)"

.PHONY: tfstate-backup-qualify
tfstate-backup-qualify:
	$(VENV)/bin/python scripts/qualify-pg-backend.py --known-hosts "$(TFSTATE_KNOWN_HOSTS)" --scheduled-backup

# Garage has an isolated local bootstrap state, never a backend hosted by itself.
GARAGE_DIR := terraform/stacks/pve-core-garage
GARAGE_SSH_PUBLIC_KEY_FILE ?= $(HOME)/.ssh/id_ed25519.pub

.PHONY: garage-plan garage-apply garage-check garage-configure
garage-plan:
	$(call LEGACY_ENDPOINT_GUARD,$(GARAGE_DIR))
	@test -r "$(GARAGE_SSH_PUBLIC_KEY_FILE)" || (echo "Missing controller public SSH key"; exit 1)
	terraform -chdir=$(GARAGE_DIR) fmt -check
	terraform -chdir=$(GARAGE_DIR) init -input=false
	terraform -chdir=$(GARAGE_DIR) validate
	$(call INFISICAL_RUN,env TF_VAR_management_ssh_public_key="$$(cat "$(GARAGE_SSH_PUBLIC_KEY_FILE)")" terraform -chdir=$(GARAGE_DIR) plan -input=false -out=garage.tfplan)

garage-apply:
	$(call LEGACY_ENDPOINT_GUARD,$(GARAGE_DIR))
	@test -f "$(GARAGE_DIR)/garage.tfplan" || (echo "Missing saved Garage plan; run make garage-plan and review it first"; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(GARAGE_DIR) apply -input=false garage.tfplan)

garage-check:
	$(ANSIBLE) ansible/playbooks/configure-garage.yml -i ansible/inventories/garage.yml --syntax-check

garage-configure:
	$(ANSIBLE) ansible/playbooks/configure-garage.yml -i ansible/inventories/garage.yml --limit garage


# ─────────────────────────────────────────────
# Workstations
# ─────────────────────────────────────────────

WS_DIR := terraform/stacks/pve-lab-workstations
WS_PLAN := /tmp/pve-lab-workstations.tfplan
WS_PLAYBOOK := ansible/playbooks/configure-workstation-host.yml
GUEST_PLAYBOOK := ansible/playbooks/configure-guests.yml
GUEST_STATIC_INVENTORY := ansible/inventories/homelab.yml
GUEST_DYNAMIC_INVENTORY := ansible/inventories/guests.proxmox.yml
GUEST_INVENTORIES := -i $(GUEST_STATIC_INVENTORY) -i $(GUEST_DYNAMIC_INVENTORY)

workstations-check:
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(WS_PLAYBOOK) --check --diff


# ─────────────────────────────────────────────
# Guests
# ─────────────────────────────────────────────

guests-check:
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(GUEST_PLAYBOOK) --syntax-check -i $(GUEST_STATIC_INVENTORY)

guests-inventory:
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(VENV)/bin/ansible-inventory $(GUEST_INVENTORIES) --graph

guests-apply:
	@test -n "$(LIMIT)" || (echo "Set LIMIT, for example: make guests-apply LIMIT=dev"; exit 1)
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(GUEST_PLAYBOOK) $(GUEST_INVENTORIES) --limit "$(LIMIT)" --diff


# ─────────────────────────────────────────────
# Forgejo Runner
# ─────────────────────────────────────────────

RUNNER_DIR := terraform/stacks/pve-compute-forgejo-runner
MIGRATION_RUNNER_DIR := terraform/stacks/pve-compute-forgejo-runner-migration
RUNNER_PLAYBOOK := ansible/playbooks/configure-forgejo-runner.yml
RUNNER_INVENTORY := ansible/inventories/runner-migration.yml
MIGRATION_RUNNER_INVENTORY := ansible/inventories/runner-migration.yml
RUNNER_SSH_PRIVATE_KEY_FILE ?= $(HOME)/.ssh/id_ed25519
RUNNER_SSH_PUBLIC_KEY_FILE ?= $(RUNNER_SSH_PRIVATE_KEY_FILE).pub

runner-check:
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(RUNNER_PLAYBOOK) --syntax-check -i $(RUNNER_INVENTORY)

runner-live-check:
	@test -n "$${INFISICAL_CLIENT_ID:-}" || (echo "Set INFISICAL_CLIENT_ID in the runtime environment"; exit 1)
	@test -n "$${INFISICAL_CLIENT_SECRET:-}" || (echo "Set INFISICAL_CLIENT_SECRET in the runtime environment"; exit 1)
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(RUNNER_PLAYBOOK) --check --diff --limit forgejo-runner-migration -i $(RUNNER_INVENTORY)

runner-bootstrap-access:
	@test -r "$(RUNNER_SSH_PUBLIC_KEY_FILE)" || (echo "Missing public key: $(RUNNER_SSH_PUBLIC_KEY_FILE)"; exit 1)
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) ansible/playbooks/bootstrap-forgejo-runner-access.yml \
		-i ansible/inventories/runner-bootstrap.yml \
		--limit forgejo-runner-bootstrap \
		-e runner_management_public_key_file="$(RUNNER_SSH_PUBLIC_KEY_FILE)"

runner-plan:
	terraform -chdir=$(RUNNER_DIR) fmt -check
	terraform -chdir=$(RUNNER_DIR) init -backend=false -input=false
	terraform -chdir=$(RUNNER_DIR) validate

runner-import:
	$(call RETIRED_ROOT,$(RUNNER_DIR))
	@test -f "$(RUNNER_DIR)/terraform.tfvars" || (echo "Create private $(RUNNER_DIR)/terraform.tfvars first"; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(RUNNER_DIR) import -input=false -var-file=terraform.tfvars proxmox_virtual_environment_container.forgejo_runner pve-compute/300)

runner-live-plan:
	$(call RETIRED_ROOT,$(RUNNER_DIR))
	@test -f "$(RUNNER_DIR)/terraform.tfvars" || (echo "Create private $(RUNNER_DIR)/terraform.tfvars first"; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(RUNNER_DIR) plan -input=false -var-file=terraform.tfvars)

runner-migration-plan:
	$(call RETIRED_ROOT,$(MIGRATION_RUNNER_DIR))
	@test -f "$(MIGRATION_RUNNER_DIR)/terraform.tfvars" || (echo "Create private $(MIGRATION_RUNNER_DIR)/terraform.tfvars first"; exit 1)
	terraform -chdir=$(MIGRATION_RUNNER_DIR) fmt -check
	$(call INFISICAL_RUN,terraform -chdir=$(MIGRATION_RUNNER_DIR) init -input=false)
	$(call INFISICAL_RUN,terraform -chdir=$(MIGRATION_RUNNER_DIR) validate)
	$(call INFISICAL_RUN,terraform -chdir=$(MIGRATION_RUNNER_DIR) plan -input=false -var-file=terraform.tfvars)

runner-migration-apply:
	$(call RETIRED_ROOT,$(MIGRATION_RUNNER_DIR))
	@test -f "$(MIGRATION_RUNNER_DIR)/terraform.tfvars" || (echo "Create private $(MIGRATION_RUNNER_DIR)/terraform.tfvars first"; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(MIGRATION_RUNNER_DIR) apply -input=false -auto-approve -var-file=terraform.tfvars)

runner-configure:
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(RUNNER_PLAYBOOK) -i $(RUNNER_INVENTORY) --limit forgejo-runner-migration --diff

runner-migration-bootstrap:
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) ansible/playbooks/bootstrap-forgejo-runner-migration.yml -i $(MIGRATION_RUNNER_INVENTORY) --limit forgejo-runner-migration --diff

runner-migration-configure:
	@test -n "$${INFISICAL_CLIENT_ID:-}" || (echo "Set INFISICAL_CLIENT_ID in the runtime environment"; exit 1)
	@test -n "$${INFISICAL_CLIENT_SECRET:-}" || (echo "Set INFISICAL_CLIENT_SECRET in the runtime environment"; exit 1)
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) ansible/playbooks/configure-forgejo-runner-migration.yml -i $(MIGRATION_RUNNER_INVENTORY) --limit forgejo-runner-migration --diff

workstations-bootstrap:
	@test "$(WORKSTATIONS_HEADLESS_APPROVED)" = yes || (echo "Review headless maintenance and stop affected VMs; set WORKSTATIONS_HEADLESS_APPROVED=yes"; exit 1)
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(WS_PLAYBOOK) --diff -e workstation_headless_approved=true

workstations-plan:
	$(call LEGACY_ENDPOINT_GUARD,$(WS_DIR))
	rm -f $(WS_PLAN)
	$(call INFISICAL_RUN,terraform -chdir=$(WS_DIR) fmt)
	$(call INFISICAL_RUN,terraform -chdir=$(WS_DIR) validate)
	$(call INFISICAL_RUN,terraform -chdir=$(WS_DIR) plan -out=$(WS_PLAN))

workstations-apply:
	$(call LEGACY_ENDPOINT_GUARD,$(WS_DIR))
	@test "$(WORKSTATIONS_HEADLESS_APPROVED)" = yes || (echo "Review workstation maintenance; set WORKSTATIONS_HEADLESS_APPROVED=yes"; exit 1)
	@test -f $(WS_PLAN) || \
		(echo "No saved workstation plan. Run 'make workstations-plan' first."; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(WS_DIR) apply -parallelism=1 $(WS_PLAN))
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(WS_PLAYBOOK) --diff -e workstation_headless_approved=true
	rm -f $(WS_PLAN)

workstations-verify:
	$(call LEGACY_ENDPOINT_GUARD,$(WS_DIR))
	$(call INFISICAL_RUN,terraform -chdir=$(WS_DIR) plan)
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(WS_PLAYBOOK) --check --diff


# ─────────────────────────────────────────────
# Monitoring
# ─────────────────────────────────────────────

deploy-monitoring:
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	@read -r -p "Infisical Client ID: " cid; \
	read -r -s -p "Infisical Client Secret: " secret; echo; \
	INFISICAL_UNIVERSAL_AUTH_CLIENT_ID="$$cid" \
	INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET="$$secret" \
	$(ANSIBLE) ansible/playbooks/deploy-monitoring.yml

.PHONY: recovery-check
recovery-check:
	$(VENV)/bin/python tests/recovery-kit.py

include services/windmill/targets.mk

# ─────────────────────────────────────────────
# pve-management: management VM mgmt-control-01 (M001, OpenTofu)
# Run from the operator workstation only. CT301 never receives these credentials.
# ─────────────────────────────────────────────

TOFU ?= tofu
MGMT_DIR := terraform/stacks/pve-management-control
MGMT_PLAN := mgmt.tfplan
MGMT_ENDPOINT ?= https://192.168.0.10:8006/
# Reusable provider cache for offline checks (git-ignored); never the root's live .terraform.
MGMT_CHECK_DATA := $(CURDIR)/.local/tofu-check/pve-management-control
MGMT_GUARD := $(VENV)/bin/python scripts/pve-auth-guard.py --
# Explicit credential source, no default and no fallback:
#   infisical: Universal Auth in the operator shell; secrets read from MGMT_INFISICAL_PATH only
#   env:       PROXMOX_VE_API_TOKEN already exported (e.g. decrypted from SOPS during recovery)
MGMT_INPUT_SOURCE ?=
MGMT_INFISICAL_PATH ?= /pve-management
define MGMT_REQUIRE_SOURCE
	@case "$(MGMT_INPUT_SOURCE)" in infisical|env) ;; *) echo "Set MGMT_INPUT_SOURCE=infisical or MGMT_INPUT_SOURCE=env (no default, no fallback)." >&2; exit 1;; esac
endef
ifeq ($(MGMT_INPUT_SOURCE),infisical)
define MGMT_RUN
	@set -euo pipefail; \
	: "$${INFISICAL_CLIENT_ID:?Set INFISICAL_CLIENT_ID in the runtime environment}"; \
	: "$${INFISICAL_CLIENT_SECRET:?Set INFISICAL_CLIENT_SECRET in the runtime environment}"; \
	token="$$(infisical login --silent --plain --domain "$(INFISICAL_DOMAIN)" \
		--method universal-auth \
		--client-id "$$INFISICAL_CLIENT_ID" \
		--client-secret "$$INFISICAL_CLIENT_SECRET")"; \
	infisical run --silent --domain "$(INFISICAL_DOMAIN)" \
		--token "$$token" \
		--projectId "$(INFISICAL_PROJECT_ID)" \
		--env "$(INFISICAL_ENV)" --path "$(MGMT_INFISICAL_PATH)" -- $(MGMT_GUARD) $(1)
endef
else
define MGMT_RUN
	@$(MGMT_GUARD) $(1)
endef
endif

.PHONY: mgmt-check mgmt-discover mgmt-plan mgmt-apply mgmt-configure mgmt-autoinstall-serve mgmt-state-backup

# Offline only: no credentials, no backend, mocked provider.
mgmt-check:
	$(TOFU) -chdir=$(MGMT_DIR) fmt -check -recursive
	@mkdir -p "$(MGMT_CHECK_DATA)"
	TF_DATA_DIR="$(MGMT_CHECK_DATA)" $(TOFU) -chdir=$(MGMT_DIR) init -backend=false -input=false -lockfile=readonly -no-color >/dev/null
	TF_DATA_DIR="$(MGMT_CHECK_DATA)" $(TOFU) -chdir=$(MGMT_DIR) validate -no-color
	TF_DATA_DIR="$(MGMT_CHECK_DATA)" $(TOFU) -chdir=$(MGMT_DIR) test -no-color
	$(ANSIBLE) ansible/playbooks/configure-mgmt-control.yml --syntax-check -i ansible/inventories/homelab.yml
	$(VENV)/bin/python tests/mgmt-control.py

# Read-only: GET requests with verified TLS. Pass datastores/bridge to check privileges, e.g.
# MGMT_DISCOVER_ARGS="--image-datastore local --disk-datastore local-lvm --bridge vmbr0"
mgmt-discover:
	$(MGMT_REQUIRE_SOURCE)
	$(call MGMT_RUN,$(VENV)/bin/python scripts/pve-discover.py --endpoint "$(MGMT_ENDPOINT)" --node pve-management $(MGMT_DISCOVER_ARGS))

mgmt-plan:
	@test "$(MGMT_ALLOCATION_REVIEWED)" = yes || (echo "Confirm every PROPOSED value with make mgmt-discover, then set MGMT_ALLOCATION_REVIEWED=yes" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@test -f "$(MGMT_DIR)/terraform.tfvars" || (echo "Create the private $(MGMT_DIR)/terraform.tfvars from terraform.tfvars.example" >&2; exit 1)
	@test -f "$(MGMT_DIR)/terraform.tfstate" || test "$(MGMT_NEW_STATE)" = yes || (echo "No $(MGMT_DIR)/terraform.tfstate here: VM 100 already exists. Copy the state from the workstation that holds it (docs/handoff.md); MGMT_NEW_STATE=yes only for a deliberately empty state." >&2; exit 1)
	@test ! -e "$(MGMT_DIR)/$(MGMT_PLAN)" || mv -f "$(MGMT_DIR)/$(MGMT_PLAN)" "$(MGMT_DIR)/mgmt.previous.tfplan"
	$(TOFU) -chdir=$(MGMT_DIR) init -input=false -lockfile=readonly
	$(call MGMT_RUN,$(TOFU) -chdir=$(MGMT_DIR) plan -input=false -out=$(MGMT_PLAN))
	@shasum -a 256 "$(MGMT_DIR)/$(MGMT_PLAN)"

# Mutates pve-management: only with explicit approval of the exact saved plan.
mgmt-apply:
	@test "$(MGMT_APPLY_APPROVED)" = yes || (echo "Explicit approval of the exact saved plan required: MGMT_APPLY_APPROVED=yes" >&2; exit 1)
	@test -n "$(MGMT_PLAN_SHA256)" || (echo "Supply MGMT_PLAN_SHA256 as printed by make mgmt-plan" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@printf '%s  %s\n' '$(MGMT_PLAN_SHA256)' '$(MGMT_DIR)/$(MGMT_PLAN)' | shasum -a 256 -c
	$(call MGMT_RUN,$(TOFU) -chdir=$(MGMT_DIR) apply -input=false $(MGMT_PLAN))
	@mv -f "$(MGMT_DIR)/$(MGMT_PLAN)" "$(MGMT_DIR)/mgmt.applied.tfplan"
	@echo "State updated locally: $(MGMT_DIR)/terraform.tfstate (this workstation only, never in Git)"

# Serves the Ubuntu Desktop autoinstall (NoCloud seed) while VM 100 installs; stop it with Ctrl-C once the
# installer has started. Run it after the apply that writes the autoinstall_user_data output, before the
# apply that creates the VM. The account password is read from $(MGMT_SECRETS_DIR)/ubuntu-password and
# served only as a sha512-crypt hash, on the LAN, while the installer runs: stop the server afterwards.
MGMT_SECRETS_DIR := $(CURDIR)/.local/mgmt-control
MGMT_SEED_DIR := $(CURDIR)/.local/autoinstall
MGMT_SEED_BIND ?= 0.0.0.0
MGMT_SEED_PORT ?= 8399
# poweroff for an in-place reinstall (ISO booted first): the VM stops at the end so the boot order can be
# put back to the disk before it starts again; reboot for a new, empty VM.
MGMT_SEED_SHUTDOWN ?= reboot
mgmt-autoinstall-serve:
	@set -euo pipefail; umask 077; mkdir -p "$(MGMT_SEED_DIR)"; pw="$(MGMT_SECRETS_DIR)/ubuntu-password"; \
	test -s "$$pw" || { echo "Write the ubuntu account password to $$pw first (one line, mode 0600)" >&2; exit 1; }; \
	hash="$$(head -n 1 "$$pw" | tr -d '\n' | openssl passwd -6 -stdin)"; \
	case "$$hash" in '$$6$$'*) ;; *) echo "openssl passwd -6 failed" >&2; exit 1;; esac; \
	case "$(MGMT_SEED_SHUTDOWN)" in reboot|poweroff) ;; *) echo "MGMT_SEED_SHUTDOWN must be reboot or poweroff" >&2; exit 1;; esac; \
	$(TOFU) -chdir=$(MGMT_DIR) output -raw autoinstall_user_data \
	| sed -e "s|@MGMT_PASSWORD_HASH@|$$hash|" -e "s|^  shutdown: reboot$$|  shutdown: $(MGMT_SEED_SHUTDOWN)|" > "$(MGMT_SEED_DIR)/user-data"; \
	grep -qF "password: \"$$hash\"" "$(MGMT_SEED_DIR)/user-data" || { echo "The autoinstall_user_data output has no password placeholder: run make mgmt-plan/mgmt-apply to refresh it" >&2; exit 1; }; \
	cp "$(MGMT_SEED_DIR)/user-data" "$(MGMT_SEED_DIR)/autoinstall.yaml"; \
	printf 'instance-id: mgmt-control-01-autoinstall\n' > "$(MGMT_SEED_DIR)/meta-data"; : > "$(MGMT_SEED_DIR)/vendor-data"; \
	chmod 0644 "$(MGMT_SEED_DIR)"/*; chmod 0755 "$(MGMT_SEED_DIR)"; \
	echo "Serving $(MGMT_SEED_DIR) on $(MGMT_SEED_BIND):$(MGMT_SEED_PORT) (fallback URL for the installer: http://<this host>:$(MGMT_SEED_PORT)/autoinstall.yaml)"; \
	python3 -m http.server "$(MGMT_SEED_PORT)" --bind "$(MGMT_SEED_BIND)" --directory "$(MGMT_SEED_DIR)"

mgmt-configure:
	@test "$(MGMT_CONFIGURE_APPROVED)" = yes || (echo "Approve configuration of mgmt-control-01 with MGMT_CONFIGURE_APPROVED=yes" >&2; exit 1)
	@test -n "$(MGMT_SOURCE_COMMIT)" || (echo "Supply MGMT_SOURCE_COMMIT: a reviewed full commit published on the GitHub mirror" >&2; exit 1)
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	@set -euo pipefail; umask 077; inventory="$(CURDIR)/.local/mgmt-control-inventory.json"; mkdir -p "$(CURDIR)/.local"; \
	$(TOFU) -chdir=$(MGMT_DIR) output -json ansible_inventory > "$$inventory"; \
	ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) -i "$$inventory" ansible/playbooks/configure-mgmt-control.yml \
	--diff -e mgmt_source_commit="$(MGMT_SOURCE_COMMIT)" -e mgmt_secrets_dir="$(MGMT_SECRETS_DIR)"

# Encrypted, dated off-machine copy of the local state (age public recipients only).
mgmt-state-backup:
	@command -v age >/dev/null || (echo "Install age first" >&2; exit 1)
	@test -n "$(MGMT_BACKUP_DIR)" && test -d "$(MGMT_BACKUP_DIR)" || (echo "Set MGMT_BACKUP_DIR to a mounted off-machine location" >&2; exit 1)
	@test -f "$(AGE_RECIPIENTS_FILE)" || (echo "Set AGE_RECIPIENTS_FILE to the public age recipients file" >&2; exit 1)
	@test -f "$(MGMT_DIR)/terraform.tfstate" || (echo "No $(MGMT_DIR)/terraform.tfstate to back up" >&2; exit 1)
	@set -euo pipefail; out="$(MGMT_BACKUP_DIR)/pve-management-control-$$(date -u +%Y%m%dT%H%M%SZ).tfstate.age"; \
	age -R "$(AGE_RECIPIENTS_FILE)" -o "$$out" "$(MGMT_DIR)/terraform.tfstate"; \
	shasum -a 256 "$$out"
