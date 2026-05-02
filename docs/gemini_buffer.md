# Хангоф #29 — SaaS запущен на total-hunter.com
**Дата:** 2026-05-02

---

## ✅ Что сделано в этой сессии

| Задача | Статус |
|---|---|
| Домен total-hunter.com (Cloudflare, SSL) | ✅ |
| Nginx + SSL на GCP → api.total-hunter.com | ✅ |
| Vercel привязан к домену, auto-deploy из ветки main | ✅ |
| CORS обновлён — добавлен total-hunter.com | ✅ |
| Биржа: списание включено (spend_credit("exchange")) | ✅ |
| Стоимость биржи: 5 → 10 алмазов (сервер + гайд) | ✅ |
| COOP заголовок (vercel.json) — OAuth работает | ✅ |
| Лендинг: картинки exchange.png + crypt.png в фичах | ✅ |
| Лендинг: большой лого со свечением (160px, glow) | ✅ |
| Лендинг: кнопка RU/EN переключает язык | ✅ |
| Дашборд: переводы RU/EN через useLang() | ✅ |
| GuidePage: 10 алмазов за биржу, lang подключён | ✅ |
| Текст лендинга отредактирован пользователем | ✅ |
| Git branch переименован master → main | ✅ |
| Все файлы (картинки, переводы, lang.js) добавлены в git | ✅ |

---

## 🔴 Чеклист запуска — что осталось

### Высокий приоритет
| # | Задача |
|---|---|
| 1 | **SEO** — meta title/description/og-tags для total-hunter.com |
| 2 | **EXE упаковка** — PyInstaller .spec файл, сборка дистрибутива |
| 3 | **Защита YOLO моделей** — шифрование crypts.pt → crypts.pt.enc |
| 4 | **Автообновление** — check version при старте, открывать браузер |
| 5 | **Coinzilla** — вставить код рекламы в Layout.jsx (место готово) |

### Средний приоритет
| # | Задача |
|---|---|
| 6 | **Автокалибровка REF_A/REF_B** — OpenCV matchTemplate для джойстика и серебра |
| 7 | **Free-Kassa webhook** — прописать URL в кабинете FK |
| 8 | **GuidePage i18n** — полный перевод (файлы guide_content.js/en.js готовы, нужно подключить все секции) |
| 9 | **Иллюстрации в гайде** — вставить calib_point_a.png, calib_point_b.png |

---

## Инфраструктура (финальный статус)

```
total-hunter.com          → Vercel (React SPA)
api.total-hunter.com      → GCP 34.68.86.57 (Nginx → uvicorn :8000)
34.68.86.57/admin         → Admin Panel
PostgreSQL                → на GCP, systemd сервис "totalhunter"
GitHub: Yevgeniy204566/totalhunter, branch: main
```

## Критические правила git (выучить наизусть)

```bash
# Редактируешь файл в VS Code → сохранил → потом:
git add web/src/constants.js       # или нужный файл
git commit -m "что изменил"
git push origin main
# Только тогда Vercel задеплоит!
```

## SEO — что нужно сделать

Добавить в `web/index.html`:
```html
<title>Total Hunter — автоматический поиск бирж и склепов в Total Battle</title>
<meta name="description" content="Бот для Total Battle: автоматический поиск бирж наёмников и сбор склепов. 100 алмазов бесплатно при регистрации.">
<meta property="og:title" content="Total Hunter">
<meta property="og:description" content="Автоматизация для Total Battle">
<meta property="og:image" content="https://total-hunter.com/img/logo.png">
<meta property="og:url" content="https://total-hunter.com">
<meta name="robots" content="index, follow">
```

И подключить Google Search Console для индексации.
