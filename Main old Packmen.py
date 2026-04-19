import customtkinter as ctk
import cv2
import numpy as np
import pyautogui
import time
import keyboard
import threading
import os
import math
import random
import json
import tkinter.messagebox as messagebox
import sys


# Импорты ваших модулей
from auth import (get_hwid, check_license, get_free_trial, spend_credit,
                  login_with_google, log_error_to_server, activate_referral)
from engine import HuntEngine


# =================================================================
# --- МАСТЕР-КОНФИГУРАЦИЯ (МЕНЯТЬ ДИАПАЗОНЫ ЗДЕСЬ) ---
# =================================================================
UI_CONFIG = {
    # Формат: (Мин, Макс, По умолчанию)
    "accuracy": (0.01, 1.0, 0.33),      # Точность нейросети (1% - 100%)
    "scan_rate": (0.01, 10.0, 0.6),     # Частота сканирования (сек)
    "pac_speed": (10, 10000, 1000),     # Скорость Пакмана (мс)
    "pac_range": (1, 500, 16),          # Дальность прыжка (px)
    "pac_style": (0, 100, 40),          # Мастер-стиль (0% - 100%)
}


# Коэффициенты для Мастер-ползунка (Стиль ходьбы)
# При 0% -> 100% стиля значения меняются в этих пределах:
STYLE_WEIGHTS = {
    "magnet": (800, 20),    # Магнетизм (от 0% до 100% стиля)
    "inertia": (30, 800),   # Инерция (от 0% до 100% стиля)
    "random": (10, 3000)     # Рандом (от 0% до 100% стиля)
}
# =================================================================


# --- ГЕОМЕТРИЯ (Константы захвата экрана) ---
CENTER_X = 90
CENTER_Y = 925
SCROLL_FACTOR = 0.84
SCAN_AREA = 180
LAND_HSV = [(5, 40, 40), (95, 255, 255)]
WATER_HSV = [(100, 60, 50), (140, 255, 255)]


MEMORY_CANVAS_SIZE = 1200
EATING_RADIUS = 12
STUCK_THRESHOLD = 5
MAX_STEP_BASE = 16
MIN_STEP_BASE = 3


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


LANGS = {
    "RU": {
        "title": "HUNTER PRO & PACMAN", "tab_hunt": "ОХОТА", "tab_ref": "РЕФЕРАЛЫ",
        "start": "ЗАПУСТИТЬ ОХОТУ", "stop": "ОСТАНОВИТЬ", "login_btn": "ВОЙТИ ЧЕРЕЗ GOOGLE",
        "accuracy": "Точность нейросети", "scan_rate": "Частота скана (сек)", "sec": "сек.",
        "clicker_title": "НАСТРОЙКИ ПАКМАНА", "clicker_on": "ВКЛЮЧИТЬ ПАКМАНА",
        "pacman_speed": "Скорость Пакмана (мс)", "pacman_range": "Дальность прыжка (px)",
        "pacman_style": "Стиль ходьбы (Край <-> Хаос)",
        "save": "СОХРАНИТЬ", "load": "ЗАГРУЗИТЬ", "status_ready": "СИСТЕМА ГОТОВА", "status_running": "БОТ РАБОТАЕТ"
    },
    "UA": {
        "title": "HUNTER PRO & PACMAN", "tab_hunt": "ПОЛЮВАННЯ", "tab_ref": "РЕФЕРАЛИ",
        "start": "ЗАПУСТИТИ ПОЛЮВАННЯ", "stop": "ЗУПИНИТИ", "login_btn": "УВІЙТИ ЧЕРЕЗ GOOGLE",
        "accuracy": "Точність нейромережі", "scan_rate": "Частота скану (сек)", "sec": "сек.",
        "clicker_title": "НАЛАШТУВАННЯ ПАКМАНА", "clicker_on": "УВІМКНУТИ ПАКМАНА",
        "pacman_speed": "Швидкість Пакмана (мс)", "pacman_range": "Дальність стрибка (px)",
        "pacman_style": "Стиль ходьби (Край <-> Хаос)",
        "save": "ЗБЕРЕГТИ", "load": "ЗАВАНТАЖИТИ", "status_ready": "СИСТЕМА ГОТОВА", "status_running": "БОТ ПРАЦЮЄ"
    },
    "EN": {
        "title": "HUNTER PRO & PACMAN", "tab_hunt": "HUNTING", "tab_ref": "REFERRALS",
        "start": "START HUNT", "stop": "STOP", "login_btn": "LOGIN WITH GOOGLE",
        "accuracy": "AI Accuracy", "scan_rate": "Scan Rate (sec)", "sec": "sec.",
        "clicker_title": "PACMAN SETTINGS", "clicker_on": "ENABLE PACMAN",
        "pacman_speed": "Pacman Speed (ms)", "pacman_range": "Jump Range (px)",
        "pacman_style": "Movement Style (Edge <-> Chaos)",
        "save": "SAVE", "load": "LOAD", "status_ready": "SYSTEM READY", "status_running": "BOT RUNNING"
    },
    "DE": {
        "title": "HUNTER PRO & PACMAN", "tab_hunt": "JAGD", "tab_ref": "REFERRALS",
        "start": "STARTEN", "stop": "STOPP", "login_btn": "GOOGLE LOGIN",
        "accuracy": "KI-Genauigkeit", "scan_rate": "Scan-Rate (sek)", "sec": "sek.",
        "clicker_title": "PACMAN SETTINGS", "clicker_on": "PACMAN AKTIVIEREN",
        "pacman_speed": "Geschwindigkeit (ms)", "pacman_range": "Sprungweite (px)",
        "pacman_style": "Gehstil (Kante <-> Chaos)",
        "save": "SPEICHERN", "load": "LADEN", "status_ready": "SYSTEM BEREIT", "status_running": "BOT LÄUFT"
    },
    "FR": {
        "title": "HUNTER PRO & PACMAN", "tab_hunt": "CHASSE", "tab_ref": "PARRAINAGE",
        "start": "DÉMARRER", "stop": "ARRÊTER", "login_btn": "CONNEXION GOOGLE",
        "accuracy": "Précision IA", "scan_rate": "Fréquence (sec)", "sec": "sec.",
        "clicker_title": "PACMAN", "clicker_on": "ACTIVER",
        "pacman_speed": "Vitesse (ms)", "pacman_range": "Rayon (px)",
        "pacman_style": "Style (Bord <-> Chaos)",
        "save": "SAUVER", "load": "CHARGER", "status_ready": "PRÊT", "status_running": "EN MARCHE"
    },
    "ES": {
        "title": "HUNTER PRO & PACMAN", "tab_hunt": "CAZA", "tab_ref": "REFERIDOS",
        "start": "INICIAR", "stop": "PARAR", "login_btn": "ENTRAR GOOGLE",
        "accuracy": "Precisión IA", "scan_rate": "Frecuencia (seg)", "sec": "seg.",
        "clicker_title": "AJUSTES", "clicker_on": "ACTIVAR",
        "pacman_speed": "Velocidad (ms)", "pacman_range": "Radio (px)",
        "pacman_style": "Estilo (Borde <-> Caos)",
        "save": "GUARDAR", "load": "CARGAR", "status_ready": "LISTO", "status_running": "BUSCANDO"
    },
    "IT": {
        "title": "HUNTER PRO & PACMAN", "tab_hunt": "CACCIA", "tab_ref": "REFERRAL",
        "start": "AVVIA", "stop": "FERMA", "login_btn": "ACCEDI GOOGLE",
        "accuracy": "Precisione", "scan_rate": "Frequenza (sec)", "sec": "sec.",
        "clicker_title": "PACMAN", "clicker_on": "ATTIVA",
        "pacman_speed": "Velocità (ms)", "pacman_range": "Raggio (px)",
        "pacman_style": "Stile (Bordo <-> Caos)",
        "save": "SALVA", "load": "CARICA", "status_ready": "PRONTO", "status_running": "RICERCA"
    },
    "PL": {
        "title": "HUNTER PRO & PACMAN", "tab_hunt": "ŁOWY", "tab_ref": "POLECONE",
        "start": "START", "stop": "STOP", "login_btn": "LOGIN GOOGLE",
        "accuracy": "Dokładność", "scan_rate": "Częstotliwość (sek)", "sec": "sek.",
        "clicker_title": "PACMAN", "clicker_on": "WŁĄCZ",
        "pacman_speed": "Prędkość (ms)", "pacman_range": "Zasięg (px)",
        "pacman_style": "Styl (Krawędź <-> Chaos)",
        "save": "ZAPISZ", "load": "WCZYTAJ", "status_ready": "GOTOWY", "status_running": "SZUKANIE"
    },
    "PT": {
        "title": "HUNTER PRO & PACMAN", "tab_hunt": "CAÇA", "tab_ref": "REFERÊNCIA",
        "start": "INICIAR", "stop": "PARAR", "login_btn": "ENTRAR GOOGLE",
        "accuracy": "Precisão", "scan_rate": "Frequência (seg)", "sec": "seg.",
        "clicker_title": "PACMAN", "clicker_on": "ATIVAR",
        "pacman_speed": "Velocidade (ms)", "pacman_range": "Raio (px)",
        "pacman_style": "Estilo (Borda <-> Caos)",
        "save": "SALVAR", "load": "CARREGAR", "status_ready": "PRONTO", "status_running": "PROCURANDO"
    },
    "TR": {
        "title": "HUNTER PRO & PACMAN", "tab_hunt": "AV", "tab_ref": "REFERANSLAR",
        "start": "BAŞLAT", "stop": "DURDUR", "login_btn": "GOOGLE GİRİŞ",
        "accuracy": "Doğruluk", "scan_rate": "Tarama Hızı (sn)", "sec": "sn.",
        "clicker_title": "PACMAN", "clicker_on": "PACMAN AÇIK",
        "pacman_speed": "Hız (ms)", "pacman_range": "Menzil (px)",
        "pacman_style": "Yürüyüş (Kenar <-> Kaos)",
        "save": "KAYDET", "load": "YÜKLE", "status_ready": "HAZIR", "status_running": "ARANIYOR"
    }
}


class CombinedHunterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.engine = HuntEngine()
        self.engine.on_found_callback = self.on_target_found
        self.current_lang = "RU"
        self.is_running = False
        self.user_email = None
       
        self.pacman_memory = None
        self.pacman_last_vec = (0, 1)
        self.pacman_stuck_counter = 0


        # Окно справа
        width, height = 520, 950
        screen_width = self.winfo_screenwidth()
        x = screen_width - width
        self.geometry(f"{width}x{height}+{x}+0")
        self.title("Total Battle Hunter Pro & Pacman v2.9")
        self.resizable(False, False)


        self.setup_ui()
        self.update_license_info()
       
        # --- ПРИОРИТЕТНЫЙ ПЕРЕХВАТ Esc (Системный хук) ---
        def esc_handler(event):
            if event.name == 'esc' and event.event_type == 'down':
                self.emergency_stop()
       
        keyboard.hook(esc_handler)


    def create_simple_slider(self, parent, label_key, config_key):
        """Создает ползунок, используя данные из UI_CONFIG"""
        cfg = UI_CONFIG[config_key]
        from_v, to_v, default = cfg[0], cfg[1], cfg[2]


        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=30, pady=(10, 0))
       
        title_lb = ctk.CTkLabel(frame, text=LANGS[self.current_lang][label_key], font=ctk.CTkFont(size=13))
        title_lb.pack(side="top", anchor="w")
       
        val_lb = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(weight="bold"), text_color="#3b8ed0")
        val_lb.pack(side="top", anchor="e", pady=(0, 2))
       
        slider = ctk.CTkSlider(parent, from_=from_v, to=to_v, command=lambda v: self.sync_labels())
        slider.set(default)
        slider.pack(padx=30, pady=(0, 10), fill="x")
       
        return slider, title_lb, val_lb


    def setup_ui(self):
        self.lang_menu = ctk.CTkOptionMenu(self, values=list(LANGS.keys()), command=self.change_lang, width=80)
        self.lang_menu.pack(anchor="ne", padx=20, pady=10)


        self.tabview = ctk.CTkTabview(self, width=480, height=800)
        self.tabview.pack(padx=10, pady=5, fill="both", expand=True)
        self.tab_hunt = self.tabview.add("Hunt")
        self.tab_ref = self.tabview.add("Ref")
       
        self.tabview._segmented_button._buttons_dict["Hunt"].configure(text=LANGS[self.current_lang]["tab_hunt"])
        self.tabview._segmented_button._buttons_dict["Ref"].configure(text=LANGS[self.current_lang]["tab_ref"])


        self.setup_hunt_tab()
        self.setup_ref_tab()


    def setup_hunt_tab(self):
        self.credits_label = ctk.CTkLabel(self.tab_hunt, text="0", font=ctk.CTkFont(size=56, weight="bold"), text_color="#45bf45")
        self.credits_label.pack(pady=10)


        # AI Settings (Берут диапазоны из UI_CONFIG)
        self.s_acc, self.l_acc_t, self.l_acc_v = self.create_simple_slider(self.tab_hunt, "accuracy", "accuracy")
        self.s_rate, self.l_rate_t, self.l_rate_v = self.create_simple_slider(self.tab_hunt, "scan_rate", "scan_rate")


        # Pacman Group
        self.pac_group = ctk.CTkFrame(self.tab_hunt, corner_radius=15, fg_color="#1a1a1a")
        self.pac_group.pack(fill="x", padx=20, pady=20)
       
        self.pac_title = ctk.CTkLabel(self.pac_group, text=LANGS[self.current_lang]["clicker_title"], font=ctk.CTkFont(size=12, weight="bold"), text_color="gray")
        self.pac_title.pack(pady=5)


        self.pacman_switch = ctk.CTkSwitch(self.pac_group, text=LANGS[self.current_lang]["clicker_on"])
        self.pacman_switch.pack(pady=5); self.pacman_switch.select()


        # Мастер-ползунки Пакмана (Берут диапазоны из UI_CONFIG)
        self.s_p_style, self.l_pst_t, self.l_pst_v = self.create_simple_slider(self.pac_group, "pacman_style", "pac_style")
        self.s_p_speed, self.l_ps_t, self.l_ps_v = self.create_simple_slider(self.pac_group, "pacman_speed", "pac_speed")
        self.s_p_range, self.l_pr_t, self.l_pr_v = self.create_simple_slider(self.pac_group, "pacman_range", "pac_range")


        # Кнопки
        c_frame = ctk.CTkFrame(self.tab_hunt, fg_color="transparent")
        c_frame.pack(fill="x", padx=40, pady=5)
        self.save_btn = ctk.CTkButton(c_frame, text=LANGS[self.current_lang]["save"], fg_color="#2b2b2b", command=self.save_settings)
        self.save_btn.pack(side="left", padx=5, expand=True, fill="x")
        self.load_btn = ctk.CTkButton(c_frame, text=LANGS[self.current_lang]["load"], fg_color="#2b2b2b", command=self.load_settings)
        self.load_btn.pack(side="right", padx=5, expand=True, fill="x")


        self.start_button = ctk.CTkButton(self.tab_hunt, text=LANGS[self.current_lang]["start"], height=80, font=ctk.CTkFont(size=24, weight="bold"), fg_color="green", command=self.toggle_bot)
        self.start_button.pack(pady=15, padx=30, fill="x")
       
        self.status_label = ctk.CTkLabel(self.tab_hunt, text=LANGS[self.current_lang]["status_ready"], text_color="gray")
        self.status_label.pack()
        self.sync_labels()


    def sync_labels(self):
        self.l_acc_v.configure(text=f"{int(self.s_acc.get()*100)}%")
        self.l_rate_v.configure(text=f"{round(self.s_rate.get(),2)}s")
        self.l_ps_v.configure(text=f"{int(self.s_p_speed.get())}ms")
        self.l_pr_v.configure(text=f"{int(self.s_p_range.get())}px")
        self.l_pst_v.configure(text=f"{int(self.s_p_style.get())}%")


    def save_settings(self):
        data = {
            "ai_acc": self.s_acc.get(), "ai_rate": self.s_rate.get(),
            "p_on": self.pacman_switch.get(), "p_speed": self.s_p_speed.get(),
            "p_range": self.s_p_range.get(), "p_style": self.s_p_style.get()
        }
        with open("settings.json", "w") as f: json.dump(data, f)


    def load_settings(self):
        if not os.path.exists("settings.json"): return
        with open("settings.json", "r") as f: d = json.load(f)
        try:
            self.s_acc.set(d.get("ai_acc", UI_CONFIG["accuracy"][2]))
            self.s_rate.set(d.get("ai_rate", UI_CONFIG["scan_rate"][2]))
            if d.get("p_on"): self.pacman_switch.select()
            else: self.pacman_switch.deselect()
            self.s_p_speed.set(d.get("p_speed", UI_CONFIG["pac_speed"][2]))
            self.s_p_range.set(d.get("p_range", UI_CONFIG["pac_range"][2]))
            self.s_p_style.set(d.get("p_style", UI_CONFIG["pac_style"][2]))
            self.sync_labels()
        except: pass


    def pacman_step(self):
        """Интеллектуальная интерполяция на основе STYLE_WEIGHTS"""
        try:
            # Нормализованный стиль (0.0 - 1.0)
            style = (self.s_p_style.get() - UI_CONFIG["pac_style"][0]) / (UI_CONFIG["pac_style"][1] - UI_CONFIG["pac_style"][0])
           
            # Линейная интерполяция весов
            m_start, m_end = STYLE_WEIGHTS["magnet"]
            calc_magnet = m_start + (m_end - m_start) * style
           
            i_start, i_end = STYLE_WEIGHTS["inertia"]
            calc_inertia = i_start + (i_end - i_start) * style
           
            r_start, r_end = STYLE_WEIGHTS["random"]
            calc_random = r_start + (r_end - r_start) * style
           
            p_range = int(self.s_p_range.get())
            if self.pacman_memory is None:
                self.pacman_memory = np.zeros((MEMORY_CANVAS_SIZE, MEMORY_CANVAS_SIZE), dtype=np.uint8)


            shot = pyautogui.screenshot(region=(CENTER_X - SCAN_AREA // 2, CENTER_Y - SCAN_AREA // 2, SCAN_AREA, SCAN_AREA))
            frame = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
            lc, mc = SCAN_AREA // 2, MEMORY_CANVAS_SIZE // 2
           
            cv2.circle(self.pacman_memory, (mc, mc), EATING_RADIUS, 255, -1)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            land, water = cv2.inRange(hsv, LAND_HSV[0], LAND_HSV[1]), cv2.inRange(hsv, WATER_HSV[0], WATER_HSV[1])
            offset = SCAN_AREA // 2
            local_memory = self.pacman_memory[mc-offset:mc+offset, mc-offset:mc+offset]
            void = cv2.bitwise_or(water, local_memory)
            food = cv2.bitwise_and(land, land, mask=cv2.bitwise_not(void))
           
            magnet_mask = cv2.bitwise_and(food, cv2.dilate(void, np.ones((5,5), np.uint8), iterations=1))
            safe_mask = np.zeros_like(food)
            cv2.rectangle(safe_mask, (lc-p_range, lc-p_range), (lc+p_range, lc+p_range), 255, -1)
           
            targets = np.column_stack(np.where(cv2.bitwise_and(food, safe_mask) > 0))
            if len(targets) > 0:
                best_t, best_s = None, -1e9
                mag_pts = cv2.bitwise_and(magnet_mask, safe_mask)
                for pt in targets:
                    ty, tx = pt
                    dx, dy = tx - lc, ty - lc
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist < MIN_STEP_BASE or dist > MAX_STEP_BASE: continue
                    nx, ny = dx/dist, dy/dist
                    dot = nx * self.pacman_last_vec[0] + ny * self.pacman_last_vec[1]
                   
                    score = (dist * 0.6) + (dot * calc_inertia) + ((1 if mag_pts[ty, tx] > 0 else 0) * calc_magnet) + random.uniform(0, calc_random)
                    if score > best_s: best_s, best_t = score, (tx, ty)
               
                if best_t:
                    tx, ty = best_t
                    fx, fy = int(np.clip(CENTER_X + (tx - lc), CENTER_X-p_range, CENTER_X+p_range)), int(np.clip(CENTER_Y + (ty - lc), CENTER_Y-p_range, CENTER_Y+p_range))
                    M = np.float32([[1, 0, -(fx - CENTER_X) * SCROLL_FACTOR], [0, 1, -(fy - CENTER_Y) * SCROLL_FACTOR]])
                    self.pacman_memory = cv2.warpAffine(self.pacman_memory, M, (MEMORY_CANVAS_SIZE, MEMORY_CANVAS_SIZE), borderMode=cv2.BORDER_CONSTANT, borderValue=0)
                    mvx, mvy = fx - CENTER_X, fy - CENTER_Y
                    d = math.sqrt(mvx**2 + mvy**2)
                    if d > 0: self.pacman_last_vec = (mvx/d, mvy/d)
                    pyautogui.click(fx, fy); self.pacman_stuck_counter = 0; return True
           
            self.pacman_stuck_counter += 1
            if self.pacman_stuck_counter >= STUCK_THRESHOLD:
                self.pacman_memory = cv2.erode(self.pacman_memory, np.ones((3,3), np.uint8), iterations=1); self.pacman_stuck_counter = 0
            return False
        except: return False


    def pacman_loop_thread(self):
        while self.is_running:
            if self.pacman_switch.get():
                self.pacman_step(); time.sleep(self.s_p_speed.get() / 1000.0)
            else: time.sleep(0.5)


    def toggle_bot(self):
        if not self.is_running:
            self.is_running = True
            self.engine.start(self.s_acc.get(), self.s_rate.get(), False, "F3", "F1")
            self.start_button.configure(text=LANGS[self.current_lang]["stop"], fg_color="red")
            self.status_label.configure(text=LANGS[self.current_lang]["status_running"], text_color="yellow")
            threading.Thread(target=self.pacman_loop_thread, daemon=True).start()
        else: self.stop_bot()


    def stop_bot(self):
        self.is_running = False; self.engine.stop()
        self.start_button.configure(text=LANGS[self.current_lang]["start"], fg_color="green")
        self.status_label.configure(text=LANGS[self.current_lang]["status_ready"], text_color="gray")


    def emergency_stop(self):
        """ПРИОРИТЕТНАЯ МГНОВЕННАЯ ОСТАНОВКА"""
        # Убираем все условия, команда стоп должна проходить всегда
        self.after(0, self.stop_bot)


    def on_target_found(self): self.after(0, self._process_found)
    def _process_found(self): spend_credit(); self.stop_bot()


    def update_license_info(self):
        try:
            data = check_license()
            if data and data.get("credits"): self.credits_label.configure(text=str(data["credits"]))
        except: pass


    def handle_login(self): login_with_google(); self.after(5000, self.update_license_info)
    def setup_ref_tab(self): pass


    def change_lang(self, val):
        self.current_lang = val
        self.tabview._segmented_button._buttons_dict["Hunt"].configure(text=LANGS[val]["tab_hunt"])
        self.tabview._segmented_button._buttons_dict["Ref"].configure(text=LANGS[val]["tab_ref"])
        self.save_btn.configure(text=LANGS[val]["save"])
        self.load_btn.configure(text=LANGS[val]["load"])
        self.start_button.configure(text=LANGS[val]["start"] if not self.is_running else LANGS[val]["stop"])
        self.pacman_switch.configure(text=LANGS[val]["clicker_on"])
        self.pac_title.configure(text=LANGS[val]["clicker_title"])
        self.l_acc_t.configure(text=LANGS[val]["accuracy"])
        self.l_rate_t.configure(text=LANGS[val]["scan_rate"])
        self.l_ps_t.configure(text=LANGS[val]["pacman_speed"])
        self.l_pr_t.configure(text=LANGS[val]["pacman_range"])
        self.l_pst_t.configure(text=LANGS[val]["pacman_style"])
        self.status_label.configure(text=LANGS[val]["status_ready"] if not self.is_running else LANGS[val]["status_running"])
        self.sync_labels()


if __name__ == "__main__":
    app = CombinedHunterApp(); app.mainloop()

