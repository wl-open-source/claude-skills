<!--
zweck: Security-Baseline: Secrets, Input-Validierung, AuthN/AuthZ, Abhängigkeits-Sicherheit.
wann-lesen: Vor Arbeit an Auth, Nutzereingaben, externen APIs oder vor jedem Release.
anleitung: Auf den Stack zuschneiden (konkrete Tools/Mechanismen).
OWASP-Punkte nur aufnehmen, wo für das Projekt relevant.
-->
# Sicherheit

## Secrets
{{WO_LIEGEN_SECRETS_WAS_NIE_INS_REPO_DARF_STARTUP_VALIDIERUNG}}

## Input-Validierung
{{VALIDIERUNGS_TOOL_DES_STACKS_REGEL_AN_ALLEN_SYSTEMGRENZEN}}

## Authentifizierung & Autorisierung
{{MECHANISMUS_ODER_ABSCHNITT_ENTFERNEN_WENN_KEIN_AUTH}}

## Abhängigkeits-Sicherheit
{{AUDIT_TOOL_UND_WANN_ES_LAEUFT_CI_DEPENDABOT}}

## Projektspezifische Risiken
{{TOP_RISIKEN_DIESES_PROJEKTS_UND_GEGENMASSNAHMEN}}
