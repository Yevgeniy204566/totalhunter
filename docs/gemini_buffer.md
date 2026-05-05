# Хангоф #35 — 2026-05-05
**Сессия:** GUI полный i18n + UX улучшения бота

---

## Что сделано сегодня

### Бот (main.py + crypt_hunter.py)
| # | Задача | Статус |
|---|--------|--------|
| 1 | Полный i18n GUI — 75+ ключей, все вкладки, кнопки, слайдеры, единицы | ✅ |
| 2 | Паттерн `self._i18n_labels` — один цикл обновляет все статичные лейблы | ✅ |
| 3 | Фикс переключения вкладок RU↔EN — `btns.pop(old)` обновляет ключ словаря | ✅ |
| 4 | Переключатель «Проверка масла / Oil check» в строке с индикаторами масла | ✅ |
| 5 | Убран `_debug_ocr_approaches` из crypt_hunter.py | ✅ |
| 6 | Окно ресайзируемое по вертикали (minsize 460×400), внешний CTkScrollableFrame | ✅ |
| 7 | On Top: правый край, высота рабочей области (SPI_GETWORKAREA - 35px) | ✅ |
| 8 | Сетка склепов: COLS=6, иконки 40px, scroll_frame 195px со своим скроллбаром | ✅ |

### Сайт (web/)
| # | Задача | Статус |
|---|--------|--------|
| 1 | LoginPage.jsx — подключён useLang + DASHBOARD, был 100% хардкод RU | ✅ |
| 2 | googleError ключ добавлен в оба dashboard_content файла | ✅ |

---

## Текущее состояние продукта

### ✅ Готово
- Бот: склепы, биржи, навигация, OCR масла
- Бот: i18n RU/EN полный (все элементы GUI)
- Бот: переключатель проверки масла
- Бот: ресайзируемое окно, On Top справа на всю рабочую высоту
- Бот: привязка к сайту через 6-значный код
- Сайт: лендинг, dashboard, рефералы, устройства, транзакции
- Сайт: i18n RU/EN полный включая LoginPage
- Сервер: FastAPI, PostgreSQL, бэкапы каждые 6ч

### ❌ Осталось до релиза
1. **EXE упаковка** — PyInstaller build.spec (YOLO, targets/, assets/, profiles/)
2. **Страница скачивания** — DownloadPage.jsx + роут /download
3. **Загрузить EXE** — GitHub Releases или CDN
4. **Free-Kassa ключи** — FK_MERCHANT_ID, FK_SECRET_WORD, FK_SECRET_WORD2 в systemd
5. **Тест оплаты** — end-to-end
6. **Тест привязки устройства** — бот → код → сайт → HWID (ручной)

---

## Следующий приоритет

### 🔴 П2 — EXE упаковка
1. **PyInstaller build.spec** — включить YOLO ultralytics, targets/*.pt, assets/, profiles/
2. **DownloadPage.jsx** на сайте — роут /download, кнопка скачать EXE
3. **Загрузить EXE** на GitHub Releases

### 🟡 П3 — Монетизация
4. **Free-Kassa ключи** на сервере
5. **Тест оплаты** end-to-end

---

## Технические данные

**Сервер:** GCP `34.68.86.57` | `/opt/totalhunter/server/`
**Деплой сайта:** git push origin main → авто
**Последний коммит:** `f8a4779` — bottom gap -35px
