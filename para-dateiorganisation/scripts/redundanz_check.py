#!/usr/bin/env python3
"""Redundanz-Loop beim Ablegen.

Prüft einen Ziel-Ablageordner **inhaltlich** (SHA-256, nicht nur nach Namen) auf
Redundanz und reduziert **exakte** Dubletten auf die *neueste* Kopie. Die
Verlierer wandern **reversibel** in die Quarantäne (`_Papierkorb/`, nie `rm`),
jede Bewegung wird ins CSV-Protokoll geschrieben (`zeitstempel;aktion;alt;neu`,
damit `undo_last_run.py` sie zurücknehmen kann).

**Near-Duplicates** (ähnlicher, aber NICHT identischer Inhalt) werden nur
**gemeldet**, nie automatisch entfernt — dort ist „neuere behalten" ein
schlechtes Kriterium (ein erneuter Download kann neuer, aber schlechter sein;
manchmal will man beide Stände).

Die Prüfung läuft als **Loop bis zum Fixpunkt** (ein Durchlauf, der nichts Neues
mehr findet), mit **Sicherheits-Cap** (Standard 3 Durchläufe) — nicht als feste
Zahl von Wiederholungen, weil eine Hash-Deduplizierung deterministisch ist und
ein Loop nur dann etwas bringt, wenn sich der Zustand zwischen den Durchläufen
ändert.

**Trockenlauf ist Standard**; erst `--apply` bewegt Dateien.

Gedacht als Ablage-Schritt: nachdem neue Dateien in einen Zielordner gelegt
wurden, hier drüberlaufen lassen, damit im Ordner nichts inhaltlich Doppeltes
liegen bleibt.

Beispiel:
    python3 redundanz_check.py <zielordner>                       # Trockenlauf
    python3 redundanz_check.py <zielordner> --apply \\
        --quarantaene <PARA-Home>/_Papierkorb/aufraeumen-<datum> \\
        --log <PARA-Home>/.para-dateiorganisation-log-<datum>.csv
"""
import argparse
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dedupe_scan as ds  # Wiederverwendung: iter_files, hash_all, find_exact_duplicates, find_near_duplicates

QUARANTINE_DEFAULT_NAME = "_Papierkorb"
LOG_PREFIX = ".para-dateiorganisation-log-"
CSV_HEADER = "zeitstempel;aktion;alt;neu\n"
DEFAULT_MAX_PASSES = 3
ACTION = "quarantaene-redundanz"


def timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def append_log(log_path, rows):
    """rows: Liste (aktion, alt, neu). Header nur schreiben, wenn Datei neu ist —
    sonst würde bei mehreren Läufen am selben Tag ein zweiter Header die CSV
    zerbrechen."""
    if not rows:
        return
    ist_neu = not os.path.exists(log_path)
    with open(log_path, "a", encoding="utf-8") as f:
        if ist_neu:
            f.write(CSV_HEADER)
        for aktion, alt, ziel in rows:
            f.write(f"{timestamp()};{aktion};{alt};{ziel}\n")


def unique_target(quarantine_dir, rel_path):
    """Zielpfad in der Quarantäne unter Beibehaltung des relativen Pfads;
    bei Kollision Zähler anhängen, nie überschreiben."""
    ziel = os.path.join(quarantine_dir, rel_path)
    os.makedirs(os.path.dirname(ziel) or ".", exist_ok=True)
    if not os.path.exists(ziel):
        return ziel
    basis, ext = os.path.splitext(ziel)
    n = 1
    while os.path.exists(f"{basis}_{n}{ext}"):
        n += 1
    return f"{basis}_{n}{ext}"


def newest(paths):
    """Von mehreren inhaltlich identischen Dateien die mit der jüngsten mtime
    behalten (Nutzerwunsch: nach Aktualität)."""
    return max(paths, key=lambda p: os.path.getmtime(p))


def scan_files(target, quarantine_dir, log_path, warnings):
    """Alle Dateien unter `target`, aber ohne die Quarantäne selbst und ohne die
    Log-Datei — sonst würde der Scan seine eigene Ausgabe wieder einlesen."""
    q_abs = os.path.abspath(quarantine_dir)
    log_abs = os.path.abspath(log_path)
    files = []
    for f in ds.iter_files(os.path.abspath(target), skip_project_dirs=True, skipped_project_dirs=[]):
        fa = os.path.abspath(f)
        if fa == log_abs:
            continue
        if fa == q_abs or fa.startswith(q_abs + os.sep):
            continue
        files.append(f)
    return files


def one_pass(target, quarantine_dir, log_path, warnings):
    """Ein Durchlauf: exakte Dubletten finden, pro Gruppe die neueste behalten,
    der Rest sind Verlierer. Bewegt nichts — nur Ermittlung."""
    files = scan_files(target, quarantine_dir, log_path, warnings)
    file_hashes = ds.hash_all(files, warnings)
    exact_groups = ds.find_exact_duplicates(file_hashes)
    losers = []
    report = []
    for g in exact_groups:
        keep = newest(g["files"])
        gruppe_verlierer = [p for p in g["files"] if p != keep]
        losers.extend(gruppe_verlierer)
        report.append({"hash": g["hash"], "behalten": keep, "verlierer": gruppe_verlierer})
    return losers, report


def run(target, apply_changes, quarantine_dir, log_path, max_passes):
    target = os.path.abspath(target)
    warnings = []
    passes = []
    quarantined_total = []
    stabil = False

    for i in range(1, max_passes + 1):
        losers, report = one_pass(target, quarantine_dir, log_path, warnings)
        if not losers:
            stabil = True
            passes.append({"durchlauf": i, "exakte_gruppen": report, "aktion": "keine (stabil)"})
            break

        bewegungen = []
        log_rows = []
        for loser in losers:
            if apply_changes:
                rel = os.path.relpath(loser, target)
                ziel = unique_target(quarantine_dir, rel)
                shutil.move(loser, ziel)
                bewegungen.append({"alt": loser, "quarantaene": ziel})
                log_rows.append((ACTION, loser, ziel))
            else:
                bewegungen.append({"alt": loser, "quarantaene": "(Trockenlauf)"})

        if apply_changes:
            append_log(log_path, log_rows)
            quarantined_total.extend(bewegungen)

        passes.append({
            "durchlauf": i,
            "exakte_gruppen": report,
            "aktion": "verschoben" if apply_changes else "wuerde-verschieben",
            "bewegungen": bewegungen,
        })

        if not apply_changes:
            # Ohne --apply ändert sich nichts am Zustand -> ein weiterer Durchlauf
            # fände exakt dasselbe. Nach einem Durchlauf stoppen (Fixpunkt-Logik
            # greift nur mit tatsächlichen Bewegungen).
            break

    # Near-Duplicates am Endzustand NUR melden, nie automatisch entfernen.
    files = scan_files(target, quarantine_dir, log_path, warnings)
    near = ds.find_near_duplicates(files, set(), warnings)

    return {
        "zielordner": target,
        "modus": "apply" if apply_changes else "trockenlauf",
        "stabil_erreicht": stabil,
        "durchlaeufe": passes,
        "quarantaene_gesamt": quarantined_total,
        "near_duplicates_nur_gemeldet": near,
        "warnings": warnings,
    }


def print_klartext(result):
    print(f"Zielordner: {result['zielordner']}  [{result['modus']}]")
    for p in result["durchlaeufe"]:
        print(f"\n— Durchlauf {p['durchlauf']} —")
        if not p["exakte_gruppen"]:
            print("  keine exakten Dubletten gefunden (stabil)")
        for g in p["exakte_gruppen"]:
            print(f"  Behalten (neueste): {g['behalten']}")
            for v in g["verlierer"]:
                marker = "(Trockenlauf) " if result["modus"] == "trockenlauf" else "-> Quarantäne "
                print(f"    Duplikat {marker}: {v}")
    near = result["near_duplicates_nur_gemeldet"]
    if near:
        print(f"\nNear-Duplicates (NUR gemeldet, nicht entfernt) — {len(near)} Gruppe(n):")
        for g in near:
            print(f"  ~ {g}")
    if result["warnings"]:
        print("\nWarnungen:")
        for w in result["warnings"]:
            print(f"  ! {w}")
    if result["modus"] == "trockenlauf":
        print("\nTrockenlauf — es wurde nichts bewegt. Mit --apply ausführen.")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="Zu prüfender Ziel-Ablageordner")
    parser.add_argument("--apply", action="store_true",
                        help="Änderungen ausführen (Standard: Trockenlauf)")
    parser.add_argument("--quarantaene", help="Quarantäne-Ordner "
                        "(Standard: <target>/_Papierkorb)")
    parser.add_argument("--log", help="CSV-Protokoll "
                        "(Standard: <target>/.para-dateiorganisation-log-<datum>.csv)")
    parser.add_argument("--max-passes", type=int, default=DEFAULT_MAX_PASSES,
                        help=f"Sicherheits-Cap für den Loop (Standard {DEFAULT_MAX_PASSES})")
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    args = parser.parse_args()

    if not os.path.isdir(args.target):
        parser.error(f"Kein Verzeichnis: {args.target}")

    datum = datetime.date.today().isoformat()
    quarantine_dir = args.quarantaene or os.path.join(os.path.abspath(args.target),
                                                      QUARANTINE_DEFAULT_NAME)
    log_path = args.log or os.path.join(os.path.abspath(args.target),
                                        f"{LOG_PREFIX}{datum}.csv")

    result = run(args.target, args.apply, quarantine_dir, log_path, args.max_passes)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_klartext(result)


if __name__ == "__main__":
    main()
