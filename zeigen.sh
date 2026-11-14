#!/bin/bash
# Show the operator document again after the Cloud Shell session was lost (Key Vault keeps it):
#   curl -fsSL https://raw.githubusercontent.com/jetweasel/bus-hauptschluessel/main/zeigen.sh | bash
set -euo pipefail
R=https://raw.githubusercontent.com/jetweasel/bus-hauptschluessel/main
W=$(mktemp -d); cd "$W"; trap 'rm -rf "$W"' EXIT
curl -fsSLO "$R/mainkey.py"
for V in $(az keyvault list -g jetweasel-schluessel --query "[].name" -o tsv); do
  if az keyvault secret show --vault-name "$V" -n bus-betreiberdokument --query value -o tsv > op-neu.jwt 2>/dev/null; then
    echo "Key Vault $V:"; python3 mainkey.py short op-neu.jwt; echo
  fi
done
