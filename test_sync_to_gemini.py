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


class TestReplaceDoc(unittest.TestCase):

    def _make_service(self, end_index):
        service = MagicMock()
        service.documents.return_value.get.return_value.execute.return_value = {
            "body": {"content": [{"endIndex": end_index}]}
        }
        return service

    def test_normal_replace_sends_delete_then_insert(self):
        service = self._make_service(end_index=50)
        replace_doc(service, "doc123", "new content")

        call = service.documents.return_value.batchUpdate.call_args
        requests = call.kwargs["body"]["requests"]

        self.assertEqual(len(requests), 2)
        self.assertEqual(
            requests[0]["deleteContentRange"]["range"],
            {"startIndex": 1, "endIndex": 49},
        )
        self.assertEqual(
            requests[1]["insertText"],
            {"location": {"index": 1}, "text": "new content"},
        )

    def test_empty_doc_skips_delete(self):
        service = self._make_service(end_index=2)
        replace_doc(service, "doc123", "content")

        call = service.documents.return_value.batchUpdate.call_args
        requests = call.kwargs["body"]["requests"]

        self.assertEqual(len(requests), 1)
        self.assertIn("insertText", requests[0])

    def test_calls_execute_on_batch_update(self):
        service = self._make_service(end_index=10)
        replace_doc(service, "doc123", "hello")
        service.documents.return_value.batchUpdate.return_value.execute.assert_called_once()


class TestSync(unittest.TestCase):

    def _tmp_file(self, tmpdir, name, content=""):
        path = os.path.join(tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    @patch("sync_to_gemini.time.sleep")
    @patch("sync_to_gemini.replace_doc")
    def test_skips_empty_file(self, mock_replace, mock_sleep):
        service = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            empty = self._tmp_file(tmp, "empty.md", "")
            with patch("sync_to_gemini.FILES", [(empty, "doc1")]):
                sync(service)
        mock_replace.assert_not_called()

    @patch("sync_to_gemini.time.sleep")
    @patch("sync_to_gemini.replace_doc")
    def test_skips_missing_file(self, mock_replace, mock_sleep):
        service = MagicMock()
        with patch("sync_to_gemini.FILES", [(r"C:\nonexistent\fake.md", "doc1")]):
            sync(service)
        mock_replace.assert_not_called()

    @patch("sync_to_gemini.time.sleep")
    @patch("sync_to_gemini.replace_doc")
    def test_continues_after_api_error(self, mock_replace, mock_sleep):
        mock_replace.side_effect = [Exception("API down"), None]
        service = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            f1 = self._tmp_file(tmp, "a.md", "content A")
            f2 = self._tmp_file(tmp, "b.md", "content B")
            with patch("sync_to_gemini.FILES", [(f1, "doc1"), (f2, "doc2")]):
                sync(service)
        self.assertEqual(mock_replace.call_count, 2)

    @patch("sync_to_gemini.time.sleep")
    @patch("sync_to_gemini.replace_doc")
    def test_sleeps_between_files(self, mock_replace, mock_sleep):
        service = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            f1 = self._tmp_file(tmp, "a.md", "A")
            f2 = self._tmp_file(tmp, "b.md", "B")
            with patch("sync_to_gemini.FILES", [(f1, "doc1"), (f2, "doc2")]):
                sync(service)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(1)
