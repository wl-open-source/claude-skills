#!/usr/bin/env python3
"""Extrahiert lokal Umbenennungs-relevante Metadaten aus Dokumenten (Datum,
Dokumenttyp-Kürzel, grober Absender), OHNE sensible Details wie IBAN,
Kontonummer, Steuer-ID, Sozialversicherungsnummer, genaue Beträge, Adressen
oder Telefonnummern preiszugeben.

Läuft komplett lokal (kein Netzwerkzugriff). Gedacht als Vorstufe, BEVOR ein
Dokument mit dem Read-Tool geöffnet wird: bei eindeutigem Treffer liefert
dieses Skript direkt einen fertigen Dateinamensvorschlag, ohne dass der
volle Dokumenttext je in den Modell-Kontext gelangt. Nur wenn kein
eindeutiger Treffer möglich ist, wird ein bereits geschwärzter Kurzausschnitt
zurückgegeben, den man sich ansehen kann.
"""

import argparse
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KUERZEL_LISTE_PATH = os.path.join(SCRIPT_DIR, "..", "references", "kuerzel-liste.md")


def _int_env(name, default):
    """Positiver Integer aus der Umgebung, sonst der Default (robust gegen Müll)."""
    try:
        wert = int(os.environ.get(name, default))
        return wert if wert >= 1 else default
    except (TypeError, ValueError):
        return default


# Wie viel eines Dokuments lokal gelesen wird. Für Datum/Dokumenttyp/Absender
# reichen die ersten Seiten; per Umgebungsvariable erhöhbar, falls das Datum
# erst auf einer späteren Seite steht.
PDF_MAX_PAGES = _int_env("PARA_PDF_MAX_PAGES", 3)
DOCX_MAX_PARAGRAPHS = _int_env("PARA_DOCX_MAX_PARAGRAPHS", 60)

def _luhn_ok(digits):
    """Luhn-Prüfsumme (Standard für Kredit-/Debitkarten). digits ist ein reiner
    Ziffern-String."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _redact_credit_card(match):
    """Schwärzt eine 13-19-stellige Zifferngruppe nur, wenn sie die Luhn-Prüfung
    besteht — so bleiben zufällige lange Zahlen (Bestell-/Sendungsnummern) mit dem
    präzisen Label unbehelligt, während echte Kartennummern zuverlässig getroffen
    werden. Luhn-negative, aber trotzdem lange Ziffernfolgen fängt danach der
    generische Fang-Rest [NUMMER] ab, es entweicht also nichts."""
    digits = re.sub(r"\D", "", match.group(0))
    if 13 <= len(digits) <= 19 and _luhn_ok(digits):
        return "[KREDITKARTE]"
    return match.group(0)


# Reihenfolge ist bewusst: spezifische, gut gelabelte Muster zuerst, generischer
# Fang-Rest (lange Ziffernblöcke) GANZ zuletzt — sonst würde er Telefon/IBAN/Karte
# vorzeitig zu einem unspezifischen [NUMMER] zusammenziehen. Grundhaltung: im
# Zweifel lieber zu viel schwärzen (Über-Schwärzung kostet nur Kontext, ein Leak
# kostet Vertrauen).
REDACT_PATTERNS = [
    # E-Mail zuerst: kann Ziffern/Punkte enthalten, darf nicht von Zahlen-Mustern zerlegt werden
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    # IBAN: erst DE-spezifisch (streng), dann generisch international
    # (2 Länder-Buchstaben, 2 Prüfziffern, 11-30 alphanumerische Zeichen, optional in Gruppen)
    (re.compile(r"\bDE\d{2}\s?(?:\d{4}\s?){4}\d{2}\b"), "[IBAN]"),
    (re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Za-z0-9]){11,30}\b"), "[IBAN]"),
    # Kreditkarte mit Luhn-Prüfung (Funktion als Replacement, siehe oben)
    (re.compile(r"\b(?:\d[ \-]?){13,19}\b"), _redact_credit_card),
    (re.compile(r"\b\d{2}\s?\d{2}\s?\d{2}\s?[A-Z]\s?\d{3}\b"), "[SV-NUMMER]"),
    (re.compile(r"\b(?:Steuer-?ID|Identifikationsnummer)\s*:?\s*\d[\d\s]{9,14}\d\b", re.I), "[STEUER-ID]"),
    (re.compile(r"\b(?:Konto-?Nr\.?|Kontonummer|Kundennummer|Aktenzeichen|Vertragsnummer)\s*:?\s*[\w\-/]+", re.I), "[KUNDEN-/KONTONUMMER]"),
    (re.compile(r"\b\d{1,3}(?:[.,]\d{3})*,\d{2}\s?(?:€|EUR)\b"), "[BETRAG]"),
    (re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+)*\b"), "[PLZ-ORT]"),
    (re.compile(r"\b(?:\+49[\s\-]?|0)\d{2,5}[\s\-/]?\d{3,10}\b"), "[TELEFON]"),
    (re.compile(r"\b(?:Herrn?|Frau)\s+[A-ZÄÖÜ][\wÄÖÜäöüß\-]+(?:\s+[A-ZÄÖÜ][\wÄÖÜäöüß\-]+){0,2}"), "[NAME]"),
    (re.compile(
        r"\b[A-ZÄÖÜ][\wÄÖÜäöüß\.\-]*(?:straße|strasse|str\.|weg|allee|platz|gasse)\s+\d+\s?[a-z]?\b",
        re.IGNORECASE,
    ), "[ADRESSE]"),
    # Generischer Fang-Rest GANZ zuletzt: lange Ziffernblöcke ohne eigenes Label
    # (Kunden-/Fall-/Vorgangsnummern, unformatierte Kartennummern). Datumsangaben
    # (TT.MM.JJJJ, ISO JJJJ-MM-TT) enthalten keine 9+ zusammenhängenden Ziffern und
    # bleiben unberührt — wichtig, weil find_date auf dem geschwärzten Text arbeitet.
    (re.compile(r"\b\d{9,}\b"), "[NUMMER]"),
]

DATE_PATTERN_DMY = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
DATE_PATTERN_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

SENDER_HINT_PATTERN = re.compile(
    r"^.*\b(?:GmbH|AG|KG|e\.\s?V\.|Jobcenter|Amt|Agentur für Arbeit|Bank|Versicherung|"
    r"Behörde|Finanzamt|Stadt(?:verwaltung)?|Gemeinde|Kanzlei)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)


def load_kuerzel_map():
    """Liest references/kuerzel-liste.md, damit die Kürzel-Tabelle nur an
    einer Stelle gepflegt werden muss (dort, nicht hier im Skript)."""
    mapping = {}
    if not os.path.isfile(KUERZEL_LISTE_PATH):
        return mapping
    with open(KUERZEL_LISTE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\|\s*([A-ZÄÖÜ]+)\s*\|\s*([^|]+?)\s*\|\s*$", line)
            if m:
                kuerzel, doku_typ = m.group(1), m.group(2)
                if kuerzel == "Kürzel":
                    continue
                mapping[kuerzel] = doku_typ
    return mapping


LETTER_SPACING_PATTERN = re.compile(r"(?:\S ){2,}\S")
GARBLED_SHORT_TOKEN_RATIO = 0.35


def collapse_letter_spacing(text):
    """Manche PDF-Formulare extrahieren Text mit einzeln durch Leerzeichen
    getrennten Zeichen ("W i l h e l m"). Versucht das zusammenzuziehen -
    hilft bei sauber-regelmäßigem Spacing, aber NICHT verlässlich bei
    unregelmäßigem Spacing (siehe is_garbled unten, das ist das eigentliche
    Sicherheitsnetz)."""

    def collapse(match):
        return match.group(0).replace(" ", "")

    return LETTER_SPACING_PATTERN.sub(collapse, text)


def is_garbled(text):
    """Manche Formular-PDFs zerstückeln Wörter beim Textextrahieren in
    Gruppen wechselnder Länge (nicht gleichmäßig 1 Zeichen), z.B.
    "Jo b ce n t e r" statt "Jobcenter". collapse_letter_spacing kann so
    etwas nicht zuverlässig reparieren - und ungenau reparierter Text ist
    gefährlich, weil Namens-/Adress-Erkennung dann still versagen kann
    (siehe echter Vorfall, der zu dieser Funktion geführt hat). Deshalb:
    lieber zuverlässig erkennen "das ist wahrscheinlich Datenmüll" und
    GAR NICHTS ausgeben, statt einen Reparaturversuch zu riskieren, der
    wieder unbemerkt scheitert. Kriterium: ungewöhnlich viele sehr kurze
    Tokens (normales Deutsch hat auch kurze Wörter wie "zu", "in", aber
    nicht in diesem Ausmaß)."""
    tokens = text.split()
    if len(tokens) < 20:
        return False
    short_tokens = sum(1 for t in tokens if len(t) <= 2)
    return (short_tokens / len(tokens)) > GARBLED_SHORT_TOKEN_RATIO


def redact(text):
    for pattern, replacement in REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def find_date(text):
    m = DATE_PATTERN_ISO.search(text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = DATE_PATTERN_DMY.search(text)
    if m:
        day, month, year = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{year}-{month}-{day}"
    return None


def _kuerzel_variants(doku_typ):
    """Aus einer Dokumenttyp-Zelle die einzelnen Suchbegriffe gewinnen.
    Parenthetische Qualifizierer ("Bescheid (Behörde/Amt)") werden entfernt,
    danach an "/" getrennt und Rand-Sonderzeichen (z.B. "Reise-") gestutzt.
    Fragmente unter 3 Zeichen fallen weg (zu unspezifisch)."""
    ohne_klammern = re.sub(r"\([^)]*\)", " ", doku_typ)
    varianten = []
    for teil in ohne_klammern.split("/"):
        teil = teil.strip().strip("-–—").strip().lower()
        if len(teil) >= 3:
            varianten.append(teil)
    return varianten


def find_kuerzel(text, kuerzel_map):
    """Erkennt den Dokumenttyp am Vorkommen seiner Bezeichner im Text.

    Verbesserungen gegenüber naivem Teilstring-Matching:
    * **Wortgrenzen** (`(?<!\\w)…(?!\\w)`, umlaut-/unicode-fest): „Vertrag" matcht
      nicht mehr in „vertraglich"/„Vertragswerkstatt".
    * **Häufigkeit statt Dict-Reihenfolge:** Kommt „Rechnung" dreimal und
      „Vertrag" einmal vor, gewinnt Rechnung — unabhängig von der Tabellen-
      reihenfolge. Gleichstand wird über die spezifischere (längere) Variante
      und erst zuletzt über die Reihenfolge aufgelöst (deterministisch).
    * **Mehrdeutigkeit wird gemeldet:** alle weiteren getroffenen Kürzel kommen
      als `alternativen` zurück, damit der Aufrufer aktiv warnen kann.

    Rückgabe: (kuerzel, quelle, alternativen). `quelle` ist das auslösende Wort
    (zum Gegenchecken), `alternativen` eine Liste von
    {kuerzel, quelle, treffer} der übrigen Fundstellen (nach Stärke sortiert)."""
    treffer = []
    for order, (kuerzel, doku_typ) in enumerate(kuerzel_map.items()):
        beste_variant, beste_anzahl = None, 0
        for variant in _kuerzel_variants(doku_typ):
            pattern = re.compile(r"(?<!\w)" + re.escape(variant) + r"(?!\w)", re.IGNORECASE)
            anzahl = len(pattern.findall(text))
            if anzahl > beste_anzahl:
                beste_variant, beste_anzahl = variant, anzahl
        if beste_anzahl > 0:
            treffer.append({"kuerzel": kuerzel, "quelle": beste_variant,
                            "treffer": beste_anzahl, "_order": order})
    if not treffer:
        return None, None, []
    # Gewinner: meiste Treffer, dann spezifischste (längste) Variante, dann Reihenfolge.
    treffer.sort(key=lambda e: (-e["treffer"], -len(e["quelle"]), e["_order"]))
    gewinner = treffer[0]
    alternativen = [{"kuerzel": e["kuerzel"], "quelle": e["quelle"], "treffer": e["treffer"]}
                    for e in treffer[1:]]
    return gewinner["kuerzel"], gewinner["quelle"], alternativen


def find_sender_hint(redacted_text):
    m = SENDER_HINT_PATTERN.search(redacted_text)
    if m:
        return m.group(0).strip()[:80]
    return None


def extract_text(path, ext, warnings, max_pages=None, max_paragraphs=None):
    max_pages = PDF_MAX_PAGES if max_pages is None else max(1, max_pages)
    max_paragraphs = DOCX_MAX_PARAGRAPHS if max_paragraphs is None else max(1, max_paragraphs)
    if ext in (".txt", ".md"):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except OSError as e:
            warnings.append(f"Konnte Text nicht lesen: {path} ({e})")
            return None

    if ext == ".pdf":
        try:
            import pypdf
        except ImportError:
            warnings.append(
                "pypdf nicht installiert — kann PDF nicht lokal analysieren "
                "(pip install pypdf). Datei muss ggf. manuell benannt werden."
            )
            return None
        try:
            reader = pypdf.PdfReader(path)
            # Nur die ersten Seiten reichen für Datum/Dokumenttyp/Absender -
            # spart Zeit bei langen Dokumenten und begrenzt ohnehin, wie viel
            # Text potenziell weiterverarbeitet wird. Grenze via PARA_PDF_MAX_PAGES
            # erhöhbar, falls das Datum erst später im Dokument steht.
            pages = reader.pages[:max_pages]
            return "\n".join((p.extract_text() or "") for p in pages)
        except Exception as e:
            warnings.append(f"Konnte PDF nicht lesen: {path} ({e})")
            return None

    if ext == ".docx":
        try:
            import docx
        except ImportError:
            warnings.append(
                "python-docx nicht installiert — kann DOCX nicht lokal analysieren "
                "(pip install python-docx)."
            )
            return None
        try:
            document = docx.Document(path)
            return "\n".join(p.text for p in document.paragraphs[:max_paragraphs])
        except Exception as e:
            warnings.append(f"Konnte DOCX nicht lesen: {path} ({e})")
            return None

    warnings.append(f"Dateityp {ext} wird von diesem Skript nicht unterstützt: {path}")
    return None


def analyze(path, kuerzel_map):
    warnings = []
    ext = os.path.splitext(path)[1].lower()
    text = extract_text(path, ext, warnings)

    result = {
        "file": path,
        "confidence": "low",
        "erkanntes_datum": None,
        "erkanntes_kuerzel": None,
        "kuerzel_quelle": None,
        "kuerzel_alternativen": None,
        "absender_hinweis": None,
        "vorschlag_dateiname": None,
        "redigierter_ausschnitt": None,
        "warnungen": warnings,
    }

    if not text or not text.strip():
        result["warnungen"].append("Kein Text extrahierbar — Datei braucht manuelle Prüfung.")
        return result

    text = collapse_letter_spacing(text)

    if is_garbled(text):
        result["warnungen"].append(
            "Text-Extraktion wirkt zerstückelt/unzuverlässig (bekanntes Problem bei "
            "manchen Formular-PDFs) — automatische Schwärzung wäre hier nicht "
            "vertrauenswürdig. Kein Ausschnitt ausgegeben, Datei braucht manuelle "
            "Entscheidung durch den Nutzer statt automatischer Erkennung."
        )
        return result

    redacted = redact(text)
    date = find_date(redacted)
    kuerzel, kuerzel_quelle, kuerzel_alternativen = find_kuerzel(redacted, kuerzel_map)
    sender_hint = find_sender_hint(redacted)

    result["erkanntes_datum"] = date
    result["erkanntes_kuerzel"] = kuerzel
    result["kuerzel_quelle"] = kuerzel_quelle
    result["kuerzel_alternativen"] = kuerzel_alternativen or None
    result["absender_hinweis"] = sender_hint

    if date and kuerzel:
        result["confidence"] = "high"
        if kuerzel_alternativen:
            andere = ", ".join(f"{a['kuerzel']} ({a['quelle']}×{a['treffer']})"
                               for a in kuerzel_alternativen)
            result["warnungen"].append(
                f"Mehrdeutiger Dokumenttyp: neben {kuerzel} auch {andere} erkannt — "
                f"Kürzel bitte prüfen, nicht ungeprüft übernehmen."
            )
        sender_slug = re.sub(r"[^A-Za-z0-9]+", "-", sender_hint).strip("-") if sender_hint else "ABSENDER-PRUEFEN"
        result["vorschlag_dateiname"] = f"{date}_{kuerzel}_{sender_slug}{ext}"
    else:
        # Kein sicherer Treffer -> nur ein bereits geschwärzter Kurzausschnitt
        # weitergeben, nie den vollen Text.
        snippet = redacted.strip().replace("\n", " ")
        result["redigierter_ausschnitt"] = snippet[:400]

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="Ein oder mehrere Dateipfade")
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Klartext")
    args = parser.parse_args()

    kuerzel_map = load_kuerzel_map()
    results = [analyze(path, kuerzel_map) for path in args.files]

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print(f"\n{r['file']}")
            print(f"  Konfidenz: {r['confidence']}")
            if r["vorschlag_dateiname"]:
                print(f"  Vorschlag: {r['vorschlag_dateiname']}")
            if r["redigierter_ausschnitt"]:
                print(f"  Ausschnitt (geschwärzt): {r['redigierter_ausschnitt']}")
            for w in r["warnungen"]:
                print(f"  Hinweis: {w}")


if __name__ == "__main__":
    main()
