#!/usr/bin/env python3
"""Synthetische Tests für P1: Idempotenz-Manifest (manifest.py) und Dedup gegen
das Ziel-PARA-Home (dedupe_scan.py --against).

Alle Dateien/Inhalte sind temporär und erfunden. Keine externen Abhängigkeiten.

    python3 tests/test_manifest_and_dedupe.py
"""

import os
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import manifest  # noqa: E402
from dedupe_scan import (  # noqa: E402
    build_known_hashes,
    find_already_in_target,
    hash_all,
)


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.manifest = os.path.join(self.dir, ".para-manifest.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_fehlendes_manifest_ist_leer(self):
        self.assertEqual(manifest.load_manifest(self.manifest), {})

    def test_record_dann_load_roundtrip(self):
        ziel = os.path.join(self.dir, "2026-07-02_RG_Anbieter.pdf")
        _write(ziel, "Rechnungsinhalt")
        recorded, warnings = manifest.record_files(self.manifest, [ziel])
        self.assertEqual(len(recorded), 1)
        self.assertEqual(warnings, [])
        index = manifest.load_manifest(self.manifest)
        self.assertEqual(len(index), 1)
        (entry,) = index.values()
        self.assertEqual(entry["ziel"], os.path.abspath(ziel))
        self.assertEqual(entry["quelle"], "2026-07-02_RG_Anbieter.pdf")
        self.assertEqual(entry["aktion"], "verschoben")
        self.assertIn("zeitstempel", entry)

    def test_check_erkennt_bereits_verarbeitet_ueber_inhalt(self):
        # Ziel-Datei (eingetragen) und Quell-Datei haben identischen Inhalt ->
        # gleicher Hash -> als bereits verarbeitet erkannt, auch bei anderem Namen.
        ziel = os.path.join(self.dir, "sortiert.txt")
        _write(ziel, "gleicher inhalt")
        manifest.record_files(self.manifest, [ziel])

        quelle = os.path.join(self.dir, "Download-mit-anderem-Namen.txt")
        _write(quelle, "gleicher inhalt")
        neu = os.path.join(self.dir, "wirklich-neu.txt")
        _write(neu, "voellig anderer inhalt")

        res = {r["datei"]: r for r in manifest.check_files(self.manifest, [quelle, neu])}
        self.assertTrue(res[quelle]["bereits_verarbeitet"])
        self.assertEqual(res[quelle]["ziel"], os.path.abspath(ziel))
        self.assertFalse(res[neu]["bereits_verarbeitet"])

    def test_record_ist_idempotent(self):
        ziel = os.path.join(self.dir, "a.txt")
        _write(ziel, "x")
        manifest.record_files(self.manifest, [ziel])
        # Zweiter Lauf mit inhaltsgleicher Datei -> kein neuer Eintrag
        ziel2 = os.path.join(self.dir, "a-kopie.txt")
        _write(ziel2, "x")
        recorded, _ = manifest.record_files(self.manifest, [ziel2])
        self.assertEqual(recorded, [])
        self.assertEqual(len(manifest.load_manifest(self.manifest)), 1)

    def test_kaputte_zeile_wird_uebersprungen(self):
        with open(self.manifest, "w", encoding="utf-8") as f:
            f.write('{"hash": "abc", "ziel": "/x"}\n')
            f.write("das ist kein json\n")
            f.write("\n")
        index = manifest.load_manifest(self.manifest)
        self.assertEqual(set(index), {"abc"})
        self.assertEqual(manifest.load_manifest._skipped_lines, 1)


class DedupGegenZielHomeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "PARA-Home")
        self.src = os.path.join(self.tmp.name, "Downloads")
        os.makedirs(self.home)
        os.makedirs(self.src)

    def tearDown(self):
        self.tmp.cleanup()

    def test_quelldatei_schon_im_ziel_wird_gemeldet(self):
        im_ziel = os.path.join(self.home, "vorhanden.pdf")
        _write(im_ziel, "identischer inhalt")
        schon_da = os.path.join(self.src, "kopie-im-download.pdf")
        _write(schon_da, "identischer inhalt")
        einzigartig = os.path.join(self.src, "neu.pdf")
        _write(einzigartig, "einzigartiger inhalt")

        warnings = []
        known = build_known_hashes([self.home], True, warnings)
        src_hashes = hash_all([schon_da, einzigartig], warnings)
        treffer = find_already_in_target(src_hashes, known)

        self.assertEqual(len(treffer), 1)
        self.assertEqual(treffer[0]["quelldatei"], schon_da)
        self.assertEqual(treffer[0]["ziel_treffer"], [im_ziel])
        self.assertEqual(warnings, [])

    def test_leeres_ziel_home_keine_treffer(self):
        einzig = os.path.join(self.src, "x.txt")
        _write(einzig, "inhalt")
        warnings = []
        known = build_known_hashes([self.home], True, warnings)
        treffer = find_already_in_target(hash_all([einzig], warnings), known)
        self.assertEqual(treffer, [])

    def test_nicht_existierendes_ziel_home_warnt(self):
        warnings = []
        known = build_known_hashes(["/pfad/gibt/es/nicht"], True, warnings)
        self.assertEqual(known, {})
        self.assertTrue(any("kein Verzeichnis" in w for w in warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
