# Konfiguration — Ziel-Ort, Struktur, Plattform

Dieses Skill verdrahtet **nichts** person- oder maschinenspezifisch. Alles Veränderliche wird zur Laufzeit ermittelt oder beim Nutzer erfragt. Diese Datei beschreibt, *wie* — sie enthält selbst keine konkreten Nutzerpfade.

## Optionale Konfigurationsdatei

Der Nutzer kann seine Einstellungen in einer Datei `~/.config/para-dateiorganisation/config.json` (bzw. plattformüblichem Config-Ort) hinterlegen. Wenn vorhanden, hat sie Vorrang vor der automatischen Erkennung. Beispielstruktur (Platzhalterwerte):

```json
{
  "para_home_primaer": "<absoluter Pfad zum privaten PARA-Ordner>",
  "para_home_weitere": { "beruflich": "<absoluter Pfad>" },
  "benennungsschema": "N_Name",
  "scan_wurzeln": ["<Downloads>", "<Desktop>"],
  "ausschluesse": ["<Library/AppData>", "<Repos>", "node_modules", ".git"],
  "loeschziel": "quarantaene_ordner"
}
```

Existiert keine Config: erkennen (siehe unten), sonst den Nutzer fragen. Die Config nur mit ausdrücklicher Zustimmung des Nutzers anlegen/ändern.

## Ziel-Ort (kanonisches PARA-Home) ermitteln

Reihenfolge:
1. Config-Datei, falls vorhanden.
2. Automatische Erkennung: im Dokumente-Ordner des Nutzers nach einem Ordner suchen, der wie ein PARA-Home aussieht (enthält Unterordner, die zu Inbox/Projekte/Areas/Resources/Archiv passen — in irgendeiner Schreibweise). Der Name des Dokumente-Ordners ist selbst lokalisiert/plattformabhängig (`Documents`, `Dokumente`, …) und wird ermittelt, nicht angenommen.
3. Gefunden → dessen Benennungskonvention exakt übernehmen.
4. Nicht gefunden → Nutzer nach Ziel-Ort und Schema fragen, dann anlegen.

## Benennungskonvention

Wird aus dem vorhandenen PARA-Home abgeleitet (die dortige Schreibweise gewinnt). Nur wenn frisch angelegt wird, ein Schema mit dem Nutzer festlegen. Gängige Varianten: `N_Name` (`1_Projekte`), `N. Name` (`1. Projekte`), `N-Name` (`1-Projekte`), deutsch oder englisch. **Innerhalb eines Homes niemals mischen.**

## Plattform-Ermittlung

OS-abhängige Details nie annehmen, sondern bestimmen:

```bash
python3 -c "import platform, pathlib; print(platform.system()); print(pathlib.Path.home())"
```

Daraus ableiten: Home-Verzeichnis, Pfadtrenner, Papierkorb-Mechanismus, Config-Ort. Der **portable Standard fürs Löschen** ist ein Quarantäne-Ordner `_Papierkorb/` innerhalb des PARA-Homes — funktioniert auf jedem OS gleich. OS-eigener Papierkorb nur, wenn die Plattform sicher bestimmt wurde (macOS `~/.Trash`, Linux `gio trash`/`~/.local/share/Trash`, Windows Recycle Bin).

## Scan-Wurzeln und Ausschlüsse (Home-weiter Modus)

Wenn der Nutzer „alles prüfen" möchte, ist damit **nicht** das gesamte Dateisystem gemeint (sinnlos und riskant), sondern die persönlichen Ablageorte im Home. Standard-Wurzeln: Downloads, Desktop, lose Dateien im Dokumente-Ordner. **Harte Ausschlüsse** (nie hineinscannen/verschieben):

- Betriebssystem-/Programm-Verzeichnisse (`/System`, `/Applications`, `Program Files`, …)
- Nutzer-Bibliotheks-/App-Daten (`~/Library`, `~/AppData`, `~/.config`, `~/.cache`, versteckte Punktordner)
- Code-Repos und Projektordner (Marker `.git`, `package.json`, `pyproject.toml`, … — siehe `dedupe_scan.py`)
- `node_modules`, Cloud-Sync-Interna, virtuelle Umgebungen
- die PARA-Homes selbst (nicht sich selbst umsortieren)

Zusätzlich eine `.para-ignore`-Datei respektieren: liegt sie in einem Ordner, wird dieser Ordner (und darunter) nie angefasst.

## Zustand / Idempotenz

Um bei wiederholten Läufen bereits Einsortiertes zu überspringen, hält das Skill ein Manifest (z.B. `<PARA-Home>/.para-manifest.jsonl`) mit Hash + Zielpfad bereits verarbeiteter Dateien. Vor dem Vorschlagen dagegen abgleichen — schon Verarbeitetes nicht erneut vorschlagen.
