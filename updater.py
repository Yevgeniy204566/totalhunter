import os
import sys
import queue
import zipfile
import tempfile
import threading
import subprocess

import requests

VERSION_API = "https://api.total-hunter.com/version/latest"
EXE_NAME    = "TotalHunter.exe"


def _ver_tuple(v: str):
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except Exception:
        return (0,)


def check_for_updates(current_version: str):
    """Return (latest_version, download_url) if update available, else (None, None)."""
    if not getattr(sys, "frozen", False):
        return None, None
    try:
        r = requests.get(VERSION_API, timeout=8)
        r.raise_for_status()
        data = r.json()
        latest  = data.get("version", "")
        dl_url  = data.get("download_url", "")
        if not latest or not dl_url:
            return None, None
        if _ver_tuple(latest) <= _ver_tuple(current_version):
            return None, None
        return latest, dl_url
    except Exception:
        pass
    return None, None


def download_and_install(download_url: str, progress_callback=None) -> str:
    """Download zip, extract to temp, write update.bat. Returns bat path."""
    tmp_dir  = tempfile.mkdtemp(prefix="th_update_")
    zip_path = os.path.join(tmp_dir, ZIP_NAME)

    r = requests.get(download_url, stream=True, timeout=300)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    done  = 0
    with open(zip_path, "wb") as f:
        for chunk in r.iter_content(65536):
            if chunk:
                f.write(chunk)
                done += len(chunk)
                if progress_callback and total:
                    progress_callback(done / total)

    extract_dir = os.path.join(tmp_dir, "new")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    exe_dir  = os.path.dirname(sys.executable)
    bat_path = os.path.join(tmp_dir, "update.bat")
    with open(bat_path, "w") as f:
        f.write("@echo off\n")
        f.write(f'taskkill /f /im {EXE_NAME} 2>nul\n')
        f.write("timeout /t 2 /nobreak >nul\n")
        f.write(f'xcopy /s /y /e "{extract_dir}\\*" "{exe_dir}\\"\n')
        f.write(f'start "" "{os.path.join(exe_dir, EXE_NAME)}"\n')
        f.write('del "%~f0"\n')

    return bat_path


def run_update_window(latest_tag: str, download_url: str):
    """Show CTk progress window, download and apply update."""
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.title("Total Hunter — Update")
    root.geometry("420x170")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    ctk.CTkLabel(root,
                 text=f"New version available: {latest_tag}",
                 font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(22, 6))

    bar = ctk.CTkProgressBar(root, width=360)
    bar.set(0)
    bar.pack(pady=6)

    lbl = ctk.CTkLabel(root, text="Downloading...",
                       font=ctk.CTkFont(size=12), text_color="#C8D8F0")
    lbl.pack()

    q = queue.Queue()

    def _download():
        def cb(p):
            q.put(("progress", p))
        try:
            bat = download_and_install(download_url, progress_callback=cb)
            q.put(("done", bat))
        except Exception as e:
            q.put(("error", str(e)))

    def _poll():
        try:
            while True:
                msg = q.get_nowait()
                if msg[0] == "progress":
                    bar.set(msg[1])
                    lbl.configure(text=f"Downloading... {int(msg[1] * 100)}%")
                elif msg[0] == "done":
                    lbl.configure(text="Installing update...")
                    root.update()
                    subprocess.Popen(["cmd", "/c", msg[1]],
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                    root.destroy()
                    sys.exit(0)
                elif msg[0] == "error":
                    lbl.configure(text=f"Update failed: {msg[1][:60]}")
                    return
        except queue.Empty:
            pass
        root.after(150, _poll)

    threading.Thread(target=_download, daemon=True).start()
    root.after(150, _poll)
    root.mainloop()
