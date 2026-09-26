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

# New isolated ownership; never invokes workstation host configuration.
CONTROLLER_DIR := terraform/stacks/pve-lab-controller
.PHONY: controller-check controller-plan controller-apply
controller-check:
	$(VENV)/bin/python tests/vm-profiles.py
	$(ANSIBLE) ansible/playbooks/configure-recovery-controller.yml --syntax-check -i ansible/inventories/homelab.yml

controller-plan:
	@test "$(CONTROLLER_ALLOCATION_REVIEWED)" = yes || (echo "Review live VMID/IP, image, storage and network allocation first"; exit 1)
	@test -f "$(CONTROLLER_DIR)/terraform.tfvars" || (echo "Missing private reviewed profile"; exit 1)
	terraform -chdir=$(CONTROLLER_DIR) init -input=false -lockfile=readonly
	$(call INFISICAL_RUN,terraform -chdir=$(CONTROLLER_DIR) plan -input=false -out=controller.tfplan)

controller-apply:
	@test "$(CONTROLLER_APPLY_APPROVED)" = yes || (echo "Explicit approval of the exact saved plan required"; exit 1)
	@test -f "$(CONTROLLER_DIR)/controller.tfplan" || (echo "Missing reviewed saved plan"; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(CONTROLLER_DIR) apply -input=false controller.tfplan)

# Stage A has a separate local authority and no default live allocations.
STAGE_A_DIR := terraform/stacks/pve-lab-k3s
.PHONY: stage-a-check stage-a-plan stage-a-apply stage-a-start stage-a-configure
stage-a-check:
	$(VENV)/bin/python tests/vm-profiles.py
	$(VENV)/bin/python tests/stage-a.py
	$(ANSIBLE) ansible/playbooks/configure-k3s-lab.yml --syntax-check -i ansible/inventories/homelab.yml
	$(ANSIBLE) ansible/playbooks/start-k3s-lab.yml --syntax-check -i ansible/inventories/homelab.yml

stage-a-plan:
	@test "$(STAGE_A_ALLOCATION_REVIEWED)" = yes || (echo "Review allocation, stopped workstations, local storage and host capacity first"; exit 1)
	rm -f "$(STAGE_A_DIR)/stage-a.tfplan"
	@test -f "$(STAGE_A_DIR)/terraform.tfvars" || (echo "Missing private reviewed Stage A inputs"; exit 1)
	terraform -chdir=$(STAGE_A_DIR) init -input=false -lockfile=readonly
	$(call INFISICAL_RUN,terraform -chdir=$(STAGE_A_DIR) plan -input=false -out=stage-a.tfplan) || { rm -f "$(STAGE_A_DIR)/stage-a.tfplan"; exit 1; }
	shasum -a 256 "$(STAGE_A_DIR)/stage-a.tfplan"

stage-a-apply:
	@test "$(STAGE_A_APPLY_APPROVED)" = yes || (echo "Explicit exact-plan approval required"; exit 1)
	@test -n "$(STAGE_A_PLAN_SHA256)" || (echo "Supply the reviewed plan SHA256"; exit 1)
	@printf '%s  %s\n' '$(STAGE_A_PLAN_SHA256)' '$(STAGE_A_DIR)/stage-a.tfplan' | shasum -a 256 -c
	$(call INFISICAL_RUN,terraform -chdir=$(STAGE_A_DIR) apply -input=false stage-a.tfplan)
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

# PostgreSQL host bootstrap state stays local; apply only the reviewed saved plan.
TFSTATE_DIR := terraform/stacks/pve-core-tfstate
TFSTATE_SSH_PUBLIC_KEY_FILE ?= $(HOME)/.ssh/id_ed25519.pub

.PHONY: tfstate-plan tfstate-apply
tfstate-plan:
	@test -r "$(TFSTATE_SSH_PUBLIC_KEY_FILE)" || (echo "Missing controller public SSH key"; exit 1)
	rm -f "$(TFSTATE_DIR)/tfstate.tfplan"
	terraform -chdir=$(TFSTATE_DIR) fmt -check
	terraform -chdir=$(TFSTATE_DIR) init -input=false
	terraform -chdir=$(TFSTATE_DIR) validate
	$(call INFISICAL_RUN,env TF_VAR_management_ssh_public_key="$$(cat "$(TFSTATE_SSH_PUBLIC_KEY_FILE)")" terraform -chdir=$(TFSTATE_DIR) plan -input=false -out=tfstate.tfplan)

tfstate-apply:
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
	@test -r "$(GARAGE_SSH_PUBLIC_KEY_FILE)" || (echo "Missing controller public SSH key"; exit 1)
	terraform -chdir=$(GARAGE_DIR) fmt -check
	terraform -chdir=$(GARAGE_DIR) init -input=false
	terraform -chdir=$(GARAGE_DIR) validate
	$(call INFISICAL_RUN,env TF_VAR_management_ssh_public_key="$$(cat "$(GARAGE_SSH_PUBLIC_KEY_FILE)")" terraform -chdir=$(GARAGE_DIR) plan -input=false -out=garage.tfplan)

garage-apply:
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
	@test -f "$(RUNNER_DIR)/terraform.tfvars" || (echo "Create private $(RUNNER_DIR)/terraform.tfvars first"; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(RUNNER_DIR) import -input=false -var-file=terraform.tfvars proxmox_virtual_environment_container.forgejo_runner pve-compute/300)

runner-live-plan:
	@test -f "$(RUNNER_DIR)/terraform.tfvars" || (echo "Create private $(RUNNER_DIR)/terraform.tfvars first"; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(RUNNER_DIR) plan -input=false -var-file=terraform.tfvars)

runner-migration-plan:
	@test -f "$(MIGRATION_RUNNER_DIR)/terraform.tfvars" || (echo "Create private $(MIGRATION_RUNNER_DIR)/terraform.tfvars first"; exit 1)
	terraform -chdir=$(MIGRATION_RUNNER_DIR) fmt -check
	$(call INFISICAL_RUN,terraform -chdir=$(MIGRATION_RUNNER_DIR) init -input=false)
	$(call INFISICAL_RUN,terraform -chdir=$(MIGRATION_RUNNER_DIR) validate)
	$(call INFISICAL_RUN,terraform -chdir=$(MIGRATION_RUNNER_DIR) plan -input=false -var-file=terraform.tfvars)

runner-migration-apply:
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
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(WS_PLAYBOOK) --diff

workstations-plan:
	rm -f $(WS_PLAN)
	$(call INFISICAL_RUN,terraform -chdir=$(WS_DIR) fmt)
	$(call INFISICAL_RUN,terraform -chdir=$(WS_DIR) validate)
	$(call INFISICAL_RUN,terraform -chdir=$(WS_DIR) plan -out=$(WS_PLAN))

workstations-apply:
	@test -f $(WS_PLAN) || \
		(echo "No saved workstation plan. Run 'make workstations-plan' first."; exit 1)
	$(call INFISICAL_RUN,terraform -chdir=$(WS_DIR) apply -parallelism=1 $(WS_PLAN))
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(WS_PLAYBOOK) --diff
	rm -f $(WS_PLAN)

workstations-verify:
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
