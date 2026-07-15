---
name: projekt-bootstrap
description: >
  Erarbeitet für ein neues (Greenfield-)Software-, Web-, Mobile- oder
  KI-Projekt einen professionellen, live recherchierten
  Tech-Stack-Vorschlag (GitHub-Metriken, Community-Größe, Doku-Qualität,
  Aktualität) und erzeugt nach ausdrücklicher Bestätigung
  Context-Markdown-Dateien unter context/ sowie CLAUDE.md und AGENTS.md
  im Projektordner. Nutze dieses Skill, wenn der Nutzer ein neues Projekt
  starten will, einen Tech-Stack-Vorschlag braucht, "Context Engineering"
  oder Context-Dateien für ein frisches Projekt erwähnt, oder eine
  CLAUDE.md für ein neues Projekt erstellen lassen möchte.
---

# projekt-bootstrap

Vier Phasen, strikt in dieser Reihenfolge. Zwischen Phase 3 und 4 liegt
ein hartes Bestätigungs-Gate.

## Voraussetzungen prüfen (vor Phase 1)

1. Zielordner klären: In welchem Verzeichnis soll das Projekt entstehen?
   Falls unklar, fragen.
2. Kollisionscheck: Existiert dort bereits `context/`, `CLAUDE.md` oder
   `AGENTS.md`? Dann STOPP — Rückfrage, nichts überschreiben ohne
   separate Bestätigung. Ein nicht ganz leerer Ordner (z.B. `git init`,
   README) ist zulässig.
3. Empfehlung: `GITHUB_TOKEN` setzen, falls verfügbar — ohne Token ist
   das GitHub-Rate-Limit (60 Anfragen/h) für einen vollen
   Recherche-Lauf knapp.

## Phase 1 — Interview

Führe das Interview nach `references/interview-leitfaden.md`:
Multiple-Choice-Fragen (AskUserQuestion) plus Freitext für die
Projektidee. Ergebnis ist ein Projektprofil mit der Liste der
Recherche-Kategorien. Bei widersprüchlichen Angaben nachhaken, nicht
raten.

## Phase 2 — Recherche (automatisiert)

Starte pro Recherche-Kategorie einen parallelen Recherche-Agent
(Agent-Tool, ein Batch). Jeder Agent erhält wörtlich die Anweisung aus
`references/recherche-anleitung.md` plus seine Kategorie und das
Projektprofil. Die Agents nutzen WebSearch, `scripts/github_metrics.py`
und Context7 und bewerten nach `references/bewertungsrubrik.md`.

Wichtig bei der Agent-Übergabe: Ersetze den Platzhalter `<skill-pfad>`
in der Recherche-Anleitung durch den absoluten Pfad dieses
Skill-Ordners und gib den absoluten Pfad der Bewertungsrubrik
(`<skill-pfad>/references/bewertungsrubrik.md`) im Agent-Prompt mit —
die Agents laufen im Projektordner und können relative Skill-Pfade
nicht auflösen.

Fehlerverhalten:
- Kein Netz / Rate-Limit: auf Modellwissen degradieren und jeden
  betroffenen Kandidaten sichtbar als "Metriken nicht live verifiziert"
  markieren — im Vorschlag UND später in tech-stack.md. Kein stiller
  Fallback.
- Liefert ein Agent nichts Brauchbares, wird die Kategorie im Vorschlag
  als offen markiert, nicht mit einer schwachen Empfehlung gefüllt.

## Phase 3 — Vorschlag + Bestätigung (HARTES GATE)

Präsentiere eine Tabelle pro Kategorie: Empfehlung, Begründung,
Metriken, 1–2 Alternativen. Der Nutzer bestätigt den Stack als Ganzes
oder tauscht einzelne Positionen; bei Tausch die
Ökosystem-Verträglichkeit der Nachbarkategorien kurz prüfen und das
Ergebnis erneut vorlegen.

**Ohne ausdrückliche, separate Bestätigung wird KEINE Datei
geschrieben.** Eine kombinierte Aufgabenbeschreibung ("mach mir Stack
und Dateien") zählt nicht als Bestätigung des konkreten Vorschlags.

## Phase 4 — Generierung

1. Dateisprache aus dem Interview anwenden. Deutsch: Dateinamen wie in
   den Templates. Englisch: Dateinamen und Überschriften nach dieser
   verbindlichen Tabelle übersetzen:

   | Deutsch | Englisch |
   |---|---|
   | projekt-brief.md | project-brief.md |
   | architektur.md | architecture.md |
   | tech-stack.md | tech-stack.md |
   | coding-standards.md | coding-standards.md |
   | testing.md | testing.md |
   | automatisierung.md | automation.md |
   | sicherheit.md | security.md |
   | api-design.md | api-design.md |
   | datenmodell.md | data-model.md |
   | design-system.md | design-system.md |
   | deployment.md | deployment.md |
   | ki-integration.md | ai-integration.md |
2. `context/` anlegen und füllen aus `references/templates/`:
   - Immer: projekt-brief, architektur, tech-stack, coding-standards,
     testing, automatisierung, sicherheit
   - Bedingt (laut Projektprofil): api-design (Backend/API),
     datenmodell (Datenbank), design-system (UI), deployment (hosting
     ≠ lokal), ki-integration (KI-Funktionen)
3. `CLAUDE.md` und `AGENTS.md` aus den Templates erzeugen; beide
   referenzieren jede erzeugte context/-Datei mit einer
   Ein-Zeilen-Beschreibung (aus dem zweck-Kommentar des Templates).
4. Selbst-Check:
   - keine `{{PLATZHALTER}}` übrig (über alle erzeugten Dateien greppen)
   - alle Referenzen in CLAUDE.md/AGENTS.md zeigen auf existierende
     Dateien
   - tech-stack.md stimmt mit dem bestätigten Vorschlag überein
   - nur die für den Projekttyp vorgesehenen bedingten Dateien existieren
5. Ergebnis zusammenfassen: Liste der erzeugten Dateien + empfohlene
   nächste Schritte (z.B. Scaffolding mit dem bestätigten Stack).
