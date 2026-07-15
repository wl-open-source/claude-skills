#!/usr/bin/env python3
"""Synthetische Tests für die konfigurierbaren Grenzen (P2 #11):
PDF-Seiten / DOCX-Absätze (extract_metadata) und OCR-Sprache (extract_image_metadata).

Keine externen Abhängigkeiten — getestet wird die Konfigurations-Logik selbst,
nicht die (optionalen) Parser-Bibliotheken.

    python3 tests/test_config.py
"""

import importlib
import os
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import extract_metadata  # noqa: E402


class IntEnvTest(unittest.TestCase):
    def test_gueltiger_wert_wird_gelesen(self):
        os.environ["PARA_TEST_INT"] = "7"
        try:
            self.assertEqual(extract_metadata._int_env("PARA_TEST_INT", 3), 7)
        finally:
            del os.environ["PARA_TEST_INT"]

    def test_muell_faellt_auf_default(self):
        os.environ["PARA_TEST_INT"] = "abc"
        try:
            self.assertEqual(extract_metadata._int_env("PARA_TEST_INT", 3), 3)
        finally:
            del os.environ["PARA_TEST_INT"]

    def test_kleiner_eins_faellt_auf_default(self):
        os.environ["PARA_TEST_INT"] = "0"
        try:
            self.assertEqual(extract_metadata._int_env("PARA_TEST_INT", 3), 3)
        finally:
            del os.environ["PARA_TEST_INT"]

    def test_fehlend_ist_default(self):
        os.environ.pop("PARA_TEST_INT", None)
        self.assertEqual(extract_metadata._int_env("PARA_TEST_INT", 5), 5)


class ConstantsTest(unittest.TestCase):
    def test_pdf_und_docx_grenzen_positiv(self):
        self.assertGreaterEqual(extract_metadata.PDF_MAX_PAGES, 1)
        self.assertGreaterEqual(extract_metadata.DOCX_MAX_PARAGRAPHS, 1)

    def test_pdf_grenze_aus_env(self):
        os.environ["PARA_PDF_MAX_PAGES"] = "9"
        try:
            reloaded = importlib.reload(extract_metadata)
            self.assertEqual(reloaded.PDF_MAX_PAGES, 9)
        finally:
            del os.environ["PARA_PDF_MAX_PAGES"]
            importlib.reload(extract_metadata)   # Standard wiederherstellen

    def test_extract_text_negatives_max_pages_wird_geklemmt(self):
        # max_pages < 1 darf nicht crashen; .txt ignoriert die Grenze ohnehin
        warnings = []
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write("Testinhalt")
            p = f.name
        try:
            txt = extract_metadata.extract_text(p, ".txt", warnings, max_pages=-5)
            self.assertEqual(txt, "Testinhalt")
        finally:
            os.unlink(p)


class OcrLangTest(unittest.TestCase):
    def test_default_ocr_lang(self):
        import extract_image_metadata
        self.assertEqual(extract_image_metadata.OCR_LANG, "deu+eng")

    def test_ocr_lang_env_override(self):
        os.environ["PARA_OCR_LANG"] = "eng"
        try:
            import extract_image_metadata
            reloaded = importlib.reload(extract_image_metadata)
            self.assertEqual(reloaded.OCR_LANG, "eng")
        finally:
            del os.environ["PARA_OCR_LANG"]
            import extract_image_metadata
            importlib.reload(extract_image_metadata)


if __name__ == "__main__":
    unittest.main(verbosity=2)
