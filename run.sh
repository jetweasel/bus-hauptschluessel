#!/bin/bash
# One line in Azure Cloud Shell (Bash or PowerShell):
#   curl -fsSL https://raw.githubusercontent.com/jetweasel/bus-hauptschluessel/main/run.sh | bash
# Creates the main key, stores it in a new Key Vault of the signed-in account and prints the new operator
# document. The document is printed only after the key is stored and read back: otherwise nothing is usable.
set -euo pipefail
# Only in the Azure Cloud Shell: there the key goes straight into the owner's Key Vault, never onto a server
if ! command -v az >/dev/null || ! az account show -o none 2>/dev/null; then
  echo "Stopp: Diese Zeile gehört in die Azure Cloud Shell (portal.azure.com, Symbol >_ oben), nicht auf einen Server." >&2
  echo "Es wurde nichts erzeugt." >&2
  exit 1
fi
R=https://raw.githubusercontent.com/jetweasel/bus-hauptschluessel/main
W=$(mktemp -d); cd "$W"; trap 'rm -rf "$W"' EXIT
curl -fsSLO "$R/mainkey.py"; curl -fsSLO "$R/op-prod-aktuell.jwt"
python3 mainkey.py new op-prod-aktuell.jwt jetweasel-bus-hauptschluessel.nk > op-neu.jwt
G=jetweasel-schluessel; V=jw-bus-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')
echo "Key Vault $V wird angelegt ..."
# A fresh subscription has to enable Key Vault once (MissingSubscriptionRegistration); takes a minute or two
if [ "$(az provider show -n Microsoft.KeyVault --query registrationState -o tsv 2>/dev/null)" != "Registered" ]; then
  echo "Key Vault wird im Abo freigeschaltet (einmalig, ein bis zwei Minuten) ..."
  az provider register -n Microsoft.KeyVault --wait -o none
fi
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
az keyvault secret set --vault-name "$V" -n bus-betreiberdokument --file op-neu.jwt -o none
echo; echo "Hauptschlüssel gesichert: Key Vault $V, Geheimnis bus-hauptschluessel."
echo "Screenshot von diesem Block an Emil (oder die Zeile mit eyJ ganz unten):"; echo
python3 mainkey.py short op-neu.jwt; echo; cat op-neu.jwt
