# build.spec — PyInstaller для TotalHunter
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# customtkinter нужно тащить целиком (темы, шрифты)
import customtkinter as _ctk
_ctk_path = os.path.dirname(_ctk.__file__)

datas = [
    # Звуковой файл биржи
    ('Logo_exchange.wav', '.'),
    # YOLO модели (зашифрованные .pte — .pt в EXE не попадают)
    ('exchange.pte', '.'),
    ('targets/crypts.pte', 'targets'),
    # Иконки склепов (PNG)
    ('targets/*.png', 'targets'),
    # Шаблоны для template_finder (визуальная навигация склепов)
    ('targets_2', 'targets_2'),
    # Картинки калибровки + иконка приложения
    ('assets',        'assets'),
    # Профили калибровки
    ('profiles',      'profiles'),
    # CustomTkinter (темы, шрифты, изображения)
    (_ctk_path,       'customtkinter'),
]

# ultralytics тащит yaml-конфиги и прочие data-файлы
datas += collect_data_files('ultralytics')

hiddenimports = [
    # GUI
    'customtkinter',
    'PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw',
    # Computer vision
    'cv2',
    'numpy',
    # YOLO
    'ultralytics',
    'ultralytics.engine.model',
    'ultralytics.engine.predictor',
    'ultralytics.models.yolo',
    'ultralytics.nn.tasks',
    'ultralytics.utils',
    'ultralytics.utils.torch_utils',
    # Screen capture & input
    'mss', 'mss.windows',
    'pyautogui',
    'keyboard',
    'pynput', 'pynput.keyboard', 'pynput.mouse',
    # OCR
    'pytesseract',
    # Network / auth
    'requests', 'urllib3',
    'google.auth', 'google.auth.transport', 'google.auth.transport.requests',
    'google.oauth2', 'google.oauth2.id_token',
    # Misc
    'packaging', 'pkg_resources',
    'tkinter', 'tkinter.ttk', 'tkinter.messagebox',
    # Шифрование моделей (условный импорт — PyInstaller не видит автоматически)
    'model_crypto',
    'cryptography', 'cryptography.fernet',
    'cryptography.hazmat', 'cryptography.hazmat.primitives',
    'cryptography.hazmat.backends',
    'tempfile',
    # Прочие модули проекта (условные импорты)
    'auto_calibration', 'calibration_ui', 'calibration',
    'button_finder', 'template_finder', 'human_input',
    'nav_logger', 'navigator_beacon',
    'version', 'updater',
]

hiddenimports += collect_submodules('ultralytics')
hiddenimports += collect_submodules('torch')

# Исключаем лишнее чтобы не раздувать сборку
excludes = [
    'matplotlib', 'scipy', 'pandas', 'jupyter', 'notebook',
    'IPython', 'jedi', 'sphinx', 'pytest',
]

_torch_binaries = collect_dynamic_libs('torch')

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=_torch_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook_torch.py'],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TotalHunter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico',
    manifest='application.manifest',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['*.pt', '*.pte'],   # модели не жмём — ломаются
    name='TotalHunter',
)
