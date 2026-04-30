# test_combiner.py
import pytest
from combiner import parse_number

def test_parse_4_1k():
    assert parse_number("4.1k") == 4100

def test_parse_4_1k_comma():
    assert parse_number("4,1k") == 4100

def test_parse_1_2M():
    assert parse_number("1.2M") == 1_200_000

def test_parse_500():
    assert parse_number("500") == 500

def test_parse_1_0k():
    assert parse_number("1.0k") == 1000

def test_parse_4_1k_div4():
    assert parse_number("4.1k") // 4 == 1025

def test_parse_invalid_returns_0():
    assert parse_number("abc") == 0

def test_parse_empty_returns_0():
    assert parse_number("") == 0

def test_parse_less_than_4_gives_small_int():
    assert parse_number("3") == 3  # caller decides to skip

import numpy as np
from combiner import _images_differ

def test_images_differ_same():
    a = np.zeros((50, 50, 3), dtype=np.uint8)
    b = np.zeros((50, 50, 3), dtype=np.uint8)
    assert _images_differ(a, b) is False

def test_images_differ_changed():
    a = np.zeros((50, 50, 3), dtype=np.uint8)
    b = np.ones((50, 50, 3), dtype=np.uint8) * 200
    assert _images_differ(a, b) is True

def test_images_differ_shape_mismatch():
    a = np.zeros((50, 50, 3), dtype=np.uint8)
    b = np.zeros((60, 50, 3), dtype=np.uint8)
    assert _images_differ(a, b) is True
