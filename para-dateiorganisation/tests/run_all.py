#!/usr/bin/env python3
"""Führt alle synthetischen Tests des Skills gebündelt aus.

    python3 tests/run_all.py          # alle test_*.py in diesem Ordner
    python3 tests/run_all.py -v       # ausführlich

Exit-Code 0 = alles grün, sonst 1. Keine externen Abhängigkeiten; die einzelnen
Testdateien nutzen ausschließlich synthetische, temporäre Daten.
"""

import os
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    verbosity = 2 if "-v" in sys.argv else 1
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=TESTS_DIR, pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
