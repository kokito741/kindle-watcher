def test_sanity():
    assert 1 + 1 == 2

def test_import_main():
    # importing should not start network operations
    import importlib
    importlib.import_module("main")