

import ctypes as _ctypes
try:
    _ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI — фикс размытости на HiDPI
except Exception:
    pass

# ── PyInstaller: preload torch DLLs before any import ────────────────────────
import sys, os
import datetime as _dt
if getattr(sys, 'frozen', False):
    import ctypes, glob as _glob
    _torch_lib = os.path.join(sys._MEIPASS, 'torch', 'lib')
    if os.path.isdir(_torch_lib):
        _k32 = ctypes.WinDLL('kernel32.dll')
        _k32.LoadLibraryW.restype = ctypes.c_void_p
        os.add_dll_directory(_torch_lib)
        for _dll in ['libiomp5md.dll', 'c10.dll', 'torch_global_deps.dll',
                     'torch_cpu.dll', 'torch.dll', 'torch_python.dll']:
            _p = os.path.join(_torch_lib, _dll)
            if os.path.exists(_p):
                _k32.LoadLibraryW(_p)
        del _k32, _glob, _dll, _p, _torch_lib
# ─────────────────────────────────────────────────────────────────────────────

import json
import threading
import customtkinter as ctk
from auth import (get_hwid, check_license, get_free_trial, spend_credit,
                  login_with_google, log_error_to_server, activate_referral,
                  transfer_referral_balance, generate_link_code, get_balance_update,
                  seconds_since_last_contact, HEARTBEAT_TIMEOUT)
from engine import HuntEngine
from crypt_hunter import CryptHunter
# from combiner import CombinerEngine  # Combo заморожен — импорт отключён
from coord_manager import coord_manager, REF_A, REF_B
import chest_reader
import tkinter.messagebox as messagebox
import keyboard
import webbrowser
from version import VERSION

if getattr(sys, 'frozen', False):
    _config_dir = os.path.dirname(sys.executable)
    _bundled_config = os.path.join(sys._MEIPASS, 'gui_config.json')
else:
    _config_dir = os.path.dirname(os.path.abspath(__file__))
    _bundled_config = None
GUI_CONFIG_PATH = os.path.join(_config_dir, 'gui_config.json')
# Первый запуск: копируем дефолт из bundle, если конфига ещё нет
if not os.path.exists(GUI_CONFIG_PATH) and _bundled_config and os.path.exists(_bundled_config):
    import shutil as _shutil
    _shutil.copy2(_bundled_config, GUI_CONFIG_PATH)


# Настройки внешнего вида
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── MD3 Color Themes ─────────────────────────────────────────────────────────
THEMES = {
    "Dark Mode": {
        # Black bg + Ocean-style accents 10% darker
        "bg": "#000000", "card": "#080E14", "elevated": "#0D1520",
        "primary": "#0C85BC", "primary_dim": "#0D94D0",
        "secondary": "#3A9AC8", "error": "#8B1A1A", "error_hover": "#6E1414",
        "error_text": "#E08080", "on_surface": "#F0F8FF", "on_surface2": "#A8C8E0",
        "outline": "#152030", "separator": "#0A1018",
        "green_btn": "#1A4A30", "green_hover": "#123520",
        "blue_btn": "#025E8E", "blue_hover": "#036A9E",
        "tab_selected": "#025E8E", "tab_selected_hover": "#036A9E",
        "value_text": "#0D94D0", "checkbox": "#0C85BC", "checkbox_hover": "#0D94D0",
    },
    "Deep Night": {
        # Sapphire magic — иссиня-чёрный + deep sapphire gem
        "bg": "#050810", "card": "#0A0F1E", "elevated": "#0F1528",
        "primary": "#1B3A82", "primary_dim": "#2A4A9E",
        "secondary": "#2040A0", "error": "#7A2020", "error_hover": "#5E1818",
        "error_text": "#C08080", "on_surface": "#FFFFFF", "on_surface2": "#CCDDFF",
        "outline": "#1A2440", "separator": "#0A1020",
        "green_btn": "#0F3A2A", "green_hover": "#0A2A1E",
        "blue_btn": "#1B3A82", "blue_hover": "#2A4A9E",
        "tab_selected": "#1B3A82", "tab_selected_hover": "#2A4A9E",
        "value_text": "#88AAFF", "checkbox": "#3D6EFF", "checkbox_hover": "#5580FF",
    },
    "Ocean": {
        "bg": "#0D1B2A", "card": "#1B2A3B", "elevated": "#1E3448",
        "primary": "#0EA5E9", "primary_dim": "#38BDF8",
        "secondary": "#7DD3FC", "error": "#B3261E", "error_hover": "#8C1D18",
        "error_text": "#F2B8B5", "on_surface": "#E0F2FE", "on_surface2": "#BAE6FD",
        "outline": "#164E63", "separator": "#0C3547",
        "green_btn": "#065F46", "green_hover": "#064E3B",
        "blue_btn": "#1E40AF", "blue_hover": "#1E3A8A",
        "tab_selected": "#0369A1", "tab_selected_hover": "#0284C7",
        "value_text": "#38BDF8", "checkbox": "#0EA5E9", "checkbox_hover": "#38BDF8",
    },
    "Light": {
        # Wet Asphalt & Sand — dark matte asphalt bg + warm sandy accents
        "bg": "#1C2128", "card": "#161B22", "elevated": "#12171D",
        "primary": "#C8A96E", "primary_dim": "#B8945A",
        "secondary": "#D4B483", "error": "#8B2A1A", "error_hover": "#6E1E12",
        "error_text": "#E8A090", "on_surface": "#F0EDE8", "on_surface2": "#B8B0A0",
        "outline": "#2E3540", "separator": "#252C36",
        "green_btn": "#1A4A30", "green_hover": "#123520",
        "blue_btn": "#2A3A4A", "blue_hover": "#354A5E",
        "tab_selected": "#8A7040", "tab_selected_hover": "#A08050",
        "value_text": "#D4B483", "checkbox": "#C8A96E", "checkbox_hover": "#D4B483",
    },
}


def _load_theme(name: str) -> dict:
    return THEMES.get(name, THEMES["Dark Mode"])


def _read_saved_theme() -> str:
    try:
        with open(GUI_CONFIG_PATH) as f:
            return json.load(f).get("theme", "Dark Mode")
    except Exception:
        return "Dark Mode"


MD3_NAME = _read_saved_theme()
MD3 = _load_theme(MD3_NAME)


TUNE_TARGET_NAMES = ("wt_icon", "carter", "top_accel", "march_accel", "chest_sender", "chest_type", "chest_collect")


LANGS = {
    "RU": {
        # --- существующие ---
        "title": "Total Hunter", "tab_hunt": "БИРЖИ", "tab_combo": "Combo", "tab_ref": "РЕФЕРАЛЫ",
        "get_trial": "ПОЛУЧИТЬ 300 ПОПЫТОК", "start": "ЗАПУСТИТЬ ОХОТУ", "stop": "ОСТАНОВИТЬ",
        "no_credits": "У вас 0 алмазов! Привяжите устройство на сайте.", "offline_stopped": "Остановлено: нет связи с сервером", "login_btn": "ПРИВЯЗАТЬ УСТРОЙСТВО",
        "banned": "ВАШ АККАУНТ ЗАБЛОКИРОВАН", "ref_title": "ПАРТНЕРСКАЯ ПРОГРАММА",
        "my_code": "ВАШ КОД ДЛЯ ПРИГЛАШЕНИЯ:", "friend_code": "КОД ПРИГЛАСИТЕЛЯ (+50):",
        "activate_ref": "АКТИВИРОВАТЬ", "ref_used": "БОНУС АКТИВИРОВАН ✅",
        "accuracy": "Точность поиска", "scan_rate": "Частота сканирования", "sec": "сек.",
        "copy": "КОПИРОВАТЬ", "share_text": "ПОДЕЛИТЕСЬ КОДОМ И ПОЛУЧАЙТЕ %", "copied": "Скопировано!",
        "clicker_title": "Синхронизация Clickermann", "clicker_on": "ВКЛЮЧИТЬ", "key_start": "Старт:", "key_stop": "Стоп:",
        "status_ready": "СИСТЕМА ГОТОВА", "status_running": "СТАТУС: В ПОИСКЕ...",
        # --- новые tab names ---
        "tab_crypt": "СКЛЕПЫ", "tab_cal": "Калибровка", "tab_roy": "РОЙ", "tab_chest": "СУНДУКИ",
        # --- chest tab ---
        "chest_kingdom_lb": "Королевство:", "chest_clan_lb": "Название клана:",
        "chest_start_btn": "СТАРТ", "chest_stop_btn": "СТОП",
        "chest_status_ready": "Готово к сбору", "chest_status_running": "Сбор сундуков...",
        "chest_status_stopped": "Остановлено", "chest_status_no_dialog": "Откройте «Мой клан → Подарки»",
        "chest_missing_fields": "Укажите Королевство и Клан",
        "chest_send_btn": "ОТПРАВИТЬ НА СЕРВЕР", "chest_send_success": "Отправлено на сервер",
        "chest_send_failed": "Сервер недоступен. Данные сохранены локально.",
        "tab_ancient": "ДРЕВНИЙ", "ancient_status_running": "Сбор турнирной таблицы...", "ancient_status_sent": "Отправлено на сервер", "ancient_status_failed": "Сервер недоступен. Данные сохранены локально.",
        "ancient_desc": "Откройте диалог «Статистика» в игре перед запуском.",
        "chest_total_lb": "Всего открыто:",
        "chest_speed_lb": "Скорость клика:",
        # --- hunt tab ---
        "nn_title": "Нейросеть", "nav_main_title": "Навигация",
        "nav_extra_title": "Дополнительно", "nav_auto": "Авто",
        "save_settings": "Сохранить настройки",
        "nav_step": "Шаг:", "nav_wait": "Скорость работы (сек/шаг):",
        "nav_inland": "Глубина нырка (экранов):", "nav_ocean": "Граница океан/суша (%):",
        "nav_waterpx": "Мин. размер водоёма:", "nav_diagblind": "Коэф. диагонали возврата:",
        "nav_footprint": "Память следов (сек):", "nav_delta": "Дельта возврата (px):",
        "nav_pitch": "Живость хода (%):",
        # --- crypt tab ---
        "crypt_icons_title": "Выберите типы склепов:",
        "crypt_conf_lb": "Точность поиска", "crypt_accel_lb": "Ускорение марша (0–5)",
        "crypt_break_lb": "Перерыв между склепами", "crypt_march_lb": "Дальность марша Картера",
        "crypt_scroll_lb": "Частота YOLO-детекции", "scroll_clicks_lb": "Тики скролла", "crypt_profile_lb": "Профиль:",
        "crypt_swing1_lb": "Swing 1 — Исследовать ↑↓:", "crypt_swing2_lb": "Swing 2 — Ускорение ↑↓:",
        "crypt_speed_lb": "Скорость кликов",
        "crypt_save_btn": "💾  Сохранить настройки",
        "crypt_start": "ЗАПУСТИТЬ СБОР СКЛЕПОВ", "crypt_stop_btn": "ОСТАНОВИТЬ",
        "crypt_ready": "ГОТОВО", "crypt_stopped": "Остановлено",
        "crypt_select_warn": "Выберите хотя бы один тип!", "crypt_searching": "СТАТУС: В ПОИСКЕ...",
        "crypt_collected": "Собрано", "crypt_last": "последний",
        # --- calibration tab ---
        "cal_title": "Калибровка экрана",
        "cal_desc": "Откройте игру в привычном режиме, затем установите две точки.",
        "cal_pt_a_lb": "Точка A — мини-карта",
        "cal_pt_a_desc": "Уменьшите зум\nмини-карты до мин.\nКликните по центру.",
        "cal_pt_b_lb": "Точка B — Серебро",
        "cal_pt_b_desc": "Наведите на иконку\nСеребра до появления «+».\nКликните по «+».",
        "cal_profile_lb": "Профиль:", "cal_not_calibrated": "Не откалиброван",
        "cal_auto_btn": "АВТОКАЛИБРОВАТЬ", "cal_manual_btn": "КАЛИБРОВАТЬ",
        "cal_save_btn": "💾  Сохранить", "cal_load_btn": "📂  Загрузить",
        "cal_tune_title": "Тюнинг кликов", "cal_tune_wt_icon": "Дозорная башня", "cal_tune_carter": "Отправка Картера", "cal_tune_top_accel": "Ускорить (Картер)", "cal_tune_march_accel": "Использовать ускорение", "cal_tune_reset": "Сброс", "cal_tune_chest_sender": "Имя игрока (сундуки)", "cal_tune_chest_type": "Источник (сундуки)", "cal_tune_chest_collect": "Открыть (сундуки)",
        # --- ref tab additions ---
        "ref_bal_title": "Реферальный баланс", "ref_transfer_btn": "💸  Перевести на баланс  →",
        "ref_link_title": "Ваша реферальная ссылка:", "ref_code_prefix": "Код: ",
        "ref_stats_title": "Рефералы",
        # --- units ---
        "unit_sec": "с", "unit_min": "мин", "unit_scan": "скан",
        "tr_event": "Торговые Пути", "tr_active": "🟢 ИДЁТ — осталось", "tr_ends_in": "🟢 ИДЁТ — до конца:", "tr_starts_in": "до начала:",
        # --- roy tab ---
        "roy_title": "⬡  СИСТЕМА РОЙ", "roy_subtitle": "Делись координатами бирж — получай чужие",
        "roy_balance_title": "⏱ Баланс доступа", "roy_join": "Участвовать в Рое",
        "roy_kingdom_label": "Королевство №:", "roy_coords_title": "Координаты от участников:",
        "roy_refresh": "↻  Обновить пул", "roy_no_data": "Нет данных. Включи Рой и запусти бота.",
        "roy_error": "Ошибка", "roy_empty_pool": "Нет активных координат.",
        "roy_pool_empty": "Пул пуст", "roy_pool_count": "Координат в пуле",
    },
    "EN": {
        # --- существующие ---
        "title": "Total Hunter", "tab_hunt": "EXCHANGE", "tab_combo": "Combo", "tab_ref": "REFERRALS",
        "get_trial": "GET 300 TRIALS", "start": "START HUNT", "stop": "STOP",
        "no_credits": "0 diamonds! Link your device on the website.", "offline_stopped": "Stopped: no connection to server", "login_btn": "LINK DEVICE",
        "banned": "ACCOUNT BANNED", "ref_title": "REFERRAL SYSTEM",
        "my_code": "YOUR INVITE CODE:", "friend_code": "INVITER CODE (+50):",
        "activate_ref": "ACTIVATE", "ref_used": "BONUS ACTIVE ✅",
        "accuracy": "Detection Accuracy", "scan_rate": "Scan Interval", "sec": "sec.",
        "copy": "COPY", "share_text": "SHARE CODE AND GET %", "copied": "Copied!",
        "clicker_title": "Clickermann Sync", "clicker_on": "ENABLED", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "READY", "status_running": "STATUS: SEARCHING...",
        # --- новые tab names ---
        "tab_crypt": "CRYPTS", "tab_cal": "Calibration", "tab_roy": "SWARM", "tab_chest": "CHESTS",
        # --- chest tab ---
        "chest_kingdom_lb": "Kingdom:", "chest_clan_lb": "Clan name:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Ready to collect", "chest_status_running": "Collecting chests...",
        "chest_status_stopped": "Stopped", "chest_status_no_dialog": "Open «My Clan → Gifts»",
        "chest_missing_fields": "Enter Kingdom and Clan name",
        "chest_send_btn": "SEND TO SERVER", "chest_send_success": "Sent to server",
        "chest_send_failed": "Server unavailable. Data saved locally.",
        "tab_ancient": "ANCIENT", "ancient_status_running": "Collecting tournament data...", "ancient_status_sent": "Sent to server", "ancient_status_failed": "Server unavailable. Data saved locally.",
        "ancient_desc": "Open the in-game «Statistics» dialog before starting.",
        "chest_total_lb": "Total opened:",
        "chest_speed_lb": "Click speed:",
        # --- hunt tab ---
        "nn_title": "Neural Net", "nav_main_title": "Navigation",
        "nav_extra_title": "Advanced", "nav_auto": "Auto",
        "save_settings": "Save settings",
        "nav_step": "Step:", "nav_wait": "Bot speed (sec/step):",
        "nav_inland": "Dive depth (screens):", "nav_ocean": "Ocean/land ratio (%):",
        "nav_waterpx": "Min. water area (px):", "nav_diagblind": "Return diagonal coeff:",
        "nav_footprint": "Footprint TTL (sec):", "nav_delta": "Return delta (px):",
        "nav_pitch": "Motion smoothness (%):",
        # --- crypt tab ---
        "crypt_icons_title": "Select crypt types:",
        "crypt_conf_lb": "Detection accuracy", "crypt_accel_lb": "March acceleration (0–5)",
        "crypt_break_lb": "Break between crypts", "crypt_march_lb": "Carter march distance",
        "crypt_scroll_lb": "YOLO detection rate", "scroll_clicks_lb": "Scroll ticks", "crypt_profile_lb": "Profile:",
        "crypt_swing1_lb": "Swing 1 — Study ↑↓:", "crypt_swing2_lb": "Swing 2 — Speed up ↑↓:",
        "crypt_speed_lb": "Click speed",
        "crypt_save_btn": "💾  Save settings",
        "crypt_start": "START CRYPT HUNT", "crypt_stop_btn": "STOP",
        "crypt_ready": "READY", "crypt_stopped": "Stopped",
        "crypt_select_warn": "Select at least one type!", "crypt_searching": "STATUS: SEARCHING...",
        "crypt_collected": "Collected", "crypt_last": "last",
        # --- calibration tab ---
        "cal_title": "Screen Calibration",
        "cal_desc": "Open the game normally, then set two anchor points.",
        "cal_pt_a_lb": "Point A — minimap",
        "cal_pt_a_desc": "Set minimap zoom\nto minimum.\nClick center.",
        "cal_pt_b_lb": "Point B — Silver",
        "cal_pt_b_desc": "Hover Silver icon\nuntil «+» appears.\nClick «+».",
        "cal_profile_lb": "Profile:", "cal_not_calibrated": "Not calibrated",
        "cal_auto_btn": "AUTO CALIBRATE", "cal_manual_btn": "CALIBRATE",
        "cal_save_btn": "💾  Save", "cal_load_btn": "📂  Load",
        "cal_tune_title": "Click Tuning", "cal_tune_wt_icon": "Watchtower", "cal_tune_carter": "Send Carter", "cal_tune_top_accel": "Speed Up (Carter)", "cal_tune_march_accel": "Use Acceleration", "cal_tune_reset": "Reset", "cal_tune_chest_sender": "Player Name (Chests)", "cal_tune_chest_type": "Source (Chests)", "cal_tune_chest_collect": "Open (Chests)",
        # --- ref tab additions ---
        "ref_bal_title": "Referral Balance", "ref_transfer_btn": "💸  Transfer to balance  →",
        "ref_link_title": "Your referral link:", "ref_code_prefix": "Code: ",
        "ref_stats_title": "Referrals",
        # --- units ---
        "unit_sec": "s", "unit_min": "min", "unit_scan": "scan",
        "tr_event": "Trade Routes", "tr_active": "🟢 ACTIVE — left:", "tr_ends_in": "🟢 ACTIVE — ends in:", "tr_starts_in": "starts in:",
        # --- roy tab ---
        "roy_title": "⬡  SWARM SYSTEM", "roy_subtitle": "Share exchange coords — get others' in return",
        "roy_balance_title": "⏱ Access Balance", "roy_join": "Join the Swarm",
        "roy_kingdom_label": "Kingdom №:", "roy_coords_title": "Coordinates from members:",
        "roy_refresh": "↻  Refresh pool", "roy_no_data": "No data. Enable Swarm and start the bot.",
        "roy_error": "Error", "roy_empty_pool": "No active coordinates.",
        "roy_pool_empty": "Pool empty", "roy_pool_count": "Coords in pool",
    },
    "DE": {
        "title": "Total Hunter", "tab_hunt": "BÖRSEN", "tab_combo": "Combo", "tab_ref": "PARTNER",
        "get_trial": "300 VERSUCHE HOLEN", "start": "JAGD STARTEN", "stop": "STOPP",
        "no_credits": "0 Diamanten! Gerät auf Website verknüpfen.", "offline_stopped": "Gestoppt: keine Verbindung zum Server", "login_btn": "GERÄT VERKNÜPFEN",
        "banned": "KONTO GESPERRT", "ref_title": "PARTNERPROGRAMM",
        "my_code": "DEIN EINLADUNGSCODE:", "friend_code": "EINLADER-CODE (+50):",
        "activate_ref": "AKTIVIEREN", "ref_used": "BONUS AKTIV ✅",
        "accuracy": "Erkennungsgenauigkeit", "scan_rate": "Scan-Intervall", "sec": "Sek.",
        "copy": "KOPIEREN", "share_text": "CODE TEILEN UND % ERHALTEN", "copied": "Kopiert!",
        "clicker_title": "Clickermann Sync", "clicker_on": "AKTIVIERT", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "BEREIT", "status_running": "STATUS: SUCHE...",
        "tab_crypt": "KRYPTEN", "tab_cal": "Kalibrierung", "tab_roy": "SCHWARM", "tab_chest": "TRUHEN",
        # --- chest tab ---
        "chest_kingdom_lb": "Königreich:", "chest_clan_lb": "Clanname:",
        "chest_start_btn": "START", "chest_stop_btn": "STOPP",
        "chest_status_ready": "Bereit zum Sammeln", "chest_status_running": "Truhen werden gesammelt...",
        "chest_status_stopped": "Gestoppt", "chest_status_no_dialog": "Öffne «Mein Clan → Geschenke»",
        "chest_missing_fields": "Königreich und Clan angeben",
        "chest_send_btn": "AN SERVER SENDEN", "chest_send_success": "An Server gesendet",
        "chest_send_failed": "Server nicht erreichbar. Daten lokal gespeichert.",
        "tab_ancient": "URALTER", "ancient_status_running": "Turnierdaten werden gesammelt...", "ancient_status_sent": "An Server gesendet", "ancient_status_failed": "Server nicht erreichbar. Daten lokal gespeichert.",
        "ancient_desc": "Öffne den Dialog «Statistik» im Spiel, bevor du startest.",
        "chest_total_lb": "Insgesamt geöffnet:",
        "chest_speed_lb": "Klickgeschwindigkeit:",
        "nn_title": "Neuronales Netz", "nav_main_title": "Navigation",
        "nav_extra_title": "Erweitert", "nav_auto": "Auto", "save_settings": "Einstellungen speichern",
        "nav_step": "Schritt:", "nav_wait": "Geschw. (Sek/Schritt):",
        "nav_inland": "Tauchtiefe (Bildschirme):", "nav_ocean": "Ozean/Land-Verh. (%):",
        "nav_waterpx": "Min. Wasserfläche (px):", "nav_diagblind": "Rückkehr-Diag.-Koeff.:",
        "nav_footprint": "Spur-TTL (Sek.):", "nav_delta": "Rückkehr-Delta (px):",
        "nav_pitch": "Bewegungsfl. (%):",
        "crypt_icons_title": "Krypttypen auswählen:",
        "crypt_conf_lb": "Erkennungsgenauigkeit", "crypt_accel_lb": "Marchbeschl. (0–5)",
        "crypt_break_lb": "Pause zwischen Krypten", "crypt_march_lb": "Carter-Marchdistanz",
        "crypt_scroll_lb": "YOLO-Erkennungsrate", "scroll_clicks_lb": "Scroll-Ticks", "crypt_profile_lb": "Profil:",
        "crypt_swing1_lb": "Swing 1 — Erkunden ↑↓:", "crypt_swing2_lb": "Swing 2 — Beschl. ↑↓:",
        "crypt_speed_lb": "Klickgeschwindigkeit", "crypt_save_btn": "💾  Einstellungen speichern",
        "crypt_start": "KRYPTJAGD STARTEN", "crypt_stop_btn": "STOPP",
        "crypt_ready": "BEREIT", "crypt_stopped": "Gestoppt",
        "crypt_select_warn": "Mind. einen Typ wählen!", "crypt_searching": "STATUS: SUCHE...",
        "crypt_collected": "Gesammelt", "crypt_last": "letztes",
        "cal_title": "Bildschirmkalibrierung", "cal_desc": "Spiel öffnen, dann zwei Ankerpunkte setzen.",
        "cal_pt_a_lb": "Punkt A — Minikarte", "cal_pt_a_desc": "Minikarte-Zoom\nauf Minimum.\nMitte klicken.",
        "cal_pt_b_lb": "Punkt B — Silber", "cal_pt_b_desc": "Silber-Symbol hover\nbis «+» erscheint.\nAuf «+» klicken.",
        "cal_profile_lb": "Profil:", "cal_not_calibrated": "Nicht kalibriert",
        "cal_auto_btn": "AUTO KALIBRIEREN", "cal_manual_btn": "KALIBRIEREN",
        "cal_save_btn": "💾  Speichern", "cal_load_btn": "📂  Laden",
        "cal_tune_title": "Klick-Tuning", "cal_tune_wt_icon": "Wachturm", "cal_tune_carter": "Carter senden", "cal_tune_top_accel": "Beschleunigen (Carter)", "cal_tune_march_accel": "Beschleunigung verwenden", "cal_tune_reset": "Zurücksetzen", "cal_tune_chest_sender": "Spielername (Truhen)", "cal_tune_chest_type": "Quelle (Truhen)", "cal_tune_chest_collect": "Öffnen (Truhen)",
        "ref_bal_title": "Partner-Guthaben", "ref_transfer_btn": "💸  Auf Guthaben übertragen  →",
        "ref_link_title": "Dein Empfehlungslink:", "ref_code_prefix": "Code: ", "ref_stats_title": "Partner",
        "unit_sec": "s", "unit_min": "min", "unit_scan": "scan",
        "tr_event": "Handelsrouten", "tr_active": "🟢 AKTIV — verbleibend:", "tr_ends_in": "🟢 AKTIV — endet in:", "tr_starts_in": "beginnt in:",
        # --- roy tab ---
        "roy_title": "⬡  SCHWARM-SYSTEM", "roy_subtitle": "Koordinaten teilen — andere erhalten",
        "roy_balance_title": "⏱ Zugangsguthaben", "roy_join": "Am Schwarm teilnehmen",
        "roy_kingdom_label": "Königreich №:", "roy_coords_title": "Koordinaten der Mitglieder:",
        "roy_refresh": "↻  Pool aktualisieren", "roy_no_data": "Keine Daten. Schwarm aktivieren und Bot starten.",
        "roy_error": "Fehler", "roy_empty_pool": "Keine aktiven Koordinaten.",
        "roy_pool_empty": "Pool leer", "roy_pool_count": "Koordinaten im Pool",
    },
    "ES": {
        "title": "Total Hunter", "tab_hunt": "BOLSAS", "tab_combo": "Combo", "tab_ref": "REFERIDOS",
        "get_trial": "OBTENER 300 INTENTOS", "start": "INICIAR CAZA", "stop": "DETENER",
        "no_credits": "¡0 diamantes! Vincula tu dispositivo en el sitio.", "offline_stopped": "Detenido: sin conexión con el servidor", "login_btn": "VINCULAR DISPOSITIVO",
        "banned": "CUENTA BLOQUEADA", "ref_title": "PROGRAMA DE REFERIDOS",
        "my_code": "TU CÓDIGO DE INVITACIÓN:", "friend_code": "CÓDIGO DEL INVITADOR (+50):",
        "activate_ref": "ACTIVAR", "ref_used": "BONO ACTIVO ✅",
        "accuracy": "Precisión de detección", "scan_rate": "Intervalo de escaneo", "sec": "seg.",
        "copy": "COPIAR", "share_text": "COMPARTE EL CÓDIGO Y GANA %", "copied": "¡Copiado!",
        "clicker_title": "Clickermann Sync", "clicker_on": "ACTIVADO", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "LISTO", "status_running": "ESTADO: BUSCANDO...",
        "tab_crypt": "CRIPTAS", "tab_cal": "Calibración", "tab_roy": "ENJAMBRE", "tab_chest": "COFRES",
        # --- chest tab ---
        "chest_kingdom_lb": "Reino:", "chest_clan_lb": "Nombre del clan:",
        "chest_start_btn": "INICIAR", "chest_stop_btn": "DETENER",
        "chest_status_ready": "Listo para recolectar", "chest_status_running": "Recolectando cofres...",
        "chest_status_stopped": "Detenido", "chest_status_no_dialog": "Abra «Mi clan → Regalos»",
        "chest_missing_fields": "Indique Reino y Clan",
        "chest_send_btn": "ENVIAR AL SERVIDOR", "chest_send_success": "Enviado al servidor",
        "chest_send_failed": "Servidor no disponible. Datos guardados localmente.",
        "tab_ancient": "ANTIGUO", "ancient_status_running": "Recolectando datos del torneo...", "ancient_status_sent": "Enviado al servidor", "ancient_status_failed": "Servidor no disponible. Datos guardados localmente.",
        "ancient_desc": "Abre el diálogo «Estadísticas» en el juego antes de empezar.",
        "chest_total_lb": "Total abiertos:",
        "chest_speed_lb": "Velocidad de clic:",
        "nn_title": "Red Neuronal", "nav_main_title": "Navegación",
        "nav_extra_title": "Avanzado", "nav_auto": "Auto", "save_settings": "Guardar ajustes",
        "nav_step": "Paso:", "nav_wait": "Velocidad (seg/paso):",
        "nav_inland": "Prof. de buceo (pantallas):", "nav_ocean": "Ratio océano/tierra (%):",
        "nav_waterpx": "Área mín. de agua (px):", "nav_diagblind": "Coef. diag. retorno:",
        "nav_footprint": "TTL de huella (seg.):", "nav_delta": "Delta de retorno (px):",
        "nav_pitch": "Fluidez movimiento (%):",
        "crypt_icons_title": "Seleccionar tipos de cripta:",
        "crypt_conf_lb": "Precisión de detección", "crypt_accel_lb": "Aceleración de marcha (0–5)",
        "crypt_break_lb": "Pausa entre criptas", "crypt_march_lb": "Distancia de marcha Carter",
        "crypt_scroll_lb": "Tasa de detección YOLO", "scroll_clicks_lb": "Ticks desplazamiento", "crypt_profile_lb": "Perfil:",
        "crypt_swing1_lb": "Swing 1 — Explorar ↑↓:", "crypt_swing2_lb": "Swing 2 — Acelerar ↑↓:",
        "crypt_speed_lb": "Velocidad de clic", "crypt_save_btn": "💾  Guardar ajustes",
        "crypt_start": "INICIAR CAZA DE CRIPTAS", "crypt_stop_btn": "DETENER",
        "crypt_ready": "LISTO", "crypt_stopped": "Detenido",
        "crypt_select_warn": "¡Selecciona al menos un tipo!", "crypt_searching": "ESTADO: BUSCANDO...",
        "crypt_collected": "Recolectado", "crypt_last": "último",
        "cal_title": "Calibración de pantalla", "cal_desc": "Abre el juego normalmente, luego establece dos puntos de anclaje.",
        "cal_pt_a_lb": "Punto A — minimapa", "cal_pt_a_desc": "Zoom del minimapa\nal mínimo.\nClic en el centro.",
        "cal_pt_b_lb": "Punto B — Plata", "cal_pt_b_desc": "Hover sobre ícono Plata\nhasta que aparezca «+».\nClic en «+».",
        "cal_profile_lb": "Perfil:", "cal_not_calibrated": "No calibrado",
        "cal_auto_btn": "AUTO CALIBRAR", "cal_manual_btn": "CALIBRAR",
        "cal_save_btn": "💾  Guardar", "cal_load_btn": "📂  Cargar",
        "cal_tune_title": "Ajuste de clics", "cal_tune_wt_icon": "Torre de guardia", "cal_tune_carter": "Enviar Carter", "cal_tune_top_accel": "Acelerar (Carter)", "cal_tune_march_accel": "Usar aceleración", "cal_tune_reset": "Restablecer", "cal_tune_chest_sender": "Nombre del jugador (Cofres)", "cal_tune_chest_type": "Fuente (Cofres)", "cal_tune_chest_collect": "Abrir (Cofres)",
        "ref_bal_title": "Saldo de referidos", "ref_transfer_btn": "💸  Transferir al saldo  →",
        "ref_link_title": "Tu enlace de referido:", "ref_code_prefix": "Código: ", "ref_stats_title": "Referidos",
        "unit_sec": "s", "unit_min": "min", "unit_scan": "scan",
        "tr_event": "Rutas Comerciales", "tr_active": "🟢 ACTIVO — quedan:", "tr_ends_in": "🟢 ACTIVO — termina en:", "tr_starts_in": "comienza en:",
        # --- roy tab ---
        "roy_title": "⬡  SISTEMA ENJAMBRE", "roy_subtitle": "Comparte coordenadas — recibe las de otros",
        "roy_balance_title": "⏱ Saldo de acceso", "roy_join": "Unirse al Enjambre",
        "roy_kingdom_label": "Reino №:", "roy_coords_title": "Coordenadas de participantes:",
        "roy_refresh": "↻  Actualizar pool", "roy_no_data": "Sin datos. Activa el Enjambre y lanza el bot.",
        "roy_error": "Error", "roy_empty_pool": "Sin coordenadas activas.",
        "roy_pool_empty": "Pool vacío", "roy_pool_count": "Coords en el pool",
    },
    "FR": {
        "title": "Total Hunter", "tab_hunt": "ÉCHANGES", "tab_combo": "Combo", "tab_ref": "PARRAINAGES",
        "get_trial": "OBTENIR 300 ESSAIS", "start": "LANCER LA CHASSE", "stop": "ARRÊTER",
        "no_credits": "0 diamants ! Liez votre appareil sur le site.", "offline_stopped": "Arrêté : pas de connexion au serveur", "login_btn": "LIER L'APPAREIL",
        "banned": "COMPTE BANNI", "ref_title": "PROGRAMME DE PARRAINAGE",
        "my_code": "VOTRE CODE D'INVITATION :", "friend_code": "CODE DU PARRAIN (+50) :",
        "activate_ref": "ACTIVER", "ref_used": "BONUS ACTIF ✅",
        "accuracy": "Précision de détection", "scan_rate": "Intervalle de scan", "sec": "sec.",
        "copy": "COPIER", "share_text": "PARTAGEZ LE CODE ET GAGNEZ %", "copied": "Copié !",
        "clicker_title": "Clickermann Sync", "clicker_on": "ACTIVÉ", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "PRÊT", "status_running": "STATUT : RECHERCHE...",
        "tab_crypt": "CRYPTES", "tab_cal": "Calibration", "tab_roy": "ESSAIM", "tab_chest": "COFFRES",
        # --- chest tab ---
        "chest_kingdom_lb": "Royaume :", "chest_clan_lb": "Nom du clan :",
        "chest_start_btn": "DÉMARRER", "chest_stop_btn": "ARRÊTER",
        "chest_status_ready": "Prêt à collecter", "chest_status_running": "Collecte des coffres...",
        "chest_status_stopped": "Arrêté", "chest_status_no_dialog": "Ouvrez «Mon clan → Cadeaux»",
        "chest_missing_fields": "Indiquez le Royaume et le Clan",
        "chest_send_btn": "ENVOYER AU SERVEUR", "chest_send_success": "Envoyé au serveur",
        "chest_send_failed": "Serveur indisponible. Données enregistrées localement.",
        "tab_ancient": "ANCIEN", "ancient_status_running": "Collecte des données du tournoi...", "ancient_status_sent": "Envoyé au serveur", "ancient_status_failed": "Serveur indisponible. Données enregistrées localement.",
        "ancient_desc": "Ouvrez la boîte de dialogue «Statistiques» dans le jeu avant de démarrer.",
        "chest_total_lb": "Total ouverts :",
        "chest_speed_lb": "Vitesse de clic :",
        "nn_title": "Réseau de neurones", "nav_main_title": "Navigation",
        "nav_extra_title": "Avancé", "nav_auto": "Auto", "save_settings": "Sauvegarder les paramètres",
        "nav_step": "Pas :", "nav_wait": "Vitesse (sec/pas) :",
        "nav_inland": "Prof. de plongée (écrans) :", "nav_ocean": "Ratio océan/terre (%) :",
        "nav_waterpx": "Surface eau min. (px) :", "nav_diagblind": "Coeff. diag. retour :",
        "nav_footprint": "TTL empreinte (sec.) :", "nav_delta": "Delta retour (px) :",
        "nav_pitch": "Fluidité mouvement (%) :",
        "crypt_icons_title": "Sélectionner types de crypte :",
        "crypt_conf_lb": "Précision de détection", "crypt_accel_lb": "Accél. de marche (0–5)",
        "crypt_break_lb": "Pause entre cryptes", "crypt_march_lb": "Distance de marche Carter",
        "crypt_scroll_lb": "Taux détection YOLO", "scroll_clicks_lb": "Ticks défilement", "crypt_profile_lb": "Profil :",
        "crypt_swing1_lb": "Swing 1 — Explorer ↑↓ :", "crypt_swing2_lb": "Swing 2 — Accél. ↑↓ :",
        "crypt_speed_lb": "Vitesse de clic", "crypt_save_btn": "💾  Sauvegarder",
        "crypt_start": "DÉMARRER LA CHASSE AUX CRYPTES", "crypt_stop_btn": "ARRÊTER",
        "crypt_ready": "PRÊT", "crypt_stopped": "Arrêté",
        "crypt_select_warn": "Sélectionnez au moins un type !", "crypt_searching": "STATUT : RECHERCHE...",
        "crypt_collected": "Collecté", "crypt_last": "dernier",
        "cal_title": "Calibration de l'écran", "cal_desc": "Ouvrez le jeu normalement, puis définissez deux points d'ancrage.",
        "cal_pt_a_lb": "Point A — minimap", "cal_pt_a_desc": "Zoom minimap\nau minimum.\nCliquer au centre.",
        "cal_pt_b_lb": "Point B — Argent", "cal_pt_b_desc": "Survoler icône Argent\njusqu'à «+».\nCliquer sur «+».",
        "cal_profile_lb": "Profil :", "cal_not_calibrated": "Non calibré",
        "cal_auto_btn": "AUTO CALIBRER", "cal_manual_btn": "CALIBRER",
        "cal_save_btn": "💾  Sauvegarder", "cal_load_btn": "📂  Charger",
        "cal_tune_title": "Réglage des clics", "cal_tune_wt_icon": "Tour de guet", "cal_tune_carter": "Envoyer Carter", "cal_tune_top_accel": "Accélérer (Carter)", "cal_tune_march_accel": "Utiliser l'accélération", "cal_tune_reset": "Réinitialiser", "cal_tune_chest_sender": "Nom du joueur (Coffres)", "cal_tune_chest_type": "Source (Coffres)", "cal_tune_chest_collect": "Ouvrir (Coffres)",
        "ref_bal_title": "Solde parrainage", "ref_transfer_btn": "💸  Transférer au solde  →",
        "ref_link_title": "Votre lien de parrainage :", "ref_code_prefix": "Code : ", "ref_stats_title": "Parrainages",
        "unit_sec": "s", "unit_min": "min", "unit_scan": "scan",
        "tr_event": "Routes Commerciales", "tr_active": "🟢 ACTIF — reste :", "tr_ends_in": "🟢 ACTIF — fin dans :", "tr_starts_in": "commence dans :",
        # --- roy tab ---
        "roy_title": "⬡  SYSTÈME ESSAIM", "roy_subtitle": "Partage des coords — reçois celles des autres",
        "roy_balance_title": "⏱ Solde d'accès", "roy_join": "Rejoindre l'Essaim",
        "roy_kingdom_label": "Royaume №:", "roy_coords_title": "Coordonnées des membres :",
        "roy_refresh": "↻  Actualiser le pool", "roy_no_data": "Pas de données. Active l'Essaim et lance le bot.",
        "roy_error": "Erreur", "roy_empty_pool": "Aucune coordonnée active.",
        "roy_pool_empty": "Pool vide", "roy_pool_count": "Coords dans le pool",
    },
    "IT": {
        "title": "Total Hunter", "tab_hunt": "BORSE", "tab_combo": "Combo", "tab_ref": "REFERRAL",
        "get_trial": "OTTIENI 300 TENTATIVI", "start": "AVVIA CACCIA", "stop": "FERMA",
        "no_credits": "0 diamanti! Collega il tuo dispositivo sul sito.", "offline_stopped": "Fermato: nessuna connessione al server", "login_btn": "COLLEGA DISPOSITIVO",
        "banned": "ACCOUNT BANNATO", "ref_title": "PROGRAMMA REFERRAL",
        "my_code": "IL TUO CODICE INVITO:", "friend_code": "CODICE INVITANTE (+50):",
        "activate_ref": "ATTIVA", "ref_used": "BONUS ATTIVO ✅",
        "accuracy": "Precisione rilevamento", "scan_rate": "Intervallo scansione", "sec": "sec.",
        "copy": "COPIA", "share_text": "CONDIVIDI IL CODICE E GUADAGNA %", "copied": "Copiato!",
        "clicker_title": "Clickermann Sync", "clicker_on": "ABILITATO", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "PRONTO", "status_running": "STATO: RICERCA...",
        "tab_crypt": "CRIPTE", "tab_cal": "Calibrazione", "tab_roy": "SCIAME", "tab_chest": "SCRIGNI",
        # --- chest tab ---
        "chest_kingdom_lb": "Regno:", "chest_clan_lb": "Nome del clan:",
        "chest_start_btn": "AVVIA", "chest_stop_btn": "STOP",
        "chest_status_ready": "Pronto per la raccolta", "chest_status_running": "Raccolta scrigni...",
        "chest_status_stopped": "Fermato", "chest_status_no_dialog": "Apri «Il mio clan → Regali»",
        "chest_missing_fields": "Indica Regno e Clan",
        "chest_send_btn": "INVIA AL SERVER", "chest_send_success": "Inviato al server",
        "chest_send_failed": "Server non disponibile. Dati salvati localmente.",
        "tab_ancient": "ANTICO", "ancient_status_running": "Raccolta dati del torneo...", "ancient_status_sent": "Inviato al server", "ancient_status_failed": "Server non disponibile. Dati salvati localmente.",
        "ancient_desc": "Apri la finestra «Statistiche» nel gioco prima di avviare.",
        "chest_total_lb": "Totale aperti:",
        "chest_speed_lb": "Velocità di clic:",
        "nn_title": "Rete Neurale", "nav_main_title": "Navigazione",
        "nav_extra_title": "Avanzato", "nav_auto": "Auto", "save_settings": "Salva impostazioni",
        "nav_step": "Passo:", "nav_wait": "Velocità (sec/passo):",
        "nav_inland": "Prof. immersione (schermi):", "nav_ocean": "Rapporto oceano/terra (%):",
        "nav_waterpx": "Area acqua min. (px):", "nav_diagblind": "Coeff. diag. ritorno:",
        "nav_footprint": "TTL impronta (sec.):", "nav_delta": "Delta ritorno (px):",
        "nav_pitch": "Fluidità movimento (%):",
        "crypt_icons_title": "Seleziona tipi di cripta:",
        "crypt_conf_lb": "Precisione rilevamento", "crypt_accel_lb": "Accelerazione marcia (0–5)",
        "crypt_break_lb": "Pausa tra cripte", "crypt_march_lb": "Distanza marcia Carter",
        "crypt_scroll_lb": "Frequenza rilevamento YOLO", "scroll_clicks_lb": "Tick scorrimento", "crypt_profile_lb": "Profilo:",
        "crypt_swing1_lb": "Swing 1 — Esplora ↑↓:", "crypt_swing2_lb": "Swing 2 — Accel. ↑↓:",
        "crypt_speed_lb": "Velocità clic", "crypt_save_btn": "💾  Salva impostazioni",
        "crypt_start": "AVVIA CACCIA CRIPTE", "crypt_stop_btn": "FERMA",
        "crypt_ready": "PRONTO", "crypt_stopped": "Fermato",
        "crypt_select_warn": "Seleziona almeno un tipo!", "crypt_searching": "STATO: RICERCA...",
        "crypt_collected": "Raccolto", "crypt_last": "ultimo",
        "cal_title": "Calibrazione schermo", "cal_desc": "Apri il gioco normalmente, poi imposta due punti di ancoraggio.",
        "cal_pt_a_lb": "Punto A — minimappa", "cal_pt_a_desc": "Zoom minimappa\nal minimo.\nClicca al centro.",
        "cal_pt_b_lb": "Punto B — Argento", "cal_pt_b_desc": "Passa su icona Argento\nfinché appare «+».\nClicca su «+».",
        "cal_profile_lb": "Profilo:", "cal_not_calibrated": "Non calibrato",
        "cal_auto_btn": "AUTO CALIBRA", "cal_manual_btn": "CALIBRA",
        "cal_save_btn": "💾  Salva", "cal_load_btn": "📂  Carica",
        "cal_tune_title": "Regolazione clic", "cal_tune_wt_icon": "Torre di guardia", "cal_tune_carter": "Invia Carter", "cal_tune_top_accel": "Accelera (Carter)", "cal_tune_march_accel": "Usa accelerazione", "cal_tune_reset": "Ripristina", "cal_tune_chest_sender": "Nome giocatore (Forzieri)", "cal_tune_chest_type": "Fonte (Forzieri)", "cal_tune_chest_collect": "Apri (Forzieri)",
        "ref_bal_title": "Saldo referral", "ref_transfer_btn": "💸  Trasferisci al saldo  →",
        "ref_link_title": "Il tuo link referral:", "ref_code_prefix": "Codice: ", "ref_stats_title": "Referral",
        "unit_sec": "s", "unit_min": "min", "unit_scan": "scan",
        "tr_event": "Rotte Commerciali", "tr_active": "🟢 ATTIVO — rimane:", "tr_ends_in": "🟢 ATTIVO — finisce in:", "tr_starts_in": "inizia tra:",
        # --- roy tab ---
        "roy_title": "⬡  SISTEMA SCIAME", "roy_subtitle": "Condividi coordinate — ricevi quelle degli altri",
        "roy_balance_title": "⏱ Saldo accesso", "roy_join": "Partecipa allo Sciame",
        "roy_kingdom_label": "Regno №:", "roy_coords_title": "Coordinate dei membri:",
        "roy_refresh": "↻  Aggiorna pool", "roy_no_data": "Nessun dato. Attiva lo Sciame e avvia il bot.",
        "roy_error": "Errore", "roy_empty_pool": "Nessuna coordinata attiva.",
        "roy_pool_empty": "Pool vuoto", "roy_pool_count": "Coord nel pool",
    },
    "NL": {
        "title": "Total Hunter", "tab_hunt": "BEURZEN", "tab_combo": "Combo", "tab_ref": "REFS",
        "get_trial": "300 POGINGEN KRIJGEN", "start": "JACHT STARTEN", "stop": "STOPPEN",
        "no_credits": "0 diamanten! Koppel je apparaat op de website.", "offline_stopped": "Gestopt: geen verbinding met de server", "login_btn": "APPARAAT KOPPELEN",
        "banned": "ACCOUNT GEBLOKKEERD", "ref_title": "REFERRALPROGRAMMA",
        "my_code": "JOUW UITNODIGINGSCODE:", "friend_code": "CODE VAN UITNODIGER (+50):",
        "activate_ref": "ACTIVEREN", "ref_used": "BONUS ACTIEF ✅",
        "accuracy": "Detectienauwkeurigheid", "scan_rate": "Scaninterval", "sec": "sec.",
        "copy": "KOPIËREN", "share_text": "DEEL CODE EN VERDIEN %", "copied": "Gekopieerd!",
        "clicker_title": "Clickermann Sync", "clicker_on": "INGESCHAKELD", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "KLAAR", "status_running": "STATUS: ZOEKEN...",
        "tab_crypt": "CRYPTEN", "tab_cal": "Kalibratie", "tab_roy": "ZWERM", "tab_chest": "KISTEN",
        # --- chest tab ---
        "chest_kingdom_lb": "Koninkrijk:", "chest_clan_lb": "Clannaam:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Gereed om te verzamelen", "chest_status_running": "Kisten verzamelen...",
        "chest_status_stopped": "Gestopt", "chest_status_no_dialog": "Open «Mijn clan → Geschenken»",
        "chest_missing_fields": "Vul Koninkrijk en Clan in",
        "chest_send_btn": "VERZENDEN NAAR SERVER", "chest_send_success": "Verzonden naar server",
        "chest_send_failed": "Server niet bereikbaar. Gegevens lokaal opgeslagen.",
        "tab_ancient": "ALOUDE", "ancient_status_running": "Toernooigegevens verzamelen...", "ancient_status_sent": "Verzonden naar server", "ancient_status_failed": "Server niet bereikbaar. Gegevens lokaal opgeslagen.",
        "ancient_desc": "Open het «Statistieken»-dialoogvenster in de game voordat je start.",
        "chest_total_lb": "Totaal geopend:",
        "chest_speed_lb": "Kliksnelheid:",
        "nn_title": "Neuraal Netwerk", "nav_main_title": "Navigatie",
        "nav_extra_title": "Geavanceerd", "nav_auto": "Auto", "save_settings": "Instellingen opslaan",
        "nav_step": "Stap:", "nav_wait": "Snelheid (sec/stap):",
        "nav_inland": "Duikdiepte (schermen):", "nav_ocean": "Oceaan/land-verh. (%):",
        "nav_waterpx": "Min. wateroppervlak (px):", "nav_diagblind": "Terugkeer diag.-coeff.:",
        "nav_footprint": "Voetafdruk TTL (sec.):", "nav_delta": "Terugkeerdelta (px):",
        "nav_pitch": "Bewegingsvloeiendheid (%):",
        "crypt_icons_title": "Selecteer crypttypen:",
        "crypt_conf_lb": "Detectienauwkeurigheid", "crypt_accel_lb": "Marsbescherming (0–5)",
        "crypt_break_lb": "Pauze tussen crypten", "crypt_march_lb": "Carter-marsafstand",
        "crypt_scroll_lb": "YOLO-detectiesnelheid", "scroll_clicks_lb": "Scroll-ticks", "crypt_profile_lb": "Profiel:",
        "crypt_swing1_lb": "Swing 1 — Verkennen ↑↓:", "crypt_swing2_lb": "Swing 2 — Versnellen ↑↓:",
        "crypt_speed_lb": "Kliksnelheid", "crypt_save_btn": "💾  Instellingen opslaan",
        "crypt_start": "CRYPTJACHT STARTEN", "crypt_stop_btn": "STOPPEN",
        "crypt_ready": "KLAAR", "crypt_stopped": "Gestopt",
        "crypt_select_warn": "Selecteer minstens één type!", "crypt_searching": "STATUS: ZOEKEN...",
        "crypt_collected": "Verzameld", "crypt_last": "laatste",
        "cal_title": "Schermkalibratie", "cal_desc": "Open het spel normaal, stel dan twee ankerpunten in.",
        "cal_pt_a_lb": "Punt A — minikaart", "cal_pt_a_desc": "Minikaart-zoom\nnaar minimum.\nKlik in midden.",
        "cal_pt_b_lb": "Punt B — Zilver", "cal_pt_b_desc": "Hover over Zilver-icoon\ntot «+» verschijnt.\nKlik op «+».",
        "cal_profile_lb": "Profiel:", "cal_not_calibrated": "Niet gekalibreerd",
        "cal_auto_btn": "AUTO KALIBREREN", "cal_manual_btn": "KALIBREREN",
        "cal_save_btn": "💾  Opslaan", "cal_load_btn": "📂  Laden",
        "cal_tune_title": "Klik-tuning", "cal_tune_wt_icon": "Wachttoren", "cal_tune_carter": "Carter sturen", "cal_tune_top_accel": "Versnellen (Carter)", "cal_tune_march_accel": "Versnelling gebruiken", "cal_tune_reset": "Herstellen", "cal_tune_chest_sender": "Spelersnaam (Kisten)", "cal_tune_chest_type": "Bron (Kisten)", "cal_tune_chest_collect": "Openen (Kisten)",
        "ref_bal_title": "Referralsaldo", "ref_transfer_btn": "💸  Overzetten naar saldo  →",
        "ref_link_title": "Jouw referrallink:", "ref_code_prefix": "Code: ", "ref_stats_title": "Referrals",
        "unit_sec": "s", "unit_min": "min", "unit_scan": "scan",
        "tr_event": "Handelsroutes", "tr_active": "🟢 ACTIEF — over:", "tr_ends_in": "🟢 ACTIEF — eindigt in:", "tr_starts_in": "begint over:",
        # --- roy tab ---
        "roy_title": "⬡  ZWERM-SYSTEEM", "roy_subtitle": "Deel coördinaten — ontvang die van anderen",
        "roy_balance_title": "⏱ Toegangssaldo", "roy_join": "Deelnemen aan Zwerm",
        "roy_kingdom_label": "Koninkrijk №:", "roy_coords_title": "Coördinaten van leden:",
        "roy_refresh": "↻  Pool vernieuwen", "roy_no_data": "Geen data. Activeer Zwerm en start de bot.",
        "roy_error": "Fout", "roy_empty_pool": "Geen actieve coördinaten.",
        "roy_pool_empty": "Pool leeg", "roy_pool_count": "Coords in pool",
    },
    "NO": {
        "title": "Total Hunter", "tab_hunt": "BØRSER", "tab_combo": "Combo", "tab_ref": "REFERANSER",
        "get_trial": "FÅ 300 FORSØK", "start": "START JAKT", "stop": "STOPP",
        "no_credits": "0 diamanter! Koble enheten på nettstedet.", "offline_stopped": "Stoppet: ingen forbindelse til serveren", "login_btn": "KOBLE ENHET",
        "banned": "KONTO UTESTENGT", "ref_title": "REFERANSEPROGRAM",
        "my_code": "DIN INVITASJONSKODE:", "friend_code": "INVITERERS KODE (+50):",
        "activate_ref": "AKTIVER", "ref_used": "BONUS AKTIV ✅",
        "accuracy": "Deteksjonsnøyaktighet", "scan_rate": "Skanneintervall", "sec": "sek.",
        "copy": "KOPIER", "share_text": "DEL KODE OG TJEN %", "copied": "Kopiert!",
        "clicker_title": "Clickermann Sync", "clicker_on": "AKTIVERT", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "KLAR", "status_running": "STATUS: SØKER...",
        "tab_crypt": "KRYPTER", "tab_cal": "Kalibrering", "tab_roy": "SVERM", "tab_chest": "KISTER",
        # --- chest tab ---
        "chest_kingdom_lb": "Kongerike:", "chest_clan_lb": "Klannavn:",
        "chest_start_btn": "START", "chest_stop_btn": "STOPP",
        "chest_status_ready": "Klar til å samle", "chest_status_running": "Samler kister...",
        "chest_status_stopped": "Stoppet", "chest_status_no_dialog": "Åpne «Min klan → Gaver»",
        "chest_missing_fields": "Angi kongerike og klan",
        "chest_send_btn": "SEND TIL SERVER", "chest_send_success": "Sendt til server",
        "chest_send_failed": "Server utilgjengelig. Data lagret lokalt.",
        "tab_ancient": "URGAMMEL", "ancient_status_running": "Samler turneringsdata...", "ancient_status_sent": "Sendt til server", "ancient_status_failed": "Server utilgjengelig. Data lagret lokalt.",
        "ancient_desc": "Åpne «Statistikk»-dialogen i spillet før du starter.",
        "chest_total_lb": "Totalt åpnet:",
        "chest_speed_lb": "Klikkhastighet:",
        "nn_title": "Nevralt Nettverk", "nav_main_title": "Navigasjon",
        "nav_extra_title": "Avansert", "nav_auto": "Auto", "save_settings": "Lagre innstillinger",
        "nav_step": "Steg:", "nav_wait": "Hastighet (sek/steg):",
        "nav_inland": "Dybde (skjermer):", "nav_ocean": "Hav/land-forhold (%):",
        "nav_waterpx": "Min. vannflate (px):", "nav_diagblind": "Returdiag.-koeff.:",
        "nav_footprint": "Fotavtrykk TTL (sek.):", "nav_delta": "Returdelta (px):",
        "nav_pitch": "Bevegelsesflyt (%):",
        "crypt_icons_title": "Velg krypttyper:",
        "crypt_conf_lb": "Deteksjonsnøyaktighet", "crypt_accel_lb": "Marsjacc. (0–5)",
        "crypt_break_lb": "Pause mellom krypter", "crypt_march_lb": "Carter marsjavstand",
        "crypt_scroll_lb": "YOLO-deteksjonsrate", "scroll_clicks_lb": "Rulletaster", "crypt_profile_lb": "Profil:",
        "crypt_swing1_lb": "Swing 1 — Utforsk ↑↓:", "crypt_swing2_lb": "Swing 2 — Accel. ↑↓:",
        "crypt_speed_lb": "Klikkhastighet", "crypt_save_btn": "💾  Lagre innstillinger",
        "crypt_start": "START KRYPTJAKT", "crypt_stop_btn": "STOPP",
        "crypt_ready": "KLAR", "crypt_stopped": "Stoppet",
        "crypt_select_warn": "Velg minst én type!", "crypt_searching": "STATUS: SØKER...",
        "crypt_collected": "Samlet", "crypt_last": "siste",
        "cal_title": "Skjermkalibrering", "cal_desc": "Åpne spillet normalt, sett deretter to ankerpunkter.",
        "cal_pt_a_lb": "Punkt A — minikart", "cal_pt_a_desc": "Sett minikart-zoom\ntil minimum.\nKlikk senter.",
        "cal_pt_b_lb": "Punkt B — Sølv", "cal_pt_b_desc": "Hold over Sølv-ikon\ntil «+» vises.\nKlikk «+».",
        "cal_profile_lb": "Profil:", "cal_not_calibrated": "Ikke kalibrert",
        "cal_auto_btn": "AUTO KALIBRER", "cal_manual_btn": "KALIBRER",
        "cal_save_btn": "💾  Lagre", "cal_load_btn": "📂  Last",
        "cal_tune_title": "Klikk-tuning", "cal_tune_wt_icon": "Vakttårn", "cal_tune_carter": "Send Carter", "cal_tune_top_accel": "Accel. (Carter)", "cal_tune_march_accel": "Bruk akselerasjon", "cal_tune_reset": "Tilbakestill", "cal_tune_chest_sender": "Spillernavn (Kister)", "cal_tune_chest_type": "Kilde (Kister)", "cal_tune_chest_collect": "Åpne (Kister)",
        "ref_bal_title": "Referansesaldo", "ref_transfer_btn": "💸  Overfør til saldo  →",
        "ref_link_title": "Din referanselink:", "ref_code_prefix": "Kode: ", "ref_stats_title": "Referanser",
        "unit_sec": "s", "unit_min": "min", "unit_scan": "scan",
        "tr_event": "Handelsruter", "tr_active": "🟢 AKTIV — gjenstår:", "tr_ends_in": "🟢 AKTIV — slutter om:", "tr_starts_in": "starter om:",
        # --- roy tab ---
        "roy_title": "⬡  SVERM-SYSTEM", "roy_subtitle": "Del koordinater — motta andres",
        "roy_balance_title": "⏱ Tilgangssaldo", "roy_join": "Delta i Svermen",
        "roy_kingdom_label": "Kongerike №:", "roy_coords_title": "Koordinater fra medlemmer:",
        "roy_refresh": "↻  Oppdater pool", "roy_no_data": "Ingen data. Aktiver Sverm og start boten.",
        "roy_error": "Feil", "roy_empty_pool": "Ingen aktive koordinater.",
        "roy_pool_empty": "Pool tom", "roy_pool_count": "Coords i pool",
    },
    "PL": {
        "title": "Total Hunter", "tab_hunt": "GIEŁDY", "tab_combo": "Combo", "tab_ref": "POLECENIA",
        "get_trial": "ZDOBĄDŹ 300 PRÓB", "start": "ROZPOCZNIJ POLOWANIE", "stop": "ZATRZYMAJ",
        "no_credits": "0 diamentów! Połącz urządzenie na stronie.", "offline_stopped": "Zatrzymano: brak połączenia z serwerem", "login_btn": "POŁĄCZ URZĄDZENIE",
        "banned": "KONTO ZABLOKOWANE", "ref_title": "PROGRAM POLECIEŃ",
        "my_code": "TWÓJ KOD ZAPROSZENIA:", "friend_code": "KOD ZAPRASZAJĄCEGO (+50):",
        "activate_ref": "AKTYWUJ", "ref_used": "BONUS AKTYWNY ✅",
        "accuracy": "Dokładność wykrywania", "scan_rate": "Interwał skanowania", "sec": "sek.",
        "copy": "KOPIUJ", "share_text": "UDOSTĘPNIJ KOD I ZDOBĄDŹ %", "copied": "Skopiowano!",
        "clicker_title": "Clickermann Sync", "clicker_on": "WŁĄCZONO", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "GOTOWY", "status_running": "STATUS: SZUKAM...",
        "tab_crypt": "KRYPTY", "tab_cal": "Kalibracja", "tab_roy": "RÓJ", "tab_chest": "SKRZYNIE",
        # --- chest tab ---
        "chest_kingdom_lb": "Królestwo:", "chest_clan_lb": "Nazwa klanu:",
        "chest_start_btn": "START", "chest_stop_btn": "STOP",
        "chest_status_ready": "Gotowy do zbierania", "chest_status_running": "Zbieranie skrzyń...",
        "chest_status_stopped": "Zatrzymano", "chest_status_no_dialog": "Otwórz «Mój klan → Prezenty»",
        "chest_missing_fields": "Podaj Królestwo i Klan",
        "chest_send_btn": "WYŚLIJ NA SERWER", "chest_send_success": "Wysłano na serwer",
        "chest_send_failed": "Serwer niedostępny. Dane zapisane lokalnie.",
        "tab_ancient": "STARODAWNY", "ancient_status_running": "Zbieranie danych turniejowych...", "ancient_status_sent": "Wysłano na serwer", "ancient_status_failed": "Serwer niedostępny. Dane zapisane lokalnie.",
        "ancient_desc": "Otwórz okno «Statystyki» w grze przed uruchomieniem.",
        "chest_total_lb": "Łącznie otwarto:",
        "chest_speed_lb": "Szybkość kliknięcia:",
        "nn_title": "Sieć Neuronowa", "nav_main_title": "Nawigacja",
        "nav_extra_title": "Zaawansowane", "nav_auto": "Auto", "save_settings": "Zapisz ustawienia",
        "nav_step": "Krok:", "nav_wait": "Prędkość (sek/krok):",
        "nav_inland": "Głębokość (ekrany):", "nav_ocean": "Stosunek ocean/ląd (%):",
        "nav_waterpx": "Min. pow. wody (px):", "nav_diagblind": "Wsp. diag. powrotu:",
        "nav_footprint": "TTL śladu (sek.):", "nav_delta": "Delta powrotu (px):",
        "nav_pitch": "Płynność ruchu (%):",
        "crypt_icons_title": "Wybierz typy krypt:",
        "crypt_conf_lb": "Dokładność wykrywania", "crypt_accel_lb": "Przyspieszenie marszu (0–5)",
        "crypt_break_lb": "Przerwa między kryptami", "crypt_march_lb": "Dystans marszu Carter",
        "crypt_scroll_lb": "Częstotliwość YOLO", "scroll_clicks_lb": "Tiki przewijania", "crypt_profile_lb": "Profil:",
        "crypt_swing1_lb": "Swing 1 — Eksploruj ↑↓:", "crypt_swing2_lb": "Swing 2 — Przyspiesz ↑↓:",
        "crypt_speed_lb": "Prędkość klikania", "crypt_save_btn": "💾  Zapisz ustawienia",
        "crypt_start": "ROZPOCZNIJ POLOWANIE NA KRYPTY", "crypt_stop_btn": "ZATRZYMAJ",
        "crypt_ready": "GOTOWY", "crypt_stopped": "Zatrzymano",
        "crypt_select_warn": "Wybierz co najmniej jeden typ!", "crypt_searching": "STATUS: SZUKAM...",
        "crypt_collected": "Zebrano", "crypt_last": "ostatni",
        "cal_title": "Kalibracja ekranu", "cal_desc": "Otwórz grę normalnie, następnie ustaw dwa punkty zakotwiczenia.",
        "cal_pt_a_lb": "Punkt A — minimapa", "cal_pt_a_desc": "Zoom minimapy\ndo minimum.\nKliknij centrum.",
        "cal_pt_b_lb": "Punkt B — Srebro", "cal_pt_b_desc": "Najedź na ikonę Srebra\naż pojawi się «+».\nKliknij «+».",
        "cal_profile_lb": "Profil:", "cal_not_calibrated": "Nieskalibrowany",
        "cal_auto_btn": "AUTO KALIBRUJ", "cal_manual_btn": "KALIBRUJ",
        "cal_save_btn": "💾  Zapisz", "cal_load_btn": "📂  Wczytaj",
        "cal_tune_title": "Strojenie kliknięć", "cal_tune_wt_icon": "Wieża strażnicza", "cal_tune_carter": "Wyślij Cartera", "cal_tune_top_accel": "Przyspiesz (Carter)", "cal_tune_march_accel": "Użyj przyspieszenia", "cal_tune_reset": "Resetuj", "cal_tune_chest_sender": "Nazwa gracza (Skrzynie)", "cal_tune_chest_type": "Źródło (Skrzynie)", "cal_tune_chest_collect": "Otwórz (Skrzynie)",
        "ref_bal_title": "Saldo polecień", "ref_transfer_btn": "💸  Przenieś na saldo  →",
        "ref_link_title": "Twój link polecający:", "ref_code_prefix": "Kod: ", "ref_stats_title": "Polecenia",
        "unit_sec": "s", "unit_min": "min", "unit_scan": "skan",
        "tr_event": "Szlaki Handlowe", "tr_active": "🟢 TRWA — zostało:", "tr_ends_in": "🟢 TRWA — kończy się za:", "tr_starts_in": "zaczyna się za:",
        # --- roy tab ---
        "roy_title": "⬡  SYSTEM RÓJ", "roy_subtitle": "Udostępnij koordynaty — otrzymaj innych",
        "roy_balance_title": "⏱ Saldo dostępu", "roy_join": "Dołącz do Roju",
        "roy_kingdom_label": "Królestwo №:", "roy_coords_title": "Koordynaty od uczestników:",
        "roy_refresh": "↻  Odśwież pulę", "roy_no_data": "Brak danych. Włącz Rój i uruchom bota.",
        "roy_error": "Błąd", "roy_empty_pool": "Brak aktywnych koordynatów.",
        "roy_pool_empty": "Pula pusta", "roy_pool_count": "Koord. w puli",
    },
    "PT": {
        "title": "Total Hunter", "tab_hunt": "BOLSAS", "tab_combo": "Combo", "tab_ref": "INDICAÇÕES",
        "get_trial": "OBTER 300 TENTATIVAS", "start": "INICIAR CAÇA", "stop": "PARAR",
        "no_credits": "0 diamantes! Vincule seu dispositivo no site.", "offline_stopped": "Parado: sem conexão com o servidor", "login_btn": "VINCULAR DISPOSITIVO",
        "banned": "CONTA BANIDA", "ref_title": "PROGRAMA DE INDICAÇÃO",
        "my_code": "SEU CÓDIGO DE CONVITE:", "friend_code": "CÓDIGO DO CONVIDADOR (+50):",
        "activate_ref": "ATIVAR", "ref_used": "BÔNUS ATIVO ✅",
        "accuracy": "Precisão de detecção", "scan_rate": "Intervalo de varredura", "sec": "seg.",
        "copy": "COPIAR", "share_text": "COMPARTILHE O CÓDIGO E GANHE %", "copied": "Copiado!",
        "clicker_title": "Clickermann Sync", "clicker_on": "ATIVADO", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "PRONTO", "status_running": "STATUS: BUSCANDO...",
        "tab_crypt": "CRIPTAS", "tab_cal": "Calibração", "tab_roy": "ENXAME", "tab_chest": "BAÚS",
        # --- chest tab ---
        "chest_kingdom_lb": "Reino:", "chest_clan_lb": "Nome do clã:",
        "chest_start_btn": "INICIAR", "chest_stop_btn": "PARAR",
        "chest_status_ready": "Pronto para coletar", "chest_status_running": "Coletando baús...",
        "chest_status_stopped": "Parado", "chest_status_no_dialog": "Abra «Meu clã → Presentes»",
        "chest_missing_fields": "Informe Reino e Clã",
        "chest_send_btn": "ENVIAR AO SERVIDOR", "chest_send_success": "Enviado ao servidor",
        "chest_send_failed": "Servidor indisponível. Dados salvos localmente.",
        "tab_ancient": "ANCIÃO", "ancient_status_running": "Coletando dados do torneio...", "ancient_status_sent": "Enviado ao servidor", "ancient_status_failed": "Servidor indisponível. Dados salvos localmente.",
        "ancient_desc": "Abra a caixa de diálogo «Estatísticas» no jogo antes de iniciar.",
        "chest_total_lb": "Total aberto:",
        "chest_speed_lb": "Velocidade de clique:",
        "nn_title": "Rede Neural", "nav_main_title": "Navegação",
        "nav_extra_title": "Avançado", "nav_auto": "Auto", "save_settings": "Salvar configurações",
        "nav_step": "Passo:", "nav_wait": "Velocidade (seg/passo):",
        "nav_inland": "Prof. de mergulho (telas):", "nav_ocean": "Proporção oceano/terra (%):",
        "nav_waterpx": "Área mín. de água (px):", "nav_diagblind": "Coef. diag. retorno:",
        "nav_footprint": "TTL de rastro (seg.):", "nav_delta": "Delta de retorno (px):",
        "nav_pitch": "Fluidez de movimento (%):",
        "crypt_icons_title": "Selecionar tipos de cripta:",
        "crypt_conf_lb": "Precisão de detecção", "crypt_accel_lb": "Aceleração de marcha (0–5)",
        "crypt_break_lb": "Pausa entre criptas", "crypt_march_lb": "Distância de marcha Carter",
        "crypt_scroll_lb": "Taxa de detecção YOLO", "scroll_clicks_lb": "Ticks de rolagem", "crypt_profile_lb": "Perfil:",
        "crypt_swing1_lb": "Swing 1 — Explorar ↑↓:", "crypt_swing2_lb": "Swing 2 — Acelerar ↑↓:",
        "crypt_speed_lb": "Velocidade de clique", "crypt_save_btn": "💾  Salvar configurações",
        "crypt_start": "INICIAR CAÇA DE CRIPTAS", "crypt_stop_btn": "PARAR",
        "crypt_ready": "PRONTO", "crypt_stopped": "Parado",
        "crypt_select_warn": "Selecione pelo menos um tipo!", "crypt_searching": "STATUS: BUSCANDO...",
        "crypt_collected": "Coletado", "crypt_last": "último",
        "cal_title": "Calibração de tela", "cal_desc": "Abra o jogo normalmente, depois defina dois pontos de ancoragem.",
        "cal_pt_a_lb": "Ponto A — minimapa", "cal_pt_a_desc": "Zoom do minimapa\nao mínimo.\nClique no centro.",
        "cal_pt_b_lb": "Ponto B — Prata", "cal_pt_b_desc": "Passe sobre ícone Prata\naté aparecer «+».\nClique em «+».",
        "cal_profile_lb": "Perfil:", "cal_not_calibrated": "Não calibrado",
        "cal_auto_btn": "AUTO CALIBRAR", "cal_manual_btn": "CALIBRAR",
        "cal_save_btn": "💾  Salvar", "cal_load_btn": "📂  Carregar",
        "cal_tune_title": "Ajuste de cliques", "cal_tune_wt_icon": "Torre de vigia", "cal_tune_carter": "Enviar Carter", "cal_tune_top_accel": "Acelerar (Carter)", "cal_tune_march_accel": "Usar aceleração", "cal_tune_reset": "Redefinir", "cal_tune_chest_sender": "Nome do jogador (Baús)", "cal_tune_chest_type": "Fonte (Baús)", "cal_tune_chest_collect": "Abrir (Baús)",
        "ref_bal_title": "Saldo de indicações", "ref_transfer_btn": "💸  Transferir para saldo  →",
        "ref_link_title": "Seu link de indicação:", "ref_code_prefix": "Código: ", "ref_stats_title": "Indicações",
        "unit_sec": "s", "unit_min": "min", "unit_scan": "scan",
        "tr_event": "Rotas Comerciais", "tr_active": "🟢 ATIVO — restam:", "tr_ends_in": "🟢 ATIVO — termina em:", "tr_starts_in": "começa em:",
        # --- roy tab ---
        "roy_title": "⬡  SISTEMA ENXAME", "roy_subtitle": "Partilha coordenadas — recebe as dos outros",
        "roy_balance_title": "⏱ Saldo de acesso", "roy_join": "Participar no Enxame",
        "roy_kingdom_label": "Reino №:", "roy_coords_title": "Coordenadas dos membros:",
        "roy_refresh": "↻  Atualizar pool", "roy_no_data": "Sem dados. Ativa o Enxame e inicia o bot.",
        "roy_error": "Erro", "roy_empty_pool": "Sem coordenadas ativas.",
        "roy_pool_empty": "Pool vazio", "roy_pool_count": "Coords no pool",
    },
    "SV": {
        "title": "Total Hunter", "tab_hunt": "BÖRSER", "tab_combo": "Combo", "tab_ref": "HÄNVISNINGAR",
        "get_trial": "FÅ 300 FÖRSÖK", "start": "STARTA JAKT", "stop": "STOPP",
        "no_credits": "0 diamanter! Koppla enheten på webbplatsen.", "offline_stopped": "Stoppad: ingen anslutning till servern", "login_btn": "KOPPLA ENHET",
        "banned": "KONTO BLOCKERAT", "ref_title": "HÄNVISNINGSPROGRAM",
        "my_code": "DIN INBJUDNINGSKOD:", "friend_code": "INBJUDARES KOD (+50):",
        "activate_ref": "AKTIVERA", "ref_used": "BONUS AKTIV ✅",
        "accuracy": "Detektionsnoggrannhet", "scan_rate": "Skanningsintervall", "sec": "sek.",
        "copy": "KOPIERA", "share_text": "DELA KOD OCH TJÄNA %", "copied": "Kopierat!",
        "clicker_title": "Clickermann Sync", "clicker_on": "AKTIVERAD", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "REDO", "status_running": "STATUS: SÖKER...",
        "tab_crypt": "KRYPTOR", "tab_cal": "Kalibrering", "tab_roy": "SVÄRM", "tab_chest": "KISTOR",
        # --- chest tab ---
        "chest_kingdom_lb": "Kungarike:", "chest_clan_lb": "Klannamn:",
        "chest_start_btn": "START", "chest_stop_btn": "STOPP",
        "chest_status_ready": "Redo att samla", "chest_status_running": "Samlar kistor...",
        "chest_status_stopped": "Stoppad", "chest_status_no_dialog": "Öppna «Mitt klan → Gåvor»",
        "chest_missing_fields": "Ange kungarike och klan",
        "chest_send_btn": "SKICKA TILL SERVER", "chest_send_success": "Skickat till server",
        "chest_send_failed": "Servern är inte tillgänglig. Data sparad lokalt.",
        "tab_ancient": "FORNTIDA", "ancient_status_running": "Samlar turneringsdata...", "ancient_status_sent": "Skickat till server", "ancient_status_failed": "Servern är inte tillgänglig. Data sparad lokalt.",
        "ancient_desc": "Öppna dialogrutan «Statistik» i spelet innan du startar.",
        "chest_total_lb": "Totalt öppnade:",
        "chest_speed_lb": "Klickhastighet:",
        "nn_title": "Neuralt Nätverk", "nav_main_title": "Navigation",
        "nav_extra_title": "Avancerat", "nav_auto": "Auto", "save_settings": "Spara inställningar",
        "nav_step": "Steg:", "nav_wait": "Hastighet (sek/steg):",
        "nav_inland": "Dykdjup (skärmar):", "nav_ocean": "Hav/land-förhållande (%):",
        "nav_waterpx": "Min. vattenareal (px):", "nav_diagblind": "Återvändsdiag.-koeff.:",
        "nav_footprint": "Fotspår TTL (sek.):", "nav_delta": "Återvändsdelta (px):",
        "nav_pitch": "Rörelsesmidighet (%):",
        "crypt_icons_title": "Välj krypttyper:",
        "crypt_conf_lb": "Detektionsnoggrannhet", "crypt_accel_lb": "Marschaccel. (0–5)",
        "crypt_break_lb": "Paus mellan kryptor", "crypt_march_lb": "Carter marsjavstånd",
        "crypt_scroll_lb": "YOLO-detektionsfrekvens", "scroll_clicks_lb": "Bläddra ticks", "crypt_profile_lb": "Profil:",
        "crypt_swing1_lb": "Swing 1 — Utforska ↑↓:", "crypt_swing2_lb": "Swing 2 — Accel. ↑↓:",
        "crypt_speed_lb": "Klickhastighet", "crypt_save_btn": "💾  Spara inställningar",
        "crypt_start": "STARTA KRYPTJAKT", "crypt_stop_btn": "STOPP",
        "crypt_ready": "REDO", "crypt_stopped": "Stoppad",
        "crypt_select_warn": "Välj minst en typ!", "crypt_searching": "STATUS: SÖKER...",
        "crypt_collected": "Samlat", "crypt_last": "senaste",
        "cal_title": "Skärmkalibrering", "cal_desc": "Öppna spelet normalt, ställ sedan in två ankarpunkter.",
        "cal_pt_a_lb": "Punkt A — minikarta", "cal_pt_a_desc": "Minikarta-zoom\ntill minimum.\nKlicka mitten.",
        "cal_pt_b_lb": "Punkt B — Silver", "cal_pt_b_desc": "Hover över Silver-ikon\ntills «+» syns.\nKlicka «+».",
        "cal_profile_lb": "Profil:", "cal_not_calibrated": "Inte kalibrerad",
        "cal_auto_btn": "AUTO KALIBRERA", "cal_manual_btn": "KALIBRERA",
        "cal_save_btn": "💾  Spara", "cal_load_btn": "📂  Ladda",
        "cal_tune_title": "Klick-justering", "cal_tune_wt_icon": "Vakttorn", "cal_tune_carter": "Skicka Carter", "cal_tune_top_accel": "Accelerera (Carter)", "cal_tune_march_accel": "Använd acceleration", "cal_tune_reset": "Återställ", "cal_tune_chest_sender": "Spelarnamn (Kistor)", "cal_tune_chest_type": "Källa (Kistor)", "cal_tune_chest_collect": "Öppna (Kistor)",
        "ref_bal_title": "Hänvisningssaldo", "ref_transfer_btn": "💸  Överför till saldo  →",
        "ref_link_title": "Din hänvisningslänk:", "ref_code_prefix": "Kod: ", "ref_stats_title": "Hänvisningar",
        "unit_sec": "s", "unit_min": "min", "unit_scan": "scan",
        "tr_event": "Handelsrutter", "tr_active": "🟢 AKTIV — kvar:", "tr_ends_in": "🟢 AKTIV — slutar om:", "tr_starts_in": "börjar om:",
        # --- roy tab ---
        "roy_title": "⬡  SVÄRM-SYSTEM", "roy_subtitle": "Dela koordinater — få andras",
        "roy_balance_title": "⏱ Åtkomstsaldo", "roy_join": "Delta i Svärmen",
        "roy_kingdom_label": "Kungadöme №:", "roy_coords_title": "Koordinater från medlemmar:",
        "roy_refresh": "↻  Uppdatera pool", "roy_no_data": "Inga data. Aktivera Svärm och starta boten.",
        "roy_error": "Fel", "roy_empty_pool": "Inga aktiva koordinater.",
        "roy_pool_empty": "Pool tom", "roy_pool_count": "Koords i pool",
    },
    "TR": {
        "title": "Total Hunter", "tab_hunt": "BORSALAR", "tab_combo": "Combo", "tab_ref": "REFERANSLAR",
        "get_trial": "300 DENEME AL", "start": "AVI BAŞLAT", "stop": "DURDUR",
        "no_credits": "0 elmas! Cihazınızı sitede bağlayın.", "offline_stopped": "Durduruldu: sunucuyla bağlantı yok", "login_btn": "CİHAZI BAĞLA",
        "banned": "HESAP ENGELLENDİ", "ref_title": "REFERANS PROGRAMI",
        "my_code": "DAVET KODUNUZ:", "friend_code": "DAVET EDENİN KODU (+50):",
        "activate_ref": "ETKİNLEŞTİR", "ref_used": "BONUS AKTİF ✅",
        "accuracy": "Algılama hassasiyeti", "scan_rate": "Tarama aralığı", "sec": "sn.",
        "copy": "KOPYALA", "share_text": "KODU PAYLAŞ VE % KAZAN", "copied": "Kopyalandı!",
        "clicker_title": "Clickermann Sync", "clicker_on": "ETKİN", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "HAZIR", "status_running": "DURUM: ARIYOR...",
        "tab_crypt": "KRİPTALAR", "tab_cal": "Kalibrasyon", "tab_roy": "OĞUL", "tab_chest": "SANDIKLAR",
        # --- chest tab ---
        "chest_kingdom_lb": "Krallık:", "chest_clan_lb": "Klan adı:",
        "chest_start_btn": "BAŞLAT", "chest_stop_btn": "DURDUR",
        "chest_status_ready": "Toplamaya hazır", "chest_status_running": "Sandıklar toplanıyor...",
        "chest_status_stopped": "Durduruldu", "chest_status_no_dialog": "«Klanım → Hediyeler»'i açın",
        "chest_missing_fields": "Krallık ve Klan girin",
        "chest_send_btn": "SUNUCUYA GÖNDER", "chest_send_success": "Sunucuya gönderildi",
        "chest_send_failed": "Sunucuya erişilemiyor. Veriler yerel olarak kaydedildi.",
        "tab_ancient": "KADİM", "ancient_status_running": "Turnuva verileri toplanıyor...", "ancient_status_sent": "Sunucuya gönderildi", "ancient_status_failed": "Sunucuya erişilemiyor. Veriler yerel olarak kaydedildi.",
        "ancient_desc": "Başlamadan önce oyundaki «İstatistik» penceresini açın.",
        "chest_total_lb": "Toplam açılan:",
        "chest_speed_lb": "Tıklama hızı:",
        "nn_title": "Sinir Ağı", "nav_main_title": "Navigasyon",
        "nav_extra_title": "Gelişmiş", "nav_auto": "Otomatik", "save_settings": "Ayarları kaydet",
        "nav_step": "Adım:", "nav_wait": "Hız (sn/adım):",
        "nav_inland": "Dalış derinliği (ekran):", "nav_ocean": "Okyanus/kara oranı (%):",
        "nav_waterpx": "Min. su alanı (px):", "nav_diagblind": "Dönüş çapraz katsayısı:",
        "nav_footprint": "İz TTL (sn.):", "nav_delta": "Dönüş deltası (px):",
        "nav_pitch": "Hareket akıcılığı (%):",
        "crypt_icons_title": "Kripta türlerini seçin:",
        "crypt_conf_lb": "Algılama hassasiyeti", "crypt_accel_lb": "Yürüyüş ivmesi (0–5)",
        "crypt_break_lb": "Kriptalar arası mola", "crypt_march_lb": "Carter yürüyüş mesafesi",
        "crypt_scroll_lb": "YOLO algılama hızı", "scroll_clicks_lb": "Kaydırma adımları", "crypt_profile_lb": "Profil:",
        "crypt_swing1_lb": "Swing 1 — Keşfet ↑↓:", "crypt_swing2_lb": "Swing 2 — Hızlan ↑↓:",
        "crypt_speed_lb": "Tıklama hızı", "crypt_save_btn": "💾  Ayarları kaydet",
        "crypt_start": "KRİPTA AVINI BAŞLAT", "crypt_stop_btn": "DURDUR",
        "crypt_ready": "HAZIR", "crypt_stopped": "Durduruldu",
        "crypt_select_warn": "En az bir tür seçin!", "crypt_searching": "DURUM: ARIYOR...",
        "crypt_collected": "Toplandı", "crypt_last": "son",
        "cal_title": "Ekran kalibrasyonu", "cal_desc": "Oyunu normal açın, ardından iki çapa noktası belirleyin.",
        "cal_pt_a_lb": "Nokta A — mini harita", "cal_pt_a_desc": "Mini harita zoom'u\nminimuma alın.\nMerkeze tıklayın.",
        "cal_pt_b_lb": "Nokta B — Gümüş", "cal_pt_b_desc": "Gümüş simgesinin üzerine\ngelin «+» görene dek.\n«+» üzerine tıklayın.",
        "cal_profile_lb": "Profil:", "cal_not_calibrated": "Kalibre edilmedi",
        "cal_auto_btn": "OTOMATİK KALİBRE", "cal_manual_btn": "KALİBRE ET",
        "cal_save_btn": "💾  Kaydet", "cal_load_btn": "📂  Yükle",
        "cal_tune_title": "Tıklama ayarı", "cal_tune_wt_icon": "Gözetleme kulesi", "cal_tune_carter": "Carter gönder", "cal_tune_top_accel": "Hızlan (Carter)", "cal_tune_march_accel": "İvmelenmeyi kullan", "cal_tune_reset": "Sıfırla", "cal_tune_chest_sender": "Oyuncu adı (Sandıklar)", "cal_tune_chest_type": "Kaynak (Sandıklar)", "cal_tune_chest_collect": "Aç (Sandıklar)",
        "ref_bal_title": "Referans bakiyesi", "ref_transfer_btn": "💸  Bakiyeye aktar  →",
        "ref_link_title": "Referans linkiniz:", "ref_code_prefix": "Kod: ", "ref_stats_title": "Referanslar",
        "unit_sec": "s", "unit_min": "dk", "unit_scan": "scan",
        "tr_event": "Ticaret Yolları", "tr_active": "🟢 AKTİF — kaldı:", "tr_ends_in": "🟢 AKTİF — bitiş:", "tr_starts_in": "başlıyor:",
        # --- roy tab ---
        "roy_title": "⬡  OĞUL SİSTEMİ", "roy_subtitle": "Koordinatları paylaş — diğerlerinkini al",
        "roy_balance_title": "⏱ Erişim Bakiyesi", "roy_join": "Oğula Katıl",
        "roy_kingdom_label": "Krallık №:", "roy_coords_title": "Üyelerden koordinatlar:",
        "roy_refresh": "↻  Havuzu yenile", "roy_no_data": "Veri yok. Oğulu etkinleştir ve botu başlat.",
        "roy_error": "Hata", "roy_empty_pool": "Aktif koordinat yok.",
        "roy_pool_empty": "Havuz boş", "roy_pool_count": "Havuzdaki koord.",
    },
    "AR": {
        "title": "Total Hunter", "tab_hunt": "البورصات", "tab_combo": "Combo", "tab_ref": "الإحالات",
        "get_trial": "احصل على 300 محاولة", "start": "ابدأ الصيد", "stop": "إيقاف",
        "no_credits": "0 ألماس! اربط جهازك على الموقع.", "offline_stopped": "تم الإيقاف: لا يوجد اتصال بالخادم", "login_btn": "ربط الجهاز",
        "banned": "الحساب محظور", "ref_title": "برنامج الإحالة",
        "my_code": "رمز دعوتك:", "friend_code": "رمز المدعو (+50):",
        "activate_ref": "تفعيل", "ref_used": "المكافأة نشطة ✅",
        "accuracy": "دقة الكشف", "scan_rate": "فترة المسح", "sec": "ث.",
        "copy": "نسخ", "share_text": "شارك الرمز واكسب %", "copied": "تم النسخ!",
        "clicker_title": "Clickermann Sync", "clicker_on": "مفعّل", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "جاهز", "status_running": "الحالة: يبحث...",
        "tab_crypt": "المقابر", "tab_cal": "معايرة", "tab_roy": "سرب", "tab_chest": "الصناديق",
        # --- chest tab ---
        "chest_kingdom_lb": "المملكة:", "chest_clan_lb": "اسم العشيرة:",
        "chest_start_btn": "بدء", "chest_stop_btn": "إيقاف",
        "chest_status_ready": "جاهز للجمع", "chest_status_running": "جمع الصناديق...",
        "chest_status_stopped": "متوقف", "chest_status_no_dialog": "افتح «عشيرتي → الهدايا»",
        "chest_missing_fields": "أدخل المملكة والعشيرة",
        "chest_send_btn": "إرسال إلى الخادم", "chest_send_success": "تم الإرسال إلى الخادم",
        "chest_send_failed": "الخادم غير متاح. تم حفظ البيانات محليًا.",
        "tab_ancient": "القديم", "ancient_status_running": "جمع بيانات البطولة...", "ancient_status_sent": "تم الإرسال إلى الخادم", "ancient_status_failed": "الخادم غير متاح. تم حفظ البيانات محليًا.",
        "ancient_desc": "افتح نافذة «الإحصائيات» في اللعبة قبل البدء.",
        "chest_total_lb": "الإجمالي المفتوح:",
        "chest_speed_lb": "سرعة النقر:",
        "nn_title": "الشبكة العصبية", "nav_main_title": "التنقل",
        "nav_extra_title": "متقدم", "nav_auto": "تلقائي", "save_settings": "حفظ الإعدادات",
        "nav_step": "خطوة:", "nav_wait": "السرعة (ث/خطوة):",
        "nav_inland": "عمق الغطس (شاشات):", "nav_ocean": "نسبة محيط/أرض (%):",
        "nav_waterpx": "أدنى مساحة ماء (px):", "nav_diagblind": "معامل قطري العودة:",
        "nav_footprint": "TTL الأثر (ث.):", "nav_delta": "دلتا العودة (px):",
        "nav_pitch": "سلاسة الحركة (%):",
        "crypt_icons_title": "اختر أنواع المقابر:",
        "crypt_conf_lb": "دقة الكشف", "crypt_accel_lb": "تسارع المسير (0–5)",
        "crypt_break_lb": "استراحة بين المقابر", "crypt_march_lb": "مسافة مسير كارتر",
        "crypt_scroll_lb": "معدل كشف YOLO", "scroll_clicks_lb": "نقرات التمرير", "crypt_profile_lb": "الملف الشخصي:",
        "crypt_swing1_lb": "Swing 1 — استكشاف ↑↓:", "crypt_swing2_lb": "Swing 2 — تسريع ↑↓:",
        "crypt_speed_lb": "سرعة النقر", "crypt_save_btn": "💾  حفظ الإعدادات",
        "crypt_start": "ابدأ صيد المقابر", "crypt_stop_btn": "إيقاف",
        "crypt_ready": "جاهز", "crypt_stopped": "متوقف",
        "crypt_select_warn": "اختر نوعاً واحداً على الأقل!", "crypt_searching": "الحالة: يبحث...",
        "crypt_collected": "تم جمعه", "crypt_last": "الأخير",
        "cal_title": "معايرة الشاشة", "cal_desc": "افتح اللعبة ثم حدد نقطتي إرساء.",
        "cal_pt_a_lb": "النقطة A — الخريطة الصغيرة", "cal_pt_a_desc": "اضبط تكبير\nالخريطة للحد الأدنى.\nانقر في المركز.",
        "cal_pt_b_lb": "النقطة B — الفضة", "cal_pt_b_desc": "مرر على أيقونة الفضة\nحتى «+» يظهر.\nانقر على «+».",
        "cal_profile_lb": "الملف:", "cal_not_calibrated": "غير معاير",
        "cal_auto_btn": "معايرة تلقائية", "cal_manual_btn": "معايرة",
        "cal_save_btn": "💾  حفظ", "cal_load_btn": "📂  تحميل",
        "cal_tune_title": "ضبط النقرات", "cal_tune_wt_icon": "برج المراقبة", "cal_tune_carter": "إرسال كارتر", "cal_tune_top_accel": "تسريع (كارتر)", "cal_tune_march_accel": "استخدام التسريع", "cal_tune_reset": "إعادة تعيين", "cal_tune_chest_sender": "اسم اللاعب (الصناديق)", "cal_tune_chest_type": "المصدر (الصناديق)", "cal_tune_chest_collect": "فتح (الصناديق)",
        "ref_bal_title": "رصيد الإحالات", "ref_transfer_btn": "💸  تحويل إلى الرصيد  →",
        "ref_link_title": "رابط إحالتك:", "ref_code_prefix": "الرمز: ", "ref_stats_title": "الإحالات",
        "unit_sec": "ث", "unit_min": "د", "unit_scan": "مسح",
        "tr_event": "طرق التجارة", "tr_active": "🟢 نشط — متبقي:", "tr_ends_in": "🟢 نشط — ينتهي خلال:", "tr_starts_in": "يبدأ خلال:",
        # --- roy tab ---
        "roy_title": "⬡  نظام السرب", "roy_subtitle": "شارك الإحداثيات — احصل على إحداثيات الآخرين",
        "roy_balance_title": "⏱ رصيد الوصول", "roy_join": "انضم إلى السرب",
        "roy_kingdom_label": "المملكة №:", "roy_coords_title": "إحداثيات الأعضاء:",
        "roy_refresh": "↻  تحديث المجمع", "roy_no_data": "لا بيانات. فعّل السرب وشغّل البوت.",
        "roy_error": "خطأ", "roy_empty_pool": "لا إحداثيات نشطة.",
        "roy_pool_empty": "المجمع فارغ", "roy_pool_count": "إحداثيات في المجمع",
    },
    "JA": {
        "title": "Total Hunter", "tab_hunt": "取引所", "tab_combo": "Combo", "tab_ref": "紹介",
        "get_trial": "300回分を取得", "start": "ハントを開始", "stop": "停止",
        "no_credits": "ダイヤ0個！サイトでデバイスを登録してください。", "offline_stopped": "停止しました：サーバーとの接続がありません", "login_btn": "デバイスを登録",
        "banned": "アカウントBANされました", "ref_title": "紹介プログラム",
        "my_code": "招待コード:", "friend_code": "招待者コード (+50):",
        "activate_ref": "有効化", "ref_used": "ボーナス有効 ✅",
        "accuracy": "検出精度", "scan_rate": "スキャン間隔", "sec": "秒",
        "copy": "コピー", "share_text": "コードを共有して%を獲得", "copied": "コピーしました！",
        "clicker_title": "Clickermann Sync", "clicker_on": "有効", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "準備完了", "status_running": "ステータス: 検索中...",
        "tab_crypt": "クリプト", "tab_cal": "キャリブレーション", "tab_roy": "群れ", "tab_chest": "宝箱",
        # --- chest tab ---
        "chest_kingdom_lb": "王国:", "chest_clan_lb": "クラン名:",
        "chest_start_btn": "開始", "chest_stop_btn": "停止",
        "chest_status_ready": "収集準備完了", "chest_status_running": "宝箱を収集中...",
        "chest_status_stopped": "停止しました", "chest_status_no_dialog": "「マイクラン → ギフト」を開いてください",
        "chest_missing_fields": "王国とクランを入力してください",
        "chest_send_btn": "サーバーに送信", "chest_send_success": "サーバーに送信しました",
        "chest_send_failed": "サーバーに接続できません。データはローカルに保存されました。",
        "tab_ancient": "古代の者", "ancient_status_running": "トーナメントデータを収集中...", "ancient_status_sent": "サーバーに送信しました", "ancient_status_failed": "サーバーに接続できません。データはローカルに保存されました。",
        "ancient_desc": "開始する前にゲーム内の「統計」ダイアログを開いてください。",
        "chest_total_lb": "開封総数:",
        "chest_speed_lb": "クリック速度:",
        "nn_title": "ニューラルネット", "nav_main_title": "ナビゲーション",
        "nav_extra_title": "詳細設定", "nav_auto": "自動", "save_settings": "設定を保存",
        "nav_step": "ステップ:", "nav_wait": "速度 (秒/ステップ):",
        "nav_inland": "潜水深度 (画面):", "nav_ocean": "海/陸比率 (%):",
        "nav_waterpx": "最小水域 (px):", "nav_diagblind": "帰還対角係数:",
        "nav_footprint": "足跡TTL (秒):", "nav_delta": "帰還デルタ (px):",
        "nav_pitch": "動きの滑らかさ (%):",
        "crypt_icons_title": "クリプトタイプを選択:",
        "crypt_conf_lb": "検出精度", "crypt_accel_lb": "進軍加速 (0–5)",
        "crypt_break_lb": "クリプト間の休憩", "crypt_march_lb": "カーター進軍距離",
        "crypt_scroll_lb": "YOLO検出レート", "scroll_clicks_lb": "スクロールティック", "crypt_profile_lb": "プロファイル:",
        "crypt_swing1_lb": "Swing 1 — 探索 ↑↓:", "crypt_swing2_lb": "Swing 2 — 加速 ↑↓:",
        "crypt_speed_lb": "クリック速度", "crypt_save_btn": "💾  設定を保存",
        "crypt_start": "クリプトハントを開始", "crypt_stop_btn": "停止",
        "crypt_ready": "準備完了", "crypt_stopped": "停止しました",
        "crypt_select_warn": "最低1つのタイプを選択！", "crypt_searching": "ステータス: 検索中...",
        "crypt_collected": "収集済", "crypt_last": "最後",
        "cal_title": "画面キャリブレーション", "cal_desc": "ゲームを開き、2つのアンカーポイントを設定します。",
        "cal_pt_a_lb": "ポイントA — ミニマップ", "cal_pt_a_desc": "ミニマップのズームを\n最小に設定。\n中央をクリック。",
        "cal_pt_b_lb": "ポイントB — シルバー", "cal_pt_b_desc": "シルバーアイコンを\n«+»が現れるまでホバー。\n«+»をクリック。",
        "cal_profile_lb": "プロファイル:", "cal_not_calibrated": "未キャリブレーション",
        "cal_auto_btn": "自動キャリブレーション", "cal_manual_btn": "キャリブレーション",
        "cal_save_btn": "💾  保存", "cal_load_btn": "📂  読込",
        "cal_tune_title": "クリック調整", "cal_tune_wt_icon": "見張り塔", "cal_tune_carter": "カーター派遣", "cal_tune_top_accel": "加速 (カーター)", "cal_tune_march_accel": "加速使用", "cal_tune_reset": "リセット", "cal_tune_chest_sender": "プレイヤー名（チェスト）", "cal_tune_chest_type": "ソース（チェスト）", "cal_tune_chest_collect": "開く（チェスト）",
        "ref_bal_title": "紹介残高", "ref_transfer_btn": "💸  残高に転送  →",
        "ref_link_title": "あなたの紹介リンク:", "ref_code_prefix": "コード: ", "ref_stats_title": "紹介",
        "unit_sec": "秒", "unit_min": "分", "unit_scan": "スキャン",
        "tr_event": "交易路", "tr_active": "🟢 開催中 — 残り:", "tr_ends_in": "🟢 開催中 — 終了まで:", "tr_starts_in": "開始まで:",
        # --- roy tab ---
        "roy_title": "⬡  群れシステム", "roy_subtitle": "座標を共有 — 他のメンバーの座標を受け取る",
        "roy_balance_title": "⏱ アクセス残高", "roy_join": "群れに参加",
        "roy_kingdom_label": "王国 №:", "roy_coords_title": "メンバーからの座標:",
        "roy_refresh": "↻  プール更新", "roy_no_data": "データなし。群れを有効にしてボットを起動。",
        "roy_error": "エラー", "roy_empty_pool": "アクティブな座標なし。",
        "roy_pool_empty": "プール空", "roy_pool_count": "プール内座標数",
    },
    "ZH": {
        "title": "Total Hunter", "tab_hunt": "交易所", "tab_combo": "Combo", "tab_ref": "推荐",
        "get_trial": "获取300次试用", "start": "开始狩猎", "stop": "停止",
        "no_credits": "0钻石！请在网站上绑定设备。", "offline_stopped": "已停止：与服务器失去连接", "login_btn": "绑定设备",
        "banned": "账户已封禁", "ref_title": "推荐计划",
        "my_code": "您的邀请码:", "friend_code": "邀请人代码 (+50):",
        "activate_ref": "激活", "ref_used": "奖励已激活 ✅",
        "accuracy": "检测精度", "scan_rate": "扫描间隔", "sec": "秒",
        "copy": "复制", "share_text": "分享代码获得%", "copied": "已复制！",
        "clicker_title": "Clickermann Sync", "clicker_on": "已启用", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "准备就绪", "status_running": "状态: 搜索中...",
        "tab_crypt": "地下墓穴", "tab_cal": "校准", "tab_roy": "蜂群", "tab_chest": "宝箱",
        # --- chest tab ---
        "chest_kingdom_lb": "王国:", "chest_clan_lb": "公会名称:",
        "chest_start_btn": "开始", "chest_stop_btn": "停止",
        "chest_status_ready": "准备收集", "chest_status_running": "正在收集宝箱...",
        "chest_status_stopped": "已停止", "chest_status_no_dialog": "请打开「我的公会 → 礼物」",
        "chest_missing_fields": "请输入王国和公会名称",
        "chest_send_btn": "发送到服务器", "chest_send_success": "已发送到服务器",
        "chest_send_failed": "服务器不可用，数据已保存到本地。",
        "tab_ancient": "古代生物", "ancient_status_running": "正在收集锦标赛数据...", "ancient_status_sent": "已发送到服务器", "ancient_status_failed": "服务器不可用，数据已保存到本地。",
        "ancient_desc": "开始前请打开游戏内的「统计」对话框。",
        "chest_total_lb": "已开启总数:",
        "chest_speed_lb": "点击速度:",
        "nn_title": "神经网络", "nav_main_title": "导航",
        "nav_extra_title": "高级设置", "nav_auto": "自动", "save_settings": "保存设置",
        "nav_step": "步长:", "nav_wait": "速度 (秒/步):",
        "nav_inland": "下潜深度 (屏幕):", "nav_ocean": "海洋/陆地比 (%):",
        "nav_waterpx": "最小水域 (px):", "nav_diagblind": "返回对角系数:",
        "nav_footprint": "足迹TTL (秒):", "nav_delta": "返回增量 (px):",
        "nav_pitch": "运动流畅度 (%):",
        "crypt_icons_title": "选择地下墓穴类型:",
        "crypt_conf_lb": "检测精度", "crypt_accel_lb": "行军加速 (0–5)",
        "crypt_break_lb": "墓穴间休息", "crypt_march_lb": "卡特行军距离",
        "crypt_scroll_lb": "YOLO检测率", "scroll_clicks_lb": "滚动点击数", "crypt_profile_lb": "配置文件:",
        "crypt_swing1_lb": "Swing 1 — 探索 ↑↓:", "crypt_swing2_lb": "Swing 2 — 加速 ↑↓:",
        "crypt_speed_lb": "点击速度", "crypt_save_btn": "💾  保存设置",
        "crypt_start": "开始墓穴狩猎", "crypt_stop_btn": "停止",
        "crypt_ready": "准备就绪", "crypt_stopped": "已停止",
        "crypt_select_warn": "请至少选择一种类型！", "crypt_searching": "状态: 搜索中...",
        "crypt_collected": "已收集", "crypt_last": "最后",
        "cal_title": "屏幕校准", "cal_desc": "正常打开游戏，然后设置两个锚点。",
        "cal_pt_a_lb": "点A — 小地图", "cal_pt_a_desc": "将小地图缩放\n调至最小。\n点击中心。",
        "cal_pt_b_lb": "点B — 白银", "cal_pt_b_desc": "悬停在白银图标\n直到«+»出现。\n点击«+»。",
        "cal_profile_lb": "配置文件:", "cal_not_calibrated": "未校准",
        "cal_auto_btn": "自动校准", "cal_manual_btn": "校准",
        "cal_save_btn": "💾  保存", "cal_load_btn": "📂  加载",
        "cal_tune_title": "点击调整", "cal_tune_wt_icon": "瞭望塔", "cal_tune_carter": "派遣卡特", "cal_tune_top_accel": "加速 (卡特)", "cal_tune_march_accel": "使用加速", "cal_tune_reset": "重置", "cal_tune_chest_sender": "玩家名称（宝箱）", "cal_tune_chest_type": "来源（宝箱）", "cal_tune_chest_collect": "打开（宝箱）",
        "ref_bal_title": "推荐余额", "ref_transfer_btn": "💸  转入余额  →",
        "ref_link_title": "您的推荐链接:", "ref_code_prefix": "代码: ", "ref_stats_title": "推荐",
        "unit_sec": "秒", "unit_min": "分", "unit_scan": "扫描",
        "tr_event": "贸易路线", "tr_active": "🟢 进行中 — 剩余:", "tr_ends_in": "🟢 进行中 — 结束于:", "tr_starts_in": "开始于:",
        # --- roy tab ---
        "roy_title": "⬡  蜂群系统", "roy_subtitle": "分享交易所坐标 — 获取他人的坐标",
        "roy_balance_title": "⏱ 访问余额", "roy_join": "加入蜂群",
        "roy_kingdom_label": "王国 №:", "roy_coords_title": "成员坐标:",
        "roy_refresh": "↻  刷新池", "roy_no_data": "无数据。启用蜂群并启动机器人。",
        "roy_error": "错误", "roy_empty_pool": "没有活跃坐标。",
        "roy_pool_empty": "池为空", "roy_pool_count": "池中坐标数",
    },
    "ZH_TW": {
        "title": "Total Hunter", "tab_hunt": "交易所", "tab_combo": "Combo", "tab_ref": "推薦",
        "get_trial": "獲取300次試用", "start": "開始狩獵", "stop": "停止",
        "no_credits": "0鑽石！請在網站上綁定裝置。", "offline_stopped": "已停止：與伺服器失去連線", "login_btn": "綁定裝置",
        "banned": "帳戶已封禁", "ref_title": "推薦計畫",
        "my_code": "您的邀請碼:", "friend_code": "邀請人代碼 (+50):",
        "activate_ref": "啟動", "ref_used": "獎勵已啟動 ✅",
        "accuracy": "偵測精度", "scan_rate": "掃描間隔", "sec": "秒",
        "copy": "複製", "share_text": "分享代碼獲得%", "copied": "已複製！",
        "clicker_title": "Clickermann Sync", "clicker_on": "已啟用", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "準備就緒", "status_running": "狀態: 搜尋中...",
        "tab_crypt": "地下墓穴", "tab_cal": "校準", "tab_roy": "蜂群", "tab_chest": "寶箱",
        # --- chest tab ---
        "chest_kingdom_lb": "王國:", "chest_clan_lb": "公會名稱:",
        "chest_start_btn": "開始", "chest_stop_btn": "停止",
        "chest_status_ready": "準備收集", "chest_status_running": "正在收集寶箱...",
        "chest_status_stopped": "已停止", "chest_status_no_dialog": "請打開「我的公會 → 禮物」",
        "chest_missing_fields": "請輸入王國和公會名稱",
        "chest_send_btn": "發送到伺服器", "chest_send_success": "已發送到伺服器",
        "chest_send_failed": "伺服器無法連線，資料已儲存在本機。",
        "tab_ancient": "古代生物", "ancient_status_running": "正在收集錦標賽資料...", "ancient_status_sent": "已發送到伺服器", "ancient_status_failed": "伺服器無法連線，資料已儲存在本機。",
        "ancient_desc": "開始前請打開遊戲內的「統計」對話框。",
        "chest_total_lb": "已開啟總數:",
        "chest_speed_lb": "點擊速度:",
        "nn_title": "神經網路", "nav_main_title": "導航",
        "nav_extra_title": "進階設定", "nav_auto": "自動", "save_settings": "儲存設定",
        "nav_step": "步長:", "nav_wait": "速度 (秒/步):",
        "nav_inland": "下潛深度 (畫面):", "nav_ocean": "海洋/陸地比 (%):",
        "nav_waterpx": "最小水域 (px):", "nav_diagblind": "返回對角係數:",
        "nav_footprint": "足跡TTL (秒):", "nav_delta": "返回增量 (px):",
        "nav_pitch": "運動流暢度 (%):",
        "crypt_icons_title": "選擇地下墓穴類型:",
        "crypt_conf_lb": "偵測精度", "crypt_accel_lb": "行軍加速 (0–5)",
        "crypt_break_lb": "墓穴間休息", "crypt_march_lb": "卡特行軍距離",
        "crypt_scroll_lb": "YOLO偵測率", "scroll_clicks_lb": "捲動點擊數", "crypt_profile_lb": "設定檔:",
        "crypt_swing1_lb": "Swing 1 — 探索 ↑↓:", "crypt_swing2_lb": "Swing 2 — 加速 ↑↓:",
        "crypt_speed_lb": "點擊速度", "crypt_save_btn": "💾  儲存設定",
        "crypt_start": "開始墓穴狩獵", "crypt_stop_btn": "停止",
        "crypt_ready": "準備就緒", "crypt_stopped": "已停止",
        "crypt_select_warn": "請至少選擇一種類型！", "crypt_searching": "狀態: 搜尋中...",
        "crypt_collected": "已收集", "crypt_last": "最後",
        "cal_title": "螢幕校準", "cal_desc": "正常開啟遊戲，然後設定兩個錨點。",
        "cal_pt_a_lb": "點A — 小地圖", "cal_pt_a_desc": "將小地圖縮放\n調至最小。\n點擊中心。",
        "cal_pt_b_lb": "點B — 白銀", "cal_pt_b_desc": "將滑鼠懸停在白銀圖示\n直到«+»出現。\n點擊«+»。",
        "cal_profile_lb": "設定檔:", "cal_not_calibrated": "未校準",
        "cal_auto_btn": "自動校準", "cal_manual_btn": "校準",
        "cal_save_btn": "💾  儲存", "cal_load_btn": "📂  載入",
        "cal_tune_title": "點擊調整", "cal_tune_wt_icon": "瞭望塔", "cal_tune_carter": "派遣卡特", "cal_tune_top_accel": "加速 (卡特)", "cal_tune_march_accel": "使用加速", "cal_tune_reset": "重置", "cal_tune_chest_sender": "玩家名稱（寶箱）", "cal_tune_chest_type": "來源（寶箱）", "cal_tune_chest_collect": "打開（寶箱）",
        "ref_bal_title": "推薦餘額", "ref_transfer_btn": "💸  轉入餘額  →",
        "ref_link_title": "您的推薦連結:", "ref_code_prefix": "代碼: ", "ref_stats_title": "推薦",
        "unit_sec": "秒", "unit_min": "分", "unit_scan": "掃描",
        "tr_event": "貿易路線", "tr_active": "🟢 進行中 — 剩餘:", "tr_ends_in": "🟢 進行中 — 結束於:", "tr_starts_in": "開始於:",
        # --- roy tab ---
        "roy_title": "⬡  蜂群系統", "roy_subtitle": "分享交易所座標 — 獲取他人的座標",
        "roy_balance_title": "⏱ 訪問餘額", "roy_join": "加入蜂群",
        "roy_kingdom_label": "王國 №:", "roy_coords_title": "成員座標:",
        "roy_refresh": "↻  刷新池", "roy_no_data": "無數據。啟用蜂群並啟動機器人。",
        "roy_error": "錯誤", "roy_empty_pool": "沒有活躍座標。",
        "roy_pool_empty": "池為空", "roy_pool_count": "池中座標數",
    },
    "KO": {
        "title": "Total Hunter", "tab_hunt": "거래소", "tab_combo": "Combo", "tab_ref": "추천",
        "get_trial": "300회 체험 받기", "start": "사냥 시작", "stop": "정지",
        "no_credits": "다이아 0개! 웹사이트에서 기기를 연결하세요.", "offline_stopped": "정지됨: 서버와 연결 없음", "login_btn": "기기 연결",
        "banned": "계정 차단됨", "ref_title": "추천 프로그램",
        "my_code": "초대 코드:", "friend_code": "초대자 코드 (+50):",
        "activate_ref": "활성화", "ref_used": "보너스 활성화 ✅",
        "accuracy": "감지 정확도", "scan_rate": "스캔 간격", "sec": "초",
        "copy": "복사", "share_text": "코드 공유하여 % 획득", "copied": "복사됨!",
        "clicker_title": "Clickermann Sync", "clicker_on": "활성화됨", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "준비 완료", "status_running": "상태: 검색 중...",
        "tab_crypt": "크립트", "tab_cal": "보정", "tab_roy": "군집", "tab_chest": "보물상자",
        # --- chest tab ---
        "chest_kingdom_lb": "왕국:", "chest_clan_lb": "클랜 이름:",
        "chest_start_btn": "시작", "chest_stop_btn": "정지",
        "chest_status_ready": "수집 준비 완료", "chest_status_running": "상자 수집 중...",
        "chest_status_stopped": "정지됨", "chest_status_no_dialog": "«내 클랜 → 선물»을 여세요",
        "chest_missing_fields": "왕국과 클랜을 입력하세요",
        "chest_send_btn": "서버로 전송", "chest_send_success": "서버로 전송됨",
        "chest_send_failed": "서버에 연결할 수 없습니다. 데이터는 로컬에 저장되었습니다.",
        "tab_ancient": "고대의 존재", "ancient_status_running": "토너먼트 데이터 수집 중...", "ancient_status_sent": "서버로 전송됨", "ancient_status_failed": "서버에 연결할 수 없습니다. 데이터는 로컬에 저장되었습니다.",
        "ancient_desc": "시작하기 전에 게임 내 「통계」 대화상자를 여세요.",
        "chest_total_lb": "총 개봉:",
        "chest_speed_lb": "클릭 속도:",
        "nn_title": "신경망", "nav_main_title": "네비게이션",
        "nav_extra_title": "고급 설정", "nav_auto": "자동", "save_settings": "설정 저장",
        "nav_step": "단계:", "nav_wait": "속도 (초/단계):",
        "nav_inland": "잠수 깊이 (화면):", "nav_ocean": "해양/육지 비율 (%):",
        "nav_waterpx": "최소 수역 (px):", "nav_diagblind": "귀환 대각 계수:",
        "nav_footprint": "발자국 TTL (초):", "nav_delta": "귀환 델타 (px):",
        "nav_pitch": "움직임 부드러움 (%):",
        "crypt_icons_title": "크립트 유형 선택:",
        "crypt_conf_lb": "감지 정확도", "crypt_accel_lb": "행군 가속 (0–5)",
        "crypt_break_lb": "크립트 사이 휴식", "crypt_march_lb": "카터 행군 거리",
        "crypt_scroll_lb": "YOLO 감지 속도", "scroll_clicks_lb": "스크롤 틱", "crypt_profile_lb": "프로파일:",
        "crypt_swing1_lb": "Swing 1 — 탐색 ↑↓:", "crypt_swing2_lb": "Swing 2 — 가속 ↑↓:",
        "crypt_speed_lb": "클릭 속도", "crypt_save_btn": "💾  설정 저장",
        "crypt_start": "크립트 사냥 시작", "crypt_stop_btn": "정지",
        "crypt_ready": "준비 완료", "crypt_stopped": "정지됨",
        "crypt_select_warn": "최소 한 가지 유형 선택!", "crypt_searching": "상태: 검색 중...",
        "crypt_collected": "수집됨", "crypt_last": "마지막",
        "cal_title": "화면 보정", "cal_desc": "게임을 정상적으로 열고 두 개의 앵커 포인트를 설정합니다.",
        "cal_pt_a_lb": "포인트 A — 미니맵", "cal_pt_a_desc": "미니맵 줌을\n최소로 설정.\n중앙 클릭.",
        "cal_pt_b_lb": "포인트 B — 실버", "cal_pt_b_desc": "실버 아이콘에\n«+»가 나타날 때까지 호버.\n«+» 클릭.",
        "cal_profile_lb": "프로파일:", "cal_not_calibrated": "보정 안 됨",
        "cal_auto_btn": "자동 보정", "cal_manual_btn": "보정",
        "cal_save_btn": "💾  저장", "cal_load_btn": "📂  불러오기",
        "cal_tune_title": "클릭 조정", "cal_tune_wt_icon": "감시탑", "cal_tune_carter": "카터 파견", "cal_tune_top_accel": "가속 (카터)", "cal_tune_march_accel": "가속 사용", "cal_tune_reset": "초기화", "cal_tune_chest_sender": "플레이어 이름(상자)", "cal_tune_chest_type": "출처(상자)", "cal_tune_chest_collect": "열기(상자)",
        "ref_bal_title": "추천 잔액", "ref_transfer_btn": "💸  잔액으로 이전  →",
        "ref_link_title": "추천 링크:", "ref_code_prefix": "코드: ", "ref_stats_title": "추천",
        "unit_sec": "초", "unit_min": "분", "unit_scan": "스캔",
        "tr_event": "교역로", "tr_active": "🟢 진행중 — 남은:", "tr_ends_in": "🟢 진행중 — 종료까지:", "tr_starts_in": "시작까지:",
        # --- roy tab ---
        "roy_title": "⬡  군집 시스템", "roy_subtitle": "교역소 좌표 공유 — 다른 멤버의 좌표 받기",
        "roy_balance_title": "⏱ 접속 잔액", "roy_join": "군집 참가",
        "roy_kingdom_label": "왕국 №:", "roy_coords_title": "멤버 좌표:",
        "roy_refresh": "↻  풀 새로고침", "roy_no_data": "데이터 없음. 군집을 활성화하고 봇을 실행하세요.",
        "roy_error": "오류", "roy_empty_pool": "활성 좌표 없음.",
        "roy_pool_empty": "풀 비어 있음", "roy_pool_count": "풀 내 좌표 수",
    },
    "UK": {
        "title": "Total Hunter", "tab_hunt": "БІРЖІ", "tab_combo": "Combo", "tab_ref": "РЕФЕРАЛИ",
        "get_trial": "ОТРИМАТИ 300 СПРОБ", "start": "ЗАПУСТИТИ ПОЛЮВАННЯ", "stop": "ЗУПИНИТИ",
        "no_credits": "У вас 0 алмазів! Прив'яжіть пристрій на сайті.", "offline_stopped": "Зупинено: немає зв'язку із сервером", "login_btn": "ПРИВ'ЯЗАТИ ПРИСТРІЙ",
        "banned": "ВАШ АКАУНТ ЗАБЛОКОВАНО", "ref_title": "ПАРТНЕРСЬКА ПРОГРАМА",
        "my_code": "ВАШ КОД ЗАПРОШЕННЯ:", "friend_code": "КОД ЗАПРОШУВАЧА (+50):",
        "activate_ref": "АКТИВУВАТИ", "ref_used": "БОНУС АКТИВОВАНО ✅",
        "accuracy": "Точність пошуку", "scan_rate": "Частота сканування", "sec": "сек.",
        "copy": "КОПІЮВАТИ", "share_text": "ПОДІЛІТЬСЯ КОДОМ І ОТРИМАЙТЕ %", "copied": "Скопійовано!",
        "clicker_title": "Синхронізація Clickermann", "clicker_on": "УВІМКНУТИ", "key_start": "Старт:", "key_stop": "Стоп:",
        "status_ready": "СИСТЕМА ГОТОВА", "status_running": "СТАТУС: У ПОШУКУ...",
        "tab_crypt": "СКЛЕПИ", "tab_cal": "Калібрування", "tab_roy": "РОЙ", "tab_chest": "СКРИНІ",
        # --- chest tab ---
        "chest_kingdom_lb": "Королівство:", "chest_clan_lb": "Назва клану:",
        "chest_start_btn": "СТАРТ", "chest_stop_btn": "СТОП",
        "chest_status_ready": "Готовий до збору", "chest_status_running": "Збір скринь...",
        "chest_status_stopped": "Зупинено", "chest_status_no_dialog": "Відкрийте «Мій клан → Подарунки»",
        "chest_missing_fields": "Вкажіть Королівство і Клан",
        "chest_send_btn": "ВІДПРАВИТИ НА СЕРВЕР", "chest_send_success": "Відправлено на сервер",
        "chest_send_failed": "Сервер недоступний. Дані збережено локально.",
        "tab_ancient": "ДАВНІЙ", "ancient_status_running": "Збір турнірної таблиці...", "ancient_status_sent": "Відправлено на сервер", "ancient_status_failed": "Сервер недоступний. Дані збережено локально.",
        "ancient_desc": "Відкрийте діалог «Статистика» в грі перед запуском.",
        "chest_total_lb": "Всього відкрито:",
        "chest_speed_lb": "Швидкість кліку:",
        "nn_title": "Нейромережа", "nav_main_title": "Навігація",
        "nav_extra_title": "Додатково", "nav_auto": "Авто", "save_settings": "Зберегти налаштування",
        "nav_step": "Крок:", "nav_wait": "Швидкість (сек/крок):",
        "nav_inland": "Глибина пірнання (екранів):", "nav_ocean": "Межа океан/суша (%):",
        "nav_waterpx": "Мін. розмір водойми:", "nav_diagblind": "Коеф. діагоналі повернення:",
        "nav_footprint": "Пам'ять слідів (сек):", "nav_delta": "Дельта повернення (px):",
        "nav_pitch": "Жвавість ходу (%):",
        "crypt_icons_title": "Виберіть типи склепів:",
        "crypt_conf_lb": "Точність пошуку", "crypt_accel_lb": "Прискорення маршу (0–5)",
        "crypt_break_lb": "Перерва між склепами", "crypt_march_lb": "Дальність маршу Картера",
        "crypt_scroll_lb": "Частота YOLO-детекції", "scroll_clicks_lb": "Тіки прокрутки", "crypt_profile_lb": "Профіль:",
        "crypt_swing1_lb": "Swing 1 — Дослідити ↑↓:", "crypt_swing2_lb": "Swing 2 — Прискорення ↑↓:",
        "crypt_speed_lb": "Швидкість кліків", "crypt_save_btn": "💾  Зберегти налаштування",
        "crypt_start": "ЗАПУСТИТИ ЗБІР СКЛЕПІВ", "crypt_stop_btn": "ЗУПИНИТИ",
        "crypt_ready": "ГОТОВО", "crypt_stopped": "Зупинено",
        "crypt_select_warn": "Виберіть хоча б один тип!", "crypt_searching": "СТАТУС: У ПОШУКУ...",
        "crypt_collected": "Зібрано", "crypt_last": "останній",
        "cal_title": "Калібрування екрана", "cal_desc": "Відкрийте гру у звичному режимі, потім встановіть дві точки.",
        "cal_pt_a_lb": "Точка A — міні-карта", "cal_pt_a_desc": "Зменшіть зум\nміні-карти до мін.\nКлікніть по центру.",
        "cal_pt_b_lb": "Точка B — Срібло", "cal_pt_b_desc": "Наведіть на іконку\nСрібла до появи «+».\nКлікніть по «+».",
        "cal_profile_lb": "Профіль:", "cal_not_calibrated": "Не відкалібровано",
        "cal_auto_btn": "АВТОКАЛІБРУВАТИ", "cal_manual_btn": "КАЛІБРУВАТИ",
        "cal_save_btn": "💾  Зберегти", "cal_load_btn": "📂  Завантажити",
        "cal_tune_title": "Тюнінг кліків", "cal_tune_wt_icon": "Дозорна вежа", "cal_tune_carter": "Відправка Картера", "cal_tune_top_accel": "Прискорити (Картер)", "cal_tune_march_accel": "Використати прискорення", "cal_tune_reset": "Скинути", "cal_tune_chest_sender": "Ім'я гравця (скрині)", "cal_tune_chest_type": "Джерело (скрині)", "cal_tune_chest_collect": "Відкрити (скрині)",
        "ref_bal_title": "Реферальний баланс", "ref_transfer_btn": "💸  Перевести на баланс  →",
        "ref_link_title": "Ваше реферальне посилання:", "ref_code_prefix": "Код: ", "ref_stats_title": "Реферали",
        "unit_sec": "с", "unit_min": "хв", "unit_scan": "скан",
        "tr_event": "Торгові Шляхи", "tr_active": "🟢 ЙДЕ — залишилось", "tr_ends_in": "🟢 ЙДЕ — до кінця:", "tr_starts_in": "до початку:",
        # --- roy tab ---
        "roy_title": "⬡  СИСТЕМА РОЙ", "roy_subtitle": "Ділись координатами — отримуй координати інших",
        "roy_balance_title": "⏱ Баланс доступу", "roy_join": "Приєднатись до Рою",
        "roy_kingdom_label": "Королівство №:", "roy_coords_title": "Координати учасників:",
        "roy_refresh": "↻  Оновити пул", "roy_no_data": "Немає даних. Увімкни Рій і запусти бота.",
        "roy_error": "Помилка", "roy_empty_pool": "Немає активних координат.",
        "roy_pool_empty": "Пул порожній", "roy_pool_count": "Координат у пулі",
    },
    "ID": {
        "title": "Total Hunter", "tab_hunt": "BURSA", "tab_combo": "Combo", "tab_ref": "REFERRAL",
        "get_trial": "DAPATKAN 300 PERCOBAAN", "start": "MULAI PERBURUAN", "stop": "BERHENTI",
        "no_credits": "0 berlian! Hubungkan perangkat di situs web.", "offline_stopped": "Berhenti: tidak ada koneksi ke server", "login_btn": "HUBUNGKAN PERANGKAT",
        "banned": "AKUN DIBLOKIR", "ref_title": "PROGRAM REFERRAL",
        "my_code": "KODE UNDANGAN ANDA:", "friend_code": "KODE PENGUNDANG (+50):",
        "activate_ref": "AKTIFKAN", "ref_used": "BONUS AKTIF ✅",
        "accuracy": "Akurasi deteksi", "scan_rate": "Interval pemindaian", "sec": "dtk.",
        "copy": "SALIN", "share_text": "BAGIKAN KODE DAN DAPATKAN %", "copied": "Disalin!",
        "clicker_title": "Clickermann Sync", "clicker_on": "DIAKTIFKAN", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "SIAP", "status_running": "STATUS: MENCARI...",
        "tab_crypt": "KRIPTA", "tab_cal": "Kalibrasi", "tab_roy": "KAWANAN", "tab_chest": "PETI",
        # --- chest tab ---
        "chest_kingdom_lb": "Kerajaan:", "chest_clan_lb": "Nama klan:",
        "chest_start_btn": "MULAI", "chest_stop_btn": "BERHENTI",
        "chest_status_ready": "Siap mengumpulkan", "chest_status_running": "Mengumpulkan peti...",
        "chest_status_stopped": "Dihentikan", "chest_status_no_dialog": "Buka «Klan Saya → Hadiah»",
        "chest_missing_fields": "Masukkan Kerajaan dan Klan",
        "chest_send_btn": "KIRIM KE SERVER", "chest_send_success": "Terkirim ke server",
        "chest_send_failed": "Server tidak tersedia. Data disimpan secara lokal.",
        "tab_ancient": "KUNO", "ancient_status_running": "Mengumpulkan data turnamen...", "ancient_status_sent": "Terkirim ke server", "ancient_status_failed": "Server tidak tersedia. Data disimpan secara lokal.",
        "ancient_desc": "Buka dialog «Statistik» dalam game sebelum memulai.",
        "chest_total_lb": "Total dibuka:",
        "chest_speed_lb": "Kecepatan klik:",
        "nn_title": "Jaringan Saraf", "nav_main_title": "Navigasi",
        "nav_extra_title": "Lanjutan", "nav_auto": "Otomatis", "save_settings": "Simpan pengaturan",
        "nav_step": "Langkah:", "nav_wait": "Kecepatan (dtk/langkah):",
        "nav_inland": "Kedalaman selam (layar):", "nav_ocean": "Rasio laut/darat (%):",
        "nav_waterpx": "Luas air min. (px):", "nav_diagblind": "Koef. diagonal kembali:",
        "nav_footprint": "TTL jejak (dtk.):", "nav_delta": "Delta kembali (px):",
        "nav_pitch": "Kelancaran gerakan (%):",
        "crypt_icons_title": "Pilih jenis kripta:",
        "crypt_conf_lb": "Akurasi deteksi", "crypt_accel_lb": "Percepatan mars (0–5)",
        "crypt_break_lb": "Jeda antar kripta", "crypt_march_lb": "Jarak mars Carter",
        "crypt_scroll_lb": "Laju deteksi YOLO", "scroll_clicks_lb": "Tik gulir", "crypt_profile_lb": "Profil:",
        "crypt_swing1_lb": "Swing 1 — Jelajahi ↑↓:", "crypt_swing2_lb": "Swing 2 — Percepat ↑↓:",
        "crypt_speed_lb": "Kecepatan klik", "crypt_save_btn": "💾  Simpan pengaturan",
        "crypt_start": "MULAI PERBURUAN KRIPTA", "crypt_stop_btn": "BERHENTI",
        "crypt_ready": "SIAP", "crypt_stopped": "Berhenti",
        "crypt_select_warn": "Pilih setidaknya satu jenis!", "crypt_searching": "STATUS: MENCARI...",
        "crypt_collected": "Dikumpulkan", "crypt_last": "terakhir",
        "cal_title": "Kalibrasi layar", "cal_desc": "Buka game secara normal, lalu tetapkan dua titik jangkar.",
        "cal_pt_a_lb": "Titik A — peta mini", "cal_pt_a_desc": "Atur zoom peta mini\nke minimum.\nKlik tengah.",
        "cal_pt_b_lb": "Titik B — Perak", "cal_pt_b_desc": "Arahkan ke ikon Perak\nhingga «+» muncul.\nKlik «+».",
        "cal_profile_lb": "Profil:", "cal_not_calibrated": "Belum dikalibrasi",
        "cal_auto_btn": "KALIBRASI OTOMATIS", "cal_manual_btn": "KALIBRASI",
        "cal_save_btn": "💾  Simpan", "cal_load_btn": "📂  Muat",
        "cal_tune_title": "Penyetelan klik", "cal_tune_wt_icon": "Menara pengawas", "cal_tune_carter": "Kirim Carter", "cal_tune_top_accel": "Percepat (Carter)", "cal_tune_march_accel": "Gunakan percepatan", "cal_tune_reset": "Reset", "cal_tune_chest_sender": "Nama pemain (Peti)", "cal_tune_chest_type": "Sumber (Peti)", "cal_tune_chest_collect": "Buka (Peti)",
        "ref_bal_title": "Saldo referral", "ref_transfer_btn": "💸  Transfer ke saldo  →",
        "ref_link_title": "Tautan referral Anda:", "ref_code_prefix": "Kode: ", "ref_stats_title": "Referral",
        "unit_sec": "d", "unit_min": "mnt", "unit_scan": "scan",
        "tr_event": "Jalur Perdagangan", "tr_active": "🟢 AKTIF — sisa:", "tr_ends_in": "🟢 AKTIF — berakhir dalam:", "tr_starts_in": "dimulai dalam:",
        # --- roy tab ---
        "roy_title": "⬡  SISTEM KAWANAN", "roy_subtitle": "Bagikan koordinat bursa — terima koordinat anggota lain",
        "roy_balance_title": "⏱ Saldo akses", "roy_join": "Bergabung ke Kawanan",
        "roy_kingdom_label": "Kerajaan №:", "roy_coords_title": "Koordinat anggota:",
        "roy_refresh": "↻  Perbarui pool", "roy_no_data": "Tidak ada data. Aktifkan Kawanan dan jalankan bot.",
        "roy_error": "Kesalahan", "roy_empty_pool": "Tidak ada koordinat aktif.",
        "roy_pool_empty": "Pool kosong", "roy_pool_count": "Koordinat dalam pool",
    },
}

LANG_LABELS = {
    "EN": "🇬🇧 EN", "UK": "🇺🇦 UA", "RU": "🇷🇺 RU",
    "DE": "🇩🇪 DE", "ES": "🇪🇸 ES", "FR": "🇫🇷 FR",
    "IT": "🇮🇹 IT", "NL": "🇳🇱 NL", "NO": "🇳🇴 NO",
    "PL": "🇵🇱 PL", "PT": "🇧🇷 PT", "SV": "🇸🇪 SV",
    "TR": "🇹🇷 TR", "AR": "🇸🇦 AR", "JA": "🇯🇵 JA",
    "ZH": "🇨🇳 ZH", "ZH_TW": "🇹🇼 TW", "KO": "🇰🇷 KO",
    "ID": "🇮🇩 ID",
}
LANG_BY_LABEL = {v: k for k, v in LANG_LABELS.items()}

# ── PIL-drawn flag images ──────────────────────────────────────────────────

def _hx(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4)) + (255,)

_FLAG_SPECS = {
    "RU":    ("h3",     ["#FFFFFF","#0039A6","#D52B1E"]),
    "EN":    ("cross",  "#012169","#C8102E","#FFFFFF"),
    "UK":    ("h2",     ["#005BBB","#FFD500"]),
    "DE":    ("h3",     ["#000000","#DD0000","#FFCE00"]),
    "ES":    ("h3",     ["#C60B1E","#FFC400","#C60B1E"]),
    "FR":    ("v3",     ["#002395","#FFFFFF","#ED2939"]),
    "IT":    ("v3",     ["#009246","#FFFFFF","#CE2B37"]),
    "NL":    ("h3",     ["#AE1C28","#FFFFFF","#21468B"]),
    "NO":    ("ncross", "#EF2B2D","#003680","#FFFFFF"),
    "PL":    ("h2",     ["#FFFFFF","#DC143C"]),
    "PT":    ("v2",     ["#006600","#FF0000"]),
    "SV":    ("ncross", "#006AA7","#FECC02","#006AA7"),
    "TR":    ("cresc",  "#E30A17","#FFFFFF"),
    "AR":    ("solid",  "#006C35"),
    "JA":    ("dot",    "#FFFFFF","#BC002D"),
    "ZH":    ("solid",  "#DE2910"),
    "ZH_TW": ("h2",    ["#000095","#FE0000"]),
    "KO":    ("dot",    "#FFFFFF","#003478"),
    "ID":    ("h2",     ["#CE1126","#FFFFFF"]),
}

def _draw_flag(code):
    from PIL import Image as _Im, ImageDraw as _Dr
    W, H = 28, 18
    img = _Im.new("RGBA", (W, H), (60, 60, 60, 255))
    d = _Dr.Draw(img)
    s = _FLAG_SPECS.get(code)
    if not s:
        return img
    t = s[0]
    if t == "h2":
        c1, c2 = s[1]
        d.rectangle([0, 0, W, H // 2], fill=_hx(c1))
        d.rectangle([0, H // 2, W, H], fill=_hx(c2))
    elif t == "h3":
        c1, c2, c3 = s[1]
        h = H // 3
        d.rectangle([0, 0, W, h],     fill=_hx(c1))
        d.rectangle([0, h, W, h * 2], fill=_hx(c2))
        d.rectangle([0, h * 2, W, H], fill=_hx(c3))
    elif t == "v2":
        c1, c2 = s[1]
        w = W // 3
        d.rectangle([0, 0, w, H],     fill=_hx(c1))
        d.rectangle([w, 0, W, H],     fill=_hx(c2))
    elif t == "v3":
        c1, c2, c3 = s[1]
        w = W // 3
        d.rectangle([0, 0, w, H],         fill=_hx(c1))
        d.rectangle([w, 0, w * 2, H],     fill=_hx(c2))
        d.rectangle([w * 2, 0, W, H],     fill=_hx(c3))
    elif t == "ncross":          # Nordic cross (SV, NO)
        bg, arm, _ = s[1], s[2], s[3]
        d.rectangle([0, 0, W, H],                fill=_hx(bg))
        cx = W // 3
        d.rectangle([cx - 2, 0, cx + 2, H],     fill=_hx(arm))
        d.rectangle([0, H // 2 - 2, W, H // 2 + 2], fill=_hx(arm))
    elif t == "cross":           # Union Jack simplified
        bg, fc, mc = s[1], s[2], s[3]
        d.rectangle([0, 0, W, H],                    fill=_hx(bg))
        d.rectangle([0, H // 2 - 3, W, H // 2 + 3], fill=_hx(mc))
        d.rectangle([W // 2 - 3, 0, W // 2 + 3, H], fill=_hx(mc))
        d.rectangle([0, H // 2 - 1, W, H // 2 + 1], fill=_hx(fc))
        d.rectangle([W // 2 - 1, 0, W // 2 + 1, H], fill=_hx(fc))
    elif t == "solid":
        d.rectangle([0, 0, W, H], fill=_hx(s[1]))
    elif t == "crescent":        # Turkey: red + white crescent hint
        d.rectangle([0, 0, W, H], fill=_hx(s[1]))
        r = H // 3
        cx, cy = W // 3, H // 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r],         fill=_hx(s[2]))
        d.ellipse([cx - r + 4, cy - r, cx + r + 4, cy + r], fill=_hx(s[1]))
    elif t == "dot":             # Japan / Korea: bg + center circle
        d.rectangle([0, 0, W, H], fill=_hx(s[1]))
        r = H // 3
        d.ellipse([W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r], fill=_hx(s[2]))
    return img


_FLAG_CTK: dict = {}

def _lang_flags():
    if not _FLAG_CTK:
        for code in LANG_LABELS:
            pil_img = _draw_flag(code)
            _FLAG_CTK[code] = ctk.CTkImage(
                light_image=pil_img, dark_image=pil_img, size=(28, 18))
    return _FLAG_CTK


_LANG_SHORT = {"ZH_TW": "TW", "UK": "UA"}


class LangPopupButton(ctk.CTkFrame):
    """Language selector button that opens a flag-grid popup."""

    def __init__(self, master, values, command, width=110, fg_color="#0F1528", **kw):
        super().__init__(master, width=width, height=32,
                         fg_color=fg_color, corner_radius=8)
        self._values  = values
        self._cmd     = command
        self._current = values[0] if values else ""
        self._popup   = None
        self._fgc     = fg_color
        self._btn = ctk.CTkButton(
            self, text="", image=None, compound="left",
            width=width, height=30,
            fg_color=fg_color, hover_color="#1B3A82",
            corner_radius=6, anchor="w",
            command=self._toggle,
        )
        self._btn.pack(fill="both", expand=True)
        self._refresh()
        # bind_all запрещён в CTk — биндим к корневому окну после размещения
        self.after(200, self._bind_root)

    def _code(self, label):
        return LANG_BY_LABEL.get(label, label)

    def _short(self, code):
        return _LANG_SHORT.get(code, code)

    def _refresh(self):
        code  = self._code(self._current)
        flags = _lang_flags()
        self._btn.configure(image=flags.get(code),
                            text=f"  {self._short(code)}")

    def set(self, label):
        self._current = label
        self._refresh()

    def _toggle(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
        else:
            self._open()

    def _open(self):
        p = ctk.CTkToplevel(self)
        p.overrideredirect(True)
        p.attributes("-topmost", True)
        # Позиционируем: правый край попапа = правый край кнопки, открывается вниз
        POPUP_W = 150
        ITEM_H  = 32
        VISIBLE = min(12, len(self._values))  # не больше 12 строк без скролла
        POPUP_H = VISIBLE * ITEM_H + 8
        btn_right = self.winfo_rootx() + self.winfo_width()
        x = btn_right - POPUP_W
        y = self.winfo_rooty() + self.winfo_height() + 2
        p.geometry(f"{POPUP_W}x{POPUP_H}+{x}+{y}")
        p.configure(fg_color="#0A0F1E")
        f = ctk.CTkScrollableFrame(p, width=POPUP_W - 4,
                                    fg_color="#0A0F1E", corner_radius=6)
        f.pack(fill="both", expand=True, padx=2, pady=2)
        flags = _lang_flags()
        for lbl in self._values:
            code = self._code(lbl)
            sel  = (lbl == self._current)
            ctk.CTkButton(
                f,
                text=f"  {self._short(code)}",
                image=flags.get(code),
                compound="left",
                width=POPUP_W - 12, height=ITEM_H - 4,
                fg_color="#1B3A82" if sel else "#0F1528",
                hover_color="#2A4A9E",
                corner_radius=4, anchor="w",
                command=lambda lb=lbl, pp=p: self._pick(lb, pp),
            ).pack(fill="x", padx=2, pady=1)
        self._popup = p

    def _pick(self, label, popup):
        self._current = label
        self._refresh()
        try:
            popup.destroy()
        except Exception:
            pass
        self._popup = None
        if self._cmd:
            self._cmd(label)

    def _bind_root(self):
        try:
            self.winfo_toplevel().bind("<Button-1>", self._outside_click, add="+")
        except Exception:
            pass

    def _outside_click(self, ev):
        if not (self._popup and self._popup.winfo_exists()):
            return
        try:
            px, py = self._popup.winfo_rootx(), self._popup.winfo_rooty()
            pw, ph = self._popup.winfo_width(), self._popup.winfo_height()
            bx, by = self._btn.winfo_rootx(), self._btn.winfo_rooty()
            bw, bh = self._btn.winfo_width(), self._btn.winfo_height()
            in_p = px <= ev.x_root <= px + pw and py <= ev.y_root <= py + ph
            in_b = bx <= ev.x_root <= bx + bw and by <= ev.y_root <= by + bh
            if not in_p and not in_b:
                self._popup.destroy()
                self._popup = None
        except Exception:
            pass


class TotalHunterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._roy_self_reported: set = set()  # координаты только что найденные нами — не звучать в ROY
        self.engine = HuntEngine()
        self.engine.on_found_callback = self.on_target_found
        self.engine.on_last_exchange_callback = self._on_last_exchange_found
        self.engine.on_engine_restart_callback = self._on_exchange_restart
        self.engine.on_pool_refresh_callback   = self._on_pool_auto_refresh
        self.engine.on_exchange_found_callback = self._on_exchange_found
        self.crypt_engine = CryptHunter()
        self.is_crypt_running = False
        self._crypt_found_count = 0
        # self.combo_engine = CombinerEngine()  # Combo временно отключён
        self.is_combo_running = False
        self._chest_running = False
        self._chest_stop_event = threading.Event()
        saved_lang = {}
        if os.path.exists(GUI_CONFIG_PATH):
            try:
                import json as _j
                with open(GUI_CONFIG_PATH) as _f:
                    saved_lang = _j.load(_f)
            except Exception:
                pass
        self.current_lang = saved_lang.get("lang", "EN")
        self.user_email = None
        self.current_credits = 0
        self.my_ref_id = "---"
        self.is_running = False # ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННОЙ СОСТОЯНИЯ
        self._esc_stopped = False      # True после ESC — блокирует авто-перезапуск
        self._auto_restart_id = None   # ID таймера after(10000) — отменяется по ESC
        self._i18n_labels = []  # (widget, lang_key)
       
        self.title(f"Total Hunter v{VERSION}")
        # Динамический размер и позиция: высота = рабочая область экрана, прижато вправо
        try:
            import ctypes, ctypes.wintypes
            _rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(_rect), 0)
            _work_x = _rect.left
            _work_h = _rect.bottom - _rect.top - 35
            _snap_x = _rect.right - 460 - 10
        except Exception:
            _work_x = 0
            _work_h = self.winfo_screenheight() - 90
            _snap_x = self.winfo_screenwidth() - 460 - 10
        self.geometry(f"460x{_work_h}+{_snap_x}+{_work_x}")
        self.resizable(False, True)
        self.minsize(460, 400)
        self.configure(fg_color=MD3["bg"])

        self._outer = ctk.CTkScrollableFrame(
            self, fg_color=MD3["bg"], corner_radius=0,
            scrollbar_button_color=MD3["outline"],
            scrollbar_button_hover_color=MD3["primary"],
        )
        self._outer.pack(fill="both", expand=True)

        # Шапка: «Поверх окон» слева, выбор языка справа
        _header = ctk.CTkFrame(self._outer, fg_color="transparent")
        _header.pack(fill="x", padx=20, pady=(10, 4))
        self.always_on_top_var = ctk.BooleanVar(value=True)
        ctk.CTkLabel(_header, text="On top:", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MD3["on_surface"]).pack(side="left")
        ctk.CTkSwitch(_header, text="", variable=self.always_on_top_var,
                      onvalue=True, offvalue=False, command=self._on_always_on_top,
                      width=46,
                      button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
                      progress_color=MD3["primary"]).pack(side="left", padx=(4, 0))
        self.lang_menu = LangPopupButton(
            _header,
            values=list(LANG_LABELS.values()),
            command=self.change_lang,
            width=110,
            fg_color=MD3["elevated"],
        )
        self.lang_menu.set(LANG_LABELS.get(self.current_lang, "🇬🇧 EN"))
        self.lang_menu.pack(side="right")
        # Theme selector
        self.theme_restart_label = ctk.CTkLabel(_header, text="",
                                                font=ctk.CTkFont(size=10),
                                                text_color=MD3["error_text"])
        self.theme_restart_label.pack(side="right", padx=(0, 4))
        self.theme_var = ctk.StringVar(value=MD3_NAME)
        self.theme_menu = ctk.CTkOptionMenu(
            _header,
            values=list(THEMES.keys()),
            variable=self.theme_var,
            width=90, height=24,
            fg_color=MD3["elevated"],
            button_color=MD3["primary"],
            button_hover_color=MD3["primary_dim"],
            text_color=MD3["on_surface"],
            command=self._on_theme_change,
        )
        self.theme_menu.pack(side="right", padx=(0, 4))
        ctk.CTkButton(
            _header, text="+5", width=36, height=24,
            fg_color="#1A5C2A", hover_color="#226B33",
            text_color="#4ADE80", corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: webbrowser.open("https://total-hunter.com/dashboard/earn"),
        ).pack(side="right", padx=(0, 2))


        # Заголовок и HWID
        self.label_title = ctk.CTkLabel(self._outer, text=LANGS[self.current_lang]["title"],
                                        font=ctk.CTkFont(size=22, weight="bold"),
                                        text_color=MD3["on_surface"])
        self.label_title.pack(pady=(0, 5))
        self.label_hwid = ctk.CTkLabel(self._outer, text=f"HWID: {get_hwid()}",
                                       font=ctk.CTkFont(size=10),
                                       text_color=MD3["outline"])
        self.label_hwid.pack()
        self.label_email = ctk.CTkLabel(self._outer, text="",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        text_color=MD3["primary"])
        self.label_email.pack()

        # ── Глобальный инфо-баннер (логин / объявления) ──────────────────
        self.info_banner = ctk.CTkFrame(self._outer, fg_color=MD3["elevated"],
                                        corner_radius=10)
        self.info_banner.pack(fill="x", padx=20, pady=(4, 0))

        # Кнопка пробных 300 кредитов — видна, пока не использована (не требует
        # логина, только HWID); стоит ПЕРЕД кнопкой логина — новый юзер должен
        # сначала попробовать бота, а не сразу упираться в требование логина.
        self.trial_button = ctk.CTkButton(self.info_banner,
                                          text=LANGS[self.current_lang]["get_trial"],
                                          fg_color="#1A5C2A", hover_color="#226B33",
                                          text_color=MD3["on_surface"],
                                          height=40, corner_radius=8,
                                          command=self.claim_trial_action)
        self.trial_button.pack(pady=(6, 0), padx=10, fill="x")

        # Кнопка Google Входа — видна пока не авторизован
        self.login_button = ctk.CTkButton(self.info_banner,
                                          text=LANGS[self.current_lang]["login_btn"],
                                          fg_color="#C62828", hover_color="#B71C1C",
                                          text_color=MD3["on_surface"],
                                          height=40, corner_radius=8,
                                          command=self.handle_login)
        self.login_button.pack(pady=6, padx=10, fill="x")

        # Объявления (broadcast) — видны после авторизации
        self.broadcast_frame = ctk.CTkFrame(self.info_banner, fg_color="transparent",
                                            corner_radius=0)
        self.broadcast_label = ctk.CTkLabel(self.broadcast_frame, text="",
                                            font=ctk.CTkFont(size=13),
                                            text_color="#00CFFF", wraplength=380)

        # ── Навигация: два ряда (grid) ───────────────────────────────────
        self._nav_frame = ctk.CTkFrame(self._outer, fg_color=MD3["elevated"], corner_radius=12)
        self._nav_frame.pack(padx=20, pady=(10, 0), fill="x")
        self._nav_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Ряд 0 — СКЛЕПЫ, БИРЖИ, РОЙ, РЕФЕРАЛЫ
        self._tab_init_names = {k: LANGS[self.current_lang][k]
                                for k in ("tab_crypt", "tab_hunt", "tab_roy", "tab_ref")}
        self._main_seg = ctk.CTkSegmentedButton(
            self._nav_frame,
            values=list(self._tab_init_names.values()),
            command=self._on_seg_change,
            height=32,
            fg_color=MD3["elevated"],
            selected_color=MD3["tab_selected"],
            selected_hover_color=MD3["tab_selected_hover"],
            unselected_color=MD3["elevated"],
            unselected_hover_color=MD3["card"],
            text_color=MD3["on_surface"],
            corner_radius=6,
            font=ctk.CTkFont(size=13),
        )
        self._main_seg.grid(row=0, column=0, columnspan=4, sticky="ew", padx=4, pady=(4, 0))
        self._main_seg.set(self._tab_init_names["tab_crypt"])

        # Ряд 1 — СУНДУКИ, ДРЕВНИЙ, КАЛИБРОВКА
        self._tab2_init_names = {k: LANGS[self.current_lang][k]
                                 for k in ("tab_chest", "tab_ancient", "tab_cal")}
        self._main_seg2 = ctk.CTkSegmentedButton(
            self._nav_frame,
            values=list(self._tab2_init_names.values()),
            command=self._on_seg2_change,
            height=28,
            fg_color=MD3["elevated"],
            selected_color=MD3["tab_selected"],
            selected_hover_color=MD3["tab_selected_hover"],
            unselected_color=MD3["elevated"],
            unselected_hover_color=MD3["card"],
            text_color=MD3["on_surface"],
            corner_radius=6,
            font=ctk.CTkFont(size=13),
        )
        self._main_seg2.grid(row=1, column=0, columnspan=4, sticky="ew", padx=4, pady=(2, 4))

        # Ряд 2 — Индикатор активного РОЙ (виден на ВСЕХ вкладках когда РОЙ тратит баланс)
        self._roy_indicator_lb = ctk.CTkLabel(
            self._nav_frame,
            text="⚡ РОЙ АКТИВЕН  ·  баланс тает  (−30 сек/мин)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FFC107",
            fg_color="transparent",
        )
        # Изначально скрыт; _update_roy_indicator() управляет видимостью через grid

        # ── Контентная область ────────────────────────────────────────────
        self._content_frame = ctk.CTkFrame(self._outer, fg_color=MD3["card"],
                                            corner_radius=12, height=740)
        self._content_frame.pack(padx=20, pady=(4, 0), fill="x")
        self._content_frame.pack_propagate(False)

        # Фреймы вкладок (показываются/скрываются вручную)
        self.tab_crypt = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self.tab_hunt  = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        # self.tab_combo = ...  # временно отключён
        self.tab_ref   = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self.tab_roy   = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self.tab_chest = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self.tab_ancient = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        self._cal_frame = ctk.CTkScrollableFrame(self._content_frame, fg_color="transparent")

        self._active_tab_key = "tab_crypt"
        self._cal_visible = False
        self.tab_crypt.pack(fill="both", expand=True)

        # Общие переменные для калибровки (нужны в нескольких вкладках)
        _BASE = os.path.dirname(os.path.abspath(__file__))
        self._PROFILES = {
            "Client":    os.path.join(_BASE, "profiles", "profile_client.json"),
            "Browser 1": os.path.join(_BASE, "profiles", "profile_chrome.json"),
            "Browser 2": os.path.join(_BASE, "profiles", "profile_firefox.json"),
        }
        self._cal_profile_var    = ctk.StringVar(value="Client")
        self._dialog_offset_y_var = ctk.IntVar(value=0)
        self._swing1_var = ctk.IntVar(value=0)
        self._swing2_var = ctk.IntVar(value=0)

        self.setup_hunt_tab()
        self.setup_crypt_tab()
        # self.setup_combo_tab()  # временно отключён
        self.setup_ref_tab()
        self.setup_chest_tab()
        self.setup_ancient_tab()
        self.setup_calibration_tab()
        self.setup_roy_tab()
        self.update_license_info()
        self.after(1000, self._start_balance_sync)
        self.after(500, self._tick_trade_routes)
        self.after(60_000, self._tick_roy_drain)
        # On Top включён по умолчанию (см. CLAUDE.md: snap вправо, always-on-top) —
        # отложенный вызов, чтобы winfo_width()/winfo_height() в _on_always_on_top
        # вернули реальные размеры окна после отрисовки, а не 1x1 до неё.
        self.after(200, self._on_always_on_top)

        # Глобальный перехват ESC — стоп в любом окне
        def _esc_handler(event):
            if event.name == 'esc' and event.event_type == 'down':
                # Игнорируем ESC если бот сам нажимает его на шаге 11 (закрытие диалога биржи)
                pacman = getattr(self.engine, '_pacman', None) if self.is_running else None
                if pacman and getattr(pacman, '_suppressing_esc', False):
                    return
                self.after(0, self._emergency_stop)
        keyboard.hook(_esc_handler)


    def setup_hunt_tab(self):
        # Баланс + алмаз рядом
        _bal_row = ctk.CTkFrame(self.tab_hunt, fg_color="transparent")
        _bal_row.pack(pady=(4, 2))
        self.credits_label = ctk.CTkLabel(_bal_row, text="0",
                                          font=ctk.CTkFont(size=36, weight="bold"),
                                          text_color="#4ADE80")
        self.credits_label.pack(side="left")
        ctk.CTkButton(_bal_row, text="◆", width=36, height=40,
                      fg_color="#0A0F1E", hover_color="#1A2A5E",
                      text_color="#00CFFF", corner_radius=8,
                      font=ctk.CTkFont(size=22, weight="bold"),
                      command=lambda: webbrowser.open("https://total-hunter.com/dashboard/balance"),
                      ).pack(side="left", padx=(8, 0))


        # ─── Карточка «Нейросеть» ────────────────────────────────────────
        nn_frame = ctk.CTkFrame(self.tab_hunt, fg_color=MD3["elevated"],
                                corner_radius=12, border_width=1,
                                border_color=MD3["outline"])
        nn_frame.pack(fill="x", padx=20, pady=(4, 2))
        _nn_title_lb = ctk.CTkLabel(nn_frame, text=LANGS[self.current_lang]["nn_title"],
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MD3["on_surface"])
        _nn_title_lb.pack(anchor="w", padx=12, pady=(4, 2))
        self._i18n_labels.append((_nn_title_lb, "nn_title"))

        self.acc_frame = ctk.CTkFrame(nn_frame, fg_color="transparent")
        self.acc_frame.pack(fill="x", padx=12, pady=(4, 0))
        self.acc_lb = ctk.CTkLabel(self.acc_frame,
                                   text=LANGS[self.current_lang]["accuracy"],
                                   font=ctk.CTkFont(size=13),
                                   text_color=MD3["on_surface2"])
        self.acc_lb.pack(side="left")
        self.acc_val_lb = ctk.CTkLabel(self.acc_frame, text="70%",
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       text_color=MD3["value_text"])
        self.acc_val_lb.pack(side="right")
        self.conf_slider = ctk.CTkSlider(nn_frame, from_=0.1, to=0.9,
                                         command=self.update_slider_labels,
                                         button_color=MD3["primary"],
                                         button_hover_color=MD3["primary_dim"],
                                         progress_color=MD3["primary"])
        self.conf_slider.set(0.7)
        self.conf_slider.pack(padx=12, pady=(2, 2), fill="x")

        # Скорость работы — второй ползунок в карточке Нейросеть
        self.nav_wait_frame = ctk.CTkFrame(nn_frame, fg_color="transparent")
        self.nav_wait_frame.pack(fill="x", padx=12, pady=(4, 0))
        _nav_wait_lb = ctk.CTkLabel(self.nav_wait_frame, text=LANGS[self.current_lang]["nav_wait"],
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#FFC83C")
        _nav_wait_lb.pack(side="left")
        self._i18n_labels.append((_nav_wait_lb, "nav_wait"))
        self.nav_wait_val = ctk.CTkLabel(self.nav_wait_frame, text="1.5 сек",
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         text_color=MD3["value_text"])
        self.nav_wait_val.pack(side="right")
        self.nav_wait_slider = ctk.CTkSlider(nn_frame, from_=0.4, to=2.0,
                                             number_of_steps=16,
                                             command=self._update_nav_labels,
                                             button_color=MD3["primary"],
                                             button_hover_color=MD3["primary_dim"],
                                             progress_color=MD3["primary"])
        self.nav_wait_slider.set(1.5)
        self.nav_wait_slider.pack(padx=12, pady=(2, 8), fill="x")

        # ─── Карточка «Навигация» — три главных ползунка ─────────────────────
        nav_main_frame = ctk.CTkFrame(self.tab_hunt, fg_color=MD3["elevated"],
                                      corner_radius=12, border_width=1,
                                      border_color=MD3["outline"])
        nav_main_frame.pack(fill="x", padx=20, pady=(2, 2))
        _nav_main_title_lb = ctk.CTkLabel(nav_main_frame, text=LANGS[self.current_lang]["nav_main_title"],
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MD3["on_surface"])
        _nav_main_title_lb.pack(anchor="w", padx=12, pady=(4, 2))
        self._i18n_labels.append((_nav_main_title_lb, "nav_main_title"))

        # Шаг джойстика
        self.nav_step_frame = ctk.CTkFrame(nav_main_frame, fg_color="transparent")
        self.nav_step_frame.pack(fill="x", padx=12, pady=(2, 0))
        _nav_step_lb = ctk.CTkLabel(self.nav_step_frame, text=LANGS[self.current_lang]["nav_step"],
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#FFC83C")
        _nav_step_lb.pack(side="left")
        self._i18n_labels.append((_nav_step_lb, "nav_step"))
        self.nav_step_val = ctk.CTkLabel(self.nav_step_frame, text="13 px",
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         text_color=MD3["value_text"])
        self.nav_step_val.pack(side="right")
        self.nav_step_slider = ctk.CTkSlider(nav_main_frame, from_=10, to=20,
                                              number_of_steps=10,
                                              command=self._update_nav_labels_and_dot,
                                              button_color=MD3["primary"],
                                              button_hover_color=MD3["primary_dim"],
                                              progress_color=MD3["primary"])
        self.nav_step_slider.set(13)
        self.nav_step_slider.pack(padx=12, pady=(2, 2), fill="x")

        # Глубина нырка
        self.nav_inland_frame = ctk.CTkFrame(nav_main_frame, fg_color="transparent")
        self.nav_inland_frame.pack(fill="x", padx=12, pady=(2, 0))
        _nav_inland_lb = ctk.CTkLabel(self.nav_inland_frame, text=LANGS[self.current_lang]["nav_inland"],
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#FFC83C")
        _nav_inland_lb.pack(side="left")
        self._i18n_labels.append((_nav_inland_lb, "nav_inland"))
        self.nav_inland_val = ctk.CTkLabel(self.nav_inland_frame, text="5",
                                           font=ctk.CTkFont(size=14, weight="bold"),
                                           text_color=MD3["value_text"])
        self.nav_inland_val.pack(side="right")
        self.nav_inland_slider = ctk.CTkSlider(
            nav_main_frame, from_=1, to=10, number_of_steps=9,
            command=self._update_nav_labels,
            button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_inland_slider.set(5)
        self.nav_inland_slider.pack(padx=12, pady=(2, 4), fill="x")


        # Калибровка джойстика (мини-карта)
        self.nav_frame = ctk.CTkFrame(self.tab_hunt, fg_color=MD3["elevated"],
                                      corner_radius=12)
        self.nav_frame.pack(fill="x", padx=20, pady=3)
        # Заголовок + переключатель навигации в одной строке
        self.nav_header_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        self.nav_header_frame.pack(fill="x", padx=10, pady=(4, 2))
        self.nav_lb = ctk.CTkLabel(self.nav_header_frame,
                                   text=LANGS[self.current_lang]["nav_extra_title"],
                                   font=ctk.CTkFont(size=14, weight="bold"),
                                   text_color=MD3["on_surface"])
        self.nav_lb.pack(side="left")
        self._i18n_labels.append((self.nav_lb, "nav_extra_title"))
        self.nav_enabled_var = ctk.BooleanVar(value=True)
        self.nav_toggle = ctk.CTkSwitch(
            self.nav_header_frame,
            text=LANGS[self.current_lang]["nav_auto"],
            variable=self.nav_enabled_var,
            onvalue=True, offvalue=False,
            command=self._on_nav_toggle,
            font=ctk.CTkFont(size=13),
            text_color=MD3["on_surface2"],
            button_color=MD3["primary"],
            button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_toggle.pack(side="right")
        self._i18n_labels.append((self.nav_toggle, "nav_auto"))

        # CENTER X / Y — берётся из calibration (coord_manager.ref_a)
        # Невидимые виджеты для обратной совместимости с _on_nav_toggle и _load_settings
        self.nav_xy_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        self.nav_cx_entry = ctk.CTkEntry(self.nav_xy_frame)
        self.nav_cy_entry = ctk.CTkEntry(self.nav_xy_frame)

        # ── Coastal Snake parameters ──────────────────────────────────────
        nav_sliders_frame = ctk.CTkScrollableFrame(self.nav_frame,
                                                    fg_color="transparent",
                                                    scrollbar_button_color=MD3["outline"],
                                                    scrollbar_button_hover_color=MD3["primary"],
                                                    height=120)
        nav_sliders_frame.pack(fill="x", padx=0, pady=(0, 0))

        # Порог океана (% суши)
        self.nav_ocean_frame = ctk.CTkFrame(nav_sliders_frame, fg_color="transparent")
        self.nav_ocean_frame.pack(fill="x", padx=10, pady=(0, 2))
        _nav_ocean_lb = ctk.CTkLabel(self.nav_ocean_frame, text=LANGS[self.current_lang]["nav_ocean"],
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"])
        _nav_ocean_lb.pack(side="left")
        self._i18n_labels.append((_nav_ocean_lb, "nav_ocean"))
        self.nav_ocean_val = ctk.CTkLabel(self.nav_ocean_frame, text="3%",
                                          font=ctk.CTkFont(size=14, weight="bold"),
                                          text_color=MD3["value_text"])
        self.nav_ocean_val.pack(side="right")
        self.nav_ocean_slider = ctk.CTkSlider(
            nav_sliders_frame, from_=1, to=15, number_of_steps=14,
            command=self._update_nav_labels,
            button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_ocean_slider.set(3)
        self.nav_ocean_slider.pack(padx=10, pady=(0, 2), fill="x")

        # Мин. пикселей воды для детекта океана
        self.nav_waterpx_frame = ctk.CTkFrame(nav_sliders_frame, fg_color="transparent")
        self.nav_waterpx_frame.pack(fill="x", padx=10, pady=(0, 2))
        _nav_waterpx_lb = ctk.CTkLabel(self.nav_waterpx_frame, text=LANGS[self.current_lang]["nav_waterpx"],
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"])
        _nav_waterpx_lb.pack(side="left")
        self._i18n_labels.append((_nav_waterpx_lb, "nav_waterpx"))
        self.nav_waterpx_val = ctk.CTkLabel(self.nav_waterpx_frame, text="500",
                                            font=ctk.CTkFont(size=14, weight="bold"),
                                            text_color=MD3["value_text"])
        self.nav_waterpx_val.pack(side="right")
        self.nav_waterpx_slider = ctk.CTkSlider(
            nav_sliders_frame, from_=100, to=2000, number_of_steps=19,
            command=self._update_nav_labels,
            button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_waterpx_slider.set(500)
        self.nav_waterpx_slider.pack(padx=10, pady=(0, 2), fill="x")

        # Коэф. диагонали возврата
        self.nav_diagblind_frame = ctk.CTkFrame(nav_sliders_frame, fg_color="transparent")
        self.nav_diagblind_frame.pack(fill="x", padx=10, pady=(0, 2))
        _nav_diagblind_lb = ctk.CTkLabel(self.nav_diagblind_frame, text=LANGS[self.current_lang]["nav_diagblind"],
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"])
        _nav_diagblind_lb.pack(side="left")
        self._i18n_labels.append((_nav_diagblind_lb, "nav_diagblind"))
        self.nav_diagblind_val = ctk.CTkLabel(self.nav_diagblind_frame, text="0.50",
                                              font=ctk.CTkFont(size=14, weight="bold"),
                                              text_color=MD3["value_text"])
        self.nav_diagblind_val.pack(side="right")
        self.nav_diagblind_slider = ctk.CTkSlider(
            nav_sliders_frame, from_=0.0, to=1.0, number_of_steps=10,
            command=self._update_nav_labels,
            button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_diagblind_slider.set(0.5)
        self.nav_diagblind_slider.pack(padx=10, pady=(0, 2), fill="x")

        # Радиус конуса детекции берега
        # Память следов (TTL секунды)
        self.nav_footprint_frame = ctk.CTkFrame(nav_sliders_frame, fg_color="transparent")
        self.nav_footprint_frame.pack(fill="x", padx=10, pady=(0, 2))
        _nav_footprint_lb = ctk.CTkLabel(self.nav_footprint_frame, text=LANGS[self.current_lang]["nav_footprint"],
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"])
        _nav_footprint_lb.pack(side="left")
        self._i18n_labels.append((_nav_footprint_lb, "nav_footprint"))
        self.nav_footprint_val = ctk.CTkLabel(self.nav_footprint_frame, text="2 мин",
                                              font=ctk.CTkFont(size=14, weight="bold"),
                                              text_color=MD3["value_text"])
        self.nav_footprint_val.pack(side="right")
        self.nav_footprint_slider = ctk.CTkSlider(
            nav_sliders_frame, from_=60, to=1200, number_of_steps=19,
            command=self._update_nav_labels,
            button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_footprint_slider.set(120)
        self.nav_footprint_slider.pack(padx=10, pady=(0, 2), fill="x")

        # Дельта возврата (подмешивание вправо при возврате)
        self.nav_delta_frame = ctk.CTkFrame(nav_sliders_frame, fg_color="transparent")
        self.nav_delta_frame.pack(fill="x", padx=10, pady=(0, 2))
        _nav_delta_lb = ctk.CTkLabel(self.nav_delta_frame, text=LANGS[self.current_lang]["nav_delta"],
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"])
        _nav_delta_lb.pack(side="left")
        self._i18n_labels.append((_nav_delta_lb, "nav_delta"))
        self.nav_delta_val = ctk.CTkLabel(self.nav_delta_frame, text="0 px",
                                          font=ctk.CTkFont(size=14, weight="bold"),
                                          text_color=MD3["value_text"])
        self.nav_delta_val.pack(side="right")
        self.nav_delta_slider = ctk.CTkSlider(
            nav_sliders_frame, from_=0, to=20, number_of_steps=20,
            command=self._update_nav_labels,
            button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_delta_slider.set(0)
        self.nav_delta_slider.pack(padx=10, pady=(0, 4), fill="x")

        # Живость хода (smooth_alpha)
        self.nav_pitch_frame = ctk.CTkFrame(nav_sliders_frame, fg_color="transparent")
        self.nav_pitch_frame.pack(fill="x", padx=10, pady=(0, 2))
        _nav_pitch_lb = ctk.CTkLabel(self.nav_pitch_frame, text=LANGS[self.current_lang]["nav_pitch"],
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"])
        _nav_pitch_lb.pack(side="left")
        self._i18n_labels.append((_nav_pitch_lb, "nav_pitch"))
        self.nav_pitch_val = ctk.CTkLabel(self.nav_pitch_frame, text="50%",
                                          font=ctk.CTkFont(size=14, weight="bold"),
                                          text_color=MD3["value_text"])
        self.nav_pitch_val.pack(side="right")
        self.nav_pitch_slider = ctk.CTkSlider(
            nav_sliders_frame, from_=10, to=100, number_of_steps=18,
            command=self._update_nav_labels,
            button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_pitch_slider.set(100)
        self.nav_pitch_slider.pack(padx=10, pady=(0, 4), fill="x")

        # Кнопка сохранения настроек
        self.save_btn = ctk.CTkButton(self.nav_frame, text=LANGS[self.current_lang]["save_settings"],
                                      height=28,
                                      fg_color=MD3["green_btn"],
                                      hover_color=MD3["green_hover"],
                                      text_color=MD3["on_surface"],
                                      corner_radius=8,
                                      command=self._save_settings)
        self.save_btn.pack(padx=10, pady=(2, 4), fill="x")
        self._i18n_labels.append((self.save_btn, "save_settings"))

        # Загружаем сохранённые настройки если есть
        self._load_settings()

        # ─── Карточка «Последняя найденная биржа» ───────────────────────
        _last_ex_card = ctk.CTkFrame(self.tab_hunt, fg_color=MD3["elevated"],
                                     corner_radius=10, border_width=1,
                                     border_color=MD3["outline"])
        _last_ex_card.pack(fill="x", padx=20, pady=(4, 2))
        ctk.CTkLabel(_last_ex_card, text="Последняя биржа:",
                     font=ctk.CTkFont(size=12),
                     text_color=MD3["on_surface2"]).pack(anchor="w", padx=12, pady=(4, 0))
        self._last_exchange_lb = ctk.CTkLabel(_last_ex_card, text="—",
                                              font=ctk.CTkFont(size=13, weight="bold"),
                                              text_color=MD3["value_text"])
        self._last_exchange_lb.pack(anchor="w", padx=12, pady=(0, 4))

        # Кнопка Запуска (FAB-style prominent action)
        self.start_button = ctk.CTkButton(
            self.tab_hunt, text=LANGS[self.current_lang]["start"],
            height=56, font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"], corner_radius=14,
            command=self.toggle_bot)
        self.start_button.pack(pady=5, padx=40, fill="x")

        # Статус
        self.status_label = ctk.CTkLabel(self.tab_hunt,
                                         text=LANGS[self.current_lang]["status_ready"],
                                         text_color=MD3["on_surface2"])
        self.status_label.pack()

        # ─── Торговые Пути — обратный отсчёт ────────────────────────────────────
        _tr_card = ctk.CTkFrame(self.tab_hunt, fg_color=MD3["elevated"], corner_radius=10)
        _tr_card.pack(fill="x", padx=20, pady=(8, 4))
        self._tr_hunt_title_lb = ctk.CTkLabel(
            _tr_card, text=f"⏰ {LANGS[self.current_lang].get('tr_event', 'Trade Routes')}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=MD3["on_surface2"],
        )
        self._tr_hunt_title_lb.pack(pady=(6, 2))
        self._tr_hunt_label = ctk.CTkLabel(
            _tr_card, text="...",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4ADE80",
        )
        self._tr_hunt_label.pack(pady=(0, 8))


    def setup_crypt_tab(self):
        """Вкладка «Склепы» — выбор типов, настройки, старт/стоп."""
        from PIL import Image

        # Баланс + алмаз рядом
        _crypt_bal_row = ctk.CTkFrame(self.tab_crypt, fg_color="transparent")
        _crypt_bal_row.pack(pady=(4, 2))
        self.crypt_credits_label = ctk.CTkLabel(
            _crypt_bal_row, text="0",
            font=ctk.CTkFont(size=46, weight="bold"), text_color="#4ADE80"
        )
        self.crypt_credits_label.pack(side="left")
        ctk.CTkButton(_crypt_bal_row, text="◆", width=36, height=40,
                      fg_color="#0A0F1E", hover_color="#1A2A5E",
                      text_color="#00CFFF", corner_radius=8,
                      font=ctk.CTkFont(size=22, weight="bold"),
                      command=lambda: webbrowser.open("https://total-hunter.com/dashboard/balance"),
                      ).pack(side="left", padx=(8, 0))

        # ─── Сетка иконок склепов ────────────────────────────
        icons_label = ctk.CTkLabel(self.tab_crypt, text=LANGS[self.current_lang]["crypt_icons_title"],
                                   font=ctk.CTkFont(size=13),
                                   text_color=MD3["on_surface2"])
        icons_label.pack(pady=(2, 1))
        self._i18n_labels.append((icons_label, "crypt_icons_title"))

        scroll_frame = ctk.CTkScrollableFrame(self.tab_crypt, height=195,
                                               fg_color=MD3["card"],
                                               corner_radius=12,
                                               border_width=1,
                                               border_color=MD3["outline"],
                                               scrollbar_fg_color="transparent",
                                               scrollbar_button_color=MD3["outline"],
                                               scrollbar_button_hover_color=MD3["value_text"])
        scroll_frame.pack(padx=20, pady=(3, 0), fill="x")

        ctk.CTkFrame(self.tab_crypt, height=1, fg_color=MD3["outline"]).pack(
            fill="x", padx=20, pady=(5, 0)
        )

        targets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'targets')
        # Порядок: Ordinary 1-12, Epic 2-18, R 1-2
        crypt_order = (
            [f"Ordinary_{i}" for i in range(1, 13)] +
            [f"Epic_{i}"     for i in range(2, 19)] +
            [f"R_{i}"        for i in range(1, 3)]
        )

        self._crypt_vars: dict = {}
        self._crypt_icons: list = []  # держим ссылки чтобы GC не убрал

        COLS = 6
        for idx, crypt_name in enumerate(crypt_order):
            row = idx // COLS
            col = idx % COLS

            # Разделитель между группами (перед Epic и перед R)
            if crypt_name in ('Epic_2', 'R_1'):
                sep_row = row
                sep = ctk.CTkFrame(scroll_frame, height=2, fg_color=MD3["separator"])
                sep.grid(row=sep_row * 2, column=0, columnspan=COLS,
                         padx=4, pady=(4, 1), sticky="ew")

            cell = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            cell.grid(row=row * 2 + 1, column=col, padx=3, pady=2)

            # Иконка
            icon_path = os.path.join(targets_dir, f"{crypt_name}.png")
            try:
                pil_img = Image.open(icon_path).resize((40, 40))
                ctk_img = ctk.CTkImage(pil_img, size=(40, 40))
                self._crypt_icons.append(ctk_img)
                ctk.CTkLabel(cell, image=ctk_img, text="").pack()
            except Exception:
                ctk.CTkLabel(cell, text="?", width=40, height=40).pack()

            # Чекбокс
            var = ctk.BooleanVar(value=False)
            self._crypt_vars[crypt_name] = var
            ctk.CTkCheckBox(cell, text="", variable=var, width=20,
                            checkmark_color=MD3["bg"],
                            fg_color=MD3["checkbox"],
                            hover_color=MD3["checkbox_hover"],
                            border_color=MD3["outline"]).pack()

        # ─── Настройки ───────────────────────────────────────
        settings_frame = ctk.CTkScrollableFrame(self.tab_crypt, fg_color=MD3["elevated"],
                                                 corner_radius=12, height=165,
                                                 border_width=1,
                                                 border_color=MD3["outline"],
                                                 scrollbar_fg_color="transparent",
                                                 scrollbar_button_color=MD3["outline"],
                                                 scrollbar_button_hover_color=MD3["value_text"])
        settings_frame.pack(fill="x", padx=20, pady=4)

        def _slider_row(lang_key, default_text, highlight=False):
            """Хелпер: строка-заголовок слайдера."""
            row = ctk.CTkFrame(settings_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=(4, 0))
            name_lb = ctk.CTkLabel(row, text=LANGS[self.current_lang][lang_key],
                                   font=ctk.CTkFont(size=13, weight="bold" if highlight else "normal"),
                                   text_color="#FFC83C" if highlight else MD3["on_surface2"])
            name_lb.pack(side="left")
            val = ctk.CTkLabel(row, text=default_text,
                               font=ctk.CTkFont(size=14, weight="bold"),
                               text_color=MD3["value_text"])
            val.pack(side="right")
            self._i18n_labels.append((name_lb, lang_key))
            return val

        # Точность поиска
        self.crypt_conf_val = _slider_row("crypt_conf_lb", "70%")
        self.crypt_conf_slider = ctk.CTkSlider(settings_frame, from_=0.1, to=0.9,
                                               command=self._update_crypt_labels,
                                               button_color=MD3["primary"],
                                               button_hover_color=MD3["primary_dim"],
                                               progress_color=MD3["primary"])
        self.crypt_conf_slider.set(0.7)
        self.crypt_conf_slider.pack(padx=10, pady=(2, 4), fill="x")

        # Ускорение марша
        self.crypt_accel_val = _slider_row("crypt_accel_lb", "3", highlight=True)
        self.crypt_accel_slider = ctk.CTkSlider(settings_frame, from_=0, to=5,
                                                number_of_steps=5,
                                                command=self._update_crypt_labels,
                                                button_color=MD3["primary"],
                                                button_hover_color=MD3["primary_dim"],
                                                progress_color=MD3["primary"])
        self.crypt_accel_slider.set(3)
        self.crypt_accel_slider.pack(padx=10, pady=(2, 4), fill="x")

        # Перерыв между склепами
        self.crypt_break_val = _slider_row("crypt_break_lb", "10 с")
        self.crypt_break_slider = ctk.CTkSlider(settings_frame, from_=3, to=300,
                                                command=self._update_crypt_labels,
                                                button_color=MD3["primary"],
                                                button_hover_color=MD3["primary_dim"],
                                                progress_color=MD3["primary"])
        self.crypt_break_slider.set(10)
        self.crypt_break_slider.pack(padx=10, pady=(2, 4), fill="x")

        # Дальность марша Картера
        self.crypt_march_val = _slider_row("crypt_march_lb", "15 мин", highlight=True)
        self.crypt_march_slider = ctk.CTkSlider(settings_frame, from_=1, to=30,
                                                command=self._update_crypt_labels,
                                                button_color=MD3["primary"],
                                                button_hover_color=MD3["primary_dim"],
                                                progress_color=MD3["primary"])
        self.crypt_march_slider.set(15)
        self.crypt_march_slider.pack(padx=10, pady=(2, 4), fill="x")

        # Пауза между YOLO-детекциями (scroll_speed + 0.2 сек)
        self.crypt_scroll_val = _slider_row("crypt_scroll_lb", "скан 1.2 с")
        self.crypt_scroll_slider = ctk.CTkSlider(settings_frame, from_=0.0, to=4.0,
                                                 command=self._update_crypt_labels,
                                                 button_color=MD3["primary"],
                                                 button_hover_color=MD3["primary_dim"],
                                                 progress_color=MD3["primary"])
        self.crypt_scroll_slider.set(1.0)
        self.crypt_scroll_slider.pack(padx=10, pady=(2, 4), fill="x")

        # Тики скролла (1–100, для Chrome ~50, для Клиента ~3)
        self.scroll_clicks_val = _slider_row("scroll_clicks_lb", "3")
        self.scroll_clicks_slider = ctk.CTkSlider(settings_frame, from_=1, to=200,
                                                  number_of_steps=199,
                                                  command=self._update_crypt_labels,
                                                  button_color=MD3["primary"],
                                                  button_hover_color=MD3["primary_dim"],
                                                  progress_color=MD3["primary"])
        self.scroll_clicks_slider.set(3)
        self.scroll_clicks_slider.pack(padx=10, pady=(2, 4), fill="x")

        # Скорость кликов (−0.5 медленнее ←→ быстрее +0.5)
        self.crypt_speed_val = _slider_row("crypt_speed_lb", "0.0 с", highlight=True)
        self.crypt_speed_slider = ctk.CTkSlider(settings_frame, from_=-2.0, to=2.0,
                                                number_of_steps=40,
                                                command=self._update_crypt_labels,
                                                button_color=MD3["primary"],
                                                button_hover_color=MD3["primary_dim"],
                                                progress_color=MD3["primary"])
        self.crypt_speed_slider.set(0.0)
        self.crypt_speed_slider.pack(padx=10, pady=(2, 4), fill="x")

        # ── Профиль калибровки ────────────────────────────────────
        misc_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        misc_row.pack(fill="x", padx=10, pady=(2, 0))
        _crypt_profile_lb = ctk.CTkLabel(misc_row, text=LANGS[self.current_lang]["crypt_profile_lb"],
                                         font=ctk.CTkFont(size=13),
                                         text_color=MD3["on_surface2"])
        _crypt_profile_lb.pack(side="left")
        self._i18n_labels.append((_crypt_profile_lb, "crypt_profile_lb"))
        ctk.CTkOptionMenu(misc_row, values=list(self._PROFILES.keys()),
                          variable=self._cal_profile_var, width=100,
                          command=self._on_crypt_profile_change,
                          fg_color=MD3["card"],
                          button_color=MD3["primary"],
                          button_hover_color=MD3["primary_dim"],
                          text_color=MD3["on_surface"],
                          corner_radius=6).pack(side="left", padx=(4, 6))
        # Единая кнопка сохранения
        self.crypt_save_settings_btn = ctk.CTkButton(
                      settings_frame, text=LANGS[self.current_lang]["crypt_save_btn"],
                      height=32,
                      fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
                      text_color=MD3["on_surface"], corner_radius=8,
                      command=self._save_crypt_settings_all)
        self.crypt_save_settings_btn.pack(padx=10, pady=(6, 6), fill="x")
        self._i18n_labels.append((self.crypt_save_settings_btn, "crypt_save_btn"))

        # Обратный отсчёт (над кнопкой — всегда в зоне видимости)
        self.crypt_countdown_label = ctk.CTkLabel(
            self.tab_crypt, text="",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#FFB300",
        )
        self.crypt_countdown_label.pack(pady=(3, 0))

        # Разбивка времени: туда + обратно + буфер
        self.crypt_timer_detail_label = ctk.CTkLabel(
            self.tab_crypt, text="",
            font=ctk.CTkFont(size=13), text_color=MD3["outline"],
        )
        self.crypt_timer_detail_label.pack(pady=(0, 2))

        # ─── Кнопка Старт/Стоп ───────────────────────────────
        self.crypt_start_btn = ctk.CTkButton(
            self.tab_crypt, text=LANGS[self.current_lang]["crypt_start"],
            height=56, font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"], corner_radius=16,
            command=self.toggle_crypt_bot
        )
        self.crypt_start_btn.pack(pady=(3, 4), padx=20, fill="x")

        # Статус
        self.crypt_status_label = ctk.CTkLabel(
            self.tab_crypt, text=LANGS[self.current_lang]["crypt_ready"],
            text_color=MD3["on_surface2"]
        )
        self.crypt_status_label.pack(pady=(0, 2))

        self._load_crypt_settings()

    def _update_crypt_labels(self, _=None):
        sec = LANGS[self.current_lang]["unit_sec"]
        min_ = LANGS[self.current_lang]["unit_min"]
        scan = LANGS[self.current_lang]["unit_scan"]
        conf = int(self.crypt_conf_slider.get() * 100)
        self.crypt_conf_val.configure(text=f"{conf}%")
        accel = int(self.crypt_accel_slider.get())
        march_min = int(self.crypt_march_slider.get())
        self.crypt_march_val.configure(text=f"{march_min} {min_}")
        self.crypt_accel_val.configure(text=str(accel))
        brk = int(self.crypt_break_slider.get())
        self.crypt_break_val.configure(text=f"{brk} {sec}")
        sc = round(self.crypt_scroll_slider.get(), 1)
        self.crypt_scroll_val.configure(text=f"{scan} {sc + 0.2:.1f} {sec}")
        clicks = int(self.scroll_clicks_slider.get())
        self.scroll_clicks_val.configure(text=str(clicks))
        spd = round(self.crypt_speed_slider.get(), 1)
        spd_text = f"+{spd} {sec}" if spd > 0 else f"{spd} {sec}"
        self.crypt_speed_val.configure(text=spd_text)

    def on_crypt_found(self, crypt_type: str):
        """Вызывается ПОСЛЕ возвращения Картера (коллекция завершена)."""
        self._crypt_found_count += 1
        count = self._crypt_found_count
        L = LANGS[self.current_lang]
        self.after(0, lambda: self.crypt_status_label.configure(
            text=f"{L['crypt_collected']}: {count} | {L['crypt_last']}: {crypt_type}"
        ))
        from auth import spend_credit
        try:
            res = spend_credit()
            if res and res.get("success"):
                new_credits = res.get("credits", res.get("remaining", max(0, self.current_credits - 1)))
                self.after(0, lambda n=new_credits: self._update_credits_display(n))
            elif res and res.get("low_credits"):
                self.after(0, self.toggle_crypt_bot)
                self.after(0, lambda: webbrowser.open("https://total-hunter.com/dashboard/balance"))
            elif seconds_since_last_contact() > HEARTBEAT_TIMEOUT:
                self.after(0, self.toggle_crypt_bot)
                self.after(0, lambda: messagebox.showwarning("Hunter", LANGS[self.current_lang]["offline_stopped"]))
            else:
                new_credits = max(0, self.current_credits - 1)
                self.after(0, lambda n=new_credits: self._update_credits_display(n))
        except Exception:
            pass

    def on_crypt_status(self, msg: str):
        self.after(0, lambda: self.crypt_status_label.configure(text=msg))

    def on_crypt_countdown(self, remaining: int, total: int,
                           march_one_way: int = 0, buf: int = 0):
        if remaining > 0:
            big_text = f"{remaining} с"
            detail = f"→ {march_one_way} с  +  ← {march_one_way} с  +  {buf} с  =  {total} с"
        else:
            big_text = ""
            detail = ""
        def _update(t=big_text, d=detail):
            self.crypt_countdown_label.configure(text=t)
            self.crypt_timer_detail_label.configure(text=d)
        self.after(0, _update)

    def on_crypt_stop(self, reason: str):
        self.is_crypt_running = False
        stop_text = f"СТОП: {reason}"
        stop_color = MD3["error_text"]
        def _update(t=stop_text, c=stop_color):
            self.crypt_start_btn.configure(text=LANGS[self.current_lang]["crypt_start"],
                                           fg_color=MD3["green_btn"],
                                           hover_color=MD3["green_hover"])
            self.crypt_status_label.configure(text=t, text_color=c)
            self.crypt_countdown_label.configure(text="")
            self.crypt_timer_detail_label.configure(text="")
        self.after(0, _update)

    def toggle_crypt_bot(self):
        if self.is_crypt_running:
            self.is_crypt_running = False
            # stop path — no credits check needed
            self.crypt_engine.stop()
            self.crypt_start_btn.configure(text=LANGS[self.current_lang]["crypt_start"],
                                           fg_color=MD3["green_btn"],
                                           hover_color=MD3["green_hover"])
            self.crypt_status_label.configure(text=LANGS[self.current_lang]["crypt_stopped"],
                                             text_color=MD3["on_surface2"])
            self.crypt_countdown_label.configure(text="")
            self.crypt_timer_detail_label.configure(text="")
        else:
            if self.current_credits <= 0:
                messagebox.showwarning("Hunter", LANGS[self.current_lang]["no_credits"]); return
            selected = [k for k, v in self._crypt_vars.items() if v.get()]
            if not selected:
                self.crypt_status_label.configure(
                    text=LANGS[self.current_lang]["crypt_select_warn"], text_color="#FFB300"
                )
                return
            self.is_crypt_running = True
            self._crypt_found_count = 0
            self.crypt_status_label.configure(text=LANGS[self.current_lang]["crypt_searching"],
                                             text_color=MD3["secondary"])
            self.crypt_start_btn.configure(text=LANGS[self.current_lang]["crypt_stop_btn"],
                                           fg_color=MD3["error"],
                                           hover_color=MD3["error_hover"])
            self.crypt_engine.lang = self.current_lang
            self.crypt_engine.start(
                selected_crypts=selected,
                conf=self.crypt_conf_slider.get(),
                accelerations=int(self.crypt_accel_slider.get()),
                break_sec=int(self.crypt_break_slider.get()),
                scroll_speed=round(self.crypt_scroll_slider.get(), 1),
                max_march_min=int(self.crypt_march_slider.get()),
                swing1=self._swing1_var.get(),
                swing2=self._swing2_var.get(),
                speed_delta=round(self.crypt_speed_slider.get(), 1),
                on_found_callback=self.on_crypt_found,
                on_status_callback=self.on_crypt_status,
                on_stop_callback=self.on_crypt_stop,
                on_countdown_callback=self.on_crypt_countdown,
            )

    def toggle_chest_bot(self):
        L = LANGS[self.current_lang]
        if self._chest_running:
            self._chest_stop_event.set()
            return

        import chest_reader
        try:
            frame = chest_reader.grab_fullscreen()
            bbox = chest_reader.detect_dialog_bbox(frame)
        except Exception as exc:
            self.chest_status_label.configure(text=f"Ошибка захвата: {exc}",
                                              text_color=MD3["error_text"])
            return
        if bbox is None:
            self.chest_status_label.configure(text=L["chest_status_no_dialog"],
                                              text_color=MD3["error_text"])
            return

        self._chest_running = True
        self._chest_stop_event = threading.Event()
        import chest_reader
        _conn = chest_reader.init_db()
        self._update_chest_counts_display(chest_reader.get_unsynced_counts(_conn))
        _conn.close()
        pause_range = self._chest_pause_range(self.chest_speed_slider.get())
        full_lang = bool(self.chest_full_lang_var.get())
        self.chest_start_btn.configure(text=L["chest_stop_btn"],
                                       fg_color=MD3["error"], hover_color=MD3["error_hover"])
        self.chest_status_label.configure(text=L["chest_status_running"],
                                          text_color=MD3["secondary"])
        self.chest_send_btn.configure(state="disabled")

        stop_event = self._chest_stop_event

        def _on_update(counts):
            self.after(0, lambda c=dict(counts): self._update_chest_counts_display(c))

        def _worker():
            try:
                result = chest_reader.collect_chests(stop_event.is_set, on_update=_on_update,
                                                      pause_range=pause_range, full_lang=full_lang)
            except Exception as exc:
                result = {"counts": {}, "error": str(exc)}
            self.after(0, lambda: self._on_chest_collection_done(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_chest_collection_done(self, result):
        L = LANGS[self.current_lang]
        self._chest_running = False
        self.chest_start_btn.configure(text=L["chest_start_btn"],
                                       fg_color=MD3["green_btn"], hover_color=MD3["green_hover"])
        self.chest_status_label.configure(text=L["chest_status_stopped"],
                                          text_color=MD3["on_surface2"])
        self.chest_send_btn.configure(state="normal")
        self._update_chest_counts_display(result.get("counts", {}))

    def send_chests_to_server(self):
        L = LANGS[self.current_lang]
        kingdom = self.chest_kingdom_entry.get().strip()
        clan = self.chest_clan_entry.get().strip()
        if not kingdom or not clan:
            self.chest_status_label.configure(text=L["chest_missing_fields"],
                                              text_color=MD3["error_text"])
            return

        self.chest_send_btn.configure(state="disabled")

        def _worker():
            import chest_reader
            conn = chest_reader.init_db()
            rows = chest_reader.get_unsynced(conn)
            if not rows:
                conn.close()
                self.after(0, lambda: (
                    self.chest_send_btn.configure(state="normal"),
                    self.chest_status_label.configure(
                        text=L["chest_status_stopped"], text_color=MD3["on_surface2"]),
                ))
                return

            items = [{"chest_type": r[2], "sender": r[1], "timestamp": r[3]} for r in rows]
            ids = [r[0] for r in rows]
            result = chest_reader.export_to_api(kingdom, clan, items)
            if result.get("success"):
                chest_reader.mark_synced(conn, ids)
            conn.close()

            def _update():
                self.chest_send_btn.configure(state="normal")
                if result.get("success"):
                    self.chest_status_label.configure(text=L["chest_send_success"],
                                                       text_color=MD3["secondary"])
                    self._update_chest_counts_display({})
                elif result.get("low_credits"):
                    messagebox.showwarning("Hunter", L["no_credits"])
                    self.chest_status_label.configure(text=L["chest_status_stopped"],
                                                       text_color=MD3["on_surface2"])
                else:
                    self.chest_status_label.configure(text=L["chest_send_failed"],
                                                       text_color=MD3["error_text"])
            self.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()

    def toggle_combo_bot(self):
        if not hasattr(self, 'combo_engine'):
            return  # Combo заморожен
        if self.is_combo_running:
            self.is_combo_running = False
            self.combo_engine.stop()
            self.combo_start_btn.configure(text="ЗАПУСТИТЬ COMBO",
                                           fg_color=MD3["green_btn"],
                                           hover_color=MD3["green_hover"])
            self.combo_status_label.configure(text="Остановлено",
                                              text_color=MD3["on_surface2"])
        else:
            self.is_combo_running = True
            delay = round(self.combo_speed_slider.get(), 2)
            self.combo_start_btn.configure(text="ОСТАНОВИТЬ",
                                           fg_color=MD3["error"],
                                           hover_color=MD3["error_hover"])
            self.combo_status_label.configure(text="СТАТУС: В РАБОТЕ...",
                                              text_color=MD3["secondary"])
            self.combo_engine.start(
                delay=delay,
                status_callback=self._on_combo_status,
            )

    def _on_combo_status(self, msg: str):
        def _ui():
            self.combo_status_label.configure(text=msg)
            if msg in ("Готово — конец списка", "Остановлено", "Окно перекрыто — стоп"):
                self.is_combo_running = False
                self.combo_start_btn.configure(text="ЗАПУСТИТЬ COMBO",
                                               fg_color=MD3["green_btn"],
                                               hover_color=MD3["green_hover"])
        self.after(0, _ui)

    def _on_always_on_top(self):
        """Переключить режим «поверх всех окон» и обновить зону исключения YOLO."""
        on_top = self.always_on_top_var.get()
        self.wm_attributes('-topmost', on_top)
        if on_top:
            try:
                import ctypes, ctypes.wintypes
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
                work_x  = rect.left
                work_y  = rect.top
                work_w  = rect.right  - rect.left
                work_h  = rect.bottom - rect.top - 35
            except Exception:
                work_x, work_y = 0, 0
                work_w  = self.winfo_screenwidth()
                work_h  = self.winfo_screenheight() - 90

            # Берём реальный размер окна ПОСЛЕ отрисовки
            self.update_idletasks()
            win_w = self.winfo_width()
            win_h = min(work_h, work_w)

            # Прижать к правому краю с отступом 10px, не выходя за границы
            snap_x = max(work_x, work_x + work_w - win_w - 10)
            snap_y = work_y

            self.geometry(f"{win_w}x{work_h}+{snap_x}+{snap_y}")
            self.update_idletasks()
            x = self.winfo_x()
            y = self.winfo_y()
            w = self.winfo_width()
            h = self.winfo_height()
            self.crypt_engine.set_exclusion_region((x, y, w, h))
        else:
            self.crypt_engine.set_exclusion_region(None)

    def _save_crypt_settings_all(self):
        """Сохраняет все настройки Склепов в активный профиль калибровки."""
        self._save_crypt_settings()

    def _save_crypt_settings(self):
        """Сохраняет настройки Склепов (слайдеры, свинги, выбор) в файл активного профиля."""
        try:
            profile_name = self._cal_profile_var.get()
            path = self._PROFILES[profile_name]
            cfg = {}
            if os.path.exists(path):
                with open(path, 'r') as f:
                    cfg = json.load(f)
            # Настройки Склепов
            cfg['crypt_selected']      = [k for k, v in self._crypt_vars.items() if v.get()]
            cfg['crypt_conf']          = round(self.crypt_conf_slider.get(), 2)
            cfg['crypt_accelerations'] = int(self.crypt_accel_slider.get())
            cfg['crypt_break_sec']     = int(self.crypt_break_slider.get())
            cfg['crypt_scroll_speed']  = round(self.crypt_scroll_slider.get(), 1)
            cfg['crypt_max_march_min'] = int(self.crypt_march_slider.get())
            cfg['crypt_swing1']        = self._swing1_var.get()
            cfg['crypt_swing2']        = self._swing2_var.get()
            cfg['crypt_speed_delta']   = round(self.crypt_speed_slider.get(), 1)
            sc_clicks = int(self.scroll_clicks_slider.get())
            cfg['scroll_clicks']       = sc_clicks
            coord_manager.scroll_clicks = sc_clicks
            # Настройки Бирж
            cfg['step']                = int(self.nav_step_slider.get())
            cfg['conf']                = round(self.conf_slider.get(), 2)
            cfg['bot_speed']           = round(self.nav_wait_slider.get(), 1)
            cfg['max_inland_steps']    = int(self.nav_inland_slider.get())
            cfg['ocean_land_ratio']    = int(self.nav_ocean_slider.get()) / 100.0
            cfg['min_water_px']        = int(self.nav_waterpx_slider.get())
            cfg['diagonal_blind_coeff'] = round(self.nav_diagblind_slider.get(), 2)
            cfg['nav_footprint_ttl']   = int(self.nav_footprint_slider.get())
            cfg['return_delta_px']     = int(self.nav_delta_slider.get())
            cfg['smooth_alpha']        = int(self.nav_pitch_slider.get())
            with open(path, 'w') as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def _load_crypt_from_profile(self, path: str):
        """Загружает настройки Склепов из JSON профиля калибровки."""
        try:
            with open(path, 'r') as f:
                cfg = json.load(f)
            # Если в профиле нет crypt-настроек — не трогаем UI
            if 'crypt_selected' not in cfg and 'crypt_conf' not in cfg:
                return
            for v in self._crypt_vars.values():
                v.set(False)
            for name in cfg.get('crypt_selected', []):
                if name in self._crypt_vars:
                    self._crypt_vars[name].set(True)
            if 'crypt_conf' in cfg:
                self.crypt_conf_slider.set(cfg['crypt_conf'])
            if 'crypt_accelerations' in cfg:
                self.crypt_accel_slider.set(cfg['crypt_accelerations'])
            if 'crypt_break_sec' in cfg:
                self.crypt_break_slider.set(cfg['crypt_break_sec'])
            if 'crypt_scroll_speed' in cfg:
                self.crypt_scroll_slider.set(cfg['crypt_scroll_speed'])
            if 'crypt_max_march_min' in cfg:
                self.crypt_march_slider.set(cfg['crypt_max_march_min'])
            if 'crypt_swing1' in cfg:
                self._swing1_var.set(cfg['crypt_swing1'])
            if 'crypt_swing2' in cfg:
                self._swing2_var.set(cfg['crypt_swing2'])
            if 'crypt_speed_delta' in cfg:
                self.crypt_speed_slider.set(cfg['crypt_speed_delta'])
            if 'scroll_clicks' in cfg:
                sc_clicks = int(cfg['scroll_clicks'])
                self.scroll_clicks_slider.set(sc_clicks)
                coord_manager.scroll_clicks = sc_clicks
            self._update_crypt_labels()
            # Настройки Бирж
            if 'step' in cfg:
                self.nav_step_slider.set(cfg['step'])
            if 'conf' in cfg:
                self.conf_slider.set(cfg['conf'])
            spd = cfg.get('bot_speed') or cfg.get('move_wait', 1.5)
            self.nav_wait_slider.set(spd)
            if 'max_inland_steps' in cfg:
                self.nav_inland_slider.set(cfg['max_inland_steps'])
            if 'ocean_land_ratio' in cfg:
                self.nav_ocean_slider.set(int(cfg['ocean_land_ratio'] * 100))
            if 'min_water_px' in cfg:
                self.nav_waterpx_slider.set(cfg['min_water_px'])
            if 'diagonal_blind_coeff' in cfg:
                self.nav_diagblind_slider.set(cfg['diagonal_blind_coeff'])
            if 'nav_footprint_ttl' in cfg:
                raw_ttl = cfg['nav_footprint_ttl']
                self.nav_footprint_slider.set(max(60, min(1200, int(raw_ttl))))
            if 'return_delta_px' in cfg:
                self.nav_delta_slider.set(int(cfg['return_delta_px']))
            if 'smooth_alpha' in cfg:
                self.nav_pitch_slider.set(int(cfg['smooth_alpha']))
            self._update_nav_labels()
            self.update_slider_labels()
        except Exception:
            pass

    def _on_crypt_profile_change(self, profile_name: str):
        """Смена профиля в Склепах — загружает калибровку + все настройки Склепов."""
        path = self._PROFILES.get(profile_name, '')
        if path and os.path.exists(path):
            coord_manager.load(path)
            self._dialog_offset_y_var.set(coord_manager.dialog_offset_y)
            self._load_crypt_from_profile(path)
        self._save_gui_config_key("last_calibration_profile", profile_name)

    def _load_crypt_settings(self):
        """Загружает настройки Склепов из активного профиля (или gui_config.json как фоллбэк)."""
        try:
            profile_name = self._cal_profile_var.get()
            path = self._PROFILES.get(profile_name, '')
            if path and os.path.exists(path):
                self._load_crypt_from_profile(path)
                return
            # Фоллбэк: старые установки из gui_config.json
            if not os.path.exists(GUI_CONFIG_PATH):
                return
            with open(GUI_CONFIG_PATH, 'r') as f:
                cfg = json.load(f)
            for name in cfg.get('crypt_selected', []):
                if name in self._crypt_vars:
                    self._crypt_vars[name].set(True)
            if 'crypt_conf' in cfg:
                self.crypt_conf_slider.set(cfg['crypt_conf'])
            if 'crypt_accelerations' in cfg:
                self.crypt_accel_slider.set(cfg['crypt_accelerations'])
            if 'crypt_break_sec' in cfg:
                self.crypt_break_slider.set(cfg['crypt_break_sec'])
            if 'crypt_scroll_speed' in cfg:
                self.crypt_scroll_slider.set(cfg['crypt_scroll_speed'])
            if 'crypt_max_march_min' in cfg:
                self.crypt_march_slider.set(cfg['crypt_max_march_min'])
            if 'crypt_swing1' in cfg:
                self._swing1_var.set(cfg['crypt_swing1'])
            if 'crypt_swing2' in cfg:
                self._swing2_var.set(cfg['crypt_swing2'])
            self._update_crypt_labels()
        except Exception:
            pass

    def setup_combo_tab(self):
        """Вкладка Combo — автокомбинирование материалов."""

        ctk.CTkLabel(self.tab_combo,
                     text="COMBO — Комбинирование",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=MD3["primary"]).pack(pady=(16, 4))

        ctk.CTkLabel(self.tab_combo,
                     text="Откройте окно «Комбинирование» в игре,\nзатем нажмите СТАРТ.",
                     font=ctk.CTkFont(size=12),
                     text_color=MD3["on_surface2"],
                     justify="center").pack(pady=(0, 12))

        # ── Слайдер скорости ─────────────────────────────────
        speed_frame = ctk.CTkFrame(self.tab_combo, fg_color=MD3["elevated"],
                                   corner_radius=12, border_width=1,
                                   border_color=MD3["outline"])
        speed_frame.pack(padx=30, pady=(0, 10), fill="x")

        ctk.CTkLabel(speed_frame, text="Задержка между кликами",
                     font=ctk.CTkFont(size=12),
                     text_color=MD3["on_surface2"]).pack(pady=(10, 0))

        speed_row = ctk.CTkFrame(speed_frame, fg_color="transparent")
        speed_row.pack(fill="x", padx=10, pady=(4, 10))

        self.combo_speed_slider = ctk.CTkSlider(
            speed_row, from_=0.05, to=0.5, number_of_steps=45,
            fg_color=MD3["outline"], progress_color=MD3["primary"],
            button_color=MD3["secondary"], button_hover_color=MD3["primary_dim"],
            command=self._update_combo_speed_label)
        self.combo_speed_slider.set(0.1)
        self.combo_speed_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.combo_speed_val = ctk.CTkLabel(speed_row, text="0.10 с",
                                            font=ctk.CTkFont(size=13),
                                            text_color=MD3["value_text"], width=50)
        self.combo_speed_val.pack(side="left")

        # ── Кнопка Старт/Стоп ────────────────────────────────
        self.combo_start_btn = ctk.CTkButton(
            self.tab_combo, text="ЗАПУСТИТЬ COMBO",
            height=56, font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"], corner_radius=16,
            command=self.toggle_combo_bot)
        self.combo_start_btn.pack(pady=(10, 4), padx=20, fill="x")

        self.combo_status_label = ctk.CTkLabel(
            self.tab_combo, text="ГОТОВО",
            text_color=MD3["on_surface2"])
        self.combo_status_label.pack(pady=(0, 4))

    def _update_combo_speed_label(self, _=None):
        val = round(self.combo_speed_slider.get(), 2)
        self.combo_speed_val.configure(text=f"{val:.2f} с")

    def setup_ref_tab(self):
        # Заголовок
        self.ref_title_lb = ctk.CTkLabel(self.tab_ref,
                                         text=LANGS[self.current_lang]["ref_title"],
                                         font=ctk.CTkFont(size=20, weight="bold"),
                                         text_color=MD3["primary"])
        self.ref_title_lb.pack(pady=(14, 4))
        self.share_lb = ctk.CTkLabel(self.tab_ref,
                                     text=LANGS[self.current_lang]["share_text"],
                                     font=ctk.CTkFont(size=11),
                                     text_color=MD3["on_surface2"])
        self.share_lb.pack(pady=(0, 6))

        # ── Реферальный баланс ────────────────────────────────────────────
        ref_bal_card = ctk.CTkFrame(self.tab_ref, fg_color=MD3["elevated"],
                                    corner_radius=12, border_width=1,
                                    border_color=MD3["outline"])
        ref_bal_card.pack(padx=20, pady=(0, 8), fill="x")
        _ref_bal_title_lb = ctk.CTkLabel(ref_bal_card, text=LANGS[self.current_lang]["ref_bal_title"],
                     font=ctk.CTkFont(size=11), text_color=MD3["on_surface2"])
        _ref_bal_title_lb.pack(pady=(10, 0))
        self._i18n_labels.append((_ref_bal_title_lb, "ref_bal_title"))
        self.ref_balance_label = ctk.CTkLabel(ref_bal_card, text="0 ◆",
                                              font=ctk.CTkFont(size=28, weight="bold"),
                                              text_color="#FFD700")
        self.ref_balance_label.pack(pady=(2, 6))
        self.ref_transfer_btn = ctk.CTkButton(
            ref_bal_card, text=LANGS[self.current_lang]["ref_transfer_btn"],
            height=32, corner_radius=8,
            fg_color=MD3["blue_btn"], hover_color=MD3["blue_hover"],
            text_color=MD3["on_surface"],
            command=self._do_transfer_ref_balance)
        self.ref_transfer_btn.pack(padx=10, pady=(0, 10), fill="x")
        self._i18n_labels.append((self.ref_transfer_btn, "ref_transfer_btn"))

        # ── Реферальная ссылка (PRIMARY — AP-13) ─────────────────────────
        _ref_link_title_lb = ctk.CTkLabel(self.tab_ref, text=LANGS[self.current_lang]["ref_link_title"],
                     font=ctk.CTkFont(size=11), text_color=MD3["on_surface2"])
        _ref_link_title_lb.pack(pady=(4, 0))
        self._i18n_labels.append((_ref_link_title_lb, "ref_link_title"))
        link_frame = ctk.CTkFrame(self.tab_ref, fg_color=MD3["card"],
                                  corner_radius=10, border_width=1,
                                  border_color=MD3["outline"])
        link_frame.pack(padx=20, pady=(2, 2), fill="x")
        self.ref_link_val = ctk.CTkLabel(link_frame, text="https://total-hunter.com/ref/---",
                                         font=ctk.CTkFont(size=12),
                                         text_color=MD3["primary"])
        self.ref_link_val.pack(side="left", padx=10, pady=8, fill="x", expand=True)
        ctk.CTkButton(link_frame, text="📋", width=36, height=30,
                      fg_color=MD3["elevated"], hover_color=MD3["outline"],
                      text_color=MD3["on_surface"], corner_radius=8,
                      command=self.copy_link).pack(side="right", padx=6, pady=6)

        # my_code_val — невидимый виджет, хранит ref_id для copy_code()
        self.my_code_lb = ctk.CTkLabel(self.tab_ref, text="")
        self.my_code_val = ctk.CTkLabel(self.tab_ref, text="---")

        # ── Статистика L1 / L2 / L3 ──────────────────────────────────────
        stats_card = ctk.CTkFrame(self.tab_ref, fg_color=MD3["elevated"],
                                  corner_radius=12, border_width=1,
                                  border_color=MD3["outline"])
        stats_card.pack(padx=20, pady=(0, 8), fill="x")
        _ref_stats_title_lb = ctk.CTkLabel(stats_card, text=LANGS[self.current_lang]["ref_stats_title"],
                                          font=ctk.CTkFont(size=11),
                                          text_color=MD3["on_surface2"])
        _ref_stats_title_lb.pack(pady=(8, 2))
        self._i18n_labels.append((_ref_stats_title_lb, "ref_stats_title"))
        stats_row = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_row.pack(pady=(0, 10))
        for col, label in enumerate(["L1", "L2", "L3"]):
            col_frame = ctk.CTkFrame(stats_row, fg_color=MD3["card"],
                                     corner_radius=8, width=80)
            col_frame.pack(side="left", padx=8)
            ctk.CTkLabel(col_frame, text=label, font=ctk.CTkFont(size=10),
                         text_color=MD3["on_surface2"]).pack(pady=(6, 0))
            lbl = ctk.CTkLabel(col_frame, text="0",
                               font=ctk.CTkFont(size=20, weight="bold"),
                               text_color=MD3["primary"])
            lbl.pack(pady=(0, 6))
            setattr(self, f"ref_l{col+1}_label", lbl)

        # Код пригласителя перенесён на сайт (dashboard/referrals)
        self.friend_code_lb = ctk.CTkLabel(self.tab_ref, text="")
        self.ref_entry = ctk.CTkEntry(self.tab_ref)
        self.ref_btn = ctk.CTkButton(self.tab_ref, text="")


    def update_slider_labels(self, _=None):
        acc = int(self.conf_slider.get() * 100)
        self.acc_val_lb.configure(text=f"{acc}%")


    def _update_credits_display(self, n: int):
        """Обновляет счётчик кредитов на всех вкладках сразу."""
        self.current_credits = n
        self.credits_label.configure(text=str(n))
        self.crypt_credits_label.configure(text=str(n))
        self._set_start_buttons_state(n > 0)

    def _set_start_buttons_state(self, enabled: bool):
        """Блокирует/разблокирует кнопки старта при нулевом балансе.
        Кнопки в режиме СТОП (поиск идёт) не трогаем — пользователь должен иметь возможность остановить."""
        state = "normal" if enabled else "disabled"
        # Биржи + дубль кнопки в РОЙ
        if not self.is_running:
            if hasattr(self, 'start_button'):
                self.start_button.configure(state=state)
            if hasattr(self, '_roy_hunt_btn'):
                self._roy_hunt_btn.configure(state=state)
        # Склепы
        if not self.is_crypt_running:
            if hasattr(self, 'crypt_start_btn'):
                self.crypt_start_btn.configure(state=state)
        # Сундуки
        if not self._chest_running:
            if hasattr(self, 'chest_start_btn'):
                self.chest_start_btn.configure(state=state)
        # Combo (заморожен — guard)
        if not self.is_combo_running:
            if hasattr(self, 'combo_start_btn'):
                self.combo_start_btn.configure(state=state)

    def _start_balance_sync(self):
        """Запускает фоновый long-poll поток — мгновенное обновление баланса."""
        def _worker():
            import time
            while True:
                try:
                    data = get_balance_update()
                    if data and data.get("credits") is not None:
                        self.after(0, lambda c=data["credits"]: self._update_credits_display(c))
                except Exception:
                    time.sleep(2)
        threading.Thread(target=_worker, daemon=True).start()

    def update_license_info(self):
        try:
            data = check_license()
            if not data: return
           
            if data.get("banned"):
                messagebox.showerror("System", LANGS[self.current_lang]["banned"])
                self.destroy(); sys.exit()
               
            self.current_credits = data.get("credits", 0)
            self._update_credits_display(self.current_credits)
           
            if data.get("email"):
                self.user_email = data.get("email")
                self.label_email.configure(text=f"User: {self.user_email}")
                # Авторизован — скрываем кнопку логина в баннере
                self.login_button.pack_forget()
            if data.get("trial_used"):
                self.trial_button.pack_forget()
            if data.get("ref_id"):
                self.my_ref_id = data["ref_id"]
                self.my_code_val.configure(text=self.my_ref_id)
                self.ref_link_val.configure(
                    text=f"https://total-hunter.com/ref/{self.my_ref_id}")
            ref_credits = data.get("ref_credits", 0)
            self.ref_balance_label.configure(text=f"{ref_credits} ◆")
            refs = data.get("referrals") or {}
            self.ref_l1_label.configure(text=str(refs.get("l1", 0)))
            self.ref_l2_label.configure(text=str(refs.get("l2", 0)))
            self.ref_l3_label.configure(text=str(refs.get("l3", 0)))
            if data.get("is_referred"):
                self.ref_entry.pack_forget(); self.ref_btn.pack_forget()
                self.friend_code_lb.configure(text=LANGS[self.current_lang]["ref_used"], text_color="#4ADE80", font=ctk.CTkFont(size=14, weight="bold"))
            if data.get("broadcast"):
                self.broadcast_frame.pack(fill="x", padx=0, pady=0)
                self.broadcast_label.pack(padx=10, pady=5)
                self.broadcast_label.configure(text=f"📢 {data['broadcast']}")
                self.info_banner.pack(fill="x", padx=20, pady=(4, 0))
            else:
                self.broadcast_frame.pack_forget()
                # Прячем баннер полностью, если в нём больше нечего показывать:
                # нет broadcast, юзер авторизован (email) и трайл уже использован
                if data.get("email") and data.get("trial_used"):
                    self.info_banner.pack_forget()
        except: pass


    def _show_tab(self, key):
        """Показать фрейм вкладки по ключу, скрыть остальные."""
        _all = (self.tab_crypt, self.tab_hunt, self.tab_ref, self.tab_roy, self.tab_chest,
                self.tab_ancient, self._cal_frame)
        for f in _all:
            f.pack_forget()
        self._cal_visible = False
        tab_map = {
            "tab_crypt": self.tab_crypt,
            "tab_hunt":  self.tab_hunt,
            "tab_ref":   self.tab_ref,
            "tab_roy":   self.tab_roy,
            "tab_chest": self.tab_chest,
            "tab_ancient": self.tab_ancient,
        }
        frame = tab_map.get(key)
        if frame:
            self._active_tab_key = key
            frame.pack(fill="both", expand=True)
        if key in self._tab_init_names:
            self._main_seg.set(self._tab_init_names.get(key, ""))
            self._main_seg2.set("")
        else:
            self._main_seg.set("")
            self._main_seg2.set(self._tab2_init_names.get(key, ""))
        if key in ("tab_hunt", "tab_roy") and hasattr(self, '_roy_enabled_var'):
            self._roy_refresh_pool()

    def _on_seg_change(self, val):
        """Вызывается при клике на верхний ряд вкладок."""
        for k, v in self._tab_init_names.items():
            if v == val:
                self._show_tab(k)
                return

    def _on_seg2_change(self, val):
        """Вызывается при клике на нижний ряд вкладок (СУНДУКИ, ДРЕВНИЙ, КАЛИБРОВКА)."""
        for k, v in self._tab2_init_names.items():
            if v == val:
                if k == "tab_cal":
                    self._main_seg.set("")
                    for f in (self.tab_crypt, self.tab_hunt, self.tab_ref, self.tab_roy,
                               self.tab_chest, self.tab_ancient):
                        f.pack_forget()
                    self._cal_frame.pack(fill="both", expand=True)
                    self._cal_visible = True
                else:
                    self._show_tab(k)
                return

    def _toggle_cal(self):
        if self._cal_visible:
            self._cal_visible = False
            self._show_tab(self._active_tab_key)
        else:
            self._on_seg2_change(self._tab2_init_names["tab_cal"])

    def _on_nav_toggle(self):
        """Dim nav controls when auto-navigation is disabled."""
        enabled = self.nav_enabled_var.get()
        state = "normal" if enabled else "disabled"
        for w in (self.nav_step_slider,):
            w.configure(state=state)

    def _update_nav_labels(self, _=None):
        sec = LANGS[self.current_lang]["unit_sec"]
        min_ = LANGS[self.current_lang]["unit_min"]
        self.nav_step_val.configure(text=f"{int(self.nav_step_slider.get())} px")
        self.nav_wait_val.configure(text=f"{self.nav_wait_slider.get():.1f} {sec}")
        self.nav_inland_val.configure(text=f"{int(self.nav_inland_slider.get())}")
        self.nav_ocean_val.configure(text=f"{int(self.nav_ocean_slider.get())}%")
        self.nav_waterpx_val.configure(text=f"{int(self.nav_waterpx_slider.get())}")
        self.nav_diagblind_val.configure(text=f"{self.nav_diagblind_slider.get():.2f}")
        ttl = int(self.nav_footprint_slider.get())
        self.nav_footprint_val.configure(
            text=f"{ttl // 60} {min_}" if ttl >= 60 else f"{ttl} {sec}"
        )
        self.nav_delta_val.configure(text=f"{int(self.nav_delta_slider.get())} px")
        self.nav_pitch_val.configure(text=f"{int(self.nav_pitch_slider.get())}%")

    def _update_nav_labels_and_dot(self, _=None):
        self._update_nav_labels()
        self._show_calibration_dot()

    def _show_calibration_dot(self, _=None):
        """Show a red dot on screen at the joystick center (from calibration)."""
        import tkinter as tk
        try:
            cx = int(coord_manager.ref_a[0])
            cy = int(coord_manager.ref_a[1])
        except Exception:
            return

        if not hasattr(self, '_dot_win') or not self._dot_win.winfo_exists():
            self._dot_win = tk.Toplevel(self)
            self._dot_win.overrideredirect(True)
            self._dot_win.attributes('-topmost', True)
            self._dot_canvas = tk.Canvas(self._dot_win, width=16, height=16,
                                          bg='black', highlightthickness=0)
            self._dot_canvas.pack()
            self._dot_canvas.create_oval(1, 1, 15, 15, fill='red', outline='yellow', width=1)

        self._dot_win.geometry(f'16x16+{cx - 8}+{cy - 8}')
        self._dot_win.deiconify()

        if hasattr(self, '_dot_after'):
            self.after_cancel(self._dot_after)
        self._dot_after = self.after(3000, lambda: self._dot_win.withdraw())

    def _show_chest_rect_overlay(self, ref_rect, offset_name):
        """Draw a topmost border-only rectangle over the game at the OCR crop
        position for the given chest field, so the owner can see exactly what
        will be read while nudging the D-Pad — mirrors _show_calibration_dot's
        Toplevel/after pattern but sized to the real crop, not a fixed dot."""
        import tkinter as tk
        x, y, w, h = coord_manager.to_region_dialog(*ref_rect)
        dx, dy = coord_manager.get_ui_offset(offset_name)
        x, y = x + dx, y + dy

        if not hasattr(self, '_chest_rect_win') or not self._chest_rect_win.winfo_exists():
            self._chest_rect_win = tk.Toplevel(self)
            self._chest_rect_win.overrideredirect(True)
            self._chest_rect_win.attributes('-topmost', True)
            self._chest_rect_win.attributes('-transparentcolor', 'black')
            self._chest_rect_canvas = tk.Canvas(self._chest_rect_win, bg='black',
                                                 highlightthickness=0)
            self._chest_rect_canvas.pack(fill="both", expand=True)

        self._chest_rect_win.geometry(f'{w}x{h}+{x}+{y}')
        self._chest_rect_canvas.delete("all")
        self._chest_rect_canvas.config(width=w, height=h)
        self._chest_rect_canvas.create_rectangle(1, 1, w - 1, h - 1, outline='red', width=2)
        self._chest_rect_win.deiconify()

        if hasattr(self, '_chest_rect_after'):
            self.after_cancel(self._chest_rect_after)
        self._chest_rect_after = self.after(3000, lambda: self._chest_rect_win.withdraw())

    def _save_settings(self):
        """Сохраняет настройки Бирж в активный профиль."""
        try:
            self._save_crypt_settings()
            messagebox.showinfo("OK", "Настройки сохранены")
        except Exception as e:
            messagebox.showerror("Error", f"Не удалось сохранить: {e}")

    def _load_settings(self):
        """Загружает настройки Бирж из активного профиля."""
        try:
            profile_name = self._cal_profile_var.get()
            path = self._PROFILES.get(profile_name, '')
            if path and os.path.exists(path):
                self._load_crypt_from_profile(path)
                return
            # Фоллбэк: gui_config.json для старых установок
            if not os.path.exists(GUI_CONFIG_PATH):
                return
            with open(GUI_CONFIG_PATH) as f:
                cfg = json.load(f)
            if 'step' in cfg:
                self.nav_step_slider.set(cfg['step'])
            if 'conf' in cfg:
                self.conf_slider.set(cfg['conf'])
            spd = cfg.get('bot_speed') or cfg.get('move_wait', 1.5)
            self.nav_wait_slider.set(spd)
            self.nav_inland_slider.set(cfg.get("max_inland_steps", 5))
            self.nav_ocean_slider.set(int(cfg.get("ocean_land_ratio", 0.03) * 100))
            self.nav_waterpx_slider.set(cfg.get("min_water_px", 500))
            self.nav_diagblind_slider.set(cfg.get("diagonal_blind_coeff", 0.5))
            raw_ttl = cfg.get("nav_footprint_ttl", 120)
            self.nav_footprint_slider.set(max(60, min(1200, int(raw_ttl))))
            self.nav_delta_slider.set(int(cfg.get("return_delta_px", 0)))
            self.nav_pitch_slider.set(int(cfg.get("smooth_alpha", 100)))
            self._update_nav_labels()
            self.update_slider_labels()
        except Exception:
            pass

    def toggle_bot(self):
        if not self.is_running:
            # Отключаем On Top — бот должен видеть весь экран без перекрытия
            if self.always_on_top_var.get():
                self.always_on_top_var.set(False)
                self._on_always_on_top()
            if self.current_credits <= 0:
                messagebox.showwarning("Hunter", LANGS[self.current_lang]["no_credits"]); return
            try:
                # Центр джойстика — из калибровки (единственный источник правды)
                cx, cy = int(coord_manager.anchor_x), int(coord_manager.anchor_y)
                step = int(self.nav_step_slider.get())
                bot_speed = float(self.nav_wait_slider.get())
            except ValueError:
                messagebox.showerror("Error", "Неверные параметры навигации"); return

            try:
                self.engine.roy_enabled  = self._roy_enabled_var.get()
                self.engine.roy_kingdom  = self._get_roy_kingdom()
                self.engine.start(
                    conf=self.conf_slider.get(),
                    center_x=cx,
                    center_y=cy,
                    joystick_step=int(self.nav_step_slider.get()),
                    move_wait=bot_speed,
                    navigation_enabled=self.nav_enabled_var.get(),
                    max_inland_steps=int(self.nav_inland_slider.get()),
                    ocean_land_ratio=int(self.nav_ocean_slider.get()) / 100.0,
                    min_water_px=int(self.nav_waterpx_slider.get()),
                    diagonal_blind_coeff=round(self.nav_diagblind_slider.get(), 2),
                    footprint_ttl=float(self.nav_footprint_slider.get()),
                    return_delta_px=int(self.nav_delta_slider.get()),
                    smooth_alpha=float(self.nav_pitch_slider.get()) / 100.0,
                    use_beacon=bool(self._load_gui_config().get('use_beacon', False)),
                    pixels_per_step=int(self._load_gui_config().get('nav_pps', 20)),
                )
                self.start_button.configure(text=LANGS[self.current_lang]["stop"],
                                            fg_color=MD3["error"],
                                            hover_color=MD3["error_hover"])
                if hasattr(self, '_roy_hunt_btn'):
                    self._roy_hunt_btn.configure(text=LANGS[self.current_lang]["stop"],
                                                 fg_color=MD3["error"],
                                                 hover_color=MD3["error_hover"])
                self.status_label.configure(text=LANGS[self.current_lang]["status_running"],
                                            text_color="#FFD740")
                self.is_running = True
                self._esc_stopped = False  # ручной старт сбрасывает флаг ESC
            except Exception as e:
                messagebox.showerror("Error", f"Engine failed: {e}")
        else:
            self.engine.stop()
            self.start_button.configure(text=LANGS[self.current_lang]["start"],
                                        fg_color=MD3["green_btn"],
                                        hover_color=MD3["green_hover"])
            if hasattr(self, '_roy_hunt_btn'):
                self._roy_hunt_btn.configure(text=LANGS[self.current_lang]["start"],
                                             fg_color=MD3["green_btn"],
                                             hover_color=MD3["green_hover"])
            self.status_label.configure(text=LANGS[self.current_lang]["status_ready"],
                                        text_color=MD3["on_surface2"])
            self.is_running = False


    def _on_pool_auto_refresh(self, pool: list) -> None:
        """Авто-обновление пула сразу после успешного report() — из фонового треда.
        Pre-populate known IDs before update — собственные координаты не вызывают звук.
        """
        if not self._roy_enabled_var.get():
            return
        def _refresh():
            self._roy_pool_known_ids |= {
                (e.get('kingdom'), e.get('x'), e.get('y')) for e in pool
            }
            self._roy_update_list(pool)
        self.after(0, _refresh)

    def _on_exchange_found(self) -> None:
        """Биржа найдена — вызывается из фонового треда навигатора.
        Останавливаем движок и планируем ОДИН чистый перезапуск через Tkinter mainloop."""
        self.engine.stop()
        self.after(0, self._gui_set_stopped)
        self._auto_restart_id = self.after(10000, self._programmatic_restart)

    def _programmatic_restart(self) -> None:
        """Перезапуск движка через Tkinter mainloop — вызывается ровно один раз через after(10000).
        Эквивалент ручного нажатия кнопки СТАРТ после 10-секундной паузы."""
        self._auto_restart_id = None
        if self._esc_stopped:
            return  # пользователь нажал ESC — перезапуск запрещён
        if self.is_running:
            return  # пользователь уже запустил вручную
        if not self.engine._last_start_kwargs:
            return
        try:
            self.engine._initial_yolo_block_sec = 60.0
            self.engine.start(**self.engine._last_start_kwargs)
            self._gui_set_running()
            self.is_running = True
        except Exception as e:
            _roy_log(f"Programmatic restart failed: {e}")

    def _on_exchange_restart(self, state: str) -> None:
        """Callback из engine (фоновый поток) — планируем обновление GUI в главном потоке."""
        if state == 'stopped':
            self.after(0, self._gui_set_stopped)
        elif state == 'starting':
            self.after(0, self._gui_set_running)

    def _gui_set_stopped(self) -> None:
        """Обновляем GUI в состояние СТОП (thread-safe через after)."""
        self.is_running = False
        try:
            self.start_button.configure(
                text=LANGS[self.current_lang]["start"],
                fg_color=MD3["green_btn"], hover_color=MD3["green_hover"])
            if hasattr(self, '_roy_hunt_btn'):
                self._roy_hunt_btn.configure(
                    text=LANGS[self.current_lang]["start"],
                    fg_color=MD3["green_btn"], hover_color=MD3["green_hover"])
            self.status_label.configure(
                text=LANGS[self.current_lang]["status_ready"],
                text_color=MD3["on_surface2"])
        except Exception:
            pass

    def _gui_set_running(self) -> None:
        """Обновляем GUI в состояние РАБОТАЕТ (thread-safe через after)."""
        self.is_running = True
        try:
            self.start_button.configure(
                text=LANGS[self.current_lang]["stop"],
                fg_color=MD3["error"], hover_color=MD3["error_hover"])
            if hasattr(self, '_roy_hunt_btn'):
                self._roy_hunt_btn.configure(
                    text=LANGS[self.current_lang]["stop"],
                    fg_color=MD3["error"], hover_color=MD3["error_hover"])
            self.status_label.configure(
                text=LANGS[self.current_lang]["status_running"],
                text_color="#FFD740")
        except Exception:
            pass

    def _emergency_stop(self):
        """ESC — наивысший приоритет: полная остановка, никаких авто-перезапусков."""
        # Отменяем любой запланированный авто-перезапуск
        if self._auto_restart_id is not None:
            self.after_cancel(self._auto_restart_id)
            self._auto_restart_id = None
        # Флаг: ESC был нажат — _programmatic_restart не будет перезапускать
        self._esc_stopped = True

        if self.is_running:
            self.engine.stop()
            self.start_button.configure(text=LANGS[self.current_lang]["start"],
                                        fg_color=MD3["green_btn"],
                                        hover_color=MD3["green_hover"])
            if hasattr(self, '_roy_hunt_btn'):
                self._roy_hunt_btn.configure(text=LANGS[self.current_lang]["start"],
                                             fg_color=MD3["green_btn"],
                                             hover_color=MD3["green_hover"])
            self.status_label.configure(text=LANGS[self.current_lang]["status_ready"],
                                        text_color=MD3["on_surface2"])
            self.is_running = False
        # Склепы
        if self.is_crypt_running:
            self.is_crypt_running = False
            self.crypt_engine.stop()
            self.crypt_start_btn.configure(text=LANGS[self.current_lang]["crypt_start"],
                                           fg_color=MD3["green_btn"],
                                           hover_color=MD3["green_hover"])
            self.crypt_status_label.configure(text=f"{LANGS[self.current_lang]['crypt_stopped']} (ESC)",
                                              text_color=MD3["on_surface2"])
        # Сундуки
        if self._chest_running:
            self._chest_stop_event.set()
        # Combo (заморожен — guard на случай если engine не инициализирован)
        if self.is_combo_running and hasattr(self, 'combo_engine'):
            self.is_combo_running = False
            self.combo_engine.stop()
        # Обновить пул — восстановить незаконченные записи после остановки
        if hasattr(self, '_roy_enabled_var') and self._roy_enabled_var.get():
            self.after(500, self._roy_refresh_pool)

    def on_target_found(self):
        """Вызывается из фонового потока движка"""
        self.after(0, self._process_found)


    def _process_found(self):
        """Безопасно обновляем UI в главном потоке. Змейка продолжается — бот не останавливается,
        кроме подтверждённого нулевого баланса или долгого отсутствия связи с сервером."""
        res = spend_credit("exchange")
        if res and res.get("success"):
            self._update_credits_display(res.get("credits", res.get("remaining", self.current_credits - 10)))
        elif res and res.get("low_credits"):
            self.toggle_bot()
            webbrowser.open("https://total-hunter.com/dashboard/balance")
        elif seconds_since_last_contact() > HEARTBEAT_TIMEOUT:
            self.toggle_bot()
            messagebox.showwarning("Hunter", LANGS[self.current_lang]["offline_stopped"])

    def _on_last_exchange_found(self, result: dict) -> None:
        """Callback из engine: обновляет карточку последней найденной биржи (вкладка Биржи)."""
        import time as _t
        ts   = _t.strftime("%H:%M:%S")
        text = f"K:{result['kingdom']}  X:{result['x']}  Y:{result['y']}  ·  {ts}"
        self.after(0, lambda t=text: self._last_exchange_lb.configure(text=t))
        # Запомнить координаты — ROY не должен играть звук на нашу же находку
        key = (result.get('kingdom'), result.get('x'), result.get('y'))
        self._roy_self_reported.add(key)


    def handle_login(self):
        code, expires = generate_link_code()
        if not code:
            messagebox.showerror("Hunter", "Connection error. Check internet and try again.")
            return

        # Show code in button — остаётся кликабельной: код больше не истекает
        # за 10 мин (сервер), но юзер может застрять на сайте/логине Google и
        # ему нужен способ повторить попытку без рестарта бота. Повторный клик
        # просто сгенерирует новый код (старый инвалидируется на сервере).
        self.login_button.configure(
            text=f"Code: {code}   (click to retry)",
            fg_color="#1B3A4B",
            hover_color="#1B3A4B",
        )
        webbrowser.open("https://total-hunter.com/dashboard/devices")
        self._poll_link_status()

    def _poll_link_status(self):
        """Poll every 5 sec until device is linked (email appears)."""
        data = check_license()
        if data and data.get("email"):
            self.update_license_info()
            return
        self.after(5000, self._poll_link_status)


    def copy_code(self):
        code = self.my_code_val.cget("text")
        if code not in ("---", ""):
            self.clipboard_clear()
            self.clipboard_append(code)
            messagebox.showinfo("OK", LANGS[self.current_lang]["copied"])

    def copy_link(self):
        link = self.ref_link_val.cget("text")
        if "---" not in link:
            self.clipboard_clear()
            self.clipboard_append(link)
            messagebox.showinfo("OK", LANGS[self.current_lang]["copied"])

    def _do_transfer_ref_balance(self):
        self.ref_transfer_btn.configure(state="disabled", text="⏳ Перевод...")
        def _worker():
            ok, msg, new_credits = transfer_referral_balance()
            def _upd():
                self.ref_transfer_btn.configure(state="normal",
                                                text=LANGS[self.current_lang]["ref_transfer_btn"])
                if ok:
                    self.ref_balance_label.configure(text="0 ◆")
                    self._update_credits_display(new_credits)
                    messagebox.showinfo("Перевод", msg or "Баланс успешно переведён!")
                else:
                    messagebox.showerror("Ошибка", msg or "Не удалось перевести баланс.")
            self.after(0, _upd)
        import threading
        threading.Thread(target=_worker, daemon=True).start()


    def activate_ref_action(self):
        code = self.ref_entry.get().strip().upper()
        if not code: return
        res = activate_referral(code)
        if res.get("success"):
            messagebox.showinfo("Referral", res.get("message"))
            self.update_license_info()
        else: messagebox.showerror("Error", res.get("message"))


    def claim_trial_action(self):
        # Блокируем кнопку на время запроса (до 15с при медленном интернете) —
        # без этого дублирующий клик уходит вторым запросом параллельно первому;
        # сервер это уже исключает атомарным UPDATE, кнопка — просто UX, чтобы
        # не казалось, что клик не сработал.
        self.trial_button.configure(state="disabled", text="⏳...")

        def _worker():
            res = get_free_trial()

            def _upd():
                if res.get("success"):
                    messagebox.showinfo("Hunter", res.get("message"))
                else:
                    messagebox.showerror("Hunter", res.get("message") or "Ошибка сервера")
                    self.trial_button.configure(state="normal",
                                                text=LANGS[self.current_lang]["get_trial"])
                self.update_license_info()
            self.after(0, _upd)
        threading.Thread(target=_worker, daemon=True).start()


    # ── ROY методы ───────────────────────────────────────────────────────────

    def setup_roy_tab(self):
        self._roy_enabled_var = ctk.BooleanVar(value=self._load_gui_config().get("roy_enabled", False))
        self._roy_pool_known_ids: set = set()  # (kingdom, x, y) — уже виденные координаты
        self._pool_countdown_labels: list = []  # [(CTkLabel, expires_ts), ...] — для тикера
        self._pool_countdown_running: bool = False
        self._start_roy_sse_listener()
        L = LANGS[self.current_lang]

        self._roy_title_lb = ctk.CTkLabel(
            self.tab_roy,
            text=L['roy_title'],
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=MD3["primary"],
        )
        self._roy_title_lb.pack(pady=(16, 4))

        self._roy_subtitle_lb = ctk.CTkLabel(
            self.tab_roy,
            text=L['roy_subtitle'],
            font=ctk.CTkFont(size=11),
            text_color=MD3["on_surface2"],
        )
        self._roy_subtitle_lb.pack(pady=(0, 8))

        # ─── Торговые Пути — таймер события ─────────────────────────────────────
        _tr_roy_card = ctk.CTkFrame(self.tab_roy, fg_color=MD3["elevated"], corner_radius=10)
        _tr_roy_card.pack(fill="x", padx=20, pady=(0, 6))
        self._tr_roy_title_lb = ctk.CTkLabel(
            _tr_roy_card, text=f"⏰ {LANGS[self.current_lang].get('tr_event', 'Trade Routes')}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=MD3["on_surface2"],
        )
        self._tr_roy_title_lb.pack(pady=(6, 2))
        self._tr_roy_label = ctk.CTkLabel(
            _tr_roy_card, text="...",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4ADE80",
        )
        self._tr_roy_label.pack(pady=(0, 8))

        # ─── Кнопки управления поиском (дубль вкладки Биржи) ─────────────────────
        self._roy_hunt_btn = ctk.CTkButton(
            self.tab_roy,
            text=LANGS[self.current_lang]["start"],
            height=44, font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"], corner_radius=12,
            command=self.toggle_bot,
        )
        self._roy_hunt_btn.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkFrame(self.tab_roy, height=1, fg_color=MD3["outline"]).pack(
            fill="x", padx=20, pady=(0, 6))

        bal_card = ctk.CTkFrame(self.tab_roy, fg_color=MD3["elevated"], corner_radius=10)
        bal_card.pack(fill="x", padx=20, pady=(0, 10))
        self._roy_balance_title_lb = ctk.CTkLabel(bal_card, text=L['roy_balance_title'],
                     font=ctk.CTkFont(size=11), text_color=MD3["on_surface2"])
        self._roy_balance_title_lb.pack(pady=(8, 2))
        self._roy_balance_lb = ctk.CTkLabel(
            bal_card, text="— мин",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=MD3["primary"],
        )
        self._roy_balance_lb.pack(pady=(0, 8))

        toggle_row = ctk.CTkFrame(self.tab_roy, fg_color="transparent")
        toggle_row.pack(fill="x", padx=20, pady=(0, 8))
        self._roy_join_lb = ctk.CTkLabel(toggle_row, text=L['roy_join'],
                     font=ctk.CTkFont(size=13))
        self._roy_join_lb.pack(side="left")
        self._roy_switch = ctk.CTkSwitch(
            toggle_row, text="", variable=self._roy_enabled_var,
            onvalue=True, offvalue=False,
            command=self._on_roy_toggle,
            fg_color=MD3["outline"], progress_color=MD3["primary"],
        )
        self._roy_switch.pack(side="right")

        # ─── Номер Королевства ───────────────────────────────────────────────
        kingdom_row = ctk.CTkFrame(self.tab_roy, fg_color=MD3["elevated"], corner_radius=8)
        kingdom_row.pack(fill="x", padx=20, pady=(0, 8))
        self._roy_kingdom_lb = ctk.CTkLabel(kingdom_row, text=L['roy_kingdom_label'],
                     font=ctk.CTkFont(size=12),
                     text_color=MD3["on_surface2"])
        self._roy_kingdom_lb.pack(side="left", padx=(12, 8))
        self._roy_kingdom_entry = ctk.CTkEntry(
            kingdom_row, width=80, height=28,
            placeholder_text="233",
            justify="center",
            fg_color=MD3["card"], border_color=MD3["outline"],
        )
        self._roy_kingdom_entry.pack(side="left", padx=(0, 4), pady=6)
        saved_k = self._load_gui_config().get("roy_kingdom", 0)
        if saved_k:
            self._roy_kingdom_entry.insert(0, str(saved_k))
        self._roy_kingdom_entry.bind("<Return>", self._on_roy_kingdom_change)
        self._roy_kingdom_entry.bind("<FocusOut>", self._on_roy_kingdom_change)
        self._roy_kingdom_confirm_btn = ctk.CTkButton(
            kingdom_row, text="✓", width=28, height=28,
            corner_radius=6,
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"],
            command=self._on_roy_kingdom_change,
        )
        self._roy_kingdom_confirm_btn.pack(side="left", padx=(0, 8), pady=6)

        ctk.CTkFrame(self.tab_roy, height=1, fg_color=MD3["outline"]).pack(
            fill="x", padx=20, pady=(4, 8))

        self._roy_coords_lb = ctk.CTkLabel(
            self.tab_roy, text=L['roy_coords_title'],
            font=ctk.CTkFont(size=11), text_color=MD3["on_surface2"],
        )
        self._roy_coords_lb.pack(anchor="w", padx=22)

        self._roy_list_frame = ctk.CTkScrollableFrame(
            self.tab_roy, height=400, fg_color=MD3["elevated"], corner_radius=8,
        )
        self._roy_list_frame.pack(fill="x", padx=20, pady=(4, 8))


        self._roy_status_lb = ctk.CTkLabel(
            self.tab_roy, text="",
            font=ctk.CTkFont(size=10), text_color=MD3["on_surface2"],
        )
        self._roy_status_lb.pack(pady=(0, 4))

        # ТЕСТ (закомментирован — раскомментировать для визуальной проверки):
        # from datetime import datetime, timezone, timedelta as _td
        # _now = datetime.now(timezone.utc)
        # def _ago(m): return (_now - _td(minutes=m)).isoformat()
        # self._roy_update_list([
        #     {"kingdom": 471, "x": 383, "y": 812, "percent":  7, "updated_at": _ago(1)},
        #     {"kingdom": 471, "x": 512, "y": 340, "percent": 33, "updated_at": _ago(3)},
        #     {"kingdom": 471, "x": 198, "y": 655, "percent": 15, "updated_at": _ago(5)},
        #     {"kingdom": 471, "x": 820, "y": 120, "percent": 42, "updated_at": _ago(8)},
        #     {"kingdom": 471, "x": 401, "y": 900, "percent": 61, "updated_at": _ago(11)},
        #     {"kingdom": 205, "x": 711, "y": 199, "percent": 78, "updated_at": _ago(13)},
        #     {"kingdom": 205, "x": 300, "y": 450, "percent": 12, "updated_at": _ago(15)},
        #     {"kingdom": 205, "x": 555, "y": 700, "percent": 55, "updated_at": _ago(17)},
        #     {"kingdom": 317, "x": 100, "y": 250, "percent":  3, "updated_at": _ago(18)},
        #     {"kingdom": 317, "x": 440, "y": 380, "percent": 88, "updated_at": _ago(19)},
        # ])

        self._roy_no_data_lb = ctk.CTkLabel(
            self._roy_list_frame,
            text=L['roy_no_data'],
            font=ctk.CTkFont(size=11), text_color=MD3["on_surface2"],
        )
        self._roy_no_data_lb.pack(pady=20)
        self._roy_placeholder_key = 'roy_no_data'

        if self._roy_enabled_var.get():
            self.after(1500, self._roy_refresh_balance)
            self.after(2000, self._roy_refresh_pool)  # загрузить пул при старте

    # ╔══════════════════════════════════════════════════════════════════════╗
    # ║  ⚙️  ИВЕНТ «ТОРГОВЫЕ ПУТИ» — МЕНЯЙ ЗДЕСЬ (клиент)               ║
    # ║  Должен совпадать с server/roy.py                                  ║
    # ║  Старт: 2026-06-01 20:00 Киев = 17:00 UTC                         ║
    # ║  Цикл: [━ ИВЕНТ 24ч ━][━━━━━ ПАУЗА 120ч ━━━━━] = 144ч (6 дней)  ║
    # ╚══════════════════════════════════════════════════════════════════════╝
    _TR_ANCHOR_TS  = 1780333200   # ← МЕНЯЙ: unix-timestamp ближайшего старта (UTC)
    _TR_CYCLE_H    = 144          # ← МЕНЯЙ: полный период (24ч ивент + 120ч пауза)
    _TR_DURATION_H = 24           # ← МЕНЯЙ: длительность ивента в часах

    @staticmethod
    def _is_event_active() -> tuple:
        """
        Возвращает (active: bool, secs_left: int).
        secs_left = секунд до конца ивента (если active=True)
                  = секунд до начала следующего (если active=False).
        """
        import time as _t
        cycle_sec    = TotalHunterApp._TR_CYCLE_H    * 3600
        duration_sec = TotalHunterApp._TR_DURATION_H * 3600
        offset       = (_t.time() - TotalHunterApp._TR_ANCHOR_TS) % cycle_sec
        if offset < duration_sec:
            return True,  int(duration_sec - offset)
        else:
            return False, int(cycle_sec - offset)

    def _update_trade_routes_labels(self):
        """Таймер ивента «Торговые Пути» — 5-дневный цикл, расчёт на клиенте."""
        active, secs = self._is_event_active()
        L  = LANGS[self.current_lang]
        h  = secs // 3600
        m  = (secs % 3600) // 60

        if active:
            txt   = f"{L.get('tr_ends_in', '🟢 ИДЁТ — до конца:')} {h}ч {m:02d}мин"
            color = "#4ADE80"
        else:
            txt   = f"{L.get('tr_starts_in', 'до начала:')} {h}ч {m:02d}мин"
            color = MD3["on_surface2"]

        if hasattr(self, '_tr_hunt_label'):
            self._tr_hunt_label.configure(text=txt, text_color=color)
        if hasattr(self, '_tr_roy_label'):
            self._tr_roy_label.configure(text=txt, text_color=color)
        if hasattr(self, 'engine') and self.engine:
            self.engine.event_active = active
        self._update_roy_indicator()

    def _tick_trade_routes(self):
        """Повторяющийся тик каждую минуту."""
        self._update_trade_routes_labels()
        self.after(60_000, self._tick_trade_routes)

    def _tick_roy_drain(self):
        """Повторяющийся тик каждую минуту: списывает баланс за простой РОЙ.

        Простой = тумблер РОЙ включён, но поиск бирж не идёт (is_running=False).
        Списание выполняется на сервере (POST /roy/idle); здесь только условие запуска.
        Дополнительное условие: игрок должен быть на вкладке БИРЖИ или РОЙ.
        """
        if (hasattr(self, '_roy_enabled_var') and self._roy_enabled_var.get()
                and not self.is_running and self.engine.event_active):
            def _send():
                try:
                    from roy.roy_client import RoyClient
                    from auth import get_hwid
                    if RoyClient(get_hwid()).idle():
                        self._roy_refresh_balance()
                except Exception:
                    pass
            threading.Thread(target=_send, daemon=True).start()
        self.after(60_000, self._tick_roy_drain)

    def _update_roy_indicator(self):
        """Показывает/скрывает жёлтый индикатор активного РОЙ в панели навигации.
        Индикатор виден на ВСЕХ вкладках — чтобы игрок не забыл про расход баланса."""
        if not hasattr(self, '_roy_indicator_lb'):
            return
        active = (hasattr(self, '_roy_enabled_var') and self._roy_enabled_var.get()
                  and hasattr(self, 'engine') and self.engine.event_active)
        if active:
            self._roy_indicator_lb.grid(row=2, column=0, columnspan=4, sticky="ew",
                                        padx=8, pady=(0, 4))
        else:
            self._roy_indicator_lb.grid_remove()

    def _on_roy_toggle(self):
        enabled = self._roy_enabled_var.get()
        self._save_gui_config_key("roy_enabled", enabled)
        if hasattr(self, 'engine') and self.engine:
            self.engine.roy_enabled = enabled
        if enabled:
            self._roy_refresh_balance()
            self._roy_refresh_pool()
        else:
            self._roy_update_list([])  # скрыть координаты при отключении
        self._update_roy_indicator()

    def _on_roy_kingdom_change(self, event=None):
        try:
            val = int(self._roy_kingdom_entry.get())
            self._save_gui_config_key("roy_kingdom", val)
            from roy.roy_client import RoyClient
            from auth import get_hwid
            threading.Thread(
                target=lambda: RoyClient(hwid=get_hwid()).register(val),
                daemon=True,
            ).start()
        except (ValueError, AttributeError):
            pass

    def _get_roy_kingdom(self) -> int:
        try:
            return int(self._roy_kingdom_entry.get())
        except (ValueError, AttributeError):
            return 0

    def _roy_refresh_balance(self):
        """Обновляет баланс времени с сервера."""
        L = LANGS[self.current_lang]
        def _fetch():
            try:
                from roy.roy_client import RoyClient
                from auth import get_hwid
                client = RoyClient(get_hwid())
                bal = client.get_balance()
                mins = bal // 60
                secs = bal % 60
                text = f"{mins}:{secs:02d} {L['unit_min']}" if mins > 0 else f"{secs} {L['unit_sec']}"
                color = "#4ADE80" if bal > 300 else ("#FACC15" if bal > 60 else "#F87171")
                self.after(0, lambda: self._roy_balance_lb.configure(text=text, text_color=color))
            except Exception:
                self.after(0, lambda: self._roy_balance_lb.configure(text="—"))
        threading.Thread(target=_fetch, daemon=True).start()


    def _start_roy_sse_listener(self):
        """Daemon-тред: слушает SSE сервера. При pool_updated — звук + обновление пула.
        Работает на любой вкладке пока тумблер РОЙ включён и ивент активен.
        """
        import json as _json
        def _loop():
            import requests as _req, time as _t
            url = "https://api.total-hunter.com/roy/status-stream"
            while True:
                try:
                    with _req.get(url, stream=True, timeout=70) as r:
                        for raw in r.iter_lines(decode_unicode=True):
                            if raw.startswith('data:'):
                                try:
                                    data = _json.loads(raw[5:].strip())
                                    if (data.get('pool_updated')
                                            and self._roy_enabled_var.get()
                                            and self.engine.event_active):
                                        self.after(0, self._roy_refresh_pool)
                                except Exception:
                                    pass
                except Exception:
                    _t.sleep(5)
        threading.Thread(target=_loop, daemon=True).start()

    def _roy_refresh_pool(self):
        """Загружает список координат из пула Роя и обновляет список."""
        if not self._roy_enabled_var.get():
            return
        err_label = LANGS[self.current_lang]['roy_error']
        def _fetch():
            try:
                from roy.roy_client import RoyClient
                from auth import get_hwid
                client = RoyClient(get_hwid())
                pool = client.get_pool(consume=False)
                self.after(0, lambda: self._roy_update_list(pool))
            except Exception as e:
                self.after(0, lambda: self._roy_status_lb.configure(text=f"{err_label}: {e}"))
        threading.Thread(target=_fetch, daemon=True).start()


    def _roy_update_list(self, pool: list):
        """Перерисовывает список координат в ScrollableFrame."""
        L = LANGS[self.current_lang]
        # Звук если появились новые координаты которых раньше не было — но не наши собственные
        new_ids = {(e.get('kingdom'), e.get('x'), e.get('y')) for e in pool}
        truly_new = (new_ids - self._roy_pool_known_ids) - getattr(self, '_roy_self_reported', set())
        if truly_new and self._roy_enabled_var.get():
            _sound = getattr(self.engine, 'sound_path', None) if hasattr(self, 'engine') and self.engine else None
            try:
                import winsound
                if _sound:
                    winsound.PlaySound(_sound, winsound.SND_FILENAME | winsound.SND_ASYNC)
                else:
                    winsound.Beep(1000, 400)
            except Exception:
                pass
        self._roy_pool_known_ids = new_ids

        for w in self._roy_list_frame.winfo_children():
            w.destroy()
        # winfo_children().destroy() above also kills any placeholder label
        # created here or in setup_roy_tab — drop the stale reference so
        # change_lang() doesn't later try to .configure() a dead Tk widget.
        self._roy_no_data_lb = None

        if not pool:
            self._roy_no_data_lb = ctk.CTkLabel(
                self._roy_list_frame,
                text=L['roy_empty_pool'],
                font=ctk.CTkFont(size=11), text_color=MD3["on_surface2"],
            )
            self._roy_no_data_lb.pack(pady=20)
            self._roy_placeholder_key = 'roy_empty_pool'
            self._roy_status_lb.configure(text=L['roy_pool_empty'])
            return

        self._roy_status_lb.configure(text=f"{L['roy_pool_count']}: {len(pool)}")
        from datetime import datetime, timezone, timedelta

        # Сортировка: свежие (маленький elapsed) сверху
        def _elapsed_sec(e):
            try:
                upd = datetime.fromisoformat(e.get('updated_at', ''))
                return (datetime.now(timezone.utc) - upd).total_seconds()
            except Exception:
                return 9999
        pool = sorted(pool, key=_elapsed_sec)

        import time as _t
        _now_ts = _t.time()
        # POOL_TTL_MIN=20 мин (совпадает с server/roy.py)
        _POOL_TTL_SEC = 20 * 60

        # Сбрасываем список меток (тикер подхватит новые виджеты)
        self._pool_countdown_labels.clear()

        for entry in pool:
            row = ctk.CTkFrame(self._roy_list_frame, fg_color=MD3["card"], corner_radius=6)
            row.pack(fill="x", padx=4, pady=2)
            pct = entry.get('percent', 0)
            pct_color = "#4ADE80" if pct < 50 else ("#FACC15" if pct < 80 else "#F87171")

            # Возраст: сколько ПРОШЛО с момента нахождения биржи (0:00 → 20:00)
            updated_raw = entry.get('updated_at')
            updated_ts  = None
            if updated_raw:
                try:
                    upd = datetime.fromisoformat(updated_raw)
                    updated_ts = upd.timestamp()
                    elapsed = min(_POOL_TTL_SEC, int(_now_ts - updated_ts))
                    mm, ss = elapsed // 60, elapsed % 60
                    timer_text  = f"⏱ {mm:02d}:{ss:02d}"
                    timer_color = "#4ADE80" if elapsed < 600 else ("#FACC15" if elapsed < 900 else "#F87171")
                except Exception:
                    timer_text, timer_color = "⏱ --:--", MD3["on_surface2"]
            else:
                timer_text, timer_color = "⏱ --:--", MD3["on_surface2"]

            # Королевство — жирный, золотой (без слова ГОС)
            ctk.CTkLabel(
                row,
                text=str(entry['kingdom']),
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#F0C070",
            ).pack(side="left", padx=(10, 6), pady=5)
            # Координаты
            ctk.CTkLabel(
                row,
                text=f"X:{entry['x']}  Y:{entry['y']}",
                font=ctk.CTkFont(size=12),
                text_color=MD3["on_surface"],
            ).pack(side="left", padx=(0, 4), pady=5)
            # Таймер — обратный отсчёт MM:SS (живёт через _tick_pool_countdown)
            timer_lb = ctk.CTkLabel(
                row, text=timer_text,
                font=ctk.CTkFont(size=11),
                text_color=timer_color,
            )
            timer_lb.pack(side="right", padx=6)
            if updated_ts is not None:
                self._pool_countdown_labels.append((timer_lb, updated_ts))
            # Процент
            ctk.CTkLabel(
                row, text=f"{pct}%",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=pct_color,
            ).pack(side="right", padx=(6, 2))

        # Запустить тикер, если ещё не запущен
        if self._pool_countdown_labels and not self._pool_countdown_running:
            self._pool_countdown_running = True
            self.after(1000, self._tick_pool_countdown)

    def _tick_pool_countdown(self):
        """Секундный тикер: обновляет MM:SS в строках пула без перезагрузки сервера."""
        import time as _t
        now = _t.time()
        _POOL_TTL_SEC = 20 * 60
        for (label, updated_ts) in self._pool_countdown_labels:
            try:
                elapsed = min(_POOL_TTL_SEC, int(now - updated_ts))
                mm, ss = elapsed // 60, elapsed % 60
                color = ("#4ADE80" if elapsed < 600 else
                         "#FACC15" if elapsed < 900 else
                         "#F87171")
                label.configure(text=f"⏱ {mm:02d}:{ss:02d}", text_color=color)
            except Exception:
                pass  # виджет уничтожен при refresh — пропускаем

        if self._pool_countdown_labels:
            # Если хоть одна запись истекла — обновить список с сервера (он уже отфильтрован)
            if any((now - ts) >= _POOL_TTL_SEC for (_, ts) in self._pool_countdown_labels):
                self._pool_countdown_labels.clear()
                self._pool_countdown_running = False
                self._roy_refresh_pool()
                return
            self.after(1000, self._tick_pool_countdown)
        else:
            self._pool_countdown_running = False

    def change_lang(self, val):
        old_val = self.current_lang
        code = LANG_BY_LABEL.get(val, val)  # "🇷🇺 RU" → "RU", или уже код (backward compat)
        self.current_lang = code
        val = code
        self._save_gui_config_key("lang", code)
        self.label_title.configure(text=LANGS[val]["title"])
        self.acc_lb.configure(text=LANGS[val]["accuracy"])
        self.start_button.configure(text=LANGS[val]["start"] if not self.is_running else LANGS[val]["stop"])
        self.ref_title_lb.configure(text=LANGS[val]["ref_title"])
        self.share_lb.configure(text=LANGS[val]["share_text"])
        self.status_label.configure(text=LANGS[val]["status_ready"] if not self.is_running else LANGS[val]["status_running"])

        # Статичные i18n лейблы
        for widget, key in self._i18n_labels:
            widget.configure(text=LANGS[val].get(key, LANGS["EN"].get(key, key)))

        # Навигация — обновляем оба ряда вкладок
        new_names = {k: LANGS[val][k] for k in ("tab_crypt", "tab_hunt", "tab_roy", "tab_ref")}
        self._tab_init_names = new_names
        self._main_seg.configure(values=list(new_names.values()))
        new_names2 = {k: LANGS[val][k] for k in ("tab_chest", "tab_ancient", "tab_cal")}
        self._tab2_init_names = new_names2
        self._main_seg2.configure(values=list(new_names2.values()))
        if self._cal_visible:
            self._main_seg.set("")
            self._main_seg2.set(new_names2["tab_cal"])
        elif self._active_tab_key in new_names:
            self._main_seg.set(new_names[self._active_tab_key])
            self._main_seg2.set("")
        else:
            self._main_seg.set("")
            self._main_seg2.set(new_names2.get(self._active_tab_key, ""))

        # Таймер Торговых Путей — заголовки и текст
        _tr_name = f"⏰ {LANGS[val].get('tr_event', 'Trade Routes')}"
        if hasattr(self, '_tr_hunt_title_lb'):
            self._tr_hunt_title_lb.configure(text=_tr_name)
        if hasattr(self, '_tr_roy_title_lb'):
            self._tr_roy_title_lb.configure(text=_tr_name)
        self._update_trade_routes_labels()

        # ROY hunt button
        if hasattr(self, '_roy_hunt_btn'):
            self._roy_hunt_btn.configure(
                text=LANGS[val]["stop"] if self.is_running else LANGS[val]["start"]
            )

        # ROY static labels
        if hasattr(self, '_roy_title_lb'):
            self._roy_title_lb.configure(text=LANGS[val]['roy_title'])
        if hasattr(self, '_roy_subtitle_lb'):
            self._roy_subtitle_lb.configure(text=LANGS[val]['roy_subtitle'])
        if hasattr(self, '_roy_balance_title_lb'):
            self._roy_balance_title_lb.configure(text=LANGS[val]['roy_balance_title'])
        if hasattr(self, '_roy_join_lb'):
            self._roy_join_lb.configure(text=LANGS[val]['roy_join'])
        if hasattr(self, '_roy_kingdom_lb'):
            self._roy_kingdom_lb.configure(text=LANGS[val]['roy_kingdom_label'])
        if hasattr(self, '_roy_coords_lb'):
            self._roy_coords_lb.configure(text=LANGS[val]['roy_coords_title'])
        if getattr(self, '_roy_no_data_lb', None) is not None:
            self._roy_no_data_lb.configure(text=LANGS[val][self._roy_placeholder_key])
        # Перезапросить баланс чтобы единицы времени обновились
        if hasattr(self, '_roy_enabled_var') and self._roy_enabled_var.get():
            self._roy_refresh_balance()

        # crypt_start_btn — только если бот не запущен
        if not self.is_crypt_running:
            self.crypt_start_btn.configure(text=LANGS[val]["crypt_start"])
            self.crypt_status_label.configure(text=LANGS[val]["crypt_ready"])

        # Calibration point labels
        for pt_lb, pt_desc_lb, lb_key, desc_key in getattr(self, '_cal_point_label_widgets', []):
            pt_lb.configure(text=LANGS[val][lb_key])
            pt_desc_lb.configure(text=LANGS[val][desc_key])

        # Tune option menu — перестроить labels, сохранить выбранный индекс
        if hasattr(self, '_tune_option_menu'):
            _tko = TUNE_TARGET_NAMES
            _new_vals = [LANGS[val]["tab_cal"]] + [LANGS[val][f"cal_tune_{k}"] for k in _tko]
            self._tune_option_menu.configure(values=_new_vals)
            _idx = getattr(self, '_tune_idx', -1)
            if _idx < 0:
                self._ui_tune_btn_var.set(_new_vals[0])
            else:
                self._ui_tune_btn_var.set(_new_vals[_idx + 1])

        self.update_slider_labels()
        self._update_nav_labels()
        self._update_crypt_labels()
        self.update_license_info()

    def _on_theme_change(self, name: str) -> None:
        self._save_gui_config_key("theme", name)
        self.theme_restart_label.configure(text="↻ restart")
        self.after(3000, lambda: self.theme_restart_label.configure(text=""))

    # ── helpers ─────────────────────────────────────────────────────────────

    def _load_gui_config(self) -> dict:
        if os.path.exists(GUI_CONFIG_PATH):
            with open(GUI_CONFIG_PATH, "r") as f:
                return json.load(f)
        return {}

    def _save_gui_config_key(self, key: str, value) -> None:
        cfg = self._load_gui_config()
        cfg[key] = value
        with open(GUI_CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)

    def _save_dialog_profile(self):
        """Сохраняет dialog_offset_y в выбранный профиль калибровки."""
        coord_manager.dialog_offset_y = self._dialog_offset_y_var.get()
        profile_name = self._cal_profile_var.get()
        path = self._PROFILES[profile_name]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        coord_manager.save(path)
        self._save_gui_config_key("last_calibration_profile", profile_name)

    def _chest_pause_range(self, slider_value: float) -> tuple:
        """Owner-confirmed: floor removed (2026-06-25) — real pause is always
        0.3+ s from OCR processing time, so additional 0 s slider is safe."""
        lower = max(0.0, slider_value - 0.1)
        return (lower, lower + 0.2)

    def setup_chest_tab(self):
        L = LANGS[self.current_lang]

        title_lb = ctk.CTkLabel(self.tab_chest, text=L["tab_chest"],
                                font=ctk.CTkFont(size=20, weight="bold"),
                                text_color=MD3["primary"])
        title_lb.pack(pady=(14, 8))
        self._i18n_labels.append((title_lb, "tab_chest"))

        # ── Королевство / Клан ────────────────────────────────────────────
        id_card = ctk.CTkFrame(self.tab_chest, fg_color=MD3["elevated"],
                               corner_radius=12, border_width=1,
                               border_color=MD3["outline"])
        id_card.pack(padx=20, pady=(0, 8), fill="x")

        kingdom_row = ctk.CTkFrame(id_card, fg_color="transparent")
        kingdom_row.pack(padx=10, pady=(10, 4), fill="x")
        self.chest_kingdom_lb = ctk.CTkLabel(kingdom_row, text=L["chest_kingdom_lb"],
                                             font=ctk.CTkFont(size=12),
                                             text_color=MD3["on_surface2"])
        self.chest_kingdom_lb.pack(side="left", padx=(0, 8))
        self._i18n_labels.append((self.chest_kingdom_lb, "chest_kingdom_lb"))
        self.chest_kingdom_entry = ctk.CTkEntry(kingdom_row, width=120)
        self.chest_kingdom_entry.pack(side="left")
        saved_kingdom = self._load_gui_config().get("chest_kingdom", "")
        if saved_kingdom:
            self.chest_kingdom_entry.insert(0, saved_kingdom)
        self.chest_kingdom_entry.bind("<FocusOut>", self._on_chest_kingdom_change)

        clan_row = ctk.CTkFrame(id_card, fg_color="transparent")
        clan_row.pack(padx=10, pady=(4, 10), fill="x")
        self.chest_clan_lb = ctk.CTkLabel(clan_row, text=L["chest_clan_lb"],
                                          font=ctk.CTkFont(size=12),
                                          text_color=MD3["on_surface2"])
        self.chest_clan_lb.pack(side="left", padx=(0, 8))
        self._i18n_labels.append((self.chest_clan_lb, "chest_clan_lb"))
        self.chest_clan_entry = ctk.CTkEntry(clan_row, width=160)
        self.chest_clan_entry.pack(side="left")
        saved_clan = self._load_gui_config().get("chest_clan", "")
        if saved_clan:
            self.chest_clan_entry.insert(0, saved_clan)
        self.chest_clan_entry.bind("<FocusOut>", self._on_chest_clan_change)

        # ── Отправить на сервер ──────────────────────────────────────────
        self.chest_send_btn = ctk.CTkButton(
            self.tab_chest, text=L["chest_send_btn"],
            height=38, corner_radius=10,
            fg_color=MD3["blue_btn"], hover_color=MD3["blue_hover"],
            text_color=MD3["on_surface"], font=ctk.CTkFont(size=13, weight="bold"),
            command=self.send_chests_to_server)
        self.chest_send_btn.pack(padx=20, pady=(4, 4), fill="x")
        self._i18n_labels.append((self.chest_send_btn, "chest_send_btn"))

        self.chest_status_label = ctk.CTkLabel(self.tab_chest, text=L["chest_status_ready"],
                                               font=ctk.CTkFont(size=12),
                                               text_color=MD3["on_surface2"])
        self.chest_status_label.pack(pady=(0, 8))
        self._i18n_labels.append((self.chest_status_label, "chest_status_ready"))

        # ── Live-счётчик по типам — фиксированная высота, список скроллится
        # внутри своих границ и не выталкивает СТАРТ ниже ──────────────────
        counts_card = ctk.CTkFrame(self.tab_chest, fg_color=MD3["elevated"],
                                   corner_radius=12, border_width=1,
                                   border_color=MD3["outline"])
        counts_card.pack(padx=20, pady=(0, 8), fill="both", expand=True)
        self.chest_counts_frame = ctk.CTkScrollableFrame(
            counts_card, fg_color="transparent", height=260)
        self.chest_counts_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.chest_total_label = ctk.CTkLabel(counts_card, text=f"{L['chest_total_lb']} 0",
                                              font=ctk.CTkFont(size=13, weight="bold"),
                                              text_color=MD3["value_text"])
        self.chest_total_label.pack(pady=(0, 10))

        # ── Скорость клика — ползунок анти-детект паузы, над СТАРТ ───────
        saved_pause = self._load_gui_config().get("chest_click_pause", 0.22)
        self.chest_speed_label = ctk.CTkLabel(
            self.tab_chest, text=f"{L['chest_speed_lb']} {saved_pause:.2f} {L['sec']}",
            font=ctk.CTkFont(size=11), text_color=MD3["on_surface2"])
        self.chest_speed_label.pack(padx=20, pady=(0, 2))
        self.chest_speed_slider = ctk.CTkSlider(
            self.tab_chest, from_=0.0, to=1.0, number_of_steps=100,
            command=self._on_chest_speed_change)
        self.chest_speed_slider.set(saved_pause)
        self.chest_speed_slider.pack(padx=20, pady=(0, 8), fill="x")

        # ── Light/Full — переключатель набора языков OCR имени игрока ────
        saved_full_lang = self._load_gui_config().get("chest_full_lang_ocr", False)
        self.chest_full_lang_var = ctk.BooleanVar(value=saved_full_lang)
        lang_toggle_row = ctk.CTkFrame(self.tab_chest, fg_color="transparent")
        lang_toggle_row.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(lang_toggle_row, text="Light", font=ctk.CTkFont(size=12)).pack(side="left")
        self.chest_full_lang_switch = ctk.CTkSwitch(
            lang_toggle_row, text="Full", variable=self.chest_full_lang_var,
            onvalue=True, offvalue=False,
            command=self._on_chest_full_lang_change,
            fg_color=MD3["outline"], progress_color=MD3["primary"],
        )
        self.chest_full_lang_switch.pack(side="right")

        # ── Старт/Стоп — внизу, всегда после счётчика ────────────────────
        self.chest_start_btn = ctk.CTkButton(
            self.tab_chest, text=L["chest_start_btn"],
            height=42, corner_radius=10,
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"], font=ctk.CTkFont(size=14, weight="bold"),
            command=self.toggle_chest_bot)
        self.chest_start_btn.pack(padx=20, pady=(4, 14), fill="x")
        self._i18n_labels.append((self.chest_start_btn, "chest_start_btn"))

        # ── Показать текущий невыгруженный остаток сразу при открытии вкладки,
        # без этого счётчик после перезапуска бота врал бы нулём ───────────
        try:
            import chest_reader
            conn = chest_reader.init_db()
            self._update_chest_counts_display(chest_reader.get_unsynced_counts(conn))
            conn.close()
        except Exception:
            pass

    def _on_chest_kingdom_change(self, event=None):
        self._save_gui_config_key("chest_kingdom", self.chest_kingdom_entry.get().strip())

    def _on_chest_clan_change(self, event=None):
        self._save_gui_config_key("chest_clan", self.chest_clan_entry.get().strip())

    def _on_chest_speed_change(self, value):
        L = LANGS[self.current_lang]
        self._save_gui_config_key("chest_click_pause", round(float(value), 2))
        self.chest_speed_label.configure(text=f"{L['chest_speed_lb']} {float(value):.2f} {L['sec']}")

    def _on_chest_full_lang_change(self):
        self._save_gui_config_key("chest_full_lang_ocr", bool(self.chest_full_lang_var.get()))

    # ── ancient tab (tournament roster import) ──────────────────────────────

    def setup_ancient_tab(self):
        L = LANGS[self.current_lang]

        title_lb = ctk.CTkLabel(self.tab_ancient, text=L["tab_ancient"],
                                font=ctk.CTkFont(size=20, weight="bold"),
                                text_color=MD3["primary"])
        title_lb.pack(pady=(14, 8))
        self._i18n_labels.append((title_lb, "tab_ancient"))

        desc_lb = ctk.CTkLabel(
            self.tab_ancient, text=L["ancient_desc"],
            font=ctk.CTkFont(size=12), text_color=MD3["on_surface2"], wraplength=380)
        desc_lb.pack(pady=(0, 12), padx=20)
        self._i18n_labels.append((desc_lb, "ancient_desc"))

        row_ak = ctk.CTkFrame(self.tab_ancient, fg_color="transparent")
        row_ak.pack(fill="x", padx=20, pady=(0, 4))
        lb_ak = ctk.CTkLabel(row_ak, text=L.get("chest_kingdom_lb", "Kingdom:"),
                              width=130, anchor="w", font=ctk.CTkFont(size=13))
        lb_ak.pack(side="left")
        self.ancient_kingdom_entry = ctk.CTkEntry(row_ak, height=32, corner_radius=8)
        self.ancient_kingdom_entry.pack(side="left", fill="x", expand=True)
        self._i18n_labels.append((lb_ak, "chest_kingdom_lb"))

        row_ac = ctk.CTkFrame(self.tab_ancient, fg_color="transparent")
        row_ac.pack(fill="x", padx=20, pady=(0, 8))
        lb_ac = ctk.CTkLabel(row_ac, text=L.get("chest_clan_lb", "Clan name:"),
                              width=130, anchor="w", font=ctk.CTkFont(size=13))
        lb_ac.pack(side="left")
        self.ancient_clan_entry = ctk.CTkEntry(row_ac, height=32, corner_radius=8)
        self.ancient_clan_entry.pack(side="left", fill="x", expand=True)
        self._i18n_labels.append((lb_ac, "chest_clan_lb"))

        saved_full_lang = self._load_gui_config().get("ancient_full_lang_ocr", False)
        self.ancient_full_lang_var = ctk.BooleanVar(value=saved_full_lang)
        ancient_lang_toggle_row = ctk.CTkFrame(self.tab_ancient, fg_color="transparent")
        ancient_lang_toggle_row.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(ancient_lang_toggle_row, text="Light", font=ctk.CTkFont(size=12)).pack(side="left")
        self.ancient_full_lang_switch = ctk.CTkSwitch(
            ancient_lang_toggle_row, text="Full", variable=self.ancient_full_lang_var,
            onvalue=True, offvalue=False,
            command=self._on_ancient_full_lang_change,
            fg_color=MD3["outline"], progress_color=MD3["primary"],
        )
        self.ancient_full_lang_switch.pack(side="right")

        self.ancient_start_btn = ctk.CTkButton(
            self.tab_ancient, text=L["chest_start_btn"],
            height=42, corner_radius=10,
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"], font=ctk.CTkFont(size=14, weight="bold"),
            command=self.toggle_ancient_collection)
        self.ancient_start_btn.pack(padx=20, pady=(4, 8), fill="x")
        self._i18n_labels.append((self.ancient_start_btn, "chest_start_btn"))

        self.ancient_status_label = ctk.CTkLabel(self.tab_ancient, text=L["chest_status_ready"],
                                                 font=ctk.CTkFont(size=12),
                                                 text_color=MD3["on_surface2"])
        self.ancient_status_label.pack(pady=(0, 8))
        self._i18n_labels.append((self.ancient_status_label, "chest_status_ready"))

        self._ancient_running = False

    def _on_ancient_full_lang_change(self):
        self._save_gui_config_key("ancient_full_lang_ocr", bool(self.ancient_full_lang_var.get()))

    def toggle_ancient_collection(self):
        L = LANGS[self.current_lang]
        if self._ancient_running:
            self._ancient_stop_event.set()
            return

        kingdom = self.ancient_kingdom_entry.get().strip()
        clan = self.ancient_clan_entry.get().strip()
        if not kingdom or not clan:
            self.ancient_status_label.configure(text=L["chest_missing_fields"],
                                                text_color=MD3["error_text"])
            return

        self._ancient_running = True
        self._ancient_stop_event = threading.Event()
        full_lang = bool(self.ancient_full_lang_var.get())
        self.ancient_start_btn.configure(text=L["chest_stop_btn"],
                                         fg_color=MD3["error"], hover_color=MD3["error_hover"])
        self.ancient_status_label.configure(text=L["ancient_status_running"],
                                            text_color=MD3["secondary"])

        stop_event = self._ancient_stop_event

        def _worker():
            try:
                import tournament_reader
                data = tournament_reader.collect_tournament_data(
                    stop_flag=stop_event.is_set, full_lang=full_lang)
                timestamp = _dt.datetime.now().isoformat(timespec='seconds')
                success = tournament_reader.export_to_api(kingdom, clan, data, timestamp)
            except Exception as e:
                print(f"[ancient] ошибка: {e}")
                success = False
            self.after(0, lambda: self._on_ancient_collection_done(success))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_ancient_collection_done(self, success):
        L = LANGS[self.current_lang]
        self._ancient_running = False
        self.ancient_start_btn.configure(text=L["chest_start_btn"],
                                         fg_color=MD3["green_btn"], hover_color=MD3["green_hover"])
        if success:
            self.ancient_status_label.configure(text=L["ancient_status_sent"],
                                                text_color=MD3["secondary"])
        else:
            self.ancient_status_label.configure(text=L["ancient_status_failed"],
                                                text_color=MD3["error_text"])

    def _update_chest_counts_display(self, counts):
        if not hasattr(self, "_chest_count_labels"):
            self._chest_count_labels = {}
        total = 0
        for chest_type, n in counts.items():
            total += n
            if chest_type in self._chest_count_labels:
                self._chest_count_labels[chest_type].configure(text=f"{chest_type}: {n}")
            else:
                row_lb = ctk.CTkLabel(self.chest_counts_frame, text=f"{chest_type}: {n}",
                                      font=ctk.CTkFont(size=12), text_color=MD3["on_surface"])
                row_lb.pack(anchor="w", pady=1)
                self._chest_count_labels[chest_type] = row_lb
        for chest_type in list(self._chest_count_labels):
            if chest_type not in counts:
                self._chest_count_labels[chest_type].destroy()
                del self._chest_count_labels[chest_type]
        L = LANGS[self.current_lang]
        self.chest_total_label.configure(text=f"{L['chest_total_lb']} {total}")

    # ── calibration tab ─────────────────────────────────────────────────────

    def setup_calibration_tab(self):
        from PIL import Image
        PROFILES = self._PROFILES
        _assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

        _cal_title_lb = ctk.CTkLabel(
            self._cal_frame,
            text=LANGS[self.current_lang]["cal_title"],
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=MD3["on_surface"],
        )
        _cal_title_lb.pack(pady=(12, 2))
        self._i18n_labels.append((_cal_title_lb, "cal_title"))

        _cal_desc_lb = ctk.CTkLabel(
            self._cal_frame,
            text=LANGS[self.current_lang]["cal_desc"],
            font=ctk.CTkFont(size=12),
            text_color=MD3["on_surface2"],
            justify="center",
        )
        _cal_desc_lb.pack(pady=(0, 6))
        self._i18n_labels.append((_cal_desc_lb, "cal_desc"))

        # ── Область изображений — калибровка ↔ тюнинг ────────────────────
        # _img_area — обёртка; внутри переключаются два фрейма пак/забытьпак
        _img_area = ctk.CTkFrame(self._cal_frame, fg_color="transparent")
        _img_area.pack(fill="x", padx=16, pady=(0, 6))

        # Фрейм с 2-мя скринами калибровки (показывается по умолчанию)
        _cal_imgs_frame = ctk.CTkFrame(_img_area, fg_color="transparent")
        _cal_imgs_frame.pack(fill="x")

        if not hasattr(self, '_cal_images'):
            self._cal_images = []
        self._cal_point_label_widgets = []
        for col, (fname, pt_label_key, pt_desc_key, color) in enumerate([
            ("calib_point_a.png", "cal_pt_a_lb", "cal_pt_a_desc", MD3["primary"]),
            ("calib_point_b.png", "cal_pt_b_lb", "cal_pt_b_desc", "#B060FF"),
        ]):
            card = ctk.CTkFrame(_cal_imgs_frame, fg_color=MD3["elevated"],
                                corner_radius=10, border_width=1,
                                border_color=MD3["outline"])
            card.grid(row=0, column=col, padx=(0, 6) if col == 0 else (6, 0), sticky="nsew")
            _cal_imgs_frame.grid_columnconfigure(col, weight=1)

            pt_lb = ctk.CTkLabel(card, text=LANGS[self.current_lang][pt_label_key],
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=color)
            pt_lb.pack(pady=(8, 2))
            try:
                pil_img = Image.open(os.path.join(_assets, fname))
                w, h = pil_img.size
                new_w = 175
                new_h = int(h * new_w / w)
                pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
                ctk_img = ctk.CTkImage(pil_img, size=(new_w, new_h))
                ctk.CTkLabel(card, image=ctk_img, text="").pack(padx=4)
                self._cal_images.append(ctk_img)
            except Exception:
                ctk.CTkLabel(card, text="[фото]", height=80,
                             text_color=MD3["on_surface2"]).pack()
            pt_desc_lb = ctk.CTkLabel(card, text=LANGS[self.current_lang][pt_desc_key],
                         font=ctk.CTkFont(size=11),
                         text_color=MD3["on_surface2"],
                         justify="center")
            pt_desc_lb.pack(pady=(4, 8))
            self._cal_point_label_widgets.append((pt_lb, pt_desc_lb, pt_label_key, pt_desc_key))

        # Лейбл для скриншота тюнинга (скрыт до выбора пункта)
        _tune_img_label = ctk.CTkLabel(_img_area, text="", image=None)
        self._tune_screen_images = {}

        def _show_cal_images():
            _tune_img_label.pack_forget()
            _cal_imgs_frame.pack(fill="x")

        def _show_tune_image(key):
            _cal_imgs_frame.pack_forget()
            if key not in self._tune_screen_images:
                fname = _TUNE_SCREEN_MAP.get(key)
                img = None
                if fname:
                    try:
                        pil_img = Image.open(os.path.join(_assets, fname))
                        w, h = pil_img.size
                        new_w = 380
                        new_h = int(h * new_w / w)
                        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
                        img = ctk.CTkImage(pil_img, size=(new_w, new_h))
                    except Exception:
                        pass
                self._tune_screen_images[key] = img
            ctk_img = self._tune_screen_images[key]
            _tune_img_label.configure(image=ctk_img if ctk_img else None)
            _tune_img_label.pack(padx=8, pady=4)

        # ── Profile dropdown ──────────────────────────────────────────────
        profile_frame = ctk.CTkFrame(self._cal_frame, fg_color="transparent")
        profile_frame.pack(fill="x", padx=40, pady=4)
        _cal_profile_lb = ctk.CTkLabel(profile_frame, text=LANGS[self.current_lang]["cal_profile_lb"],
                                       text_color=MD3["on_surface2"])
        _cal_profile_lb.pack(side="left")
        self._i18n_labels.append((_cal_profile_lb, "cal_profile_lb"))
        ctk.CTkOptionMenu(
            profile_frame,
            values=list(PROFILES.keys()),
            variable=self._cal_profile_var,
            fg_color=MD3["elevated"],
            button_color=MD3["primary"],
            button_hover_color=MD3["primary_dim"],
            text_color=MD3["on_surface"],
            corner_radius=8,
        ).pack(side="right")

        # ── Status label ──────────────────────────────────────────────────
        self._cal_status_label = ctk.CTkLabel(
            self._cal_frame,
            text=LANGS[self.current_lang]["cal_not_calibrated"],
            font=ctk.CTkFont(size=13),
            text_color="#FFB300",
        )
        self._cal_status_label.pack(pady=8)

        def _update_status():
            try:
                import mss as _mss_diag
                with _mss_diag.mss() as _s:
                    _mw = _s.monitors[0]['width']
                    _mh = _s.monitors[0]['height']
                _diag = f"\nэкран: tk={self.winfo_screenwidth()}×{self.winfo_screenheight()} / mss={_mw}×{_mh}"
            except Exception:
                _diag = ""
            self._cal_status_label.configure(
                text=(
                    f"scale_x={coord_manager.scale_x:.4f}  "
                    f"scale_y={coord_manager.scale_y:.4f}\n"
                    f"anchor=({coord_manager.anchor_x}, {coord_manager.anchor_y})  "
                    f"dialog_offset_y={coord_manager.dialog_offset_y}"
                    f"{_diag}"
                ),
                text_color="#4ADE80",
            )

        def _load_profile():
            path = PROFILES[self._cal_profile_var.get()]
            if not os.path.exists(path):
                messagebox.showerror("Ошибка", f"Файл не найден:\n{path}")
                return
            coord_manager.load(path)
            self._dialog_offset_y_var.set(coord_manager.dialog_offset_y)
            self._load_crypt_from_profile(path)
            _update_status()
            _tune_refresh_display()
            self._save_gui_config_key("last_calibration_profile",
                                      self._cal_profile_var.get())

        def _auto_calibrate():
            from auto_calibration import auto_detect_point_a, auto_detect_point_b
            from calibration_ui import calibrate_one_point
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()

            # ── Этап 1: детектируем Point A → лупа → пользователь подтверждает ──
            self.withdraw()
            try:
                start_a = auto_detect_point_a(screen_w, screen_h)
            except Exception as e:
                messagebox.showerror("Авто-калибровка", f"Ошибка детекции A:\n{e}")
                self.deiconify()
                return
            self.deiconify()

            point_a = calibrate_one_point(
                self, start_a, "Точка А — центр мини-карты (лево-низ)"
            )
            if point_a is None:
                return

            # ── Этап 2: детектируем Point B → лупа → пользователь подтверждает ──
            self.withdraw()
            try:
                start_b = auto_detect_point_b(screen_w, screen_h)
            except Exception as e:
                messagebox.showerror("Авто-калибровка", f"Ошибка детекции B:\n{e}")
                self.deiconify()
                return
            self.deiconify()

            point_b = calibrate_one_point(
                self, start_b, "Точка Б — крестик серебра (право-верх)"
            )
            if point_b is None:
                return

            coord_manager.calibrate(point_a, point_b)
            _update_status()

        def _calibrate():
            from calibration_ui import run_calibration
            self.iconify()  # minimize (not withdraw) — withdraw breaks child Toplevels
            try:
                point_a, point_b = run_calibration(parent=self)
            finally:
                self.deiconify()
            if point_a and point_b:
                coord_manager.calibrate(point_a, point_b)
                _update_status()

        def _save_profile():
            coord_manager.dialog_offset_y = self._dialog_offset_y_var.get()
            path = PROFILES[self._cal_profile_var.get()]
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            coord_manager.save(path)
            self._save_crypt_settings()
            self._save_gui_config_key("last_calibration_profile",
                                      self._cal_profile_var.get())
            messagebox.showinfo("Сохранено", f"Профиль сохранён:\n{path}")


        # ── Кнопка Калибровать — главная (error tonal) ───────────────────
        self._cal_manual_btn = ctk.CTkButton(
            self._cal_frame,
            text=LANGS[self.current_lang]["cal_manual_btn"],
            command=_calibrate,
            fg_color=MD3["error"],
            hover_color=MD3["error_hover"],
            text_color=MD3["on_surface"],
            height=56,
            corner_radius=16,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self._cal_manual_btn.pack(fill="x", padx=40, pady=(8, 6))
        self._i18n_labels.append((self._cal_manual_btn, "cal_manual_btn"))

        # ── Сохранить / Загрузить — в одну строку ────────────────────────
        save_load_row = ctk.CTkFrame(self._cal_frame, fg_color="transparent")
        save_load_row.pack(fill="x", padx=40, pady=(0, 8))
        self._cal_save_btn = ctk.CTkButton(save_load_row, text=LANGS[self.current_lang]["cal_save_btn"],
                      command=_save_profile,
                      fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
                      text_color=MD3["on_surface"], corner_radius=8,
                      height=36)
        self._cal_save_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self._i18n_labels.append((self._cal_save_btn, "cal_save_btn"))
        self._cal_load_btn = ctk.CTkButton(save_load_row, text=LANGS[self.current_lang]["cal_load_btn"],
                      command=_load_profile,
                      fg_color=MD3["blue_btn"], hover_color=MD3["blue_hover"],
                      text_color=MD3["on_surface"], corner_radius=8,
                      height=36)
        self._cal_load_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))
        self._i18n_labels.append((self._cal_load_btn, "cal_load_btn"))

        # ── Тюнинг кликов (D-Pad) ────────────────────────────────────────
        # Порядок фиксирован: 0=wt_icon, 1=carter, 2=top_accel, 3=march_accel
        _TUNE_INTERNAL = TUNE_TARGET_NAMES
        _TUNE_SCREEN_MAP = {
            "wt_icon":       "tune_wt_icon.png",
            "carter":        "tune_carter.png",
            "top_accel":     "tune_top_accel.png",
            "march_accel":   "tune_march_accel.png",
            "chest_sender":  "tune_chest_sender.png",
            "chest_type":    "tune_chest_type.png",
            "chest_collect": "tune_chest_collect.png",
        }

        def _tune_labels():
            calib = LANGS[self.current_lang]["tab_cal"]
            return [calib] + [LANGS[self.current_lang][f"cal_tune_{k}"] for k in _TUNE_INTERNAL]

        tune_card = ctk.CTkFrame(self._cal_frame, fg_color=MD3["card"],
                                  corner_radius=10, border_width=1,
                                  border_color=MD3["outline"])
        tune_card.pack(fill="x", padx=16, pady=(10, 4))

        _tune_title_lb = ctk.CTkLabel(tune_card, text=LANGS[self.current_lang]["cal_tune_title"],
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=MD3["primary"])
        _tune_title_lb.pack(pady=(8, 4))
        self._i18n_labels.append((_tune_title_lb, "cal_tune_title"))

        # idx = -1 означает режим «Калибровка» (показываем скрины точек А/Б)
        self._tune_idx = -1
        self._ui_tune_btn_var = ctk.StringVar(value=_tune_labels()[0])

        def _tune_on_select(display_val):
            labels = _tune_labels()
            if display_val == labels[0]:       # первый пункт — «Калибровка»
                self._tune_idx = -1
            elif display_val in labels[1:]:
                self._tune_idx = labels[1:].index(display_val)
            _tune_refresh_display()

        self._tune_option_menu = ctk.CTkOptionMenu(
            tune_card, values=_tune_labels(),
            variable=self._ui_tune_btn_var,
            fg_color=MD3["elevated"], button_color=MD3["primary"],
            button_hover_color=MD3["primary_dim"],
            text_color=MD3["on_surface"], corner_radius=8,
            command=_tune_on_select,
        )
        self._tune_option_menu.pack(fill="x", padx=12, pady=(0, 4))

        self._tune_display_lb = ctk.CTkLabel(
            tune_card, text="",
            font=ctk.CTkFont(size=13), text_color=MD3["on_surface"])
        self._tune_display_lb.pack(pady=(0, 2))

        _CHEST_TUNE_RECTS = {
            "chest_sender": chest_reader.SENDER_REF_RECT,
            "chest_type": chest_reader.SOURCE_REF_RECT,
        }

        def _tune_get_key():
            if self._tune_idx < 0:
                return None
            return _TUNE_INTERNAL[self._tune_idx]

        def _tune_show_chest_overlay_if_relevant():
            key = _tune_get_key()
            if key and key in _CHEST_TUNE_RECTS:
                self._show_chest_rect_overlay(_CHEST_TUNE_RECTS[key], key)

        def _tune_refresh_display():
            key = _tune_get_key()
            if key is None:
                _show_cal_images()
                self._tune_display_lb.configure(text="")
                return
            ox, oy = coord_manager.get_ui_offset(key)
            self._tune_display_lb.configure(text=f"X: {ox:+d}px   Y: {oy:+d}px")
            _tune_show_chest_overlay_if_relevant()
            _show_tune_image(key)

        def _tune_apply(dx, dy):
            key = _tune_get_key()
            if key is None:
                return
            ox, oy = coord_manager.get_ui_offset(key)
            coord_manager.set_ui_offset(key, ox + dx, oy + dy)
            _tune_refresh_display()

        # Step size toggle
        _tune_step = ctk.CTkSegmentedButton(
            tune_card, values=["1px", "5px"],
            fg_color=MD3["elevated"],
            selected_color=MD3["primary"],
            selected_hover_color=MD3["primary_dim"],
            unselected_color=MD3["card"],
            unselected_hover_color=MD3["elevated"],
            text_color=MD3["on_surface"],
            font=ctk.CTkFont(size=12),
        )
        _tune_step.set("5px")
        _tune_step.pack(pady=(0, 4))

        def _step():
            return 1 if _tune_step.get() == "1px" else 5

        # D-Pad cross
        dpad_frame = ctk.CTkFrame(tune_card, fg_color="transparent")
        dpad_frame.pack(pady=(0, 6))
        _btn = dict(width=44, height=34, corner_radius=8,
                    fg_color=MD3["elevated"], hover_color=MD3["outline"],
                    text_color=MD3["on_surface"],
                    font=ctk.CTkFont(size=18))
        ctk.CTkButton(dpad_frame, text="▲",
                      command=lambda: _tune_apply(0, -_step()),
                      **_btn).grid(row=0, column=1, padx=4, pady=3)
        ctk.CTkButton(dpad_frame, text="◄",
                      command=lambda: _tune_apply(-_step(), 0),
                      **_btn).grid(row=1, column=0, padx=4, pady=3)
        ctk.CTkButton(dpad_frame, text="►",
                      command=lambda: _tune_apply(_step(), 0),
                      **_btn).grid(row=1, column=2, padx=4, pady=3)
        ctk.CTkButton(dpad_frame, text="▼",
                      command=lambda: _tune_apply(0, _step()),
                      **_btn).grid(row=2, column=1, padx=4, pady=3)

        # Reset button
        _tune_reset_btn = ctk.CTkButton(tune_card, text=LANGS[self.current_lang]["cal_tune_reset"],
                      command=lambda: (
                          coord_manager.set_ui_offset(_tune_get_key(), 0, 0) if _tune_get_key() else None,
                          _tune_refresh_display(),
                      ),
                      fg_color=MD3["card"], hover_color=MD3["elevated"],
                      text_color=MD3["on_surface2"], height=26, corner_radius=8,
                      font=ctk.CTkFont(size=12))
        _tune_reset_btn.pack(pady=(0, 10))
        self._i18n_labels.append((_tune_reset_btn, "cal_tune_reset"))

        _tune_refresh_display()

        # ── REF info ──────────────────────────────────────────────────────
        ctk.CTkLabel(
            self._cal_frame,
            text=f"Эталон 1920×1080:\nА={REF_A} мини-карта   Б={REF_B} серебро",
            font=ctk.CTkFont(size=10),
            text_color=MD3["outline"],
            justify="center",
        ).pack(pady=(20, 0))

        # ── Создаём дефолтные профили если их нет (первый запуск / после ZIP без profiles/) ──
        for _prof_path in PROFILES.values():
            if not os.path.exists(_prof_path):
                os.makedirs(os.path.dirname(os.path.abspath(_prof_path)), exist_ok=True)
                coord_manager.save(_prof_path)

        # ── Auto-load on startup ──────────────────────────────────────────
        last = self._load_gui_config().get("last_calibration_profile", "Client")
        self._cal_profile_var.set(last)
        default_path = PROFILES.get(last, PROFILES["Client"])
        if os.path.exists(default_path):
            try:
                coord_manager.load(default_path)
                self._dialog_offset_y_var.set(coord_manager.dialog_offset_y)
                self._load_crypt_from_profile(default_path)
                _update_status()
                _tune_refresh_display()
            except Exception as _e:
                self._cal_status_label.configure(
                    text=f"⚠ Профиль не загружен: {_e}\nИспользуются координаты 1920×1080",
                    text_color="#FFB300",
                )


def _crash_handler(exc: BaseException) -> None:
    """Silent Observer: записывает crash_report.txt и отправляет на сервер."""
    import traceback as _tb
    import json as _json
    import platform as _platform
    import urllib.request as _req
    import datetime as _dt

    if getattr(sys, 'frozen', False):
        _root = os.path.dirname(sys.executable)
    else:
        _root = os.path.dirname(os.path.abspath(__file__))

    try:
        _hwid = get_hwid()
    except Exception:
        _hwid = None

    report = {
        "hwid":      _hwid,
        "version":   VERSION,
        "os_info":   _platform.platform(),
        "traceback": _tb.format_exc(),
        "timestamp": _dt.datetime.now().isoformat(),
    }

    crash_path = os.path.join(_root, "crash_report.txt")
    try:
        with open(crash_path, "w", encoding="utf-8") as _f:
            _json.dump(report, _f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    try:
        _data = _json.dumps({k: v for k, v in report.items() if k != "timestamp"}).encode("utf-8")
        _req_obj = _req.Request(
            "https://api.total-hunter.com/web/crash_report",
            data=_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        _req.urlopen(_req_obj, timeout=5)
    except Exception:
        pass

    try:
        win = ctk.CTk()
        win.title("Total Hunter — Ошибка запуска")
        win.geometry("500x340")
        win.resizable(False, False)
        win.configure(fg_color=MD3["bg"])

        ctk.CTkLabel(win, text="Ошибка запуска",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=MD3["error_text"]).pack(pady=(20, 4))
        ctk.CTkLabel(win,
                     text=f"Отчёт сохранён: crash_report.txt\nОтправлен разработчику автоматически.",
                     text_color=MD3["on_surface2"], font=ctk.CTkFont(size=12)).pack(pady=(0, 8))

        tb_box = ctk.CTkTextbox(win, height=150,
                                font=ctk.CTkFont(family="Consolas", size=10),
                                fg_color=MD3["card"])
        tb_box.pack(fill="x", padx=20, pady=(0, 10))
        tb_box.insert("end", report["traceback"][-1200:])
        tb_box.configure(state="disabled")

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkButton(btn_row, text="Открыть crash_report.txt",
                      command=lambda: os.startfile(crash_path) if os.path.exists(crash_path) else None,
                      fg_color=MD3["blue_btn"], hover_color=MD3["blue_hover"],
                      corner_radius=8, height=34).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Закрыть",
                      command=win.destroy,
                      fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
                      corner_radius=8, height=34).pack(side="left", expand=True, fill="x")
        win.mainloop()
    except Exception:
        try:
            import tkinter.messagebox as _mb
            _mb.showerror("Total Hunter", f"Ошибка запуска.\nОтчёт: {crash_path}\n\n{str(exc)[:400]}")
        except Exception:
            pass


if __name__ == "__main__":
    try:
        from version import VERSION
        from updater import check_for_updates, run_update_window
        latest_tag, url = check_for_updates(VERSION)
        if latest_tag and url:
            run_update_window(latest_tag, url)

        app = TotalHunterApp()
        app.mainloop()
    except Exception as _exc:
        _crash_handler(_exc)


