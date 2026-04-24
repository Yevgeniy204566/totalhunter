import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from sync_to_gemini import read_local, replace_doc, sync


class TestReadLocal(unittest.TestCase):

    def test_missing_file_returns_none(self):
        result = read_local(r"C:\nonexistent\totally_fake_file.md")
        self.assertIsNone(result)

    def test_empty_file_returns_none(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as f:
            path = f.name
        try:
            result = read_local(path)
            self.assertIsNone(result)
        finally:
            os.unlink(path)

    def test_valid_file_returns_content(self):
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".md", mode="w", encoding="utf-8"
        ) as f:
            f.write("# Hello\nworld")
            path = f.name
        try:
            result = read_local(path)
            self.assertEqual(result, "# Hello\nworld")
        finally:
            os.unlink(path)
