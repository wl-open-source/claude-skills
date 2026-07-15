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
docker compose exec app env | grep -viE 'password|secret|token|_url'   # Config da (ohne Secrets)?
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
