# Design: sync_to_gemini.py

**Date:** 2026-04-24  
**Goal:** Синхронизировать 4 локальных .md файла проекта в Google Docs, чтобы Gemini NotebookLM видел актуальный контекст после каждого Хангоф.

---

## Контекст

Gemini NotebookLM читает только Google Docs. Контекст проекта хранится в 4 .md файлах:
- `C:\BattleBot\ANTI-PATTERNS.md`
- `C:\BattleBot\CLAUDE.md`
- `C:\BattleBot\STATE.md`
- `C:\Users\Admin\.claude\projects\C--BattleBot\memory\MEMORY.md`

Пользователь создал 4 пустых Google Docs в папке `Gemini_Sync` на Google Drive.  
Скрипт обновляет их содержимое через Google Docs API.

---

## Архитектура

```
sync_to_gemini.py
credentials.json    ← OAuth client (Desktop App), скачать из GCP Console
token.json          ← создаётся автоматически при первом запуске
```

**Зависимости:**
```
google-api-python-client
google-auth-oauthlib
```

---

## Google Doc IDs (захардкожены в скрипте)

| Файл | Google Doc ID |
|---|---|
| ANTI-PATTERNS.md | `14JVf2k-hzw9Aci0Ju8yBPGFKoT8n3RuX9PSGp8j3qvE` |
| CLAUDE.md | `1CBEhm1g1pGLHNwhpkcRZtNA03kOZ9N-N00gsGlGuM3I` |
| MEMORY.md | `18xMjHfyq754LuhrIf1zWgynm3SAFLWimA0cYiN37ZoA` |
| STATE.md | `10rqfqo2UCF25FZWRj9TCZOaIJCGuav6ZP_JyJUVEYdA` |

---

## Алгоритм

```
для каждого файла (строго последовательно):
  1. Проверить os.path.getsize(src) == 0 → [SKIP], не трогать Google Doc
  2. Прочитать .md как plain text (UTF-8)
  3. documents().get(docId) → получить endIndex
  4. batchUpdate():
     a. deleteContentRange [1, endIndex-1]  (только если endIndex > 2)
     b. insertText index=1, text=content
  5. Вывести [OK] или [ERR]
  6. time.sleep(1)  ← пауза между файлами
итог: "Готово: N/4"
```

---

## Защиты

| Ситуация | Поведение |
|---|---|
| Локальный .md пустой (0 байт) | `[SKIP]` — Google Doc не трогается |
| Локальный .md не найден | `[SKIP]` — Google Doc не трогается |
| API error | `[ERR] filename → exception text`, продолжаем следующий |
| endIndex <= 2 (Doc уже пустой) | Пропускаем deleteContentRange, только insertText |

---

## Настройка (один раз)

1. [Google Cloud Console](https://console.cloud.google.com/) → создать проект
2. APIs & Services → Enable APIs → **Google Docs API** → Enable
3. APIs & Services → Credentials → Create Credentials → **OAuth client ID**
   - Application type: **Desktop app**
   - Скачать JSON → сохранить как `C:\BattleBot\credentials.json`
4. OAuth consent screen → добавить свой email в Test users
5. Установить зависимости:
   ```
   pip install google-api-python-client google-auth-oauthlib
   ```
6. Первый запуск: `python sync_to_gemini.py`
   - Откроется браузер → войти в Google → разрешить доступ
   - `token.json` сохранится автоматически

---

## Запуск

```bash
python sync_to_gemini.py
```

Запускать после каждого **Хангоф** (обновления STATE.md / ANTI-PATTERNS.md).

---

## Что НЕ делаем

- Не используем MCP `create_file` — он не умеет обновлять существующие Google Docs
- Не параллельные вызовы — строго sequential (прошлый опыт: 30к токенов впустую)
- Не выносим Doc IDs в отдельный config.json — избыточная абстракция для 4 статичных ID
- Не форматируем Markdown → Google Docs headings — plain text достаточен для Gemini
