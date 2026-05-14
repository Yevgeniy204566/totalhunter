import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_version_is_125():
    from version import VERSION
    assert VERSION == "1.2.6", f"Expected 1.2.6, got {VERSION}"
