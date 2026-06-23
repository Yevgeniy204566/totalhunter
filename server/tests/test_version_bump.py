import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

def test_version_is_185():
    from version import VERSION
    assert VERSION == "1.8.5", f"Expected 1.8.5, got {VERSION}"
