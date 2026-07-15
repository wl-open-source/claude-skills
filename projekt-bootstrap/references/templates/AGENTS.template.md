<!--
zweck: Einstiegsdatei für andere KI-Coding-Tools (Cursor, Codex, Gemini CLI …) nach AGENTS.md-Standard.
wann-lesen: Wird von AGENTS.md-kompatiblen Tools automatisch geladen; muss kompakt bleiben.
anleitung: Alle {{PLATZHALTER}} füllen. Tabelle enthält NUR tatsächlich
erzeugte context/-Dateien; Beschreibungen aus deren zweck-Kommentar
übernehmen. Kein Inhalt aus context/-Dateien duplizieren.
-->
# {{PROJEKTNAME}}

Diese Datei wird inhaltsgleich mit CLAUDE.md gepflegt. Änderungen in beiden Dateien nachziehen.

{{EIN_ABSATZ_WAS_DAS_PROJEKT_IST_UND_FUER_WEN}}

## Tech-Stack (Kurzfassung)

{{STACK_IN_3_BIS_5_ZEILEN_DETAILS_IN_CONTEXT_TECH_STACK}}

## Context-Dateien

Vor Arbeit am jeweiligen Thema die passende Datei lesen:

| Datei | Wann lesen |
|---|---|
| `context/projekt-brief.md` | {{BESCHREIBUNG_AUS_ZWECK}} |
| `context/architektur.md` | {{BESCHREIBUNG_AUS_ZWECK}} |
| `context/tech-stack.md` | {{BESCHREIBUNG_AUS_ZWECK}} |
{{WEITERE_ZEILEN_FUER_ALLE_ERZEUGTEN_DATEIEN}}

## Conventions

- {{PROJEKTSPEZIFISCHE_REGELN_BUILD_TEST_LINT_BEFEHLE_BRANCH_KONVENTION}}
