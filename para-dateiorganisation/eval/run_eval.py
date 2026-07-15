#!/usr/bin/env python3
"""Eval-Harness für das PARA-Dateiorganisations-Skill (ROADMAP #10).

Misst zwei Dinge **quantitativ** über einen Fall-Korpus, komplementär zu den
isolierten Unit-Tests unter ``tests/``:

* **Track A — deterministische Qualität (kein LLM, CI-tauglich).** Läuft die
  echten Skript-APIs (``extract_metadata.analyze``, ``dedupe_scan.*``,
  ``triage.run``, ``extract_metadata.redact``) gegen synthetische Fixtures mit
  bekanntem Ground-Truth. Vollständig headless, keine Cloud, keine echten Daten.
* **Track B — Trigger & PARA-Qualität (LLM-Judge, optional).** Nutzt einen
  Judge über die Anthropic-API, *falls* ``ANTHROPIC_API_KEY`` gesetzt ist; sonst
  wird Track B sauber übersprungen (kein stiller Ausfall).

Die wichtigste Kennzahl ist die **Schwärzungs-Leak-Rate**: sie muss 0 sein.
Überlebt eine IBAN/E-Mail/Kreditkarte die Schwärzung, reißt die harte Schwelle
und der Runner endet mit Exit-Code ≠ 0.

    python3 eval/run_eval.py --track a        # Kern, immer lauffähig
    python3 eval/run_eval.py --track all      # + LLM-Judge (braucht API-Key)
    python3 eval/run_eval.py --prove-gate     # beweist, dass die Leak-Gate feuert
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.request

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(EVAL_DIR, "..", "scripts")
CASES_DIR = os.path.join(EVAL_DIR, "cases")
sys.path.insert(0, SCRIPTS_DIR)

import dedupe_scan  # noqa: E402
import extract_metadata  # noqa: E402
import triage  # noqa: E402

# Metrik -> (Schwelle, hart). Harte Schwellen sind Gates: Bruch = sofort rot.
# Weiche Schwellen sollen bei sauber konstruierten Fixtures ohnehin 100 % sein;
# ein Bruch signalisiert eine echte Regression im jeweiligen Skript.
THRESHOLDS = {
    "schwaerzung_leak_frei":   (1.00, True),
    "datum_korrekt":           (0.90, False),
    "kuerzel_korrekt":         (0.85, False),
    "confidence_korrekt":      (0.90, False),
    "garbled_gefangen":        (1.00, True),
    "mehrdeutigkeit_gemeldet": (1.00, False),
    "exakte_dup_precision":    (1.00, True),
    "near_dup_erkannt":        (1.00, False),
    "bereits_im_ziel_erkannt": (1.00, False),
    "triage_klassifikation":   (0.95, False),
    # Track B (nur mit API-Key)
    "trigger_precision":       (0.90, False),
    "trigger_recall":          (0.90, False),
    "para_kategorie_korrekt":  (0.75, False),
}

TRACK_A_METRIKEN = [m for m in THRESHOLDS if not m.startswith(("trigger_", "para_"))]


class Scorecard:
    """Sammelt Treffer/Gesamt pro Metrik plus die Fehldetails."""

    def __init__(self):
        self.metriken = {}   # name -> {"hits": int, "total": int}
        self.fehler = []     # menschenlesbare Fehlschlag-Beschreibungen

    def add(self, name, ok, detail=""):
        m = self.metriken.setdefault(name, {"hits": 0, "total": 0})
        m["total"] += 1
        if ok:
            m["hits"] += 1
        else:
            self.fehler.append(f"[{name}] {detail}")

    def set_quote(self, name, hits, total):
        """Direkt eine Quote setzen (für Precision/Recall aus Track B)."""
        self.metriken[name] = {"hits": hits, "total": total}

    def rate(self, name):
        m = self.metriken.get(name)
        if not m or m["total"] == 0:
            return 1.0
        return m["hits"] / m["total"]


# --------------------------------------------------------------------------- #
# Fixtures / Laden
# --------------------------------------------------------------------------- #

def _load_jsonl(name):
    faelle = []
    with open(os.path.join(CASES_DIR, name), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                faelle.append(json.loads(line))
    return faelle


def _load_json(name):
    with open(os.path.join(CASES_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def _materialize(fixture, ordner):
    """Schreibt [{name, inhalt}] als echte Dateien nach ``ordner``; gibt Pfade."""
    os.makedirs(ordner, exist_ok=True)
    pfade = []
    for item in fixture:
        p = os.path.join(ordner, item["name"])
        with open(p, "w", encoding="utf-8") as f:
            f.write(item.get("inhalt", ""))
        pfade.append(p)
    return pfade


# --------------------------------------------------------------------------- #
# Track A
# --------------------------------------------------------------------------- #

def track_a_metadata(sc, kuerzel_map):
    faelle = _load_jsonl("metadata.jsonl")
    with tempfile.TemporaryDirectory() as d:
        for fall in faelle:
            p = os.path.join(d, fall["dateiname"])
            with open(p, "w", encoding="utf-8") as f:
                f.write(fall["inhalt"])
            res = extract_metadata.analyze(p, kuerzel_map)

            if fall["erwartet_garbled"]:
                ok = (res["redigierter_ausschnitt"] is None
                      and any("zerstückelt" in w for w in res["warnungen"]))
                sc.add("garbled_gefangen", ok,
                       f'{fall["id"]}: zerstückelter Text nicht als garbled erkannt')
                continue

            if fall["erwartetes_datum"] is not None:
                sc.add("datum_korrekt",
                       res["erkanntes_datum"] == fall["erwartetes_datum"],
                       f'{fall["id"]}: Datum {res["erkanntes_datum"]!r} != '
                       f'{fall["erwartetes_datum"]!r}')

            if fall["erwartetes_kuerzel"] is not None:
                sc.add("kuerzel_korrekt",
                       res["erkanntes_kuerzel"] == fall["erwartetes_kuerzel"],
                       f'{fall["id"]}: Kürzel {res["erkanntes_kuerzel"]!r} != '
                       f'{fall["erwartetes_kuerzel"]!r}')

            sc.add("confidence_korrekt",
                   res["confidence"] == fall["erwartete_confidence"],
                   f'{fall["id"]}: Konfidenz {res["confidence"]!r} != '
                   f'{fall["erwartete_confidence"]!r}')

            if fall.get("erwartet_alternativen"):
                alts = [a["kuerzel"] for a in (res.get("kuerzel_alternativen") or [])]
                sc.add("mehrdeutigkeit_gemeldet",
                       all(x in alts for x in fall["erwartet_alternativen"]),
                       f'{fall["id"]}: Alternativen {alts} decken '
                       f'{fall["erwartet_alternativen"]} nicht ab')


def _leak_pruefen(inhalt, verboten):
    """Gibt die Teilstrings zurück, die die Schwärzung überlebt haben."""
    geschwaerzt = extract_metadata.redact(inhalt)
    return [v for v in verboten if v in geschwaerzt]


def track_a_redaction(sc):
    faelle = _load_jsonl("redaction.jsonl")
    for fall in faelle:
        lecks = _leak_pruefen(fall["inhalt"], fall["darf_nicht_enthalten"])
        for v in fall["darf_nicht_enthalten"]:
            sc.add("schwaerzung_leak_frei", v not in lecks,
                   f'{fall["id"]}: "{v}" überlebte die Schwärzung')


def track_a_dedupe(sc):
    faelle = _load_json("dedupe.json")
    for fall in faelle:
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "src")
            pfade = _materialize(fall["fixture"], src)
            warnings = []
            file_hashes = dedupe_scan.hash_all(pfade, warnings)

            if "erwartet_exakte_gruppen" in fall:
                groups = dedupe_scan.find_exact_duplicates(file_hashes)
                sc.add("exakte_dup_precision",
                       len(groups) == fall["erwartet_exakte_gruppen"],
                       f'{fall["id"]}: {len(groups)} exakte Gruppen '
                       f'(erwartet {fall["erwartet_exakte_gruppen"]})')
                if "erwartet_behalten" in fall and groups:
                    behalten = os.path.basename(groups[0]["empfehlung_behalten"])
                    sc.add("exakte_dup_precision",
                           behalten == fall["erwartet_behalten"],
                           f'{fall["id"]}: behalten {behalten!r} != '
                           f'{fall["erwartet_behalten"]!r}')

            if "erwartet_near_gruppen" in fall:
                exact_groups = dedupe_scan.find_exact_duplicates(file_hashes)
                redundant = {p for g in exact_groups for p in g["files"]
                             if p != g["empfehlung_behalten"]}
                near = dedupe_scan.find_near_duplicates(pfade, redundant, warnings)
                sc.add("near_dup_erkannt",
                       len(near) == fall["erwartet_near_gruppen"],
                       f'{fall["id"]}: {len(near)} near-Gruppen '
                       f'(erwartet {fall["erwartet_near_gruppen"]})')

            if "erwartet_bereits_im_ziel" in fall:
                home = os.path.join(d, "home")
                _materialize(fall["home"], home)
                known = dedupe_scan.build_known_hashes([home], True, warnings)
                treffer = dedupe_scan.find_already_in_target(file_hashes, known)
                sc.add("bereits_im_ziel_erkannt",
                       len(treffer) == fall["erwartet_bereits_im_ziel"],
                       f'{fall["id"]}: {len(treffer)} Treffer '
                       f'(erwartet {fall["erwartet_bereits_im_ziel"]})')


def track_a_triage(sc):
    faelle = _load_json("triage.json")
    for fall in faelle:
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "src")
            _materialize(fall["fixture"], src)
            home_dirs = None
            if fall.get("home"):
                home = os.path.join(d, "home")
                _materialize(fall["home"], home)
                home_dirs = [home]

            res = triage.run(
                sources=[src],
                quarantine_dir=os.path.join(src, "_Papierkorb"),
                log_path=os.path.join(src, ".para-eval-log.csv"),
                queue_path=os.path.join(src, ".para-triage-queue.jsonl"),
                home_dirs=home_dirs, apply=False, kuerzel_map=None,
            )
            muell = len(res["quarantaene"])
            inhalt = sum(1 for e in res["queue_neu"] if e["klasse"] == "inhalt")
            dublette = sum(1 for e in res["queue_neu"] if e["klasse"] == "dublette")

            sc.add("triage_klassifikation", muell == fall["erwartet_muell"],
                   f'{fall["id"]}: Müll {muell} != {fall["erwartet_muell"]}')
            sc.add("triage_klassifikation", inhalt == fall["erwartet_inhalt"],
                   f'{fall["id"]}: Inhalt {inhalt} != {fall["erwartet_inhalt"]}')
            sc.add("triage_klassifikation", dublette == fall["erwartet_dublette"],
                   f'{fall["id"]}: Dublette {dublette} != {fall["erwartet_dublette"]}')


def run_track_a(sc, kuerzel_map):
    track_a_metadata(sc, kuerzel_map)
    track_a_redaction(sc)
    track_a_dedupe(sc)
    track_a_triage(sc)


# --------------------------------------------------------------------------- #
# Track B (optional, LLM-Judge)
# --------------------------------------------------------------------------- #

def _judge(user_text, system, model=None):
    """Fragt den Judge; gibt Antworttext oder None (bei fehlendem Key/Fehler)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    model = model or os.environ.get("PARA_EVAL_JUDGE_MODEL", "claude-haiku-4-5-20251001")
    body = json.dumps({
        "model": model,
        "max_tokens": 16,
        "system": system,
        "messages": [{"role": "user", "content": user_text}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"content-type": "application/json", "x-api-key": key,
                 "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.load(r)
    except Exception as e:  # Netz/Auth/Rate-Limit -> sauber überspringen
        return f"__FEHLER__{e}"
    return "".join(b.get("text", "") for b in resp.get("content", [])).strip()


def track_b(sc):
    """Gibt einen Status-String zurück (ausgeführt / übersprungen + Grund)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "übersprungen — kein ANTHROPIC_API_KEY gesetzt (Track A bleibt maßgeblich)"

    trigger_system = (
        "Du entscheidest, ob ein Datei-Organisations-Skill zuständig ist. Das Skill "
        "räumt lokale Ordner auf, benennt Dateien nach Inhalt um, findet Duplikate und "
        "sortiert nach der PARA-Methode. Es ist NICHT zuständig für reines Programmieren, "
        "E-Mail-Verwaltung oder das inhaltliche Zusammenfassen einzelner Dokumente. "
        "Antworte NUR mit JA oder NEIN.")
    tp = fp = tn = fn = 0
    for fall in _load_jsonl("trigger.jsonl"):
        ans = _judge(fall["prompt"], trigger_system)
        if ans is None or ans.startswith("__FEHLER__"):
            return f"übersprungen — Judge nicht erreichbar ({ans})"
        getriggert = ans.upper().lstrip().startswith("JA")
        if fall["soll_triggern"] and getriggert:
            tp += 1
        elif fall["soll_triggern"] and not getriggert:
            fn += 1
        elif not fall["soll_triggern"] and getriggert:
            fp += 1
        else:
            tn += 1
    sc.set_quote("trigger_precision", tp, tp + fp)
    sc.set_quote("trigger_recall", tp, tp + fn)

    para_system = (
        "Ordne die Datei genau einer PARA-Kategorie zu: Projects (laufendes Vorhaben mit "
        "Ziel/Deadline), Areas (Dauerverantwortung ohne Enddatum), Resources "
        "(Referenzmaterial) oder Archives (abgeschlossen/inaktiv). "
        "Antworte NUR mit dem einen englischen Kategoriewort.")
    for fall in _load_jsonl("para.jsonl"):
        ans = _judge(f'Dateiname: {fall["dateiname"]}\nKontext: {fall["kontext"]}',
                     para_system)
        if ans is None or ans.startswith("__FEHLER__"):
            break
        ok = ans.strip().rstrip(".").lower().startswith(fall["erwartete_kategorie"].lower())
        sc.add("para_kategorie_korrekt", ok,
               f'{fall["id"]}: Judge {ans!r} != {fall["erwartete_kategorie"]!r}')
    return "ausgeführt"


# --------------------------------------------------------------------------- #
# Bewertung / Ausgabe
# --------------------------------------------------------------------------- #

def _bewerten(sc):
    """Gibt (overall_ok, zeilen) zurück. zeilen = Liste von Metrik-Dicts."""
    overall_ok = True
    zeilen = []
    for name, (schwelle, hart) in THRESHOLDS.items():
        if name not in sc.metriken:
            continue
        m = sc.metriken[name]
        rate = sc.rate(name)
        bestanden = rate >= schwelle
        if not bestanden:
            overall_ok = False
        zeilen.append({
            "metrik": name, "hits": m["hits"], "total": m["total"],
            "rate": rate, "schwelle": schwelle, "hart": hart, "bestanden": bestanden,
        })
    return overall_ok, zeilen


def _print_scorecard(zeilen, sc, b_status):
    print("\nPARA-Eval — Scorecard")
    print("=" * 64)
    print(f"{'Metrik':<26}{'Quote':>10}{'Schwelle':>10}{'Gate':>7}{'':>4}")
    print("-" * 64)
    for z in zeilen:
        gate = "hart" if z["hart"] else "weich"
        mark = "OK" if z["bestanden"] else "FAIL"
        quote = f'{z["hits"]}/{z["total"]}'
        print(f'{z["metrik"]:<26}{quote:>10}{z["schwelle"]*100:>9.0f}%{gate:>7}{mark:>5}')
    print("-" * 64)
    if b_status:
        print(f"Track B: {b_status}")
    if sc.fehler:
        print(f"\nFehlschläge ({len(sc.fehler)}):")
        for f in sc.fehler:
            print(f"  - {f}")


def prove_gate():
    """Beweist, dass die Leak-Erkennung feuert: ein absichtlich NICHT geschwärzter
    Wert muss als Leck erkannt werden. Erfolg -> Exit 0 (der Beweis gelang)."""
    inhalt = "Hallo Welt, dies ist ein harmloser Satz ohne echte Schwärz-Muster."
    verboten = ["Welt"]  # wird bewusst NICHT von REDACT_PATTERNS getroffen
    lecks = _leak_pruefen(inhalt, verboten)
    if lecks:
        print(f"GATE WIRKSAM: absichtliches Leck erkannt ({lecks}) — bei einem echten "
              "PII-Leak würde der Runner rot (Exit ≠ 0).")
        return 0
    print("GATE DEFEKT: absichtliches Leck wurde NICHT erkannt.")
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--track", choices=["a", "b", "all"], default="a",
                    help="a = deterministisch (Standard), b = LLM-Judge, all = beide")
    ap.add_argument("--json", action="store_true", help="Scorecard als JSON")
    ap.add_argument("--prove-gate", action="store_true",
                    help="Beweist, dass die Schwärzungs-Leak-Gate feuert, dann Ende")
    args = ap.parse_args()

    if args.prove_gate:
        sys.exit(prove_gate())

    sc = Scorecard()
    b_status = None
    kuerzel_map = extract_metadata.load_kuerzel_map()

    try:
        if args.track in ("a", "all"):
            run_track_a(sc, kuerzel_map)
        if args.track in ("b", "all"):
            b_status = track_b(sc)
    except Exception as e:  # ein Track-Crash ist selbst ein Fehlschlag
        sc.add("harness_ohne_crash", False, f"Ausnahme: {e!r}")
        THRESHOLDS.setdefault("harness_ohne_crash", (1.00, True))

    overall_ok, zeilen = _bewerten(sc)

    if args.json:
        print(json.dumps({
            "track": args.track, "bestanden": overall_ok,
            "track_b": b_status, "metriken": zeilen, "fehler": sc.fehler,
        }, indent=2, ensure_ascii=False))
    else:
        _print_scorecard(zeilen, sc, b_status)
        a_faelle = sum(z["total"] for z in zeilen if z["metrik"] in TRACK_A_METRIKEN)
        print(f'\nErgebnis: {"BESTANDEN" if overall_ok else "DURCHGEFALLEN"} '
              f'({a_faelle} Track-A-Prüfungen)')

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
