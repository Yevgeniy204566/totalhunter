import pytest
import numpy as np
from unittest.mock import patch, MagicMock


# ── shared minimap stub ──────────────────────────────────────────────────
def _land_minimap():
    """180×180 BGR frame that looks like land (green-ish)."""
    mm = np.zeros((180, 180, 3), dtype=np.uint8)
    mm[:, :] = (30, 120, 30)   # BGR green ≈ land
    return mm


def _water_minimap():
    """180×180 BGR frame that looks like water (blue-ish)."""
    mm = np.zeros((180, 180, 3), dtype=np.uint8)
    mm[:, :] = (160, 80, 20)   # BGR blue ≈ water
    return mm


# ── Test 1 ───────────────────────────────────────────────────────────────
def test_old_navigator_class_unchanged():
    """CoastalSnakeNavigator from navigator.py must be importable and intact."""
    from navigator import CoastalSnakeNavigator
    nav = CoastalSnakeNavigator.__new__(CoastalSnakeNavigator)
    assert hasattr(CoastalSnakeNavigator, 'step')
    assert hasattr(CoastalSnakeNavigator, 'move')
    assert 'max_inland_steps' in CoastalSnakeNavigator.__init__.__code__.co_varnames


# ── Test 2 ───────────────────────────────────────────────────────────────
def test_beacon_navigator_importable():
    from navigator_beacon import CoastalSnakeNavigatorBeacon
    from navigator import CoastalSnakeNavigator
    assert issubclass(CoastalSnakeNavigatorBeacon, CoastalSnakeNavigator)
