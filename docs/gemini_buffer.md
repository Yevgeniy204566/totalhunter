# Хангоф #50 — 2026-05-13 (MLM реферальное дерево)

## Что сделано

### MLM Реферальное дерево — ПОЛНОСТЬЮ ГОТОВО ✅

**Backend:**
- Новый endpoint `GET /web/referral/tree` в `server/web_routes.py`
- 3 async-запроса: L1 (invited_by_id == me), L2 (IN l1_ids), L3 (IN l2_ids)
- Pydantic схемы: `TreeNodeL3 → TreeNodeL2 → TreeNodeL1 → ReferralTreeResponse`
- Email masking: `email[:3] + "***"` (без домена — все на Gmail)
- Alembic миграция `h4i5j6k7l8m9` — индекс на `users.invited_by_id`
- ⚠️ down_revision = `14e8d8e2a95a` (не `g3h4i5j6k7l8`!) — на сервере есть лишние миграции
- 4 теста: empty, auth required, L1 structure, email masking

**Frontend:**
- Новая страница `/dashboard/tree` (`ReferralTreePage.jsx`) — полный экран без Layout
- Верхняя панель: `← Назад` + заголовок + счётчик L1/L2/L3
- `ZoomableCanvas` — drag мышью + колесо зума (20%–250%), кнопки +/−/⟳, счётчик %
- Org-chart: root → L1 → L2 → L3, CSS connector lines, `align-items: flex-start`
- Все уровни раскрываются (фикс: `onMouseDown={e => e.stopPropagation()}` на NodeCard)
- Мобилка: вертикальный аккордеон (≤640px)
- Первые 5 L1 + кнопка `+ ещё N` / `Свернуть`
- В ReferralsPage: убрана встроенная карточка, добавлен баннер-ссылка → `/dashboard/tree`

**Деплой:**
- GCP: `git pull` + `systemctl restart` + Alembic upgrade ✅
- Alembic на GCP: `DATABASE_URL=... /opt/totalhunter/venv/bin/alembic upgrade h4i5j6k7l8m9`
- venv путь: `/opt/totalhunter/venv/bin/alembic`
- VERCEL_TOKEN сохранён в `.env.local`

## Технические нюансы

### Alembic на GCP — важные команды
```bash
# Получить DATABASE_URL из запущенного сервиса
sudo strings /proc/$(systemctl show -p MainPID totalhunter | cut -d= -f2)/environ | grep DATABASE_URL
# Результат: postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter

# Запустить миграцию
DATABASE_URL=postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter \
  /opt/totalhunter/venv/bin/alembic upgrade <revision>

# Если "Multiple head revisions" — указывать конкретный revision ID, не "head"
```

### Серверные миграции которых нет в репо (нужно синхронизировать!)
На GCP есть эти файлы которых нет локально:
- `14e8d8e2a95a_final_merge_for_payments.py`
- `575bdc292d9e_merge_heads.py`
- `22864ea6408d_add_web_platform_tables.py`
→ Нужно скопировать их в `server/alembic/versions/` и запушить в репо

### ZoomableCanvas — баг с pointerEvents (решено)
- При mousedown на ZoomableCanvas → `dragging=true` → `pointerEvents: none` на inner div
- Клики по NodeCard не проходили (mouseup шёл на outer div, click не генерировался на кнопке)
- **Фикс:** `onMouseDown={e => e.stopPropagation()}` на NodeCard — drag не запускается при клике на карточку

## Статус задач на следующую сессию
1. Синхронизировать серверные миграции в репо (скопировать с GCP)
2. PopAds одобрение → AdSlot.jsx
3. Тест v1.2.2 у пользователей
4. Скачать в хедере EXE → ZIP
