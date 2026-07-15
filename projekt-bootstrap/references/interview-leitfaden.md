# Interview-Leitfaden

Fragen per AskUserQuestion stellen, möglichst gebündelt (max. 4 Fragen
pro Aufruf). Freitextfrage zur Projektidee immer zuerst, als normale
Chat-Frage.

## Frage 0 (Freitext, immer zuerst)

"Beschreibe kurz, was das Produkt tun soll: Kernfunktionen,
Zielgruppe, Besonderheiten."

## Frage 1 — Projekttyp (Mehrfachauswahl)

Web-App | Website (statisch/Content) | Desktop-App | Mobile-App |
Full-Stack (Frontend + Backend) | KI-Projekt | CLI/Tool

## Frage 2 — Zielplattformen (Mehrfachauswahl, abhängig von Frage 1)

Desktop: macOS | Windows | Linux
Mobile: iOS | Android
Web: moderne Browser | auch Legacy-Support nötig

## Frage 3 — Nativ vs. Cross-Platform (nur Desktop/Mobile)

Nativ pro Plattform | Cross-Platform bevorzugt | Empfehlung überlassen

## Frage 4 — Rahmenbedingungen

- Bestehende Präferenzen (Sprache/Framework/Tools)? (Freitext-Option)
- Hosting: Cloud (Anbieter?) | eigener Server | lokal/Desktop only |
  noch offen
- Solo oder Team? Team-Erfahrung mit welchen Sprachen?

## Frage 5 — Dateisprache

Deutsch | Englisch (Default: Englisch)

## Widerspruchs-Check

Vor Abschluss prüfen, ob Antworten kollidieren (z.B. "nur iOS" als
Plattform, aber "muss im Browser laufen" in der Projektidee). Bei
Widerspruch: gezielt nachfragen, NICHT raten.

## Projektprofil (internes Ergebnisformat)

```yaml
projektidee: <Freitext-Zusammenfassung>
projekttyp: [web-app, ki-projekt, ...]
plattformen: [macos, ios, browser, ...]
cross_platform: ja | nein | offen
praeferenzen: <bestehende Vorgaben oder "keine">
hosting: <cloud-anbieter | eigener-server | lokal | offen>
team: <solo | team + Erfahrung>
dateisprache: de | en
```

## Ableitung: Profil → Recherche-Kategorien

| Kategorie | Wann aktiv |
|---|---|
| Programmiersprache | immer |
| Framework (App/Web/Backend) | immer außer reine Library. Bei CLI/Tool zählt das CLI-Framework (z.B. Argument-Parser) als diese Kategorie |
| Wichtige Libraries | immer |
| Datenbank + ORM | wenn server- oder schemabasierte Persistenz nötig (aus Projektidee ableiten; im Zweifel fragen). Rein lokale On-Device-Speicherung mit Plattform-Bordmitteln aktiviert die Kategorie NICHT |
| Testing | immer |
| Automatisierung / CI-CD | immer |
| Deployment / Hosting | wenn hosting ≠ lokal |
| KI-SDK / Provider | wenn projekttyp ki-projekt enthält oder Projektidee KI-Funktionen nennt |
| UI / Design-System-Basis | wenn projekttyp Web-App, Website, Desktop oder Mobile enthält |

## Ableitung: Profil → bedingte context/-Dateien

| Datei | Bedingung |
|---|---|
| api-design | Backend oder API Teil des Projekts |
| datenmodell | Kategorie "Datenbank + ORM" war aktiv |
| design-system | Kategorie "UI / Design-System-Basis" war aktiv |
| deployment | Kategorie "Deployment / Hosting" war aktiv |
| ki-integration | Kategorie "KI-SDK / Provider" war aktiv |
