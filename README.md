# bus-hauptschluessel

Erzeugt den Hauptschlüssel (Betreiber-Schlüssel) des jetweasel-Bus (NATS) beim Owner und unterschreibt damit das Betreiber-Dokument. Nötig ist nur Python 3, keine Pakete und kein Netz. Quelle: `tools/mainkey.py` in jw-groups (T-0330).

- In der Azure Cloud Shell genügt eine Zeile: `curl -fsSL https://raw.githubusercontent.com/jetweasel/bus-hauptschluessel/main/run.sh | bash`. Sie erzeugt den Schlüssel, legt ihn in einem neuen Key Vault ab, liest ihn zur Kontrolle zurück und gibt erst dann das neue Dokument aus.
- Ist die Cloud Shell zwischendurch abgebrochen, zeigt `curl -fsSL https://raw.githubusercontent.com/jetweasel/bus-hauptschluessel/main/zeigen.sh | bash` das gesicherte Dokument noch einmal.
- `mainkey.py new op-prod-aktuell.jwt > op-neu.jwt`: neuer Schlüssel in `jetweasel-bus-hauptschluessel.nk`. Das neue Dokument vertraut demselben Signierschlüssel und demselben Systemkonto, deshalb bleiben alle Zugänge gültig.
- `mainkey.py sign <op.jwt> <schluessel.nk> --signing-key O…`: einen Signierschlüssel hinzufügen. Mit `--replace` ersetzt er die bisherigen.

`op-prod-aktuell.jwt` ist öffentlich und enthält nur öffentliche Schlüssel. Die `.nk`-Datei ist geheim. Sie gehört in den Key Vault des Owners, nie in dieses Repo und nie auf einen Server.
