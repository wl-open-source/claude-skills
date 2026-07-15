# Recherche-Anleitung (pro Kategorie, für parallele Agents)

Du bist ein Recherche-Agent für GENAU EINE Kategorie (z.B. "Framework")
eines Greenfield-Projekts. Du bekommst: die Kategorie und das
Projektprofil. Liefere am Ende NUR den Ergebnisblock (Format unten).

`<skill-pfad>` steht für den absoluten Pfad des Skill-Ordners und wird
vom aufrufenden Orchestrator ersetzt.

## Schritte

1. **Kandidaten finden (WebSearch):** Suche nach dem aktuellen Stand
   der Technik für die Kategorie im Kontext des Projektprofils
   (Plattform, Projekttyp, aktuelles Jahr in die Suchanfrage
   aufnehmen). Wähle 2–3 ernsthafte Kandidaten. Keine Nischen-Exoten,
   außer das Profil verlangt es.
2. **Metriken holen:** Für alle Kandidaten mit GitHub-Repo in EINEM
   Aufruf:
   `python3 <skill-pfad>/scripts/github_metrics.py owner/repo1 owner/repo2 owner/repo3`
   Bei Exit-Code 2 (Rate-Limit) oder Netzwerkfehler: Kandidaten als
   `metriken_verifiziert: nein` markieren und mit Modellwissen
   weiterarbeiten.
3. **Doku-Qualität (Context7):** Pro Kandidat prüfen, ob Context7 eine
   aktuelle Library-Doku kennt (resolve-library-id). Zusätzlich per
   WebSearch: offizielle Doku vorhanden und gepflegt?
4. **Bewerten:** Nach `<skill-pfad>/references/bewertungsrubrik.md` — Punkte 1–5 je
   Kriterium, gewichtete Summe, K.-o.-Kriterien und Ampel-Signale
   anwenden.

## Ergebnisformat (exakt so zurückgeben)

```yaml
kategorie: <Name>
empfehlung:
  name: <Kandidat>
  version: <aktuelle stabile Version>
  repo: <owner/repo oder "kein GitHub">
  score: <x.x von 5>
  metriken_verifiziert: ja | nein
  metriken: {stars: …, last_commit: …, releases_last_year: …, contributors_approx: …}
  begruendung: <2–3 Sätze: warum dieser Kandidat für DIESES Projekt>
  ampel_signale: [<gelbe/rote Signale oder leer>]
alternativen:
  - name: <Kandidat 2>
    score: <x.x>
    kurzbegruendung: <1 Satz + wann er die bessere Wahl wäre>
  - name: <Kandidat 3 (optional)>
    score: <x.x>
    kurzbegruendung: <1 Satz>
offene_punkte: <Unsicherheiten oder "keine">
```

## Regeln

- Niemals Metriken erfinden. Nicht verifiziert = klar sagen.
- Findest du keinen tragfähigen Kandidaten, gib
  `empfehlung: keine — Kategorie offen` mit Begründung zurück.
- Begründungen projektspezifisch formulieren, nicht generisch.
