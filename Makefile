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

# ─────────────────────────────────────────────
# Bootstrap deployment runner deploy-runner-01 (M003, ADR-014, OpenTofu)
# The VM root is applied from the operator workstation only, with the same token and gates as mgmt-*.
# terraform/stacks/ci-disposable is applied only BY the runner (homelab-deploy wrapper), never from here.
# ─────────────────────────────────────────────

DEPLOY_RUNNER_DIR := terraform/stacks/deploy-runner
DEPLOY_RUNNER_PLAN := deploy-runner.tfplan
DEPLOY_RUNNER_ROOTS := $(DEPLOY_RUNNER_DIR) terraform/stacks/ci-disposable
DEPLOY_RUNNER_CHECK_DATA := $(CURDIR)/.local/tofu-check

.PHONY: deploy-runner-check deploy-runner-plan deploy-runner-apply deploy-runner-configure

# Offline only: no credentials, no backend, mocked provider.
deploy-runner-check:
	@set -euo pipefail; for r in $(DEPLOY_RUNNER_ROOTS); do \
		d="$(DEPLOY_RUNNER_CHECK_DATA)/$$(basename "$$r")"; mkdir -p "$$d"; \
		$(TOFU) -chdir=$$r fmt -check -recursive; \
		TF_DATA_DIR="$$d" $(TOFU) -chdir=$$r init -backend=false -input=false -lockfile=readonly -no-color >/dev/null; \
		TF_DATA_DIR="$$d" $(TOFU) -chdir=$$r validate -no-color >/dev/null; \
		TF_DATA_DIR="$$d" $(TOFU) -chdir=$$r test -no-color | tail -n 1; \
	done
	$(ANSIBLE) ansible/playbooks/configure-deploy-runner.yml --syntax-check -i ansible/inventories/homelab.yml
	$(VENV)/bin/python tests/deploy-runner.py

deploy-runner-plan:
	@test "$(DEPLOY_RUNNER_ALLOCATION_REVIEWED)" = yes || (echo "Confirm the allocation in $(DEPLOY_RUNNER_DIR)/terraform.tfvars, then set DEPLOY_RUNNER_ALLOCATION_REVIEWED=yes" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@test -f "$(DEPLOY_RUNNER_DIR)/terraform.tfvars" || (echo "Create the private $(DEPLOY_RUNNER_DIR)/terraform.tfvars from terraform.tfvars.example" >&2; exit 1)
	@test -f "$(DEPLOY_RUNNER_DIR)/terraform.tfstate" || test "$(DEPLOY_RUNNER_NEW_STATE)" = yes || (echo "No $(DEPLOY_RUNNER_DIR)/terraform.tfstate here. Only the first creation of deploy-runner-01 starts from an empty state (DEPLOY_RUNNER_NEW_STATE=yes); otherwise copy the state from the workstation that holds it." >&2; exit 1)
	@test ! -e "$(DEPLOY_RUNNER_DIR)/$(DEPLOY_RUNNER_PLAN)" || mv -f "$(DEPLOY_RUNNER_DIR)/$(DEPLOY_RUNNER_PLAN)" "$(DEPLOY_RUNNER_DIR)/deploy-runner.previous.tfplan"
	$(TOFU) -chdir=$(DEPLOY_RUNNER_DIR) init -input=false -lockfile=readonly
	$(call MGMT_RUN,$(TOFU) -chdir=$(DEPLOY_RUNNER_DIR) plan -input=false -out=$(DEPLOY_RUNNER_PLAN))
	@shasum -a 256 "$(DEPLOY_RUNNER_DIR)/$(DEPLOY_RUNNER_PLAN)"

# Mutates the doku-lab cluster (deploy-runner-01 on pve-core): only with explicit approval of the exact saved plan.
deploy-runner-apply:
	@test "$(DEPLOY_RUNNER_APPLY_APPROVED)" = yes || (echo "Explicit approval of the exact saved plan required: DEPLOY_RUNNER_APPLY_APPROVED=yes" >&2; exit 1)
	@test -n "$(DEPLOY_RUNNER_PLAN_SHA256)" || (echo "Supply DEPLOY_RUNNER_PLAN_SHA256 as printed by make deploy-runner-plan" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@printf '%s  %s\n' '$(DEPLOY_RUNNER_PLAN_SHA256)' '$(DEPLOY_RUNNER_DIR)/$(DEPLOY_RUNNER_PLAN)' | shasum -a 256 -c
	$(call MGMT_RUN,$(TOFU) -chdir=$(DEPLOY_RUNNER_DIR) apply -input=false $(DEPLOY_RUNNER_PLAN))
	@mv -f "$(DEPLOY_RUNNER_DIR)/$(DEPLOY_RUNNER_PLAN)" "$(DEPLOY_RUNNER_DIR)/deploy-runner.applied.tfplan"
	@echo "State updated locally: $(DEPLOY_RUNNER_DIR)/terraform.tfstate (this workstation only, never in Git)"

# Configures deploy-runner-01. Secrets come from the environment only, e.g.
#   scripts/secrets.py run /deploy-runner -- make deploy-runner-configure DEPLOY_RUNNER_CONFIGURE_APPROVED=yes
deploy-runner-configure:
	@test "$(DEPLOY_RUNNER_CONFIGURE_APPROVED)" = yes || (echo "Approve configuration of deploy-runner-01 with DEPLOY_RUNNER_CONFIGURE_APPROVED=yes" >&2; exit 1)
	@for v in FORGEJO_RUNNER_UUID FORGEJO_RUNNER_TOKEN DEPLOY_PROXMOX_VE_API_TOKEN; do test -n "$${!v:-}" || { echo "Set $$v in the environment (Infisical /deploy-runner)" >&2; exit 1; }; done
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	@set -euo pipefail; umask 077; inventory="$(CURDIR)/.local/deploy-runner-inventory.json"; mkdir -p "$(CURDIR)/.local"; \
	$(TOFU) -chdir=$(DEPLOY_RUNNER_DIR) output -json ansible_inventory > "$$inventory"; \
	ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) -i "$$inventory" ansible/playbooks/configure-deploy-runner.yml --diff

# Approval of a runner plan happens here, over SSH, never in a Forgejo job (whose logs are public and whose
# code any branch can change). Review shows the saved plan from the runner itself; approve writes the
# root-owned approval file the wrapper requires before `apply`.
DEPLOY_ROOT ?=
DEPLOY_RUNNER_SSH = ssh -o StrictHostKeyChecking=yes -o BatchMode=yes "debian@$$($(TOFU) -chdir=$(DEPLOY_RUNNER_DIR) output -raw address)"
define DEPLOY_ROOT_REQUIRED
	@printf '%s' "$(DEPLOY_ROOT)" | grep -Eq '^[a-z0-9][a-z0-9-]{0,62}$$' || (echo "Set DEPLOY_ROOT to a runner root, e.g. DEPLOY_ROOT=ci-disposable" >&2; exit 1)
endef

.PHONY: deploy-runner-review deploy-runner-approve
deploy-runner-review:
	$(DEPLOY_ROOT_REQUIRED)
	$(DEPLOY_RUNNER_SSH) sudo -n -u deploy /usr/local/sbin/homelab-deploy "$(DEPLOY_ROOT)" show

deploy-runner-approve:
	@test "$(DEPLOY_RUNNER_APPROVE)" = yes || (echo "Approve the reviewed plan explicitly: DEPLOY_RUNNER_APPROVE=yes" >&2; exit 1)
	$(DEPLOY_ROOT_REQUIRED)
	@printf '%s' "$(DEPLOY_PLAN_SHA256)" | grep -Eq '^[0-9a-f]{64}$$' || (echo "Set DEPLOY_PLAN_SHA256 to the PLAN_SHA256 shown by make deploy-runner-review" >&2; exit 1)
	printf '%s\n' "$(DEPLOY_PLAN_SHA256)" | $(DEPLOY_RUNNER_SSH) "sudo -n sh -c 'umask 022; cat > /etc/homelab-deploy/approvals/$(DEPLOY_ROOT).sha256'"
	@echo "Approved $(DEPLOY_PLAN_SHA256) for $(DEPLOY_ROOT); dispatch Deploy → apply with this SHA256."

# ─────────────────────────────────────────────
# k3s cluster on doku-lab (M004, ADR-011, OpenTofu + Ansible)
# VMs from terraform/stacks/k3s, applied from the operator workstation with the same token and gates as
# mgmt-*; k3s from ansible/playbooks/configure-k3s.yml with K3S_TOKEN from Infisical dev:/k3s.
# Rebuild one node from IaC: k3s-cluster-plan K3S_CLUSTER_REPLACE=<name>, apply, hostkeys, configure.
# ─────────────────────────────────────────────

K3S_CLUSTER_DIR := terraform/stacks/k3s
K3S_CLUSTER_PLAN := k3s.tfplan
K3S_CLUSTER_REPLACE ?=

.PHONY: k3s-cluster-check k3s-cluster-plan k3s-cluster-apply k3s-cluster-hostkeys k3s-cluster-configure

# Offline only: no credentials, no backend, mocked provider.
k3s-cluster-check:
	@set -euo pipefail; d="$(DEPLOY_RUNNER_CHECK_DATA)/k3s"; mkdir -p "$$d"; \
	$(TOFU) -chdir=$(K3S_CLUSTER_DIR) fmt -check -recursive; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(K3S_CLUSTER_DIR) init -backend=false -input=false -lockfile=readonly -no-color >/dev/null; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(K3S_CLUSTER_DIR) validate -no-color >/dev/null; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(K3S_CLUSTER_DIR) test -no-color | tail -n 1
	$(ANSIBLE) ansible/playbooks/configure-k3s.yml --syntax-check -i ansible/inventories/homelab.yml
	bash -n scripts/pin-guest-hostkey.sh
	$(VENV)/bin/python tests/k3s-cluster.py

k3s-cluster-plan:
	@test "$(K3S_CLUSTER_ALLOCATION_REVIEWED)" = yes || (echo "Confirm the allocation in $(K3S_CLUSTER_DIR)/terraform.tfvars, then set K3S_CLUSTER_ALLOCATION_REVIEWED=yes" >&2; exit 1)
	@test -z "$(K3S_CLUSTER_REPLACE)" || printf '%s' "$(K3S_CLUSTER_REPLACE)" | grep -Eq '^k3s-(server|agent)-[0-9]{2}$$' || (echo "K3S_CLUSTER_REPLACE must name one k3s VM, e.g. k3s-server-01" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@test -f "$(K3S_CLUSTER_DIR)/terraform.tfvars" || (echo "Create the private $(K3S_CLUSTER_DIR)/terraform.tfvars from terraform.tfvars.example" >&2; exit 1)
	@test -f "$(K3S_CLUSTER_DIR)/terraform.tfstate" || test "$(K3S_CLUSTER_NEW_STATE)" = yes || (echo "No $(K3S_CLUSTER_DIR)/terraform.tfstate here. Only the first creation starts from an empty state (K3S_CLUSTER_NEW_STATE=yes); otherwise copy the state from the workstation that holds it." >&2; exit 1)
	@test ! -e "$(K3S_CLUSTER_DIR)/$(K3S_CLUSTER_PLAN)" || mv -f "$(K3S_CLUSTER_DIR)/$(K3S_CLUSTER_PLAN)" "$(K3S_CLUSTER_DIR)/k3s.previous.tfplan"
	$(TOFU) -chdir=$(K3S_CLUSTER_DIR) init -input=false -lockfile=readonly
	$(call MGMT_RUN,$(TOFU) -chdir=$(K3S_CLUSTER_DIR) plan -input=false -out=$(K3S_CLUSTER_PLAN) $(if $(K3S_CLUSTER_REPLACE),'-replace=proxmox_virtual_environment_vm.node["$(K3S_CLUSTER_REPLACE)"]'))
	@shasum -a 256 "$(K3S_CLUSTER_DIR)/$(K3S_CLUSTER_PLAN)"

# Mutates the doku-lab cluster (k3s VMs): only with explicit approval of the exact saved plan.
k3s-cluster-apply:
	@test "$(K3S_CLUSTER_APPLY_APPROVED)" = yes || (echo "Explicit approval of the exact saved plan required: K3S_CLUSTER_APPLY_APPROVED=yes" >&2; exit 1)
	@test -n "$(K3S_CLUSTER_PLAN_SHA256)" || (echo "Supply K3S_CLUSTER_PLAN_SHA256 as printed by make k3s-cluster-plan" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@printf '%s  %s\n' '$(K3S_CLUSTER_PLAN_SHA256)' '$(K3S_CLUSTER_DIR)/$(K3S_CLUSTER_PLAN)' | shasum -a 256 -c
	$(call MGMT_RUN,$(TOFU) -chdir=$(K3S_CLUSTER_DIR) apply -input=false $(K3S_CLUSTER_PLAN))
	@mv -f "$(K3S_CLUSTER_DIR)/$(K3S_CLUSTER_PLAN)" "$(K3S_CLUSTER_DIR)/k3s.applied.tfplan"
	@chmod 0600 "$(K3S_CLUSTER_DIR)/terraform.tfstate"
	@echo "State updated locally: $(K3S_CLUSTER_DIR)/terraform.tfstate (this workstation only, never in Git)"

# Pins each k3s VM's SSH host key once the network and the VM's own disk agree (new or rebuilt VMs).
k3s-cluster-hostkeys:
	@set -euo pipefail; \
	$(TOFU) -chdir=$(K3S_CLUSTER_DIR) output -json ansible_inventory | \
	jq -r '{"pve-management":"192.168.0.10","pve-core":"192.168.0.11","pve-infra":"192.168.0.12","pve-lab":"192.168.0.16"} as $$pve | .all.children.k3s_cluster.hosts | to_entries[] | "\($$pve[.value.proxmox_node]) \(.value.vm_id) \(.value.ansible_host)"' | \
	while read -r node vmid ip; do scripts/pin-guest-hostkey.sh "$$node" "$$vmid" "$$ip"; done

# Configures k3s. The token comes from the environment only, e.g.
#   scripts/secrets.py run /k3s -- make k3s-cluster-configure K3S_CLUSTER_CONFIGURE_APPROVED=yes
k3s-cluster-configure:
	@test "$(K3S_CLUSTER_CONFIGURE_APPROVED)" = yes || (echo "Approve configuration of the k3s nodes with K3S_CLUSTER_CONFIGURE_APPROVED=yes" >&2; exit 1)
	@test -n "$${K3S_TOKEN:-}" || { echo "Set K3S_TOKEN in the environment (Infisical dev:/k3s)" >&2; exit 1; }
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	@set -euo pipefail; umask 077; inventory="$(CURDIR)/.local/k3s-inventory.json"; mkdir -p "$(CURDIR)/.local"; \
	$(TOFU) -chdir=$(K3S_CLUSTER_DIR) output -json ansible_inventory > "$$inventory"; \
	ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) -i "$$inventory" ansible/playbooks/configure-k3s.yml --diff

# ─────────────────────────────────────────────
# Headlamp, the Kubernetes UI (M005, ADR-011). Official chart, pinned; deployed from the workstation with
# the doku-lab kubeconfig until Argo CD takes over (M009). The admin login token goes to the secret store.
# ─────────────────────────────────────────────

HEADLAMP_CHART_VERSION := 0.46.0
HEADLAMP_REPO := https://kubernetes-sigs.github.io/headlamp/

.PHONY: headlamp-check headlamp-deploy headlamp-token

# Offline: renders the pinned chart with our values and checks the access rules (needs the chart download).
headlamp-check:
	$(VENV)/bin/python tests/headlamp.py

headlamp-deploy:
	@test "$(HEADLAMP_DEPLOY_APPROVED)" = yes || (echo "Approve the Headlamp deployment with HEADLAMP_DEPLOY_APPROVED=yes" >&2; exit 1)
	kubectl --context doku-lab apply -f services/argocd/apps/headlamp.yaml
	$(call ARGOCD_WAIT,headlamp)

# Copies the admin login token into the active secret store, path /headlamp (HEADLAMP_ADMIN_TOKEN), without
# printing it; scripts/secrets.py reads it back and compares.
headlamp-token:
	@set -euo pipefail; printf 'HEADLAMP_ADMIN_TOKEN=%s\n' "$$(kubectl --context doku-lab -n headlamp get secret headlamp-admin-token -o jsonpath='{.data.token}' | base64 -d)" \
	  | $(VENV)/bin/python scripts/secrets.py set /headlamp

# ─────────────────────────────────────────────
# Phase Console, the secret store that replaces Infisical (M008, ADR-004). Official chart, pinned; database
# "phase" on the shared PostgreSQL (ADR-015). Installed and kept in sync by Argo CD.
# ─────────────────────────────────────────────

PHASE_CHART_VERSION := 1.0.2
PHASE_REPO := https://helm.phase.dev
PHASE_SECRET_INPUTS := PHASE_SECRET_KEY PHASE_SERVER_SECRET PHASE_REDIS_PASSWORD PG_APP_PHASE_PASSWORD

.PHONY: phase-check phase-deploy

# Offline: renders the pinned chart with our values and checks the routes (needs the chart download), and
# tests scripts/secrets.py with fake stores and a throw-away age key.
phase-check:
	$(VENV)/bin/python tests/phase.py
	$(VENV)/bin/python tests/secrets.py

# Writes the Secret Phase needs, then hands Phase to Argo CD (services/argocd/apps/phase.yaml) and waits. The
# four values come from the environment only and go straight into the Kubernetes Secret (never printed):
# PHASE_SERVER_SECRET decrypts the stored secrets; losing it loses them. Chart, routes and the patch that
# lowers the minimum password length are in services/phase/kustomization.yaml. The pods read host and
# settings only when they start: after changing them, `kubectl -n phase rollout restart deployment`.
phase-deploy:
	@test "$(PHASE_DEPLOY_APPROVED)" = yes || (echo "Approve the Phase deployment with PHASE_DEPLOY_APPROVED=yes" >&2; exit 1)
	@for v in $(PHASE_SECRET_INPUTS); do test -n "$${!v:-}" || { echo "Set $$v in the environment (bootstrap secrets of Phase and the database password of the application phase)" >&2; exit 1; }; done
	@kubectl --context doku-lab create namespace phase --dry-run=client -o yaml | kubectl --context doku-lab apply -f - >/dev/null
	@set -euo pipefail; kubectl --context doku-lab -n phase create secret generic phase-console-secret --dry-run=client -o yaml \
	  --from-env-file=<(printf 'SECRET_KEY=%s\nSERVER_SECRET=%s\nREDIS_PASSWORD=%s\nDATABASE_PASSWORD=%s\n' "$$PHASE_SECRET_KEY" "$$PHASE_SERVER_SECRET" "$$PHASE_REDIS_PASSWORD" "$$PG_APP_PHASE_PASSWORD") \
	  | kubectl --context doku-lab apply -f - >/dev/null; echo "secret/phase-console-secret applied"
	kubectl --context doku-lab apply -f services/argocd/apps/phase.yaml
	$(call ARGOCD_WAIT,phase)

# ─────────────────────────────────────────────
# Ingress certificate: Traefik's default certificate for *.192.168.0.40.sslip.io (services/ingress).
# Certificate and key come from the environment only (store path /ingress), e.g.
#   scripts/secrets.py run /ingress -- make ingress-tls-deploy INGRESS_TLS_DEPLOY_APPROVED=yes
# The deployed certificate must be the one in keys/k3s-ingress.crt, which the workstation trusts.
# ─────────────────────────────────────────────

INGRESS_CERT_MANAGER_CHART := v1.21.3
INGRESS_CERT_MANAGER_REPO := https://charts.jetstack.io

.PHONY: ingress-check ingress-certs-deploy ingress-tls-deploy

# Offline: renders the pinned cert-manager chart and checks issuer, certificate and store (needs the chart download).
ingress-check:
	$(VENV)/bin/python tests/ingress.py

# Writes the Cloudflare token, then hands cert-manager, the Let's Encrypt issuer (Cloudflare DNS-01), the
# *.doku-lab.net wildcard, Traefik's certificate store and the routes to services outside k3s to Argo CD
# (services/argocd/apps/ingress.yaml).
#   scripts/secrets.py run /ingress -- make ingress-certs-deploy INGRESS_CERTS_DEPLOY_APPROVED=yes
ingress-certs-deploy:
	@test "$(INGRESS_CERTS_DEPLOY_APPROVED)" = yes || (echo "Approve cert-manager and the certificate issuer with INGRESS_CERTS_DEPLOY_APPROVED=yes" >&2; exit 1)
	@test -n "$${CLOUDFLARE_API_TOKEN:-}" || { echo "Set CLOUDFLARE_API_TOKEN in the environment (store path /ingress)" >&2; exit 1; }
	@kubectl --context doku-lab create namespace cert-manager --dry-run=client -o yaml | kubectl --context doku-lab apply -f - >/dev/null
	@set -euo pipefail; kubectl --context doku-lab -n cert-manager create secret generic cloudflare-api-token --dry-run=client -o yaml \
	  --from-env-file=<(printf 'api-token=%s\n' "$$CLOUDFLARE_API_TOKEN") | kubectl --context doku-lab apply -f - >/dev/null; echo "secret/cloudflare-api-token applied"
	kubectl --context doku-lab apply -f services/argocd/apps/ingress.yaml
	$(call ARGOCD_WAIT,ingress)
	kubectl --context doku-lab -n kube-system wait certificate/doku-lab-wildcard --for=condition=Ready --timeout=600s

ingress-tls-deploy:
	@test "$(INGRESS_TLS_DEPLOY_APPROVED)" = yes || (echo "Approve the ingress certificate deployment with INGRESS_TLS_DEPLOY_APPROVED=yes" >&2; exit 1)
	@for v in INGRESS_TLS_CERT_B64 INGRESS_TLS_KEY_B64; do test -n "$${!v:-}" || { echo "Set $$v in the environment (store path /ingress)" >&2; exit 1; }; done
	@set -euo pipefail; diff -q <(printf '%s' "$$INGRESS_TLS_CERT_B64" | base64 -d | openssl x509 -outform der | sha256sum) <(openssl x509 -in keys/k3s-ingress.crt -outform der | sha256sum) >/dev/null \
	  || { echo "The certificate in the store is not keys/k3s-ingress.crt" >&2; exit 1; }
	@set -euo pipefail; kubectl --context doku-lab -n kube-system create secret tls ingress-default-tls --dry-run=client -o yaml \
	  --cert=<(printf '%s' "$$INGRESS_TLS_CERT_B64" | base64 -d) --key=<(printf '%s' "$$INGRESS_TLS_KEY_B64" | base64 -d) \
	  | kubectl --context doku-lab apply -f - >/dev/null; echo "secret/ingress-default-tls applied"

# ─────────────────────────────────────────────
# Shared storage for k3s user data (M006, ADR-012): storage-01 on pve-core (NFS) + NFS CSI driver.
# Same gates as the other workstation roots. The VM holds data: prevent_destroy, no replace target.
# ─────────────────────────────────────────────

STORAGE_DIR := terraform/stacks/storage
STORAGE_PLAN := storage.tfplan
STORAGE_CSI_CHART_VERSION := 4.13.6
STORAGE_CSI_REPO := https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts

.PHONY: storage-check storage-plan storage-apply storage-hostkeys storage-configure storage-csi-deploy

# Offline only: no credentials, no backend, mocked provider.
storage-check:
	@set -euo pipefail; d="$(DEPLOY_RUNNER_CHECK_DATA)/storage"; mkdir -p "$$d"; \
	$(TOFU) -chdir=$(STORAGE_DIR) fmt -check -recursive; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(STORAGE_DIR) init -backend=false -input=false -lockfile=readonly -no-color >/dev/null; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(STORAGE_DIR) validate -no-color >/dev/null; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(STORAGE_DIR) test -no-color | tail -n 1
	$(ANSIBLE) ansible/playbooks/configure-storage.yml --syntax-check -i ansible/inventories/homelab.yml
	$(VENV)/bin/python tests/storage.py

storage-plan:
	@test "$(STORAGE_ALLOCATION_REVIEWED)" = yes || (echo "Confirm the allocation in $(STORAGE_DIR)/terraform.tfvars, then set STORAGE_ALLOCATION_REVIEWED=yes" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@test -f "$(STORAGE_DIR)/terraform.tfvars" || (echo "Create the private $(STORAGE_DIR)/terraform.tfvars from terraform.tfvars.example" >&2; exit 1)
	@test -f "$(STORAGE_DIR)/terraform.tfstate" || test "$(STORAGE_NEW_STATE)" = yes || (echo "No $(STORAGE_DIR)/terraform.tfstate here. Only the first creation starts from an empty state (STORAGE_NEW_STATE=yes); otherwise copy the state from the workstation that holds it." >&2; exit 1)
	@test ! -e "$(STORAGE_DIR)/$(STORAGE_PLAN)" || mv -f "$(STORAGE_DIR)/$(STORAGE_PLAN)" "$(STORAGE_DIR)/storage.previous.tfplan"
	$(TOFU) -chdir=$(STORAGE_DIR) init -input=false -lockfile=readonly
	$(call MGMT_RUN,$(TOFU) -chdir=$(STORAGE_DIR) plan -input=false -out=$(STORAGE_PLAN))
	@shasum -a 256 "$(STORAGE_DIR)/$(STORAGE_PLAN)"

# Mutates the doku-lab cluster (storage-01): only with explicit approval of the exact saved plan.
storage-apply:
	@test "$(STORAGE_APPLY_APPROVED)" = yes || (echo "Explicit approval of the exact saved plan required: STORAGE_APPLY_APPROVED=yes" >&2; exit 1)
	@test -n "$(STORAGE_PLAN_SHA256)" || (echo "Supply STORAGE_PLAN_SHA256 as printed by make storage-plan" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@printf '%s  %s\n' '$(STORAGE_PLAN_SHA256)' '$(STORAGE_DIR)/$(STORAGE_PLAN)' | shasum -a 256 -c
	$(call MGMT_RUN,$(TOFU) -chdir=$(STORAGE_DIR) apply -input=false $(STORAGE_PLAN))
	@mv -f "$(STORAGE_DIR)/$(STORAGE_PLAN)" "$(STORAGE_DIR)/storage.applied.tfplan"
	@chmod 0600 "$(STORAGE_DIR)/terraform.tfstate"
	@echo "State updated locally: $(STORAGE_DIR)/terraform.tfstate (this workstation only, never in Git)"

storage-hostkeys:
	@set -euo pipefail; \
	$(TOFU) -chdir=$(STORAGE_DIR) output -json ansible_inventory | \
	jq -r '{"pve-core":"192.168.0.11"} as $$pve | .all.children.storage.hosts | to_entries[] | "\($$pve[.value.proxmox_node]) \(.value.vm_id) \(.value.ansible_host)"' | \
	while read -r node vmid ip; do scripts/pin-guest-hostkey.sh "$$node" "$$vmid" "$$ip"; done

storage-configure:
	@test "$(STORAGE_CONFIGURE_APPROVED)" = yes || (echo "Approve configuration of storage-01 with STORAGE_CONFIGURE_APPROVED=yes" >&2; exit 1)
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	@set -euo pipefail; umask 077; inventory="$(CURDIR)/.local/storage-inventory.json"; mkdir -p "$(CURDIR)/.local"; \
	$(TOFU) -chdir=$(STORAGE_DIR) output -json ansible_inventory > "$$inventory"; \
	ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) -i "$$inventory" ansible/playbooks/configure-storage.yml --diff

# NFS CSI driver and the nvme-shared StorageClass, installed and kept in sync by Argo CD
# (services/argocd/apps/storage.yaml).
storage-csi-deploy:
	@test "$(STORAGE_CSI_DEPLOY_APPROVED)" = yes || (echo "Approve the CSI deployment with STORAGE_CSI_DEPLOY_APPROVED=yes" >&2; exit 1)
	kubectl --context doku-lab apply -f services/argocd/apps/storage.yaml
	$(call ARGOCD_WAIT,storage)

# ─────────────────────────────────────────────
# Shared PostgreSQL platform (M007, ADR-015): pg-01..03, one per Proxmox host, outside k3s. PostgreSQL 17
# under Patroni with etcd and a virtual IP (192.168.0.60). Same gates as the other workstation roots.
# The VMs hold data: prevent_destroy, no replace target.
# ─────────────────────────────────────────────

POSTGRESQL_DIR := terraform/stacks/postgresql
POSTGRESQL_PLAN := postgresql.tfplan

.PHONY: postgresql-check postgresql-plan postgresql-apply postgresql-hostkeys postgresql-configure postgresql-status

# Offline only: no credentials, no backend, mocked provider.
postgresql-check:
	@set -euo pipefail; d="$(DEPLOY_RUNNER_CHECK_DATA)/postgresql"; mkdir -p "$$d"; \
	$(TOFU) -chdir=$(POSTGRESQL_DIR) fmt -check -recursive; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(POSTGRESQL_DIR) init -backend=false -input=false -lockfile=readonly -no-color >/dev/null; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(POSTGRESQL_DIR) validate -no-color >/dev/null; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(POSTGRESQL_DIR) test -no-color | tail -n 1
	$(ANSIBLE) ansible/playbooks/configure-postgresql.yml --syntax-check -i ansible/inventories/homelab.yml
	$(VENV)/bin/python tests/postgresql.py

postgresql-plan:
	@test "$(POSTGRESQL_ALLOCATION_REVIEWED)" = yes || (echo "Confirm the allocation in $(POSTGRESQL_DIR)/terraform.tfvars, then set POSTGRESQL_ALLOCATION_REVIEWED=yes" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@test -f "$(POSTGRESQL_DIR)/terraform.tfvars" || (echo "Create the private $(POSTGRESQL_DIR)/terraform.tfvars from terraform.tfvars.example" >&2; exit 1)
	@test -f "$(POSTGRESQL_DIR)/terraform.tfstate" || test "$(POSTGRESQL_NEW_STATE)" = yes || (echo "No $(POSTGRESQL_DIR)/terraform.tfstate here. Only the first creation starts from an empty state (POSTGRESQL_NEW_STATE=yes); otherwise copy the state from the workstation that holds it." >&2; exit 1)
	@test ! -e "$(POSTGRESQL_DIR)/$(POSTGRESQL_PLAN)" || mv -f "$(POSTGRESQL_DIR)/$(POSTGRESQL_PLAN)" "$(POSTGRESQL_DIR)/postgresql.previous.tfplan"
	$(TOFU) -chdir=$(POSTGRESQL_DIR) init -input=false -lockfile=readonly
	$(call MGMT_RUN,$(TOFU) -chdir=$(POSTGRESQL_DIR) plan -input=false -out=$(POSTGRESQL_PLAN))
	@shasum -a 256 "$(POSTGRESQL_DIR)/$(POSTGRESQL_PLAN)"

# Mutates the doku-lab cluster (pg-01..03): only with explicit approval of the exact saved plan.
postgresql-apply:
	@test "$(POSTGRESQL_APPLY_APPROVED)" = yes || (echo "Explicit approval of the exact saved plan required: POSTGRESQL_APPLY_APPROVED=yes" >&2; exit 1)
	@test -n "$(POSTGRESQL_PLAN_SHA256)" || (echo "Supply POSTGRESQL_PLAN_SHA256 as printed by make postgresql-plan" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@printf '%s  %s\n' '$(POSTGRESQL_PLAN_SHA256)' '$(POSTGRESQL_DIR)/$(POSTGRESQL_PLAN)' | shasum -a 256 -c
	$(call MGMT_RUN,$(TOFU) -chdir=$(POSTGRESQL_DIR) apply -input=false $(POSTGRESQL_PLAN))
	@mv -f "$(POSTGRESQL_DIR)/$(POSTGRESQL_PLAN)" "$(POSTGRESQL_DIR)/postgresql.applied.tfplan"
	@chmod 0600 "$(POSTGRESQL_DIR)/terraform.tfstate"
	@echo "State updated locally: $(POSTGRESQL_DIR)/terraform.tfstate (this workstation only, never in Git)"

postgresql-hostkeys:
	@set -euo pipefail; \
	$(TOFU) -chdir=$(POSTGRESQL_DIR) output -json ansible_inventory | \
	jq -r '{"pve-core":"192.168.0.11","pve-infra":"192.168.0.12","pve-lab":"192.168.0.16"} as $$pve | .all.children.postgresql.hosts | to_entries[] | "\($$pve[.value.proxmox_node]) \(.value.vm_id) \(.value.ansible_host)"' | \
	while read -r node vmid ip; do scripts/pin-guest-hostkey.sh "$$node" "$$vmid" "$$ip"; done

# Configures etcd, Patroni, the virtual IP and the application databases. Credentials come from the
# environment only, e.g.
#   scripts/secrets.py run /postgresql -- make postgresql-configure POSTGRESQL_CONFIGURE_APPROVED=yes
postgresql-configure:
	@test "$(POSTGRESQL_CONFIGURE_APPROVED)" = yes || (echo "Approve configuration of the PostgreSQL members with POSTGRESQL_CONFIGURE_APPROVED=yes" >&2; exit 1)
	@test -n "$${PG_SUPERUSER_PASSWORD:-}" || { echo "Set PG_SUPERUSER_PASSWORD and the other PG_* credentials in the environment (secret store path /postgresql)" >&2; exit 1; }
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	@set -euo pipefail; umask 077; inventory="$(CURDIR)/.local/postgresql-inventory.json"; mkdir -p "$(CURDIR)/.local"; \
	$(TOFU) -chdir=$(POSTGRESQL_DIR) output -json ansible_inventory > "$$inventory"; \
	ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) -i "$$inventory" ansible/playbooks/configure-postgresql.yml --diff

# ─────────────────────────────────────────────
# Lean observability (TASK-020): Prometheus, Loki and Grafana on k3s, Alloy as the only collector (one in
# the cluster, one on every VM). Official charts, pinned; kept in sync by Argo CD.
# ─────────────────────────────────────────────

OBS_DIR := services/observability
OBS_PROMETHEUS_CHART := 29.47.2
OBS_LOKI_CHART := 7.6.0
OBS_ALLOY_CHART := 1.16.0
OBS_GRAFANA_CHART := 14.5.0
OBS_PROMETHEUS_REPO := https://prometheus-community.github.io/helm-charts
OBS_GRAFANA_LABS_REPO := https://grafana.github.io/helm-charts
OBS_GRAFANA_REPO := https://grafana-community.github.io/helm-charts
OBS_AGENT_ROOTS := k3s postgresql storage deploy-runner

.PHONY: observability-check observability-deploy observability-agents

# Offline: renders the pinned charts with our values, checks the allow-lists and routes (needs the chart downloads).
observability-check:
	$(ANSIBLE) ansible/playbooks/configure-observability-agents.yml --syntax-check -i ansible/inventories/homelab.yml
	$(VENV)/bin/python tests/observability.py

# Writes Grafana's two passwords (environment only: store paths /monitoring and /postgresql), then hands the
# four charts, the routes, the Alloy configuration and the dashboards to Argo CD
# (services/argocd/apps/monitoring.yaml).
observability-deploy:
	@test "$(OBSERVABILITY_DEPLOY_APPROVED)" = yes || (echo "Approve the observability deployment with OBSERVABILITY_DEPLOY_APPROVED=yes" >&2; exit 1)
	@for v in GRAFANA_ADMIN_PASSWORD PG_APP_GRAFANA_PASSWORD; do test -n "$${!v:-}" || { echo "Set $$v in the environment (store paths /monitoring and /postgresql)" >&2; exit 1; }; done
	@kubectl --context doku-lab create namespace monitoring --dry-run=client -o yaml | kubectl --context doku-lab apply -f - >/dev/null
	@set -euo pipefail; k="kubectl --context doku-lab -n monitoring"; \
	$$k create secret generic grafana-admin --dry-run=client -o yaml --from-env-file=<(printf 'admin-user=admin\nadmin-password=%s\n' "$$GRAFANA_ADMIN_PASSWORD") | $$k apply -f - >/dev/null; \
	$$k create secret generic grafana-db --dry-run=client -o yaml --from-env-file=<(printf 'password=%s\n' "$$PG_APP_GRAFANA_PASSWORD") | $$k apply -f - >/dev/null; \
	echo "secrets applied"
	kubectl --context doku-lab apply -f services/argocd/apps/monitoring.yaml
	$(call ARGOCD_WAIT,monitoring)

# Installs and configures Alloy on every VM of the listed roots (inventories from their OpenTofu outputs).
# OBS_INVENTORY=netbox reads the same hosts from NetBox instead (ansible/inventories/netbox.yml, read-only
# token, no OpenTofu state needed): scripts/secrets.py run /netbox -- make observability-agents OBS_INVENTORY=netbox …
# OBS_ANSIBLE_ARGS passes extra arguments to ansible-playbook, e.g. --check.
# On the PostgreSQL members it also creates the read-only monitoring role, through the local socket.
observability-agents:
	@test "$(OBSERVABILITY_AGENTS_APPROVED)" = yes || (echo "Approve the agent configuration with OBSERVABILITY_AGENTS_APPROVED=yes" >&2; exit 1)
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	@set -euo pipefail; umask 077; mkdir -p "$(CURDIR)/.local"; args=(); \
	if [ "$(OBS_INVENTORY)" = netbox ]; then \
	  test -n "$${NETBOX_READ_TOKEN:-}" || { echo "Set NETBOX_READ_TOKEN in the environment (store path /netbox)" >&2; exit 1; }; \
	  export NETBOX_TOKEN="$$NETBOX_READ_TOKEN"; args=(-i ansible/inventories/netbox.yml); \
	else for root in $(OBS_AGENT_ROOTS); do inventory="$(CURDIR)/.local/$$root-inventory.json"; \
	  $(TOFU) -chdir=terraform/stacks/$$root output -json ansible_inventory > "$$inventory"; args+=(-i "$$inventory"); done; fi; \
	ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) "$${args[@]}" ansible/playbooks/configure-observability-agents.yml --diff $(OBS_ANSIBLE_ARGS)

# Read-only: members, roles, replication lag, and which member holds the virtual IP.
postgresql-status:
	@set -euo pipefail; \
	$(TOFU) -chdir=$(POSTGRESQL_DIR) output -json ansible_inventory | \
	jq -r '.all.children.postgresql as $$g | $$g.hosts | to_entries[] | "\(.key) \(.value.ansible_user)@\(.value.ansible_host) \($$g.vars.patroni_virtual_ip)"' | \
	{ listed=no; while read -r name target vip; do \
	  if [ "$$listed" = no ] && ssh -n -o BatchMode=yes -o ConnectTimeout=5 "$$target" 'sudo -u postgres patronictl -c /etc/patroni/config.yml list' 2>/dev/null; then listed=yes; fi; \
	  ssh -n -o BatchMode=yes -o ConnectTimeout=5 "$$target" "ip -4 -o addr show | grep -q ' $$vip/' && echo 'virtual IP $$vip: $$name' || true" 2>/dev/null || echo "$$name: unreachable"; \
	done; }

# ─────────────────────────────────────────────
# LAN DNS (TASK-022): dns-01 on pve-infra runs AdGuard Home from the configuration in Git, outside k3s.
# Same gates as the other workstation roots. The admin password hash comes from the store path /dns:
#   scripts/secrets.py run /dns -- make dns-configure DNS_CONFIGURE_APPROVED=yes
# DNS_SERVICE_ADDRESS=192.168.0.20 makes the VM answer on the LAN's DNS address as well (cutover: only
# after the old AdGuard container is stopped).
# ─────────────────────────────────────────────

DNS_DIR := terraform/stacks/dns
DNS_PLAN := dns.tfplan

.PHONY: dns-check dns-plan dns-apply dns-hostkeys dns-configure

# Offline only: no credentials, no backend, mocked provider.
dns-check:
	@set -euo pipefail; d="$(DEPLOY_RUNNER_CHECK_DATA)/dns"; mkdir -p "$$d"; \
	$(TOFU) -chdir=$(DNS_DIR) fmt -check -recursive; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(DNS_DIR) init -backend=false -input=false -lockfile=readonly -no-color >/dev/null; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(DNS_DIR) validate -no-color >/dev/null; \
	TF_DATA_DIR="$$d" $(TOFU) -chdir=$(DNS_DIR) test -no-color | tail -n 1
	$(ANSIBLE) ansible/playbooks/configure-dns.yml --syntax-check -i ansible/inventories/homelab.yml
	$(VENV)/bin/python tests/dns.py

dns-plan:
	@test "$(DNS_ALLOCATION_REVIEWED)" = yes || (echo "Confirm the allocation in $(DNS_DIR)/terraform.tfvars, then set DNS_ALLOCATION_REVIEWED=yes" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@test -f "$(DNS_DIR)/terraform.tfvars" || (echo "Create the private $(DNS_DIR)/terraform.tfvars from terraform.tfvars.example" >&2; exit 1)
	@test -f "$(DNS_DIR)/terraform.tfstate" || test "$(DNS_NEW_STATE)" = yes || (echo "No $(DNS_DIR)/terraform.tfstate here. Only the first creation starts from an empty state (DNS_NEW_STATE=yes); otherwise copy the state from the workstation that holds it." >&2; exit 1)
	@test ! -e "$(DNS_DIR)/$(DNS_PLAN)" || mv -f "$(DNS_DIR)/$(DNS_PLAN)" "$(DNS_DIR)/dns.previous.tfplan"
	$(TOFU) -chdir=$(DNS_DIR) init -input=false -lockfile=readonly
	$(call MGMT_RUN,$(TOFU) -chdir=$(DNS_DIR) plan -input=false -out=$(DNS_PLAN))
	@shasum -a 256 "$(DNS_DIR)/$(DNS_PLAN)"

# Mutates the doku-lab cluster (dns-01): only with explicit approval of the exact saved plan.
dns-apply:
	@test "$(DNS_APPLY_APPROVED)" = yes || (echo "Explicit approval of the exact saved plan required: DNS_APPLY_APPROVED=yes" >&2; exit 1)
	@test -n "$(DNS_PLAN_SHA256)" || (echo "Supply DNS_PLAN_SHA256 as printed by make dns-plan" >&2; exit 1)
	$(MGMT_REQUIRE_SOURCE)
	@printf '%s  %s\n' '$(DNS_PLAN_SHA256)' '$(DNS_DIR)/$(DNS_PLAN)' | shasum -a 256 -c
	$(call MGMT_RUN,$(TOFU) -chdir=$(DNS_DIR) apply -input=false $(DNS_PLAN))
	@mv -f "$(DNS_DIR)/$(DNS_PLAN)" "$(DNS_DIR)/dns.applied.tfplan"
	@chmod 0600 "$(DNS_DIR)/terraform.tfstate"
	@echo "State updated locally: $(DNS_DIR)/terraform.tfstate (this workstation only, never in Git)"

dns-hostkeys:
	@set -euo pipefail; \
	$(TOFU) -chdir=$(DNS_DIR) output -json ansible_inventory | \
	jq -r '{"pve-core":"192.168.0.11","pve-infra":"192.168.0.12","pve-lab":"192.168.0.16"} as $$pve | .all.children.dns.hosts | to_entries[] | "\($$pve[.value.proxmox_node]) \(.value.vm_id) \(.value.ansible_host)"' | \
	while read -r node vmid ip; do scripts/pin-guest-hostkey.sh "$$node" "$$vmid" "$$ip"; done

dns-configure:
	@test "$(DNS_CONFIGURE_APPROVED)" = yes || (echo "Approve configuration of dns-01 with DNS_CONFIGURE_APPROVED=yes" >&2; exit 1)
	@test -n "$${ADGUARD_ADMIN_HASH:-}" || { echo "Set ADGUARD_ADMIN_HASH in the environment (store path /dns)" >&2; exit 1; }
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	@set -euo pipefail; umask 077; inventory="$(CURDIR)/.local/dns-inventory.json"; mkdir -p "$(CURDIR)/.local"; \
	$(TOFU) -chdir=$(DNS_DIR) output -json ansible_inventory > "$$inventory"; \
	ANSIBLE_HOST_KEY_CHECKING=True $(ANSIBLE) -i "$$inventory" ansible/playbooks/configure-dns.yml --diff $(if $(DNS_SERVICE_ADDRESS),-e adguard_service_address=$(DNS_SERVICE_ADDRESS))

# ─────────────────────────────────────────────
# Argo CD (M009, ADR-011): keeps the applications of services/argocd/apps in sync with the main branch on
# Forgejo. Argo CD itself is installed from the workstation: on a rebuilt cluster it is what deploys the rest.
# ─────────────────────────────────────────────

ARGOCD_CHART_VERSION := 10.18.1
ARGOCD_REPO := https://argoproj.github.io/argo-helm
ARGOCD_HELM_ARGS := argocd argo-cd --repo $(ARGOCD_REPO) --version $(ARGOCD_CHART_VERSION) --namespace argocd -f services/argocd/values.yaml
# Waits until the named application is in sync with Git and healthy.
ARGOCD_WAIT = kubectl --context doku-lab -n argocd wait --timeout=900s --for=jsonpath='{.status.sync.status}'=Synced application/$(1) && kubectl --context doku-lab -n argocd wait --timeout=900s --for=jsonpath='{.status.health.status}'=Healthy application/$(1)

.PHONY: argocd-check argocd-deploy argocd-password

# Offline: renders the pinned chart with our values and checks route, project and applications (needs the chart download).
argocd-check:
	$(VENV)/bin/python tests/argocd.py

# No secret input: Argo CD generates its own keys and the first admin password (see argocd-password).
argocd-deploy:
	@test "$(ARGOCD_DEPLOY_APPROVED)" = yes || (echo "Approve the Argo CD deployment with ARGOCD_DEPLOY_APPROVED=yes" >&2; exit 1)
	@kubectl --context doku-lab create namespace argocd --dry-run=client -o yaml | kubectl --context doku-lab apply -f - >/dev/null
	helm upgrade --install $(ARGOCD_HELM_ARGS) --kube-context doku-lab --wait --timeout 10m
	kubectl --context doku-lab apply -f services/argocd/access.yaml

# Moves the generated admin password into the secret store (path /argocd, never printed) and removes the
# Kubernetes Secret that held it in clear, as the Argo CD documentation asks. Run once after the first deploy.
argocd-password:
	@test "$(ARGOCD_PASSWORD_APPROVED)" = yes || (echo "Approve storing the Argo CD admin password with ARGOCD_PASSWORD_APPROVED=yes" >&2; exit 1)
	@set -euo pipefail; k="kubectl --context doku-lab -n argocd"; \
	$$k get secret argocd-initial-admin-secret >/dev/null 2>&1 || { echo "argocd-initial-admin-secret is gone: the password is already in the secret store (path /argocd)"; exit 0; }; \
	printf 'ARGOCD_ADMIN_PASSWORD=%s\n' "$$($$k get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)" | scripts/secrets.py set /argocd; \
	$$k delete secret argocd-initial-admin-secret

# ─────────────────────────────────────────────
# NetBox (M013, ADR-016): inventory and IPAM on k3s (services/netbox), official chart, shared PostgreSQL.
# Installed and kept in sync by Argo CD (services/argocd/apps/netbox.yaml pins the chart). Nothing below is
# needed to build or rebuild the platform: every root keeps its own variables and inventory, NetBox is
# populated from them.
# ─────────────────────────────────────────────

NETBOX_SECRET_INPUTS := NETBOX_SECRET_KEY NETBOX_API_TOKEN_PEPPER NETBOX_SUPERUSER_PASSWORD NETBOX_VALKEY_PASSWORD PG_APP_NETBOX_PASSWORD
NETBOX_SYNC := $(VENV)/bin/python scripts/netbox-sync.py

.PHONY: netbox-check netbox-deploy netbox-identities netbox-discover netbox-plan netbox-apply netbox-inventory netbox-export

# Offline: renders the pinned chart with our values (needs the chart download) and runs the inventory
# reconciliation against an in-memory NetBox.
netbox-check:
	$(VENV)/bin/python tests/netbox.py

# Writes the Secret NetBox needs, then hands NetBox to Argo CD and waits until it is in sync and healthy. The
# five values come from the environment only and go straight into the Kubernetes Secret (never printed).
# api_token stays empty: the image creates no token for the superuser; `make netbox-identities` provisions
# short-lived ones from the password when it needs them.
#   scripts/secrets.py run /netbox /postgresql -- make netbox-deploy NETBOX_DEPLOY_APPROVED=yes
netbox-deploy:
	@test "$(NETBOX_DEPLOY_APPROVED)" = yes || (echo "Approve the NetBox deployment with NETBOX_DEPLOY_APPROVED=yes" >&2; exit 1)
	@for v in $(NETBOX_SECRET_INPUTS); do test -n "$${!v:-}" || { echo "Set $$v in the environment (store paths /netbox and /postgresql)" >&2; exit 1; }; done
	@kubectl --context doku-lab create namespace netbox --dry-run=client -o yaml | kubectl --context doku-lab apply -f - >/dev/null
	@set -euo pipefail; kubectl --context doku-lab -n netbox create secret generic netbox-secrets --dry-run=client -o yaml \
	  --from-env-file=<(printf 'secret_key=%s\napi_token_peppers={"1":"%s"}\nemail_password=\nusername=admin\nemail=admin@doku-lab.net\npassword=%s\napi_token=\nvalkey_password=%s\ndb_password=%s\n' \
	    "$$NETBOX_SECRET_KEY" "$$NETBOX_API_TOKEN_PEPPER" "$$NETBOX_SUPERUSER_PASSWORD" "$$NETBOX_VALKEY_PASSWORD" "$$PG_APP_NETBOX_PASSWORD") \
	  | kubectl --context doku-lab apply -f - >/dev/null; echo "secret/netbox-secrets applied"
	kubectl --context doku-lab apply -f services/argocd/apps/netbox.yaml
	$(call ARGOCD_WAIT,netbox)

# Service accounts for automation, created with a 10-minute superuser token provisioned from the password: "inventory-sync" may write the
# inventory, "automation-read" may only read it. Their API tokens go into the secret store (path /netbox).
#   scripts/secrets.py run /netbox -- make netbox-identities NETBOX_IDENTITIES_APPROVED=yes
netbox-identities:
	@test "$(NETBOX_IDENTITIES_APPROVED)" = yes || (echo "Approve the creation of the NetBox service accounts with NETBOX_IDENTITIES_APPROVED=yes" >&2; exit 1)
	$(NETBOX_SYNC) identities

# Read-only snapshot of one Proxmox environment into .local/netbox/ (GET requests only):
#   scripts/secrets.py run /pve-management -- make netbox-discover NETBOX_SOURCE=doku-lab
#   scripts/secrets.py run / -- make netbox-discover NETBOX_SOURCE=legacy
netbox-discover:
	@test -n "$(NETBOX_SOURCE)" || (echo "Set NETBOX_SOURCE to a source of services/netbox/inventory.yaml (doku-lab or legacy)" >&2; exit 1)
	$(NETBOX_SYNC) discover $(NETBOX_SOURCE)

# What the reconciliation would change in NetBox, and what needs a human decision. Writes nothing.
#   scripts/secrets.py run /netbox -- make netbox-plan
netbox-plan:
	$(NETBOX_SYNC) plan

#   scripts/secrets.py run /netbox -- make netbox-apply NETBOX_APPLY_APPROVED=yes
netbox-apply:
	@test "$(NETBOX_APPLY_APPROVED)" = yes || (echo "Read 'make netbox-plan' first, then approve the inventory write with NETBOX_APPLY_APPROVED=yes" >&2; exit 1)
	$(NETBOX_SYNC) apply

# The whole inventory as sorted YAML files, one per kind, for a history in Git (read-only token):
#   scripts/secrets.py run /netbox -- make netbox-export NETBOX_EXPORT_DIR=/path/to/a/private/checkout
netbox-export:
	@test -n "$(NETBOX_EXPORT_DIR)" || (echo "Set NETBOX_EXPORT_DIR to the directory to write (a checkout of the private history repository)" >&2; exit 1)
	$(NETBOX_SYNC) export "$(NETBOX_EXPORT_DIR)"

# The Ansible inventory as NetBox serves it (read-only token):
#   scripts/secrets.py run /netbox -- make netbox-inventory
netbox-inventory:
	@test -n "$${NETBOX_READ_TOKEN:-}" || { echo "Set NETBOX_READ_TOKEN in the environment (store path /netbox)" >&2; exit 1; }
	NETBOX_TOKEN="$$NETBOX_READ_TOKEN" $(VENV)/bin/ansible-inventory -i ansible/inventories/netbox.yml --graph

# ─────────────────────────────────────────────
# Windmill on k3s (M009, ADR-005): forms, schedules and flows that read their data from NetBox (ADR-016).
# Official chart, kept in sync by Argo CD (services/argocd/apps/windmill.yaml), database "windmill" on the
# shared PostgreSQL. The targets of services/windmill/targets.mk belong to the retired Compose deployment.
# ─────────────────────────────────────────────

WINDMILL_K3S_CHART_VERSION := 4.0.324
WINDMILL_K3S_REPO := https://windmill-labs.github.io/windmill-helm-charts/
WINDMILL_ADMIN := $(VENV)/bin/python scripts/windmill-admin.py

.PHONY: windmill-k3s-check windmill-deploy windmill-bootstrap windmill-push

# Offline: renders the pinned chart with our values (needs the chart download) and checks the scripts of windmill/.
windmill-k3s-check:
	$(VENV)/bin/python tests/windmill-k3s.py

# Writes the database connection string (environment only, never printed), then hands Windmill to Argo CD.
#   scripts/secrets.py run /postgresql -- make windmill-deploy WINDMILL_DEPLOY_APPROVED=yes
windmill-deploy:
	@test "$(WINDMILL_DEPLOY_APPROVED)" = yes || (echo "Approve the Windmill deployment with WINDMILL_DEPLOY_APPROVED=yes" >&2; exit 1)
	@test -n "$${PG_APP_WINDMILL_PASSWORD:-}" || { echo "Set PG_APP_WINDMILL_PASSWORD in the environment (store path /postgresql)" >&2; exit 1; }
	@kubectl --context doku-lab create namespace windmill --dry-run=client -o yaml | kubectl --context doku-lab apply -f - >/dev/null
	@set -euo pipefail; kubectl --context doku-lab -n windmill create secret generic windmill-secrets --dry-run=client -o yaml \
	  --from-env-file=<(printf 'url=postgres://windmill:%s@192.168.0.60:5432/windmill?sslmode=require\n' "$$PG_APP_WINDMILL_PASSWORD") \
	  | kubectl --context doku-lab apply -f - >/dev/null; echo "secret/windmill-secrets applied"
	kubectl --context doku-lab apply -f services/argocd/apps/windmill.yaml
	$(call ARGOCD_WAIT,windmill)

# Once after the first deployment: replaces the built-in administrator password, creates the workspace and the
# automation token (stored at /windmill, never printed) and gives the workspace its read-only NetBox access.
#   scripts/secrets.py run /windmill /netbox -- make windmill-bootstrap WINDMILL_BOOTSTRAP_APPROVED=yes
windmill-bootstrap:
	@test "$(WINDMILL_BOOTSTRAP_APPROVED)" = yes || (echo "Approve the Windmill bootstrap with WINDMILL_BOOTSTRAP_APPROVED=yes" >&2; exit 1)
	$(WINDMILL_ADMIN) bootstrap

# Publishes the scripts of windmill/ to the workspace (creates or updates; never deletes).
#   scripts/secrets.py run /windmill -- make windmill-push
windmill-push:
	$(WINDMILL_ADMIN) push

# ─────────────────────────────────────────────
# Authentik (M014, ADR-017): single sign-on for the web interfaces. Official chart, kept in sync by Argo CD
# (services/argocd/apps/authentik.yaml), database "authentik" on the shared PostgreSQL. Applications, groups
# and access rules are the blueprints of services/authentik/blueprints. Every application keeps its local
# administrator: nothing needs Authentik to be rebuilt or repaired.
# ─────────────────────────────────────────────

AUTHENTIK_CHART_VERSION := 2026.8.5
AUTHENTIK_REPO := https://charts.goauthentik.io
# One OIDC client secret per application that signs in through Authentik: SSO_<NAME>_CLIENT_SECRET.
AUTHENTIK_CLIENTS := ARGOCD GRAFANA NETBOX WINDMILL
AUTHENTIK_SECRET_INPUTS := AUTHENTIK_SECRET_KEY AUTHENTIK_BOOTSTRAP_PASSWORD AUTHENTIK_BOOTSTRAP_TOKEN $(foreach c,$(AUTHENTIK_CLIENTS),SSO_$(c)_CLIENT_SECRET)
AUTHENTIK_ADMIN := $(VENV)/bin/python scripts/authentik-admin.py

.PHONY: authentik-check authentik-secrets authentik-deploy authentik-status

# Offline: renders the pinned chart with our values and checks route, blueprints and client wiring (needs the chart download).
authentik-check:
	$(VENV)/bin/python tests/authentik.py

# Generates the values the store does not hold yet (never replaces one, never prints one). Run again after
# adding a name to AUTHENTIK_CLIENTS.
authentik-secrets:
	@test "$(AUTHENTIK_SECRETS_APPROVED)" = yes || (echo "Approve the creation of the missing Authentik secrets with AUTHENTIK_SECRETS_APPROVED=yes" >&2; exit 1)
	scripts/ensure-secrets.py /postgresql PG_APP_AUTHENTIK_PASSWORD
	scripts/ensure-secrets.py /authentik $(AUTHENTIK_SECRET_INPUTS)

# Writes the Secret Authentik reads its configuration and the client secrets from (environment only, never
# printed), hands Authentik to Argo CD, restarts the worker when a client secret was added, and waits until
# every blueprint is applied.
#   scripts/secrets.py run /authentik /postgresql -- make authentik-deploy AUTHENTIK_DEPLOY_APPROVED=yes
authentik-deploy:
	@test "$(AUTHENTIK_DEPLOY_APPROVED)" = yes || (echo "Approve the Authentik deployment with AUTHENTIK_DEPLOY_APPROVED=yes" >&2; exit 1)
	@for v in $(AUTHENTIK_SECRET_INPUTS) PG_APP_AUTHENTIK_PASSWORD; do test -n "$${!v:-}" || { echo "Set $$v in the environment (store paths /authentik and /postgresql; make authentik-secrets creates what is missing)" >&2; exit 1; }; done
	@kubectl --context doku-lab create namespace authentik --dry-run=client -o yaml | kubectl --context doku-lab apply -f - >/dev/null
	@set -euo pipefail; k="kubectl --context doku-lab -n authentik"; \
	before="$$($$k get secret authentik-secrets -o jsonpath='{.metadata.resourceVersion}' 2>/dev/null || true)"; \
	$$k create secret generic authentik-secrets --dry-run=client -o yaml \
	  --from-env-file=<(printf 'AUTHENTIK_POSTGRESQL__PASSWORD=%s\n' "$$PG_APP_AUTHENTIK_PASSWORD"; for v in $(AUTHENTIK_SECRET_INPUTS); do printf '%s=%s\n' "$$v" "$${!v}"; done) \
	  | $$k apply -f - >/dev/null; echo "secret/authentik-secrets applied"; \
	after="$$($$k get secret authentik-secrets -o jsonpath='{.metadata.resourceVersion}')"; \
	if [ -n "$$before" ] && [ "$$before" != "$$after" ]; then $$k rollout restart deployment/authentik-server deployment/authentik-worker; fi
	kubectl --context doku-lab apply -f services/argocd/apps/authentik.yaml
	$(call ARGOCD_WAIT,authentik)
	kubectl --context doku-lab -n authentik rollout status deployment/authentik-server deployment/authentik-worker --timeout=900s
	AUTHENTIK_EXPECTED_BLUEPRINTS=$(words $(wildcard services/authentik/blueprints/*.yaml)) $(AUTHENTIK_ADMIN) status --apply

# Blueprints, applications and who may open them, as Authentik reports them (read-only).
#   scripts/secrets.py run /authentik -- make authentik-status
authentik-status:
	$(AUTHENTIK_ADMIN) status
