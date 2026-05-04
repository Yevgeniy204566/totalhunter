# Хангоф #34 — 2026-05-05
**Сессия:** Бот i18n + привязка устройств + сайт аудит

---

## Что сделано сегодня

### Бот (main.py + auth.py)
| # | Задача | Статус |
|---|--------|--------|
| 1 | Привязка устройства: `generate_link_code()` в auth.py | ✅ |
| 2 | GUI привязки в КАЛИБРОВКА: кнопка кода + таймер 10 мин + автообновление email | ✅ |
| 3 | LANGS расширен 60+ ключами (все вкладки, кнопки, слайдеры, сообщения) | ✅ |
| 4 | Все хардкоженные RU строки заменены на LANGS ссылки | ✅ |
| 5 | Все вкладки обёрнуты в CTkScrollableFrame — скролл при уменьшении окна | ✅ |
| 6 | Окно теперь ресайзируемое (minsize 400×560) | ✅ |

### Сайт (web/)
| # | Задача | Статус |
|---|--------|--------|
| 1 | Полный i18n аудит — все страницы dashboard RU/EN | ✅ |
| 2 | Balance: премиум glassmorphism дизайн (LITE/PRO/ULTRA) | ✅ |
| 3 | Layout: убран пустой sticky баннер | ✅ |
| 4 | Деплой автоматизирован через API (токен + alias) | ✅ |

---

## Архитектура привязки устройства

```
БОТ                          СЕРВЕР                    САЙТ
[Получить код] ──POST /web/link/generate──▶ создаёт LinkCode (6 цифр, 10 мин TTL)
               ◀─ {code: "123456"} ────────
[Показывает: 1 2 3 4 5 6]
[Таймер 10:00 ▼]

Пользователь вводит код на сайте /dashboard/devices
                                 POST /web/link/verify
                                 HWID привязывается к Google аккаунту
                                 bot_user сливается в web_user

[Каждые 15 сек: check_license()]
[Если email появился → "Аккаунт привязан: user@gmail.com"]
```

---

## Текущее состояние продукта

### ✅ Готово
- Бот: склепы, биржи, навигация, OCR масла
- Бот: i18n RU/EN полный, скроллируемые вкладки
- Бот: привязка к сайту через 6-значный код
- Сайт: лендинг, dashboard, рефералы, устройства, транзакции
- Сайт: i18n RU/EN полный
- Сервер: FastAPI, PostgreSQL, бэкапы каждые 6ч
- Безопасность: атомарные списания, anti-double-dipping

### ❌ Осталось до релиза
1. **Доделать i18n бота** — проверить LoginPage сайта (не переведена)
2. **EXE упаковка** — PyInstaller build.spec
3. **Страница скачивания** — кнопка Download на сайте
4. **Free-Kassa ключи** — FK_MERCHANT_ID, FK_SECRET_WORD, FK_SECRET_WORD2 в systemd
5. **Убрать debug-OCR** — _debug_ocr_approaches из _read_oil_panel (crypt_hunter.py)
6. **Auto-update** — updater.py + force_update флаг

---

## Задание на завтра (приоритет)

### 🔴 П1 — Перед упаковкой
1. **Проверить LoginPage сайта** — перевести на RU/EN если нужно
2. **Убрать debug-OCR** из crypt_hunter.py (временные тесты, нельзя в релиз)
3. **Протестировать** привязку устройства end-to-end (бот → код → сайт → привязка)

### 🔴 П2 — EXE упаковка
4. **PyInstaller** — build.spec с YOLO, targets/, assets/, profiles/
5. **Страница Download на сайте** — DownloadPage.jsx + роут /download
6. **Загрузить EXE** на CDN или GitHub Releases

### 🟡 П3 — Монетизация
7. **Free-Kassa ключи** на сервере (systemd service)
8. **Тест оплаты** end-to-end

---

## Технические данные

**Сервер:** GCP `34.68.86.57` | `/opt/totalhunter/server/`
**Vercel токен:** `vcp_2OacfkL9S4wbYB31ngyotlULFv7nedPLGMp6ICpIILlk13PbwP3NVtBj`
**Деплой:** git push origin main → хук → alias через API (Claude делает сам)
**Последний коммит:** `891026f` — i18n бота
