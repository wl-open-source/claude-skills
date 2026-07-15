# Provisionierung: neuer Hetzner-Cloud-Server

## 1. SSH-Key bei Hetzner hinterlegen (einmalig, kostenlos)

```bash
hcloud ssh-key create --name <SSH_KEY_NAME> \
  --public-key-from-file ~/.ssh/id_ed25519.pub
hcloud ssh-key list
```

## 2. Cloud-Firewall anlegen (einmalig, kostenlos)

```bash
hcloud firewall create --name base-fw
for rule in "22" "80" "443"; do
  hcloud firewall add-rule base-fw --direction in --protocol tcp \
    --port $rule --source-ips 0.0.0.0/0 --source-ips ::/0
done
hcloud firewall describe base-fw
```

## 3. Server erstellen — ⚠️ KOSTET GELD, Bestätigung erforderlich

Vorher zeigen: Typ, Standort, Image, ungefährer Monatspreis.
**`hcloud server-type list` ist maßgeblich** — Typnamen ändern sich: die alte
`cx`-Linie (`cx22` etc.) existiert nicht mehr. Kleinster x86-Allrounder in nbg1
ist aktuell `cx23` (2 vCPU, 4 GB, ~3,79 €/Mo); günstige ARM-Alternative: `cax11`.

```bash
hcloud server create \
  --name <SERVER_NAME> \
  --type cx23 \
  --image ubuntu-24.04 \
  --location nbg1 \
  --ssh-key <SSH_KEY_NAME> \
  --firewall base-fw
```

IP notieren:

```bash
hcloud server ip <SERVER_NAME>   # → <SERVER_IP>
```

## 4. Verifikation

```bash
hcloud server describe <SERVER_NAME> | grep -E "Status|IP"
ssh -o StrictHostKeyChecking=accept-new root@<SERVER_IP> "lsb_release -a && uptime"
```

Erwartung: Status `running`, Ubuntu 24.04, Login ohne Passwortabfrage.

> ⚠️ Blockt die lokale Permission-Baseline `Bash(ssh *)` (deny), scheitern alle
> Server-Schritte — deny schlägt jedes allow. Dann die Regel für die Dauer des
> Setups lockern oder die ssh-Befehle manuell (`!`-Prefix) ausführen.

→ Direkt weiter mit `haertung.md` — ein ungehärteter Server bleibt
keine Stunde unbeobachtet im Netz.

## Server löschen — ⚠️ DESTRUKTIV, Bestätigung erforderlich

```bash
hcloud server delete <SERVER_NAME>
```
