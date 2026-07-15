---
name: para-dateiorganisation
description: Analysiert Dateien in einem Ordner (z.B. Downloads, Desktop, Dokumente), schlägt professionelle Umbenennungen nach deutschem Standard (DIN 5008, ISO-Datum) vor, findet Löschkandidaten (Temp-Dateien, leere Dateien, veraltete Installer) und erkennt Duplikate/Redundanzen sowohl über den Dateinamen als auch über den tatsächlichen Inhalt (Hash- und Textähnlichkeitsvergleich), und organisiert alles in eine Second-Brain-Struktur nach der PARA-Methode (Projects/Areas/Resources/Archives) von Tiago Forte. Nutze dieses Skill immer, wenn der Nutzer sagt "räum meine Downloads/Dokumente/Desktop auf", "benenne die Dateien professionell um", "organisiere diese Dateien", "finde Duplikate", "was kann ich hier löschen", "bring Struktur in diesen Ordner" oder ähnliche Aufräum-/Organisationswünsche für lokale Dateien äußert — auch wenn PARA oder Second Brain nicht explizit erwähnt werden.
---

# PARA-Dateiorganisation

Bringt einen unordentlichen Ordner (typischerweise Downloads) in einen professionell benannten, dedupliziertem und nach der PARA-Methode organisierten Zustand. Der Kerngedanke: **Vorschlagen, nie automatisch ausführen.** Jede Umbenennung, jede Verschiebung, jede Löschung ist eine Änderung, die der Nutzer sehen und einzeln freigeben muss, bevor sie passiert — genau wie bei jeder anderen state-changing Aktion.

## Zwei Schichten — und wo dieses Skill überhaupt greift

Dieses Skill hat bewusst zwei Ebenen, damit es überall dort nützlich ist, wo Claude läuft, ohne etwas Unmögliches zu versprechen:

- **Schicht 1 — die Methode (universell):** die PARA-Prinzipien, das Benennungsschema, der Entscheidungs-Workflow, die Datenschutz-Disziplin. Das ist reine Anleitung und funktioniert überall — auch als reine Beratung auf Mobilgeräten oder im Web, wo es keinen Dateizugriff gibt.
- **Schicht 2 — die Automatik (nur mit lokaler Umgebung):** die Python-Skripte (Duplikat-Scan, Metadaten-Extraktion, OCR) und alles, was Dateien verschiebt/löscht. Das setzt eine Shell + Python + lokalen Dateizugriff voraus (typisch: Claude Code auf Desktop). **In mobiler oder Web-Claude gibt es keinen lokalen Dateizugriff — dann greift nur Schicht 1.** Das offen sagen, statt so zu tun, als ließe sich dort etwas organisieren.

**Nichts fest verdrahten.** Dieses Skill ist so gebaut, dass es an keinen konkreten Nutzer, kein konkretes Betriebssystem und keinen festen Pfad gebunden ist. Zielorte, vorhandene PARA-Struktur und plattformspezifische Details werden **zur Laufzeit ermittelt** (siehe `references/konfiguration.md`) oder beim Nutzer erfragt — niemals im Skill hartkodiert. Beispielnamen in dieser Anleitung (Firmen, Behörden, Personen) sind reine Platzhalter.

**Plattform-Details nicht raten, sondern ermitteln.** Papierkorb-Pfad, Home-Verzeichnis, verfügbare Werkzeuge unterscheiden sich je OS (macOS/Windows/Linux). Vor OS-abhängigen Aktionen die Plattform bestimmen (z.B. per `python3 -c "import platform,sys; print(platform.system(), sys.platform)"`) und den passenden Weg wählen — oder den portablen Standardweg (Quarantäne-Ordner statt OS-Papierkorb, siehe Schritt 3).

> **Verifikationsstand (ehrlich):** Die plattformabhängigen Teile — OS-Papierkorb, Desktop-Notiz (`triage.py --notify`) und die Wächter-Vorlagen in `assets/` (launchd/systemd/Task Scheduler) — sind **für macOS/Linux/Windows ausgelegt, aber nur auf macOS ausgeführt/verifiziert**. Auf Linux/Windows gilt: erst im Trockenlauf prüfen, bevor `--apply` läuft. Der **portable Standardweg** (Quarantäne-Ordner statt OS-Papierkorb) ist bewusst OS-unabhängig und der sichere Default überall.

## Warum diese Reihenfolge wichtig ist

Analyse → Umbenennungsplan → Duplikaterkennung → Löschkandidaten → PARA-Einordnung → Bestätigung. Diese Reihenfolge ist kein Zufall: Duplikate müssen erkannt sein, *bevor* man Löschkandidaten vorschlägt (sonst empfiehlt man versehentlich das Original zu löschen und das Duplikat zu behalten). Und die PARA-Einordnung passiert erst, wenn die Dateien schon sauber benannt und dedupliziert sind — sonst landen Duplikate doppelt in der neuen Struktur.

## Schritt 1: Scan & Inhalt verstehen

Bevor du irgendetwas vorschlägst, musst du den Inhalt kennen — der Dateiname allein reicht nicht ("Dokument.pdf" oder "Scan001.pdf" verraten nichts). Aber *wie* du an den Inhalt kommst, hängt von der Art der Datei ab — das ist kein Detail, sondern die wichtigste Weiche in diesem Skill:

- **Code-/Projektdateien, Repos, Design-Assets:** nicht lesen, nicht anfassen — außerhalb des Scopes (siehe Ausnahmetabelle Schritt 2).
- **Bilder von Ausweisdokumenten** (Personalausweis, Reisepass, Führerschein, Sozialversicherungsausweis o.ä. — erkennbar am Dateinamen oder am Ordnerkontext): **niemals inhaltlich analysieren, auch nicht per Vision.** Nur der Dateiname entscheidet über Einordnung/Umbenennung. Diese Bilder sind sensibler als jedes Textdokument — im Zweifel eine Datei zu dieser Kategorie zählen, nicht zu wenig vorsichtig sein.
- **Screenshots und Fotos mit möglicherweise sensiblem Inhalt (nicht Ausweisdokumente):** zuerst `scripts/extract_image_metadata.py` lokal ausführen (EXIF-Datum + lokale OCR, mit derselben Schwärzung wie oben) — nicht per Vision ansehen. OCR kann Ziffern verwechseln (z.B. Datum falsch erkennen) — einen Vorschlag aus diesem Skript deshalb als Entwurf behandeln, nicht blind übernehmen; bei Unsicherheit kurz mit dem Nutzer gegenchecken statt zu vertrauen.
- **Eindeutig hochsensible Dokumente** (Finanzunterlagen wie Kontoauszüge, Depot-/Steuerbescheide, Lohnabrechnungen; Gesundheits-/Arztunterlagen, Befunde, Rezepte; Ausweis-PDFs; Verträge oder Anträge mit vollständigen Personendaten — erkennbar am Dateinamen oder am Ordnerkontext): **Default = gar nicht extrahieren.** Nach dem Dateinamen benennen/einordnen oder den Nutzer fragen ("Wie soll ich diese Datei benennen?"). `scripts/extract_metadata.py` schwärzt zwar lokal, aber **Schwärzung ist Risiko-Reduktion, kein Schutz** (Regex kann sensible Stellen übersehen — siehe Absatz unten). Bei eindeutig sensiblem Inhalt wird die lokale Extraktion deshalb **nicht** ausgeführt, außer der Nutzer erlaubt sie ausdrücklich für genau diese Datei. Die lokale Extraktion ist für den *unklaren/harmlosen* Verdacht gedacht, nicht für das, was ohnehin schon klar sensibel ist.
- **Alle anderen Text-/Dokument-Dateien (.pdf, .docx, .txt, .md), deren Inhalt personenbezogen, finanziell, rechtlich oder gesundheitsbezogen sein *könnte* (unklarer/harmloser Verdacht):** zuerst `scripts/extract_metadata.py` lokal ausführen (siehe unten) — **nicht** direkt mit dem Read-Tool öffnen. Das gilt nicht nur für Dateien, die schon an ihrem Namen als Rechnung/Bescheid erkennbar sind, sondern gerade auch für kryptisch benannte Dateien ("Scan001.pdf", "01505537718612.pdf") — die sind am Namen ja *nicht* erkennbar, könnten aber genau deshalb sensibel sein. Stellt sich beim Ausschnitt heraus, dass die Datei doch klar hochsensibel ist (Kategorie oben), dann dort weiterbehandeln: nichts Weiteres extrahieren, nach Dateiname/Nachfrage benennen.
- **Eindeutig unkritische Dateien** (offensichtliche Notizen, Marketing-Texte, Exporte ohne Personenbezug, technische Dokumentation): direkt mit dem Read-Tool lesen, das ist unproblematisch.

Warum diese Reihenfolge (lokale Extraktion vor Read-Tool) wichtig ist: Alles, was das Read-Tool öffnet, wird Teil des Modell-Kontexts und läuft damit über die Cloud-API. `scripts/extract_metadata.py` läuft dagegen komplett lokal auf der Maschine des Nutzers und schwärzt IBAN (deutsch und international), E-Mail-Adressen, Kreditkartennummern (Luhn-geprüft), Kontonummer, Steuer-ID, Sozialversicherungsnummer, Beträge, Adressen, Telefonnummern und lange Ziffernblöcke, bevor überhaupt etwas zurückgegeben wird. Bei eindeutigem Treffer (Datum + Dokumenttyp erkannt) liefert es direkt einen fertigen Dateinamensvorschlag — der volle Dokumenttext muss dann nie gelesen werden. Nur wenn kein eindeutiger Treffer möglich ist, gibt es einen bereits geschwärzten Kurzausschnitt zurück, den man sich ansehen kann.

**Wichtig — geschwärzt ≠ sicher:** Diese Schwärzung ist Risiko-*Reduktion*, kein Schutz. Sie beruht auf Regex-Mustern, und die versagen nachweislich (in der Praxis ging bei einem zerstückelten Behörden-PDF ein Name/eine Adresse durch, bis die `is_garbled`-Erkennung nachgezogen wurde). Verlasse dich also **nie** darauf, dass ein geschwärzter Ausschnitt wirklich frei von sensiblen Daten ist. Deshalb gilt: für *eindeutig* sensible Dokumente (Ausweis, Finanzen, Gesundheit) gar nicht erst extrahieren (siehe Kategorie oben), und einen `confidence: "high"`-Vorschlag nie ungeprüft übernehmen (siehe unten).

```bash
python3 scripts/extract_metadata.py <datei1> <datei2> ... --json
```

Wenn `confidence: "low"` zurückkommt und auch der geschwärzte Ausschnitt keine sichere Einordnung erlaubt: den Nutzer kurz fragen ("Um was für ein Dokument handelt es sich, damit ich es richtig benenne?"), statt das Originaldokument doch mit dem Read-Tool zu öffnen. Das volle Dokument nur dann direkt lesen, wenn der Nutzer das für genau diese Datei explizit erlaubt.

Ein `confidence: "high"` heißt nur „Datum + Dokumenttyp automatisch erkannt", **nicht** „geprüft und sicher" — nie ungeprüft übernehmen. Immer das Feld `kuerzel_quelle` prüfen — es zeigt, welches Wort den Dokumenttyp-Treffer ausgelöst hat. Ein Kontoauszug, in dessen Kleingedrucktem einmal "Vertrag" vorkommt, wird sonst fälschlich als `VTR` erkannt. Passt `kuerzel_quelle` nicht zum offensichtlichen Dokumenttyp (z.B. Dateiname sagt "Kontoauszug", Quelle ist "vertrag"), dem Skript-Vorschlag nicht folgen, sondern nach Dateiname/Kontext entscheiden oder kurz nachfragen.

Manche Formular-PDFs (v.a. bei Behörden) extrahieren Text zerstückelt in Zeichengruppen wechselnder Länge ("Jo b ce n t e r" statt "Jobcenter") — Namens-/Adress-Erkennung würde darauf still versagen. Das Skript erkennt das (ungewöhnlich viele sehr kurze Tokens) und gibt in diesem Fall **gar keinen** Ausschnitt aus, nur eine Warnung. Für solche Dateien: den Nutzer fragen, ob er selbst kurz sagen kann, um was es sich handelt (Dokumenttyp + Datum reichen meist), statt das PDF doch direkt zu öffnen.

Bei sehr vielen Dateien (>~50): erst grob nach Dateityp/Größe/Änderungsdatum sortieren, dann in Batches verarbeiten statt alles auf einmal.

Ordne jede Datei testweise einer der folgenden Kategorien zu, das steuert die weiteren Schritte:
- **Umbenennen + einordnen** (der Normalfall: PDFs, Dokumente, Screenshots, Exporte)
- **Nicht umbenennen** (siehe Ausnahmen unten), aber ggf. trotzdem einordnen
- **Löschkandidat** (siehe Schritt 3)
- **Unklar** — hier lieber den Nutzer kurz fragen als zu raten. Falsch benannte Rechnungen oder falsch einsortierte Verträge sind teurer zu korrigieren als eine Rückfrage.

## Schritt 2: Umbenennung nach deutschem Standard

Standardschema (DIN 5008 / ISO 8601 Datum):

```
JJJJ-MM-TT_<Kürzel>_<Was-es-genau-ist>.<endung>
```

- **Datum** = Dokumentendatum aus dem Inhalt (Rechnungsdatum, Ausstellungsdatum), *nicht* das Datei-Systemdatum. Wenn kein Datum im Inhalt erkennbar ist, das Änderungsdatum der Datei nehmen und das im Umbenennungsplan kurz kennzeichnen ("Datum aus Dateisystem, da im Inhalt nicht auffindbar").
- **Kürzel** = Dokumenttyp-Kürzel, nicht der Absender. Die Kürzel-Tabelle in `references/kuerzel-liste.md` ist ein **erweiterbares Beispiel-Set** (deutsche Dokumenttypen), kein Gesetz — dort nachschlagen, bei neuen Dokumenttypen ergänzen, für andere Sprachen/Kontexte anpassen. Konsistenz über die Zeit ist wichtiger als das perfekte Kürzel beim ersten Mal.
- **Was-es-genau-ist** = kurzer Freitext, der den Absender/Vertragspartner und ggf. das Thema enthält, Wörter durch Bindestriche getrennt, keine Umlaute/Sonderzeichen (hält Dateinamen cross-plattform- und skriptsicher).

Beispiel (Platzhalter): `2026-03-15_RG_<Anbieter>_Mobilfunk-Maerz.pdf`

### Begründete Ausnahmen vom Standardschema

Nicht jeder Dateityp profitiert vom selben Schema — hier lieber die Ausnahme respektieren als stur das Standardschema durchzudrücken:

| Dateityp | Umgang | Warum |
|---|---|---|
| Fotos aus Kamera/Handy | **Nicht einzeln umbenennen.** Nur den übergeordneten Ordner sinnvoll benennen (z.B. `2026-05_Urlaub-Italien/`). | EXIF-Metadaten sind die verlässliche Quelle; Massenumbenennung zerstört Referenzen in Cloud-Sync/Backups und bringt keinen Mehrwert. |
| Installer/Setup (.dmg, .exe, .pkg, .msi) | **Nicht umbenennen.** | Enthält oft Versionsnummer im Originalnamen, die für Nachvollziehbarkeit zählt. |
| Code-/Projektdateien, Repos | **Nicht umbenennen, nicht in PARA verschieben.** | Unterliegen eigenen Konventionen (Git, Framework) — außerhalb des Scopes dieses Skills. |
| Screenshots | `JJJJ-MM-TT_Screenshot_<Kontext>.png` | Kontext (wovon der Screenshot ist) schlägt Uhrzeit als Suchkriterium. |
| Bewerbungsunterlagen | `JJJJ-MM-TT_BEW_<Firma>_<Dokumenttyp>.pdf` | Firma ist meist der Suchbegriff, nicht das Kürzel. |
| Blanko-Formulare / Vordrucke (leere Ausfüllfelder, kein eingetragener Vorgang, z.B. leere Verdienstbescheinigung, Gewerbeanmeldung-Vordruck) | `Vorlage_<Typ>.<endung>`, **kein** Datumsschema, gehören nach `3-Ressourcen/Vorlagen/` | Eine leere Vorlage hat kein Dokumentendatum und keinen Vorgang — sie mit einem Datum zu versehen täuscht einen Vorgang vor, den es nicht gibt. Erkennbar an generischen Feldbezeichnern ("Herr/Frau", "geb. am", "wohnhaft in") ohne eingetragene Werte. |

Wenn eine Datei in keine der bekannten Kategorien passt: lieber ein neues, klar benanntes Kürzel in `references/kuerzel-liste.md` ergänzen (mit kurzer Begründung), statt ein unpassendes bestehendes Kürzel zu erzwingen.

## Schritt 3: Löschkandidaten

Nur *vorschlagen* — niemals ohne separate Bestätigung löschen (siehe "Bestätigung" unten). Kandidaten:

- System-/Temp-Artefakte: `.DS_Store`, `Thumbs.db`, `~$*`, `*.tmp`, `*.crdownload`, `*.part`, `*.download`
- 0-Byte-Dateien
- Exakte Duplikate — alle bis auf die "Master"-Kopie (siehe Schritt 4 für die Ermittlung)
- Alte Installer, bei denen im selben Ordner bereits eine neuere Version derselben Software liegt (z.B. `App-1.2.dmg` neben `App-1.5.dmg`)
- Downloads, die seit sehr langer Zeit (z.B. >12 Monate) unverändert und nie an anderer Stelle referenziert wurden — hier explizit als "unsicherer Kandidat, bitte prüfen" kennzeichnen, nicht als sicheren Löschkandidaten, denn Alter allein ist kein verlässliches Signal für Irrelevanz.

Finde diese Kandidaten pragmatisch mit `find`/`fd` (Bash) für die simplen Fälle (Größe, Namen-Pattern, Alter). Für die exakten Duplikate nutze das Skript aus Schritt 4, dopple die Logik nicht per Hand.

**Löschen heißt: reversibel machen, nie `rm`.** Kein permanentes Löschen — immer so, dass sich ein Kandidat zurückholen lässt, falls er sich im Nachhinein als falsch erweist. Plattformabhängig den richtigen Weg wählen:

- **Portabler Standardweg (überall gleich, bevorzugt):** die Datei in einen Quarantäne-Ordner `_Papierkorb/` **innerhalb des Zielbereichs** verschieben (z.B. `<PARA-Home>/_Papierkorb/`), statt sie ins OS-eigene System zu geben. Funktioniert identisch auf macOS/Windows/Linux, ist transparent und lässt sich vom Nutzer selbst leeren.
- **OS-Papierkorb (wenn ausdrücklich gewünscht):** macOS `~/.Trash/`, Linux `~/.local/share/Trash/files/` (bzw. `gio trash`), Windows Recycle Bin (z.B. via PowerShell). Nur nutzen, wenn die Plattform sicher bestimmt wurde.

In beiden Fällen: bei Namenskollision einen Zähler anhängen, nie überschreiben.

## Schritt 4: Duplikat- und Redundanzerkennung

Reines Namens-Pattern-Matching (`Datei (1).pdf`, `Datei copy.pdf`) erkennt nur einen Bruchteil echter Redundanz — zwei Dateien mit komplett unterschiedlichen Namen können denselben oder nahezu denselben Inhalt haben, und das ist der eigentlich interessante Fall. Nutze dafür `scripts/dedupe_scan.py`:

```bash
python3 scripts/dedupe_scan.py <verzeichnis> --json
```

Das Skript liefert:
- **`exact_duplicates`**: Gruppen von Dateien mit identischem SHA-256-Hash (garantiert gleicher Inhalt), inklusive einer Empfehlung, welche Datei als "Original" behalten werden sollte (bevorzugt: Datei ohne "(1)"/"Kopie"/"copy"-Suffix im Namen, sonst die älteste).
- **`near_duplicates`**: Text-Dokumente (.txt, .md, .pdf, .docx sofern `pypdf`/`python-docx` installiert sind) mit hoher Textähnlichkeit (Standard-Schwelle 85%), z.B. "Vertrag_final.pdf" vs. "Vertrag_final_v2.pdf" mit fast identischem Inhalt. Das Skript vergleicht nur innerhalb derselben Dateiendung.
- **`subset_folders`**: direkte Unterordner, deren Inhalt (als Menge von Datei-Hashes) vollständig in einem anderen Ordner enthalten oder mit ihm identisch ist — z.B. "files (2)" komplett in "files (3)". Das ist der typische Fall bei mehrfach heruntergeladenen/entpackten Ordnern und wird von der reinen Hash-Gleichheit *nicht* erfasst (der größere Ordner hat ja mehr Dateien). `beziehung` ist entweder `identisch` oder `a_enthalten_in_b`. Wie bei Near-Duplicates: ein Signal, kein Urteil — der kleinere Ordner ist Löschkandidat, *sofern* der größere der gewünschte Stand ist.
- **`bereits_im_ziel`** (nur mit `--against <PARA-Home>`): Quelldateien, die inhaltsgleich schon im Ziel-PARA-Home liegen — ein erneuter Import wäre eine Dublette. So wird nicht versehentlich eine Datei importiert, die dort längst (evtl. unter anderem Namen) existiert. `--against` ist mehrfach angebbar (mehrere Homes). Achtung: Es hasht den gesamten Ziel-Baum; für den *inkrementellen* Fall (nur was dieses Skill selbst schon einsortiert hat) ist das Manifest über `scripts/manifest.py` der günstigere Weg — siehe Schritt 5.
- **`skipped_project_dirs`**: Code-/Projektordner (erkannt an Markern wie `.git`, `package.json`, `pyproject.toml`), die standardmäßig übersprungen wurden, weil das Skill sie ohnehin nicht anfasst. Werden bewusst gemeldet, nicht still ignoriert — mit `--include-project-dirs` lässt sich das Überspringen abschalten. Das hält den Report frei von Rauschen aus `__init__.py`- und Framework-Boilerplate.
- **`warnings`**: welche Dateien/Formate aus welchem Grund nicht geprüft werden konnten (z.B. fehlende Bibliothek) — das dem Nutzer transparent mitteilen statt es zu verschweigen, sonst wirkt eine unvollständige Prüfung wie eine vollständige.

Bei sehr großen Verzeichnissen (>~2000 Dateien) kann der paarweise Textvergleich spürbar dauern — das Skript meldet das über `warnings`, ggf. mit `--skip-near-duplicates` nur den schnellen Hash-Vergleich fahren und das dem Nutzer erklären.

Near-Duplicate-Gruppen sind ein Signal, kein Urteil — ob "v2" wirklich die zu behaltende Version ist oder ob beide Versionen fachlich relevant sind (z.B. zwei Vertragsentwürfe mit Änderungen), das entscheidet der Nutzer, nicht das Skript.

## Schritt 5: PARA-Einordnung (Second Brain, Tiago Forte)

Kernprinzip von PARA: Ordnung nach **Handlungsrelevanz**, nicht nach Thema. Vier Kategorien:
- **Projekte** — hat ein Ziel *und* ein Enddatum/Deadline.
- **Bereiche (Areas)** — dauerhafte Verantwortung ohne Enddatum (Gesundheit, Finanzen, ein Kundenkonto).
- **Ressourcen (Resources)** — Nachschlagematerial/Interessen, aktuell nicht handlungsrelevant.
- **Archiv (Archives)** — abgeschlossene/inaktive Dinge aus den anderen drei Kategorien.

Bevor eine Datei einsortiert wird, die Frage stellen: "Laufendes Projekt mit Deadline, dauerhafter Verantwortungsbereich, Nachschlagematerial, oder abgeschlossen/inaktiv?"

### Ziel-Ort und Benennung: erst erkennen, dann anpassen, sonst fragen

Das kanonische PARA-Zuhause ist **nicht** der aufzuräumende Ordner selbst (Downloads/Desktop sind nur Durchgangszonen) und **nicht** in diesem Skill hartkodiert. So wird es bestimmt:

1. **Erkennen:** Prüfen, ob am erwarteten Ablageort (siehe `references/konfiguration.md`, Standard-Kandidaten wie ein `PARA*`-Ordner in `Dokumente/Documents`) bereits eine PARA-Struktur existiert. Wenn ja: **deren Benennungskonvention exakt übernehmen** (z.B. `1_Projekte` vs. `1. Projekte` vs. `1-Projects`), keine Parallelstruktur mit abweichender Schreibweise anlegen.
2. **Anpassen:** Neue Dateien in genau diese vorhandene Struktur einsortieren, vorhandene Unterordner wiederverwenden.
3. **Fragen:** Existiert noch keine PARA-Struktur, den Nutzer nach Ziel-Ort und gewünschtem Schema fragen (gängige Vorlagen anbieten) und erst dann anlegen. Nicht raten.

Konventionsbeispiele (eine davon wählen/erkennen, nicht mischen): `0_Inbox / 1_Projekte / 2_Areas / 3_Resources / 4_Archive` — oder englisch `0_Inbox / 1_Projects / 2_Areas / 3_Resources / 4_Archives` — oder mit Punkt/Bindestrich. Das Nummern-Präfix dient nur der stabilen Sortierung, nicht als inhaltliche Aussage.

### Regeln

- **Struktur höchstens 3 Ebenen tief**, danach liegen Dateien direkt im Ordner (Beispiel: `1_Projekte/<Projekt>/<optionale Unterkategorie>/`).
- **Code-Projekte, Export-Dumps und Backups zählen als ein geschlossenes Objekt** auf Ebene ≤3: Der Ordner selbst muss die 3-Ebenen-Grenze einhalten, seine **interne** Verschachtelung (node_modules, Export-Bäume, Repo-Struktur) bleibt aber unangetastet und wird nicht mitgezählt. Die 3-Ebenen-Regel gilt nur für **Ablage-Ordner**, nicht für den Innenbau solcher Einheiten.
- **Nie einen leeren Ordner anlegen, bevor Inhalt dafür existiert** (Forte-Prinzip) — Ordner entstehen aus tatsächlichem Bedarf.
- Ein abgeschlossenes Projekt wandert **komplett** ins Archiv (nicht einzelne Dateien nach Ressourcen) — das hält die Kategorien sauber getrennt.
- **Mehrere PARA-Homes** (z.B. privat vs. beruflich) kommen vor. Standard ist das primäre/private Home; nur wenn eine Datei klar in einen anderen Kontext gehört (erkennbarer Arbeits-/Team-Bezug), dort einsortieren — im Zweifel kurz fragen.
- Alles, was das Skill sichtet und **nicht** löscht, gehört am Ende in dieses kanonische PARA-Home einsortiert — nicht im Durchgangsordner (Downloads/Desktop) liegen gelassen, egal welchen Ordner das Skill gerade geprüft hat.

### Redundanz-Loop beim Ablegen

Immer wenn neue Dateien in einen Zielordner gelegt werden, danach prüfen, ob im **gesamten Zielordner** schon inhaltlich Redundantes liegt — und zwar **inhaltsbasiert (SHA-256), nicht nur nach Dateiname**. Zwei Dateien mit völlig verschiedenen Namen können denselben Inhalt haben; genau die findet ein reiner Namensvergleich nicht. Dafür gibt es `scripts/redundanz_check.py` (nutzt intern `dedupe_scan.py`):

- **Exakte Dubletten** (gleicher Hash): automatisch auf die **neueste** Kopie reduzieren — die älteren wandern **reversibel** in die Quarantäne (`_Papierkorb/`, nie `rm`) und ins CSV-Protokoll (undo-fähig via `undo_last_run.py`). Weil der Inhalt byte-identisch ist, ist „neuere behalten" hier unkritisch.
- **Near-Duplicates** (ähnlicher, aber **nicht** identischer Inhalt, z.B. `Vertrag_v1` vs. `Vertrag_v2`): **nur melden, nie automatisch löschen.** „Neuere behalten" ist hier ein schlechtes Kriterium — ein erneuter Download kann neuer, aber schlechter/abgeschnitten sein, und manchmal sind beide Stände fachlich relevant. Diese Entscheidung trifft der Nutzer.
- **Loop bis zum Fixpunkt statt fester Zahl:** Der Check läuft wiederholt, bis ein Durchlauf **nichts Neues** mehr entfernt (Kaskaden-Fälle: nachdem Dubletten weg sind, wird ein Unterordner ggf. zur Teilmenge eines anderen). Ein fixes „3×" wäre willkürlich — eine Hash-Deduplizierung ist deterministisch, ein Loop bringt nur etwas, wenn sich der Zustand zwischen den Durchläufen ändert. Deshalb: bis-stabil, mit **Sicherheits-Cap** (Standard 3 Durchläufe) als Notbremse.
- **Trockenlauf ist Standard**, `--apply` führt aus:
  ```bash
  python3 scripts/redundanz_check.py <zielordner>                       # nur ansehen
  python3 scripts/redundanz_check.py <zielordner> --apply \
      --quarantaene <PARA-Home>/_Papierkorb/aufraeumen-<datum> \
      --log <PARA-Home>/.para-dateiorganisation-log-<datum>.csv
  ```

## Schritt 6: Plan präsentieren, dann bestätigen lassen

Präsentiere immer erst einen vollständigen Plan, bevor irgendetwas verschoben, umbenannt oder gelöscht wird — aufgeteilt in die vier Kategorien:

1. Umbenennungen (alt → neu)
2. Löschkandidaten (mit Begründung, getrennt nach "sicher" und "bitte prüfen")
3. Erkannte Duplikate/Near-Duplicates (mit Empfehlung, welche Version bleibt)
4. Zielordner-Zuordnung (inkl. neu anzulegender Ordner)

Führe die Aktionen erst nach expliziter, separater Bestätigung durch den Nutzer aus — eine Aufforderung wie "räum die Downloads auf" ist die Erlaubnis zu analysieren und einen Plan zu erstellen, nicht die Erlaubnis, Dateien zu verschieben oder zu löschen. Bestätigung kann kategorienweise erfolgen (z.B. Umbenennungen ja, Löschungen erst nach Rückfrage).

**Bei der Ausführung — zwei Dinge, die die Aktion nachvollziehbar und sicher machen:**

- **Protokoll führen:** Jede tatsächlich ausgeführte Umbenennung/Verschiebung/Löschung (alt-Pfad, neu-Pfad bzw. Papierkorb-Ziel, Zeitstempel) in eine Log-Datei schreiben (z.B. `<zielverzeichnis>/.para-dateiorganisation-log-<datum>.csv`). Bei 50+ betroffenen Dateien ist das der einzige Weg, Wochen später noch nachvollziehen zu können, was wohin gewandert ist. Die Kopfzeile (`zeitstempel;aktion;alt;neu`) nur schreiben, wenn die Log-Datei noch nicht existiert — bei mehreren Aufräum-Läufen am selben Tag wird sonst mitten im Protokoll ein zweiter Header eingefügt, der die CSV zerbricht. Also: existiert die Datei → nur anhängen; existiert sie nicht → erst Header, dann anhängen.
- **Gebündelt statt einzeln ausführen:** Viele Einzel-Verschiebungen als ein zusammenhängendes Bash-Kommando (Schleife oder mehrere `mv`-Zeilen in einem Aufruf) statt Datei für Datei einzeln aufzurufen — spart Zeit und macht das Protokollieren einfacher.
- **Manifest fortschreiben (Idempotenz):** Nach dem Verschieben die am Ziel gelandeten Dateien ins Manifest eintragen, damit ein späterer Lauf sie nicht erneut vorschlägt:
  ```bash
  python3 scripts/manifest.py record <PARA-Home>/.para-manifest.jsonl <ziel1> <ziel2> ...
  ```
  Und **vor** dem Vorschlagen (Schritt 1/6) die Quelldateien dagegen prüfen — schon Einsortiertes überspringen:
  ```bash
  python3 scripts/manifest.py check <PARA-Home>/.para-manifest.jsonl <quelle1> <quelle2> ... --json
  ```
  `check` erkennt bereits Verarbeitetes am Inhalts-Hash, also auch dann, wenn die Datei erneut unter anderem Namen heruntergeladen wurde. Das Manifest ist der günstige, inkrementelle Gegenpart zu `dedupe_scan.py --against` (das den ganzen Ziel-Baum hasht).
- **Rückgängig machen (Undo):** Weil das Protokoll `neu`-Pfade festhält, lässt sich ein Lauf komplett zurücknehmen — jede Bewegung ist `neu → alt`, egal ob Umbenennung, Verschiebung oder Quarantäne. Dafür gibt es `scripts/undo_last_run.py`. Standard ist ein **Trockenlauf** (nur Plan, nichts wird bewegt); erst `--apply` führt aus. Es überschreibt nie ein wieder existierendes `alt` und meldet fehlende Quellen, statt zu crashen:
  ```bash
  python3 scripts/undo_last_run.py <zielverzeichnis>            # Trockenlauf: was würde zurückgenommen
  python3 scripts/undo_last_run.py <zielverzeichnis> --apply    # ausführen
  python3 scripts/undo_last_run.py <zielverzeichnis> --tag N --apply   # nur die letzten N Aktionen
  ```
  Genutzt wird automatisch die **neueste** Log-Datei im Verzeichnis. Fanden mehrere Läufe am selben Tag statt (eine gemeinsame Tagesdatei), grenzt `--tag N` auf die letzten N protokollierten Aktionen ein.

## Home-weiter Scan (mehrere Ordner auf einmal)

Wenn der Nutzer „alles aufräumen / das ganze System prüfen" möchte: das ist **nicht** wörtlich das gesamte Dateisystem (sinnlos und riskant), sondern die persönlichen Ablageorte im Home (Downloads, Desktop, lose Dokumente). Scan-Wurzeln, harte Ausschlüsse und `.para-ignore` sind in `references/konfiguration.md` beschrieben. Auch hier gilt Schritt 6: erst vollständiger Plan, dann Freigabe. Bereits Einsortiertes über das Manifest überspringen (Idempotenz).

## Optional: Schicht-2-Automatik (lokaler Wächter, ohne LLM)

Für Nutzer, die nicht jedes Mal manuell anstoßen wollen, gibt es einen **rein lokalen** Vor-Sortierer `scripts/triage.py` — kein LLM, keine Cloud. Er ist als Kern eines Ordner-Wächters gedacht und läuft an, sobald neue Dateien in einem Durchgangsordner auftauchen:

- **Müll → Quarantäne:** eindeutige Wegwerf-Artefakte (`.DS_Store`, `~$*`, `*.crdownload`/`*.part`, 0-Byte) wandern nach `_Papierkorb/` — reversibel, nie `rm`.
- **Hashen + Dedup gegen das Home** (`--against-home`) und **Idempotenz** über das Manifest (`--manifest`): schon Einsortiertes/schon in der Queue Stehendes wird nicht erneut angefasst.
- **Lokale, geschwärzte Metadaten** für Inhaltsdateien; diese landen als JSON-Zeile in einer Queue (`.para-triage-queue.jsonl`) zur späteren, **bestätigten** Einsortierung. `triage.py` **verschiebt Inhaltsdateien nie selbst** — kein Auto-Verschieben sensibler Dateien.
- **Trockenlauf als Standard**, `--apply` führt aus. Jede Quarantäne-Bewegung geht ins selbe CSV-Protokoll, also von `undo_last_run.py` zurücknehmbar.

```bash
python3 scripts/triage.py <Durchgangsordner>                       # Trockenlauf ansehen
python3 scripts/triage.py <Durchgangsordner> --apply --notify \
  --manifest <PARA-Home>/.para-manifest.jsonl --against-home <PARA-Home>
```

Die eigentliche Automatik-Aktivierung (macOS `launchd`, Linux `systemd`, Windows Task Scheduler) liegt als **Vorlage** in `assets/` — bewusst nicht geladen, der Nutzer aktiviert sie selbst (siehe `assets/README.md`).

## Referenzen

- `references/konfiguration.md` — Ziel-Ort/PARA-Home ermitteln, Benennung erkennen, Plattform bestimmen, Scan-Wurzeln/Ausschlüsse, Idempotenz-Manifest. **Zuerst hier klären, wohin einsortiert wird**, bevor Schritt 5 ausgeführt wird.
- `references/kuerzel-liste.md` — erweiterbares Beispiel-Set der Dokumenttyp-Kürzel, bei Bedarf ergänzen/anpassen
- `scripts/dedupe_scan.py` — Hash- und Textähnlichkeits-basierte Duplikaterkennung; mit `--against <PARA-Home>` auch Abgleich gegen das Ziel-Home (verhindert erneuten Import inhaltsgleicher Dateien) (Nutzung siehe Schritt 4)
- `scripts/redundanz_check.py` — Redundanz-Loop beim Ablegen: prüft einen Zielordner inhaltlich (SHA-256), reduziert **exakte** Dubletten auf die neueste Kopie (Verlierer reversibel → Quarantäne + Log, undo-fähig), meldet **Near-Duplicates** nur, läuft bis-stabil mit Cap (Standard 3). Trockenlauf als Standard, `--apply` führt aus (Nutzung siehe „Redundanz-Loop beim Ablegen" in Schritt 5)
- `scripts/undo_last_run.py` — nimmt die Bewegungen eines Aufräum-Laufs aus dem CSV-Protokoll zurück (`neu → alt`); Trockenlauf als Standard, `--apply` führt aus, überschreibt nie (Nutzung siehe Schritt 6)
- `scripts/triage.py` — lokaler Wächter-Kern (Schicht 2, ohne LLM): Müll → Quarantäne, Hashen, Dedup gegen Home, lokale geschwärzte Metadaten, neue Dateien in eine Queue; idempotent via Manifest, Trockenlauf als Standard (Nutzung siehe „Schicht-2-Automatik")
- `assets/` — Wächter-Vorlagen (launchd/systemd/Task Scheduler) für `triage.py`, plattform-erkennend und **nicht automatisch geladen**; Installations- und Sicherheitshinweise in `assets/README.md`
- `tests/` — synthetische Tests (nur Wegwerf-Daten); gebündelt über `python3 tests/run_all.py`. Konfigurierbar per Umgebungsvariablen: `PARA_PDF_MAX_PAGES` (gelesene PDF-Seiten), `PARA_DOCX_MAX_PARAGRAPHS`, `PARA_OCR_LANG` (OCR-Sprache, auch als `--lang`)
- `scripts/manifest.py` — Idempotenz-Manifest (`.para-manifest.jsonl`): `record` schreibt verarbeitete Dateien fort, `check` überspringt bereits Einsortiertes anhand des Inhalts-Hashes (Nutzung siehe Schritt 5)
- `scripts/extract_metadata.py` — lokale, datenschutzschonende Metadaten-Extraktion (Datum/Kürzel/Absender-Hinweis) mit automatischer Schwärzung von IBAN (deutsch + international), E-Mail, Kreditkarte (Luhn-geprüft), Kontonummer, Steuer-ID, Sozialversicherungsnummer, Beträgen, Adressen, Telefonnummern und langen Ziffernblöcken — Schwärzung ist Risiko-Reduktion, kein Schutz (Nutzung siehe Schritt 1). Die Kürzel-Erkennung matcht an **Wortgrenzen** (kein Teiltreffer wie „Vertrag" in „vertraglich"), gewinnt nach **Häufigkeit** (nicht Tabellenreihenfolge) und **meldet Mehrdeutigkeit** aktiv (`kuerzel_alternativen` + Warnung), wenn mehrere Dokumenttypen im Text vorkommen — ein `confidence: "high"` bleibt trotzdem prüfpflichtig.
- `tests/test_redact.py` — synthetische Tests für die Schwärzung (`python3 tests/test_redact.py`, keine externen Abhängigkeiten)
- `tests/test_manifest_and_dedupe.py` — synthetische Tests für Manifest-Idempotenz und Dedup gegen das Ziel-Home (`python3 tests/test_manifest_and_dedupe.py`)
- `scripts/extract_image_metadata.py` — dasselbe für Bilder (EXIF-Datum + lokale OCR statt Vision), verweigert bei Ausweisdokument-Verdacht aus Prinzip (Nutzung siehe Schritt 1)
