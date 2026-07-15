# hetzner-server-runbook — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein Claude-Code-Skill, das Hetzner-Cloud-Server provisioniert, härtet und Docker-Compose-Apps darauf deployt — als ausführbares, schrittweise bestätigbares Runbook.

**Architecture:** Ein Skill-Verzeichnis mit kompakter `SKILL.md` (Trigger + Workflow-Übersicht) und sechs Referenzdateien (Progressive Disclosure). Keine Skripte — das Skill leitet Claude an, `hcloud`- und `ssh`-Befehle sichtbar und einzeln bestätigbar auszuführen.

**Tech Stack:** Markdown-Skill, hcloud CLI, Ubuntu 24.04 LTS, Docker + Compose v2, Caddy (Auto-TLS), ufw/fail2ban/unattended-upgrades, restic.

## Global Constraints

- Entwicklung in `~/Desktop/skills/hetzner-server-runbook/`, Installation per Symlink nach `~/.claude/skills/hetzner-server-runbook`.
- Alle Inhalte deutsch; Befehle, Config-Keys und Tool-Namen englisch.
- **Keine personenbezogenen Daten** in Skill-Dateien: keine echten Namen, Domains, IPs, Hostnamen, E-Mail-Adressen. Immer Platzhalter: `<SERVER_NAME>`, `<DOMAIN>`, `<SERVER_IP>`, `<SSH_KEY_NAME>`.
- `HCLOUD_TOKEN` nur aus der Umgebung; nie in Dateien oder Logs.
- Jede kostenpflichtige/destruktive Aktion im Skill-Text explizit als „Bestätigung erforderlich" markiert (Muster: Befehl zeigen → warten → ausführen).
- Verifikation je Task statt Unit-Tests: (a) Datei existiert und hat erwartete Abschnitte, (b) `grep -riE 'wilhelm|lenz|@gmail|@icloud' <datei>` liefert nichts, (c) Commit erst nach bestandener Verifikation.
- Commit-Messages: Conventional Commits (`feat:`, `docs:`), keine AI-Attribution.

---

### Task 1: Skill-Gerüst + SKILL.md

**Files:**
- Create: `hetzner-server-runbook/SKILL.md`
- Create: `hetzner-server-runbook/references/` (Verzeichnis)

**Interfaces:**
- Produces: SKILL.md verweist auf die sechs Referenzdateien aus Task 2–7 mit exakt diesen Namen: `provisionierung.md`, `haertung.md`, `docker-caddy.md`, `deployment.md`, `backups.md`, `troubleshooting.md`.

- [ ] **Step 1: SKILL.md schreiben**

````markdown
---
name: hetzner-server-runbook
description: Provisioniert Hetzner-Cloud-Server per hcloud CLI, härtet sie (SSH-Key-only, ufw, fail2ban, Auto-Updates) und deployt Docker-Compose-Anwendungen mit Caddy als Reverse Proxy (automatisches HTTPS). Enthält Runbooks für Backups (Snapshots + restic) und Server-Troubleshooting. Nutze dieses Skill, wenn der Nutzer sagt "setz einen neuen Server auf", "provisioniere einen Hetzner-Server", "deploye die App auf den Server", "härte den Server ab", "richte Backups ein", "der Server ist down" oder ähnliche Wünsche zu Hetzner, VPS-Setup, Linux-Server-Konfiguration oder Docker-Deployment äußert.
---

# Hetzner Server Runbook

Ausführbares Runbook: Claude führt die Schritte selbst aus (hcloud, ssh),
aber sichtbar und einzeln. **Nie mehrere Schritte stillschweigend bündeln.**

## Eiserne Regeln

1. `HCLOUD_TOKEN` kommt aus der Umgebung (`hcloud context` oder Env-Var).
   Token niemals anzeigen, loggen oder in Dateien schreiben.
2. **Bestätigung erforderlich** vor jeder Aktion, die Geld kostet oder
   destruktiv ist: Server/Volumes/Snapshots erstellen, löschen, resizen,
   DNS ändern. Muster: exakten Befehl zeigen → auf separates Ja warten →
   ausführen.
3. Secrets (DB-Passwörter, .env) nur auf dem Server, Dateirechte `600`,
   nie ins Git.
4. Vor destruktiven Server-Befehlen (`rm`, `docker compose down -v`,
   `ufw enable` bei aktiver SSH-Session): Konsequenz nennen, bestätigen
   lassen.

## Workflows

| Wunsch | Referenz |
|---|---|
| Neuen Server erstellen | `references/provisionierung.md` |
| Server absichern/härten | `references/haertung.md` |
| Docker + Reverse Proxy einrichten | `references/docker-caddy.md` |
| App deployen / Rollback | `references/deployment.md` |
| Backups einrichten / wiederherstellen | `references/backups.md` |
| Fehler diagnostizieren | `references/troubleshooting.md` |

**Kompletter Neuaufbau** = Provisionierung → Härtung → Docker/Caddy →
Deployment → Backups, in dieser Reihenfolge. Nach jedem Block kurz
verifizieren (steht im jeweiligen Dokument) und dem Nutzer den Stand melden.

## Vorbedingungen prüfen (immer zuerst)

```bash
hcloud version || echo "hcloud fehlt: brew install hcloud"
hcloud context active || echo "Kein Kontext: hcloud context create <name>"
ls ~/.ssh/id_ed25519.pub || echo "Kein SSH-Key: ssh-keygen -t ed25519"
```
````

- [ ] **Step 2: Verifikation**

```bash
python3 -c "
import re, pathlib
t = pathlib.Path('hetzner-server-runbook/SKILL.md').read_text()
fm = re.search(r'^---\n(.*?)\n---', t, re.S).group(1)
assert 'name: hetzner-server-runbook' in fm
assert len(fm) < 2000
for ref in ['provisionierung','haertung','docker-caddy','deployment','backups','troubleshooting']:
    assert f'references/{ref}.md' in t, ref
print('OK')
"
grep -riE 'wilhelm|lenz|@gmail|@icloud' hetzner-server-runbook/ && echo "FEHLER: persönliche Daten" || echo "sauber"
```
Expected: `OK` und `sauber`.

- [ ] **Step 3: Commit**

```bash
git add hetzner-server-runbook/SKILL.md
git commit -m "feat: hetzner-server-runbook Skill-Gerüst mit SKILL.md"
```

---

### Task 2: references/provisionierung.md

**Files:**
- Create: `hetzner-server-runbook/references/provisionierung.md`

**Interfaces:**
- Produces: Platzhalter-Konventionen `<SERVER_NAME>`, `<SSH_KEY_NAME>`, `<SERVER_IP>`, die alle späteren Referenzen weiterverwenden.

- [ ] **Step 1: Datei schreiben**

````markdown
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

Vorher zeigen: Typ, Standort, Image, ungefährer Monatspreis
(`hcloud server-type list` für aktuelle Typen; CX22 ≈ kleinster Allrounder).

```bash
hcloud server create \
  --name <SERVER_NAME> \
  --type cx22 \
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

→ Direkt weiter mit `haertung.md` — ein ungehärteter Server bleibt
keine Stunde unbeobachtet im Netz.

## Server löschen — ⚠️ DESTRUKTIV, Bestätigung erforderlich

```bash
hcloud server delete <SERVER_NAME>
```
````

- [ ] **Step 2: Verifikation**

```bash
grep -c "Bestätigung erforderlich" hetzner-server-runbook/references/provisionierung.md
grep -riE 'wilhelm|lenz|@gmail' hetzner-server-runbook/references/provisionierung.md || echo "sauber"
```
Expected: mindestens `2`, dann `sauber`.

- [ ] **Step 3: Commit**

```bash
git add hetzner-server-runbook/references/provisionierung.md
git commit -m "feat: Provisionierungs-Runbook (hcloud: Key, Firewall, Server)"
```

---

### Task 3: references/haertung.md

**Files:**
- Create: `hetzner-server-runbook/references/haertung.md`

**Interfaces:**
- Consumes: `<SERVER_IP>` aus provisionierung.md
- Produces: Deploy-User `deploy`, den docker-caddy.md und deployment.md voraussetzen.

- [ ] **Step 1: Datei schreiben**

````markdown
# Härtung: Ubuntu 24.04 Basis-Absicherung

Alle Befehle zunächst als `root@<SERVER_IP>` per ssh.

## 1. System aktualisieren

```bash
apt-get update && apt-get -y upgrade
```

## 2. Deploy-User anlegen (sudo, ohne Passwort-Login)

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deploy
chmod 440 /etc/sudoers.d/deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys
```

**Prüfen, bevor Root-Login abgeschaltet wird** (neue Terminal-Session!):

```bash
ssh deploy@<SERVER_IP> "sudo whoami"   # → root
```

## 3. SSH härten — ⚠️ erst nach erfolgreichem deploy-Login!

```bash
cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
X11Forwarding no
EOF
sshd -t && systemctl restart ssh
```

## 4. Firewall (ufw)

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose
```

## 5. fail2ban + automatische Security-Updates

```bash
apt-get install -y fail2ban unattended-upgrades
cat > /etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled = true
backend = systemd
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades
```

## 6. Verifikation

```bash
ssh root@<SERVER_IP> "echo geht-noch" # Erwartung: Permission denied
ssh deploy@<SERVER_IP> "sudo ufw status | head -3 && sudo fail2ban-client status sshd | head -5"
```
````

- [ ] **Step 2: Verifikation**

```bash
grep -q "PermitRootLogin no" hetzner-server-runbook/references/haertung.md && \
grep -q "erst nach erfolgreichem deploy-Login" hetzner-server-runbook/references/haertung.md && echo OK
grep -riE 'wilhelm|lenz|@gmail' hetzner-server-runbook/references/haertung.md || echo "sauber"
```
Expected: `OK`, `sauber`.

- [ ] **Step 3: Commit**

```bash
git add hetzner-server-runbook/references/haertung.md
git commit -m "feat: Härtungs-Runbook (deploy-User, SSH, ufw, fail2ban)"
```

---

### Task 4: references/docker-caddy.md

**Files:**
- Create: `hetzner-server-runbook/references/docker-caddy.md`

**Interfaces:**
- Consumes: User `deploy` aus haertung.md
- Produces: Docker-Netzwerk `web` und Verzeichnis `/srv/caddy/`, die deployment.md voraussetzt.

- [ ] **Step 1: Datei schreiben**

````markdown
# Docker + Caddy Reverse Proxy (Auto-HTTPS)

Als `deploy@<SERVER_IP>`.

## 1. Docker installieren (offizielles Apt-Repo)

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker deploy
# neu einloggen, dann:
docker run --rm hello-world
```

## 2. Gemeinsames Netz + Caddy

```bash
docker network create web
sudo mkdir -p /srv/caddy && sudo chown deploy:deploy /srv/caddy
```

`/srv/caddy/compose.yaml`:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks: [web]
volumes:
  caddy_data:
  caddy_config:
networks:
  web:
    external: true
```

`/srv/caddy/Caddyfile` (pro App ein Block; `<APP>` = Compose-Service-Name):

```
<DOMAIN> {
    reverse_proxy <APP>:8000
}
```

Ohne eigene Domain (Tests): `<SERVER_IP mit Bindestrichen>.sslip.io`,
z. B. `203-0-113-10.sslip.io` — löst automatisch auf die IP auf,
Caddy holt dafür ein echtes Zertifikat.

```bash
cd /srv/caddy && docker compose up -d
```

## 3. Verifikation

```bash
docker compose -f /srv/caddy/compose.yaml ps   # caddy: running
curl -sI http://localhost | head -1            # HTTP-Antwort von Caddy
```

Config-Änderungen laden: `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`
````

- [ ] **Step 2: Verifikation**

```bash
grep -q "docker network create web" hetzner-server-runbook/references/docker-caddy.md && \
grep -q "sslip.io" hetzner-server-runbook/references/docker-caddy.md && echo OK
grep -riE 'wilhelm|lenz|@gmail' hetzner-server-runbook/references/docker-caddy.md || echo "sauber"
```
Expected: `OK`, `sauber`.

- [ ] **Step 3: Commit**

```bash
git add hetzner-server-runbook/references/docker-caddy.md
git commit -m "feat: Docker+Caddy-Runbook (Apt-Repo, web-Netz, Auto-TLS)"
```

---

### Task 5: references/deployment.md

**Files:**
- Create: `hetzner-server-runbook/references/deployment.md`

**Interfaces:**
- Consumes: Netz `web`, `/srv/caddy/Caddyfile`, User `deploy`
- Produces: App-Layout `/srv/apps/<APP>/` mit `.env` (`IMAGE_TAG`), auf das backups.md und troubleshooting.md verweisen.

- [ ] **Step 1: Datei schreiben**

````markdown
# Deployment: Docker-Compose-App auf den Server bringen

## App-Layout auf dem Server

```
/srv/apps/<APP>/
├── compose.yaml
└── .env          # Secrets + IMAGE_TAG, chmod 600, NIE ins Git
```

Beispiel `compose.yaml` (FastAPI + PostgreSQL):

```yaml
services:
  app:
    image: ghcr.io/<GITHUB_USER>/<APP>:${IMAGE_TAG:-latest}
    restart: unless-stopped
    env_file: .env
    depends_on: [db]
    networks: [web, default]
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - db_data:/var/lib/postgresql/data
volumes:
  db_data:
networks:
  web:
    external: true
```

Wichtig: Nur `app` hängt im `web`-Netz (für Caddy erreichbar),
`db` bleibt intern. Keine `ports:` am App-Container — Caddy ist der
einzige Eingang.

## Deploy-Ablauf

```bash
ssh deploy@<SERVER_IP>
cd /srv/apps/<APP>
# 1. Aktuellen Stand für Rollback merken:
grep IMAGE_TAG .env   # alten Tag notieren
# 2. Neuen Tag setzen (oder git pull bei Build auf dem Server):
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=<NEUER_TAG>/' .env
docker compose pull
docker compose up -d
# 3. Health-Check:
docker compose ps
docker compose logs --tail 30 app
curl -fsS https://<DOMAIN>/health || echo "FEHLER: App antwortet nicht"
```

## Rollback — sofort, ohne Diskussion

```bash
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=<ALTER_TAG>/' .env
docker compose up -d
curl -fsS https://<DOMAIN>/health
```

Deshalb: **immer mit Versions-Tags deployen, nie nur `latest`** —
`latest` kann man nicht zurückrollen.

## Caddy an neue App anbinden

Block in `/srv/caddy/Caddyfile` ergänzen, dann:

```bash
cd /srv/caddy && docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```
````

- [ ] **Step 2: Verifikation**

```bash
grep -q "Rollback" hetzner-server-runbook/references/deployment.md && \
grep -q "IMAGE_TAG" hetzner-server-runbook/references/deployment.md && \
grep -q "chmod 600" hetzner-server-runbook/references/deployment.md && echo OK
grep -riE 'wilhelm|lenz|@gmail' hetzner-server-runbook/references/deployment.md || echo "sauber"
```
Expected: `OK`, `sauber`.

- [ ] **Step 3: Commit**

```bash
git add hetzner-server-runbook/references/deployment.md
git commit -m "feat: Deployment-Runbook (Compose-Layout, Tags, Rollback)"
```

---

### Task 6: references/backups.md

**Files:**
- Create: `hetzner-server-runbook/references/backups.md`

**Interfaces:**
- Consumes: App-Layout `/srv/apps/<APP>/` aus deployment.md

- [ ] **Step 1: Datei schreiben**

````markdown
# Backups: zwei Ebenen

## Ebene 1: Hetzner-Backups (ganzer Server) — ⚠️ KOSTET (+20 % Serverpreis)

```bash
hcloud server enable-backup <SERVER_NAME>   # 7 rotierende Auto-Backups
```

Alternativ manueller Snapshot vor riskanten Änderungen (kostet pro GB):

```bash
hcloud server create-image --type snapshot --description "vor-upgrade" <SERVER_NAME>
```

## Ebene 2: restic (Daten granular, verschlüsselt)

Ziel z. B. Hetzner Storage Box (`<STORAGEBOX_USER>@<STORAGEBOX_HOST>` via sftp).

```bash
sudo apt-get install -y restic
export RESTIC_REPOSITORY="sftp:<STORAGEBOX_USER>@<STORAGEBOX_HOST>:/backups/<SERVER_NAME>"
export RESTIC_PASSWORD_FILE=/home/deploy/.restic-pw   # chmod 600!
restic init
```

### PostgreSQL sichern (Dump, nicht Volume-Kopie!)

```bash
cd /srv/apps/<APP>
set -a; source .env; set +a   # POSTGRES_* aus der App-.env laden
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > /srv/backups/<APP>-$(date +%F).sql.gz
restic backup /srv/backups /srv/apps
```

### Täglich automatisch (systemd-Timer statt cron)

`/etc/systemd/system/backup.service`:

```ini
[Unit]
Description=Restic-Backup

[Service]
Type=oneshot
User=deploy
EnvironmentFile=/home/deploy/.restic-env
ExecStart=/usr/local/bin/backup.sh
```

`/etc/systemd/system/backup.timer`:

```ini
[Unit]
Description=Tägliches Restic-Backup

[Timer]
OnCalendar=daily
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
```

`/usr/local/bin/backup.sh` (chmod 755) enthält die Dump- und
restic-Befehle von oben; `/home/deploy/.restic-env` (chmod 600) die
Variablen `RESTIC_REPOSITORY` und `RESTIC_PASSWORD_FILE`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now backup.timer
systemctl list-timers backup.timer
```

## Restore-Test — ein Backup ohne Restore-Test ist keins

```bash
restic snapshots
restic restore latest --target /tmp/restore-test --include /srv/backups
gunzip -t /tmp/restore-test/srv/backups/<APP>-*.sql.gz && echo "Dump intakt"
```

Vierteljährlich: Dump in frische Postgres-Instanz einspielen und
Stichprobe abfragen.
````

- [ ] **Step 2: Verifikation**

```bash
grep -q "pg_dump" hetzner-server-runbook/references/backups.md && \
grep -q "Restore-Test" hetzner-server-runbook/references/backups.md && echo OK
grep -riE 'wilhelm|lenz|@gmail' hetzner-server-runbook/references/backups.md || echo "sauber"
```
Expected: `OK`, `sauber`.

- [ ] **Step 3: Commit**

```bash
git add hetzner-server-runbook/references/backups.md
git commit -m "feat: Backup-Runbook (Hetzner-Backups, restic, Restore-Test)"
```

---

### Task 7: references/troubleshooting.md

**Files:**
- Create: `hetzner-server-runbook/references/troubleshooting.md`

- [ ] **Step 1: Datei schreiben**

````markdown
# Troubleshooting: Diagnose-Reihenfolge

Von außen nach innen — nicht raten, messen. Befehle sind read-only,
außer wo markiert.

## 1. Ist es DNS/Netz?

```bash
dig +short <DOMAIN>          # zeigt die erwartete <SERVER_IP>?
ping -c 3 <SERVER_IP>
hcloud server describe <SERVER_NAME> | grep Status
```

## 2. Kommt man bis Caddy?

```bash
curl -svo /dev/null https://<DOMAIN> 2>&1 | grep -E "HTTP|SSL|certificate"
ssh deploy@<SERVER_IP> "sudo ss -tlnp | grep -E ':80|:443'"
ssh deploy@<SERVER_IP> "sudo ufw status"
```

Zertifikatsfehler → Caddy-Logs: `docker compose -f /srv/caddy/compose.yaml logs --tail 50 caddy`

## 3. Läuft der Container?

```bash
cd /srv/apps/<APP>
docker compose ps            # State: running? restarting = Crash-Loop!
docker compose logs --tail 100 app
docker compose exec app env | grep -v PASSWORD   # Config da?
```

## 4. Ressourcen?

```bash
df -h /                      # Disk voll ist Ursache Nr. 1
free -h
docker system df             # alte Images fressen Disk
sudo journalctl -p err --since "1 hour ago" --no-pager | tail -20
```

Disk voll → Aufräumen (⚠️ Bestätigung): `docker system prune -af --volumes` löscht
auch ungenutzte Volumes — vorher `docker volume ls` prüfen!

## 5. Datenbank?

```bash
docker compose exec db pg_isready
docker compose logs --tail 50 db
```

## Eskalationsregel

Nach 2–3 erfolglosen Hypothesen: Stand zusammenfassen, gesammelte
Fakten zeigen, nicht weiter raten. Notausgang: letztes Backup +
frischer Server ist oft schneller als eine korrupte Kiste zu retten.
````

- [ ] **Step 2: Verifikation**

```bash
grep -q "df -h" hetzner-server-runbook/references/troubleshooting.md && \
grep -q "Eskalationsregel" hetzner-server-runbook/references/troubleshooting.md && echo OK
grep -riE 'wilhelm|lenz|@gmail' hetzner-server-runbook/references/troubleshooting.md || echo "sauber"
```
Expected: `OK`, `sauber`.

- [ ] **Step 3: Commit**

```bash
git add hetzner-server-runbook/references/troubleshooting.md
git commit -m "feat: Troubleshooting-Runbook (Diagnose von außen nach innen)"
```

---

### Task 8: Gesamt-Review + Installation

**Files:**
- Create: Symlink `~/.claude/skills/hetzner-server-runbook` → `~/Desktop/skills/hetzner-server-runbook`

- [ ] **Step 1: Vollständigkeits-Check**

```bash
python3 -c "
import pathlib
base = pathlib.Path('hetzner-server-runbook')
refs = ['provisionierung','haertung','docker-caddy','deployment','backups','troubleshooting']
assert (base/'SKILL.md').exists()
for r in refs:
    p = base/f'references/{r}.md'
    assert p.exists() and p.stat().st_size > 500, r
print('alle Dateien da')
"
grep -riE 'wilhelm|lenz|@gmail|@icloud|192\.168|10\.0\.' hetzner-server-runbook/ && echo "FEHLER" || echo "sauber"
```
Expected: `alle Dateien da`, `sauber`.

- [ ] **Step 2: Installation per Symlink**

```bash
ln -s ~/Desktop/skills/hetzner-server-runbook ~/.claude/skills/hetzner-server-runbook
ls -la ~/.claude/skills/ | grep hetzner
```

- [ ] **Step 3: Trigger-Test** — in neuer Session prüfen, dass „setz mir einen neuen Hetzner-Server auf" das Skill lädt.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: hetzner-server-runbook fertiggestellt und installiert"
```

---

### Task 9: E2E-Verifikation am echten Hetzner-Account

**⚠️ Jeder kostenpflichtige Schritt nur nach separater Bestätigung des Operators.**

- [ ] **Step 1:** Per Skill (neue Session): CX22-Testserver provisionieren + härten (Task-2/3-Runbooks live)
- [ ] **Step 2:** Docker + Caddy einrichten, Test-App deployen (Compose: `traefik/whoami` als App-Ersatz + Postgres), Domain via sslip.io
- [ ] **Step 3:** `curl -fsS https://<IP-mit-Bindestrichen>.sslip.io` → HTTP 200 mit gültigem Zertifikat
- [ ] **Step 4:** Rollback-Ablauf einmal durchspielen (IMAGE_TAG wechseln und zurück)
- [ ] **Step 5:** Server löschen (Bestätigung!), Kosten-Check: `hcloud server list` leer
- [ ] **Step 6:** Erkenntnisse aus dem Live-Test zurück in die Referenzdateien einarbeiten, committen
