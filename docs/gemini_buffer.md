# Gemini Buffer — Хангоф #38 — 2026-05-07 вечер

---

## ✅ Что сделано сегодня

### 1. NOWPayments — работает полностью
- Платёж $10 прошёл → 5000 алмазов начислены мгновенно
- Подпись IPN: raw bytes HMAC-SHA512 (НЕ json.loads — нарушало порядок вложенного объекта `fee`)
- Единственный пакет: $10 / 5000 алмазов
- Free-Kassa удалена отовсюду: код, тексты, память, CLAUDE.md

### 2. Long-poll синхронизация баланса
- `server/vault.py`: GET /vault/sync/{hwid} держит соединение 50 сек
- `notify_balance_changed(hwid)` вызывается после payments webhook и earn reward
- Бот: бесконечный цикл в daemon-треде, обновляет баланс мгновенно
- Проверено: списали алмаз за поиск склепа → баланс в боте обновился сразу

### 3. Earn/Casino — страница бесплатных алмазов
- URL: `/dashboard/earn` (зелёная кнопка +5КР в хедере)
- Рандомная награда: 90%→5, 5%→10, 3%→20, 1%→30, 1%→50 (джекпот)
- Анимация: барабан крутит числа, останавливается на выигрыше с эффектами
- Лимит: 5 раз в день. Сервер: server/earn.py

### 4. Рекламные слоты Coinzilla
- AdSlot.jsx: компонент-заглушка (728×90, 300×250, 320×50)
- Desktop: leaderboard под хедером + sidebar >1280px
- Mobile: sticky 320×50 над нижней навигацией
- Лендинг: баннер между Stats и Features
- Верификационный мета-тег: `9c67590e6f729fcc1fd6186aa1b7aa01`
- Статус: ожидаем одобрение сайта + паспорта (1-3 дня)

### 5. Другое
- Версия в заголовке программы: `f"Total Hunter v{VERSION}"` — автоматически
- Колонка "Версия бота" в админке — бот отправляет версию при check_auth
- Кнопка перевода реф. алмазов в Referrals — зелёная, заметная
- Free-Kassa → NOWPayments везде в текстах сайта
- v1.1.0 код готов в репо, сборка EXE не сделана (TotalHunter.exe был открыт)

---

## 🔴 Задачи на завтра

1. **Coinzilla** — получить JS-коды зон → вставить в AdSlot.jsx
2. **Проверить рекламу** PC и мобиле
3. **Собрать v1.1.0 EXE** — закрыть программу → build_release.py → ZIP → gh release → API update
4. **Earn реальный плеер** — когда одобрят Bitmedia/Lootably → подключить iframe

---

## Шпаргалка команд

```bash
# Деплой сайта (ТОЛЬКО так — hook кешируется):
TOKEN="$(cat C:/BattleBot/.claude/settings.local.json | python -c "import sys,json; print(json.load(sys.stdin)['env']['VERCEL_TOKEN'])")"
TEAM="team_CkkRPXdwtRtsL9YCk8n4Fzla"
curl -s -X POST "https://api.vercel.com/v13/deployments?teamId=$TEAM&forceNew=1" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"totalhunter","project":"prj_mWtcb6hJCkl40YLWheeIlxD5NmXj","gitSource":{"type":"github","repoId":"1215361801","ref":"main"}}'
# Потом ждать READY и прикрепить домен

# Деплой GCP:
cd /opt/totalhunter/server && sudo git pull origin main && sudo systemctl restart totalhunter

# Сборка бота:
Set-Location C:\BattleBot; $env:PYTHONIOENCODING="utf-8"; python build_release.py
# Потом ZIP + gh release + API version/update
```
