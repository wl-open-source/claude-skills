#!/usr/bin/env python3
"""Synthetische Tests für die Schwärzung in extract_metadata.py.

ALLE Werte hier sind frei erfunden (Testnummern, Beispiel-Domains). Es sind
KEINE echten personenbezogenen Daten. Standard-Testkartennummern (z.B.
4242 4242 4242 4242) sind absichtlich Luhn-gültig, aber keine echten Karten.

Ausführen (keine externen Abhängigkeiten nötig):
    python3 tests/test_redact.py
"""

import os
import sys
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from extract_metadata import (  # noqa: E402
    redact,
    find_date,
    is_garbled,
    _luhn_ok,
    analyze,
)


class RedactInternationalTest(unittest.TestCase):
    """P0.2 — die neuen, international gehärteten Muster."""

    def test_email_wird_geschwaerzt(self):
        out = redact("Kontakt: max.muster+rechnung@example.co.uk bitte antworten")
        self.assertIn("[EMAIL]", out)
        self.assertNotIn("example.co.uk", out)

    def test_deutsche_iban_wird_geschwaerzt(self):
        out = redact("Bankverbindung DE89 3704 0044 0532 0130 00 danke")
        self.assertIn("[IBAN]", out)
        self.assertNotIn("3704", out)

    def test_internationale_iban_wird_geschwaerzt(self):
        # Synthetische, gültig geformte Nicht-DE-IBANs
        for iban in ["GB29 NWBK 6016 1331 9268 19", "FR14 2004 1010 0505 0001 3M02 606"]:
            out = redact(f"IBAN: {iban}")
            self.assertIn("[IBAN]", out, f"IBAN nicht geschwärzt: {iban}")

    def test_luhn_gueltige_kreditkarte_wird_geschwaerzt(self):
        # 4242... ist eine bekannte Luhn-gültige Testnummer (keine echte Karte)
        for card in ["4242 4242 4242 4242", "4242-4242-4242-4242", "4242424242424242"]:
            out = redact(f"Karte {card} Ablauf 12/28")
            self.assertIn("[KREDITKARTE]", out, f"Karte nicht geschwärzt: {card}")
            self.assertNotIn("4242", out)

    def test_luhn_ungueltige_gruppe_ist_keine_kreditkarte(self):
        # Luhn-negativ -> kein [KREDITKARTE]-Label. Unformatiert greift aber der
        # generische Fang-Rest, es entweicht also keine lange Ziffernfolge.
        gruppiert = redact("Referenz 1234 5678 9012 3456 Ende")
        self.assertNotIn("[KREDITKARTE]", gruppiert)
        unformatiert = redact("Referenz 1234567890123456 Ende")
        self.assertIn("[NUMMER]", unformatiert)
        self.assertNotIn("1234567890123456", unformatiert)

    def test_lange_ziffernfolge_ohne_label_wird_geschwaerzt(self):
        out = redact("Ihr Vorgang 123456789012 wurde bearbeitet")
        self.assertIn("[NUMMER]", out)
        self.assertNotIn("123456789012", out)

    def test_luhn_helper(self):
        self.assertTrue(_luhn_ok("4242424242424242"))
        self.assertFalse(_luhn_ok("1234567890123456"))


class DatumUeberlebtSchwaerzungTest(unittest.TestCase):
    """Regression: find_date arbeitet auf dem geschwärzten Text — Datumsangaben
    dürfen von den Zahlen-Mustern NICHT zerstört werden."""

    def test_iso_datum_bleibt(self):
        out = redact("Ausgestellt am 2026-07-02 gegenueber jemandem")
        self.assertIn("2026-07-02", out)
        self.assertEqual(find_date(out), "2026-07-02")

    def test_dmy_datum_bleibt_trotz_sensibler_daten(self):
        text = "Rechnung vom 02.07.2026, IBAN DE89 3704 0044 0532 0130 00, Betrag 1.234,56 EUR"
        out = redact(text)
        self.assertEqual(find_date(out), "2026-07-02")
        self.assertIn("[IBAN]", out)
        self.assertIn("[BETRAG]", out)


class GarbledLeakSchutzTest(unittest.TestCase):
    """Der bekannte Leak-Fall: zerstückelter Behörden-PDF-Text. is_garbled muss
    greifen, und analyze darf dann KEINEN Ausschnitt ausgeben."""

    def test_zerstueckelter_text_gilt_als_garbled(self):
        # Realitätsnah: unregelmäßige 2-Zeichen-Gruppen, die collapse_letter_spacing
        # (das nur reine Einzelzeichen-Folgen zusammenzieht) NICHT reparieren kann.
        garbled = " ".join(["Jo", "bc", "en", "te", "rr", "He", "rr", "Mu", "st", "er"] * 3)
        self.assertTrue(is_garbled(garbled))

    def test_analyze_gibt_bei_garbled_keinen_ausschnitt(self):
        # Über eine echte Textdatei laufen lassen, damit der volle Pfad greift
        # (inkl. collapse_letter_spacing VOR is_garbled).
        import tempfile

        garbled = " ".join(["He", "rr", "Mu", "st", "er", "ma", "nn", "Jo", "bc", "en"] * 4)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(garbled)
            path = f.name
        try:
            result = analyze(path, kuerzel_map={})
            self.assertIsNone(result["redigierter_ausschnitt"])
            self.assertTrue(any("zerstückelt" in w for w in result["warnungen"]))
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
