# Roadmap — offene Verbesserungen (priorisiert)

Stand: nach dem ersten Praxiseinsatz. Reihenfolge = Empfehlung zum Abarbeiten.
Diese Datei ist person-neutral; konkrete Nutzer-/Migrationsaufgaben stehen bewusst
ganz unten und gehören **nicht** ins geteilte Skill.

## P0 — Sicherheit & Vertrauen (zuerst) — ✅ ERLEDIGT

### 1. Schwärzung ehrlich einordnen + „im Zweifel nicht extrahieren" — ✅ erledigt
- **Problem:** Die lokale Schwärzung ist Risiko-Reduktion, kein Schutz. In der Praxis
  ist sie schon einmal versagt (Behörden-PDF mit zerstückeltem Text → Name/Adresse
  gingen durch, bis `is_garbled` griff).
- **To-do:** In `SKILL.md` klar sagen „geschwärzt ≠ sicher". Für *eindeutig* sensible
  Dokumente (Ausweis, Finanzen, Gesundheit) Default = **nur Dateiname nutzen bzw.
  Nutzer fragen, gar nicht extrahieren**. Extraktion nur bei unklarem/harmlosem Verdacht.
- **Fertig, wenn:** SKILL.md-Passage + Verhalten dokumentiert; kein „high confidence"
  wird ungeprüft übernommen.
- **Umgesetzt:** Neue SKILL.md-Kategorie „Eindeutig hochsensible Dokumente" (Default =
  gar nicht extrahieren, nur Dateiname/Nachfrage); bestehende Kategorie auf
  „unklarer/harmloser Verdacht" umformuliert; expliziter Absatz „geschwärzt ≠ sicher";
  `confidence: "high"`-Absatz verschärft (nie ungeprüft übernehmen).

### 2. Schwärzung international härten — ✅ erledigt
- **Problem:** `REDACT_PATTERNS` in `extract_metadata.py` ist deutsch-zentriert. Kein
  Treffer für E-Mail-Adressen, Kreditkartennummern, internationale IBANs, generische
  lange Ziffernfolgen, Namen außerhalb „Herr/Frau …".
- **To-do:** Muster ergänzen (E-Mail; Kreditkarte inkl. optionalem Luhn-Check;
  IBAN generisch `[A-Z]{2}\d{2}…`; lange Ziffernblöcke). Synthetische Tests dazu.
- **Fertig, wenn:** Neue Muster + Tests; die bekannten Leak-Fälle abgedeckt oder sauber
  als „garbled" abgefangen.
- **Umgesetzt:** Muster für E-Mail, generische IBAN, Kreditkarte (mit Luhn-Check,
  Funktion als Replacement) und langen Ziffernblock-Fang-Rest ergänzt; Reihenfolge
  dokumentiert (spezifisch → generisch); `tests/test_redact.py` mit 11 synthetischen
  Tests (inkl. Regression: Datum überlebt Schwärzung, garbled → kein Ausschnitt).
  Alle Tests grün. „Namen außerhalb Herr/Frau" bewusst NICHT als Regex — zu
  fehleranfällig; stattdessen greift der Grundsatz „eindeutig sensibel = nicht
  extrahieren" aus P0.1 plus der `is_garbled`-Schutz.

## P1 — Doku/Implementierungs-Lücke schließen — ✅ ERLEDIGT

### 3. Idempotenz-Manifest wirklich bauen — ✅ erledigt
- **Problem:** `konfiguration.md` beschreibt ein `.para-manifest.jsonl`, aber kein Skript
  liest/schreibt es. Ein zweiter Lauf schlägt bereits Einsortiertes erneut vor.
- **To-do:** Beim Ausführen Hash + Zielpfad ins Manifest schreiben; vor dem Vorschlagen
  dagegen abgleichen.
- **Umgesetzt:** `scripts/manifest.py` mit Bibliotheks-API (`load_manifest`,
  `record_files`, `check_files`, `append_entries`) und CLI (`record`/`check`).
  `record` schreibt Hash + Zielpfad + Aktion + Zeitstempel als JSON-Zeile fort
  (idempotent — bekannte Hashes nicht doppelt); `check` erkennt bereits Einsortiertes
  am Inhalts-Hash (auch bei neuem Namen). In SKILL.md Schritt 5 verdrahtet. Kaputte
  Manifest-Zeilen werden toleriert (übersprungen). Tests grün.

### 4. Dedup gegen das Ziel-PARA-Home — ✅ erledigt
- **Problem:** `dedupe_scan.py` prüft nur *einen* Ordner. Es erkennt nicht automatisch,
  dass eine Download-Datei inhaltsgleich schon im PARA-Home liegt (wurde in der ersten
  Session von Hand gefunden).
- **To-do:** Option/Funktion, die ein oder mehrere Ziel-Homes als „bekannte Hashes"
  einliest und Quelldateien meldet, die dort schon existieren (Import verhindern).
- **Umgesetzt:** `dedupe_scan.py --against <PARA-Home>` (mehrfach angebbar) via
  `build_known_hashes` + `find_already_in_target`; neues Ausgabefeld `bereits_im_ziel`
  (Quelldatei + Fundstellen im Ziel). Hasht den ganzen Ziel-Baum; für den inkrementellen
  Fall verweist die Doku auf das günstigere Manifest (#3). Tests grün.

## P1 — Schicht-2-Automatik (war ohnehin offen) — ✅ ERLEDIGT

### 5. `triage.py` — lokaler Wächter-Kern (kein LLM) — ✅ erledigt
- Scan eines Ordners: Müll → Quarantäne, Hashen, Dedup gegen Home, Metadaten lokal
  ziehen, neue Dateien in eine Queue schreiben, Desktop-Notiz auslösen. Idempotent via
  Manifest (#3). Rein lokal, keine Cloud, kein automatisches Verschieben sensibler Dateien.
- **Umgesetzt:** `scripts/triage.py` orchestriert die bestehenden Bausteine
  (`manifest`, `dedupe_scan.build_known_hashes`, `extract_metadata.analyze`), dupliziert
  keine Logik. Nur eindeutiger Müll wird automatisch (reversibel) nach `_Papierkorb/`
  verschoben; **Inhaltsdateien nie** — die landen als JSON-Zeile in `.para-triage-queue.jsonl`.
  Trockenlauf als Standard, `--apply` führt aus, `--notify` löst plattform-erkennend eine
  Desktop-Notiz aus. Idempotent (Manifest-Hash + Queue-Hash). Quarantäne-Bewegungen gehen
  ins CSV-Protokoll → von `undo_last_run.py` (#7) zurücknehmbar. `tests/test_triage.py`
  (13 Tests, inkl. Undo-Integration) + CLI-Smoke-Test grün. In SKILL.md dokumentiert.

### 6. Wächter-Vorlagen (plattform-erkennend, als Assets, NICHT geladen) — ✅ erledigt
- macOS `launchd` (WatchPaths), Windows Task Scheduler / Ordner-Watcher, Linux
  systemd-path/inotify. Klar getrennt, optional, mit Install-Hinweis.
- **Umgesetzt:** `assets/` mit `launchd/…watch.plist` (WatchPaths, plutil-validiert),
  `systemd/…​.path` + `…​.service` (inotify-Trigger), `windows/register-task.ps1`
  (Task Scheduler) und `assets/README.md` (Platzhalter-Tabelle, Plattform-Erkennung,
  Install/Deinstallation, Sicherheitshinweise). Einheitliche `__TOKEN__`-Platzhalter
  (XML-sicher), nichts wird vom Skill selbst geladen/gestartet.

### 7. `undo_last_run.py` — ✅ erledigt
- Liest das CSV-Protokoll und macht die Moves des letzten Laufs rückgängig.
- **Umgesetzt:** `scripts/undo_last_run.py` liest `.para-dateiorganisation-log-<datum>.csv`
  und kehrt jede Zeile `neu → alt` um — aktions-agnostisch (Umbenennung/Verschiebung/
  Quarantäne gleich). Standard = **Trockenlauf**, `--apply` führt aus, `--tag N` grenzt
  auf die letzten N Aktionen ein. Überschreibt nie ein wieder existierendes `alt`, meldet
  fehlende Quellen statt zu crashen, arbeitet Zeilen rückwärts ab und **simuliert
  Zwischenzustände** (verkettete Moves a→b→c lösen sich korrekt auf). `tests/test_undo.py`
  (9 Tests) + CLI-Smoke-Test grün. In SKILL.md Schritt 6 verdrahtet.

## P2 — Qualität & Robustheit

### 8. Kürzel-Erkennung verbessern — ✅ erledigt
- Aktuell naiver Teilstring in Dict-Reihenfolge (Doc mit „Rechnung" *und* „Vertrag" ist
  reihenfolgeabhängig). Besser: Wortgrenzen, „spezifischstes/häufigstes Kürzel gewinnt",
  Mehrdeutigkeit aktiv melden. (`kuerzel_quelle` entschärft nur, behebt nicht.)
- **Umgesetzt:** `find_kuerzel` neu — Wortgrenzen-Matching (`(?<!\w)…(?!\w)`, umlaut-/
  unicode-fest, kein Teiltreffer), Gewinner nach **Trefferzahl → Spezifität (längere
  Variante) → Reihenfolge** (deterministisch), parenthetische Qualifizierer werden
  gestutzt (`_kuerzel_variants`). Weitere Fundstellen kommen als `kuerzel_alternativen`
  zurück; `analyze` (Text **und** Bild) hängt bei Mehrdeutigkeit eine Warnung an und
  behält die Prüfpflicht bei. Beide Aufrufer (`extract_metadata`, `extract_image_metadata`)
  + Triage-Queue-Feld mitgezogen. `tests/test_kuerzel.py` (11 Tests) grün, 52 gesamt.

### 9. Cross-Platform wirklich testen — ✅ ehrlich dokumentiert (nicht voll verifiziert)
- Windows/Linux-Pfade (Papierkorb etc.) sind entworfen, aber nur auf macOS ausgeführt.
  Entweder testen — oder Claim ehrlich auf „ausgelegt für alle, verifiziert auf macOS".
- **Umgesetzt (Variante 2, ehrlicher Claim):** Da diese Umgebung nur macOS (Darwin) ist,
  lässt sich Linux/Windows hier nicht *echt* verifizieren. Deshalb expliziter
  „Verifikationsstand (ehrlich)"-Absatz in `SKILL.md` (beim Plattform-Hinweis) **und**
  in `assets/README.md`: plattformabhängige Teile (OS-Papierkorb, `--notify`, Wächter-
  Vorlagen) sind für alle drei OS ausgelegt, aber nur auf macOS ausgeführt; auf
  Linux/Windows erst Trockenlauf. Der portable Standardweg (Quarantäne-Ordner) bleibt der
  OS-unabhängige, überall sichere Default. **Echtes Ausführen auf Linux/Windows bleibt
  offen** — nur auf entsprechender Hardware/CI machbar.

### 10. Eval-Harness (skill-creator) — ✅ erledigt (Track A; Track B optional/additiv)
- ~15–20 Testfälle für Trigger-Genauigkeit + Qualität; quantitativ messen statt „an einem
  Ordner erprobt".
- **Umgesetzt:** `eval/run_eval.py` mit zwei Tracks über einen inline-Fall-Korpus
  (`eval/cases/*`, zur Laufzeit in `tempfile` materialisiert — synthetisch, rerun-stabil,
  keine Logik-Duplizierung, ruft die echten Skript-APIs). **Track A** (deterministisch,
  CI-tauglich, kein LLM): 29 Prüfungen über ~13 Fälle — Datum, Kürzel, Konfidenz,
  Mehrdeutigkeit, **Schwärzungs-Leak-Rate**, garbled-Fang, exakte/near-Duplikate,
  „bereits im Ziel", Triage-Klassifikation. Scorecard + Exit-Code; harte Gates
  (Leak-frei / garbled / exakte-Precision = 100 %). `--prove-gate` beweist, dass die
  Leak-Erkennung feuert; ein Leck macht den ganzen Runner rot (verifiziert). **Track B**
  (Trigger-Precision/-Recall + PARA-Kategorie via Anthropic-Judge) läuft nur mit
  `ANTHROPIC_API_KEY`, sonst sauberes Überspringen mit Vermerk (kein stiller Ausfall).
  `eval/README.md` erklärt Ausführen, Kennzahlen und „neuen Fall hinzufügen".
  `python3 eval/run_eval.py --track a` → grün, Exit 0.

### 11. Kleinigkeiten — ✅ erledigt
- `extract_metadata.py` liest nur die ersten 3 PDF-Seiten (Datum auf späterer Seite geht
  verloren) → konfigurierbar/Fallback.
- Gebündelte Tests unter `tests/` mit synthetischen Fixtures.
- OCR-Sprache (`lang="deu+eng"`) konfigurierbar machen.
- **Umgesetzt:** PDF-Seiten via `PARA_PDF_MAX_PAGES` (+ `max_pages`-Param), DOCX-Absätze
  via `PARA_DOCX_MAX_PARAGRAPHS`, robuste `_int_env`-Auswertung (Müll/<1 → Default);
  OCR-Sprache via `PARA_OCR_LANG` + CLI `--lang` in `extract_image_metadata.py`.
  Gebündelter Runner `tests/run_all.py` (unittest-Discovery, Exit-Code). `tests/test_config.py`
  (9 Tests). **Gesamt jetzt 61 Tests**, alle grün.

## Getrennt: persönliche (nicht-Skill-) Aufgaben
Diese betreffen die konkrete Maschine des Erst-Nutzers, nicht das geteilte Skill:
- Erste Downloads-Ablage ins kanonische PARA-Home migrieren (in dessen Namenskonvention).
- Abweichende Konventionen mehrerer vorhandener PARA-Homes angleichen.
- Wächter aktiv laden.
