---
name: meeting-summary
description: Summarizes a meeting transcript or rough notes into one fixed, consistent structure (Zusammenfassung, Themen, Entscheidungen, Action Items mit Verantwortlichem/Deadline, offene Fragen, nächste Schritte) — output is always in German, no matter what language the meeting was in. Use this skill whenever the user pastes a meeting transcript, call recording transcript, or rough notes and asks for a summary, protocol, or recap — including phrases like "fass das Meeting zusammen", "Protokoll erstellen", "Notizen vom Call", "Zusammenfassung vom Standup/1:1/Sync", or "summarize this meeting/call". Also trigger when the user pastes a block of dialogue or bullet notes from a meeting without explicitly naming the skill, as long as they're asking for a structured recap rather than just an answer to a question about the content.
---

# Meeting Summary

Verwandelt ein Meeting-Transkript oder Stichpunkt-Notizen in eine strukturierte Zusammenfassung. Der Kernpunkt dieses Skills: die Struktur ist **immer identisch**, egal wie chaotisch oder lückenhaft der Input ist — der Nutzer will sich beim Überfliegen nie neu orientieren müssen.

## Ausgabeformat

Gib IMMER exakt dieses Template aus, auch wenn einzelne Abschnitte leer bleiben (siehe "Umgang mit Lücken" unten). Die Ausgabe ist immer auf Deutsch, unabhängig von der Sprache des Inputs.

```markdown
# Meeting-Zusammenfassung: [Titel/Thema]

**Datum:** [Datum, falls bekannt, sonst "nicht angegeben"]
**Teilnehmer:** [Namen, falls bekannt, sonst "nicht angegeben"]

## Zusammenfassung
[2-3 Sätze TL;DR: worum ging es, was kam dabei heraus]

## Besprochene Themen
- **[Thema 1]:** Kernpunkte
- **[Thema 2]:** Kernpunkte

## Entscheidungen
- [Entscheidung 1]
- [Entscheidung 2]

## Action Items
| Aufgabe | Verantwortlich | Deadline |
|---|---|---|
| ... | ... | ... |

## Offene Fragen
- [Unklarheiten, die noch zu klären sind]

## Nächste Schritte
- [Folgetermin, nächster Meilenstein]
```

## Umgang mit Lücken

Der Input ist selten vollständig — Transkripte haben keine Metadaten, Notizen sind stichpunktartig. Trotzdem die volle Struktur beibehalten:

- Fehlt ein ganzer Abschnitt inhaltlich (z. B. keine offenen Fragen wurden besprochen), schreibe **"Keine"** statt den Abschnitt zu streichen. Die Struktur muss bei jedem Aufruf gleich aussehen, damit sie auf einen Blick vertraut ist.
- Fehlen Datum/Teilnehmer im Transkript, schreibe **"nicht angegeben"** statt zu raten oder das Feld leer zu lassen.
- Bei Action Items: Verantwortlichen und Deadline nur eintragen, wenn sie im Input tatsächlich genannt wurden. Wenn nicht explizit genannt, **"nicht genannt"** eintragen — nichts erfinden, auch wenn aus dem Kontext eine Person naheliegend wirkt.

## Entscheidungen vs. offene Fragen sauber trennen

Das ist der Teil, der am leichtesten durcheinandergerät. Eine "Entscheidung" ist nur, was im Meeting tatsächlich final beschlossen wurde ("wir machen X", "wir gehen mit Variante B"). Alles, was noch zur Diskussion stand, vertagt wurde oder bei dem Uneinigkeit bestand, gehört unter "Offene Fragen" — auch wenn es wie eine Tendenz klang. Im Zweifel lieber unter "Offene Fragen" einsortieren als fälschlich als Entscheidung markieren, denn das hat reale Konsequenzen (jemand handelt danach).

## Action Items extrahieren

Achte auf implizite Zusagen, nicht nur explizite "Action Item: ..."-Markierungen. Sätze wie "ich kümmere mich darum" oder "Anna schickt das bis Freitag" sind Action Items, auch wenn sie beiläufig im Gesprächsfluss fallen. Verantwortliche Person ist die, die die Zusage macht — nicht zwangsläufig die Person, über die gesprochen wird.

## Quellenformate

Funktioniert mit:
- Eingefügten Rohtranskripten (Zoom/Teams/Otter-Export, mit oder ohne Sprecherlabels und Zeitstempeln)
- Stichpunktartigen Notizen, die der Nutzer während/nach dem Meeting eingetippt hat
- Einer Mischung aus beidem

Zeitstempel und Sprecherlabels im Rohtranskript sind nur Hilfsinformation für die Zuordnung von Action Items — sie tauchen nicht in der Zusammenfassung selbst auf.
