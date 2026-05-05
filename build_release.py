"""
build_release.py — Total Hunter v1.0.2 Protected Build
=======================================================
Гибридная сборка: Nuitka компилирует ключевые модули в .pyd (C++),
затем PyInstaller упаковывает всё в EXE.

Запуск:
    cd C:/BattleBot
    python build_release.py
"""

import subprocess
import sys
import os
import shutil
import glob

# Force UTF-8 output so Cyrillic/arrow chars don't crash on cp1251 console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.abspath(__file__))

# Модули с чувствительной логикой → компилируем в .pyd
PROTECTED_MODULES = [
    "auth.py",
    "engine.py",
    "navigator.py",
    "crypt_hunter.py",
    "minimap_reader.py",
    "coord_manager.py",
    "model_crypto.py",
    "updater.py",
    "version.py",
]


def run(cmd, **kwargs):
    print(f"\n>>> {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=ROOT, **kwargs)


def compile_module(src: str):
    """Компилирует .py в .pyd через Nuitka (--module)."""
    name = os.path.basename(src)
    print(f"  [Nuitka] Compiling {name} -> .pyd")
    run([
        sys.executable, "-m", "nuitka",
        "--module",
        "--remove-output",
        "--no-pyi-file",
        "--assume-yes-for-downloads",
        src,
    ])


def find_pyd(module_name: str):
    """Ищет скомпилированный .pyd файл."""
    base = module_name.replace(".py", "")
    pattern = os.path.join(ROOT, f"{base}*.pyd")
    found = glob.glob(pattern)
    return found[0] if found else None


def clean():
    """Удаляет старые dist/ и build/."""
    for d in ["dist", "build"]:
        path = os.path.join(ROOT, d)
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"  Удалено: {d}/")


def check_assets():
    """Проверяет наличие всех необходимых ассетов."""
    required = [
        "exchange.pte",
        "targets/crypts.pte",
        "assets/icon.ico",
        "version.py",
        "build.spec",
    ]
    missing = []
    for f in required:
        if not os.path.exists(os.path.join(ROOT, f)):
            missing.append(f)
    if missing:
        print(f"\nWARN  Отсутствуют файлы: {missing}")
        print("    Запусти python model_crypto.py если нет .pte файлов")
        return False
    return True


def main():
    print("=" * 60)
    print("  Total Hunter — Protected Build v1.0.2")
    print("  Nuitka (ключевые модули) + PyInstaller (упаковка)")
    print("=" * 60)

    os.chdir(ROOT)

    # Шаг 1: Проверяем ассеты
    print("\n[1/4] Проверка ассетов...")
    if not check_assets():
        sys.exit(1)
    print("  OK Все ассеты на месте")

    # Шаг 2: Компиляция чувствительных модулей в .pyd
    print("\n[2/4] Kompiliatsiia modulei (Nuitka -> C++)...")
    compiled = []
    skipped = []
    for mod in PROTECTED_MODULES:
        src = os.path.join(ROOT, mod)
        if os.path.exists(src):
            try:
                compile_module(src)
                pyd = find_pyd(mod)
                if pyd:
                    compiled.append(os.path.basename(pyd))
                    print(f"  OK {mod} → {os.path.basename(pyd)}")
                else:
                    print(f"  WARN  {mod}: .pyd не найден, используем .py")
                    skipped.append(mod)
            except subprocess.CalledProcessError as e:
                print(f"  WARN  {mod}: ошибка компиляции ({e}), используем .py")
                skipped.append(mod)
        else:
            print(f"  –  {mod}: файл не найден, пропускаем")

    print(f"\n  Скомпилировано: {len(compiled)} модулей")
    if skipped:
        print(f"  Пропущено (будут в .py): {skipped}")

    # Шаг 3: Очистка и PyInstaller сборка
    print("\n[3/4] Очистка dist/ и build/...")
    clean()

    print("\n[4/4] PyInstaller упаковка...")
    run([sys.executable, "-m", "PyInstaller", "build.spec", "-y"])

    # Шаг 5: Удаляем исходные .py для скомпилированных модулей из dist
    # (PyInstaller может включить и .py и .pyd — оставляем только .pyd)
    dist_internal = os.path.join(ROOT, "dist", "TotalHunter", "_internal")
    if os.path.exists(dist_internal):
        for mod in PROTECTED_MODULES:
            py_in_dist = os.path.join(dist_internal, mod)
            if os.path.exists(py_in_dist):
                os.remove(py_in_dist)
                print(f"  Удалён из dist: {mod} (заменён .pyd)")

    print("\n" + "=" * 60)
    print("  OK СБОРКА ЗАВЕРШЕНА")
    print(f"  EXE: dist/TotalHunter/TotalHunter.exe")
    print(f"  Защищено модулей: {len(compiled)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
