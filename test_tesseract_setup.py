import os
import sys
import tesseract_setup as ts


def test_find_tesseract_frozen_returns_bundled_path_when_present(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    exe_dir = tmp_path
    bin_dir = exe_dir / "tesseract_bin"
    bin_dir.mkdir()
    bundled = bin_dir / "tesseract.exe"
    bundled.write_text("fake exe")
    monkeypatch.setattr(sys, 'executable', str(exe_dir / "TotalHunter.exe"))

    result = ts.find_tesseract()
    assert result == str(bundled)


def test_find_tesseract_frozen_returns_none_when_bundled_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / "TotalHunter.exe"))

    assert ts.find_tesseract() is None


def test_find_tesseract_dev_uses_shutil_which_first(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.setattr(ts.shutil, 'which', lambda name: r'C:\PATH\tesseract.exe')

    assert ts.find_tesseract() == r'C:\PATH\tesseract.exe'


def test_find_tesseract_dev_falls_back_to_standard_paths(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.setattr(ts.shutil, 'which', lambda name: None)
    monkeypatch.setattr(ts.os.path, 'isfile',
                        lambda p: p == r'C:\Program Files\Tesseract-OCR\tesseract.exe')

    assert ts.find_tesseract() == r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def test_find_tesseract_dev_returns_none_when_nothing_found(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.setattr(ts.shutil, 'which', lambda name: None)
    monkeypatch.setattr(ts.os.path, 'isfile', lambda p: False)

    assert ts.find_tesseract() is None


def _make_fake_pytesseract_module():
    class _FakePytesseractModule:
        class pytesseract:
            tesseract_cmd = None
    return _FakePytesseractModule()


def test_configure_pytesseract_sets_cmd_when_found(monkeypatch):
    monkeypatch.setattr(ts, 'find_tesseract', lambda: r'C:\found\tesseract.exe')
    fake = _make_fake_pytesseract_module()

    result = ts.configure_pytesseract(fake)

    assert result is True
    assert fake.pytesseract.tesseract_cmd == r'C:\found\tesseract.exe'


def test_configure_pytesseract_logs_and_returns_false_when_not_found(monkeypatch):
    monkeypatch.setattr(ts, 'find_tesseract', lambda: None)
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    fake = _make_fake_pytesseract_module()
    logged = []

    result = ts.configure_pytesseract(fake, log=logged.append)

    assert result is False
    assert fake.pytesseract.tesseract_cmd is None
    assert len(logged) == 1
    assert "Tesseract OCR не найден" in logged[0]
