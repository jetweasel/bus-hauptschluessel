# bus-hauptschluessel

Erzeugt den Hauptschlüssel (Betreiber-Schlüssel) des jetweasel-Bus (NATS) beim Owner und unterschreibt damit das Betreiber-Dokument. Nötig ist nur Python 3, keine Pakete und kein Netz. Quelle: `tools/mainkey.py` in jw-groups (T-0330).

- `mainkey.py new op-prod-aktuell.jwt > op-neu.jwt`: neuer Schlüssel in `jetweasel-bus-hauptschluessel.nk`. Das neue Dokument vertraut demselben Signierschlüssel und demselben Systemkonto, deshalb bleiben alle Zugänge gültig.
- `mainkey.py sign <op.jwt> <schluessel.nk> --signing-key O…`: einen Signierschlüssel hinzufügen. Mit `--replace` ersetzt er die bisherigen.

`op-prod-aktuell.jwt` ist öffentlich und enthält nur öffentliche Schlüssel. Die `.nk`-Datei ist geheim. Sie gehört in den Key Vault des Owners, nie in dieses Repo und nie auf einen Server.
