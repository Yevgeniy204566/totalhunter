import os
import sys
import glob
import ctypes

if getattr(sys, 'frozen', False):
    base = sys._MEIPASS

    torch_lib = os.path.join(base, 'torch', 'lib')
    torch_dir = os.path.join(base, 'torch')

    # Регистрируем папки через AddDllDirectory
    for d in (torch_lib, torch_dir, base):
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except Exception:
                pass
            os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')

    # Принудительно загружаем все DLL из torch/lib ДО того как torch их запросит
    kernel32 = ctypes.WinDLL('kernel32.dll', use_last_error=True)
    kernel32.LoadLibraryW.restype = ctypes.c_void_p

    load_order = [
        'libiomp5md.dll',
        'libiompstubs5md.dll',
        'c10.dll',
        'torch_global_deps.dll',
        'torch_cpu.dll',
        'torch.dll',
        'torch_python.dll',
        'shm.dll',
        'uv.dll',
    ]

    for dll_name in load_order:
        dll_path = os.path.join(torch_lib, dll_name)
        if os.path.exists(dll_path):
            kernel32.LoadLibraryW(dll_path)
