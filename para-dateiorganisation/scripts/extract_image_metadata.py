#!/usr/bin/env python3
"""Extrahiert lokal Umbenennungs-relevante Metadaten aus Bildern (Screenshots,
Fotos): EXIF-Aufnahmedatum + lokale OCR-Texterkennung (Deutsch+Englisch),
mit derselben Schwärzung wie extract_metadata.py (IBAN, Kontonummer,
Beträge, Adressen, Namen, Telefonnummern).

Läuft komplett lokal (kein Netzwerkzugriff, OCR über tesseract). Gedacht als
Vorstufe, BEVOR ein Bild überhaupt inhaltlich betrachtet wird (Vision) -
bei eindeutigem Treffer liefert dieses Skript direkt einen
Dateinamensvorschlag, ohne dass das Bild je in den Modell-Kontext gelangt.

Ausweisdokumente (Personalausweis, Reisepass, Führerschein u.ä.) werden
NIE per OCR/Vision verarbeitet, auch nicht hierüber - siehe SKILL.md
Schritt 1. Dieses Skript verweigert bei solchen Dateinamen aus Prinzip.
"""

import argparse
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from extract_metadata import (  # noqa: E402
    redact,
    collapse_letter_spacing,
    is_garbled,
    find_date,
    find_kuerzel,
    find_sender_hint,
    load_kuerzel_map,
)

ID_DOCUMENT_MARKERS = re.compile(
    r"personalausweis|reisepass|f[üu]hrerschein|ausweis|passport|identity[-_]?card",
    re.IGNORECASE,
)

EXIF_DATE_TAGS = ["EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"]


def exif_date(path, warnings):
    try:
        import exifread
    except ImportError:
        warnings.append("exifread nicht installiert — kein EXIF-Datum verfügbar.")
        return None
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=False)
    except Exception as e:
        warnings.append(f"Konnte EXIF nicht lesen: {path} ({e})")
        return None
    for tag_name in EXIF_DATE_TAGS:
        if tag_name in tags:
            raw = str(tags[tag_name])  # Format: "YYYY:MM:DD HH:MM:SS"
            m = re.match(r"(\d{4}):(\d{2}):(\d{2})", raw)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


# OCR-Sprache: Standard deutsch+englisch, per Umgebungsvariable/CLI überschreibbar
# (z.B. "eng" oder "deu+eng+fra"), je nach installierten Tesseract-Sprachpaketen.
OCR_LANG = os.environ.get("PARA_OCR_LANG", "deu+eng")


def ocr_text(path, warnings, lang=None):
    lang = lang or OCR_LANG
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        warnings.append("pytesseract/Pillow nicht installiert — keine OCR möglich.")
        return None
    try:
        with Image.open(path) as img:
            return pytesseract.image_to_string(img, lang=lang)
    except Exception as e:
        warnings.append(f"OCR fehlgeschlagen: {path} ({e})")
        return None


def analyze(path, kuerzel_map, ocr_lang=None):
    warnings = []
    result = {
        "file": path,
        "confidence": "low",
        "ist_ausweisdokument_verdacht": False,
        "exif_datum": None,
        "erkanntes_datum": None,
        "erkanntes_kuerzel": None,
        "kuerzel_quelle": None,
        "kuerzel_alternativen": None,
        "absender_hinweis": None,
        "vorschlag_dateiname": None,
        "redigierter_ausschnitt": None,
        "warnungen": warnings,
    }

    if ID_DOCUMENT_MARKERS.search(os.path.basename(path)):
        result["ist_ausweisdokument_verdacht"] = True
        warnings.append(
            "Dateiname deutet auf Ausweisdokument hin — wird NICHT per OCR/Vision "
            "analysiert. Nur nach Dateiname behandeln."
        )
        return result

    result["exif_datum"] = exif_date(path, warnings)
    text = ocr_text(path, warnings, lang=ocr_lang)

    if not text or not text.strip():
        return result

    text = collapse_letter_spacing(text)

    if is_garbled(text):
        warnings.append(
            "OCR-Text wirkt zerstückelt/unzuverlässig — automatische Schwärzung "
            "wäre hier nicht vertrauenswürdig. Kein Ausschnitt ausgegeben."
        )
        return result

    redacted = redact(text)
    date = find_date(redacted) or result["exif_datum"]
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
        ext = os.path.splitext(path)[1].lower()
        sender_slug = re.sub(r"[^A-Za-z0-9]+", "-", sender_hint).strip("-") if sender_hint else "Screenshot"
        result["vorschlag_dateiname"] = f"{date}_{kuerzel}_{sender_slug}{ext}"
    else:
        snippet = redacted.strip().replace("\n", " ")
        result["redigierter_ausschnitt"] = snippet[:400]

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="Ein oder mehrere Bildpfade")
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Klartext")
    parser.add_argument("--lang", default=None,
                        help=f"OCR-Sprache (Standard: {OCR_LANG}, via PARA_OCR_LANG änderbar), "
                             "z.B. 'eng' oder 'deu+eng+fra'")
    args = parser.parse_args()

    kuerzel_map = load_kuerzel_map()
    results = [analyze(path, kuerzel_map, ocr_lang=args.lang) for path in args.files]

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print(f"\n{r['file']}")
            print(f"  Konfidenz: {r['confidence']}, EXIF-Datum: {r['exif_datum']}")
            if r["vorschlag_dateiname"]:
                print(f"  Vorschlag: {r['vorschlag_dateiname']}")
            if r["redigierter_ausschnitt"]:
                print(f"  Ausschnitt (geschwärzt): {r['redigierter_ausschnitt']}")
            for w in r["warnungen"]:
                print(f"  Hinweis: {w}")


if __name__ == "__main__":
    main()
