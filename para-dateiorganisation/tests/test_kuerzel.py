#!/usr/bin/env python3
"""Synthetische Tests für die verbesserte Kürzel-Erkennung (P2 #8).

Deckt Wortgrenzen, Häufigkeit-schlägt-Reihenfolge, Spezifitäts-Tie-Break und
Mehrdeutigkeits-Meldung ab. Keine externen Abhängigkeiten.

    python3 tests/test_kuerzel.py
"""

import os
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from extract_metadata import (  # noqa: E402
    _kuerzel_variants,
    analyze,
    find_kuerzel,
    load_kuerzel_map,
)

# Kleine, deterministische Test-Map (unabhängig von der echten Kürzel-Liste).
MAP = {"RG": "Rechnung", "VTR": "Vertrag", "BESCH": "Bescheid (Behörde/Amt)"}


class VariantsTest(unittest.TestCase):
    def test_klammern_werden_entfernt(self):
        self.assertEqual(_kuerzel_variants("Bescheid (Behörde/Amt)"), ["bescheid"])

    def test_slash_trennt_mehrere(self):
        self.assertEqual(_kuerzel_variants("Zeugnis/Zertifikat"), ["zeugnis", "zertifikat"])

    def test_zu_kurze_fragmente_fallen_weg(self):
        # "ab" ist unter 3 Zeichen -> ignoriert
        self.assertEqual(_kuerzel_variants("ab/Rechnung"), ["rechnung"])


class FindKuerzelTest(unittest.TestCase):
    def test_wortgrenze_kein_teiltreffer(self):
        # "vertraglich" darf NICHT als Vertrag (VTR) zählen
        kuerzel, quelle, alt = find_kuerzel("Das ist rein vertraglich geregelt.", MAP)
        self.assertIsNone(kuerzel)
        self.assertEqual(alt, [])

    def test_echtes_wort_trifft(self):
        kuerzel, quelle, alt = find_kuerzel("Hier ist ein Vertrag.", MAP)
        self.assertEqual(kuerzel, "VTR")
        self.assertEqual(quelle, "vertrag")

    def test_haeufigkeit_schlaegt_reihenfolge(self):
        # RG steht in der Map vor VTR — aber Vertrag kommt öfter vor -> VTR gewinnt
        text = "Vertrag ... dieser Vertrag ... noch ein Vertrag. Eine Rechnung."
        kuerzel, quelle, alt = find_kuerzel(text, MAP)
        self.assertEqual(kuerzel, "VTR")
        self.assertEqual(alt[0]["kuerzel"], "RG")
        self.assertEqual(alt[0]["treffer"], 1)

    def test_mehrdeutigkeit_wird_gemeldet(self):
        text = "Rechnung und Vertrag im selben Dokument."
        kuerzel, quelle, alt = find_kuerzel(text, MAP)
        self.assertEqual(len(alt), 1)                     # der jeweils andere Typ
        self.assertIn(alt[0]["kuerzel"], {"RG", "VTR"})

    def test_spezifitaet_bricht_gleichstand(self):
        # Gleiche Trefferzahl -> längere (spezifischere) Variante gewinnt
        m = {"KURZ": "abc", "LANG": "abcdef"}
        kuerzel, quelle, alt = find_kuerzel("abc und abcdef", m)
        self.assertEqual(kuerzel, "LANG")
        self.assertEqual(quelle, "abcdef")

    def test_parenthese_variante_matcht_kernwort(self):
        kuerzel, quelle, alt = find_kuerzel("Der Bescheid vom Amt.", MAP)
        self.assertEqual(kuerzel, "BESCH")
        self.assertEqual(quelle, "bescheid")

    def test_kein_treffer(self):
        self.assertEqual(find_kuerzel("Nichts Passendes hier.", MAP), (None, None, []))


class AnalyzeAmbiguityTest(unittest.TestCase):
    def test_analyze_warnt_bei_mehrdeutigkeit(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "doc.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write("Rechnung vom 03.07.2026 - siehe auch den Vertrag dazu.")
            res = analyze(p, load_kuerzel_map())
            self.assertEqual(res["confidence"], "high")
            self.assertIsNotNone(res["kuerzel_alternativen"])
            self.assertTrue(any("Mehrdeutig" in w for w in res["warnungen"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
