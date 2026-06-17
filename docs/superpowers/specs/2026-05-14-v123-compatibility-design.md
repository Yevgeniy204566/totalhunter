# Spec: Total Hunter v1.2.3 — Compatibility Fixes

**Date:** 2026-05-14  
**Status:** Approved (Claude + Gemini audit)  
**Scope:** Fix STATUS_ILLEGAL_INSTRUCTION crash on old CPUs + CUDA fallback  
**Out of scope:** DPI awareness (deferred to v1.2.4)

---

## Problem

Clients with pre-2013 CPUs (Intel Sandy/Ivy Bridge, AMD Bulldozer, and also
some newer Gemini Lake / Apollo Lake Celeron/Pentium without AVX) crash with
`STATUS_ILLEGAL_INSTRUCTION` (c000001d) when `auth.pyd` or other Nuitka
modules are loaded. Root cause: Nuitka's default build with LTO enabled allows
MSVC to emit AVX/AVX2 instructions tuned to the developer's machine.

Secondary problem: machines without a CUDA-capable GPU (or with broken cudnn /
insufficient VRAM) can crash when YOLO is initialized, because
`torch.cuda.is_available()` can return `True` yet `.to('cuda')` still fails.

---

## Fix 1 — Nuitka SSE2 baseline (`build_release.py`)

**File:** `build_release.py`, function `compile_module()`

Add `--lto=no` to the Nuitka command. This disables Link-Time Optimization,
preventing the cross-file vectorization that produces AVX2 instructions. With
LTO off, MSVC compiles each translation unit independently and stays at the
SSE2 baseline (all x64 CPUs since 2003).

**Constraint:** Must NOT have `--msvc-conf=...` or any `/arch:AVX*` env vars
(`CL`, `_CL_`) in the build environment.

```python
run([
    sys.executable, "-m", "nuitka",
    "--module",
    "--remove-output",
    "--no-pyi-file",
    "--assume-yes-for-downloads",
    "--lto=no",   # SSE2 baseline — old CPU compatibility
    src,
])
```

**Expected result:** All 9 `.pyd` modules compile without AVX instructions.
Clients with Sandy Bridge, Ivy Bridge, Bulldozer, and Gemini Lake CPUs can run
the bot.

---

## Fix 2 — YOLO CPU fallback (`model_crypto.py` + `engine.py`)

**Two call sites:**

1. `model_crypto.py::yolo_from_encrypted()` — after `YOLO(tmp_path)`
2. `engine.py::HuntEngine.__init__()` — after `YOLO(pt_path)` (plain .pt branch)

**Pattern to apply at both sites:**

```python
import torch
try:
    _device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model.to(_device)
except Exception:
    model.to('cpu')  # save-point: cuda visible but broken/OOM
```

**Why double try/except:** `cuda.is_available()` can return `True` when the
driver is present but `.to('cuda')` still raises (OOM, missing cudnn DLL,
driver mismatch). The outer except guarantees CPU fallback in all edge cases.

The encrypted branch goes through `yolo_from_encrypted()` exclusively — fixing
it there covers `HuntEngine` for all production builds. The plain `.pt` branch
in `engine.py` is a dev/fallback path that also needs the fix.

---

## Fix 3 — Version metadata sync

| File | Field | Old | New |
|---|---|---|---|
| `version.py` | `VERSION` | `"1.2.2"` | `"1.2.3"` |
| `installer.iss` | `MyAppVersion` | `"1.2.0"` | `"1.2.3"` |

The stale `1.2.0` in `installer.iss` would cause support confusion (client
reports version X, actual binary is X+3).

---

## Out of scope

- **DPI awareness** (`SetProcessDpiAwareness(2)`) — deferred to v1.2.4.
  Must be the very first call in `main.py` before any GUI import. Needs
  separate testing on 125%/150% DPI machines to avoid coordinate regression.
- torch/numpy AVX inside `.whl` — cannot fix without switching wheel versions;
  diagnose via Event Viewer if `--lto=no` alone doesn't resolve a specific case.

---

## Startup diagnostics (main.py)

Add a brief log line at bot start so AnyDesk sessions show applied fixes immediately:

```python
print(f"[v1.2.3] Device: {_device} | LTO: disabled")
```

---

## Test criteria

1. Build completes: `len(compiled) == 9` modules, no `WARN`
2. Bot starts on a machine without CUDA: no crash, log shows `device=cpu`
3. Bot starts on a machine with CUDA: normal operation, `device=cuda`
4. Installer version string = `1.2.3` in Add/Remove Programs
