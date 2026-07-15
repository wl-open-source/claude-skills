#!/usr/bin/env python3
"""Synthetische Tests für triage.py (P1 #5) inkl. Integration mit undo_last_run.

Alle Pfade/Inhalte sind temporär und erfunden. Keine externen Abhängigkeiten
(Metadaten-Extraktion wird über kuerzel_map=None umgangen, ausser wo explizit getestet).

    python3 tests/test_triage.py
"""

import os
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import triage  # noqa: E402
import manifest  # noqa: E402
import undo_last_run as undo  # noqa: E402


def _write(path, content="inhalt"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class IsJunkTest(unittest.TestCase):
    def test_systemdateien_sind_muell(self):
        for name in (".DS_Store", "Thumbs.db", "desktop.ini"):
            junk, _ = triage.is_junk("/x/" + name)
            self.assertTrue(junk, name)

    def test_temp_und_abbruch_downloads_sind_muell(self):
        for name in ("a.tmp", "b.crdownload", "c.part", "d.download", "~$doc.docx"):
            junk, _ = triage.is_junk("/x/" + name)
            self.assertTrue(junk, name)

    def test_normale_datei_ist_kein_muell(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "rechnung.pdf")
            _write(p, "echter inhalt")
            junk, _ = triage.is_junk(p)
            self.assertFalse(junk)

    def test_null_byte_datei_ist_muell(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "leer.pdf")
            _write(p, "")
            junk, grund = triage.is_junk(p)
            self.assertTrue(junk)
            self.assertIn("0-Byte", grund)


class TriageRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tmp.name, "Downloads")
        self.quar = os.path.join(self.tmp.name, "PARA", "_Papierkorb")
        self.queue = os.path.join(self.tmp.name, "PARA", ".para-triage-queue.jsonl")
        self.log = os.path.join(self.src, ".para-dateiorganisation-log-2026-07-03.csv")
        os.makedirs(self.src)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, **kw):
        params = dict(sources=[self.src], quarantine_dir=self.quar, log_path=self.log,
                      queue_path=self.queue, kuerzel_map=None)
        params.update(kw)
        return triage.run(**params)

    def test_trockenlauf_bewegt_und_schreibt_nichts(self):
        _write(os.path.join(self.src, ".DS_Store"), "x")
        _write(os.path.join(self.src, "brief.pdf"), "inhalt")
        res = self._run(apply=False)
        self.assertEqual(len(res["quarantaene"]), 1)
        self.assertEqual(len(res["queue_neu"]), 1)
        # Nichts wurde tatsächlich bewegt oder geschrieben
        self.assertTrue(os.path.exists(os.path.join(self.src, ".DS_Store")))
        self.assertFalse(os.path.exists(self.quar))
        self.assertFalse(os.path.exists(self.queue))
        self.assertFalse(os.path.exists(self.log))

    def test_apply_quarantaeniert_muell_und_protokolliert(self):
        ds = os.path.join(self.src, ".DS_Store")
        _write(ds, "x")
        res = self._run(apply=True)
        self.assertEqual(len(res["quarantaene"]), 1)
        self.assertFalse(os.path.exists(ds))                       # weg aus Quelle
        self.assertTrue(os.path.exists(os.path.join(self.quar, ".DS_Store")))
        self.assertTrue(os.path.exists(self.log))                  # Protokoll geschrieben
        with open(self.log, encoding="utf-8") as f:
            inhalt = f.read()
        self.assertIn("zeitstempel;aktion;alt;neu", inhalt)
        self.assertIn("quarantäne", inhalt)

    def test_apply_schreibt_inhaltsdatei_in_queue_ohne_zu_verschieben(self):
        brief = os.path.join(self.src, "brief.pdf")
        _write(brief, "wichtiger inhalt")
        res = self._run(apply=True)
        self.assertEqual(len(res["queue_neu"]), 1)
        self.assertTrue(os.path.exists(brief))     # Inhaltsdatei NICHT verschoben
        self.assertTrue(os.path.exists(self.queue))
        q = triage.load_queue_hashes(self.queue)
        self.assertEqual(len(q), 1)

    def test_idempotent_queue_kein_doppelter_eintrag(self):
        _write(os.path.join(self.src, "brief.pdf"), "wichtiger inhalt")
        self._run(apply=True)
        # Zweiter Lauf: Datei liegt noch da, darf aber nicht erneut in die Queue
        res2 = self._run(apply=True)
        self.assertEqual(len(res2["queue_neu"]), 0)
        self.assertEqual(len(res2["uebersprungen"]), 1)
        self.assertIn("Queue", res2["uebersprungen"][0]["grund"])

    def test_idempotent_manifest_hash_wird_uebersprungen(self):
        brief = os.path.join(self.src, "brief.pdf")
        _write(brief, "schon einsortiert")
        man = os.path.join(self.tmp.name, "PARA", ".para-manifest.jsonl")
        # Datei ist inhaltsgleich schon im Manifest -> triage überspringt sie
        os.makedirs(os.path.dirname(man), exist_ok=True)
        manifest.record_files(man, [brief])
        res = self._run(apply=True, manifest_path=man)
        self.assertEqual(len(res["queue_neu"]), 0)
        self.assertEqual(len(res["uebersprungen"]), 1)
        self.assertIn("Manifest", res["uebersprungen"][0]["grund"])

    def test_dedup_gegen_home_markiert_dublette(self):
        home = os.path.join(self.tmp.name, "PARA", "1_Projekte")
        _write(os.path.join(home, "vorhanden.pdf"), "identischer inhalt")
        _write(os.path.join(self.src, "nochmal-geladen.pdf"), "identischer inhalt")
        res = self._run(apply=True, home_dirs=[home])
        self.assertEqual(len(res["queue_neu"]), 1)
        eintrag = res["queue_neu"][0]
        self.assertTrue(eintrag["bereits_im_ziel"])
        self.assertEqual(eintrag["klasse"], "dublette")
        self.assertTrue(eintrag["ziel_treffer"])

    def test_quarantaene_und_state_dateien_werden_ausgeschlossen(self):
        # Datei liegt bereits in der Quarantäne -> triage fasst sie nicht erneut an
        os.makedirs(self.quar)
        _write(os.path.join(self.quar, "alt.tmp"), "x")
        # Eigene State-Dateien -> ignorieren
        _write(os.path.join(self.src, ".para-ignore"), "")
        _write(os.path.join(self.src, ".para-triage-queue.jsonl"), "")
        res = self._run(apply=True)
        self.assertEqual(len(res["quarantaene"]), 0)
        self.assertEqual(len(res["queue_neu"]), 0)

    def test_metadaten_werden_gezogen_wenn_kuerzelmap_gesetzt(self):
        import extract_metadata
        _write(os.path.join(self.src, "brief.txt"), "Rechnung vom 03.07.2026, Betrag 100 EUR")
        res = self._run(apply=True, kuerzel_map=extract_metadata.load_kuerzel_map())
        self.assertEqual(len(res["queue_neu"]), 1)
        self.assertIn("confidence", res["queue_neu"][0])

    def test_undo_nimmt_triage_quarantaene_zurueck(self):
        ds = os.path.join(self.src, ".DS_Store")
        _write(ds, "x")
        self._run(apply=True)
        self.assertFalse(os.path.exists(ds))
        # undo gegen den Quellordner (dort liegt das Protokoll)
        u = undo.run(directory=self.src, apply=True)
        self.assertEqual(len(u["erledigt"]), 1)
        self.assertTrue(os.path.exists(ds))     # Müll zurück am Ursprung
        self.assertFalse(os.path.exists(os.path.join(self.quar, ".DS_Store")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
