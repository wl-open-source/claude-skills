# Plan: Eval-Harness (ROADMAP #10)

Status: **geplant, noch nicht implementiert.** Dieses Dokument ist der Entwurf,
damit #10 in einer frischen Session ohne Kontextverlust startklar ist. Vor der
Umsetzung `/compact` bzw. Neustart (die Vorsession lief token-/kostenintensiv).

## Ziel

Zwei Dinge **quantitativ** messen statt „an einem Ordner erprobt":

1. **Trigger-Genauigkeit** — aktiviert das Skill bei den richtigen Prompts und
   *nicht* bei den falschen?
2. **Qualität** — liefern die Skripte + der PARA-Fluss die richtigen Ergebnisse
   (Datum, Kürzel, Dedup, Triage und vor allem **Schwärzung**)?

Komplementär zu den vorhandenen 61 Unit-Tests: die prüfen Funktionen isoliert,
der Harness misst **end-to-end + quantitativ über einen Fall-Korpus**.

## Verzeichnis-Aufbau

```
eval/
  PLAN.md                — dieses Dokument
  README.md              — Ausführen, Kennzahlen, neue Fälle hinzufügen (bei Umsetzung)
  run_eval.py            — Harness: läuft alle Tracks, druckt Scorecard, Exit-Code
  cases/
    trigger.jsonl        — {prompt, soll_triggern: bool, notiz}
    metadata.jsonl       — {fixture, erwartetes_datum, erwartetes_kuerzel, min_confidence}
    redaction.jsonl      — {fixture, darf_nicht_enthalten: [...]}   # Leak-Test
    dedupe.json          — {fixture_ordner, erwartete_exact_groups, erwartete_near, bereits_im_ziel}
    triage.json          — {fixture_ordner, erwartet_muell, erwartet_queue, erwartet_dublette}
  fixtures/              — synthetische Eingabedateien/-ordner (NUR Wegwerf-Daten)
```

## Zwei Tracks (getrennt, weil unterschiedlich automatisierbar)

**Track A — Deterministische Qualität (kein LLM, CI-tauglich).** Der Kern.
Läuft `extract_metadata.analyze`, `dedupe_scan.*`, `triage.run`, `find_kuerzel`
gegen Fixtures mit bekanntem Ground-Truth und scored automatisch. Vollständig
headless reproduzierbar, keine Cloud. Nutzt die vorhandenen Skript-APIs —
**keine Logik-Duplizierung**.

**Track B — Trigger & PARA-Qualität (LLM-Judge, optional).** Trigger-Entscheidung
und PARA-Kategorisierung sind modellgetrieben. Der Runner nutzt einen Judge
(Anthropic API), *falls* ein Key gesetzt ist; sonst überspringt er Track B sauber
mit Vermerk (kein stiller Ausfall). So bleibt A immer grün-lauffähig, B ist additiv.

## Kennzahlen & Schwellen (Vorschlag)

| Metrik | Track | Schwelle |
|---|---|---|
| **Schwärzung: Leak-Rate** (PII überlebt) | A | **0 %** (hart, blockierend) |
| Datums-Erkennung korrekt | A | ≥ 90 % |
| Kürzel korrekt (inkl. Mehrdeutigkeit gemeldet) | A | ≥ 85 % |
| `is_garbled` fängt zerstückelte PDFs | A | 100 % → kein Ausschnitt |
| Exakte Duplikate: Precision | A | 100 % |
| Triage-Klassifikation (Müll/Inhalt/Dublette) | A | ≥ 95 % |
| Trigger-Precision / -Recall | B | ≥ 90 % / ≥ 90 % |
| PARA-Kategorie plausibel (Judge-Rubrik 1–5) | B | Ø ≥ 4.0 |

Harte Schwelle = Runner-Exit-Code ≠ 0. Die **Leak-Rate=0** ist die wichtigste
Gate: eine überlebende IBAN/E-Mail/Kreditkarte lässt den Eval scheitern.

## Fall-Korpus (~18 Fälle)

- **Trigger (6):** 3 positiv („räum Downloads auf", „finde Duplikate",
  „bring Struktur rein") · 3 negativ (Nachbarthemen, die *nicht* triggern sollen,
  z.B. „schreib mir ein Python-Skript", „lösch meine Mails", „fasse dieses PDF zusammen").
- **Metadata (6):** ISO-Datum · DMY-Datum · eindeutiges Kürzel · **mehrdeutiges**
  Kürzel (RG+VTR, Alternativen gemeldet) · Garbled-PDF (→ kein Ausschnitt) ·
  kein Datum/Kürzel (→ low confidence).
- **Redaction-Leak (2):** Fixture mit IBAN+E-Mail+Kreditkarte → kein Klartextwert
  im Output · internationaler Fall (GB-IBAN).
- **Dedupe/Triage (4):** exakte Dublette · Near-Duplicate (v1/v2) · Quelle schon
  im Ziel-Home (`--against`) · Triage-Mix (Müll + Inhalt + Dublette in einem Ordner).

Fixtures für Garbled/PDF: bevorzugt collapse-resistente 2-Zeichen-Tokens
verwenden (siehe `tests/test_redact.py`), damit `collapse_letter_spacing` sie
nicht „repariert" und `is_garbled` verlässlich greift.

## Runner-Design

- `run_eval.py [--track a|b|all] [--json]` → pro Fall Pass/Fail + Metrik,
  am Ende Scorecard-Tabelle, **Exit-Code** ≠ 0 wenn eine harte Schwelle reißt.
- Rerun-stabil (nur Fixtures/`tempfile`), keine echten Daten, keine Cloud in Track A.
- Importiert die Skript-Module aus `../scripts` (gleiches sys.path-Muster wie die Tests).

## Reihenfolge der Umsetzung

1. **Track A vollständig** (Fixtures + Runner + Scoring + `eval/README.md`) —
   klar abgegrenzt, hoher Wert, besonders die Schwärzungs-Leak-Gate.
2. **Track B** als optionale zweite Stufe (Judge-Prompt + Rubrik + API-Key-Handling).

Damit ist #10 auch dann sinnvoll „fertig", wenn Track B (mangels Key/Zeit) ruht.

## Definition of Done

- `python3 eval/run_eval.py --track a` läuft grün, Exit-Code 0, ~14 A-Fälle.
- Leak-Rate-Gate nachweislich wirksam (ein absichtlich kaputter Fixture lässt ihn rot werden).
- `eval/README.md` erklärt Ausführen + „neuen Fall hinzufügen".
- ROADMAP #10 auf ✅ mit „Umgesetzt:"-Notiz; ggf. Track B als Rest vermerkt.
