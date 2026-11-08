#!/usr/bin/env bash
set -euo pipefail
stack=terraform/stacks/pve-core-windmill
id=$(terraform -chdir="$stack" output -raw ctid)
[[ $id =~ ^[0-9]+$ ]]
addr=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=yes root@192.168.0.11 \
  "test \"\$(hostname -s)\" = pve-core && test \"\$(pct exec $id -- hostname -s)\" = windmill && pct exec $id -- ip -j -4 addr show dev eth0" |
  python3 -c 'import ipaddress,json,sys
lan=ipaddress.ip_network("192.168.0.0/24")
ips=[a["local"] for dev in json.load(sys.stdin) for a in dev["addr_info"]
     if a["scope"]=="global" and ipaddress.ip_address(a["local"]) in lan]
if len(ips)!=1: sys.exit("Expected one LAN DHCP address on windmill eth0; retry after DHCP.")
print(ips[0])')
if [[ ${1:-configure} == address ]]; then
  printf '%s\n' "$addr"
  exit 0
fi
printf 'Windmill CT %s on pve-core: DHCP %s\n' "$id" "$addr"
trust=$(mktemp)
trap 'rm -f "$trust"' EXIT
# Authenticate the guest key through the already trusted hypervisor, not keyscan.
pub=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=yes root@192.168.0.11 \
  "test \"\$(hostname -s)\" = pve-core && test \"\$(pct exec $id -- hostname -s)\" = windmill && pct exec $id -- cat /etc/ssh/ssh_host_ed25519_key.pub")
[[ $pub == ssh-ed25519\ * ]]
printf '%s %s\n' "$addr" "$pub" > "$trust"
if [[ ${1:-configure} == access ]]; then
  ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$trust" \
    -o ExitOnForwardFailure=yes -N -L 127.0.0.1:18000:127.0.0.1:8000 root@"$addr"
  exit 0
fi
[[ ${1:-configure} == configure && ${WINDMILL_CONFIGURE_APPROVED:-} == yes ]]
: "${INFISICAL_CLIENT_ID:?Use the authenticated operator shell}"
: "${INFISICAL_CLIENT_SECRET:?Use the authenticated operator shell}"
ANSIBLE_HOST_KEY_CHECKING=True ANSIBLE_SSH_COMMON_ARGS="-o StrictHostKeyChecking=yes -o UserKnownHostsFile=$trust" \
  .venv/bin/ansible-playbook -i windmill, -u root -e "ansible_host=$addr" \
    ansible/playbooks/configure-windmill.yml
