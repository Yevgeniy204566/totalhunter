"""
found_sound.py — звук находки биржи: один выключатель для Биржи 1.0, 2.0 и РОЙ.

Владелец 2026-09-27: на вкладке Бирж звук можно отключить — тогда звуковое оповещение
о найденных биржах не поступает. Флаг ставит GUI (переключатель на вкладке Бирж),
читают все три места, где играет звук находки.
"""
import winsound

enabled = True


def play(path, beep_ms: int = 500) -> None:
    if not enabled:
        return
    try:
        if path:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
    except Exception:
        pass
    try:
        winsound.Beep(1000, beep_ms)
    except Exception:
        pass
