# Design: projekt-bootstrap

**Datum:** 2026-07-03
**Status:** Entwurf zur Abnahme
**Skill-Ordner:** `projekt-bootstrap/`

## Zweck

Ein Skill, das für ein neues (Greenfield-)Software-, Web-, Mobile- oder
KI-Projekt einen professionellen Tech-Stack-Vorschlag erarbeitet und nach
ausdrücklicher Bestätigung durch den Nutzer projektspezifische
Context-Markdown-Dateien ("Context Engineering") unter `context/` sowie
passende Einstiegsdateien `CLAUDE.md` und `AGENTS.md` im Projektordner
erzeugt.

Der Stack-Vorschlag basiert auf Live-Recherche: aktueller Stand der
Software- und Webentwicklung, Community-Größe und -Beliebtheit,
Doku-Qualität sowie objektive GitHub-Metriken (Stars, Wartungsaktivität,
Release-Frequenz). Automatisierungs-Tooling (CI/CD, Linter/Formatter,
Pre-Commit-Hooks, Testautomatisierung) ist fester Bestandteil jeder
Empfehlung.

## Abgrenzung (bewusst NICHT im Umfang)

- Kein Scaffolding von Code, keine Installation von Dependencies — es
  entstehen ausschließlich Markdown-Dateien.
- Keine Analyse bestehender Codebasen (nur Greenfield). Ein nicht ganz
  leerer Ordner (z.B. `git init` + README) ist zulässig.
- Keine tool-spezifischen Dateien außer `CLAUDE.md` und `AGENTS.md`
  (keine `.cursorrules` o.ä.).

## Getroffene Entscheidungen

| # | Entscheidung | Begründung |
|---|---|---|
| 1 | Nur Greenfield | Klar abgegrenzter erster Wurf; Bestandsanalyse wäre ein eigenes Skill |
| 2 | Live-Recherche pro Lauf | Empfehlungen veralten sonst; Aktualität ist Kernanforderung |
| 3 | Automatisierung doppelt: Tooling in der Empfehlung + automatisierter Skill-Ablauf | Nutzerwunsch, per Empfehlung konkretisiert |
| 4 | `CLAUDE.md` + `AGENTS.md`, beide referenzieren dieselben tool-neutralen `context/`-Dateien | AGENTS.md ist der offene Standard für Cursor, Codex & Co.; keine Doppelpflege |
| 5 | Name `projekt-bootstrap` | Steht im Werkstatt-README bereits als geplantes Skill |
| 6 | Dateisprache wählbar (Deutsch/Englisch), Default Englisch | Context-Dateien werden oft mit internationalen Teams/Tools geteilt |
| 7 | Ansatz: Phasen-Workflow mit Template-Skeletten | Struktur/Konsistenz aus Templates, Inhalt/Aktualität aus Modell + Live-Recherche |

## Ablauf (4 Phasen)

### Phase 1 — Interview

Kompakte Befragung per Multiple-Choice plus Freitext für die Projektidee:

- Projekttyp (Mehrfachauswahl): Web-App, Website, Desktop
  (macOS/Windows/Linux), Mobile nativ (iOS/Android), Full-Stack,
  KI-Projekt, CLI/Tool
- Zielplattformen; nativ vs. cross-platform zulässig?
- Kernfunktionen und Besonderheiten (Freitext)
- Rahmenbedingungen: bestehende Sprach-/Tool-Präferenzen,
  Hosting-Vorstellungen, Solo oder Team
- Sprache der generierten Dateien (Deutsch/Englisch, Default Englisch)

Ergebnis: internes **Projektprofil**, das die Recherche-Kategorien
bestimmt (ein CLI-Tool bekommt z.B. keine UI-Framework-Kategorie).
Bei widersprüchlichem Profil (z.B. "nur iOS" + "muss im Browser laufen")
hakt das Interview nach, statt zu raten.

### Phase 2 — Recherche (automatisiert)

Pro Kategorie läuft ein paralleler Recherche-Agent mit fester Anleitung
aus `references/recherche-anleitung.md`. Kategorien je nach Profil:
Programmiersprache, Framework, wichtige Libraries, Datenbank/ORM,
Testing, Automatisierung/CI-CD, Deployment, ggf. KI-SDK/Provider.

Jeder Agent:

1. **WebSearch** — aktueller Stand der Technik, 2–3 Kandidaten je Kategorie
2. **`scripts/github_metrics.py`** — objektive Zahlen pro Kandidat:
   Stars, letzter Commit, Release-Datum/-Frequenz, Contributor-Näherung,
   Open-Issue-Verhältnis
3. **Context7** — existiert aktuelle, gepflegte Dokumentation?

Bewertung nach fester Rubrik (`references/bewertungsrubrik.md`):

| Kriterium | Gewicht |
|---|---|
| Aktualität / Wartung | 25 % |
| Community-Größe / Beliebtheit | 25 % |
| Doku-Qualität | 20 % |
| Robustheit / Reife | 20 % |
| Ökosystem-Fit zum Restprojekt | 10 % |

Die Rubrik enthält zusätzlich harte Schwellenwerte
(z.B. letzter Commit > 12 Monate = rot).

### Phase 3 — Vorschlag + Bestätigung

Übersichtliche Tabelle pro Kategorie: Empfehlung mit Begründung und
Metriken, dazu 1–2 Alternativen. Der Nutzer bestätigt den Stack als
Ganzes oder tauscht einzelne Positionen; bei Tausch wird die
Ökosystem-Verträglichkeit der Nachbarkategorien kurz geprüft.

**Harte Regel:** Ohne ausdrückliche, separate Bestätigung wird keine
Datei geschrieben (explicit-separate-permission-Muster).

### Phase 4 — Generierung

Im Projektordner entsteht:

```
<projekt>/
├── CLAUDE.md          # Einstieg Claude Code, referenziert context/*
├── AGENTS.md          # Einstieg andere Tools, referenziert context/*
└── context/
    ├── projekt-brief.md        # immer
    ├── architektur.md          # immer
    ├── tech-stack.md           # immer (bestätigter Stack, Versionen, Begründung, Metriken)
    ├── coding-standards.md     # immer
    ├── testing.md              # immer
    ├── automatisierung.md      # immer (CI/CD, Linter, Hooks, Release)
    ├── sicherheit.md           # immer
    ├── api-design.md           # bedingt: Backend/API
    ├── datenmodell.md          # bedingt: Datenbank
    ├── design-system.md        # bedingt: UI (Web-Frontend/Mobile/Desktop)
    ├── deployment.md           # bedingt: eigene Infrastruktur
    └── ki-integration.md       # bedingt: KI-Funktionen (Modelle, Provider, Evals, Kosten)
```

`CLAUDE.md` und `AGENTS.md` sind kompakt und referenzieren jede
`context/`-Datei mit einer Ein-Zeilen-Beschreibung, wann sie zu lesen
ist — kein Inhalt doppelt. Bei deutscher Dateisprache heißen die Dateien
wie oben; bei englischer Dateisprache englische Dateinamen
(`project-brief.md`, `architecture.md`, …).

**Selbst-Check nach der Generierung:**

- keine Template-Platzhalter übrig
- alle Referenzen in CLAUDE.md/AGENTS.md zeigen auf existierende Dateien
- Stack-Angaben in `tech-stack.md` stimmen mit dem bestätigten Vorschlag
  überein
- nur die für den Projekttyp vorgesehenen bedingten Dateien existieren

## Skill-Dateistruktur

```
projekt-bootstrap/
├── SKILL.md                        # Orchestrierung der 4 Phasen, Trigger-Beschreibung
├── references/
│   ├── interview-leitfaden.md      # Fragenkatalog + Ableitung Profil → Kategorien
│   ├── recherche-anleitung.md      # Feste Anweisung für die Recherche-Agents
│   ├── bewertungsrubrik.md         # Gewichtete Kriterien + Schwellenwerte
│   └── templates/
│       ├── CLAUDE.template.md
│       ├── AGENTS.template.md
│       ├── projekt-brief.template.md
│       ├── architektur.template.md
│       ├── tech-stack.template.md
│       ├── coding-standards.template.md
│       ├── testing.template.md
│       ├── automatisierung.template.md
│       ├── sicherheit.template.md
│       ├── api-design.template.md
│       ├── datenmodell.template.md
│       ├── design-system.template.md
│       ├── deployment.template.md
│       └── ki-integration.template.md
└── scripts/
    └── github_metrics.py
```

**Templates** sind Skelette mit Ausfüll-Anweisungen, keine fertigen
Texte: Die Abschnittsstruktur ist fix (Konsistenz), der Inhalt wird pro
Projekt vom Modell geschrieben (Flexibilität). Jedes Template beginnt
mit einem Kommentarblock "Zweck dieser Datei / wann ein Agent sie lesen
soll" — dieser Block liefert auch die Beschreibungszeile in
CLAUDE.md/AGENTS.md. Überschriften folgen der gewählten Dateisprache
(Templates auf Deutsch verfasst; bei Englisch übersetzt das Modell die
Struktur).

**`github_metrics.py`:** nimmt Repo-Slugs (`owner/repo …`) als
Argumente, liefert JSON. Nutzt `GITHUB_TOKEN` falls gesetzt, sonst
unauthentifiziert (Rate-Limit 60 Anfragen/h — reicht knapp für einen
typischen Lauf mit ~20–25 Repos; bei Limit-Fehler klare Meldung statt
stillem Weiterlaufen). Nur Python-Standardbibliothek, keine
Abhängigkeiten, plattformunabhängig, keine personenbezogenen Daten —
Skill bleibt teilbar.

## Fehlerbehandlung

| Fall | Verhalten |
|---|---|
| Kein Netz / GitHub-Rate-Limit | Degradation auf Modellwissen; betroffene Kandidaten sichtbar als "Metriken nicht live verifiziert" markiert — im Vorschlag und in `tech-stack.md`. Kein stiller Fallback. |
| `context/`, `CLAUDE.md` oder `AGENTS.md` existiert bereits | Abbruch mit Rückfrage; nichts wird ohne separate Bestätigung überschrieben |
| Projektordner nicht leer | Zulässig; nur bei Dateikollisionen wird gefragt |
| Widersprüchliches Projektprofil | Interview hakt nach, statt zu raten |
| Recherche-Agent liefert nichts Brauchbares | Kategorie wird im Vorschlag als offen markiert, nicht mit schwacher Empfehlung gefüllt |
| `GITHUB_TOKEN` fehlt | Kein Fehler; unauthentifiziert mit Hinweis auf niedrigeres Rate-Limit |

## Test-Strategie

Drei Probeläufe gegen fiktive Projektbriefs, je in einem frischen
Scratchpad-Ordner:

1. Full-Stack-Web-App (Backend + Frontend + DB)
2. Native iOS-App
3. KI-CLI-Tool

Geprüft wird jeweils: korrekte bedingte Dateiauswahl, keine
Platzhalter-Reste, funktionierende Referenzen in CLAUDE.md/AGENTS.md,
plausible und aktuelle Stack-Vorschläge, Bestätigungs-Gate greift.
Zusätzlich: isolierter Test von `github_metrics.py` gegen 2–3 bekannte
Repos (mit und ohne Token, Fehlerfall ungültiger Slug).

## Erfolgskriterien

- Ein Lauf von leerer Projektidee bis fertigem `context/`-Satz inkl.
  CLAUDE.md/AGENTS.md ohne manuelle Zwischenschritte außer Interview
  und Stack-Bestätigung.
- Empfehlungen sind mit Live-Metriken belegt oder ehrlich als
  unverifiziert markiert.
- Generierte Dateien sind projektspezifisch (kein generischer
  Boilerplate-Text) und untereinander widerspruchsfrei.
- Skill enthält keine personenbezogenen Daten und läuft auf
  macOS/Windows/Linux.
