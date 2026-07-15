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
