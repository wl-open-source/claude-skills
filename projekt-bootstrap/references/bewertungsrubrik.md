# Bewertungsrubrik für Stack-Kandidaten

Jeder Kandidat bekommt pro Kriterium 1–5 Punkte; Gesamtscore =
gewichtete Summe. Empfehlung = höchster Score, sofern kein K.-o.

## Gewichte

| Kriterium | Gewicht | Datenquelle |
|---|---|---|
| Aktualität / Wartung | 25 % | `last_commit`, `releases_last_year`, `archived` |
| Community-Größe / Beliebtheit | 25 % | `stars`, `contributors_approx`, WebSearch (Umfragen, Downloads) |
| Doku-Qualität | 20 % | Context7-Abdeckung, offizielle Doku (WebSearch) |
| Robustheit / Reife | 20 % | Alter, `issues_per_1k_stars`, Major-Version ≥ 1, bekannte Produktionsnutzer |
| Ökosystem-Fit | 10 % | Verträglichkeit mit bereits gesetzten Kategorien des Vorschlags |

## K.-o.-Kriterien (disqualifizieren unabhängig vom Score)

- `archived: true`
- `last_commit` älter als 24 Monate
- Offiziell deprecated / Nachfolger existiert

## Ampel-Schwellen (in der Vorschlagstabelle ausweisen)

| Signal | Gelb | Rot |
|---|---|---|
| `last_commit` | > 6 Monate | > 12 Monate |
| `releases_last_year` | 0–1 | 0 UND `last_commit` > 12 Monate |
| `stars` | < 2 000 (außer Nischen-Ökosystem — dann begründen) | < 300 |
| `contributors_approx` | < 20 | < 5 (Bus-Faktor) |
| `issues_per_1k_stars` | > 150 | — (nur Hinweis, nie allein rot) |

## Punktevergabe (Richtwerte)

- 5 = führend in der Kategorie, keine gelben Signale
- 4 = solide, höchstens ein gelbes Signal
- 3 = brauchbar, mehrere gelbe Signale oder junge Reife
- 2 = riskant, rotes Signal vorhanden
- 1 = ungeeignet

## Regeln

- Metriken stammen aus `scripts/github_metrics.py`. Konnte das Script
  nicht laufen (kein Netz, Rate-Limit), Kandidaten als
  **"Metriken nicht live verifiziert"** kennzeichnen — niemals Zahlen
  schätzen und als echt ausgeben.
- Score-Gleichstand (< 0,3 Differenz): nach Ökosystem-Fit entscheiden
  und explizit begründen.
- Nicht-GitHub-Kandidaten (z.B. kommerzielle Produkte): Kriterien
  Aktualität, Doku, Robustheit per WebSearch belegen, Community per
  Umfragen/Marktanteil.
