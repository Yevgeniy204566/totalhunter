"""tesseract_setup.py — resolves the Tesseract binary path: portable tesseract_bin/
next to the EXE in a frozen build, system PATH/standard install dirs in dev mode.

Single source of truth — before this module existed, chest_reader.py and navigator.py
hardcoded the dev-machine path directly (C:\\Program Files\\Tesseract-OCR\\...), which
meant the portable tesseract_bin shipped to clients was never actually used by either
module's OCR calls.
"""
import os
import shutil
import sys


def find_tesseract():
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(os.path.dirname(sys.executable), "tesseract_bin", "tesseract.exe")
        return bundled if os.path.isfile(bundled) else None

    found = shutil.which("tesseract")
    if found:
        return found
    for path in [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'D:\Program Files\Tesseract-OCR\tesseract.exe',
        r'D:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]:
        if os.path.isfile(path):
            return path
    return None


def configure_pytesseract(pytesseract_module, log=print):
    path = find_tesseract()
    if path:
        pytesseract_module.pytesseract.tesseract_cmd = path
        return True
    if getattr(sys, 'frozen', False):
        log("КРИТИЧЕСКАЯ ОШИБКА: tesseract_bin не найден рядом с TotalHunter.exe. "
            "Проверьте целостность сборки — папка tesseract_bin должна быть рядом с EXE.")
    else:
        log("КРИТИЧЕСКАЯ ОШИБКА: Tesseract OCR не найден на ПК. "
            "Установите Tesseract для работы бота. "
            "Скачайте: https://github.com/UB-Mannheim/tesseract/wiki")
    return False
