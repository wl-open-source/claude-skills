#!/usr/bin/env python3
"""Synthetische Tests für redundanz_check.py (Redundanz-Loop beim Ablegen).

Alle Pfade/Inhalte sind temporär und erfunden. Keine externen Abhängigkeiten;
mtimes werden explizit gesetzt, damit „neueste behalten" deterministisch prüfbar
ist statt von der Ausführungsreihenfolge abzuhängen.

    python3 tests/test_redundanz.py
"""

import os
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import redundanz_check as rc  # noqa: E402
import undo_last_run as undo  # noqa: E402

OLD = 1_000_000_000  # feste, weit auseinanderliegende mtimes -> „neueste" ist eindeutig
MID = 1_500_000_000
NEW = 2_000_000_000


def _write(path, content="x", mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


class RedundanzCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.quarantaene = os.path.join(self.dir, "_Papierkorb")
        self.log = os.path.join(self.dir, ".para-dateiorganisation-log-2026-07-07.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, apply_changes, max_passes=rc.DEFAULT_MAX_PASSES):
        return rc.run(self.dir, apply_changes, self.quarantaene, self.log, max_passes)

    # --- Trockenlauf -------------------------------------------------------

    def test_trockenlauf_bewegt_nichts(self):
        a = os.path.join(self.dir, "a.txt")
        b = os.path.join(self.dir, "b.txt")
        _write(a, "identischer inhalt", OLD)
        _write(b, "identischer inhalt", NEW)

        result = self._run(apply_changes=False)

        self.assertEqual(result["modus"], "trockenlauf")
        self.assertTrue(os.path.exists(a))
        self.assertTrue(os.path.exists(b))
        self.assertEqual(result["quarantaene_gesamt"], [])
        self.assertFalse(os.path.exists(self.log))       # kein Protokoll im Trockenlauf
        self.assertFalse(os.path.exists(self.quarantaene))
        self.assertEqual(result["durchlaeufe"][0]["aktion"], "wuerde-verschieben")

    # --- Apply: exakte Dubletten ------------------------------------------

    def test_apply_reduziert_auf_neueste_und_quarantaeniert_aeltere(self):
        a = os.path.join(self.dir, "a.txt")   # älter -> Verlierer
        b = os.path.join(self.dir, "b.txt")   # neuer -> behalten
        _write(a, "gleicher inhalt", OLD)
        _write(b, "gleicher inhalt", NEW)

        result = self._run(apply_changes=True)

        self.assertTrue(os.path.exists(b))               # neueste bleibt liegen
        self.assertFalse(os.path.exists(a))              # ältere ist weg vom Original
        self.assertTrue(os.path.exists(os.path.join(self.quarantaene, "a.txt")))
        self.assertEqual(len(result["quarantaene_gesamt"]), 1)
        self.assertEqual(result["quarantaene_gesamt"][0]["alt"], a)
        self.assertTrue(result["stabil_erreicht"])       # 2. Durchlauf findet nichts mehr

    def test_neueste_von_drei_bleibt(self):
        a = os.path.join(self.dir, "a.txt")
        b = os.path.join(self.dir, "b.txt")
        c = os.path.join(self.dir, "c.txt")
        _write(a, "drilling", OLD)
        _write(b, "drilling", MID)
        _write(c, "drilling", NEW)   # neueste

        result = self._run(apply_changes=True)

        self.assertTrue(os.path.exists(c))
        self.assertFalse(os.path.exists(a))
        self.assertFalse(os.path.exists(b))
        self.assertEqual(len(result["quarantaene_gesamt"]), 2)

    # --- Apply: Near-Duplicates werden NUR gemeldet ------------------------

    def test_near_duplicates_werden_nur_gemeldet_nie_bewegt(self):
        gemeinsam = "Protokoll der Vorstandssitzung vom Quartal. " * 20
        a = os.path.join(self.dir, "vertrag_v1.txt")
        b = os.path.join(self.dir, "vertrag_v2.txt")
        _write(a, gemeinsam + "Beschluss A wurde angenommen.", OLD)
        _write(b, gemeinsam + "Beschluss B wurde abgelehnt.", NEW)

        result = self._run(apply_changes=True)

        # Ähnlich (>85%), aber NICHT byte-identisch -> keine exakte Dublette,
        # also nichts bewegen, nur melden.
        self.assertTrue(os.path.exists(a))
        self.assertTrue(os.path.exists(b))
        self.assertEqual(result["quarantaene_gesamt"], [])
        near = result["near_duplicates_nur_gemeldet"]
        self.assertTrue(near, "Near-Duplicates sollten gemeldet werden")
        gemeldete = {p for g in near for p in g["files"]}
        self.assertIn(a, gemeldete)
        self.assertIn(b, gemeldete)

    # --- Reversibilität: Log ist undo-kompatibel ---------------------------

    def test_log_ist_undo_parsebar(self):
        a = os.path.join(self.dir, "a.txt")
        b = os.path.join(self.dir, "b.txt")
        _write(a, "gleich", OLD)
        _write(b, "gleich", NEW)

        self._run(apply_changes=True)

        zeilen, warnungen = undo.parse_log(self.log)
        self.assertEqual(warnungen, [])
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["aktion"], rc.ACTION)
        self.assertEqual(zeilen[0]["alt"], a)
        self.assertEqual(zeilen[0]["neu"], os.path.join(self.quarantaene, "a.txt"))

    def test_reversibel_via_undo(self):
        a = os.path.join(self.dir, "a.txt")
        b = os.path.join(self.dir, "b.txt")
        _write(a, "wiederherstellbar", OLD)
        _write(b, "wiederherstellbar", NEW)

        self._run(apply_changes=True)
        self.assertFalse(os.path.exists(a))              # erst mal weg

        ergebnis = undo.run(directory=self.dir, apply=True)

        self.assertEqual(len(ergebnis["erledigt"]), 1)
        self.assertTrue(os.path.exists(a))               # wieder da
        with open(a, encoding="utf-8") as f:
            self.assertEqual(f.read(), "wiederherstellbar")
        self.assertTrue(os.path.exists(b))               # b nie angefasst

    # --- Loop-/Fixpunkt-Verhalten -----------------------------------------

    def test_zweiter_lauf_findet_nichts_quarantaene_nicht_erneut_gescannt(self):
        a = os.path.join(self.dir, "a.txt")
        b = os.path.join(self.dir, "b.txt")
        _write(a, "gleich", OLD)
        _write(b, "gleich", NEW)
        self._run(apply_changes=True)                    # a wandert in Quarantäne

        # Zweiter unabhängiger Lauf: die Quarantäne liegt jetzt unter self.dir,
        # darf aber nicht erneut eingelesen werden — sonst würde a als Dublette
        # von b „wiedergefunden" und endlos hin- und hergeschoben.
        zweiter = self._run(apply_changes=True)

        self.assertEqual(zweiter["quarantaene_gesamt"], [])
        self.assertTrue(zweiter["stabil_erreicht"])

    def test_max_passes_cap_begrenzt_den_loop(self):
        a = os.path.join(self.dir, "a.txt")
        b = os.path.join(self.dir, "b.txt")
        _write(a, "gleich", OLD)
        _write(b, "gleich", NEW)

        # Cap = 1: nach dem einen bewegenden Durchlauf ist Schluss, ohne den
        # bestätigenden „stabil"-Durchlauf. Beweist, dass der Cap greift.
        gekappt = self._run(apply_changes=True, max_passes=1)
        self.assertEqual(len(gekappt["durchlaeufe"]), 1)
        self.assertFalse(gekappt["stabil_erreicht"])

    def test_leerer_ordner_ist_sofort_stabil(self):
        result = self._run(apply_changes=True)
        self.assertTrue(result["stabil_erreicht"])
        self.assertEqual(result["quarantaene_gesamt"], [])
        self.assertEqual(len(result["durchlaeufe"]), 1)
        self.assertEqual(result["durchlaeufe"][0]["aktion"], "keine (stabil)")


class LogUndQuarantaeneHelferTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_log_schreibt_header_nur_einmal(self):
        log = os.path.join(self.dir, "log.csv")
        rc.append_log(log, [(rc.ACTION, "/a/x", "/q/x")])
        rc.append_log(log, [(rc.ACTION, "/a/y", "/q/y")])   # zweiter Lauf, selbe Datei

        with open(log, encoding="utf-8") as f:
            zeilen = f.read().splitlines()
        header_zeilen = [z for z in zeilen if z == rc.CSV_HEADER.strip()]
        self.assertEqual(len(header_zeilen), 1)
        self.assertEqual(len(zeilen), 3)                     # 1 Header + 2 Datenzeilen

    def test_unique_target_haengt_zaehler_an_statt_zu_ueberschreiben(self):
        q = os.path.join(self.dir, "_Papierkorb")
        _write(os.path.join(q, "doc.pdf"), "erste")

        ziel1 = rc.unique_target(q, "doc.pdf")
        self.assertNotEqual(ziel1, os.path.join(q, "doc.pdf"))
        self.assertTrue(ziel1.endswith("doc_1.pdf"))

        _write(ziel1, "zweite")
        ziel2 = rc.unique_target(q, "doc.pdf")
        self.assertTrue(ziel2.endswith("doc_2.pdf"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
