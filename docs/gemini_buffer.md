# Gemini Buffer — Хангоф #35 — 2026-05-06

---

## Что сделано сегодня (05-06 мая)

### 1. Автообновление — исправлено и задеплоено
- **Баг 1:** `ZIP_NAME` не был определён → `NameError` при скачивании. Исправлено: `ZIP_NAME = "TotalHunter.zip"` в `updater.py`
- **Баг 2:** `CREATE_NO_WINDOW` — helper.bat убивался вместе с EXE. Исправлено: `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`
- **v1.0.7 → v1.0.8:** окно появляется, но падает (сломан updater v1.0.7). Пользователи v1.0.7 — скачать вручную с сайта. С v1.0.8 всё работает.

### 2. Мобильная Админка — переделана
- Убран hamburger/drawer
- Добавлена нижняя навигация (6 табов как на сайте)
- Игроки — компактные строки-плашки вместо больших карточек
- Задеплоено на GCP

### 3. v1.0.8 — собрана и опубликована
- 9 модулей Nuitka + PyInstaller
- GitHub Release: https://github.com/Yevgeniy204566/totalhunter/releases/tag/v1.0.8
- Сервер: `/version/latest` → `1.0.8`

### 4. Путь сервера зафиксирован
`/opt/totalhunter/server` (НЕ `/app`)
```bash
cd /opt/totalhunter/server && sudo git pull origin main && sudo systemctl restart totalhunter
```

---

## 🔴 Проблема — Ярлык на рабочем столе (на завтра)

**Симптом:** Размытая иконка ярлыка, переходит из версии в версию.

**Причина:** Windows кэширует иконки в `IconCache.db`. После xcopy нового EXE кеш не обновляется. Ярлык (.lnk) не пересоздаётся.

**Решение — добавить в update.bat:**
```batch
ie4uinit.exe -show
```
Эта утилита Windows сбрасывает кеш иконок без перезапуска explorer.exe.

Изменить нужно в `updater.py` → функция `download_and_install()` → в bat_path:
```python
f.write(f'xcopy /s /y /e "{extract_dir}\\*" "{exe_dir}\\"\n')
f.write('ie4uinit.exe -show\n')   # сбросить кеш иконок
f.write(f'start "" "{os.path.join(exe_dir, EXE_NAME)}"\n')
```

---

## План на завтра (2026-05-07)

### 1. Фикс ярлыка (иконка)
- Добавить `ie4uinit.exe -show` в update.bat
- Собрать v1.0.9
- Залить, опубликовать, проверить

### 2. Тест автообновления
- Скачать v1.0.8 с total-hunter.com
- Запустить → не должен предлагать обновление (версии совпадают)
- Поднять сервер на v1.0.9 → запустить v1.0.8 → проверить полный флоу обновления

### 3. Free-Kassa
- Зарегистрировать кабинет
- Прописать webhook: `https://api.total-hunter.com/payments/webhook`
- Получить FK_SECRET_WORD + FK_SECRET_WORD2 → добавить в GCP env

---

## Шпаргалка команд (для следующей сессии)

### Сборка и публикация новой версии:
```powershell
# version.py → VERSION = "1.0.X"
python build_release.py
cd dist\TotalHunter && Compress-Archive -Path * -DestinationPath ..\..\TotalHunter.zip -Force
& "C:\Program Files\GitHub CLI\gh.exe" release create v1.0.X "C:\BattleBot\TotalHunter.zip" --title "v1.0.X" --repo "Yevgeniy204566/totalhunter"
curl -X POST "https://api.total-hunter.com/admin/version/update?version=1.0.X" -H "Authorization: Bearer dev-admin-token"
```

### Деплой сервера:
```bash
cd /opt/totalhunter/server && sudo git pull origin main && sudo systemctl restart totalhunter
```

### Экстренный сброс версии:
```bash
curl -s -X POST "https://api.total-hunter.com/admin/version/update?version=1.0.8" -H "Authorization: Bearer dev-admin-token"
```

### Деплой сайта (3 шага — Клод делает сам):
```bash
git push origin main
curl -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
# + poll READY + alias total-hunter.com (см. CLAUDE.md раздел 6.5)
```
