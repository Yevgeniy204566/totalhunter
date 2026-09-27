"""Звук находки биржи: один выключатель для 1.0, 2.0 и РОЙ (владелец 2026-09-27)."""
import found_sound


def _capture(monkeypatch):
    calls = []
    monkeypatch.setattr(found_sound.winsound, "PlaySound", lambda *a: calls.append(("play", a[0])))
    monkeypatch.setattr(found_sound.winsound, "Beep", lambda *a: calls.append(("beep",)))
    return calls


def test_sound_plays_when_enabled(monkeypatch):
    calls = _capture(monkeypatch)
    monkeypatch.setattr(found_sound, "enabled", True)
    found_sound.play("Logo_exchange.wav")
    assert calls == [("play", "Logo_exchange.wav")]


def test_no_sound_at_all_when_disabled(monkeypatch):
    calls = _capture(monkeypatch)
    monkeypatch.setattr(found_sound, "enabled", False)
    found_sound.play("Logo_exchange.wav")
    found_sound.play(None)
    assert calls == []


def test_missing_file_falls_back_to_beep(monkeypatch):
    calls = _capture(monkeypatch)
    monkeypatch.setattr(found_sound, "enabled", True)
    found_sound.play(None)
    assert calls == [("beep",)]


def test_exchange_10_navigator_respects_the_switch(monkeypatch):
    """Биржа 1.0: legacy-обработчик находки не играет звук при выключенном динамике."""
    import navigator
    calls = []
    monkeypatch.setattr(navigator.winsound, "PlaySound", lambda *a: calls.append("play"))
    monkeypatch.setattr(navigator.winsound, "Beep", lambda *a: calls.append("beep"))
    nav = navigator.PacmanEngine.__new__(navigator.PacmanEngine)
    nav.is_running = True
    nav.sound_path = "Logo_exchange.wav"
    nav.on_found_callback = None
    monkeypatch.setattr(found_sound, "enabled", False)
    nav._on_exchange_found()
    assert calls == []
    monkeypatch.setattr(found_sound, "enabled", True)
    nav._on_exchange_found()
    assert calls == ["play"]
