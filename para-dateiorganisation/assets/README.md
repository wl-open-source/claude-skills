# Wächter-Vorlagen (Schicht-2-Automatik) — optional, NICHT automatisch geladen

Diese Dateien richten einen **Ordner-Wächter** ein, der `scripts/triage.py` startet,
sobald in einem Durchgangsordner (Downloads/Desktop) neue Dateien auftauchen. Das
ist die optionale Automatik-Schicht: rein lokal, ohne LLM, ohne Cloud.

> **Nichts hier wird vom Skill selbst installiert oder gestartet.** Es sind
> Vorlagen. Der Nutzer entscheidet bewusst, ob und wo er einen Wächter aktiviert.
> `triage.py` verschiebt nie Inhaltsdateien automatisch — es sortiert nur Müll in
> die Quarantäne und schreibt neue Dateien in eine Queue zur späteren, bestätigten
> Einsortierung.

## Platzhalter (in allen Vorlagen ersetzen)

| Platzhalter    | Bedeutung                                              | Beispiel |
|----------------|--------------------------------------------------------|----------|
| `__PYTHON__`     | Absoluter Pfad zum Python-3-Interpreter                | `/usr/bin/python3` |
| `__SKILL_DIR__`  | Absoluter Pfad zu diesem Skill-Ordner                  | `/Users/du/.claude/skills/para-dateiorganisation` |
| `__WATCH_DIR__`  | Zu überwachender Durchgangsordner                      | `/Users/du/Downloads` |
| `__PARA_HOME__`  | Kanonisches PARA-Home (für Dedup/Manifest)             | `/Users/du/Dokumente/PARA` |

Ermittle `__PYTHON__` und dein Home portabel mit:

```bash
python3 -c "import sys, pathlib; print(sys.executable); print(pathlib.Path.home())"
```

## Empfohlener triage-Aufruf

```bash
__PYTHON__ __SKILL_DIR__/scripts/triage.py __WATCH_DIR__ \
  --apply --notify \
  --manifest __PARA_HOME__/.para-manifest.jsonl \
  --against-home __PARA_HOME__
```

`--apply` ist hier bewusst gesetzt (ein Wächter soll handeln), aber wegen der
Trockenlauf-Voreinstellung erst **nach** einem manuellen Test aktivieren:

```bash
__PYTHON__ __SKILL_DIR__/scripts/triage.py __WATCH_DIR__        # Trockenlauf: erst ansehen
```

## Installation je Plattform

Plattform zuerst bestimmen (nicht raten):

```bash
python3 -c "import platform; print(platform.system())"   # Darwin | Linux | Windows
```

### macOS — `launchd` (WatchPaths)

1. `launchd/com.para-dateiorganisation.watch.plist` kopieren, Platzhalter ersetzen.
2. Nach `~/Library/LaunchAgents/` legen.
3. Laden: `launchctl load ~/Library/LaunchAgents/com.para-dateiorganisation.watch.plist`
4. Entladen: `launchctl unload ~/Library/LaunchAgents/com.para-dateiorganisation.watch.plist`

`WatchPaths` löst den Job aus, sobald sich der Ordnerinhalt ändert.

### Linux — `systemd` path unit (inotify)

1. `systemd/para-dateiorganisation.path` und `…​.service` kopieren, Platzhalter ersetzen.
2. Nach `~/.config/systemd/user/` legen.
3. Aktivieren:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now para-dateiorganisation.path
   ```
4. Deaktivieren: `systemctl --user disable --now para-dateiorganisation.path`

Die `.path`-Unit beobachtet `__WATCH_DIR__` via inotify und startet die `.service`.

### Windows — Task Scheduler

1. `windows/register-task.ps1` öffnen, Platzhalter ersetzen.
2. In einer PowerShell ausführen (registriert einen Task, der bei Anmeldung und
   danach regelmäßig läuft — Windows hat kein direktes Ordner-Watch-Äquivalent im
   Task Scheduler, daher Intervall-Trigger):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\windows\register-task.ps1
   ```
3. Entfernen: `Unregister-ScheduledTask -TaskName "PARA-Dateiorganisation-Wächter"`

## Verifikationsstand (ehrlich)

Diese Vorlagen sind **für macOS/Linux/Windows ausgelegt, aber nur auf macOS
ausgeführt/verifiziert**. Auf Linux/Windows also erst den triage-Aufruf im
**Trockenlauf** prüfen (ohne `--apply`) und den Wächter kurz manuell auslösen,
bevor du dich auf die Automatik verlässt.

## Sicherheit

- Der Wächter läuft mit deinen Nutzerrechten und fasst nur `__WATCH_DIR__` an.
- Müll geht in `__WATCH_DIR__/_Papierkorb/` (reversibel), nie `rm`.
- Rückgängig machen: `__PYTHON__ __SKILL_DIR__/scripts/undo_last_run.py __WATCH_DIR__ --apply`.
- Nichts wird ins Netz gesendet.
