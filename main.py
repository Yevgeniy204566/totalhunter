



import json
import os
import customtkinter as ctk
from auth import (get_hwid, check_license, get_free_trial, spend_credit,
                  login_with_google, log_error_to_server, activate_referral)
from engine import HuntEngine
from crypt_hunter import CryptHunter
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
        "title": "Total Hunter", "tab_hunt": "БИРЖИ", "tab_ref": "РЕФЕРАЛЫ",
        "get_trial": "ПОЛУЧИТЬ 300 ПОПЫТОК", "start": "ЗАПУСТИТЬ ОХОТУ", "stop": "ОСТАНОВИТЬ",
        "no_credits": "У вас 0 поисков!", "login_btn": "ВОЙТИ ЧЕРЕЗ GOOGLE",
        "banned": "ВАШ АККАУНТ ЗАБЛОКИРОВАН", "ref_title": "ПАРТНЕРСКАЯ ПРОГРАММА",
        "my_code": "ВАШ КОД ДЛЯ ПРИГЛАШЕНИЯ:", "friend_code": "КОД ПРИГЛАСИТЕЛЯ (+50):",
        "activate_ref": "АКТИВИРОВАТЬ", "ref_used": "БОНУС АКТИВИРОВАН ✅",
        "accuracy": "Точность поиска", "scan_rate": "Частота сканирования", "sec": "сек.",
        "copy": "КОПИРОВАТЬ", "share_text": "ПОДЕЛИТЕСЬ КОДОМ И ПОЛУЧАЙТЕ %", "copied": "Скопировано!",
        "clicker_title": "Синхронизация Clickermann", "clicker_on": "ВКЛЮЧИТЬ", "key_start": "Старт:", "key_stop": "Стоп:",
        "status_ready": "СИСТЕМА ГОТОВА", "status_running": "СТАТУС: В ПОИСКЕ...",
        "add_oil": "Добавь масла",
    },
    "EN": {
        "title": "Total Hunter", "tab_hunt": "EXCHANGE", "tab_ref": "REFERRALS",
        "get_trial": "GET 300 TRIALS", "start": "START HUNT", "stop": "STOP",
        "no_credits": "0 credits left!", "login_btn": "LOGIN WITH GOOGLE",
        "banned": "ACCOUNT BANNED", "ref_title": "REFERRAL SYSTEM",
        "my_code": "YOUR INVITE CODE:", "friend_code": "INVITER CODE (+50):",
        "activate_ref": "ACTIVATE", "ref_used": "BONUS ACTIVE ✅",
        "accuracy": "Detection Accuracy", "scan_rate": "Scan Interval", "sec": "sec.",
        "copy": "COPY", "share_text": "SHARE CODE AND GET %", "copied": "Copied!",
        "clicker_title": "Clickermann Sync", "clicker_on": "ENABLED", "key_start": "Start:", "key_stop": "Stop:",
        "status_ready": "READY", "status_running": "STATUS: SEARCHING...",
        "add_oil": "Add Oil",
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
        self.current_lang = "RU"
        self.user_email = None
        self.current_credits = 0
        self.my_ref_id = "---"
        self.is_running = False # ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННОЙ СОСТОЯНИЯ
       
        self.title("Total Battle Hunter Pro v2.4")
        self.geometry("460x1010")
        self.resizable(False, False)
        self.configure(fg_color=MD3["bg"])

        # Шапка: «Поверх окон» слева, выбор языка справа
        _header = ctk.CTkFrame(self, fg_color="transparent")
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
            command=lambda: webbrowser.open("https://totalhunter.pro/dashboard"),
        ).pack(side="right", padx=(0, 2))


        # Заголовок и HWID
        self.label_title = ctk.CTkLabel(self, text=LANGS[self.current_lang]["title"],
                                        font=ctk.CTkFont(size=22, weight="bold"),
                                        text_color=MD3["on_surface"])
        self.label_title.pack(pady=(0, 5))
        self.label_hwid = ctk.CTkLabel(self, text=f"HWID: {get_hwid()}",
                                       font=ctk.CTkFont(size=10),
                                       text_color=MD3["outline"])
        self.label_hwid.pack()
        self.label_email = ctk.CTkLabel(self, text="",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        text_color=MD3["primary"])
        self.label_email.pack()

        # ── Глобальный инфо-баннер (логин / объявления) ──────────────────
        self.info_banner = ctk.CTkFrame(self, fg_color=MD3["elevated"],
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
        self.tabview = ctk.CTkTabview(self, width=420, height=780,
                                      fg_color=MD3["card"],
                                      segmented_button_fg_color=MD3["elevated"],
                                      segmented_button_selected_color=MD3["tab_selected"],
                                      segmented_button_selected_hover_color=MD3["tab_selected_hover"],
                                      segmented_button_unselected_color=MD3["elevated"],
                                      segmented_button_unselected_hover_color=MD3["card"],
                                      text_color=MD3["on_surface"],
                                      text_color_disabled=MD3["on_surface2"],
                                      corner_radius=12)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
       
        self.tab_crypt = self.tabview.add("СКЛЕПЫ")
        self.tab_hunt  = self.tabview.add(LANGS[self.current_lang]["tab_hunt"])
        self.tab_ref   = self.tabview.add(LANGS[self.current_lang]["tab_ref"])
        self.tab_calibration = self.tabview.add("КАЛИБРОВКА")


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
                      command=lambda: webbrowser.open("https://totalhunter.pro/balance"),
                      ).pack(side="left", padx=(8, 0))


        # ─── Карточка «Нейросеть» ────────────────────────────────────────
        nn_frame = ctk.CTkFrame(self.tab_hunt, fg_color=MD3["elevated"],
                                corner_radius=12, border_width=1,
                                border_color=MD3["outline"])
        nn_frame.pack(fill="x", padx=20, pady=(4, 2))
        ctk.CTkLabel(nn_frame, text="Нейросеть",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MD3["on_surface"]).pack(anchor="w", padx=12, pady=(4, 2))

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
        ctk.CTkLabel(nav_main_frame, text="Навигация",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MD3["on_surface"]).pack(anchor="w", padx=12, pady=(4, 2))

        # Шаг джойстика
        self.nav_step_frame = ctk.CTkFrame(nav_main_frame, fg_color="transparent")
        self.nav_step_frame.pack(fill="x", padx=12, pady=(2, 0))
        ctk.CTkLabel(self.nav_step_frame, text="Шаг:",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
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
        ctk.CTkLabel(self.nav_wait_frame, text="Скорость (сек/шаг):",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
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
        ctk.CTkLabel(self.nav_inland_frame, text="Глубина нырка (экранов):",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
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
                                   text="Дополнительно",
                                   font=ctk.CTkFont(size=14, weight="bold"),
                                   text_color=MD3["on_surface"])
        self.nav_lb.pack(side="left")
        self.nav_enabled_var = ctk.BooleanVar(value=True)
        self.nav_toggle = ctk.CTkSwitch(
            self.nav_header_frame,
            text="Авто",
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
        ctk.CTkLabel(self.nav_ocean_frame, text="Граница океан/суша (%):",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
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
        ctk.CTkLabel(self.nav_waterpx_frame, text="Мин. размер водоёма:",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
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

        # Угол нырка (угловой демпфер)
        self.nav_pitch_frame = ctk.CTkFrame(nav_sliders_frame, fg_color="transparent")
        self.nav_pitch_frame.pack(fill="x", padx=10, pady=(0, 2))
        ctk.CTkLabel(self.nav_pitch_frame, text="Угол нырка (°):",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
        self.nav_pitch_val = ctk.CTkLabel(self.nav_pitch_frame, text="15°",
                                           font=ctk.CTkFont(size=14, weight="bold"),
                                           text_color=MD3["value_text"])
        self.nav_pitch_val.pack(side="right")
        self.nav_pitch_slider = ctk.CTkSlider(
            nav_sliders_frame, from_=5, to=30, number_of_steps=25,
            command=self._update_nav_labels,
            button_color=MD3["primary"],
            button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_pitch_slider.set(15)
        self.nav_pitch_slider.pack(padx=10, pady=(0, 2), fill="x")

        # Порог перекрытия следов (%)
        self.nav_overlap_frame = ctk.CTkFrame(nav_sliders_frame, fg_color="transparent")
        self.nav_overlap_frame.pack(fill="x", padx=10, pady=(0, 2))
        ctk.CTkLabel(self.nav_overlap_frame, text="Перекрытие следов (%):",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
        self.nav_overlap_val = ctk.CTkLabel(self.nav_overlap_frame, text="50%",
                                             font=ctk.CTkFont(size=14, weight="bold"),
                                             text_color=MD3["value_text"])
        self.nav_overlap_val.pack(side="right")
        self.nav_overlap_slider = ctk.CTkSlider(
            nav_sliders_frame, from_=10, to=100, number_of_steps=18,
            command=self._update_nav_labels,
            button_color=MD3["primary"], button_hover_color=MD3["primary_dim"],
            progress_color=MD3["primary"],
        )
        self.nav_overlap_slider.set(50)
        self.nav_overlap_slider.pack(padx=10, pady=(0, 2), fill="x")

        # Память следов (TTL секунды)
        self.nav_footprint_frame = ctk.CTkFrame(nav_sliders_frame, fg_color="transparent")
        self.nav_footprint_frame.pack(fill="x", padx=10, pady=(0, 2))
        ctk.CTkLabel(self.nav_footprint_frame, text="Память следов (сек):",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
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

        # Кнопка сохранения настроек
        self.save_btn = ctk.CTkButton(self.nav_frame, text="Сохранить настройки",
                                      height=28,
                                      fg_color=MD3["green_btn"],
                                      hover_color=MD3["green_hover"],
                                      text_color=MD3["on_surface"],
                                      corner_radius=8,
                                      command=self._save_settings)
        self.save_btn.pack(padx=10, pady=(2, 4), fill="x")

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
                      command=lambda: webbrowser.open("https://totalhunter.pro/balance"),
                      ).pack(side="left", padx=(8, 0))

        # ─── Сетка иконок склепов ────────────────────────────
        icons_label = ctk.CTkLabel(self.tab_crypt, text="Выберите типы склепов:",
                                   font=ctk.CTkFont(size=13),
                                   text_color=MD3["on_surface2"])
        icons_label.pack(pady=(2, 1))

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
                sep_row = row  # разделитель на той же строке что начинается группа
                sep = ctk.CTkFrame(scroll_frame, height=2, fg_color=MD3["separator"])
                sep.grid(row=sep_row * 2, column=0, columnspan=COLS,
                         padx=4, pady=(6, 2), sticky="ew")

            cell = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            cell.grid(row=row * 2 + 1, column=col, padx=4, pady=4)

            # Иконка
            icon_path = os.path.join(targets_dir, f"{crypt_name}.png")
            try:
                pil_img = Image.open(icon_path).resize((48, 48))
                ctk_img = ctk.CTkImage(pil_img, size=(48, 48))
                self._crypt_icons.append(ctk_img)
                ctk.CTkLabel(cell, image=ctk_img, text="").pack()
            except Exception:
                ctk.CTkLabel(cell, text="?", width=48, height=48).pack()

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

        def _slider_row(label_text, default_text):
            """Хелпер: строка-заголовок слайдера."""
            row = ctk.CTkFrame(settings_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=(4, 0))
            ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(size=13),
                         text_color=MD3["on_surface2"]).pack(side="left")
            val = ctk.CTkLabel(row, text=default_text,
                               font=ctk.CTkFont(size=14, weight="bold"),
                               text_color=MD3["value_text"])
            val.pack(side="right")
            return val

        # Точность поиска
        self.crypt_conf_val = _slider_row("Точность поиска", "70%")
        self.crypt_conf_slider = ctk.CTkSlider(settings_frame, from_=0.1, to=0.9,
                                               command=self._update_crypt_labels,
                                               button_color=MD3["primary"],
                                               button_hover_color=MD3["primary_dim"],
                                               progress_color=MD3["primary"])
        self.crypt_conf_slider.set(0.7)
        self.crypt_conf_slider.pack(padx=10, pady=(2, 4), fill="x")

        # Ускорение марша
        self.crypt_accel_val = _slider_row("Ускорение марша (0–5)", "3")
        self.crypt_accel_slider = ctk.CTkSlider(settings_frame, from_=0, to=5,
                                                number_of_steps=5,
                                                command=self._update_crypt_labels,
                                                button_color=MD3["primary"],
                                                button_hover_color=MD3["primary_dim"],
                                                progress_color=MD3["primary"])
        self.crypt_accel_slider.set(3)
        self.crypt_accel_slider.pack(padx=10, pady=(2, 4), fill="x")

        # Перерыв между склепами
        self.crypt_break_val = _slider_row("Перерыв между склепами", "10 с")
        self.crypt_break_slider = ctk.CTkSlider(settings_frame, from_=3, to=300,
                                                command=self._update_crypt_labels,
                                                button_color=MD3["primary"],
                                                button_hover_color=MD3["primary_dim"],
                                                progress_color=MD3["primary"])
        self.crypt_break_slider.set(10)
        self.crypt_break_slider.pack(padx=10, pady=(2, 4), fill="x")

        # Дальность марша Картера
        self.crypt_march_val = _slider_row("Дальность марша Картера", "15 мин")
        self.crypt_march_slider = ctk.CTkSlider(settings_frame, from_=5, to=30,
                                                command=self._update_crypt_labels,
                                                button_color=MD3["primary"],
                                                button_hover_color=MD3["primary_dim"],
                                                progress_color=MD3["primary"])
        self.crypt_march_slider.set(15)
        self.crypt_march_slider.pack(padx=10, pady=(2, 4), fill="x")

        # Скорость скроллинга (YOLO = scroll_speed + 0.2 сек)
        self.crypt_scroll_val = _slider_row("Скорость скроллинга", "скан 1.2 с")
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
        ctk.CTkLabel(misc_row, text="Профиль:", font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
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
        ctk.CTkLabel(offset_row, text="Микроподстройка кликов ↑↓:",
                     font=ctk.CTkFont(size=13),
                     text_color=MD3["on_surface2"]).pack(side="left")
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
        ctk.CTkButton(settings_frame, text="💾  Сохранить настройки",
                      height=32,
                      fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
                      text_color=MD3["on_surface"], corner_radius=8,
                      command=self._save_crypt_settings_all
                      ).pack(padx=10, pady=(6, 6), fill="x")

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
            self.tab_crypt, text="ЗАПУСТИТЬ СБОР СКЛЕПОВ",
            height=56, font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
            text_color=MD3["on_surface"], corner_radius=16,
            command=self.toggle_crypt_bot
        )
        self.crypt_start_btn.pack(pady=(3, 4), padx=20, fill="x")

        # Статус
        self.crypt_status_label = ctk.CTkLabel(
            self.tab_crypt, text="ГОТОВО", text_color=MD3["on_surface2"]
        )
        self.crypt_status_label.pack(pady=(0, 4))

        self._load_crypt_settings()

    def _update_crypt_labels(self, _=None):
        conf = int(self.crypt_conf_slider.get() * 100)
        self.crypt_conf_val.configure(text=f"{conf}%")
        accel = int(self.crypt_accel_slider.get())
        march_min = int(self.crypt_march_slider.get())
        self.crypt_march_val.configure(text=f"{march_min} мин")
        self.crypt_accel_val.configure(text=str(accel))
        brk = int(self.crypt_break_slider.get())
        self.crypt_break_val.configure(text=f"{brk} с")
        sc = round(self.crypt_scroll_slider.get(), 1)
        self.crypt_scroll_val.configure(text=f"скан {sc + 0.2:.1f} с")

    def on_crypt_found(self, crypt_type: str):
        """Вызывается ПОСЛЕ возвращения Картера (коллекция завершена)."""
        self._crypt_found_count += 1
        count = self._crypt_found_count
        self.after(0, lambda: self.crypt_status_label.configure(
            text=f"Собрано: {count} | последний: {crypt_type}"
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
            self.crypt_start_btn.configure(text="ЗАПУСТИТЬ СБОР СКЛЕПОВ",
                                           fg_color=MD3["green_btn"],
                                           hover_color=MD3["green_hover"])
            self.crypt_status_label.configure(text=t, text_color=c)
            self.crypt_countdown_label.configure(text="")
            self.crypt_timer_detail_label.configure(text="")
        self.after(0, _update)

    def toggle_crypt_bot(self):
        if self.is_crypt_running:
            self.is_crypt_running = False
            self.crypt_engine.stop()
            self.crypt_start_btn.configure(text="ЗАПУСТИТЬ СБОР СКЛЕПОВ",
                                           fg_color=MD3["green_btn"],
                                           hover_color=MD3["green_hover"])
            self.crypt_status_label.configure(text="Остановлено", text_color=MD3["on_surface2"])
            self.crypt_countdown_label.configure(text="")
            self.crypt_timer_detail_label.configure(text="")
        else:
            selected = [k for k, v in self._crypt_vars.items() if v.get()]
            if not selected:
                self.crypt_status_label.configure(
                    text="Выберите хотя бы один тип!", text_color="#FFB300"
                )
                return
            self.is_crypt_running = True
            self._crypt_found_count = 0
            self.crypt_status_label.configure(text="СТАТУС: В ПОИСКЕ...", text_color=MD3["secondary"])
            self.crypt_start_btn.configure(text="ОСТАНОВИТЬ",
                                           fg_color=MD3["error"],
                                           hover_color=MD3["error_hover"])
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
            )

    def _on_always_on_top(self):
        """Переключить режим «поверх всех окон» и обновить зону исключения YOLO."""
        on_top = self.always_on_top_var.get()
        self.wm_attributes('-topmost', on_top)
        if on_top:
            # Снапаем окно в верхний правый угол — безопасная зона:
            # мини-карта и точка калибровки A находятся слева (x≈90),
            # все элементы игры для кликов/OCR заканчиваются до x=1350.
            right_x = self.winfo_screenwidth() - 460
            self.geometry(f"460x1010+{right_x}+0")
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
            self._update_crypt_labels()
        except Exception:
            pass

    def setup_ref_tab(self):
        # Заголовок Рефералки
        self.ref_title_lb = ctk.CTkLabel(self.tab_ref,
                                         text=LANGS[self.current_lang]["ref_title"],
                                         font=ctk.CTkFont(size=20, weight="bold"),
                                         text_color=MD3["primary"])
        self.ref_title_lb.pack(pady=(16, 4))

        # ── Реферальный баланс ────────────────────────────────────────────
        ref_bal_card = ctk.CTkFrame(self.tab_ref, fg_color=MD3["elevated"],
                                    corner_radius=12, border_width=1,
                                    border_color=MD3["outline"])
        ref_bal_card.pack(padx=30, pady=(0, 10), fill="x")
        ctk.CTkLabel(ref_bal_card, text="Реферальный баланс",
                     font=ctk.CTkFont(size=11), text_color=MD3["on_surface2"],
                     ).pack(pady=(10, 0))
        self.ref_balance_label = ctk.CTkLabel(ref_bal_card, text="0 ◆",
                                              font=ctk.CTkFont(size=28, weight="bold"),
                                              text_color="#FFD700")
        self.ref_balance_label.pack(pady=(2, 6))
        ctk.CTkButton(ref_bal_card, text="💸  Перевести на баланс  →",
                      height=32, corner_radius=8,
                      fg_color=MD3["blue_btn"], hover_color=MD3["blue_hover"],
                      text_color=MD3["on_surface"],
                      command=lambda: webbrowser.open("https://totalhunter.pro/dashboard/referrals"),
                      ).pack(padx=10, pady=(0, 10), fill="x")

        self.share_lb = ctk.CTkLabel(self.tab_ref,
                                     text=LANGS[self.current_lang]["share_text"],
                                     font=ctk.CTkFont(size=13),
                                     text_color=MD3["on_surface2"], wraplength=350)
        self.share_lb.pack(pady=(0, 8))


        # Свой код
        self.my_code_frame = ctk.CTkFrame(self.tab_ref, fg_color=MD3["elevated"],
                                          corner_radius=12)
        self.my_code_frame.pack(padx=40, pady=10, fill="x")
        self.my_code_lb = ctk.CTkLabel(self.my_code_frame,
                                       text=LANGS[self.current_lang]["my_code"],
                                       font=ctk.CTkFont(size=10),
                                       text_color=MD3["on_surface2"])
        self.my_code_lb.pack(pady=(10, 0))
        self.my_code_val = ctk.CTkLabel(self.my_code_frame, text="---",
                                        font=ctk.CTkFont(size=32, weight="bold"),
                                        text_color=MD3["on_surface"])
        self.my_code_val.pack(pady=(0, 5))
        self.copy_btn = ctk.CTkButton(self.my_code_frame,
                                      text=LANGS[self.current_lang]["copy"],
                                      width=100, height=30,
                                      fg_color=MD3["card"],
                                      hover_color=MD3["outline"],
                                      text_color=MD3["secondary"],
                                      corner_radius=8,
                                      command=self.copy_code)
        self.copy_btn.pack(pady=(0, 15))


        # Поле Ввода кода друга
        self.friend_code_lb = ctk.CTkLabel(self.tab_ref,
                                           text=LANGS[self.current_lang]["friend_code"],
                                           text_color=MD3["on_surface2"])
        self.friend_code_lb.pack(pady=(30, 5))
        self.ref_entry = ctk.CTkEntry(self.tab_ref, placeholder_text="XXXXXX",
                                      height=45, justify="center",
                                      font=ctk.CTkFont(size=16),
                                      fg_color=MD3["card"],
                                      border_color=MD3["outline"],
                                      text_color=MD3["on_surface"],
                                      corner_radius=8)
        self.ref_entry.pack(padx=50, pady=5, fill="x")
        self.ref_btn = ctk.CTkButton(self.tab_ref,
                                     text=LANGS[self.current_lang]["activate_ref"],
                                     height=40,
                                     fg_color=MD3["primary"],
                                     hover_color=MD3["primary_dim"],
                                     text_color=MD3["bg"],
                                     corner_radius=8,
                                     command=self.activate_ref_action)
        self.ref_btn.pack(padx=50, pady=10, fill="x")


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
            if data.get("my_ref_id"):
                self.my_ref_id = data["my_ref_id"]
                self.my_code_val.configure(text=self.my_ref_id)
            ref_credits = data.get("ref_credits", 0)
            self.ref_balance_label.configure(text=f"{ref_credits} ◆")
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
        self.nav_step_val.configure(text=f"{int(self.nav_step_slider.get())} px")
        self.nav_wait_val.configure(text=f"{self.nav_wait_slider.get():.1f} с")
        self.nav_inland_val.configure(text=f"{int(self.nav_inland_slider.get())}")
        self.nav_ocean_val.configure(text=f"{int(self.nav_ocean_slider.get())}%")
        self.nav_waterpx_val.configure(text=f"{int(self.nav_waterpx_slider.get())}")
        if hasattr(self, 'nav_pitch_slider'):
            self.nav_pitch_val.configure(text=f"{int(self.nav_pitch_slider.get())}°")
        if hasattr(self, 'nav_overlap_slider'):
            self.nav_overlap_val.configure(text=f"{int(self.nav_overlap_slider.get())}%")
        ttl = int(self.nav_footprint_slider.get())
        self.nav_footprint_val.configure(
            text=f"{ttl // 60} мин" if ttl >= 60 else f"{ttl} с"
        )
        if hasattr(self, 'nav_pitch_slider'):
            self.nav_pitch_val.configure(text=f"{int(self.nav_pitch_slider.get())}°")

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
            cfg["max_pitch_delta"]       = int(self.nav_pitch_slider.get())
            cfg["ocean_land_ratio"]      = int(self.nav_ocean_slider.get()) / 100.0
            cfg["min_water_px"]            = int(self.nav_waterpx_slider.get())
            cfg["max_pitch_delta"]         = int(self.nav_pitch_slider.get())
            cfg["max_footprint_overlap"]   = int(self.nav_overlap_slider.get())
            cfg["nav_footprint_ttl"]       = int(self.nav_footprint_slider.get())
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
            self.nav_pitch_slider.set(cfg.get("max_pitch_delta", 15))
            self.nav_ocean_slider.set(int(cfg.get("ocean_land_ratio", 0.03) * 100))
            self.nav_waterpx_slider.set(cfg.get("min_water_px", 500))
            self.nav_pitch_slider.set(cfg.get("max_pitch_delta", 15))
            self.nav_overlap_slider.set(cfg.get("max_footprint_overlap", 50))
            raw_ttl = cfg.get("nav_footprint_ttl", 120)
            self.nav_footprint_slider.set(max(60, min(1200, int(raw_ttl))))
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
            # TODO: re-enable credits check before commercial launch
            # if self.current_credits <= 0:
            #     messagebox.showwarning("Hunter", LANGS[self.current_lang]["no_credits"]); return
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
                    max_pitch_delta=int(self.nav_pitch_slider.get()),
                    max_footprint_overlap=self.nav_overlap_slider.get() / 100.0,
                    footprint_ttl=float(self.nav_footprint_slider.get()),
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
            self.crypt_start_btn.configure(text="ЗАПУСТИТЬ СБОР СКЛЕПОВ",
                                           fg_color=MD3["green_btn"],
                                           hover_color=MD3["green_hover"])
            self.crypt_status_label.configure(text="Остановлено (ESC)",
                                              text_color=MD3["on_surface2"])

    def on_target_found(self):
        """Вызывается из фонового потока движка"""
        self.after(0, self._process_found)


    def _process_found(self):
        """Безопасно обновляем UI в главном потоке"""
        # TODO: re-enable before commercial launch
        # res = spend_credit()
        # if res and res.get("success"):
        #     self._update_credits_display(res.get("remaining", 0))

        # Визуально переключаем кнопку обратно
        self.toggle_bot()


    def handle_login(self):
        login_with_google()
        self.after(5000, self.update_license_info)


    def copy_code(self):
        code = self.my_code_val.cget("text")
        if code != "---":
            self.clipboard_clear()
            self.clipboard_append(code)
            messagebox.showinfo("OK", LANGS[self.current_lang]["copied"])


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
        self.label_title.configure(text=LANGS[val]["title"])
        self.acc_lb.configure(text=LANGS[val]["accuracy"])
        self.speed_lb.configure(text=LANGS[val]["scan_rate"])
        self.start_button.configure(text=LANGS[val]["start"] if not self.is_running else LANGS[val]["stop"])
        self.ref_title_lb.configure(text=LANGS[val]["ref_title"])
        self.my_code_lb.configure(text=LANGS[val]["my_code"])
        self.friend_code_lb.configure(text=LANGS[val]["friend_code"])
        self.ref_btn.configure(text=LANGS[val]["activate_ref"])
        self.copy_btn.configure(text=LANGS[val]["copy"])
        self.share_lb.configure(text=LANGS[val]["share_text"])
        self.status_label.configure(text=LANGS[val]["status_ready"] if not self.is_running else LANGS[val]["status_running"])
       
        btns = self.tabview._segmented_button._buttons_dict
        if LANGS[old_val]["tab_hunt"] in btns:
            btns[LANGS[old_val]["tab_hunt"]].configure(text=LANGS[val]["tab_hunt"])
        if LANGS[old_val]["tab_ref"] in btns:
            btns[LANGS[old_val]["tab_ref"]].configure(text=LANGS[val]["tab_ref"])
           
        self.update_slider_labels()
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

        ctk.CTkLabel(
            self.tab_calibration,
            text="Калибровка экрана",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=MD3["on_surface"],
        ).pack(pady=(12, 2))

        ctk.CTkLabel(
            self.tab_calibration,
            text="Откройте игру в привычном режиме, затем установите две точки.",
            font=ctk.CTkFont(size=12),
            text_color=MD3["on_surface2"],
            justify="center",
        ).pack(pady=(0, 6))

        # ── Фото + описание точек ─────────────────────────────────────────
        points_frame = ctk.CTkFrame(self.tab_calibration, fg_color="transparent")
        points_frame.pack(fill="x", padx=16, pady=(0, 6))

        for col, (fname, pt_label, pt_desc, color) in enumerate([
            ("calib_point_a.png", "Точка A — мини-карта",
             "Уменьшите зум\nмини-карты до мин.\nКликните по центру.", MD3["primary"]),
            ("calib_point_b.png", "Точка B — Серебро",
             "Наведите на иконку\nСеребра до появления «+».\nКликните по «+».", "#B060FF"),
        ]):
            card = ctk.CTkFrame(points_frame, fg_color=MD3["elevated"],
                                corner_radius=10, border_width=1,
                                border_color=MD3["outline"])
            card.grid(row=0, column=col, padx=(0, 6) if col == 0 else (6, 0), sticky="nsew")
            points_frame.grid_columnconfigure(col, weight=1)

            ctk.CTkLabel(card, text=pt_label,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=color).pack(pady=(8, 2))
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
            ctk.CTkLabel(card, text=pt_desc,
                         font=ctk.CTkFont(size=11),
                         text_color=MD3["on_surface2"],
                         justify="center").pack(pady=(4, 8))

        # ── Profile dropdown ──────────────────────────────────────────────
        profile_frame = ctk.CTkFrame(self.tab_calibration, fg_color="transparent")
        profile_frame.pack(fill="x", padx=40, pady=4)
        ctk.CTkLabel(profile_frame, text="Профиль:",
                     text_color=MD3["on_surface2"]).pack(side="left")
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
            text="Не откалиброван",
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

        # ── Кнопка Калибровать — главная (error tonal) ───────────────────
        ctk.CTkButton(
            self.tab_calibration,
            text="КАЛИБРОВАТЬ",
            command=_calibrate,
            fg_color=MD3["error"],
            hover_color=MD3["error_hover"],
            text_color=MD3["on_surface"],
            height=56,
            corner_radius=16,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(fill="x", padx=40, pady=(8, 6))

        # ── Сохранить / Загрузить — в одну строку ────────────────────────
        save_load_row = ctk.CTkFrame(self.tab_calibration, fg_color="transparent")
        save_load_row.pack(fill="x", padx=40, pady=(0, 8))
        ctk.CTkButton(save_load_row, text="💾  Сохранить",
                      command=_save_profile,
                      fg_color=MD3["green_btn"], hover_color=MD3["green_hover"],
                      text_color=MD3["on_surface"], corner_radius=8,
                      height=36).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(save_load_row, text="📂  Загрузить",
                      command=_load_profile,
                      fg_color=MD3["blue_btn"], hover_color=MD3["blue_hover"],
                      text_color=MD3["on_surface"], corner_radius=8,
                      height=36).pack(side="left", expand=True, fill="x", padx=(4, 0))

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
    app = TotalHunterApp()
    app.mainloop()


