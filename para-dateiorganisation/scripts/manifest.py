#!/usr/bin/env python3
"""Idempotenz-Manifest für die PARA-Dateiorganisation.

Hält fest, welche Dateien (per Inhalts-Hash) bereits einsortiert wurden, damit
ein zweiter Lauf nicht dasselbe erneut vorschlägt. Das Manifest ist eine
JSON-Lines-Datei (`<PARA-Home>/.para-manifest.jsonl`), eine Zeile pro Datei:

    {"hash": "<sha256>", "ziel": "<abs. Zielpfad>", "aktion": "verschoben",
     "quelle": "<Originaldateiname>", "zeitstempel": "2026-07-02T14:03:11"}

Zwei Unterbefehle:

    manifest.py check  <manifest> <quelldatei> ...
        Hasht jede Quelldatei und meldet, ob ihr Inhalt schon im Manifest steht
        (also bereits einsortiert wurde). Vor dem Vorschlagen aufrufen —
        bereits Verarbeitetes überspringen.

    manifest.py record <manifest> [--aktion verschoben] <zieldatei> ...
        Hasht jede (bereits am Ziel liegende) Datei und hängt sie ans Manifest.
        Nach der Ausführung aufrufen. Idempotent: ein Hash, der schon im
        Manifest steht, wird nicht doppelt eingetragen.

Rein lokal, keine externen Abhängigkeiten. Verändert außer dem Manifest selbst
keine Datei.
"""

import argparse
import hashlib
import json
import os
from datetime import datetime


def sha256_of(path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path):
    """Liest das Manifest und gibt {hash: eintrag} zurück. Fehlende Datei -> {}.
    Kaputte Zeilen werden übersprungen (ein manuell verpfuschtes Manifest soll
    den ganzen Lauf nicht abwürgen), ihre Anzahl steht in _skipped_lines."""
    index = {}
    skipped = 0
    if not os.path.isfile(path):
        load_manifest._skipped_lines = 0
        return index
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                digest = entry.get("hash")
            except (json.JSONDecodeError, AttributeError):
                skipped += 1
                continue
            if not digest:
                skipped += 1
                continue
            index[digest] = entry
    load_manifest._skipped_lines = skipped
    return index


load_manifest._skipped_lines = 0


def append_entries(path, entries):
    """Hängt neue Einträge ans Manifest an (eine JSON-Zeile pro Eintrag).
    Legt Verzeichnis/Datei bei Bedarf an."""
    if not entries:
        return
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def check_files(manifest_path, files):
    """Für jede Quelldatei: Hash bilden, gegen das Manifest prüfen."""
    index = load_manifest(manifest_path)
    results = []
    for path in files:
        entry = {"datei": path, "hash": None, "bereits_verarbeitet": False,
                 "ziel": None, "warnung": None}
        try:
            digest = sha256_of(path)
        except OSError as e:
            entry["warnung"] = f"Konnte nicht gehasht werden: {e}"
            results.append(entry)
            continue
        entry["hash"] = digest
        known = index.get(digest)
        if known:
            entry["bereits_verarbeitet"] = True
            entry["ziel"] = known.get("ziel")
        results.append(entry)
    return results


def record_files(manifest_path, files, aktion="verschoben"):
    """Für jede (am Ziel liegende) Datei einen Manifest-Eintrag erzeugen und
    anhängen. Schon bekannte Hashes werden übersprungen (Idempotenz)."""
    index = load_manifest(manifest_path)
    new_entries = []
    recorded = []
    warnings = []
    stamp = _now_iso()
    for path in files:
        try:
            digest = sha256_of(path)
        except OSError as e:
            warnings.append(f"Konnte nicht gehasht werden: {path} ({e})")
            continue
        if digest in index:
            continue  # schon im Manifest — nicht doppelt eintragen
        entry = {
            "hash": digest,
            "ziel": os.path.abspath(path),
            "aktion": aktion,
            "quelle": os.path.basename(path),
            "zeitstempel": stamp,
        }
        new_entries.append(entry)
        index[digest] = entry  # innerhalb dieses Laufs auch Dubletten abfangen
        recorded.append(entry)
    append_entries(manifest_path, new_entries)
    return recorded, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    sub = parser.add_subparsers(dest="befehl", required=True)

    p_check = sub.add_parser("check", help="Quelldateien gegen das Manifest prüfen")
    p_check.add_argument("manifest", help="Pfad zum .para-manifest.jsonl")
    p_check.add_argument("files", nargs="+", help="Zu prüfende Quelldateien")

    p_record = sub.add_parser("record", help="Verarbeitete Zieldateien ins Manifest schreiben")
    p_record.add_argument("manifest", help="Pfad zum .para-manifest.jsonl")
    p_record.add_argument("--aktion", default="verschoben",
                          help="Aktionslabel für die Einträge (Standard: verschoben)")
    p_record.add_argument("files", nargs="+", help="Bereits am Ziel liegende Dateien")

    args = parser.parse_args()

    if args.befehl == "check":
        results = check_files(args.manifest, args.files)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            for r in results:
                if r["warnung"]:
                    print(f"  {r['datei']}: {r['warnung']}")
                elif r["bereits_verarbeitet"]:
                    print(f"  BEREITS EINSORTIERT: {r['datei']} -> {r['ziel']}")
                else:
                    print(f"  neu: {r['datei']}")
        return

    if args.befehl == "record":
        recorded, warnings = record_files(args.manifest, args.files, args.aktion)
        if args.json:
            print(json.dumps({"eingetragen": recorded, "warnungen": warnings},
                             indent=2, ensure_ascii=False))
        else:
            print(f"{len(recorded)} neue Einträge ins Manifest geschrieben: {args.manifest}")
            for w in warnings:
                print(f"  Hinweis: {w}")
        return


if __name__ == "__main__":
    main()
