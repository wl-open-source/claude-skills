# Design: Skill `hetzner-server-runbook`

**Datum:** 2026-07-02
**Status:** Vom Operator freigegeben (Design-Gespräch)
**Ziel-Installationsort:** `~/.claude/skills/hetzner-server-runbook/`

## Zweck

Ein Claude-Code-Skill mit zwei Kernfähigkeiten:

1. **Server-Provisionierung:** Einen frischen Hetzner-Cloud-Server von null bis
   produktionsbereit aufsetzen — provisionieren, härten, Docker-Basis-Stack
   installieren.
2. **Deployment:** Docker-Compose-Anwendungen auf einen so aufgesetzten Server
   deployen, inkl. Rollback-Weg.

Das Skill ist ein **ausführbares Runbook**: Es führt die Schritte selbst per
`hcloud`-CLI und `ssh` aus, aber jeder Schritt bleibt sichtbar und einzeln
bestätigbar. Keine Blackbox-Skripte.

## Trigger (für die SKILL.md-Description)

Das Skill triggert bei Aussagen wie:

- „setz mir einen neuen Server auf" / „provisioniere einen Hetzner-Server"
- „deploye <App> auf den Server" / „bring <App> auf den Server"
- „härte den Server ab" / „mach den Server sicher"
- „richte Backups auf dem Server ein"
- „der Server/die App ist down, hilf mir beim Debuggen" (Troubleshooting-Teil)

## Dateistruktur

```
hetzner-server-runbook/
├── SKILL.md                 # Trigger-Beschreibung + Übersicht der Workflows,
│                            # verweist je Workflow auf die passende Referenz
└── references/
    ├── provisionierung.md   # hcloud CLI: Server erstellen, SSH-Key hinterlegen,
    │                        # Hetzner-Firewall, optional privates Netz
    ├── haertung.md          # SSH nur mit Key, Root-Login aus, ufw (22/80/443),
    │                        # fail2ban, unattended-upgrades, Deploy-User
    ├── docker-caddy.md      # Docker Engine + Compose v2 installieren,
    │                        # Caddy als Reverse Proxy mit automatischem TLS
    ├── deployment.md        # App-Deploy-Ablauf (git pull oder Registry-Image),
    │                        # compose up, Health-Check, Zero-Downtime-Basics,
    │                        # Rollback auf vorherige Version
    ├── backups.md           # Hetzner-Snapshots + restic für Volumes/Datenbanken,
    │                        # Restore-Test-Anleitung
    └── troubleshooting.md   # Diagnose-Checkliste: Ports, Container-Logs,
                             # TLS-Zertifikate, Disk/RAM, DNS
```

Progressive Disclosure: `SKILL.md` bleibt kompakt (Workflows + Verweise),
Details leben in den Referenzdateien und werden nur bei Bedarf gelesen.

## Festgelegte Defaults

| Entscheidung | Default | Begründung |
|---|---|---|
| Server-OS | Ubuntu 24.04 LTS | LTS-Support, beste Docker-/Doku-Lage |
| Reverse Proxy | Caddy | Auto-TLS, eine lesbare Config; Traefik erst bei vielen dynamischen Sites nötig (bewusst nicht im Scope, nachrüstbar) |
| Deploy-Einheit | Docker Compose | Passt zum bestehenden Workflow des Operators |
| SSH | Nur Key-Login, Root-Login deaktiviert, eigener Deploy-User | Standard-Härtung |
| Firewall | ufw, nur 22/80/443 offen (+ Hetzner-Cloud-Firewall) | Minimalprinzip |
| Updates | unattended-upgrades (Security) | Solo-Betrieb ohne Ops-Team |
| Backups | Hetzner-Snapshots (Server) + restic (Daten/Volumes) | Zwei Ebenen: Desaster + granular |

## Sicherheits- und Kostenregeln (im Skill festgeschrieben)

1. `HCLOUD_TOKEN` kommt ausschließlich aus der Umgebung — nie im Skill, nie in
   generierten Configs, nie in Logs.
2. Jede Aktion, die **Geld kostet oder destruktiv ist** (Server
   erstellen/löschen/resizen, Volumes, Snapshots löschen, DNS-Änderungen),
   folgt dem Muster: Vorschlag mit konkretem Befehl zeigen → auf separate
   Bestätigung warten → ausführen.
3. Keine personen- oder firmenspezifischen Daten im Skill (Namen, Domains,
   IPs, Hostnamen nur als Platzhalter) — das Skill soll teilbar und
   plattformneutral formuliert sein, analog zu `para-dateiorganisation`.
4. Generierte Secrets (DB-Passwörter etc.) landen in `.env`-Dateien auf dem
   Server mit Rechten `600`, nie im Git.

## Verifikation (nach dem Bau)

Realer End-to-End-Test mit dem vorhandenen Hetzner-Account des Operators:

1. Kleinsten Server (CX22) per Skill provisionieren und härten
2. Beispiel-App (Compose: Web-Container + PostgreSQL) deployen
3. HTTPS-Erreichbarkeit und Auto-TLS prüfen
4. Rollback einmal durchspielen
5. Server löschen (minutengenaue Abrechnung → Kosten: wenige Cent)

Jeder kostenpflichtige Schritt nur nach separater Bestätigung durch den
Operator.

## Nicht im Scope (bewusst, YAGNI)

- Traefik / Multi-Tenant-Shared-Hosting (später nachrüstbar, wenn die
  Arbeitgeber-Migration es konkret braucht)
- Hetzner Dedicated/Robot-Server (nur Cloud)
- CI/CD-Pipelines (GitHub Actions Deploy) — Kandidat für eine spätere
  Erweiterung, Grundlage dafür wird in `deployment.md` gelegt
- Kubernetes — für Solo-Betrieb Overkill

## Kontext: Gesamtportfolio

Dies ist Skill 1 von 3 aus dem beschlossenen iterativen Vorgehen:

1. `hetzner-server-runbook` (dieses Design)
2. `user-stories` — Nifty-Integration über die öffentliche Nifty-REST-API
3. `projekt-bootstrap` — Templates: FastAPI + NiceGUI + PostgreSQL + Docker
   sowie Next.js + Tailwind + shadcn/ui
