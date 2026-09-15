WS_DIR := terraform/stacks/pve-lab-workstations
WS_PLAN := /tmp/pve-lab-workstations.tfplan
WS_PLAYBOOK := ansible/playbooks/configure-workstation-host.yml

.PHONY: \
	workstations-check \
	workstations-bootstrap \
	workstations-plan \
	workstations-apply \
	workstations-verify

workstations-check:
	ansible-playbook $(WS_PLAYBOOK) --check --diff

workstations-bootstrap:
	ansible-playbook $(WS_PLAYBOOK) --diff

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
	ansible-playbook $(WS_PLAYBOOK) --diff
	rm -f $(WS_PLAN)

workstations-verify:
	infisical run --env=dev -- \
		terraform -chdir=$(WS_DIR) plan
	ansible-playbook $(WS_PLAYBOOK) --check --diff
