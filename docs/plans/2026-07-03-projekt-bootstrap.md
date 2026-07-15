# projekt-bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein Claude-Code-Skill `projekt-bootstrap`, das für Greenfield-Projekte einen live recherchierten Tech-Stack-Vorschlag erarbeitet und nach Bestätigung `context/`-Markdown-Dateien plus `CLAUDE.md`/`AGENTS.md` generiert.

**Architecture:** Phasen-Workflow-Skill (Interview → Recherche → Bestätigung → Generierung). SKILL.md orchestriert; `references/` liefert Interview-Leitfaden, Bewertungsrubrik, Recherche-Anleitung und 14 Template-Skelette; `scripts/github_metrics.py` liefert objektive GitHub-Metriken. Spec: `docs/specs/2026-07-03-projekt-bootstrap-design.md`.

**Tech Stack:** Markdown (Skill-Dateien), Python 3 (nur Standardbibliothek, GitHub REST API v3), unittest für Script-Tests.

## Global Constraints

- Alle Skill-Dateien auf Deutsch; technische Begriffe bleiben Englisch.
- Keine personenbezogenen Daten, keine echten Domains/IPs/Namen — Skill bleibt teilbar (Werkstatt-Konvention).
- `github_metrics.py`: nur Python-Standardbibliothek, plattformunabhängig (macOS/Windows/Linux), nutzt `GITHUB_TOKEN` falls gesetzt.
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:` …), KEINE AI-Attribution (kein Co-Authored-By).
- Skill-Ordner: `projekt-bootstrap/` auf Repo-Root-Ebene (kebab-case).
- Harte Regel im Skill-Verhalten: keine Dateigenerierung ohne ausdrückliche, separate Bestätigung des Stack-Vorschlags.
- Template-Konvention: Jedes Template beginnt mit einem HTML-Kommentarblock `zweck / wann-lesen / anleitung`; Platzhalter als `{{PLATZHALTER}}` in doppelten geschweiften Klammern.

---

### Task 1: Skill-Gerüst + SKILL.md

**Files:**
- Create: `projekt-bootstrap/SKILL.md`

**Interfaces:**
- Produces: SKILL.md verweist auf `references/interview-leitfaden.md`, `references/recherche-anleitung.md`, `references/bewertungsrubrik.md`, `references/templates/*.template.md`, `scripts/github_metrics.py` — exakt diese Pfade müssen die späteren Tasks liefern.

- [ ] **Step 1: SKILL.md schreiben**

Vollständiger Inhalt von `projekt-bootstrap/SKILL.md`:

````markdown
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

1. Dateisprache aus dem Interview anwenden (Deutsch: Dateinamen wie in
   den Templates; Englisch: Dateinamen und Überschriften übersetzen,
   z.B. `projekt-brief.md` → `project-brief.md`,
   `architektur.md` → `architecture.md`).
2. `context/` anlegen und füllen aus `references/templates/`:
   - Immer: projekt-brief, architektur, tech-stack, coding-standards,
     testing, automatisierung, sicherheit
   - Bedingt (laut Projektprofil): api-design (Backend/API),
     datenmodell (Datenbank), design-system (UI), deployment (eigene
     Infrastruktur), ki-integration (KI-Funktionen)
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
````

- [ ] **Step 2: Frontmatter-Validierung**

Run: `head -15 projekt-bootstrap/SKILL.md`
Expected: YAML-Frontmatter mit `name: projekt-bootstrap` und mehrzeiliger `description`, danach Beginn des Bodys.

- [ ] **Step 3: Commit**

```bash
git add projekt-bootstrap/SKILL.md
git commit -m "feat: projekt-bootstrap Skill-Gerüst mit SKILL.md"
```

---

### Task 2: scripts/github_metrics.py (TDD)

**Files:**
- Create: `projekt-bootstrap/scripts/github_metrics.py`
- Test: `projekt-bootstrap/scripts/test_github_metrics.py`

**Interfaces:**
- Produces: CLI `python3 github_metrics.py owner/repo [owner/repo …]` → JSON auf stdout: `{"owner/repo": {"stars": int, "last_commit": str|null, "archived": bool, "open_issues": int, "issues_per_1k_stars": float|null, "releases_last_year": int, "last_release": str|null, "contributors_approx": int}}`; Fehler pro Repo als `{"error": "…"}`; Exit-Codes: 0 = ok, 1 = Usage-Fehler, 2 = Rate-Limit-Abbruch. Wird von `references/recherche-anleitung.md` (Task 5) genau so referenziert.

- [ ] **Step 1: Failing Tests schreiben**

Vollständiger Inhalt von `projekt-bootstrap/scripts/test_github_metrics.py`:

```python
"""Tests für github_metrics.py — offline, alle HTTP-Aufrufe gemockt."""
import json
import unittest
from unittest import mock

import github_metrics


REPO_RESPONSE = {
    "stargazers_count": 2000,
    "pushed_at": "2026-06-01T12:00:00Z",
    "archived": False,
    "open_issues_count": 50,
}
RELEASES_RESPONSE = [
    {"published_at": "2026-05-01T00:00:00Z"},
    {"published_at": "2024-01-01T00:00:00Z"},
]


def fake_get(url):
    if url.endswith("/repos/acme/tool"):
        return REPO_RESPONSE, {}
    if "/releases?" in url:
        return RELEASES_RESPONSE, {}
    if "/contributors?" in url:
        link = '<https://api.github.com/x?page=42>; rel="last"'
        return [], {"Link": link}
    raise AssertionError(f"unerwartete URL: {url}")


class CollectTest(unittest.TestCase):
    def test_collect_berechnet_alle_felder(self):
        with mock.patch.object(github_metrics, "_get", side_effect=fake_get):
            result = github_metrics.collect("acme/tool")
        self.assertEqual(result["stars"], 2000)
        self.assertEqual(result["last_commit"], "2026-06-01T12:00:00Z")
        self.assertFalse(result["archived"])
        self.assertEqual(result["open_issues"], 50)
        self.assertEqual(result["issues_per_1k_stars"], 25.0)
        self.assertEqual(result["releases_last_year"], 1)
        self.assertEqual(result["last_release"], "2026-05-01T00:00:00Z")
        self.assertEqual(result["contributors_approx"], 42)

    def test_collect_ohne_releases_und_stars(self):
        def fake(url):
            if "/releases?" in url:
                return [], {}
            if "/contributors?" in url:
                return [], {}
            return {"stargazers_count": 0, "pushed_at": None,
                    "archived": True, "open_issues_count": 3}, {}
        with mock.patch.object(github_metrics, "_get", side_effect=fake):
            result = github_metrics.collect("acme/leer")
        self.assertIsNone(result["issues_per_1k_stars"])
        self.assertEqual(result["releases_last_year"], 0)
        self.assertIsNone(result["last_release"])
        self.assertTrue(result["archived"])
        self.assertEqual(result["contributors_approx"], 1)


class MainTest(unittest.TestCase):
    def test_main_ohne_gueltige_slugs_gibt_1(self):
        self.assertEqual(github_metrics.main(["prog"]), 1)
        self.assertEqual(github_metrics.main(["prog", "kein-slash"]), 1)

    def test_main_rate_limit_gibt_2(self):
        with mock.patch.object(
            github_metrics, "collect",
            side_effect=github_metrics.RateLimitError("Limit erreicht"),
        ), mock.patch("builtins.print") as fake_print:
            code = github_metrics.main(["prog", "acme/tool"])
        self.assertEqual(code, 2)
        payload = json.loads(fake_print.call_args_list[0].args[0])
        self.assertIn("error", payload["acme/tool"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Tests laufen lassen — müssen fehlschlagen**

Run: `cd projekt-bootstrap/scripts && python3 -m unittest test_github_metrics -v`
Expected: ERROR mit `ModuleNotFoundError: No module named 'github_metrics'`

- [ ] **Step 3: Implementierung schreiben**

Vollständiger Inhalt von `projekt-bootstrap/scripts/github_metrics.py`:

```python
#!/usr/bin/env python3
"""GitHub-Metriken für Tech-Stack-Kandidaten (projekt-bootstrap Skill).

Aufruf:   python3 github_metrics.py owner/repo [owner/repo ...]
Ausgabe:  JSON auf stdout, ein Eintrag pro Repo.
Auth:     GITHUB_TOKEN wird genutzt, falls gesetzt (höheres Rate-Limit).
Exit:     0 = ok (einzelne Repo-Fehler stehen im JSON),
          1 = Usage-Fehler, 2 = Rate-Limit-Abbruch.

Nur Python-Standardbibliothek, plattformunabhängig.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"
RELEASES_SAMPLE = 30
TIMEOUT_SECONDS = 15


class RateLimitError(Exception):
    """GitHub-Rate-Limit erschöpft — Lauf abbrechen statt still raten."""


def _request(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "projekt-bootstrap-skill",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8")), dict(resp.headers)


def _get(url):
    try:
        return _request(url)
    except urllib.error.HTTPError as err:
        if err.code in (403, 429) and err.headers.get("X-RateLimit-Remaining") == "0":
            raise RateLimitError(
                "GitHub-Rate-Limit erreicht. GITHUB_TOKEN setzen "
                "oder später erneut versuchen."
            ) from err
        raise


def _parse_iso(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _contributors_approx(slug):
    _, headers = _get(f"{API}/repos/{slug}/contributors?per_page=1&anon=true")
    match = re.search(r'[?&]page=(\d+)>; rel="last"', headers.get("Link", ""))
    return int(match.group(1)) if match else 1


def collect(slug):
    repo, _ = _get(f"{API}/repos/{slug}")
    releases, _ = _get(f"{API}/repos/{slug}/releases?per_page={RELEASES_SAMPLE}")
    year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    recent = [
        r for r in releases
        if r.get("published_at") and _parse_iso(r["published_at"]) > year_ago
    ]
    stars = repo.get("stargazers_count", 0)
    open_issues = repo.get("open_issues_count", 0)
    return {
        "stars": stars,
        "last_commit": repo.get("pushed_at"),
        "archived": repo.get("archived", False),
        "open_issues": open_issues,
        "issues_per_1k_stars": (
            round(open_issues / stars * 1000, 1) if stars else None
        ),
        "releases_last_year": len(recent),
        "last_release": (
            releases[0]["published_at"] if releases
            and releases[0].get("published_at") else None
        ),
        "contributors_approx": _contributors_approx(slug),
    }


def main(argv):
    slugs = [arg for arg in argv[1:] if "/" in arg]
    if not slugs:
        print(
            "Aufruf: github_metrics.py owner/repo [owner/repo ...]",
            file=sys.stderr,
        )
        return 1
    results = {}
    for slug in slugs:
        try:
            results[slug] = collect(slug)
        except RateLimitError as err:
            results[slug] = {"error": str(err)}
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return 2
        except urllib.error.HTTPError as err:
            results[slug] = {"error": f"HTTP {err.code} für {slug}"}
        except urllib.error.URLError as err:
            results[slug] = {"error": f"Netzwerkfehler: {err.reason}"}
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Tests laufen lassen — müssen bestehen**

Run: `cd projekt-bootstrap/scripts && python3 -m unittest test_github_metrics -v`
Expected: `OK`, 4 Tests bestanden.

- [ ] **Step 5: Commit**

```bash
git add projekt-bootstrap/scripts/github_metrics.py projekt-bootstrap/scripts/test_github_metrics.py
git commit -m "feat: github_metrics.py mit Offline-Tests (Stars, Wartung, Releases, Contributors)"
```

---

### Task 3: references/interview-leitfaden.md

**Files:**
- Create: `projekt-bootstrap/references/interview-leitfaden.md`

**Interfaces:**
- Consumes: wird von SKILL.md Phase 1 referenziert.
- Produces: Projektprofil-Format (YAML) und Ableitungstabellen Profil → Recherche-Kategorien bzw. Profil → bedingte context/-Dateien; Task 5 und SKILL.md Phase 4 bauen darauf auf.

- [ ] **Step 1: Datei schreiben**

Vollständiger Inhalt:

````markdown
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
| Framework (App/Web/Backend) | immer außer reine Library |
| Wichtige Libraries | immer |
| Datenbank + ORM | wenn Persistenz nötig (aus Projektidee ableiten; im Zweifel fragen) |
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
| design-system | Kategorie "UI" war aktiv |
| deployment | Kategorie "Deployment / Hosting" war aktiv |
| ki-integration | Kategorie "KI-SDK / Provider" war aktiv |
````

- [ ] **Step 2: Konsistenz-Check gegen SKILL.md**

Run: `grep -n "interview-leitfaden" projekt-bootstrap/SKILL.md`
Expected: Treffer in Phase 1 — Pfad `references/interview-leitfaden.md` stimmt mit der erstellten Datei überein.

- [ ] **Step 3: Commit**

```bash
git add projekt-bootstrap/references/interview-leitfaden.md
git commit -m "feat: Interview-Leitfaden (Projektprofil, Kategorien-Ableitung)"
```

---

### Task 4: references/bewertungsrubrik.md

**Files:**
- Create: `projekt-bootstrap/references/bewertungsrubrik.md`

**Interfaces:**
- Consumes: Metrik-Feldnamen aus Task 2 (`stars`, `last_commit`, `archived`, `releases_last_year`, `issues_per_1k_stars`, `contributors_approx`).
- Produces: Bewertungsschema (1–5 je Kriterium, gewichtete Summe, K.-o.-Kriterien, Ampel-Schwellen), das Task 5 vorschreibt.

- [ ] **Step 1: Datei schreiben**

Vollständiger Inhalt:

````markdown
# Bewertungsrubrik für Stack-Kandidaten

Jeder Kandidat bekommt pro Kriterium 1–5 Punkte; Gesamtscore =
gewichtete Summe. Empfehlung = höchster Score, sofern kein K.-o.

## Gewichte

| Kriterium | Gewicht | Datenquelle |
|---|---|---|
| Aktualität / Wartung | 25 % | `last_commit`, `releases_last_year`, `archived` |
| Community-Größe / Beliebtheit | 25 % | `stars`, `contributors_approx`, WebSearch (Umfragen, Downloads) |
| Doku-Qualität | 20 % | Context7-Abdeckung, offizielle Doku (WebSearch) |
| Robustheit / Reife | 20 % | Alter, `issues_per_1k_stars`, Major-Version ≥ 1, bekannte Produktionsnutzer |
| Ökosystem-Fit | 10 % | Verträglichkeit mit bereits gesetzten Kategorien des Vorschlags |

## K.-o.-Kriterien (disqualifizieren unabhängig vom Score)

- `archived: true`
- `last_commit` älter als 24 Monate
- Offiziell deprecated / Nachfolger existiert

## Ampel-Schwellen (in der Vorschlagstabelle ausweisen)

| Signal | Gelb | Rot |
|---|---|---|
| `last_commit` | > 6 Monate | > 12 Monate |
| `releases_last_year` | 0–1 | 0 UND `last_commit` > 12 Monate |
| `stars` | < 2 000 (außer Nischen-Ökosystem — dann begründen) | < 300 |
| `contributors_approx` | < 20 | < 5 (Bus-Faktor) |
| `issues_per_1k_stars` | > 150 | — (nur Hinweis, nie allein rot) |

## Punktevergabe (Richtwerte)

- 5 = führend in der Kategorie, keine gelben Signale
- 4 = solide, höchstens ein gelbes Signal
- 3 = brauchbar, mehrere gelbe Signale oder junge Reife
- 2 = riskant, rotes Signal vorhanden
- 1 = ungeeignet

## Regeln

- Metriken stammen aus `scripts/github_metrics.py`. Konnte das Script
  nicht laufen (kein Netz, Rate-Limit), Kandidaten als
  **"Metriken nicht live verifiziert"** kennzeichnen — niemals Zahlen
  schätzen und als echt ausgeben.
- Score-Gleichstand (< 0,3 Differenz): nach Ökosystem-Fit entscheiden
  und explizit begründen.
- Nicht-GitHub-Kandidaten (z.B. kommerzielle Produkte): Kriterien
  Aktualität, Doku, Robustheit per WebSearch belegen, Community per
  Umfragen/Marktanteil.
````

- [ ] **Step 2: Feldnamen-Konsistenz prüfen**

Run: `grep -o "last_commit\|releases_last_year\|issues_per_1k_stars\|contributors_approx\|archived\|stars" projekt-bootstrap/references/bewertungsrubrik.md | sort -u`
Expected: alle sechs Feldnamen, identisch mit den JSON-Keys aus `github_metrics.py` (Task 2 Interface).

- [ ] **Step 3: Commit**

```bash
git add projekt-bootstrap/references/bewertungsrubrik.md
git commit -m "feat: Bewertungsrubrik (Gewichte, K.-o.-Kriterien, Ampel-Schwellen)"
```

---

### Task 5: references/recherche-anleitung.md

**Files:**
- Create: `projekt-bootstrap/references/recherche-anleitung.md`

**Interfaces:**
- Consumes: Script-CLI aus Task 2, Rubrik aus Task 4, Kategorien aus Task 3.
- Produces: Ergebnisformat pro Kategorie (YAML-Block), das SKILL.md Phase 3 zur Vorschlagstabelle zusammensetzt.

- [ ] **Step 1: Datei schreiben**

Vollständiger Inhalt:

````markdown
# Recherche-Anleitung (pro Kategorie, für parallele Agents)

Du bist ein Recherche-Agent für GENAU EINE Kategorie (z.B. "Framework")
eines Greenfield-Projekts. Du bekommst: die Kategorie und das
Projektprofil. Liefere am Ende NUR den Ergebnisblock (Format unten).

## Schritte

1. **Kandidaten finden (WebSearch):** Suche nach dem aktuellen Stand
   der Technik für die Kategorie im Kontext des Projektprofils
   (Plattform, Projekttyp, aktuelles Jahr in die Suchanfrage
   aufnehmen). Wähle 2–3 ernsthafte Kandidaten. Keine Nischen-Exoten,
   außer das Profil verlangt es.
2. **Metriken holen:** Für alle Kandidaten mit GitHub-Repo in EINEM
   Aufruf:
   `python3 <skill-pfad>/scripts/github_metrics.py owner/repo1 owner/repo2 owner/repo3`
   Bei Exit-Code 2 (Rate-Limit) oder Netzwerkfehler: Kandidaten als
   `metriken_verifiziert: nein` markieren und mit Modellwissen
   weiterarbeiten.
3. **Doku-Qualität (Context7):** Pro Kandidat prüfen, ob Context7 eine
   aktuelle Library-Doku kennt (resolve-library-id). Zusätzlich per
   WebSearch: offizielle Doku vorhanden und gepflegt?
4. **Bewerten:** Nach `references/bewertungsrubrik.md` — Punkte 1–5 je
   Kriterium, gewichtete Summe, K.-o.-Kriterien und Ampel-Signale
   anwenden.

## Ergebnisformat (exakt so zurückgeben)

```yaml
kategorie: <Name>
empfehlung:
  name: <Kandidat>
  version: <aktuelle stabile Version>
  repo: <owner/repo oder "kein GitHub">
  score: <x.x von 5>
  metriken_verifiziert: ja | nein
  metriken: {stars: …, last_commit: …, releases_last_year: …, contributors_approx: …}
  begruendung: <2–3 Sätze: warum dieser Kandidat für DIESES Projekt>
  ampel_signale: [<gelbe/rote Signale oder leer>]
alternativen:
  - name: <Kandidat 2>
    score: <x.x>
    kurzbegruendung: <1 Satz + wann er die bessere Wahl wäre>
  - name: <Kandidat 3 (optional)>
    score: <x.x>
    kurzbegruendung: <1 Satz>
offene_punkte: <Unsicherheiten oder "keine">
```

## Regeln

- Niemals Metriken erfinden. Nicht verifiziert = klar sagen.
- Findest du keinen tragfähigen Kandidaten, gib
  `empfehlung: keine — Kategorie offen` mit Begründung zurück.
- Begründungen projektspezifisch formulieren, nicht generisch.
````

- [ ] **Step 2: Querverweise prüfen**

Run: `grep -n "recherche-anleitung\|bewertungsrubrik\|github_metrics" projekt-bootstrap/SKILL.md projekt-bootstrap/references/recherche-anleitung.md`
Expected: SKILL.md referenziert beide references-Dateien; recherche-anleitung referenziert Script und Rubrik mit korrekten Pfaden.

- [ ] **Step 3: Commit**

```bash
git add projekt-bootstrap/references/recherche-anleitung.md
git commit -m "feat: Recherche-Anleitung für parallele Stack-Agents"
```

---

### Task 6: Kern-Templates (9 Dateien)

**Files:**
- Create: `projekt-bootstrap/references/templates/CLAUDE.template.md`
- Create: `projekt-bootstrap/references/templates/AGENTS.template.md`
- Create: `projekt-bootstrap/references/templates/projekt-brief.template.md`
- Create: `projekt-bootstrap/references/templates/architektur.template.md`
- Create: `projekt-bootstrap/references/templates/tech-stack.template.md`
- Create: `projekt-bootstrap/references/templates/coding-standards.template.md`
- Create: `projekt-bootstrap/references/templates/testing.template.md`
- Create: `projekt-bootstrap/references/templates/automatisierung.template.md`
- Create: `projekt-bootstrap/references/templates/sicherheit.template.md`

**Interfaces:**
- Consumes: Ergebnisformat aus Task 5 (tech-stack füllt sich daraus), Template-Konvention aus Global Constraints.
- Produces: Kommentarblock `<!-- zweck: … wann-lesen: … anleitung: … -->` am Dateianfang jedes Templates; CLAUDE/AGENTS ziehen daraus die Beschreibungszeilen ihrer Referenztabellen.

- [ ] **Step 1: CLAUDE.template.md schreiben**

````markdown
<!--
zweck: Einstiegsdatei für Claude Code — Projektüberblick und Wegweiser zu den context/-Dateien.
wann-lesen: Wird von Claude Code automatisch geladen; muss kompakt bleiben.
anleitung: Alle {{PLATZHALTER}} füllen. Tabelle enthält NUR tatsächlich
erzeugte context/-Dateien; Beschreibungen aus deren zweck-Kommentar
übernehmen. Kein Inhalt aus context/-Dateien duplizieren.
-->
# {{PROJEKTNAME}}

{{EIN_ABSATZ_WAS_DAS_PROJEKT_IST_UND_FUER_WEN}}

## Tech-Stack (Kurzfassung)

{{STACK_IN_3_BIS_5_ZEILEN_DETAILS_IN_CONTEXT_TECH_STACK}}

## Context-Dateien

Vor Arbeit am jeweiligen Thema die passende Datei lesen:

| Datei | Wann lesen |
|---|---|
| `context/projekt-brief.md` | {{BESCHREIBUNG_AUS_ZWECK}} |
| `context/architektur.md` | {{BESCHREIBUNG_AUS_ZWECK}} |
| `context/tech-stack.md` | {{BESCHREIBUNG_AUS_ZWECK}} |
{{WEITERE_ZEILEN_FUER_ALLE_ERZEUGTEN_DATEIEN}}

## Arbeitsregeln

- {{PROJEKTSPEZIFISCHE_REGELN_BUILD_TEST_LINT_BEFEHLE_BRANCH_KONVENTION}}
````

- [ ] **Step 2: AGENTS.template.md schreiben**

Gleicher Aufbau wie CLAUDE.template.md (identische Referenztabelle), mit drei Abweichungen:
- zweck-Kommentar: „Einstiegsdatei für andere KI-Coding-Tools (Cursor, Codex, Gemini CLI …) nach AGENTS.md-Standard."
- Nach der Überschrift ein Hinweis-Absatz: „Diese Datei wird inhaltsgleich mit CLAUDE.md gepflegt. Änderungen in beiden Dateien nachziehen."
- Abschnitt „Arbeitsregeln" heißt „Conventions" (gleiche Punkte).

- [ ] **Step 3: projekt-brief.template.md schreiben**

````markdown
<!--
zweck: Ziele, Scope und Anforderungen des Projekts — die fachliche Wahrheit.
wann-lesen: Vor jeder Feature-Arbeit und bei Unklarheit über Anforderungen oder Priorität.
anleitung: Alle {{PLATZHALTER}} aus dem Interview-Projektprofil füllen.
Nicht-Ziele explizit machen — sie verhindern Scope-Creep.
-->
# Projekt-Brief: {{PROJEKTNAME}}

## Vision
{{EIN_ABSATZ}}

## Zielgruppe
{{WER_NUTZT_DAS_PRODUKT}}

## Kernfunktionen (Muss)
{{NUMMERIERTE_LISTE}}

## Nice-to-have (Später)
{{LISTE_ODER_ABSCHNITT_ENTFERNEN}}

## Nicht-Ziele
{{WAS_BEWUSST_NICHT_GEBAUT_WIRD}}

## Zielplattformen
{{PLATTFORMEN_AUS_PROFIL}}

## Rahmenbedingungen
{{HOSTING_TEAM_BUDGET_ZEIT}}

## Erfolgskriterien
{{MESSBARE_KRITERIEN}}
````

- [ ] **Step 4: architektur.template.md schreiben**

````markdown
<!--
zweck: Systemarchitektur, Komponenten, Datenfluss und Ordnerstruktur.
wann-lesen: Vor strukturellen Änderungen, neuen Modulen oder Komponenten-Schnitten.
anleitung: Architektur zum bestätigten Stack konkretisieren. Diagramm
als ASCII oder Mermaid. Ordnerstruktur als Baum mit Ein-Zeilen-Zweck
pro Ordner.
-->
# Architektur

## Architekturstil
{{Z_B_SCHICHTEN_HEXAGONAL_CLIENT_SERVER_PLUS_BEGRUENDUNG}}

## Komponentenübersicht
{{DIAGRAMM}}

## Komponenten
{{PRO_KOMPONENTE_VERANTWORTUNG_SCHNITTSTELLE_ABHAENGIGKEITEN}}

## Datenfluss
{{TYPISCHE_NUTZERAKTION_VON_ANFANG_BIS_ENDE}}

## Ordnerstruktur
{{BAUM_MIT_ZWECK_PRO_ORDNER}}

## Architektur-Entscheidungen
{{TABELLE_ENTSCHEIDUNG_ALTERNATIVE_BEGRUENDUNG}}
````

- [ ] **Step 5: tech-stack.template.md schreiben**

````markdown
<!--
zweck: Der bestätigte Tech-Stack mit Versionen, Begründungen und Recherche-Metriken.
wann-lesen: Bevor eine neue Dependency eingeführt oder eine bestehende ersetzt wird.
anleitung: Direkt aus dem bestätigten Vorschlag (Phase 3) füllen.
metriken_verifiziert ehrlich übernehmen. Stand-Datum setzen.
-->
# Tech-Stack

Stand der Recherche: {{DATUM}}. Empfehlungen basieren auf Live-Metriken
(GitHub) und WebSearch; nicht verifizierte Angaben sind markiert.

## Übersicht

| Kategorie | Wahl | Version | Score | Metriken live? |
|---|---|---|---|---|
{{EINE_ZEILE_PRO_KATEGORIE}}

## Begründungen

{{PRO_KATEGORIE_ABSATZ_MIT_BEGRUENDUNG_METRIKEN_ALTERNATIVEN_AMPEL_SIGNALEN}}

## Bewusst verworfen

{{TABELLE_KANDIDAT_ABLEHNUNGSGRUND}}

## Upgrade-Politik

{{WIE_MIT_MAJOR_UPDATES_UMGEHEN}}
````

- [ ] **Step 6: coding-standards.template.md schreiben**

````markdown
<!--
zweck: Verbindliche Code-Konventionen für dieses Projekt und diesen Stack.
wann-lesen: Vor dem Schreiben oder Reviewen von Code.
anleitung: Konventionen konkret auf Sprache/Framework zuschneiden
(Naming, Formatter, Linter mit Konfignamen). Keine allgemeinen
Weisheiten ohne Projektbezug.
-->
# Coding-Standards

## Sprache & Stil
{{SPRACHVERSION_FORMATTER_LINTER_MIT_KONFIG}}

## Naming
{{KONVENTIONEN_DATEIEN_TYPEN_FUNKTIONEN_KONSTANTEN}}

## Projektprinzipien
{{Z_B_IMMUTABILITY_EARLY_RETURNS_MAX_DATEIGROESSE_AUF_STACK_ANGEPASST}}

## Fehlerbehandlung
{{MUSTER_FUER_DIESEN_STACK_FEHLERTYPEN_LOGGING_USER_MELDUNGEN}}

## Abhängigkeiten
{{REGELN_WANN_NEUE_DEPENDENCY_ERLAUBT_SECURITY_CHECK}}
````

- [ ] **Step 7: testing.template.md schreiben**

````markdown
<!--
zweck: Teststrategie, Frameworks, Coverage-Ziele und Testbefehle.
wann-lesen: Vor dem Schreiben von Tests und vor jedem Merge.
anleitung: Frameworks aus dem bestätigten Stack; Befehle müssen nach
Scaffolding lauffähig sein. Coverage-Ziel projektgerecht begründen.
-->
# Testing

## Strategie
{{TESTPYRAMIDE_WAS_WIRD_UNIT_INTEGRATION_E2E_GETESTET}}

## Frameworks & Tools
{{TABELLE_EBENE_TOOL_ZWECK}}

## Befehle
{{TESTBEFEHLE_ALLE_EINZELN_COVERAGE_WATCH}}

## Coverage-Ziel
{{ZIEL_PROZENT_BEGRUENDUNG_AUSNAHMEN}}

## Konventionen
{{AAA_MUSTER_NAMING_TESTDATEN_MOCK_REGELN_STACKSPEZIFISCH}}
````

- [ ] **Step 8: automatisierung.template.md schreiben**

````markdown
<!--
zweck: CI/CD, Linter/Formatter-Automatik, Pre-Commit-Hooks und Release-Automatisierung.
wann-lesen: Beim Aufsetzen oder Ändern von Pipelines, Hooks oder Release-Prozessen.
anleitung: Konkrete Tools aus dem bestätigten Stack; Pipeline-Schritte
in Reihenfolge; Hook-Konfiguration benennen.
-->
# Automatisierung

## CI-Pipeline
{{PLATTFORM_UND_SCHRITTE_IN_REIHENFOLGE_LINT_TEST_BUILD}}

## Pre-Commit-Hooks
{{TOOL_UND_WELCHE_CHECKS_LOKAL_LAUFEN}}

## Formatierung & Linting
{{WAS_LAEUFT_AUTOMATISCH_WANN_SAVE_COMMIT_CI}}

## Release-Prozess
{{VERSIONIERUNG_CHANGELOG_TAGGING_DEPLOY_TRIGGER}}

## Geplante Automatisierungen
{{WAS_SPAETER_KOMMT_ODER_ABSCHNITT_ENTFERNEN}}
````

- [ ] **Step 9: sicherheit.template.md schreiben**

````markdown
<!--
zweck: Security-Baseline: Secrets, Input-Validierung, AuthN/AuthZ, Abhängigkeits-Sicherheit.
wann-lesen: Vor Arbeit an Auth, Nutzereingaben, externen APIs oder vor jedem Release.
anleitung: Auf den Stack zuschneiden (konkrete Tools/Mechanismen).
OWASP-Punkte nur aufnehmen, wo für das Projekt relevant.
-->
# Sicherheit

## Secrets
{{WO_LIEGEN_SECRETS_WAS_NIE_INS_REPO_DARF_STARTUP_VALIDIERUNG}}

## Input-Validierung
{{VALIDIERUNGS_TOOL_DES_STACKS_REGEL_AN_ALLEN_SYSTEMGRENZEN}}

## Authentifizierung & Autorisierung
{{MECHANISMUS_ODER_ABSCHNITT_ENTFERNEN_WENN_KEIN_AUTH}}

## Abhängigkeits-Sicherheit
{{AUDIT_TOOL_UND_WANN_ES_LAEUFT_CI_DEPENDABOT}}

## Projektspezifische Risiken
{{TOP_RISIKEN_DIESES_PROJEKTS_UND_GEGENMASSNAHMEN}}
````

- [ ] **Step 10: Kommentarblock-Konsistenz prüfen**

Run: `grep -L "zweck:" projekt-bootstrap/references/templates/*.template.md`
Expected: keine Ausgabe (jede Template-Datei hat den zweck-Kommentarblock).

- [ ] **Step 11: Commit**

```bash
git add projekt-bootstrap/references/templates/
git commit -m "feat: Kern-Templates (CLAUDE, AGENTS, Brief, Architektur, Stack, Standards, Testing, Automatisierung, Sicherheit)"
```

---

### Task 7: Bedingte Templates (5 Dateien)

**Files:**
- Create: `projekt-bootstrap/references/templates/api-design.template.md`
- Create: `projekt-bootstrap/references/templates/datenmodell.template.md`
- Create: `projekt-bootstrap/references/templates/design-system.template.md`
- Create: `projekt-bootstrap/references/templates/deployment.template.md`
- Create: `projekt-bootstrap/references/templates/ki-integration.template.md`

**Interfaces:**
- Consumes: Kommentarblock-Format aus Task 6, Bedingungstabelle aus Task 3.
- Produces: die 5 bedingten Templates, die SKILL.md Phase 4 Punkt 2 aufzählt.

- [ ] **Step 1: api-design.template.md schreiben**

````markdown
<!--
zweck: API-Konventionen: Stil, Endpunkt-Design, Response-Format, Versionierung, Fehlercodes.
wann-lesen: Vor dem Anlegen oder Ändern von API-Endpunkten.
anleitung: Stil (REST/GraphQL/RPC) aus dem bestätigten Stack;
Response-Envelope konkret als JSON-Beispiel zeigen.
-->
# API-Design

## Stil & Grundregeln
{{REST_GRAPHQL_RPC_URL_NAMING_KONVENTIONEN}}

## Response-Format
{{ENVELOPE_ALS_JSON_BEISPIEL_SUCCESS_DATA_ERROR_META}}

## Fehlerbehandlung
{{STATUS_CODES_FEHLERFORMAT_BEISPIEL}}

## Versionierung
{{STRATEGIE_ODER_BEGRUENDET_KEINE}}

## Paginierung, Filter, Sortierung
{{KONVENTION_FUER_LISTEN_ENDPUNKTE}}

## Rate-Limiting & Auth
{{VERWEIS_AUF_SICHERHEIT_MD_PLUS_API_SPEZIFISCHES}}
````

- [ ] **Step 2: datenmodell.template.md schreiben**

````markdown
<!--
zweck: Entitäten, Beziehungen, Migrations-Regeln und Datenbank-Konventionen.
wann-lesen: Vor Schema-Änderungen, Migrationen oder neuen Entitäten.
anleitung: Entitäten aus dem Projekt-Brief ableiten; ER-Diagramm als
Mermaid; Migrations-Tool aus dem Stack.
-->
# Datenmodell

## Datenbank & Zugriff
{{DB_ORM_AUS_STACK_VERBINDUNGSKONVENTION}}

## Entitäten
{{ER_DIAGRAMM_MERMAID_PRO_ENTITAET_FELDER_TYPEN_CONSTRAINTS}}

## Namenskonventionen
{{TABELLEN_SPALTEN_INDEXE}}

## Migrationen
{{TOOL_REGELN_ADDITIV_REVIEW_ROLLBACK}}

## Seed- & Testdaten
{{WOHER_KOMMEN_ENTWICKLUNGSDATEN}}
````

- [ ] **Step 3: design-system.template.md schreiben**

````markdown
<!--
zweck: UI-Grundlagen: Design-Tokens, Komponentenbibliothek, Layout- und Zustandskonventionen, Accessibility.
wann-lesen: Vor dem Bauen oder Ändern von UI-Komponenten und Screens.
anleitung: Komponentenbibliothek/Styling aus dem bestätigten Stack;
Tokens konkret benennen; A11y-Zielniveau festlegen.
-->
# Design-System

## Styling-Ansatz
{{TOOL_METHODE_AUS_STACK_WO_STYLES_LIEGEN}}

## Design-Tokens
{{FARBEN_TYPO_SPACING_TABELLE_ODER_TOKEN_DATEI_VERWEIS}}

## Komponenten
{{BIBLIOTHEK_REGELN_WANN_EIGENE_KOMPONENTE_STRUKTUR_NAMING}}

## Layout & Responsivität
{{BREAKPOINTS_GRID_PLATTFORM_KONVENTIONEN}}

## Zustände & Feedback
{{LOADING_ERROR_EMPTY_STATES_EINHEITLICHE_MUSTER}}

## Accessibility
{{ZIELNIVEAU_Z_B_WCAG_2_2_AA_KONKRETE_PFLICHTEN}}
````

- [ ] **Step 4: deployment.template.md schreiben**

````markdown
<!--
zweck: Umgebungen, Deploy-Prozess, Infrastruktur und Rollback.
wann-lesen: Vor jedem Deploy und bei Infrastruktur-Änderungen.
anleitung: Hosting aus dem Interview-Profil; Deploy-Schritte konkret
ausführbar beschreiben; Rollback nie weglassen.
-->
# Deployment

## Umgebungen
{{TABELLE_UMGEBUNG_ZWECK_ORT_DEPLOY_TRIGGER}}

## Infrastruktur
{{HOSTING_DIENSTE_KONFIGURATION_IAC_TOOL_FALLS_VORHANDEN}}

## Deploy-Prozess
{{SCHRITTE_IN_REIHENFOLGE_WER_DARF_AUTOMATISIERUNGSGRAD}}

## Konfiguration & Secrets pro Umgebung
{{UNTERSCHIEDE_PRO_UMGEBUNG_VERWEIS_AUF_SICHERHEIT_MD}}

## Rollback
{{KONKRETE_SCHRITTE_LETZTES_RELEASE_WIEDERHERSTELLEN}}

## Monitoring
{{LOGS_METRIKEN_ALERTS_ODER_GEPLANT}}
````

- [ ] **Step 5: ki-integration.template.md schreiben**

````markdown
<!--
zweck: KI-Funktionen: Modelle, Provider, Prompts, Evaluation, Kosten und Fallbacks.
wann-lesen: Vor Arbeit an KI-Features, Prompt-Änderungen oder Modell-Upgrades.
anleitung: Modelle/SDK aus dem bestätigten Stack mit exakten
Modell-IDs; Kosten mit aktueller Preisbasis; Eval-Ansatz konkret.
-->
# KI-Integration

## Anwendungsfälle
{{WELCHE_FEATURES_NUTZEN_KI_ANFORDERUNGEN_LATENZ_QUALITAET_KOSTEN}}

## Modelle & Provider
{{TABELLE_ANWENDUNGSFALL_MODELL_ID_PROVIDER_BEGRUENDUNG}}

## SDK & Aufruf-Muster
{{SDK_AUS_STACK_WO_LIEGEN_KI_AUFRUFE_STREAMING_TIMEOUTS_RETRIES}}

## Prompts
{{WO_LIEGEN_PROMPTS_VERSIONIERUNGS_REVIEW_REGEL}}

## Evaluation
{{WIE_WIRD_QUALITAET_GEMESSEN_TESTFAELLE_METRIKEN_REGRESSION}}

## Kosten
{{ERWARTETE_KOSTEN_BUDGET_LIMITS_MONITORING}}

## Fallbacks & Fehlerfälle
{{VERHALTEN_BEI_PROVIDER_AUSFALL_RATE_LIMIT_SCHLECHTER_ANTWORT}}
````

- [ ] **Step 6: Vollständigkeit prüfen**

Run: `ls projekt-bootstrap/references/templates/ | wc -l && ls projekt-bootstrap/references/templates/`
Expected: 14 Dateien — die 9 aus Task 6 plus die 5 aus diesem Task; Namen exakt wie in SKILL.md Phase 4 und Spec.

- [ ] **Step 7: Commit**

```bash
git add projekt-bootstrap/references/templates/
git commit -m "feat: bedingte Templates (API, Datenmodell, Design-System, Deployment, KI)"
```

---

### Task 8: Verifikation — Script-Integrationstest + 3 Probeläufe

**Files:**
- Modify: keine geplant (gefundene Fehler werden in den betroffenen Dateien behoben und als `fix:` committet)

**Interfaces:**
- Consumes: das komplette Skill aus Task 1–7.

- [ ] **Step 1: Script-Integrationstest (echtes Netz)**

Run: `python3 projekt-bootstrap/scripts/github_metrics.py facebook/react gibtsnicht/gibtsnicht`
Expected: JSON mit plausiblen Werten für `facebook/react` (stars > 200000, last_commit jünger als 1 Monat) und `{"error": "HTTP 404 für gibtsnicht/gibtsnicht"}`; Exit-Code 0.

- [ ] **Step 2: Offline-Tests erneut**

Run: `cd projekt-bootstrap/scripts && python3 -m unittest test_github_metrics -v`
Expected: `OK`.

- [ ] **Step 3: Probelauf A — Full-Stack-Web-App**

In einem frischen Scratchpad-Ordner das Skill-Verfahren nach SKILL.md durchspielen (Interview-Antworten simuliert: Full-Stack-Web-App, Browser, Cloud-Hosting, Solo, Deutsch). Prüfliste:
- Recherche-Kategorien stimmen mit der interview-leitfaden-Ableitung überein
- Vorschlagstabelle enthält Metriken + Ampel-Signale, Gate wartet auf Bestätigung
- Nach simulierter Bestätigung: `context/` mit 7 Kern-Dateien + api-design, datenmodell, design-system, deployment
- `grep -r "{{" <ordner>` → keine Treffer
- Jede in CLAUDE.md/AGENTS.md referenzierte Datei existiert (und umgekehrt)

- [ ] **Step 4: Probelauf B — native iOS-App**

Wie Step 3 (iOS nativ, kein Backend, Englisch als Dateisprache). Zusätzlich prüfen:
- englische Dateinamen (`project-brief.md`, `architecture.md`, …)
- KEINE api-design-/datenmodell-/deployment-Datei (kein Backend, kein Hosting)
- design-system vorhanden

- [ ] **Step 5: Probelauf C — KI-CLI-Tool**

Wie Step 3 (CLI-Tool mit KI-Funktionen, lokal, Deutsch). Zusätzlich prüfen:
- ki-integration.md vorhanden, design-system NICHT vorhanden
- Kollisionstest: zweiten Lauf im selben Ordner simulieren → Skill stoppt mit Rückfrage statt zu überschreiben

- [ ] **Step 6: Gefundene Probleme beheben und committen**

```bash
git add -A projekt-bootstrap/
git commit -m "fix: Korrekturen aus Probeläufen A–C"
```
(Entfällt, wenn nichts zu beheben war.)

---

### Task 9: Installation + README

**Files:**
- Create: Symlink `~/.claude/skills/projekt-bootstrap` → `~/Desktop/skills/projekt-bootstrap`
- Modify: `README.md` (Skill-Tabelle)

- [ ] **Step 1: Symlink anlegen**

Run: `ln -s ~/Desktop/skills/projekt-bootstrap ~/.claude/skills/projekt-bootstrap && ls -la ~/.claude/skills/ | grep projekt-bootstrap`
Expected: Symlink zeigt auf den Werkstatt-Ordner.

- [ ] **Step 2: README-Tabelle aktualisieren**

In `README.md` die Zeile ``| `projekt-bootstrap` | geplant |`` ersetzen durch ``| `projekt-bootstrap` | einsatzbereit |``.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: projekt-bootstrap als einsatzbereit markiert"
```
