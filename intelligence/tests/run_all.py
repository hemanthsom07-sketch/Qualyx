"""
Combined test runner for the entire /intelligence test suite.

Runs every test_*.py module in this directory without requiring
pytest (useful in environments without network/package installs).
If pytest is available in the real dev environment, prefer:
    pytest intelligence/tests -v
"""

import sys
import os
import importlib
import glob

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def run_module(module_name: str):
    module = importlib.import_module(module_name)
    test_functions = [
        (name, obj)
        for name, obj in vars(module).items()
        if name.startswith("test_") and callable(obj)
    ]
    passed, failed = 0, 0
    for name, fn in test_functions:
        try:
            fn()
            print(f"  PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {name} -> {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {name} -> {e!r}")
            failed += 1
    return passed, failed


if __name__ == "__main__":
    test_dir = os.path.dirname(__file__)
    test_files = sorted(glob.glob(os.path.join(test_dir, "test_*.py")))

    total_passed, total_failed = 0, 0
    for path in test_files:
        module_name = "intelligence.tests." + os.path.splitext(os.path.basename(path))[0]
        print(f"=== {module_name} ===")
        p, f = run_module(module_name)
        total_passed += p
        total_failed += f
        print()

    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    sys.exit(1 if total_failed else 0)
