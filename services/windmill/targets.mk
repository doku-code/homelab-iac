WINDMILL_DIR := terraform/stacks/pve-core-windmill
.PHONY: windmill-plan windmill-apply windmill-configure windmill-address windmill-access
windmill-plan:
	$(call LEGACY_ENDPOINT_GUARD,$(WINDMILL_DIR))
	terraform -chdir=$(WINDMILL_DIR) init -input=false -lockfile=readonly
	terraform -chdir=$(WINDMILL_DIR) validate
	$(VENV)/bin/python scripts/windmill-plan.py plan

windmill-apply:
	$(call LEGACY_ENDPOINT_GUARD,$(WINDMILL_DIR))
	$(VENV)/bin/python scripts/windmill-plan.py apply

windmill-configure:
	@test "$(WINDMILL_CONFIGURE_APPROVED)" = yes || (echo "Approve convergence of the dedicated CT"; exit 1)
	WINDMILL_CONFIGURE_APPROVED=yes bash scripts/windmill-configure.sh

windmill-address:
	@bash scripts/windmill-configure.sh address

windmill-access:
	@bash scripts/windmill-configure.sh access
