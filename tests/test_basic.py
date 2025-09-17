import sys
import os
import pytest

def test_sanity():
    assert 1 + 1 == 2

def test_import_main():
    # Add project root to sys.path so import works
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    import importlib
    importlib.import_module("main")  # should not raise