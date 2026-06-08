import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

def test_version_is_172():
    from version import VERSION
    assert VERSION == "1.7.2", f"Expected 1.7.2, got {VERSION}"
