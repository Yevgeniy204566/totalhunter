import re
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

def test_version_is_well_formed():
    """Just checks version.py holds a valid X.Y.Z string — not a specific
    release number, which would need editing by hand every single release
    (that drift is exactly why this test went stale for 4 releases straight)."""
    from version import VERSION
    assert re.fullmatch(r"\d+\.\d+\.\d+", VERSION), f"Not a valid X.Y.Z version: {VERSION}"
