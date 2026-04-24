# Gemini Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать `sync_to_gemini.py` — скрипт, который читает 4 локальных .md файла и полностью заменяет содержимое соответствующих Google Docs через Docs API.

**Architecture:** OAuth 2.0 (Desktop App) → Google Docs API v1. Для каждого файла: guard пустого файла → `documents().get()` → `batchUpdate(delete + insert)` → `sleep(1)`. Строго sequential.

**Tech Stack:** Python 3.13, `google-api-python-client`, `google-auth-oauthlib`, `pytest`, `unittest.mock`

---

## File Structure

| Файл | Действие | Назначение |
|---|---|---|
| `sync_to_gemini.py` | Создать | Главный скрипт: константы, функции, `__main__` |
| `test_sync_to_gemini.py` | Создать | Unit-тесты с мокнутым Google API |
| `credentials.json` | Скачать вручную | OAuth client (Desktop App) из GCP Console |
| `token.json` | Создаётся автоматически | OAuth токен после первого логина |

---

## Task 1: Установить зависимости и создать skeleton

**Files:**
- Create: `C:\BattleBot\sync_to_gemini.py`
- Create: `C:\BattleBot\test_sync_to_gemini.py`

- [ ] **Step 1: Установить зависимости**

```bash
pip install google-api-python-client google-auth-oauthlib
```

Ожидаем: установка без ошибок. Если уже установлены — `Requirement already satisfied`.

- [ ] **Step 2: Создать `sync_to_gemini.py` со скелетом**

```python
import os
import time

CREDS_PATH = r"C:\BattleBot\credentials.json"
TOKEN_PATH  = r"C:\BattleBot\token.json"
SCOPES      = ["https://www.googleapis.com/auth/documents"]

FILES = [
    (r"C:\BattleBot\ANTI-PATTERNS.md",
     "14JVf2k-hzw9Aci0Ju8yBPGFKoT8n3RuX9PSGp8j3qvE"),
    (r"C:\BattleBot\CLAUDE.md",
     "1CBEhm1g1pGLHNwhpkcRZtNA03kOZ9N-N00gsGlGuM3I"),
    (r"C:\Users\Admin\.claude\projects\C--BattleBot\memory\MEMORY.md",
     "18xMjHfyq754LuhrIf1zWgynm3SAFLWimA0cYiN37ZoA"),
    (r"C:\BattleBot\STATE.md",
     "10rqfqo2UCF25FZWRj9TCZOaIJCGuav6ZP_JyJUVEYdA"),
]


def read_local(path):
    raise NotImplementedError


def replace_doc(service, doc_id, content):
    raise NotImplementedError


def sync(service):
    raise NotImplementedError


def build_service():
    raise NotImplementedError


if __name__ == "__main__":
    print("=== Gemini Sync ===\n")
    svc = build_service()
    sync(svc)
```

- [ ] **Step 3: Создать `test_sync_to_gemini.py` скелет**

```python
import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from sync_to_gemini import read_local, replace_doc, sync
```

- [ ] **Step 4: Убедиться что импорт работает**

```bash
cd C:\BattleBot && python -c "from sync_to_gemini import read_local, replace_doc, sync; print('OK')"
```

Ожидаем: `OK`

- [ ] **Step 5: Commit**

```bash
git add sync_to_gemini.py test_sync_to_gemini.py
git commit -m "chore: skeleton for sync_to_gemini + test file"
```

---

## Task 2: TDD — `read_local()`

**Files:**
- Modify: `C:\BattleBot\test_sync_to_gemini.py`
- Modify: `C:\BattleBot\sync_to_gemini.py`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `test_sync_to_gemini.py`:

```python
class TestReadLocal(unittest.TestCase):

    def test_missing_file_returns_none(self):
        result = read_local(r"C:\nonexistent\totally_fake_file.md")
        self.assertIsNone(result)

    def test_empty_file_returns_none(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as f:
            path = f.name
        try:
            result = read_local(path)
            self.assertIsNone(result)
        finally:
            os.unlink(path)

    def test_valid_file_returns_content(self):
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".md", mode="w", encoding="utf-8"
        ) as f:
            f.write("# Hello\nworld")
            path = f.name
        try:
            result = read_local(path)
            self.assertEqual(result, "# Hello\nworld")
        finally:
            os.unlink(path)
```

- [ ] **Step 2: Запустить — убедиться что падают**

```bash
cd C:\BattleBot && python -m pytest test_sync_to_gemini.py::TestReadLocal -v
```

Ожидаем: 3 × FAILED (`NotImplementedError`)

- [ ] **Step 3: Реализовать `read_local()` в `sync_to_gemini.py`**

Заменить заглушку:

```python
def read_local(path):
    if not os.path.exists(path):
        return None
    if os.path.getsize(path) == 0:
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()
```

- [ ] **Step 4: Запустить — убедиться что проходят**

```bash
cd C:\BattleBot && python -m pytest test_sync_to_gemini.py::TestReadLocal -v
```

Ожидаем: 3 × PASSED

- [ ] **Step 5: Commit**

```bash
git add sync_to_gemini.py test_sync_to_gemini.py
git commit -m "feat: read_local() with empty/missing file guards"
```

---

## Task 3: TDD — `replace_doc()`

**Files:**
- Modify: `C:\BattleBot\test_sync_to_gemini.py`
- Modify: `C:\BattleBot\sync_to_gemini.py`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `test_sync_to_gemini.py`:

```python
class TestReplaceDoc(unittest.TestCase):

    def _make_service(self, end_index):
        service = MagicMock()
        service.documents.return_value.get.return_value.execute.return_value = {
            "body": {"content": [{"endIndex": end_index}]}
        }
        return service

    def test_normal_replace_sends_delete_then_insert(self):
        service = self._make_service(end_index=50)
        replace_doc(service, "doc123", "new content")

        call = service.documents.return_value.batchUpdate.call_args
        requests = call.kwargs["body"]["requests"]

        self.assertEqual(len(requests), 2)
        self.assertEqual(
            requests[0]["deleteContentRange"]["range"],
            {"startIndex": 1, "endIndex": 49},
        )
        self.assertEqual(
            requests[1]["insertText"],
            {"location": {"index": 1}, "text": "new content"},
        )

    def test_empty_doc_skips_delete(self):
        # endIndex=2 means only the trailing paragraph marker — nothing to delete
        service = self._make_service(end_index=2)
        replace_doc(service, "doc123", "content")

        call = service.documents.return_value.batchUpdate.call_args
        requests = call.kwargs["body"]["requests"]

        self.assertEqual(len(requests), 1)
        self.assertIn("insertText", requests[0])

    def test_calls_execute_on_batch_update(self):
        service = self._make_service(end_index=10)
        replace_doc(service, "doc123", "hello")
        service.documents.return_value.batchUpdate.return_value.execute.assert_called_once()
```

- [ ] **Step 2: Запустить — убедиться что падают**

```bash
cd C:\BattleBot && python -m pytest test_sync_to_gemini.py::TestReplaceDoc -v
```

Ожидаем: 3 × FAILED (`NotImplementedError`)

- [ ] **Step 3: Реализовать `replace_doc()` в `sync_to_gemini.py`**

Заменить заглушку:

```python
def replace_doc(service, doc_id, content):
    doc = service.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"]
    requests = []
    if end_index > 2:
        requests.append({
            "deleteContentRange": {
                "range": {"startIndex": 1, "endIndex": end_index - 1}
            }
        })
    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": content,
        }
    })
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()
```

- [ ] **Step 4: Запустить — убедиться что проходят**

```bash
cd C:\BattleBot && python -m pytest test_sync_to_gemini.py::TestReplaceDoc -v
```

Ожидаем: 3 × PASSED

- [ ] **Step 5: Commit**

```bash
git add sync_to_gemini.py test_sync_to_gemini.py
git commit -m "feat: replace_doc() — clear and insert via batchUpdate"
```

---

## Task 4: TDD — `sync()` orchestrator

**Files:**
- Modify: `C:\BattleBot\test_sync_to_gemini.py`
- Modify: `C:\BattleBot\sync_to_gemini.py`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `test_sync_to_gemini.py`:

```python
class TestSync(unittest.TestCase):

    def _tmp_file(self, tmpdir, name, content=""):
        path = os.path.join(tmpdir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    @patch("sync_to_gemini.time.sleep")
    @patch("sync_to_gemini.replace_doc")
    def test_skips_empty_file(self, mock_replace, mock_sleep):
        service = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            empty = self._tmp_file(tmp, "empty.md", "")
            with patch("sync_to_gemini.FILES", [(empty, "doc1")]):
                sync(service)
        mock_replace.assert_not_called()

    @patch("sync_to_gemini.time.sleep")
    @patch("sync_to_gemini.replace_doc")
    def test_skips_missing_file(self, mock_replace, mock_sleep):
        service = MagicMock()
        with patch("sync_to_gemini.FILES", [(r"C:\nonexistent\fake.md", "doc1")]):
            sync(service)
        mock_replace.assert_not_called()

    @patch("sync_to_gemini.time.sleep")
    @patch("sync_to_gemini.replace_doc")
    def test_continues_after_api_error(self, mock_replace, mock_sleep):
        mock_replace.side_effect = [Exception("API down"), None]
        service = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            f1 = self._tmp_file(tmp, "a.md", "content A")
            f2 = self._tmp_file(tmp, "b.md", "content B")
            with patch("sync_to_gemini.FILES", [(f1, "doc1"), (f2, "doc2")]):
                sync(service)
        self.assertEqual(mock_replace.call_count, 2)

    @patch("sync_to_gemini.time.sleep")
    @patch("sync_to_gemini.replace_doc")
    def test_sleeps_between_files(self, mock_replace, mock_sleep):
        service = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            f1 = self._tmp_file(tmp, "a.md", "A")
            f2 = self._tmp_file(tmp, "b.md", "B")
            with patch("sync_to_gemini.FILES", [(f1, "doc1"), (f2, "doc2")]):
                sync(service)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(1)
```

- [ ] **Step 2: Запустить — убедиться что падают**

```bash
cd C:\BattleBot && python -m pytest test_sync_to_gemini.py::TestSync -v
```

Ожидаем: 4 × FAILED (`NotImplementedError`)

- [ ] **Step 3: Реализовать `sync()` в `sync_to_gemini.py`**

Заменить заглушку:

```python
def sync(service):
    ok = 0
    for path, doc_id in FILES:
        name = os.path.basename(path)
        content = read_local(path)
        if content is None:
            print(f"  [SKIP] {name}")
            time.sleep(1)
            continue
        try:
            replace_doc(service, doc_id, content)
            print(f"  [OK]   {name}")
            ok += 1
        except Exception as e:
            print(f"  [ERR]  {name} → {e}")
        time.sleep(1)
    print(f"\n  Готово: {ok}/{len(FILES)}")
```

- [ ] **Step 4: Запустить — убедиться что проходят**

```bash
cd C:\BattleBot && python -m pytest test_sync_to_gemini.py::TestSync -v
```

Ожидаем: 4 × PASSED

- [ ] **Step 5: Запустить все тесты**

```bash
cd C:\BattleBot && python -m pytest test_sync_to_gemini.py -v
```

Ожидаем: 10 × PASSED, 0 failed

- [ ] **Step 6: Commit**

```bash
git add sync_to_gemini.py test_sync_to_gemini.py
git commit -m "feat: sync() orchestrator — sequential, guards, error-tolerant"
```

---

## Task 5: Добавить `build_service()` и настроить GCP

**Files:**
- Modify: `C:\BattleBot\sync_to_gemini.py`

`build_service()` — OAuth flow, не покрывается unit-тестами (требует реального Google аккаунта).

- [ ] **Step 1: Реализовать `build_service()` в `sync_to_gemini.py`**

Заменить заглушку:

```python
def build_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("docs", "v1", credentials=creds)
```

- [ ] **Step 2: Убедиться что все тесты ещё проходят**

```bash
cd C:\BattleBot && python -m pytest test_sync_to_gemini.py -v
```

Ожидаем: 10 × PASSED

- [ ] **Step 3: Настроить GCP (делает пользователь)**

1. Открыть https://console.cloud.google.com/
2. Создать проект (или выбрать существующий)
3. APIs & Services → Library → найти **Google Docs API** → **Enable**
4. APIs & Services → Credentials → **Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: любое (например `BattleBot Sync`)
   - → **Create**
5. Скачать JSON → переименовать в `credentials.json` → положить в `C:\BattleBot\`
6. APIs & Services → **OAuth consent screen** → Test users → добавить `ievgeniy2011@gmail.com`

- [ ] **Step 4: Commit**

```bash
git add sync_to_gemini.py
git commit -m "feat: build_service() — OAuth 2.0 Desktop flow"
```

---

## Task 6: Интеграционный тест (первый запуск)

- [ ] **Step 1: Убедиться что `credentials.json` на месте**

```bash
ls C:\BattleBot\credentials.json
```

Ожидаем: файл существует. Если нет — выполнить Task 5 Step 3.

- [ ] **Step 2: Запустить скрипт**

```bash
cd C:\BattleBot && python sync_to_gemini.py
```

При первом запуске откроется браузер → выбрать Google аккаунт → разрешить доступ → вернёшься в терминал.

Ожидаем:
```
=== Gemini Sync ===

  [OK]   ANTI-PATTERNS.md
  [OK]   CLAUDE.md
  [OK]   MEMORY.md
  [OK]   STATE.md

  Готово: 4/4
```

- [ ] **Step 3: Проверить в Gemini NotebookLM**

Открыть один из 4 Google Docs → убедиться что содержимое = текущий .md файл.

- [ ] **Step 4: Финальный commit**

```bash
git add token.json  # добавить в .gitignore если хочешь не хранить в репо
git commit -m "feat: sync_to_gemini.py complete — Gemini Sync workflow ready"
```

> **Важно:** `token.json` содержит OAuth токен — не публиковать в публичный репозиторий.
> Добавить в `.gitignore`: `token.json`

---

## Итог

После выполнения всех задач:
- `python sync_to_gemini.py` — одна команда после каждого Хангоф
- 4 Google Docs обновлены актуальными .md файлами
- Gemini NotebookLM видит свежий контекст проекта
