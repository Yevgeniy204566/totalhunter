# STATE.md — Бортжурнал Total Hunter

> Обновляется командой **«Хангоф»** перед `/compact` или `/clear`
> Последнее обновление: 2026-05-12 (Хангоф #47: v1.2.2 выпущен ✅ — 19 языков, PIL-флаги, OG-превью, лендинг)

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
| **Рекламные слоты** | web/AdSlot.jsx | 🟡 Заглушка (null). Ждём одобрения PopAds (до 3 дней). Coinzilla отказала — не крипто-проект. A-Ads — мин. вывод слишком высокий. | 2026-05-12 |
| **Версия в заголовке** | main.py | ✅ `f"Total Hunter v{VERSION}"` — автоматически обновляется | 2026-05-07 |
| **Версия в админке** | server/admin/index.html | ✅ Колонка "Версия бота" в таблице пользователей | 2026-05-07 |
| **Combo** | combiner.py | ⛔ ЗАМОРОЖЕН | 2026-05-02 |
| **Авто-калибровка** | auto_calibration.py | ✅ 2 этапа, 13 тестов | 2026-05-03 |
| **Движок бирж** | engine.py + navigator.py | ✅ 54 теста, smooth_alpha=0.70 | 2026-04-30 |
| **CryptHunter** | crypt_hunter.py | ✅ Anti-groundhog (_detect_fail_streak + _pre_skip). Конец списка — визуальный cv2.absdiff. Статусы конца/сброса. | 2026-05-12 |
| **Auto-update** | updater.py | ✅ v1.2.2 выпущен. ZIP (399MB) на GitHub | 2026-05-12 |
| **Динамическое окно** | main.py | ✅ SPI_GETWORKAREA при старте — высота под экран, прижато вправо. Работает на любом разрешении. | 2026-05-12 |
| **SEO** | web/ | ✅ useMeta hook (title+desc+OG per page), FAQ Schema JSON-LD (6 вопросов), sitemap обновлён | 2026-05-12 |
| **Статистика лендинга** | server/web_routes.py | ✅ Накопительная: base 300 бирж + 5000 склепов + реальные данные. Только растёт. | 2026-05-12 |
| **Installer** | installer.iss | ✅ v1.1.2: Win10+ gate, 64-bit check, авто-язык RU/EN | 2026-05-09 |
| **Silent Observer** | main.py + server/web_routes.py | ✅ crash reporter: crash_report.txt + POST /web/crash_report + вкладка Краши в админке | 2026-05-09 |
| **Snap-right fix** | main.py | ✅ SPI_GETWORKAREA при старте — высота под экран, прижато вправо сразу | 2026-05-12 |
| **Mobile OAuth** | web_routes.py + LoginPage.jsx | ✅ /auth/google/start + /callback, детект мобилки, JWT в URL | 2026-05-10 |
| **Guide — точность детекции** | guide_content.js/en.js + GuidePage.jsx | ✅ Биржи 80%, Склепы 30%, предупреждение про скорость нейросети | 2026-05-10 |
| **Скачать в хедере** | Layout.jsx | ✅ кнопка ↓ Скачать бота рядом с балансом, видна на всех страницах | 2026-05-10 |
| **Admin Panel** | server/admin/index.html | ✅ adjust_credits по user_id + вкладка Краши (crash reports) | 2026-05-09 |
| **Реф-безопасность** | server/web_routes.py | ✅ ref_bonus_claimed — бонус только при новом HWID | 2026-05-08 |
| **Лендинг** | web/LandingPage.jsx | ✅ 3D скриншоты, зелёная кнопка Setup.exe, robots.txt, sitemap | 2026-05-08 |
| **Guide Settings** | web/GuidePage.jsx + guide_content*.js | ✅ Раздел "Настройки бота": 16 слайдеров RU/EN с диапазонами | 2026-05-09 |
| **Безопасность** | server/main.py | ✅ atomic /use_credit, backup_db.sh | 2026-05-04 |

---

## Текущие ключи и токены (хранить только здесь)

### Admin API
- `ADMIN_SECRET_KEY` (в systemd сервиса): `zQ2z8D80xEnLTET0kQ0Bl85EYlTZBLIAtc37dZAmmK8`
- ⚠️ Нужно добавить `ADMIN_TOKEN=` в override.conf (сейчас работает дефолт `dev-admin-token` — небезопасно!)
- Команда обновления версии: `curl -X POST "https://api.total-hunter.com/admin/version/update?version=X.X.X" -H "Authorization: Bearer <ADMIN_TOKEN>"`

### NOWPayments
- API Key: `JKPMX8E-YS5MVV1-M0GTWDH-6WQ7SVP`
- IPN Secret: `iYOJZOwoI1a+M1gZ65bt0PAaul4GJvTd`
- Public Key: `8d82b5f6-61b6-48e5-9656-19ed7eb68c4b`
- IPN URL: `https://api.total-hunter.com/web/payment/webhook`

### Реклама
- **Coinzilla** — ОТКАЗ. Принимают только Web3/крипто-проекты.
- **A-Ads** — ОТКАЗ. Мин. вывод 0.002 BTC (~$160) через Lightning — слишком высокий.
- **PopAds** — 🟡 На модерации (до 3 дней). Мин. вывод $5 USDT TRC20. Формат: Pop-under.
- **Лучшие альтернативы:** BitMedia ($20 BTC/USDT, баннеры), BidVertiser ($10 BTC)

### Vercel
- Token: см. `.claude/settings.local.json` (не в репо)
- Team: `team_CkkRPXdwtRtsL9YCk8n4Fzla`
- Project: `prj_mWtcb6hJCkl40YLWheeIlxD5NmXj`
- GitHub repoId: `1215361801`

---

## 🔧 GCP — важные факты
- VM: `total-hunter-backend`, zone=`us-central1-f`, project=`digital-arcade-274010` (Debian 12)
- SSH: через Cloud Shell → `gcloud compute ssh total-hunter-backend --zone=us-central1-f`
- FK_* переменные (Free-Kassa) удалены из `/etc/systemd/system/totalhunter.service` 2026-05-09
- Все env vars в порядке: GOOGLE_CLIENT_ID ✅, JWT_SECRET_KEY ✅, NOWPAYMENTS ✅

## 🔍 Конкурент-разведка mercexchangefinder.com
- Crowd-sourced модель: клиенты сканируют → отправляют на сервер → WS дашборд
- API: `coords: null` в публичном ответе — координаты только за кредиты
- Их слабость: нет автонавигации, координаты платные, данные устаревают быстро
- Строить свой пул смысла нет — биржи живут 2-5 мин, не накопишь

## 🔴 Задачи на завтра

1. **PopAds** — как придёт одобрение: вставить код в AdSlot.jsx
2. **Тест v1.2.1 у пользователей** — проверить anti-groundhog и конец списка
3. **GCP deploy** — `cd /opt/totalhunter/server && sudo git pull origin main && sudo systemctl restart totalhunter` (stats base 300/5000)

---

## Архитектура платежей и синхронизации (нерушимо)

- **NOWPayments IPN**: raw bytes HMAC-SHA512 (НЕ json.loads/dumps)
- **Long-poll**: `/vault/sync/{hwid}` + `notify_balance_changed(hwid)` после commit
- **Earn endpoint**: `/web/earn/reward` + `/web/earn/status`, лимит 5/день
- **SQLAlchemy**: flush() + один commit() — никогда два db.begin()
