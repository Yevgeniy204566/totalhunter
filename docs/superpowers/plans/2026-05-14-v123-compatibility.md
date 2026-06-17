# v1.2.3 Compatibility Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix STATUS_ILLEGAL_INSTRUCTION crash on old CPUs (no AVX2) and add CUDA graceful fallback for machines without a compatible GPU.

**Architecture:** Three targeted edits — one build flag in `build_release.py`, one CUDA fallback pattern applied in two YOLO load sites (`model_crypto.py` + `engine.py`), and version metadata sync in `version.py` + `installer.iss`.

**Tech Stack:** Python 3.13, Nuitka, PyInstaller, ultralytics YOLO, torch, Inno Setup

---

## File Map

| File | Change |
|---|---|
| `build_release.py` | Add `--lto=no` to `compile_module()` |
| `model_crypto.py` | CUDA fallback after `YOLO(tmp_path)` in `yolo_from_encrypted()` |
| `engine.py` | CUDA fallback after `YOLO(pt_path)` in `HuntEngine.__init__()` |
| `version.py` | `VERSION = "1.2.2"` → `"1.2.3"` |
| `installer.iss` | `MyAppVersion "1.2.0"` → `"1.2.3"` |
| `server/main.py` | bump `CURRENT_VERSION` if present |

---

## Task 1: Version metadata sync

**Files:**
- Modify: `version.py:1`
- Modify: `installer.iss:2`

- [ ] **Step 1: Bump version.py**

Open `version.py`. Change line 1:
```python
VERSION = "1.2.3"
```

- [ ] **Step 2: Bump installer.iss**

Open `installer.iss`. Change line 2:
```
#define MyAppVersion "1.2.3"
```

- [ ] **Step 3: Check server version constant**

Run:
```
grep -r "1\.2\.2" server/
```
If `server/main.py` has a hardcoded `CURRENT_VERSION = "1.2.2"` — change it to `"1.2.3"`.

- [ ] **Step 4: Write version test**

Create `server/tests/test_version_bump.py`:
```python
def test_version_is_123():
    from version import VERSION
    assert VERSION == "1.2.3", f"Expected 1.2.3, got {VERSION}"
```

- [ ] **Step 5: Run test**

```
cd C:\BattleBot
python -m pytest server/tests/test_version_bump.py -v
```
Expected: `PASSED`

- [ ] **Step 6: Commit**

```
git add version.py installer.iss server/tests/test_version_bump.py
git commit -m "chore: bump version to v1.2.3"
```

---

## Task 2: Nuitka SSE2 baseline — `--lto=no`

**Files:**
- Modify: `build_release.py:49-56`

- [ ] **Step 1: Add --lto=no flag**

Open `build_release.py`. In `compile_module()`, the `run([...])` call currently is:
```python
run([
    sys.executable, "-m", "nuitka",
    "--module",
    "--remove-output",
    "--no-pyi-file",
    "--assume-yes-for-downloads",
    src,
])
```

Change it to:
```python
run([
    sys.executable, "-m", "nuitka",
    "--module",
    "--remove-output",
    "--no-pyi-file",
    "--assume-yes-for-downloads",
    "--lto=no",
    src,
])
```

- [ ] **Step 2: Verify no AVX env vars**

Run in the same terminal where you'll build:
```
echo %CL%
echo %_CL_%
```
Both should be empty or not contain `/arch:AVX`. If they do — unset before building.

- [ ] **Step 3: Commit**

```
git add build_release.py
git commit -m "fix: --lto=no in Nuitka — SSE2 baseline for old CPU compatibility"
```

---

## Task 3: CUDA fallback in `model_crypto.py`

**Files:**
- Modify: `model_crypto.py:69-82`

- [ ] **Step 1: Write failing test**

Create `server/tests/test_cuda_fallback.py`:
```python
import sys, types

def _make_mock_torch(cuda_available: bool, to_raises: bool = False):
    """Build a minimal torch mock."""
    mock_torch = types.ModuleType("torch")

    class MockCuda:
        @staticmethod
        def is_available():
            return cuda_available

    mock_torch.cuda = MockCuda()
    sys.modules["torch"] = mock_torch

    class MockModel:
        def __init__(self):
            self.device = "cpu"
        def to(self, device):
            if to_raises:
                raise RuntimeError("CUDA OOM")
            self.device = device
            return self

    return mock_torch, MockModel


def test_cuda_fallback_no_cuda(monkeypatch):
    """No CUDA available → device stays cpu."""
    _, MockModel = _make_mock_torch(cuda_available=False)
    import torch
    model = MockModel()
    try:
        _device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model.to(_device)
    except Exception:
        model.to('cpu')
    assert model.device == 'cpu'


def test_cuda_fallback_cuda_oom(monkeypatch):
    """CUDA available but .to() raises → fallback to cpu."""
    _, MockModel = _make_mock_torch(cuda_available=True, to_raises=True)
    import torch
    model = MockModel()
    try:
        _device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model.to(_device)
    except Exception:
        model.to('cpu')
    assert model.device == 'cpu'


def test_cuda_fallback_cuda_ok(monkeypatch):
    """CUDA available and working → device is cuda."""
    _, MockModel = _make_mock_torch(cuda_available=True, to_raises=False)
    import torch
    model = MockModel()
    try:
        _device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model.to(_device)
    except Exception:
        model.to('cpu')
    assert model.device == 'cuda'
```

- [ ] **Step 2: Run test to verify it passes (pattern test)**

```
python -m pytest server/tests/test_cuda_fallback.py -v
```
Expected: 3 × PASSED (tests validate the pattern itself).

- [ ] **Step 3: Apply fallback in model_crypto.py**

Open `model_crypto.py`. Replace `yolo_from_encrypted()` (lines 69-82):

```python
def yolo_from_encrypted(enc_path: str):
    """Загружает YOLO-модель из зашифрованного .pte файла через temp-файл."""
    import tempfile
    import torch
    from ultralytics import YOLO
    raw = load_model_bytes(enc_path)
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        model = YOLO(tmp_path)
    finally:
        os.remove(tmp_path)
    try:
        _device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model.to(_device)
    except Exception:
        model.to('cpu')
        _device = 'cpu'
    print(f"[TH v1.2.3] YOLO device: {_device}")
    return model
```

- [ ] **Step 4: Commit**

```
git add model_crypto.py server/tests/test_cuda_fallback.py
git commit -m "fix: CUDA graceful fallback in yolo_from_encrypted"
```

---

## Task 4: CUDA fallback in `engine.py` (plain .pt branch)

**Files:**
- Modify: `engine.py:20-26`

- [ ] **Step 1: Apply fallback to plain .pt load path**

Open `engine.py`. The `__init__` currently has:
```python
if os.path.exists(enc_path):
    from model_crypto import yolo_from_encrypted
    self.model = yolo_from_encrypted(enc_path)
    self.model_path = enc_path
else:
    self.model_path = pt_path
    self.model = YOLO(pt_path)
```

Change to:
```python
if os.path.exists(enc_path):
    from model_crypto import yolo_from_encrypted
    self.model = yolo_from_encrypted(enc_path)
    self.model_path = enc_path
else:
    import torch
    self.model_path = pt_path
    self.model = YOLO(pt_path)
    try:
        _device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(_device)
    except Exception:
        self.model.to('cpu')
        _device = 'cpu'
    print(f"[TH v1.2.3] YOLO device (pt): {_device}")
```

- [ ] **Step 2: Commit**

```
git add engine.py
git commit -m "fix: CUDA graceful fallback in HuntEngine plain .pt branch"
```

---

## Task 5: Final verification

- [ ] **Step 1: Run all tests**

```
cd C:\BattleBot
python -m pytest server/tests/test_version_bump.py server/tests/test_cuda_fallback.py -v
```
Expected: 4 × PASSED

- [ ] **Step 2: Verify build_release.py has --lto=no**

```
grep "lto" build_release.py
```
Expected: `"--lto=no",`

- [ ] **Step 3: Verify version strings**

```
python -c "from version import VERSION; print(VERSION)"
grep "MyAppVersion" installer.iss
```
Expected: `1.2.3` in both outputs.

- [ ] **Step 4: Final commit + tag**

```
git add -A
git status
git commit -m "feat: v1.2.3 — old CPU + CUDA compatibility"
```

---

## Notes

- **Do NOT run `python build_release.py` as part of this plan** — building is a separate step done manually after the plan is complete.
- The encrypted branch (`yolo_from_encrypted`) is the production path. The plain `.pt` branch in `engine.py` is for dev/testing without encrypted models — both need the fix.
- If a client still crashes after v1.2.3, ask them for Event Viewer → Application log → the exact `.pyd` or `.dll` that faulted. That points to a third-party AVX in torch/numpy wheels, which is a separate fix.
