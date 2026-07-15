#!/usr/bin/env python3
"""Macht die Datei-Bewegungen eines Aufräum-Laufs rückgängig.

Liest das CSV-Protokoll, das Schritt 6 in SKILL.md beim Ausführen schreibt
(`<zielverzeichnis>/.para-dateiorganisation-log-<datum>.csv`, Spalten
`zeitstempel;aktion;alt;neu`), und bewegt jede Datei von `neu` zurück nach `alt`.

Die Umkehrung ist bewusst **aktions-agnostisch**: ob eine Zeile eine Umbenennung,
eine Verschiebung ins PARA-Home oder eine Verschiebung in die Quarantäne
(`_Papierkorb/`) protokolliert, spielt keine Rolle — in allen Fällen ist das
Rückgängigmachen `neu -> alt`. Genau deshalb funktioniert dieselbe Logik für
alles, was der Aufräum-Lauf getan hat.

Sicherheit (dieselbe Disziplin wie beim Aufräumen selbst):

* **Standard = Trockenlauf.** Ohne `--apply` wird nur ein Plan gedruckt, nichts
  bewegt. Erst `--apply` führt aus.
* **Nie überschreiben.** Existiert das Rückgabeziel `alt` schon wieder, wird die
  Zeile übersprungen und als Konflikt gemeldet — statt eine andere Datei zu
  überschreiben.
* **Fehlende Quelle** (`neu` gibt es nicht mehr, z.B. weil der Nutzer die Datei
  selbst schon zurückgeschoben hat) wird gemeldet, nicht als Fehler behandelt.
* **Rückwärts-Reihenfolge.** Zeilen werden in umgekehrter Protokollreihenfolge
  abgearbeitet, damit verkettete Bewegungen sauber aufgelöst werden.

„Letzter Lauf": Das Protokoll markiert keine Lauf-Grenzen (mehrere Läufe am
selben Tag landen in derselben Tagesdatei). Standard ist deshalb die **neueste**
Log-Datei im angegebenen Verzeichnis, als Ganzes. Mit `--tag N` lassen sich nur
die letzten N protokollierten Aktionen zurücknehmen (der format-unabhängige Weg,
„nur den letzten Lauf" zu treffen, wenn man weiss, wie viele Dateien er betraf).

Rein lokal, keine externen Abhängigkeiten. Bewegt nur Dateien, die im Protokoll
stehen; legt/verändert sonst nichts ausser fehlenden Zielverzeichnissen.
"""

import argparse
import csv
import glob
import json
import os
import shutil

LOG_GLOB = ".para-dateiorganisation-log-*.csv"
HEADER = ["zeitstempel", "aktion", "alt", "neu"]


def find_newest_log(directory):
    """Neueste Protokolldatei in `directory` finden (nach mtime). None, wenn keine."""
    treffer = glob.glob(os.path.join(directory, LOG_GLOB))
    if not treffer:
        return None
    return max(treffer, key=lambda p: os.path.getmtime(p))


def parse_log(log_path):
    """Protokoll lesen -> (zeilen, warnungen).

    `zeilen` ist eine Liste von Dicts {zeitstempel, aktion, alt, neu} in
    Dateireihenfolge. Header, Leerzeilen und kaputte Zeilen werden übersprungen;
    kaputte Zeilen erzeugen eine Warnung (ein von Hand verpfuschtes Protokoll
    soll den ganzen Undo-Lauf nicht abwürgen)."""
    zeilen = []
    warnungen = []
    with open(log_path, "r", encoding="utf-8", newline="") as f:
        for nr, felder in enumerate(csv.reader(f, delimiter=";"), start=1):
            if not felder or all(not c.strip() for c in felder):
                continue
            if felder == HEADER:
                continue
            if len(felder) != 4:
                warnungen.append(f"Zeile {nr}: erwartet 4 Felder, {len(felder)} gefunden - übersprungen")
                continue
            zeitstempel, aktion, alt, neu = (c.strip() for c in felder)
            if not alt or not neu:
                warnungen.append(f"Zeile {nr}: leerer alt-/neu-Pfad - übersprungen")
                continue
            zeilen.append({"zeitstempel": zeitstempel, "aktion": aktion, "alt": alt, "neu": neu})
    return zeilen, warnungen


def plan_undo(zeilen):
    """Für jede Protokollzeile (in Rückwärtsreihenfolge) bestimmen, ob sie sich
    zurücknehmen lässt. Gibt eine Liste von Aktions-Dicts zurück:

        {alt, neu, aktion, status, grund}

    status ist einer von: 'bereit' | 'quelle_fehlt' | 'ziel_belegt' | 'identisch'
    Nur 'bereit' wird bei --apply tatsächlich ausgeführt.

    Die Zwischenzustände werden simuliert: bei verketteten Bewegungen (a->b, dann
    b->c) erzeugt der erste Undo-Schritt (c->b) erst die Quelle für den zweiten
    (b->a). Ohne diese Simulation würde der zweite Schritt statisch als
    'quelle_fehlt' erscheinen, obwohl er in der Sequenz aufgeht. `created`/
    `removed` überlagern den realen Dateizustand entsprechend."""
    plan = []
    created = set()   # Pfade, die nach vorherigen geplanten Undos existieren werden
    removed = set()   # Pfade, die dann nicht mehr existieren

    def wird_existieren(pfad):
        key = os.path.abspath(pfad)
        if key in created:
            return True
        if key in removed:
            return False
        return os.path.exists(pfad)

    for zeile in reversed(zeilen):
        alt, neu = zeile["alt"], zeile["neu"]
        eintrag = {"alt": alt, "neu": neu, "aktion": zeile["aktion"],
                   "status": "bereit", "grund": None}
        if os.path.abspath(alt) == os.path.abspath(neu):
            eintrag["status"] = "identisch"
            eintrag["grund"] = "alt und neu sind derselbe Pfad"
        elif not wird_existieren(neu):
            eintrag["status"] = "quelle_fehlt"
            eintrag["grund"] = f"'{neu}' existiert nicht (mehr)"
        elif wird_existieren(alt):
            eintrag["status"] = "ziel_belegt"
            eintrag["grund"] = f"'{alt}' existiert bereits - nicht überschrieben"
        else:
            # geplante Bewegung neu -> alt in die Simulation übernehmen
            removed.add(os.path.abspath(neu))
            created.discard(os.path.abspath(neu))
            created.add(os.path.abspath(alt))
            removed.discard(os.path.abspath(alt))
        plan.append(eintrag)
    return plan


def apply_undo(plan):
    """Alle 'bereit'-Einträge ausführen (neu -> alt). Gibt (erledigt, fehler)
    zurück; fehler sind Dicts mit zusätzlichem 'fehler'-Feld."""
    erledigt = []
    fehler = []
    for eintrag in plan:
        if eintrag["status"] != "bereit":
            continue
        alt, neu = eintrag["alt"], eintrag["neu"]
        try:
            ziel_ordner = os.path.dirname(os.path.abspath(alt))
            if ziel_ordner and not os.path.isdir(ziel_ordner):
                os.makedirs(ziel_ordner, exist_ok=True)
            # Erneut prüfen (TOCTOU-Schutz): nicht überschreiben.
            if os.path.exists(alt):
                fehler.append({**eintrag, "fehler": f"'{alt}' inzwischen belegt"})
                continue
            shutil.move(neu, alt)
            erledigt.append(eintrag)
        except OSError as e:
            fehler.append({**eintrag, "fehler": str(e)})
    return erledigt, fehler


def run(directory=None, log_path=None, tail=None, apply=False):
    """Kern-Ablauf ohne argparse - auch aus Tests direkt aufrufbar."""
    if not log_path:
        directory = directory or "."
        log_path = find_newest_log(directory)
        if not log_path:
            return {"log": None, "warnung": f"Keine Protokolldatei ({LOG_GLOB}) in {directory}",
                    "plan": [], "erledigt": [], "fehler": [], "warnungen": []}
    zeilen, warnungen = parse_log(log_path)
    plan = plan_undo(zeilen)
    if tail is not None:
        # plan ist bereits rückwärts sortiert -> die ersten `tail` sind die
        # letzten protokollierten Aktionen.
        plan = plan[:tail]
    erledigt, fehler = ([], [])
    if apply:
        erledigt, fehler = apply_undo(plan)
    return {"log": log_path, "warnung": None, "plan": plan,
            "erledigt": erledigt, "fehler": fehler, "warnungen": warnungen}


def _print_text(ergebnis, apply):
    if ergebnis["warnung"]:
        print(ergebnis["warnung"])
        return
    print(f"Protokoll: {ergebnis['log']}")
    for w in ergebnis["warnungen"]:
        print(f"  Hinweis: {w}")
    plan = ergebnis["plan"]
    bereit = [e for e in plan if e["status"] == "bereit"]
    blockiert = [e for e in plan if e["status"] != "bereit"]
    if not apply:
        print(f"\nTrockenlauf - {len(bereit)} Aktion(en) würden zurückgenommen "
              f"(mit --apply ausführen):")
        for e in bereit:
            print(f"  zurück: {e['neu']}  ->  {e['alt']}")
        for e in blockiert:
            print(f"  ÜBERSPRUNGEN [{e['status']}]: {e['neu']} ({e['grund']})")
        return
    print(f"\n{len(ergebnis['erledigt'])} Aktion(en) zurückgenommen:")
    for e in ergebnis["erledigt"]:
        print(f"  zurück: {e['neu']}  ->  {e['alt']}")
    for e in blockiert:
        print(f"  übersprungen [{e['status']}]: {e['neu']} ({e['grund']})")
    for e in ergebnis["fehler"]:
        print(f"  FEHLER: {e['neu']} -> {e['alt']}: {e['fehler']}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pfad", nargs="?", default=".",
                        help="Verzeichnis mit dem Protokoll (Standard: .) - "
                             "die neueste Log-Datei darin wird genutzt")
    parser.add_argument("--log", help="Explizite Protokolldatei statt Auto-Erkennung")
    parser.add_argument("--tag", "--tail", dest="tail", type=int, default=None,
                        metavar="N", help="Nur die letzten N protokollierten Aktionen zurücknehmen")
    parser.add_argument("--apply", action="store_true",
                        help="Tatsächlich ausführen (ohne: nur Trockenlauf/Plan)")
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    args = parser.parse_args()

    ergebnis = run(directory=args.pfad, log_path=args.log, tail=args.tail, apply=args.apply)

    if args.json:
        print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    else:
        _print_text(ergebnis, args.apply)


if __name__ == "__main__":
    main()
