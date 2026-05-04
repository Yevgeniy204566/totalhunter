# Отчёт сессии 2026-05-04
**Статус:** Всё задеплоено и работает ✅

---

## Что сделано за сессию

### 🤖 Бот (crypt_hunter.py + main.py)
| # | Изменение | Статус |
|---|-----------|--------|
| 1 | Скролл меню склепов: 3 атомарных вызова `pyautogui.scroll(-3)` × 3 | ✅ |
| 2 | OCR масла: индексы epic/rare исправлены (epic=idx2, rare=idx1) | ✅ |
| 3 | OCR масла: unsharp mask + INTER_LANCZOS4, регион +10px влево | ✅ |
| 4 | GUI масла: блок перенесён НАД кнопку Старт, центрирован | ✅ |
| 5 | GUI масла: 🟢 Обычное / 🔵 Редкое / 🟣 Эпическое — правильные цвета | ✅ |
| 6 | Ползунок "Скорость скроллинга" → "Частота YOLO-детекции" | ✅ |
| 7 | Debug OCR тесты добавлены в `_debug_ocr_approaches` | ✅ |

### 🖥 Сервер (server/)
| # | Изменение | Статус |
|---|-----------|--------|
| 1 | `/use_credit`: атомарный `UPDATE...RETURNING` — race condition закрыт | ✅ |
| 2 | `/check_auth`: возвращает L1/L2/L3 рефералов + `is_referred` | ✅ |
| 3 | `web_routes.py`: `invited_by_id` переносится при merge бот→веб | ✅ |
| 4 | `web_routes.py`: `skip_ref_welcome` — защита от двойного бонуса | ✅ |
| 5 | `schemas.py`: `referrals` + `is_referred` в `CheckAuthResponse` | ✅ |
| 6 | Задеплоено на GCP `/opt/totalhunter/server/` | ✅ |

### 💰 Рефералка (auth.py + main.py)
| # | Изменение | Статус |
|---|-----------|--------|
| 1 | `transfer_referral_balance()` в auth.py | ✅ |
| 2 | Вкладка Рефералы: ссылка `total-hunter.com/ref/{код}` — главный элемент | ✅ |
| 3 | Кнопка "Перевести" через threading (не браузер) | ✅ |
| 4 | Сетка L1 / L2 / L3 в GUI | ✅ |
| 5 | Баг `my_ref_id` → `ref_id` исправлен | ✅ |

### 🔒 Безопасность
| # | Изменение | Статус |
|---|-----------|--------|
| 1 | `scripts/backup_db.sh`: pg_dump каждые 6ч + GCS upload | ✅ |
| 2 | `scripts/restore_db.sh`: безопасное восстановление с systemctl stop | ✅ |
| 3 | Cron активирован на сервере (0 */6 * * *) | ✅ |
| 4 | Бэкап протестирован: файл 3.4K — данные читаются | ✅ |

### 🌐 Сайт (web/)
| # | Изменение | Статус |
|---|-----------|--------|
| 1 | LandingPage: логотип увеличен (720→920px) | ✅ |
| 2 | LandingPage: картинки бирж/склепов — `contain` вместо `cover`, высота 280px | ✅ |
| 3 | BalancePage: полный перевод на английский | ✅ |
| 4 | BalancePage: белый цвет цифр → цвет пакета (премиум) | ✅ |
| 5 | BalancePage: метки пакетов на EN (Starter/Hunter's Choice/Max Value) | ✅ |
| 6 | Layout: убран пустой sticky баннер "AD" | ✅ |
| 7 | Vercel: билд успешен (`2e1dc5b`, 367ms) | ✅ |

---

## Архитектура рекламы (план)

**Где размещать (максимум 3 блока на весь сайт):**
- Низ лендинга — 1 блок
- GuidePage — 2 блока
- Balance/Dashboard — **0** (убьёт конверсию)

**Сеть:** Coinzilla (гейминг/крипто)
**Защита от AdBlock:** Nginx proxy → свой домен

---

## Что осталось (приоритет)

### 🔴 КРИТИЧНО
1. **Free-Kassa ключи** — вставить FK_MERCHANT_ID, FK_SECRET_WORD, FK_SECRET_WORD2 в `/etc/systemd/system/totalhunter.service`
2. **Убрать debug-OCR** из `_read_oil_panel` в `crypt_hunter.py` (временные тесты)

### 🟡 ПЕРЕД EXE
3. Auto-update клиент (`updater.py`)
4. EXP-флаги — убрать `_EXP_DIALOG_GATE`
5. YOLO model protection (AES-256)

### 🟢 ПОСЛЕ EXE
6. EXE packaging (PyInstaller)
7. Coinzilla регистрация + embed-код
8. Google Search Console

---

## Технические данные

**Сервер:** GCP `34.68.86.57` | user: `ievgeniy2011` | backend: `/opt/totalhunter/server/`
**DB:** `postgresql://hunter:***@localhost:5432/totalhunter`
**Бэкапы:** `~/backups/` | лог: `~/backups/backup.log`
**Deploy:** `git push origin main` → Vercel auto-build
**Deploy hook:** `POST https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw`
**Последний коммит:** `2e1dc5b` — fix Layout sticky ad bar
