# Eval-Harness (ROADMAP #10)

Misst **quantitativ über einen Fall-Korpus**, ob das Skill die richtigen
Ergebnisse liefert — komplementär zu den isolierten Unit-Tests unter `../tests/`.
Die Unit-Tests prüfen Funktionen einzeln; der Harness prüft das Zusammenspiel
end-to-end gegen bekannten Ground-Truth und scored es.

## Ausführen

```bash
# Kern — deterministisch, kein LLM, keine Cloud, immer lauffähig:
python3 eval/run_eval.py --track a

# + LLM-Judge (Trigger-Genauigkeit + PARA-Kategorie); braucht ANTHROPIC_API_KEY:
python3 eval/run_eval.py --track all

# Beweist, dass die Schwärzungs-Leak-Gate feuert (Selbsttest):
python3 eval/run_eval.py --prove-gate

# Maschinenlesbar:
python3 eval/run_eval.py --track a --json
```

**Exit-Code 0** = alle Schwellen gehalten. **≠ 0** = mindestens eine Schwelle
gerissen → für CI direkt verwendbar. Track A braucht keine externen Pflicht-
Abhängigkeiten; die reinen Text-Fixtures decken alle Pfade ab (auch den
„garbled"-Pfad, den `analyze` auch auf `.txt` durchläuft).

## Zwei Tracks

| Track | Was | Automatisierbar |
|---|---|---|
| **A** | Deterministische Qualität: Datum, Kürzel, Konfidenz, **Schwärzung**, Duplikate, Triage-Klassifikation | vollständig headless, CI-tauglich |
| **B** | Trigger-Genauigkeit + PARA-Kategorie (modellgetrieben) | nur mit `ANTHROPIC_API_KEY`, sonst sauber übersprungen |

Track B überspringt ohne Key **mit Vermerk** (kein stiller Ausfall). So bleibt A
immer grün-lauffähig; B ist additiv. Judge-Modell via `PARA_EVAL_JUDGE_MODEL`
(Default: ein Haiku-Modell — für eine Ja/Nein- bzw. Ein-Wort-Entscheidung genug).

## Kennzahlen & Schwellen

| Metrik | Track | Schwelle | Gate |
|---|---|---|---|
| `schwaerzung_leak_frei` (PII überlebt Schwärzung) | A | 100 % | **hart** |
| `garbled_gefangen` (zerstückeltes PDF → kein Ausschnitt) | A | 100 % | **hart** |
| `exakte_dup_precision` | A | 100 % | **hart** |
| `datum_korrekt` | A | ≥ 90 % | weich |
| `confidence_korrekt` | A | ≥ 90 % | weich |
| `kuerzel_korrekt` | A | ≥ 85 % | weich |
| `mehrdeutigkeit_gemeldet` | A | 100 % | weich |
| `near_dup_erkannt` | A | 100 % | weich |
| `bereits_im_ziel_erkannt` | A | 100 % | weich |
| `triage_klassifikation` | A | ≥ 95 % | weich |
| `trigger_precision` / `trigger_recall` | B | ≥ 90 % | weich |
| `para_kategorie_korrekt` | B | ≥ 75 % | weich |

**Harte** Gate reißt → Runner rot, egal wie der Rest steht. Die wichtigste ist
`schwaerzung_leak_frei`: eine überlebende IBAN/E-Mail/Kreditkarte lässt den Eval
scheitern. `--prove-gate` zeigt, dass diese Erkennung tatsächlich feuert.

## Aufbau

```
eval/
  run_eval.py          Harness: Tracks, Scoring, Scorecard, Exit-Code
  cases/
    metadata.jsonl     {dateiname, inhalt, erwartetes_datum, erwartetes_kuerzel,
                        erwartete_confidence, erwartet_garbled, erwartet_alternativen}
    redaction.jsonl    {dateiname, inhalt, darf_nicht_enthalten: [...]}   # Leak-Test
    dedupe.json        [{fixture:[{name,inhalt}], home?, erwartet_exakte_gruppen|
                          erwartet_near_gruppen|erwartet_bereits_im_ziel, ...}]
    triage.json        [{fixture, home?, erwartet_muell, erwartet_inhalt, erwartet_dublette}]
    trigger.jsonl      {prompt, soll_triggern}                            # Track B
    para.jsonl         {dateiname, kontext, erwartete_kategorie}          # Track B
```

Die Fixtures stehen **inline** in den Fall-Dateien (Text) und werden zur Laufzeit
in `tempfile`-Ordner materialisiert — eine Quelle der Wahrheit, keine verwaisten
Binär-Dateien, rerun-stabil. Alle Werte sind synthetisch/erfunden (keine echten
PII; die 4242-Testkarte ist Luhn-gültig, aber keine echte Karte).

## Neuen Fall hinzufügen

1. Passende Zeile/Objekt in die richtige `cases/`-Datei eintragen (Schema oben).
   Für Metadaten/Redaction: `inhalt` als Text. Für Dedup/Triage: `fixture` als
   Liste `{name, inhalt}`, optional `home` für den Ziel-Home-Abgleich.
2. Ground-Truth-Felder setzen (was das Skript liefern *soll*).
3. `python3 eval/run_eval.py --track a` laufen lassen — der neue Fall wird
   automatisch mitgezählt; keine Änderung an `run_eval.py` nötig, solange das Feld-
   schema passt. Neue Metriken brauchen einen Eintrag in `THRESHOLDS`.

## Verhältnis zu `tests/`

`tests/` = 61 Unit-Tests (Funktions-Ebene, `python3 tests/run_all.py`).
`eval/` = end-to-end Qualitäts-Messung über einen Korpus mit Schwellen und
Exit-Code. Beide ergänzen sich; der Eval ersetzt die Unit-Tests nicht.
