# Хангоф #36 — 2026-05-05
**Сессия:** PyInstaller EXE сборка — полный цикл от нуля до работающего билда

---

## Что сделано сегодня

### EXE Упаковка (PyInstaller)
| # | Задача | Статус |
|---|--------|--------|
| 1 | build.spec создан — onedir, все data files, ultralytics/torch hidden imports | ✅ |
| 2 | model_crypto.py — Fernet шифрование .pt → .pte моделей | ✅ |
| 3 | Фикс WinError 1114 — preload torch DLL в main.py перед всеми импортами | ✅ |
| 4 | targets_2/ добавлен в сборку — шаблоны для визуальной навигации склепов | ✅ |
| 5 | unittest убран из excludes — PyTorch его требует | ✅ |
| 6 | model_crypto + все условные импорты добавлены в hiddenimports | ✅ |
| 7 | EXE запускается, GUI открывается, биржи и склепы работают | ✅ |

### Бот (main.py + crypt_hunter.py)
| # | Задача | Статус |
|---|--------|--------|
| 1 | Диагностические _status сообщения склепов закомментированы (30 строк) | ✅ |
| 2 | "Собрано/Collected", "Ждём Картера/Waiting Carter" переведены RU/EN | ✅ |
| 3 | Подсветка вкладок при смене языка — фикс через _tab_init_names | ✅ |
| 4 | EN язык по умолчанию при запуске | ✅ |
| 5 | Автокалибровка точка A — возвращает REF_A (90,925) без поиска контура | ✅ |
| 6 | Переключатель "Oil check" в строке индикаторов масла | ✅ |

### Сайт (web/)
| # | Задача | Статус |
|---|--------|--------|
| 1 | LoginPage.jsx — полный i18n подключён | ✅ |
| 2 | debug-OCR убран из _read_oil_panel | ✅ |

---

## Решённые сложные проблемы (для памяти)

### WinError 1114 — torch DLL
PyTorch DLL не загружались в frozen EXE. Решение: preload последовательности DLL в начале main.py через `kernel32.LoadLibraryW` до любого `import torch`.

### Tab highlight при смене языка
`btns.pop(old_key)` ломал click-callback (lambda с оригинальным именем). Решение: хранить `_tab_init_names` при создании табвью, менять только `text` кнопок без изменения ключей словаря.

### IndentationError после комментирования
Комментирование `self._status()` оставило пустые `if/else` блоки. Решение: скрипт добавил `pass` во все пустые тела.

---

## Текущее состояние продукта

### ✅ Готово
- Бот: склепы, биржи, навигация, OCR масла
- Бот: i18n RU/EN полный, EN по умолчанию
- Бот: EXE сборка работает (dist/TotalHunter/TotalHunter.exe, ~950MB)
- Бот: YOLO модели зашифрованы (.pte)
- Бот: Oil check toggle, ресайзируемое окно, On Top справа
- Сайт: лендинг, dashboard, все страницы RU/EN
- Сервер: FastAPI, PostgreSQL, бэкапы

### ❌ Осталось до релиза
1. **Тест привязки устройства** — бот → 6-значный код → сайт → HWID (ручной тест)
2. **DownloadPage на сайте** — /download + кнопка скачать EXE
3. **Загрузить EXE** — GitHub Releases (dist/TotalHunter/ zip или installer)
4. **Free-Kassa ключи** — FK_MERCHANT_ID, FK_SECRET_WORD, FK_SECRET_WORD2 в systemd
5. **Тест оплаты** — end-to-end Free-Kassa
6. **Раскомментировать проверку кредитов** — toggle_bot строка `# if self.current_credits <= 0`
7. **PyArmor** — купить лицензию (~$49), обфусцировать код перед финальным релизом
8. **Auto-update** — updater.py + force_update флаг

---

## Задания на следующий раз

### 🔴 П1 — Ближайшее
1. **DownloadPage** — создать страницу /download на сайте с кнопкой скачать EXE
2. **GitHub Releases** — загрузить dist/TotalHunter/ как zip-архив
3. **Тест привязки** — проверить end-to-end: бот → код → сайт → email в боте

### 🔴 П2 — Монетизация
4. **Free-Kassa ключи** на сервере в systemd
5. **Тест оплаты** end-to-end
6. **Включить списание** — раскомментировать проверку кредитов в toggle_bot

### 🟡 П3 — Безопасность
7. **PyArmor лицензия** — купить и обфусцировать перед публичным релизом

---

## Технические данные

**Сборка EXE:**
```bash
cd C:/BattleBot
python model_crypto.py      # если модели изменились
python -m PyInstaller build.spec -y
# Результат: dist/TotalHunter/TotalHunter.exe
```

**Сервер:** GCP `34.68.86.57` | `/opt/totalhunter/server/`
**Деплой сайта:** git push origin main → авто
**Последний коммит:** `3b5e534` — EN default + robust tab highlight
