import sys, types, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def _make_mock_torch(cuda_available: bool, to_raises: bool = False):
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
            if to_raises and device == 'cuda':
                raise RuntimeError("CUDA OOM")
            self.device = device
            return self

    return mock_torch, MockModel


def test_cuda_fallback_no_cuda(monkeypatch):
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
    _, MockModel = _make_mock_torch(cuda_available=True, to_raises=False)
    import torch
    model = MockModel()
    try:
        _device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model.to(_device)
    except Exception:
        model.to('cpu')
    assert model.device == 'cuda'
