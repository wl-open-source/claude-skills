#!/usr/bin/env python3
"""triage.py — lokaler Wächter-Kern für die PARA-Dateiorganisation (Schicht 2).

Ein rein lokaler Vor-Sortierer ohne LLM und ohne Cloud. Gedacht als Kern eines
Ordner-Wächters (siehe `assets/`-Vorlagen für launchd/systemd/Task Scheduler),
der bei neuen Dateien in einem Durchgangsordner (Downloads/Desktop) anläuft.

Was triage.py tut:

* **Müll → Quarantäne.** Eindeutige Wegwerf-Artefakte (Systemdateien wie
  `.DS_Store`/`Thumbs.db`, abgebrochene Downloads `*.crdownload`/`*.part`, Office-
  Sperrdateien `~$*`, 0-Byte-Dateien) werden in einen Quarantäne-Ordner
  `_Papierkorb/` verschoben — **nie** `rm`, immer reversibel.
* **Hashen + Dedup gegen das Home.** Jede Datei wird per SHA-256 identifiziert.
  Liegt derselbe Inhalt schon im PARA-Home (`--against-home`), wird die Datei als
  Dublette markiert (nicht gelöscht — nur ein Signal).
* **Lokale Metadaten.** Für Inhaltsdateien werden Datum/Dokumenttyp lokal und
  **geschwärzt** gezogen (`extract_metadata.analyze`). Nichts verlässt die Maschine.
* **Queue.** Neue Inhaltsdateien landen als JSON-Zeile in einer Queue, die später
  ein Mensch/LLM abarbeitet. triage.py **verschiebt Inhaltsdateien nie selbst** —
  das bleibt der bestätigten Einsortierung vorbehalten (kein Auto-Verschieben
  sensibler Dateien).
* **Desktop-Notiz.** Optional eine kurze Systembenachrichtigung („N neue Dateien").

Sicherheit / Disziplin:

* **Standard = Trockenlauf.** Ohne `--apply` wird nur berichtet, was passieren
  würde; nichts wird bewegt, keine Queue geschrieben, keine Notiz ausgelöst.
* **Idempotent.** Was schon im Manifest steht (`--manifest`), wird übersprungen;
  was schon in der Queue steht, wird nicht doppelt eingetragen. Wiederholte Läufe
  schlagen dasselbe nicht erneut vor.
* **Protokoll.** Jede Quarantäne-Bewegung wird ins CSV-Protokoll geschrieben
  (`<quelle>/.para-dateiorganisation-log-<datum>.csv`, `zeitstempel;aktion;alt;neu`),
  sodass `undo_last_run.py` auch Triage-Aktionen zurücknehmen kann.

Rein lokal, keine externen Pflicht-Abhängigkeiten (Metadaten-Extraktion nutzt
optionale Bibliotheken, fehlt sie, wird sauber gewarnt statt zu crashen).
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime

import dedupe_scan
import extract_metadata
import manifest

# Eindeutige Wegwerf-Artefakte (siehe SKILL.md Schritt 3).
JUNK_EXACT_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_SUFFIXES = (".tmp", ".crdownload", ".part", ".download", ".partial")
JUNK_PREFIXES = ("~$",)

# Eigene Zustandsdateien nie anfassen/einsortieren.
STATE_PREFIXES = (".para-",)
LOG_PREFIX = ".para-dateiorganisation-log-"
QUEUE_DEFAULT_NAME = ".para-triage-queue.jsonl"
QUARANTINE_DEFAULT_NAME = "_Papierkorb"
CSV_HEADER = "zeitstempel;aktion;alt;neu\n"


def is_junk(path):
    """(bool, grund) — ist die Datei ein eindeutiges Wegwerf-Artefakt?"""
    name = os.path.basename(path)
    if name in JUNK_EXACT_NAMES:
        return True, f"Systemdatei ({name})"
    if name.startswith(JUNK_PREFIXES):
        return True, "Office-Sperrdatei (~$)"
    if name.lower().endswith(JUNK_SUFFIXES):
        return True, "abgebrochener Download / Temp-Datei"
    try:
        if os.path.getsize(path) == 0:
            return True, "0-Byte-Datei (leer)"
    except OSError:
        pass
    return False, None


def is_state_file(path):
    name = os.path.basename(path)
    return name.startswith(STATE_PREFIXES) or name == ".para-ignore"


def unique_target(directory, name):
    """Kollisionssicheres Ziel in `directory` — nie überschreiben, Zähler anhängen."""
    ziel = os.path.join(directory, name)
    if not os.path.exists(ziel):
        return ziel
    stamm, endung = os.path.splitext(name)
    n = 1
    while True:
        kandidat = os.path.join(directory, f"{stamm} ({n}){endung}")
        if not os.path.exists(kandidat):
            return kandidat
        n += 1


def append_log(log_path, rows):
    """CSV-Protokollzeilen anhängen; Header nur, wenn die Datei neu ist."""
    if not rows:
        return
    neu = not os.path.isfile(log_path)
    with open(log_path, "a", encoding="utf-8") as f:
        if neu:
            f.write(CSV_HEADER)
        for zeitstempel, aktion, alt, ziel in rows:
            f.write(f"{zeitstempel};{aktion};{alt};{ziel}\n")


def load_queue_hashes(queue_path):
    """Hashes, die schon in der Queue stehen (Idempotenz). Fehlt sie -> leere Menge."""
    hashes = set()
    if not queue_path or not os.path.isfile(queue_path):
        return hashes
    with open(queue_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                eintrag = json.loads(line)
            except json.JSONDecodeError:
                continue
            h = eintrag.get("hash")
            if h:
                hashes.add(h)
    return hashes


def append_queue(queue_path, entries):
    if not entries:
        return
    parent = os.path.dirname(os.path.abspath(queue_path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(queue_path, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def send_notification(message):
    """Best-effort Desktop-Notiz je Plattform. Gibt eine Warnung zurück (str)
    oder None bei Erfolg — Fehler werden gemeldet, nicht verschluckt."""
    system = platform.system()
    try:
        if system == "Darwin":
            skript = f'display notification {json.dumps(message)} with title "PARA-Triage"'
            subprocess.run(["osascript", "-e", skript], check=True,
                           capture_output=True, timeout=10)
            return None
        if system == "Linux":
            subprocess.run(["notify-send", "PARA-Triage", message], check=True,
                           capture_output=True, timeout=10)
            return None
        if system == "Windows":
            ps = ("[reflection.assembly]::loadwithpartialname('System.Windows.Forms');"
                  "[System.Windows.Forms.MessageBox]::Show("
                  f"{json.dumps(message)},'PARA-Triage')")
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True,
                           capture_output=True, timeout=10)
            return None
        return f"Benachrichtigung auf {system} nicht unterstützt"
    except (OSError, subprocess.SubprocessError) as e:
        return f"Benachrichtigung fehlgeschlagen: {e}"


def _under(path, directory):
    if not directory:
        return False
    a = os.path.abspath(path)
    d = os.path.abspath(directory)
    return a == d or a.startswith(d + os.sep)


def run(sources, quarantine_dir, log_path, queue_path,
        manifest_path=None, home_dirs=None, apply=False, notify=False,
        kuerzel_map=None):
    """Kern-Ablauf ohne argparse — auch aus Tests direkt aufrufbar."""
    stamp = datetime.now().isoformat(timespec="seconds")
    warnungen = []

    manifest_hashes = set()
    if manifest_path:
        manifest_hashes = set(manifest.load_manifest(manifest_path).keys())

    home_hashes = {}
    if home_dirs:
        home_hashes = dedupe_scan.build_known_hashes(home_dirs, True, warnungen)

    queue_seen = load_queue_hashes(queue_path)

    quarantaene = []     # geplante/erledigte Müll-Bewegungen
    queue_neu = []       # neue Queue-Einträge (Inhaltsdateien)
    uebersprungen = []   # bereits verarbeitet / schon in Queue
    log_rows = []

    skipped_project_dirs = []
    for source in sources:
        if not os.path.isdir(source):
            warnungen.append(f"Kein Verzeichnis: {source}")
            continue
        for path in dedupe_scan.iter_files(source, True, skipped_project_dirs):
            if _under(path, quarantine_dir) or is_state_file(path):
                continue
            try:
                digest = manifest.sha256_of(path)
            except OSError as e:
                warnungen.append(f"Konnte nicht gehasht werden: {path} ({e})")
                continue

            if digest in manifest_hashes:
                uebersprungen.append({"quelle": path, "grund": "bereits einsortiert (Manifest)"})
                continue

            junk, grund = is_junk(path)
            if junk:
                ziel = unique_target(quarantine_dir, os.path.basename(path))
                eintrag = {"quelle": path, "ziel": ziel, "grund": grund}
                if apply:
                    os.makedirs(quarantine_dir, exist_ok=True)
                    ziel = unique_target(quarantine_dir, os.path.basename(path))
                    shutil.move(path, ziel)
                    eintrag["ziel"] = ziel
                    log_rows.append((stamp, "quarantäne", path, ziel))
                quarantaene.append(eintrag)
                continue

            if digest in queue_seen:
                uebersprungen.append({"quelle": path, "grund": "bereits in Queue"})
                continue

            dublette = digest in home_hashes
            entry = {
                "hash": digest,
                "quelle": path,
                "groesse": os.path.getsize(path),
                "klasse": "dublette" if dublette else "inhalt",
                "bereits_im_ziel": dublette,
                "ziel_treffer": home_hashes.get(digest, []) if dublette else [],
                "zeitstempel": stamp,
            }
            if kuerzel_map is not None:
                meta = extract_metadata.analyze(path, kuerzel_map)
                for feld in ("confidence", "erkanntes_datum", "erkanntes_kuerzel",
                             "kuerzel_alternativen", "absender_hinweis",
                             "vorschlag_dateiname", "redigierter_ausschnitt", "warnungen"):
                    entry[feld] = meta.get(feld)
            queue_neu.append(entry)
            queue_seen.add(digest)

    notiz = None
    if apply:
        append_log(log_path, log_rows)
        append_queue(queue_path, queue_neu)
        if notify and (queue_neu or quarantaene):
            msg = f"{len(queue_neu)} neue Datei(en), {len(quarantaene)} in Quarantäne"
            notiz = send_notification(msg)
            if notiz:
                warnungen.append(notiz)

    return {
        "quarantaene": quarantaene,
        "queue_neu": queue_neu,
        "uebersprungen": uebersprungen,
        "warnungen": warnungen,
        "log": log_path,
        "queue": queue_path,
    }


def _print_text(ergebnis, apply):
    modus = "AUSGEFÜHRT" if apply else "Trockenlauf (mit --apply ausführen)"
    print(f"PARA-Triage — {modus}")
    print(f"  Müll → Quarantäne: {len(ergebnis['quarantaene'])}")
    for e in ergebnis["quarantaene"]:
        print(f"    {e['quelle']}  ({e['grund']})")
    print(f"  Neu in Queue: {len(ergebnis['queue_neu'])}")
    for e in ergebnis["queue_neu"]:
        marker = " [DUBLETTE im Home]" if e.get("bereits_im_ziel") else ""
        vorschlag = e.get("vorschlag_dateiname") or "(kein sicherer Vorschlag)"
        print(f"    {e['quelle']} -> {vorschlag}{marker}")
    print(f"  Übersprungen (idempotent): {len(ergebnis['uebersprungen'])}")
    for w in ergebnis["warnungen"]:
        print(f"  Hinweis: {w}")
    if apply:
        print(f"  Queue: {ergebnis['queue']}")
        print(f"  Protokoll: {ergebnis['log']}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("quellen", nargs="+", help="Zu überwachende Ordner (Downloads/Desktop)")
    parser.add_argument("--quarantaene", help="Quarantäne-Ordner "
                        f"(Standard: <erste Quelle>/{QUARANTINE_DEFAULT_NAME})")
    parser.add_argument("--queue", help="Pfad zur Queue-Datei "
                        f"(Standard: <erste Quelle>/{QUEUE_DEFAULT_NAME})")
    parser.add_argument("--log", help="Pfad zum CSV-Protokoll "
                        "(Standard: <erste Quelle>/.para-dateiorganisation-log-<datum>.csv)")
    parser.add_argument("--manifest", help="Idempotenz-Manifest (bereits Einsortiertes überspringen)")
    parser.add_argument("--against-home", action="append", default=[], metavar="DIR",
                        help="PARA-Home für Dedup-Abgleich (mehrfach angebbar)")
    parser.add_argument("--no-metadata", action="store_true",
                        help="Keine lokale Metadaten-Extraktion (nur klassifizieren)")
    parser.add_argument("--notify", action="store_true", help="Desktop-Notiz auslösen (nur mit --apply)")
    parser.add_argument("--apply", action="store_true", help="Tatsächlich ausführen (ohne: Trockenlauf)")
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    args = parser.parse_args()

    erste = args.quellen[0]
    quarantine_dir = args.quarantaene or os.path.join(erste, QUARANTINE_DEFAULT_NAME)
    queue_path = args.queue or os.path.join(erste, QUEUE_DEFAULT_NAME)
    datum = datetime.now().strftime("%Y-%m-%d")
    log_path = args.log or os.path.join(erste, f"{LOG_PREFIX}{datum}.csv")

    kuerzel_map = None if args.no_metadata else extract_metadata.load_kuerzel_map()

    ergebnis = run(
        sources=args.quellen, quarantine_dir=quarantine_dir, log_path=log_path,
        queue_path=queue_path, manifest_path=args.manifest,
        home_dirs=args.against_home or None, apply=args.apply, notify=args.notify,
        kuerzel_map=kuerzel_map,
    )

    if args.json:
        print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    else:
        _print_text(ergebnis, args.apply)


if __name__ == "__main__":
    main()
