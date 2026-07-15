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

Einmalig anlegen:

```bash
sudo mkdir -p /srv/backups && sudo chown deploy:deploy /srv/backups
```

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
