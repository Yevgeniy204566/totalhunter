# ХАНГОФ #60 — Total Hunter
### Дата: 2026-05-20 | Большая сессия безопасности + аудиты + релизы

---

## ⚠️ КРИТИЧЕСКАЯ СИТУАЦИЯ (ЗАФИКСИРОВАТЬ)

### Бесконечная петля обновлений — ДЕНЬ СУРКА

**Статус сервера прямо сейчас:** /version/latest → 1.3.2 (ОТКАТИЛИ ВРУЧНУЮ)
**Код в репо:** version.py = 1.3.4
**Выпущены релизы:** v1.3.3 и v1.3.4 на GitHub (оба ПРОБЛЕМНЫЕ)

### Корень проблемы:
В updater.py (строка 70) был баг в xcopy команде:

**БЫЛО (сломано):**
```
xcopy /s /y /e "{extract_dir}\*" "{exe_dir}\"
```
ZIP структура: TotalHunter/TotalHunter.exe (папка внутри архива)
После extractall: extract_dir\TotalHunter\TotalHunter.exe
xcopy \* копировал папку TotalHunter\ ВНУТРЬ exe_dir → нестинг
Результат: exe_dir\TotalHunter\TotalHunter.exe (вложено!)
Старый exe оставался нетронутым → бот запускал старую версию → ПЕТЛЯ

**СТАЛО (исправлено в коде, v1.3.4):**
```
xcopy /s /y /e "{extract_dir}\TotalHunter\*" "{exe_dir}\"
```
Копирует СОДЕРЖИМОЕ папки TotalHunter\ → правильно заменяет файлы

### Почему фикс не помог:
Сломанный updater нельзя починить через само обновление.
Пользователь с v1.3.2 запускает update.bat со СТАРЫМ xcopy даже если
скачал v1.3.4. Физически невозможно.

### Текущий статус релизов:
- v1.3.2 — рабочий, но без всех исправлений безопасности
- v1.3.3 — сломан (updater с багом xcopy). НЕ ДЕЛАТЬ ПОСЛЕДНИМ.
- v1.3.4 — исправлен xcopy, но недостижим через автообновление

### Что нужно решить:
1. Понять как безопасно выкатить 1.3.4 не вызывая петли
2. Либо изменить механизм обновления (не xcopy, а PowerShell/python скрипт)
3. Либо убрать автообновление совсем и делать вручную

---

## ЧТО БЫЛО СДЕЛАНО ЗА СЕССИЮ (2026-05-19/20)

### Релизы
- v1.3.2 — README.txt, золотые ползунки, картинки кликабельны на сайте
- v1.3.3 — HTTPS, JWT raise, security фиксы (СЛОМАН updater)
- v1.3.4 — xcopy fix (НЕ АКТИВЕН — сервер на 1.3.2)

### Безопасность — сделано
- HTTP → HTTPS в auth.py, debug_reporter.py, roy/roy_client.py ✅
- ADMIN_TOKEN: raise ValueError при отсутствии ✅
- JWT_SECRET_KEY: raise ValueError при отсутствии ✅
- OWNER_EMAIL: убран из хардкода в env var (earn.py) ✅
- CORS: убран totalhunter.vercel.app ✅
- .gitignore: +credentials.json, service_account.json, .claude/, .tmp.driveupload/, *.log, *.bak ✅
- 302 .tmp.driveupload удалены из git ✅
- CLAUDE.md.bak удалён из git ✅
- web/.env.example: реальный IP заменён на домен ✅
- Все три ключа ротированы: ADMIN_TOKEN, NOWPAYMENTS_API_KEY, IPN_SECRET ✅
- JWT_SECRET_KEY добавлен на GCP в override.conf ✅
- OWNER_EMAIL добавлен на GCP в override.conf ✅
- beacon import: try-except в engine.py ✅
- combo toggle_combo_bot: hasattr guard ✅
- coord_manager.py: json.load в try-except (краш при битом профиле) ✅
- _emergency_stop: hasattr guard для combo ✅

### Код — сделано
- CombinerEngine import закомментирован в main.py ✅
- Дублированные импорты os/sys убраны в main.py ✅
- Main old Packmen.py — в репо, убрать позже

### GCP override.conf — текущее содержимое
```
[Service]
Environment="NOWPAYMENTS_API_KEY=XCBYC3W-2YXM19X-HMPNC1D-CG43J28"
Environment="NOWPAYMENTS_IPN_SECRET=qh32j9yylaWieAlRrbSnUDTqNIGYuldG"
Environment="ADMIN_TOKEN=0fb55141605437f975daa95a44b99fb7498faf0cee8ba0675999af6e21b8e5ab"
Environment="GOOGLE_CLIENT_SECRET=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"
[Service]
Environment="TELEGRAM_DEBUG_TOKEN=8872506039:AAEA8SCBFPVffh8FVLEYNfHuYHuo_Gn3Lr0"
Environment="TELEGRAM_DEBUG_CHAT_ID=578374730"
Environment="JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2"
Environment="OWNER_EMAIL=ievgeniy2011@gmail.com"
```

---

## ЧТО ОСТАЛОСЬ (следующая сессия)

### 🔴 ПЕРВОСТЕПЕННО — обновление без петли
Нужно придумать и утвердить стратегию выкатки v1.3.4.
Варианты:
A) Убрать автообновление совсем. Сделать кнопку "Проверить обновление" которая
   открывает браузер на странице скачивания. Просто. Надёжно.
B) Переписать update.bat на Python скрипт (нет зависимости от xcopy)
C) Оставить как есть, но написать в Discord инструкцию по ручной установке

### 🟡 ТЕХНИЧЕСКИЙ ДОЛГ
- server/payments.py: race condition в webhook (with_for_update())
- crypt_hunter.py: _detect_fail_streak без максимума → возможный бесконечный цикл
- engine.py + crypt_hunter.py: YOLO try-except при загрузке моделей
- updater.py: disk full не обрабатывается
- Main old Packmen.py: убрать из репо

---

## ТЕКУЩЕЕ СОСТОЯНИЕ ПРОДУКТА

| Что | Версия/Статус |
|---|---|
| Сервер /version/latest | 1.3.2 (откат) |
| Код в репо | 1.3.4 |
| GitHub Latest Release | v1.3.4 (НЕ активен на сервере) |
| Сайт total-hunter.com | ✅ последняя версия |
| GCP бэкенд | ✅ работает, все секреты обновлены |

**Следующий шаг: обсудить стратегию выкатки v1.3.4 без петли.**
