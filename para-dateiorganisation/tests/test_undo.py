#!/usr/bin/env python3
"""Synthetische Tests für undo_last_run.py (P1 #7).

Alle Pfade/Inhalte sind temporär und erfunden. Keine externen Abhängigkeiten.

    python3 tests/test_undo.py
"""

import os
import sys
import tempfile
import time
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import undo_last_run as undo  # noqa: E402


def _write(path, content="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class UndoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.log = os.path.join(self.dir, ".para-dateiorganisation-log-2026-07-02.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def _log(self, zeilen, header=True):
        with open(self.log, "w", encoding="utf-8") as f:
            if header:
                f.write("zeitstempel;aktion;alt;neu\n")
            for z in zeilen:
                f.write(";".join(z) + "\n")

    def test_parse_ueberspringt_header_und_kaputte_zeilen(self):
        self._log([
            ["2026-07-02T20:30:35", "verschoben", "/a/x.pdf", "/b/x.pdf"],
            ["kaputt", "nur", "drei"],
            ["2026-07-02T20:30:36", "umbenannt", "/a/y.pdf", "/a/z.pdf"],
        ])
        zeilen, warnungen = undo.parse_log(self.log)
        self.assertEqual(len(zeilen), 2)
        self.assertEqual(zeilen[0]["neu"], "/b/x.pdf")
        self.assertEqual(len(warnungen), 1)

    def test_apply_bewegt_neu_zurueck_nach_alt(self):
        alt = os.path.join(self.dir, "Downloads", "scan.pdf")
        neu = os.path.join(self.dir, "PARA", "2026-07-02_VS_Vertrag.pdf")
        _write(neu, "inhalt")
        # alt existiert nicht mehr (wurde beim Aufräumen wegbewegt)
        self._log([["2026-07-02T20:30:35", "verschoben", alt, neu]])

        ergebnis = undo.run(directory=self.dir, apply=True)
        self.assertEqual(len(ergebnis["erledigt"]), 1)
        self.assertTrue(os.path.exists(alt))
        self.assertFalse(os.path.exists(neu))
        with open(alt, encoding="utf-8") as f:
            self.assertEqual(f.read(), "inhalt")

    def test_trockenlauf_bewegt_nichts(self):
        alt = os.path.join(self.dir, "a", "x.pdf")
        neu = os.path.join(self.dir, "b", "x.pdf")
        _write(neu, "inhalt")
        self._log([["2026-07-02T20:30:35", "verschoben", alt, neu]])

        ergebnis = undo.run(directory=self.dir, apply=False)
        self.assertEqual(ergebnis["erledigt"], [])
        self.assertEqual(len(ergebnis["plan"]), 1)
        self.assertEqual(ergebnis["plan"][0]["status"], "bereit")
        self.assertTrue(os.path.exists(neu))    # unverändert
        self.assertFalse(os.path.exists(alt))

    def test_belegtes_ziel_wird_nicht_ueberschrieben(self):
        alt = os.path.join(self.dir, "a", "x.pdf")
        neu = os.path.join(self.dir, "b", "x.pdf")
        _write(neu, "neu-inhalt")
        _write(alt, "ALT-DARF-BLEIBEN")     # alt existiert schon wieder
        self._log([["2026-07-02T20:30:35", "verschoben", alt, neu]])

        ergebnis = undo.run(directory=self.dir, apply=True)
        self.assertEqual(ergebnis["erledigt"], [])
        self.assertEqual(ergebnis["plan"][0]["status"], "ziel_belegt")
        with open(alt, encoding="utf-8") as f:
            self.assertEqual(f.read(), "ALT-DARF-BLEIBEN")   # nicht überschrieben
        self.assertTrue(os.path.exists(neu))                 # bleibt liegen

    def test_fehlende_quelle_wird_gemeldet_nicht_gecrasht(self):
        alt = os.path.join(self.dir, "a", "x.pdf")
        neu = os.path.join(self.dir, "b", "fehlt.pdf")   # existiert nie
        self._log([["2026-07-02T20:30:35", "verschoben", alt, neu]])

        ergebnis = undo.run(directory=self.dir, apply=True)
        self.assertEqual(ergebnis["erledigt"], [])
        self.assertEqual(ergebnis["plan"][0]["status"], "quelle_fehlt")

    def test_rueckwaerts_reihenfolge_bei_verketteten_moves(self):
        # Lauf: erst a->b (umbenannt), dann b->c (verschoben). Undo muss zuerst
        # c->b und dann b->a machen, sonst kollidiert es.
        a = os.path.join(self.dir, "a.pdf")
        b = os.path.join(self.dir, "b.pdf")
        c = os.path.join(self.dir, "unter", "c.pdf")
        _write(c, "inhalt")   # Endzustand nach dem Lauf: nur c existiert
        self._log([
            ["2026-07-02T20:30:35", "umbenannt", a, b],
            ["2026-07-02T20:30:36", "verschoben", b, c],
        ])
        ergebnis = undo.run(directory=self.dir, apply=True)
        self.assertEqual(len(ergebnis["erledigt"]), 2)
        self.assertTrue(os.path.exists(a))
        self.assertFalse(os.path.exists(b))
        self.assertFalse(os.path.exists(c))

    def test_tag_begrenzt_auf_letzte_n_aktionen(self):
        a_alt = os.path.join(self.dir, "erst", "a.pdf")
        a_neu = os.path.join(self.dir, "ziel", "a.pdf")
        b_alt = os.path.join(self.dir, "erst", "b.pdf")
        b_neu = os.path.join(self.dir, "ziel", "b.pdf")
        _write(a_neu, "a")
        _write(b_neu, "b")
        self._log([
            ["2026-07-02T20:30:35", "verschoben", a_alt, a_neu],
            ["2026-07-02T20:30:36", "verschoben", b_alt, b_neu],
        ])
        # Nur die letzte Aktion (b) zurücknehmen.
        ergebnis = undo.run(directory=self.dir, tail=1, apply=True)
        self.assertEqual(len(ergebnis["erledigt"]), 1)
        self.assertTrue(os.path.exists(b_alt))   # b zurück
        self.assertFalse(os.path.exists(a_alt))  # a unberührt
        self.assertTrue(os.path.exists(a_neu))

    def test_neueste_logdatei_wird_gewaehlt(self):
        alt = os.path.join(self.dir, "a", "x.pdf")
        neu = os.path.join(self.dir, "b", "x.pdf")
        _write(neu, "inhalt")
        # Ältere Log-Datei mit irreführendem Inhalt
        alt_log = os.path.join(self.dir, ".para-dateiorganisation-log-2026-01-01.csv")
        with open(alt_log, "w", encoding="utf-8") as f:
            f.write("zeitstempel;aktion;alt;neu\n")
            f.write("2026-01-01T00:00:00;verschoben;/gibt/es/nicht;/auch/nicht\n")
        time.sleep(0.01)
        self._log([["2026-07-02T20:30:35", "verschoben", alt, neu]])
        os.utime(self.log, None)   # sicherstellen, dass self.log neuer ist

        ergebnis = undo.run(directory=self.dir, apply=False)
        self.assertEqual(ergebnis["log"], self.log)
        self.assertEqual(len(ergebnis["plan"]), 1)

    def test_kein_protokoll_meldet_sauber(self):
        ergebnis = undo.run(directory=self.dir, apply=True)
        self.assertIsNone(ergebnis["log"])
        self.assertIn("Keine Protokolldatei", ergebnis["warnung"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
