#!/bin/bash
# One line in Azure Cloud Shell (Bash or PowerShell):
#   curl -fsSL https://raw.githubusercontent.com/jetweasel/bus-hauptschluessel/main/run.sh | bash
# Creates the main key, stores it in a new Key Vault of the signed-in account and prints the new operator
# document. The document is printed only after the key is stored and read back: otherwise nothing is usable.
set -euo pipefail
R=https://raw.githubusercontent.com/jetweasel/bus-hauptschluessel/main
W=$(mktemp -d); cd "$W"; trap 'rm -rf "$W"' EXIT
curl -fsSLO "$R/mainkey.py"; curl -fsSLO "$R/op-prod-aktuell.jwt"
python3 mainkey.py new op-prod-aktuell.jwt jetweasel-bus-hauptschluessel.nk > op-neu.jwt
G=jetweasel-schluessel; V=jw-bus-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')
echo "Key Vault $V wird angelegt ..."
# Some regions take no new customers (RequestDisallowedByAzure): try the next one
for L in germanywestcentral northeurope swedencentral francecentral westeurope; do
  az group show -n "$G" -o none 2>/dev/null || az group create -n "$G" -l "$L" -o none
  if az keyvault create -n "$V" -g "$G" -l "$L" --enable-rbac-authorization false -o none 2>err.txt; then OK=1; break; fi
  grep -q RequestDisallowedByAzure err.txt || { cat err.txt >&2; exit 1; }
  echo "Region $L nimmt nichts an, nächste ..."
done
[ -n "${OK:-}" ] || { echo "FEHLER: keine Region verfügbar" >&2; exit 1; }
az keyvault secret set --vault-name "$V" -n bus-hauptschluessel --file jetweasel-bus-hauptschluessel.nk -o none
[ "$(az keyvault secret show --vault-name "$V" -n bus-hauptschluessel --query value -o tsv | tr -d '\r\n')" = "$(tr -d '\n' < jetweasel-bus-hauptschluessel.nk)" ] \
  || { echo "FEHLER: Schlüssel im Key Vault stimmt nicht, Dokument verworfen" >&2; exit 1; }
echo; echo "Hauptschlüssel gesichert: Key Vault $V, Geheimnis bus-hauptschluessel."
echo "Diese Zeile in die Kachel einfügen:"; echo; cat op-neu.jwt
