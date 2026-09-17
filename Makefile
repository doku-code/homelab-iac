SHELL := /bin/bash

# ─────────────────────────────────────────────
# Controller
# ─────────────────────────────────────────────

VENV := .venv
ANSIBLE := $(VENV)/bin/ansible-playbook

.PHONY: \
	setup-controller \
	workstations-check \
	workstations-bootstrap \
	workstations-plan \
	workstations-apply \
	workstations-verify \
	deploy-monitoring

setup-controller:
	python3 -m venv --clear $(VENV)
	$(VENV)/bin/python -m pip install -r requirements-controller.txt
	$(VENV)/bin/ansible-galaxy collection install -r collections/requirements.yml


# ─────────────────────────────────────────────
# Workstations
# ─────────────────────────────────────────────

WS_DIR := terraform/stacks/pve-lab-workstations
WS_PLAN := /tmp/pve-lab-workstations.tfplan
WS_PLAYBOOK := ansible/playbooks/configure-workstation-host.yml

workstations-check:
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(WS_PLAYBOOK) --check --diff

workstations-bootstrap:
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(WS_PLAYBOOK) --diff

workstations-plan:
	rm -f $(WS_PLAN)
	infisical run --env=dev -- \
		terraform -chdir=$(WS_DIR) fmt
	infisical run --env=dev -- \
		terraform -chdir=$(WS_DIR) validate
	infisical run --env=dev -- \
		terraform -chdir=$(WS_DIR) plan \
		-out=$(WS_PLAN)

workstations-apply:
	@test -f $(WS_PLAN) || \
		(echo "No saved workstation plan. Run 'make workstations-plan' first."; exit 1)
	infisical run --env=dev -- \
		terraform -chdir=$(WS_DIR) apply \
		-parallelism=1 $(WS_PLAN)
	@if [ ! -x "$(ANSIBLE)" ]; then $(MAKE) setup-controller; fi
	$(ANSIBLE) $(WS_PLAYBOOK) --diff
	rm -f $(WS_PLAN)

workstations-verify:
	infisical run --env=dev -- \
		terraform -chdir=$(WS_DIR) plan
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
