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
