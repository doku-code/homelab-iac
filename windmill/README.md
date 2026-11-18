# Windmill scripts

Scripts and flows of the Windmill workspace `homelab`, kept in Git and published with `make windmill-push`
(ADR-005). The path of a file is its path in Windmill: `f/netbox/next_free.py` is the script `f/netbox/next_free`.

- Scripts read infrastructure data from NetBox (ADR-016) with the workspace variable `f/netbox/read_token`, a
  read-only token written by `make windmill-bootstrap`. No token or password belongs in a script.
- A script proposes; provisioning itself stays in the OpenTofu roots and the approval-gated Make targets.
