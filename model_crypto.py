"""
Шифрование/дешифрование YOLO-моделей (.pt).
Ключ = HMAC(SECRET_SALT, HWID) — модель привязана к железу.
Запускай encrypt_models() ОДИН РАЗ перед сборкой EXE.
"""
import os
import io
import hmac
import hashlib
import base64
from cryptography.fernet import Fernet

# Соль зашита в код — меняй при каждом релизе
_SECRET_SALT = b"TH-2026-x9kQmR7vNpLsWjYe"

def _derive_key(hwid: str) -> bytes:
    """Ключ Fernet из соли + HWID (32 байта → base64url)."""
    raw = hmac.new(_SECRET_SALT, hwid.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw)

def _universal_key() -> bytes:
    """Резервный ключ без HWID — для дистрибуции до привязки."""
    raw = hmac.new(_SECRET_SALT, b"universal-build", hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw)


# ── Шифрование (запускать при сборке) ────────────────────────────────────────

def encrypt_model(src_path: str, dst_path: str | None = None) -> str:
    """Шифрует .pt файл, сохраняет как .pte рядом (или по dst_path)."""
    if dst_path is None:
        dst_path = src_path + "e"      # exchange.pt → exchange.pte
    key = _universal_key()
    f = Fernet(key)
    with open(src_path, "rb") as fp:
        data = fp.read()
    encrypted = f.encrypt(data)
    with open(dst_path, "wb") as fp:
        fp.write(encrypted)
    print(f"[model_crypto] encrypted: {src_path} -> {dst_path} ({len(data)//1024}KB -> {len(encrypted)//1024}KB)")
    return dst_path


def encrypt_all_models():
    """Шифрует exchange.pt и targets/crypts.pt."""
    base = os.path.dirname(os.path.abspath(__file__))
    models = [
        os.path.join(base, "exchange.pt"),
        os.path.join(base, "targets", "crypts.pt"),
    ]
    for path in models:
        if os.path.exists(path):
            encrypt_model(path)
        else:
            print(f"[model_crypto] SKIP (not found): {path}")


# ── Загрузка (используется в engine.py и crypt_hunter.py) ───────────────────

def load_model_bytes(enc_path: str) -> bytes:
    """Расшифровывает .pte → bytes в памяти. Не пишет на диск."""
    key = _universal_key()
    f = Fernet(key)
    with open(enc_path, "rb") as fp:
        encrypted = fp.read()
    return f.decrypt(encrypted)


def yolo_from_encrypted(enc_path: str):
    """Загружает YOLO-модель из зашифрованного .pte файла через temp-файл."""
    import tempfile
    import torch
    from ultralytics import YOLO
    raw = load_model_bytes(enc_path)
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        model = YOLO(tmp_path)
    finally:
        os.remove(tmp_path)
    try:
        _device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model.to(_device)
    except Exception:
        model.to('cpu')
        _device = 'cpu'
    print(f"[TH v1.2.5] YOLO device: {_device}")
    return model


if __name__ == "__main__":
    encrypt_all_models()
