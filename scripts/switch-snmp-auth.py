#!/usr/bin/env python3
"""Prints the snmp_exporter sign-in for the switch (its `auths` section) from the environment, as JSON, which is
also YAML. `make observability-deploy` pipes it into the Kubernetes Secret switch-snmp; nothing is written to
disk or shown. Values come from the secret store, path /switch."""
import json
import os
import sys

NAMES = ("SWITCH_SNMP_USERNAME", "SWITCH_SNMP_AUTH_PASSWORD", "SWITCH_SNMP_PRIVACY_PASSWORD")
missing = [name for name in NAMES if not os.environ.get(name)]
if missing:
    sys.exit(f"switch-snmp-auth: set {', '.join(missing)} in the environment (store path /switch)")
auth_protocol = os.environ.get("SWITCH_SNMP_AUTH_PROTOCOL", "SHA")
privacy_protocol = os.environ.get("SWITCH_SNMP_PRIVACY_PROTOCOL", "DES")
if auth_protocol not in ("MD5", "SHA") or privacy_protocol not in ("DES", "AES"):
    sys.exit("switch-snmp-auth: SWITCH_SNMP_AUTH_PROTOCOL is MD5 or SHA, SWITCH_SNMP_PRIVACY_PROTOCOL is DES or AES")
print(json.dumps({"auths": {"switch_v3": {
    "version": 3, "security_level": "authPriv", "username": os.environ["SWITCH_SNMP_USERNAME"],
    "auth_protocol": auth_protocol, "password": os.environ["SWITCH_SNMP_AUTH_PASSWORD"],
    "priv_protocol": privacy_protocol, "priv_password": os.environ["SWITCH_SNMP_PRIVACY_PASSWORD"]}}}))
