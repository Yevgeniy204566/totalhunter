# STATE.md — Бортжурнал Total Hunter

> Обновляется командой **«Хангоф»** перед `/compact` или `/clear`
> Последнее обновление: 2026-05-08 (Хангоф #39: v1.1.0 Setup.exe ✅, Inno Setup installer ✅, реф-защита HWID ✅, лендинг 3D+SEO ✅)

**Frontend URL:** https://total-hunter.com (Vercel + Cloudflare)
**Backend URL:** https://api.total-hunter.com → GCP 34.68.86.57:8000 (Nginx + SSL)

**Frontend Deploy:** forceNew API (НЕ hook — кешируется!) + alias
- Token: в `.claude/settings.local.json` → env.VERCEL_TOKEN (не в репо!)
- команда: `POST /v13/deployments?forceNew=1` с gitSource repoId=1215361801

---

## Статус модулей

| Модуль | Файл | Статус | Дата |
|---|---|---|---|
| **Платежи** | server/payments.py | ✅ NOWPayments (крипто). IPN raw bytes HMAC-SHA512. Работает. | 2026-05-07 |
| **Long-poll синхронизация** | server/vault.py | ✅ GET /vault/sync/{hwid} — мгновенный обмен баланса бот↔сайт | 2026-05-07 |
| **Earn/Casino** | server/earn.py + web/EarnPage.jsx | ✅ Зелёная кнопка +5КР → рандомная награда 5/10/20/30/50 алмазов | 2026-05-07 |
| **Рекламные слоты** | web/AdSlot.jsx | 🟡 Заглушки стоят. Ждём одобрения Coinzilla (1-3 дня) | 2026-05-07 |
| **Версия в заголовке** | main.py | ✅ `f"Total Hunter v{VERSION}"` — автоматически обновляется | 2026-05-07 |
| **Версия в админке** | server/admin/index.html | ✅ Колонка "Версия бота" в таблице пользователей | 2026-05-07 |
| **Combo** | combiner.py | ⛔ ЗАМОРОЖЕН | 2026-05-02 |
| **Авто-калибровка** | auto_calibration.py | ✅ 2 этапа, 13 тестов | 2026-05-03 |
| **Движок бирж** | engine.py + navigator.py | ✅ 54 теста, smooth_alpha=0.70 | 2026-04-30 |
| **CryptHunter** | crypt_hunter.py | ✅ слепой T_max/2^N без OCR | 2026-05-04 |
| **Auto-update** | updater.py | ✅ v1.1.0 собран и выпущен. Setup.exe + ZIP на GitHub | 2026-05-08 |
| **Installer** | installer.iss | ✅ Inno Setup, VC++ Runtime bundled, Windows 10/11 x64 | 2026-05-08 |
| **Admin Panel** | server/admin/index.html | ✅ adjust_credits по user_id (веб-пользователи без HWID) | 2026-05-08 |
| **Реф-безопасность** | server/web_routes.py | ✅ ref_bonus_claimed — бонус только при новом HWID | 2026-05-08 |
| **Лендинг** | web/LandingPage.jsx | ✅ 3D скриншоты, зелёная кнопка Setup.exe, robots.txt, sitemap | 2026-05-08 |
| **Безопасность** | server/main.py | ✅ atomic /use_credit, backup_db.sh | 2026-05-04 |

---

## Текущие ключи и токены (хранить только здесь)

### NOWPayments
- API Key: `JKPMX8E-YS5MVV1-M0GTWDH-6WQ7SVP`
- IPN Secret: `iYOJZOwoI1a+M1gZ65bt0PAaul4GJvTd`
- Public Key: `8d82b5f6-61b6-48e5-9656-19ed7eb68c4b`
- IPN URL: `https://api.total-hunter.com/web/payment/webhook`

### Coinzilla
- Verification meta: `9c67590e6f729fcc1fd6186aa1b7aa01`
- Статус: ожидание проверки сайта + паспорта (1-3 дня)

### Vercel
- Token: см. `.claude/settings.local.json` (не в репо)
- Team: `team_CkkRPXdwtRtsL9YCk8n4Fzla`
- Project: `prj_mWtcb6hJCkl40YLWheeIlxD5NmXj`
- GitHub repoId: `1215361801`

---

## 🔴 Задачи на завтра

1. **Coinzilla** — как придёт одобрение: получить JS-коды зон, вставить в AdSlot.jsx (728×90 и 300×250)
2. **Проверить рекламные слоты** на мобиле и ПК — убедиться что не перекрывают контент
3. **Собрать v1.1.0** — закрыть TotalHunter.exe, запустить build_release.py, сделать релиз
4. **Earn/реклама** — когда Bitmedia/Lootably одобрят, подключить реальный плеер вместо 5-секундной паузы

---

## Архитектура платежей и синхронизации (нерушимо)

- **NOWPayments IPN**: raw bytes HMAC-SHA512 (НЕ json.loads/dumps)
- **Long-poll**: `/vault/sync/{hwid}` + `notify_balance_changed(hwid)` после commit
- **Earn endpoint**: `/web/earn/reward` + `/web/earn/status`, лимит 5/день
- **SQLAlchemy**: flush() + один commit() — никогда два db.begin()
