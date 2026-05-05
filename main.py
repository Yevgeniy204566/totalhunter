



# ── PyInstaller: preload torch DLLs before any import ────────────────────────
import sys, os
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
import os
import customtkinter as ctk
from auth import (get_hwid, check_license, get_free_trial, spend_credit,
                  login_with_google, log_error_to_server, activate_referral,
                  transfer_referral_balance, generate_link_code)
from engine import HuntEngine
from crypt_hunter import CryptHunter
from combiner import CombinerEngine
from coord_manager import coord_manager, REF_A, REF_B
import tkinter.messagebox as messagebox
import sys
import keyboard
import webbrowser

GUI_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui_config.json')


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


LANGS = {
    "RU": {
        # --- существующие ---
        "title": "Total Hunter", "tab_hunt": "БИРЖИ", "tab_combo": "Combo", "tab_ref": "РЕФЕРАЛЫ",
        "get_trial": "ПОЛУЧИТЬ 300 ПОПЫТОК", "start": "ЗАПУСТИТЬ ОХОТУ", "stop": "ОСТАНОВИТЬ",
        "no_credits": "У вас 0 алмазов! Привяжите устройство на сайте.", "login_btn": "ПРИВЯЗАТЬ УСТРОЙСТВО",
        "banned": "ВАШ АККАУНТ ЗАБЛОКИРОВАН", "ref_title": "ПАРТНЕРСКАЯ ПРОГРАММА",
        "my_code": "ВАШ КОД ДЛЯ ПРИГЛАШЕНИЯ:", "friend_code": "КОД ПРИГЛАСИТЕЛЯ (+50):",
        "activate_ref": "АКТИВИРОВАТЬ", "ref_used": "БОНУС АКТИВИРОВАН ✅",
        "accuracy": "Точность поиска", "scan_rate": "Частота сканирования", "sec": "сек.",
        "copy": "КОПИРОВАТЬ", "share_text": "ПОДЕЛИТЕСЬ КОДОМ И ПОЛУЧАЙТЕ %", "copied": "Скопировано!",
        "clicker_title": "Синхронизация Clickermann", "clicker_on": "ВКЛЮЧИТЬ", "key_start": "Старт:", "key_stop": "Стоп:",
        "status_ready": "СИСТЕМА ГОТОВА", "status_running": "СТАТУС: В ПОИСКЕ...",
        "add_oil": "Добавь масла",
        # --- новые tab names ---
        "tab_crypt": "СКЛЕПЫ", "tab_cal": "КАЛИБРОВКА",
        # --- hunt tab ---
        "nn_title": "Нейросеть", "nav_main_title": "Навигация",
        "nav_extra_title": "Дополнительно", "nav_auto": "Авто",
        "save_settings": "Сохранить настройки",
        "nav_step": "Шаг:", "nav_wait": "Скорость (сек/шаг):",
        "nav_inland": "Глубина нырка (экранов):", "nav_ocean": "Граница океан/суша (%):",
        "nav_waterpx": "Мин. размер водоёма:", "nav_diagblind": "Коэф. диагонали возврата:",
        "nav_footprint": "Память следов (сек):", "nav_delta": "Дельта возврата (px):",
        "nav_pitch": "Живость хода (%):",
        # --- crypt tab ---
        "crypt_icons_title": "Выберите типы склепов:",
        "crypt_conf_lb": "Точность поиска", "crypt_accel_lb": "Ускорение марша (0–5)",
        "crypt_break_lb": "Перерыв между склепами", "crypt_march_lb": "Дальность марша Картера",
        "crypt_scroll_lb": "Частота YOLO-детекции", "crypt_profile_lb": "Профиль:",
        "crypt_micro_lb": "Микроподстройка кликов ↑↓:", "crypt_save_btn": "💾  Сохранить настройки",
        "crypt_start": "ЗАПУСТИТЬ СБОР СКЛЕПОВ", "crypt_stop_btn": "ОСТАНОВИТЬ",
        "crypt_ready": "ГОТОВО", "crypt_stopped": "Остановлено",
        "crypt_select_warn": "Выберите хотя бы один тип!", "crypt_searching": "СТАТУС: В ПОИСКЕ...",
        "crypt_collected": "Собрано", "crypt_last": "последний",
        "oil_check": "Проверка масла",
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
        # --- ref tab additions ---
        "ref_bal_title": "Реферальный баланс", "ref_transfer_btn": "💸  Перевести на баланс  →",
        "ref_link_title": "Ваша реферальная ссылка:", "ref_code_prefix": "Код: ",
        "ref_stats_title": "Рефералы",
        # --- units ---
        "unit_sec": "с", "unit_min": "мин", "unit_scan": "скан",
    },
    "EN": {
        # --- существующие ---
        "title": "Total Hunter", "tab_hunt": "EXCHANGE", "tab_combo": "Combo", "tab_ref": "REFERRALS",
        "get_trial": "GET 300 TRIALS", "start": "START HUNT", "stop": "STOP",
        "no_credits": "0 diamonds! Link your device on the website.", "login_btn": "LINK DEVICE",
        "banned": "ACCOUNT BANNED", "ref_title": "REFERRAL SYSTEM",
        "my_code": "YOUR INVITE CODE:", "friend_code": "INVITER CODE (+50):",
        "activate_ref": "ACTIVATE", "ref_used": "BONUS ACTIVE ✅",
        "accuracy": "Detection Accuracy", "scan_rate": "Scan Interval", "sec": "sec.",
        "copy": "COPY", "share_text": "SHARE CODE AND GET %", "copied": "Copied!",
        "clicker_title": "Clickermann Sync", "clicker_on": "ENABLED", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "READY", "status_running": "STATUS: SEARCHING...",
        "add_oil": "Add Oil",
        # --- новые tab names ---
        "tab_crypt": "CRYPTS", "tab_cal": "CALIBRATION",
        # --- hunt tab ---
        "nn_title": "Neural Net", "nav_main_title": "Navigation",
        "nav_extra_title": "Advanced", "nav_auto": "Auto",
        "save_settings": "Save settings",
        "nav_step": "Step:", "nav_wait": "Speed (sec/step):",
        "nav_inland": "Dive depth (screens):", "nav_ocean": "Ocean/land ratio (%):",
        "nav_waterpx": "Min. water area (px):", "nav_diagblind": "Return diagonal coeff:",
        "nav_footprint": "Footprint TTL (sec):", "nav_delta": "Return delta (px):",
        "nav_pitch": "Motion smoothness (%):",
        # --- crypt tab ---
        "crypt_icons_title": "Select crypt types:",
        "crypt_conf_lb": "Detection accuracy", "crypt_accel_lb": "March acceleration (0–5)",
        "crypt_break_lb": "Break between crypts", "crypt_march_lb": "Carter march distance",
        "crypt_scroll_lb": "YOLO detection rate", "crypt_profile_lb": "Profile:",
        "crypt_micro_lb": "Click micro-adjust ↑↓:", "crypt_save_btn": "💾  Save settings",
        "crypt_start": "START CRYPT HUNT", "crypt_stop_btn": "STOP",
        "crypt_ready": "READY", "crypt_stopped": "Stopped",
        "crypt_select_warn": "Select at least one type!", "crypt_searching": "STATUS: SEARCHING...",
        "crypt_collected": "Collected", "crypt_last": "last",
        "oil_check": "Oil check",
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
        # --- ref tab additions ---
        "ref_bal_title": "Referral Balance", "ref_transfer_btn": "💸  Transfer to balance  →",
        "ref_link_title": "Your referral link:", "ref_code_prefix": "Code: ",
        "ref_stats_title": "Referrals",
        # --- units ---
        "unit_sec": "s", "unit_min": "min", "unit_scan": "scan",
    },
}


class TotalHunterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.engine = HuntEngine()
        self.engine.on_found_callback = self.on_target_found
        self.crypt_engine = CryptHunter()
        self.is_crypt_running = False
        self._crypt_found_count = 0
        # self.combo_engine = CombinerEngine()  # Combo временно отключён
        self.is_combo_running = False
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
        self._i18n_labels = []  # (widget, lang_key)
       
        self.title("Total Battle Hunter Pro v2.4")
        self.geometry("460x1010")
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
        self.always_on_top_var = ctk.BooleanVar(value=False)
        ctk.CTkLabel(_header, text="On top:", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MD3["on_surface"]).pack(side="left")
        ctk.CTkSwitch(_header, text="", variable=self.always_on_top_var,
                      onvalue=True, offvalue=False, command=self._on_always_on_top,
                      width=46,
                      button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
                      progress_color=MD3["primary"]).pack(side="left", padx=(4, 0))
        self.lang_menu = ctk.CTkOptionMenu(_header, values=list(LANGS.keys()),
                                           command=self.change_lang, width=80,
                                           fg_color=MD3["elevated"],
                                           button_color=MD3["primary"],
                                           button_hover_color=MD3["primary_dim"],
                                           text_color=MD3["on_surface"],
                                           corner_radius=8)
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
            command=lambda: webbrowser.open("https://total-hunter.com/dashboard"),
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
                                            font=ctk.CTkFont(size=13, slant="italic"),
                                            text_color="#FFD740", wraplength=380)

        # Вкладки
        self.tabview = ctk.CTkTabview(self._outer, width=420, height=780,
                                      fg_color=MD3["card"],
                                      segmented_button_fg_color=MD3["elevated"],
                                      segmented_button_selected_color=MD3["tab_selected"],
                                      segmented_button_selected_hover_color=MD3["tab_selected_hover"],
                                      segmented_button_unselected_color=MD3["elevated"],
                                      segmented_button_unselected_hover_color=MD3["card"],
                                      text_color=MD3["on_surface"],
                                      text_color_disabled=MD3["on_surface2"],
                                      corner_radius=12)
        self.tabview.pack(padx=20, pady=10, fill="x")
       
        # Сохраняем имена вкладок при создании — change_lang ищет по ним
        self._tab_init_names = {k: LANGS[self.current_lang][k]
                                for k in ("tab_crypt", "tab_hunt", "tab_ref", "tab_cal")}
        self.tab_crypt = self.tabview.add(self._tab_init_names["tab_crypt"])
        self.tab_hunt  = self.tabview.add(self._tab_init_names["tab_hunt"])
        # self.tab_combo = self.tabview.add("Combo")  # временно отключён
        self.tab_ref   = self.tabview.add(self._tab_init_names["tab_ref"])
        self.tab_calibration = self.tabview.add(self._tab_init_names["tab_cal"])


        # Общие переменные для калибровки (нужны в нескольких вкладках)
        _BASE = os.path.dirname(os.path.abspath(__file__))
        self._PROFILES = {
            "Client":    os.path.join(_BASE, "profiles", "profile_client.json"),
            "Browser 1": os.path.join(_BASE, "profiles", "profile_chrome.json"),
            "Browser 2": os.path.join(_BASE, "profiles", "profile_firefox.json"),
        }
        self._cal_profile_var    = ctk.StringVar(value="Client")
        self._dialog_offset_y_var = ctk.IntVar(value=0)

        self.setup_hunt_tab()
        self.setup_crypt_tab()
        # self.setup_combo_tab()  # временно отключён
        self.setup_ref_tab()
        self.setup_calibration_tab()
        self.update_license_info()

        # Глобальный перехват ESC — стоп в любом окне
        def _esc_handler(event):
            if event.name == 'esc' and event.event_type == 'down':
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

        self.speed_frame = ctk.CTkFrame(nn_frame, fg_color="transparent")
        self.speed_frame.pack(fill="x", padx=12, pady=(0, 0))
        self.speed_lb = ctk.CTkLabel(self.speed_frame,
                                     text=LANGS[self.current_lang]["scan_rate"],
                                     font=ctk.CTkFont(size=13),
                                     text_color=MD3["on_surface2"])
        self.speed_lb.pack(side="left")
        self.speed_val_lb = ctk.CTkLabel(self.speed_frame,
                                         text=f"0.6 {LANGS[self.current_lang]['sec']}",
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         text_color=MD3["value_text"])
        self.speed_val_lb.pack(side="right")
        self.speed_slider = ctk.CTkSlider(nn_frame, from_=0.1, to=5.0,
                                          command=self.update_slider_labels,
                                          button_color=MD3["primary"],
                                          button_hover_color=MD3["primary_dim"],
                                          progress_color=MD3["primary"])
        self.speed_slider.set(0.6)
        self.speed_slider.pack(padx=12, pady=(2, 4), fill="x")


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
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"])
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

        # Скорость (ожидание после шага)
        self.nav_wait_frame = ctk.CTkFrame(nav_main_frame, fg_color="transparent")
        self.nav_wait_frame.pack(fill="x", padx=12, pady=(2, 0))
        _nav_wait_lb = ctk.CTkLabel(self.nav_wait_frame, text=LANGS[self.current_lang]["nav_wait"],
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"])
        _nav_wait_lb.pack(side="left")
        self._i18n_labels.append((_nav_wait_lb, "nav_wait"))
        self.nav_wait_val = ctk.CTkLabel(self.nav_wait_frame, text="2.0 с",
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         text_color=MD3["value_text"])
        self.nav_wait_val.pack(side="right")
        self.nav_wait_slider = ctk.CTkSlider(nav_main_frame, from_=0.5, to=5.0,
                                             command=self._update_nav_labels,
                                             button_color=MD3["primary"],
                                             button_hover_color=MD3["primary_dim"],
                                             progress_color=MD3["primary"])
        self.nav_wait_slider.set(2.0)
        self.nav_wait_slider.pack(padx=12, pady=(2, 2), fill="x")

        # Глубина нырка
        self.nav_inland_frame = ctk.CTkFrame(nav_main_frame, fg_color="transparent")
        self.nav_inland_frame.pack(fill="x", padx=12, pady=(2, 0))
        _nav_inland_lb = ctk.CTkLabel(self.nav_inland_frame, text=LANGS[self.current_lang]["nav_inland"],
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"])
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

        # CENTER X / Y
        self.nav_xy_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        self.nav_xy_frame.pack(fill="x", padx=10, pady=(0, 2))
        ctk.CTkLabel(self.nav_xy_frame, text="Center X:",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left", padx=(0,2))
        self.nav_cx_entry = ctk.CTkEntry(self.nav_xy_frame, width=55, justify="center",
                                         font=ctk.CTkFont(size=13),
                                         fg_color=MD3["card"],
                                         border_color=MD3["outline"],
                                         text_color=MD3["on_surface"],
                                         corner_radius=6)
        self.nav_cx_entry.insert(0, "90")
        self.nav_cx_entry.pack(side="left", padx=(0, 10))
        self.nav_cx_entry.bind('<KeyRelease>', self._show_calibration_dot)
        ctk.CTkLabel(self.nav_xy_frame, text="Center Y:",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left", padx=(0,2))
        self.nav_cy_entry = ctk.CTkEntry(self.nav_xy_frame, width=55, justify="center",
                                         font=ctk.CTkFont(size=13),
                                         fg_color=MD3["card"],
                                         border_color=MD3["outline"],
                                         text_color=MD3["on_surface"],
                                         corner_radius=6)
        self.nav_cy_entry.insert(0, "925")
        self.nav_cy_entry.pack(side="left")
        self.nav_cy_entry.bind('<KeyRelease>', self._show_calibration_dot)

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
        self.nav_pitch_slider.set(50)
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
                                                 corner_radius=12, height=220,
                                                 border_width=1,
                                                 border_color=MD3["outline"],
                                                 scrollbar_fg_color="transparent",
                                                 scrollbar_button_color=MD3["outline"],
                                                 scrollbar_button_hover_color=MD3["value_text"])
        settings_frame.pack(fill="x", padx=20, pady=4)

        def _slider_row(lang_key, default_text):
            """Хелпер: строка-заголовок слайдера."""
            row = ctk.CTkFrame(settings_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=(4, 0))
            name_lb = ctk.CTkLabel(row, text=LANGS[self.current_lang][lang_key],
                                   font=ctk.CTkFont(size=13),
                                   text_color=MD3["on_surface2"])
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
        self.crypt_accel_val = _slider_row("crypt_accel_lb", "3")
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
        self.crypt_march_val = _slider_row("crypt_march_lb", "15 мин")
        self.crypt_march_slider = ctk.CTkSlider(settings_frame, from_=5, to=30,
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
                          fg_color=MD3["card"],
                          button_color=MD3["primary"],
                          button_hover_color=MD3["primary_dim"],
                          text_color=MD3["on_surface"],
                          corner_radius=6).pack(side="left", padx=(4, 6))
        # ── Смещение диалога (микроподстройка кликов) ────────────
        offset_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        offset_row.pack(fill="x", padx=10, pady=(2, 0))
        _crypt_micro_lb = ctk.CTkLabel(offset_row, text=LANGS[self.current_lang]["crypt_micro_lb"],
                                       font=ctk.CTkFont(size=13),
                                       text_color=MD3["on_surface2"])
        _crypt_micro_lb.pack(side="left")
        self._i18n_labels.append((_crypt_micro_lb, "crypt_micro_lb"))
        ctk.CTkButton(offset_row, text="−", width=28, height=24,
                      fg_color=MD3["card"], hover_color=MD3["elevated"],
                      text_color=MD3["on_surface"], corner_radius=6,
                      command=lambda: self._dialog_offset_y_var.set(
                          self._dialog_offset_y_var.get() - 5)).pack(side="left", padx=(6, 0))
        ctk.CTkEntry(offset_row, textvariable=self._dialog_offset_y_var,
                     width=48, height=24, justify="center",
                     fg_color=MD3["card"], border_color=MD3["outline"],
                     text_color=MD3["on_surface"], corner_radius=6).pack(side="left", padx=2)
        ctk.CTkButton(offset_row, text="+", width=28, height=24,
                      fg_color=MD3["card"], hover_color=MD3["elevated"],
                      text_color=MD3["on_surface"], corner_radius=6,
                      command=lambda: self._dialog_offset_y_var.set(
                          self._dialog_offset_y_var.get() + 5)).pack(side="left")

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

        # ─── Масло — три типа + переключатель проверки (одна строка) ───
        oil_frame = ctk.CTkFrame(self.tab_crypt, fg_color=MD3["card"],
                                  corner_radius=10, border_width=1,
                                  border_color=MD3["outline"])
        oil_frame.pack(pady=(2, 4), padx=20, fill="x")
        self.oil_ordinary_label = ctk.CTkLabel(
            oil_frame, text="🟢 —",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#66BB6A"
        )
        self.oil_ordinary_label.pack(side="left", padx=10, pady=6)
        self.oil_rare_label = ctk.CTkLabel(
            oil_frame, text="🔵 —",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#42A5F5"
        )
        self.oil_rare_label.pack(side="left", padx=10, pady=6)
        self.oil_epic_label = ctk.CTkLabel(
            oil_frame, text="🟣 —",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#AB47BC"
        )
        self.oil_epic_label.pack(side="left", padx=10, pady=6)
        self._oil_check_var = ctk.BooleanVar(value=True)
        self._oil_check_switch = ctk.CTkSwitch(
            oil_frame,
            text=LANGS[self.current_lang]["oil_check"],
            variable=self._oil_check_var,
            onvalue=True, offvalue=False,
            command=self._save_crypt_settings,
            font=ctk.CTkFont(size=11),
            text_color=MD3["on_surface2"],
            button_color=MD3["primary"],
            button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self._oil_check_switch.pack(side="right", padx=10, pady=6)
        self._i18n_labels.append((self._oil_check_switch, "oil_check"))

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
            spend_credit()
            new_credits = max(0, self.current_credits - 1)
            self.after(0, lambda n=new_credits: self._update_credits_display(n))
        except Exception:
            pass

    def on_crypt_status(self, msg: str):
        self.after(0, lambda: self.crypt_status_label.configure(text=msg))

    def on_crypt_oil(self, ordinary: int, epic: int, rare: int):
        def _fmt(n: int) -> str:
            if n >= 1_000_000:
                return f"{n/1_000_000:.2f}M"
            if n >= 1_000:
                return f"{n//1_000}K"
            return str(n)
        def _upd():
            self.oil_ordinary_label.configure(text=f"🟢 {_fmt(ordinary)}")
            self.oil_rare_label.configure(text=f"🔵 {_fmt(rare)}")
            self.oil_epic_label.configure(text=f"🟣 {_fmt(epic)}")
        self.after(0, _upd)

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
        if reason.startswith("OIL_LOW:"):
            stop_text = LANGS[self.current_lang].get("add_oil", "Add oil")
            stop_color = "#FFB300"
        else:
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
            self.crypt_engine.oil_check_enabled = self._oil_check_var.get()
            self.crypt_engine.lang = self.current_lang
            self.crypt_engine.start(
                selected_crypts=selected,
                conf=self.crypt_conf_slider.get(),
                accelerations=int(self.crypt_accel_slider.get()),
                break_sec=int(self.crypt_break_slider.get()),
                scroll_speed=round(self.crypt_scroll_slider.get(), 1),
                max_march_min=int(self.crypt_march_slider.get()),
                on_found_callback=self.on_crypt_found,
                on_status_callback=self.on_crypt_status,
                on_stop_callback=self.on_crypt_stop,
                on_countdown_callback=self.on_crypt_countdown,
                on_oil_callback=self.on_crypt_oil,
            )

    def toggle_combo_bot(self):
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
                work_h = rect.bottom - rect.top - 35
                work_y = rect.top
            except Exception:
                work_h = self.winfo_screenheight() - 90
                work_y = 0
            right_x = self.winfo_screenwidth() - 460
            self.geometry(f"460x{work_h}+{right_x}+{work_y}")
            self.update_idletasks()
            x = self.winfo_x()
            y = self.winfo_y()
            w = self.winfo_width()
            h = self.winfo_height()
            self.crypt_engine.set_exclusion_region((x, y, w, h))
        else:
            self.crypt_engine.set_exclusion_region(None)

    def _save_crypt_settings_all(self):
        """Сохраняет ползунки + микроподстройку кликов (dialog_offset_y) за одно нажатие."""
        self._save_crypt_settings()
        self._save_dialog_profile()

    def _save_crypt_settings(self):
        try:
            cfg = {}
            if os.path.exists(GUI_CONFIG_PATH):
                with open(GUI_CONFIG_PATH, 'r') as f:
                    cfg = json.load(f)
            cfg['crypt_selected']      = [k for k, v in self._crypt_vars.items() if v.get()]
            cfg['crypt_conf']          = round(self.crypt_conf_slider.get(), 2)
            cfg['crypt_accelerations'] = int(self.crypt_accel_slider.get())
            cfg['crypt_break_sec']     = int(self.crypt_break_slider.get())
            cfg['crypt_scroll_speed']  = round(self.crypt_scroll_slider.get(), 1)
            cfg['crypt_max_march_min'] = int(self.crypt_march_slider.get())
            cfg['crypt_oil_check']     = self._oil_check_var.get()
            with open(GUI_CONFIG_PATH, 'w') as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def _load_crypt_settings(self):
        try:
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
            self._oil_check_var.set(cfg.get('crypt_oil_check', True))
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

        # ── Поле ввода кода друга ─────────────────────────────────────────
        self.friend_code_lb = ctk.CTkLabel(self.tab_ref,
                                           text=LANGS[self.current_lang]["friend_code"],
                                           text_color=MD3["on_surface2"])
        self.friend_code_lb.pack(pady=(8, 4))
        self.ref_entry = ctk.CTkEntry(self.tab_ref, placeholder_text="XXXXXX",
                                      height=40, justify="center",
                                      font=ctk.CTkFont(size=16),
                                      fg_color=MD3["card"],
                                      border_color=MD3["outline"],
                                      text_color=MD3["on_surface"],
                                      corner_radius=8)
        self.ref_entry.pack(padx=40, pady=(0, 4), fill="x")
        self.ref_btn = ctk.CTkButton(self.tab_ref,
                                     text=LANGS[self.current_lang]["activate_ref"],
                                     height=38,
                                     fg_color=MD3["primary"],
                                     hover_color=MD3["primary_dim"],
                                     text_color=MD3["bg"],
                                     corner_radius=8,
                                     command=self.activate_ref_action)
        self.ref_btn.pack(padx=40, pady=(0, 8), fill="x")


    def update_slider_labels(self, _=None):
        acc = int(self.conf_slider.get() * 100)
        self.acc_val_lb.configure(text=f"{acc}%")
        spd = round(self.speed_slider.get(), 1)
        self.speed_val_lb.configure(text=f"{spd} {LANGS[self.current_lang]['sec']}")


    def _update_credits_display(self, n: int):
        """Обновляет счётчик кредитов на всех вкладках сразу."""
        self.current_credits = n
        self.credits_label.configure(text=str(n))
        self.crypt_credits_label.configure(text=str(n))

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
                # Прячем баннер полностью если нет broadcast и пользователь авторизован
                if data.get("email"):
                    self.info_banner.pack_forget()
        except: pass


    def _on_nav_toggle(self):
        """Dim nav controls when auto-navigation is disabled."""
        enabled = self.nav_enabled_var.get()
        state = "normal" if enabled else "disabled"
        for w in (self.nav_step_slider, self.nav_wait_slider,
                  self.nav_cx_entry, self.nav_cy_entry):
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
        """Show a red dot on screen at the joystick center position."""
        import tkinter as tk
        try:
            cx = int(self.nav_cx_entry.get())
            cy = int(self.nav_cy_entry.get())
        except ValueError:
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

    def _save_settings(self):
        try:
            cfg = {
                'center_x':     self.nav_cx_entry.get(),
                'center_y':     self.nav_cy_entry.get(),
                'step':         int(self.nav_step_slider.get()),
                'conf':         round(self.conf_slider.get(), 2),
                'scan_interval': round(self.speed_slider.get(), 1),
                'move_wait':    round(self.nav_wait_slider.get(), 1),
            }
            cfg["max_inland_steps"]      = int(self.nav_inland_slider.get())
            cfg["ocean_land_ratio"]      = int(self.nav_ocean_slider.get()) / 100.0
            cfg["min_water_px"]          = int(self.nav_waterpx_slider.get())
            cfg["diagonal_blind_coeff"]  = round(self.nav_diagblind_slider.get(), 2)
            cfg["nav_footprint_ttl"]     = int(self.nav_footprint_slider.get())
            cfg["return_delta_px"]       = int(self.nav_delta_slider.get())
            cfg["smooth_alpha"]          = int(self.nav_pitch_slider.get())
            with open(GUI_CONFIG_PATH, 'w') as f:
                json.dump(cfg, f, indent=2)
            messagebox.showinfo("OK", "Настройки сохранены")
        except Exception as e:
            messagebox.showerror("Error", f"Не удалось сохранить: {e}")

    def _load_settings(self):
        try:
            if not os.path.exists(GUI_CONFIG_PATH):
                return
            with open(GUI_CONFIG_PATH) as f:
                cfg = json.load(f)
            if 'center_x' in cfg:
                self.nav_cx_entry.delete(0, 'end')
                self.nav_cx_entry.insert(0, str(cfg['center_x']))
            if 'center_y' in cfg:
                self.nav_cy_entry.delete(0, 'end')
                self.nav_cy_entry.insert(0, str(cfg['center_y']))
            if 'step' in cfg:
                self.nav_step_slider.set(cfg['step'])
            if 'conf' in cfg:
                self.conf_slider.set(cfg['conf'])
            if 'scan_interval' in cfg:
                self.speed_slider.set(cfg['scan_interval'])
            if 'move_wait' in cfg:
                self.nav_wait_slider.set(cfg['move_wait'])
            self.nav_inland_slider.set(cfg.get("max_inland_steps", 5))
            self.nav_ocean_slider.set(int(cfg.get("ocean_land_ratio", 0.03) * 100))
            self.nav_waterpx_slider.set(cfg.get("min_water_px", 500))
            self.nav_diagblind_slider.set(cfg.get("diagonal_blind_coeff", 0.5))
            raw_ttl = cfg.get("nav_footprint_ttl", 120)
            self.nav_footprint_slider.set(max(60, min(1200, int(raw_ttl))))
            self.nav_delta_slider.set(int(cfg.get("return_delta_px", 0)))
            self.nav_pitch_slider.set(int(cfg.get("smooth_alpha", 50)))
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
                cx = int(self.nav_cx_entry.get())
                cy = int(self.nav_cy_entry.get())
                step = int(self.nav_step_slider.get())
                scan_interval = float(self.speed_slider.get())
                move_wait = float(self.nav_wait_slider.get())
            except ValueError:
                messagebox.showerror("Error", "Неверные параметры навигации"); return

            try:
                self.engine.start(
                    conf=self.conf_slider.get(),
                    center_x=int(self.nav_cx_entry.get()),
                    center_y=int(self.nav_cy_entry.get()),
                    joystick_step=int(self.nav_step_slider.get()),
                    scan_interval=self.speed_slider.get(),
                    move_wait=self.nav_wait_slider.get(),
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
                self.status_label.configure(text=LANGS[self.current_lang]["status_running"],
                                            text_color="#FFD740")
                self.is_running = True
            except Exception as e:
                messagebox.showerror("Error", f"Engine failed: {e}")
        else:
            self.engine.stop()
            self.start_button.configure(text=LANGS[self.current_lang]["start"],
                                        fg_color=MD3["green_btn"],
                                        hover_color=MD3["green_hover"])
            self.status_label.configure(text=LANGS[self.current_lang]["status_ready"],
                                        text_color=MD3["on_surface2"])
            self.is_running = False


    def _emergency_stop(self):
        """ESC — мгновенная остановка бота."""
        if self.is_running:
            self.engine.stop()
            self.start_button.configure(text=LANGS[self.current_lang]["start"],
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
        # Combo
        if self.is_combo_running:
            self.is_combo_running = False
            self.combo_engine.stop()
            self.combo_start_btn.configure(text="ЗАПУСТИТЬ COMBO",
                                           fg_color=MD3["green_btn"],
                                           hover_color=MD3["green_hover"])
            self.combo_status_label.configure(text="Остановлено (ESC)",
                                              text_color=MD3["on_surface2"])

    def on_target_found(self):
        """Вызывается из фонового потока движка"""
        self.after(0, self._process_found)


    def _process_found(self):
        """Безопасно обновляем UI в главном потоке"""
        res = spend_credit("exchange")
        if res and res.get("success"):
            self._update_credits_display(res.get("remaining", 0))
        elif res and res.get("low_credits"):
            self.toggle_bot()  # сначала стоп
            webbrowser.open("https://total-hunter.com/dashboard/balance")
            return

        # Визуально переключаем кнопку обратно
        self.toggle_bot()


    def handle_login(self):
        code, expires = generate_link_code()
        if not code:
            messagebox.showerror("Hunter", "Connection error. Check internet and try again.")
            return

        # Show code in button + open devices page
        self.login_button.configure(
            text=f"Code: {code}   (10 min)",
            state="disabled", fg_color="#1B3A4B",
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
        res = get_free_trial()
        messagebox.showinfo("System", res.get("message"))
        self.update_license_info()


    def change_lang(self, val):
        old_val = self.current_lang
        self.current_lang = val
        self._save_gui_config_key("lang", val)
        self.label_title.configure(text=LANGS[val]["title"])
        self.acc_lb.configure(text=LANGS[val]["accuracy"])
        self.speed_lb.configure(text=LANGS[val]["scan_rate"])
        self.start_button.configure(text=LANGS[val]["start"] if not self.is_running else LANGS[val]["stop"])
        self.ref_title_lb.configure(text=LANGS[val]["ref_title"])
        self.friend_code_lb.configure(text=LANGS[val]["friend_code"])
        self.ref_btn.configure(text=LANGS[val]["activate_ref"])
        self.copy_btn.configure(text=LANGS[val]["copy"])
        self.share_lb.configure(text=LANGS[val]["share_text"])
        self.status_label.configure(text=LANGS[val]["status_ready"] if not self.is_running else LANGS[val]["status_running"])

        # Статичные i18n лейблы
        for widget, key in self._i18n_labels:
            widget.configure(text=LANGS[val][key])

        # Вкладки — ищем по имени созданному при запуске (_tab_init_names).
        # btns dict НЕ трогаем — ключи остаются оригинальными навсегда,
        # иначе ломается click-callback (lambda замыкает оригинальное имя).
        btns = self.tabview._segmented_button._buttons_dict
        for tab_key, init_name in self._tab_init_names.items():
            if init_name in btns:
                btns[init_name].configure(text=LANGS[val][tab_key])

        # crypt_start_btn — только если бот не запущен
        if not self.is_crypt_running:
            self.crypt_start_btn.configure(text=LANGS[val]["crypt_start"])
            self.crypt_status_label.configure(text=LANGS[val]["crypt_ready"])

        # Calibration point labels
        for pt_lb, pt_desc_lb, lb_key, desc_key in getattr(self, '_cal_point_label_widgets', []):
            pt_lb.configure(text=LANGS[val][lb_key])
            pt_desc_lb.configure(text=LANGS[val][desc_key])

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

    # ── calibration tab ─────────────────────────────────────────────────────

    def setup_calibration_tab(self):
        from PIL import Image
        PROFILES = self._PROFILES
        _assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

        _cal_title_lb = ctk.CTkLabel(
            self.tab_calibration,
            text=LANGS[self.current_lang]["cal_title"],
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=MD3["on_surface"],
        )
        _cal_title_lb.pack(pady=(12, 2))
        self._i18n_labels.append((_cal_title_lb, "cal_title"))

        _cal_desc_lb = ctk.CTkLabel(
            self.tab_calibration,
            text=LANGS[self.current_lang]["cal_desc"],
            font=ctk.CTkFont(size=12),
            text_color=MD3["on_surface2"],
            justify="center",
        )
        _cal_desc_lb.pack(pady=(0, 6))
        self._i18n_labels.append((_cal_desc_lb, "cal_desc"))

        # ── Фото + описание точек ─────────────────────────────────────────
        points_frame = ctk.CTkFrame(self.tab_calibration, fg_color="transparent")
        points_frame.pack(fill="x", padx=16, pady=(0, 6))

        self._cal_point_label_widgets = []
        for col, (fname, pt_label_key, pt_desc_key, color) in enumerate([
            ("calib_point_a.png", "cal_pt_a_lb", "cal_pt_a_desc", MD3["primary"]),
            ("calib_point_b.png", "cal_pt_b_lb", "cal_pt_b_desc", "#B060FF"),
        ]):
            card = ctk.CTkFrame(points_frame, fg_color=MD3["elevated"],
                                corner_radius=10, border_width=1,
                                border_color=MD3["outline"])
            card.grid(row=0, column=col, padx=(0, 6) if col == 0 else (6, 0), sticky="nsew")
            points_frame.grid_columnconfigure(col, weight=1)

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
                # держим ссылку
                if not hasattr(self, '_cal_images'):
                    self._cal_images = []
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

        # ── Profile dropdown ──────────────────────────────────────────────
        profile_frame = ctk.CTkFrame(self.tab_calibration, fg_color="transparent")
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
            self.tab_calibration,
            text=LANGS[self.current_lang]["cal_not_calibrated"],
            font=ctk.CTkFont(size=13),
            text_color="#FFB300",
        )
        self._cal_status_label.pack(pady=8)

        def _update_status():
            self._cal_status_label.configure(
                text=(
                    f"scale_x={coord_manager.scale_x:.4f}  "
                    f"scale_y={coord_manager.scale_y:.4f}\n"
                    f"anchor=({coord_manager.anchor_x}, {coord_manager.anchor_y})  "
                    f"dialog_offset_y={coord_manager.dialog_offset_y}"
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
            _update_status()
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
            self.withdraw()
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
            self._save_gui_config_key("last_calibration_profile",
                                      self._cal_profile_var.get())
            messagebox.showinfo("Сохранено", f"Профиль сохранён:\n{path}")

        self._cal_auto_btn = ctk.CTkButton(
            self.tab_calibration,
            text=LANGS[self.current_lang]["cal_auto_btn"],
            command=_auto_calibrate,
            fg_color=MD3["blue_btn"],
            hover_color=MD3["blue_hover"],
            text_color=MD3["on_surface"],
            height=40,
            corner_radius=12,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self._cal_auto_btn.pack(fill="x", padx=40, pady=(8, 2))
        self._i18n_labels.append((self._cal_auto_btn, "cal_auto_btn"))

        # ── Кнопка Калибровать — главная (error tonal) ───────────────────
        self._cal_manual_btn = ctk.CTkButton(
            self.tab_calibration,
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
        save_load_row = ctk.CTkFrame(self.tab_calibration, fg_color="transparent")
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

        # ── REF info ──────────────────────────────────────────────────────
        ctk.CTkLabel(
            self.tab_calibration,
            text=f"Эталон 1920×1080:\nА={REF_A} мини-карта   Б={REF_B} серебро",
            font=ctk.CTkFont(size=10),
            text_color=MD3["outline"],
            justify="center",
        ).pack(pady=(20, 0))

        # ── Auto-load on startup ──────────────────────────────────────────
        last = self._load_gui_config().get("last_calibration_profile", "Client")
        self._cal_profile_var.set(last)
        default_path = PROFILES.get(last, PROFILES["Client"])
        if os.path.exists(default_path):
            try:
                coord_manager.load(default_path)
                self._dialog_offset_y_var.set(coord_manager.dialog_offset_y)
                _update_status()
            except Exception:
                pass


if __name__ == "__main__":
    from version import VERSION
    from updater import check_for_updates, run_update_window
    latest_tag, url = check_for_updates(VERSION)
    if latest_tag and url:
        run_update_window(latest_tag, url)

    app = TotalHunterApp()
    app.mainloop()


