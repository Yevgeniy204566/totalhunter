# Gemini Buffer — 2026-05-05 15:30

---

## Процесс автообновления Total Hunter Bot

### Как работает система

Автообновление работает ТОЛЬКО в собранном EXE (не в Python-скрипте).

**Компоненты:**
- `updater.py` — логика проверки версии
- `version.py` — текущая версия (`VERSION = "1.0.7"`)
- `/version/latest` на сервере — эндпоинт с актуальной версией
- Admin Panel → Dashboard → "Версия бота" — интерфейс публикации

---

### Шаги для выпуска новой версии (напр. v1.0.8)

**1. Обновить version.py**
```python
VERSION = "1.0.8"
```

**2. Собрать EXE через build.spec**
```
pyinstaller build.spec --noconfirm
```
→ результат: `dist/TotalHunter.exe`

**3. Запаковать в ZIP**
```
cd dist && zip TotalHunter.zip TotalHunter.exe
```

**4. Загрузить на GitHub Releases**
- Создать Release с тегом `v1.0.8`
- Приложить `TotalHunter.zip`
- URL будет: `https://github.com/Yevgeniy204566/totalhunter/releases/download/v1.0.8/TotalHunter.zip`

**5. Опубликовать версию через Admin Panel**
- Зайти на `https://admin.total-hunter.com`
- Dashboard → блок "Версия бота"
- Ввести `1.0.8` в поле
- Нажать "Опубликовать"
- Проверить: поле "Текущая в БД" должно показать `1.0.8`

**ИЛИ через curl:**
```bash
curl -X POST "https://api.total-hunter.com/admin/version/update?version=1.0.8" \
  -H "Authorization: Bearer dev-admin-token"
```

**6. Проверить эндпоинт**
```bash
curl https://api.total-hunter.com/version/latest
# {"version":"1.0.8","download_url":"https://github.com/.../v1.0.8/TotalHunter.zip"}
```

---

### Как обновляется пользователь

1. Пользователь запускает старый EXE (например v1.0.6)
2. При запуске `updater.py` вызывает `check_for_updates("1.0.6")`
3. Если сервер вернул версию > текущей — показывается диалог
4. Пользователь нажимает "Обновить"
5. Скачивается ZIP с GitHub
6. Файл распаковывается рядом со старым EXE
7. Запускается новый EXE, старый завершается

**ВАЖНО:** Автообновление работает только с v1.0.6+  
Версии 1.0.3–1.0.5 использовали старый GitHub API (возвращал 404 для приватных репо) — обновление не работало. Пользователи с этими версиями должны скачать вручную.

---

### Известные проблемы / история

- **v1.0.7**: Поле "версия в БД" случайно было заполнено текстом "Обновить " (кнопка) → исправлено через curl POST на /admin/version/update?version=1.0.7
- **v1.0.3–1.0.5**: GitHub API для приватных репо возвращает 404 → переехали на собственный сервер

---

## Мобильная Админка — что сделано 2026-05-05

**Изменения в `server/admin/index.html`:**

1. **Убрал hamburger/drawer** — был неудобен на телефоне
2. **Добавил нижнюю навигацию** (как на сайте) — 6 табов: Dashboard, Игроки, Broadcast, Feedback, TOP, Логи
3. **Список игроков** — теперь компактные строки-плашки вместо больших карточек:
   - `[dot] Имя / email ... [кредиты ◆] [+] [ban] [del]`
   - Кнопка `+` вызывает `prompt()` для ввода суммы — без inline input
4. **Toast** поднят выше bottom nav (не перекрывается)
5. **Мобильный header** показывает название текущей страницы + кнопку refresh

**Нужно задеплоить на GCP:**
```bash
git add server/admin/index.html
git commit -m "feat(admin): mobile bottom nav + compact user rows"
git push origin main
# затем SSH → cd /app && git pull
```

---
