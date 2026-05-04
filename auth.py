import requests
import uuid
import hashlib
import webbrowser

# Основной адрес сервера для API (Бот)
SERVER_URL = "http://34.68.86.57:8000"
# Домен для авторизации через Google (через nip.io для обхода ограничений IP)
AUTH_DOMAIN = "http://34.68.86.57.nip.io:8000"

def get_hwid():
    """Генерирует уникальный идентификатор железа (HWID)"""
    id = str(uuid.getnode())
    return hashlib.sha256(id.encode()).hexdigest()[:16].upper()

def login_with_google():
    """Открывает браузер для привязки Google-аккаунта"""
    hwid = get_hwid()
    auth_url = f"{AUTH_DOMAIN}/google_login?hwid={hwid}"
    webbrowser.open(auth_url)
    return {"success": True, "message": "Проверьте окно браузера"}

def check_license():
    """Запрашивает статус лицензии, баланс, почту и реферальные данные"""
    hwid = get_hwid()
    try:
        response = requests.post(f"{SERVER_URL}/check_auth", json={"hwid": hwid}, timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"authorized": False, "credits": 0, "message": "Ошибка сервера"}
    except Exception as e:
        log_error_to_server(f"Check License Error: {str(e)}")
        return {"authorized": False, "credits": 0, "message": "Нет связи с сервером"}

def generate_link_code():
    """Генерирует 6-значный код для привязки бота к аккаунту на сайте.
    Возвращает (code: str, expires_in_seconds: int) или (None, 0) при ошибке."""
    hwid = get_hwid()
    try:
        response = requests.post(f"{SERVER_URL}/web/link/generate",
                                 json={"hwid": hwid}, timeout=5)
        data = response.json()
        return data.get("code"), data.get("expires_in_seconds", 600)
    except Exception as e:
        log_error_to_server(f"Generate Link Code Error: {str(e)}")
        return None, 0

def transfer_referral_balance():
    """Переводит реферальный баланс (ref_credits) → основной (credits).
    Возвращает (success: bool, message: str, new_credits: int)."""
    hwid = get_hwid()
    try:
        response = requests.post(f"{SERVER_URL}/transfer_referral_balance",
                                 json={"hwid": hwid}, timeout=5)
        data = response.json()
        return data.get("success", False), data.get("message", ""), data.get("credits", 0)
    except Exception as e:
        log_error_to_server(f"Transfer Ref Error: {str(e)}")
        return False, "Ошибка связи с сервером", 0

def activate_referral(code):
    """Отправляет код пригласителя на сервер для получения бонуса"""
    hwid = get_hwid()
    try:
        response = requests.post(f"{SERVER_URL}/activate_referral", 
                                 json={"hwid": hwid, "ref_code": code}, timeout=5)
        return response.json()
    except Exception as e:
        log_error_to_server(f"Activate Ref Error: {str(e)}")
        return {"success": False, "message": "Ошибка связи с сервером"}

def get_free_trial():
    """Запрос 300 стартовых попыток (Trial)"""
    hwid = get_hwid()
    try:
        response = requests.post(f"{SERVER_URL}/claim_trial", json={"hwid": hwid}, timeout=5)
        return response.json()
    except Exception as e:
        log_error_to_server(f"Trial Claim Error: {str(e)}")
        return {"success": False, "message": "Ошибка сервера"}

def spend_credit(hunt_type: str = "crypt"):
    """
    Списывает кредиты при нахождении цели.
    hunt_type: 'exchange' (10 кр.) или 'crypt' (1 кр.)
    Возвращает {"success": False, "low_credits": True} при 402 — бот показывает окно пополнения.
    """
    hwid = get_hwid()
    try:
        response = requests.post(
            f"{SERVER_URL}/use_credit",
            json={"hwid": hwid, "hunt_type": hunt_type},
            timeout=5,
        )
        if response.status_code == 402:
            return {"success": False, "low_credits": True, "message": response.json().get("detail", {}).get("message", "")}
        return response.json()
    except:
        return {"success": False}


def heartbeat():
    """
    Онлайн-пинг — вызывается каждые 2 минуты пока бот запущен.
    Обновляет last_seen на сервере → онлайн-счётчик в админке.
    """
    hwid = get_hwid()
    try:
        requests.post(f"{SERVER_URL}/heartbeat", json={"hwid": hwid}, timeout=3)
    except:
        pass  # heartbeat не критичен — падение не останавливает бота

def log_error_to_server(error_msg):
    """Отправляет отчет о сбое программы в твою админ-панель"""
    hwid = get_hwid()
    try:
        # Не ставим большой таймаут, чтобы не вешать программу
        requests.post(f"{SERVER_URL}/log_error", 
                      json={"hwid": hwid, "error": error_msg}, timeout=2)
    except:
        pass