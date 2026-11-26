"""
STARAPP AUTOMATED TEST RUNNER
Runs all unit and end-to-end workflow suites.

SAFETY: several suites call `reset_to_seed()` / `clear_all_tables()` which WIPE the database they
are pointed at. To protect the authoritative `data/starapp.db`, this runner copies it to a throw-away
temp directory and points the whole test process at that copy (STARAPP_DB_PATH + DATABASE_URL) BEFORE
any StarApp module is imported. The real database file is never opened for writing by the tests.

Set STARAPP_TEST_USE_REAL_DB=1 only if you deliberately want the old (destructive) behaviour.
"""

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add project root to sys.path
sys.path.insert(0, ROOT)


def _isolate_database():
    """Points the test process at a disposable copy of data/starapp.db. Returns the temp dir (or None)."""
    if os.environ.get("STARAPP_TEST_USE_REAL_DB") == "1":
        return None
    real_db = os.path.join(ROOT, "data", "starapp.db")
    tmp_dir = tempfile.mkdtemp(prefix="starapp_tests_")
    test_db = os.path.join(tmp_dir, "starapp.db")
    if os.path.exists(real_db):
        shutil.copyfile(real_db, test_db)
    os.environ["STARAPP_DB_PATH"] = test_db
    os.environ["DATABASE_URL"] = test_db  # absolute path -> backend/app/core/config.py keeps it as-is
    return tmp_dir


if __name__ == "__main__":
    _tmp = _isolate_database()
    try:
        loader = unittest.TestLoader()
        suite = loader.discover("tests", pattern="test_*.py")
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
    finally:
        if _tmp:
            shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(0 if result.wasSuccessful() else 1)
