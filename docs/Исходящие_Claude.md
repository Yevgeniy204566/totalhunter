# Исходящие → Gemini / для пользователя

## [BATTLEBOT] Диагностика зависания CryptHunter — root cause найден, фикс отложен (2026-09-09, время 19:15)

Живой инцидент: бот (v1.9.2) завис на охоте за склепами через ~23 мин, игра из-за 5-мин бездействия
показала свою рекламную заставку. Полная диагностика через серверные логи GCP + локальный
`crypt_*.log` бота (найден в `Downloads\TotalHunter\_internal\logs\` — реальный установленный бот
живёт не в `C:\BattleBot`).

**Root cause:** `_scroll_and_find()` в `crypt_hunter.py` — цикл поиска склепа в меню без верхнего
предела попыток (параметр `max_scrolls` в сигнатуре есть, но не передаётся при единственном
вызове → мёртв) + почти весь построчный лог внутри цикла закомментирован → зависание неотличимо
от краша, ни следа в логах. Сопутствующая находка: `_send_captain()` всегда возвращает `True`,
не проверяя хватило ли масла — при нехватке масла бот честно "ждёт" полный слепой таймер и
списывает кредит за не полученный склеп (подтверждено намеренным тестом владельца). Опровергнута
гипотеза владельца про существующий автостоп «не нашёл N раз — выключился» — такого кода нет,
`_emergency_stop()` мёртв. OCR в файле есть, но не подключён — подтверждено: сознательное решение
владельца (был отключён раньше из-за ложных срабатываний), не забытая недоделка.

**Статус:** фикс НЕ применялся — новая механика/архитектурное решение, владелец решил понаблюдать
за живым поведением перед тем как согласовывать конкретный фикс. Полная запись → `ANTI-PATTERNS.md`
(секция "БЕСКОНЕЧНЫЙ ЦИКЛ БЕЗ ЛОГА И БЕЗ ЛИМИТА ПОПЫТОК") и `STATE.md` (сессия #138).

---

## [ИНФРА] Переустановка Windows — списки + инструкция восстановления (2026-08-04)

Контекст: у пользователя 3 раза за день пропадала сеть, планируется переустановка Windows на диске C (другие диски не трогаются). Три проекта — BattleBot, ASTRO, Nutrition — живут на C: и синхронизируются Google Диском. Ниже: главный риск, два списка (Клод / Windows-программы) и пошаговая инструкция восстановления на чистой машине.

---

### ⚠️ ГЛАВНЫЙ РИСК — прочитать до сноса системы

**ЗАКРЫТО 2026-08-04.** Проверено `git remote -v` — у ASTRO и Nutrition не было remote, вся история git существовала только локально. Резервное копирование Google Диска копирует файлы "как есть" (включая `.git`), а не делает git-синхронизацию — если бэкап поймает `.git` в момент записи (посреди `git commit`/`gc`), можно получить повреждённый архив вместо рабочего репозитория. Для BattleBot это было не страшно (есть GitHub), для ASTRO и Nutrition — единственная копия истории.

Решение: заведены **приватные** GitHub-репозитории (не публичные, как у BattleBot — там `.env`/секреты и БД никогда не должны попасть в публичный доступ) и запушена текущая история:

| Проект | Git remote |
|---|---|
| `C:\BattleBot` | `github.com/Yevgeniy204566/totalhunter.git` (публичный — так и должно быть, см. `feedback_github_public_private.md`) |
| `C:\ASTRO` | `github.com/Yevgeniy204566/astro.git` (приватный, создан и запушен 2026-08-04) |
| `C:\Nutrition` | `github.com/Yevgeniy204566/nutrition.git` (приватный, создан и запушен 2026-08-04) |

Перед пушем вся история обоих новых репозиториев проверена на секреты (`git log --all --diff-filter=A --name-only` + греп по `.env`/`service_account`/`credentials.json`/`settings.local.json`/ключам) — чисто, `.gitignore` всегда исключал эти файлы, в историю никогда не попадали.

GitHub здесь закрывает конкретно риск повреждения `.git`, а не заменяет Google Диск: секреты (`.env`, `service_account.json`, `settings.local.json`, `*.db`) сознательно остаются вне git у всех трёх проектов и защищены только файловым бэкапом Google Диска — это отдельно проверено (см. ниже), и разносить их по двум разным системам резервного копирования не нужно.

---

### Список 1 — Claude Code: рантайм, плагины, скилы, интеграции

**Базовый рантайм (нужно поставить до Claude Code):**
- Node.js — сейчас v24.14.1 (Claude Code CLI и `bd` — npm-пакеты)
- Git — сейчас 2.53.0.windows.2
- GitHub CLI (`gh`) — сейчас 2.92.0, залогинен как `Yevgeniy204566` (после переустановки — заново `gh auth login`)
- Python 3.13.5 (полный набор компонентов, включая "Add to Path") — нужен для backend Nutrition/ASTRO
- Visual Studio Build Tools 2022 — нужен для сборки нативных Python/Node зависимостей

**Claude Code CLI (глобальные npm-пакеты):**
```
npm install -g @anthropic-ai/claude-code   # сейчас 2.1.221
npm install -g @beads/bd                    # сейчас 1.1.0 (CLI трекера задач)
```
После установки: `claude` → войти через тот же аккаунт (OAuth-логин в браузере, файл `.credentials.json` НЕ переносится и не должен — секрет, см. ниже).

**Плагины (сейчас включены в `C:\Users\Admin\.claude\settings.json` → `enabledPlugins`):**
| Плагин | Маркетплейс | Как восстановить |
|---|---|---|
| `superpowers` | `claude-plugins-official` (встроенный) | появится сам после установки Claude Code, включить через `/plugin` |
| `vercel` | `claude-plugins-official` (встроенный) | то же |
| `beads` | `beads-marketplace` → github `steveyegge/beads` | `/plugin marketplace add steveyegge/beads`, затем `/plugin install beads` |
| `template-bridge` | `template-bridge-marketplace` → github `maslennikov-ig/template-bridge` | `/plugin marketplace add maslennikov-ig/template-bridge`, затем `/plugin install template-bridge` |

Самый надёжный способ не делать это вручную — восстановить сам файл `C:\Users\Admin\.claude\settings.json` из бэкапа (см. инструкцию ниже), тогда Claude Code сам подтянет маркетплейсы и плагины при следующем запуске.

**Скилы, которые дают эти плагины (полный список на момент 2026-08-04):**
- `superpowers:*` — brainstorming, test-driven-development, systematic-debugging, writing-plans, executing-plans, subagent-driven-development, requesting-code-review, receiving-code-review, verification-before-completion, using-git-worktrees, writing-skills, dispatching-parallel-agents, finishing-a-development-branch, using-superpowers
- `beads:*` — audit, blocked, comments, decision, epic, export, import, init, quickstart, ready, rename-prefix, restore, search, show, stats, sync, version, workflow, beads (основной)
- `template-bridge:*` — browse-templates, template-catalog, unified-workflow
- `vercel:*` (скилы) — bootstrap, deploy, env, status, ai-architect, ai-gateway, ai-sdk, auth, cdn-caching, chat-sdk, deployments-cicd, env-vars, eve, knowledge-update, marketplace, microfrontends, next-cache-components, next-forge, next-upgrade, nextjs, react-best-practices, routing-middleware, runtime-cache, shadcn, turbopack, vercel-agent, vercel-cli, vercel-connect, vercel-firewall, vercel-functions, vercel-sandbox, vercel-storage, verification, workflow
- `vercel:*` (агенты через Agent tool) — ai-architect, deployment-expert, performance-optimizer

**Встроенные скилы Claude Code (идут с самим CLI, ничего доустанавливать не нужно):** dataviz, artifact-design, artifact-diagramming, artifact-capabilities, verify, run, init, review, security-review, update-config, keybindings-help, loop, schedule, claude-api, fewer-permission-prompts

**Отдельно установленный глобальный скил (НЕ встроенный, лежит в `C:\Users\Admin\.claude\skills\`):** `material-3` — если понадобится, поставить заново отдельно.

**Встроенные типы субагентов (через Agent tool, идут с CLI):** Explore, general-purpose, Plan, claude-code-guide, statusline-setup, beads:task-agent, + vercel:ai-architect/deployment-expert/performance-optimizer

**Интеграции/MCP:**
- **Chrome-расширение claude-in-chrome** — ставится отдельно из Chrome Web Store и связывается с Claude Code заново (не файл, не переносится бэкапом)
- **Google Drive-коннектор** (`mcp__claude_ai_Google_Drive__*`) — привязан к аккаунту на стороне Anthropic (claude.ai), не локальный файл, переподключать через настройки коннекторов на claude.ai
- **Vercel MCP** — OAuth, переавторизовать через `vercel authenticate` при первом использовании
- **Проектный MCP-сервер `screenshot`** (только у BattleBot) — прописан в `C:\Users\Admin\.claude.json` (не в git!): `npx -y @modelcontextprotocol/server-screenshot`. Если файл `.claude.json` не восстановится из бэкапа — нужно будет добавить вручную.

**Beads (трекер задач):** база данных каждого проекта — это Dolt DB внутри `.beads/` в самой папке проекта (BattleBot/ASTRO/Nutrition), экспорт в `.beads/issues.jsonl`. Едет вместе с проектом (git и/или файловый бэкап Google Диска) — отдельно ничего переносить не нужно.

---

### Быстрый старт после переустановки — Python + вся среда Клода (CMD, копировать-вставить)

Узкий скоуп: остальные программы (Office, Photoshop, ACDSee и т.д.) ставятся вручную с инсталляторов на диске D — этот блок только про то, что нужно для запуска Python и Claude Code со всеми плагинами. Все ID проверены прямо на этой машине через `winget show`/`winget search` перед записью сюда, не на память. Каждая команда — для окна `cmd.exe`.

**Шаг 1 — рантайм.** Если для Python/Node/Git уже есть инсталлятор на диске D — можно запустить его вместо этих команд, результат тот же:
```
winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements --override "/quiet PrependPath=1 Include_test=0"
winget install --id OpenJS.NodeJS -e --accept-package-agreements --accept-source-agreements
winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
```
⚠️ После этого шага **закрыть окно cmd и открыть новое** — иначе `python`/`node`/`git` не появятся в PATH (классические грабли Windows).

**Шаг 2 — сам Claude Code + Beads CLI:**
```
npm install -g @anthropic-ai/claude-code
npm install -g @beads/bd
```

**Шаг 3 — вернуть плагины/скилы/память.** Работает только ПОСЛЕ того, как Google Диск восстановил папку `C:\Nutrition` (там лежит бэкап, см. выше "Что сделали СЕЙЧАС"):
```
mkdir "%USERPROFILE%\.claude\skills" 2>nul
copy /Y "C:\Nutrition\CLAUDE_USER_CONFIG_BACKUP\settings.json" "%USERPROFILE%\.claude\settings.json"
copy /Y "C:\Nutrition\CLAUDE_USER_CONFIG_BACKUP\dot-claude.json" "%USERPROFILE%\.claude.json"
robocopy "C:\Nutrition\CLAUDE_USER_CONFIG_BACKUP\skills\material-3" "%USERPROFILE%\.claude\skills\material-3" /E
robocopy "C:\Nutrition\CLAUDE_USER_CONFIG_BACKUP\projects\C--BattleBot\memory" "%USERPROFILE%\.claude\projects\C--BattleBot\memory" /E
robocopy "C:\Nutrition\CLAUDE_USER_CONFIG_BACKUP\projects\C--ASTRO\memory" "%USERPROFILE%\.claude\projects\C--ASTRO\memory" /E
robocopy "C:\Nutrition\CLAUDE_USER_CONFIG_BACKUP\projects\C--Nutrition\memory" "%USERPROFILE%\.claude\projects\C--Nutrition\memory" /E
```
(`robocopy` возвращает код 0-7 при успехе, не только 0 — это нормально, не признак ошибки.)

**Шаг 4 — запустить и войти:**
```
cd C:\Nutrition
claude
```
Внутри Claude Code — войти по запросу (откроется браузер, `.credentials.json` мы намеренно не переносили, см. риск-раздел выше).

**Шаг 5 — если плагины не подтянулись сами** (проверить командой `/plugin` внутри Claude Code) — выполнить там же:
```
/plugin marketplace add steveyegge/beads
/plugin install beads
/plugin marketplace add maslennikov-ig/template-bridge
/plugin install template-bridge
```
`superpowers` и `vercel` — из встроенного маркетплейса `claude-plugins-official`, обычно подтягиваются сами вместе с восстановленным `settings.json`, отдельно добавлять не нужно.

**Опционально, если сразу нужен полный цикл деплоя BattleBot** (не обязательно в первую сессию):
```
winget install --id GitHub.cli -e --accept-package-agreements --accept-source-agreements
winget install --id Google.CloudSDK -e --accept-package-agreements --accept-source-agreements
```
Потом `gh auth login` и `gcloud auth login` — оба интерактивные (открывают браузер), выполнить самому, не через Клода.

---

### Список 2 — программы Windows, установленные сейчас на диске C

**Драйверы/железо (AMD) — переустанавливаются ОДНИМ инсталлятором с сайта AMD (Adrenalin/chipset package), не по частям:**
AMD Software 25.8.1, AMD Chipset Software, AMD Settings, AMD PSP Driver, AMD GPIO2 Driver, AMD Ryzen Balanced Driver, AMD SBxxx SMBus Driver, RyzenMasterSDK, Promontory_GPIO Driver, AMD DVR64/WVR64, Branding64

**Браузеры:** Google Chrome, Mozilla Firefox, Opera,

**Мессенджеры/связь:** Telegram Desktop, Discord, AnyDesk, 

**Облако/синхронизация:** Google Drive, 

**Разработка:** Git, GitHub CLI, Node.js, Python 3.13.5 (полный набор), Visual Studio Code, Visual Studio Build Tools 2022 + Community, Windows SDK (10.1.26100.7705), Inno Setup 6.7.1, Tesseract-OCR 5.5.0

**Офис:** Microsoft Office LTSC Professional Plus 2021 (en-us + ru-ru), Project Professional 2021 (en-us + ru-ru), Visio LTSC Professional 2021 (en-us + ru-ru) — ⚠️ нужен установочный образ + лицензионный ключ, Windows Store их не даст

**Медиа/графика:** Adobe Photoshop 2020 ⚠️ (инсталлятор+лицензия — есть на диске D), ACDSee Pro 10 ⚠️ (есть на диске D), Audacity 3.7.4, AIMP, GOM Player Plus 2.3.61.5325 ⚠️ (RePack by Dodakaedr, есть на диске D), DAEMON Tools Ultra, LAV Filters

**Утилиты:** 7-Zip, CCleaner 5.74.8184 ⚠️ (RePack by Dodakaedr, есть на диске D), Advanced Renamer, Duplicate Photo Cleaner 7

**Прочее:** µTorrent, Google Cloud SDK

⚠️ = помечены программы, где обычный магазин/офсайт не даст точную версию — нужен оригинальный установочный файл (и/или ключ), который стоит заранее скопировать в синхронизированную папку Google Диска, а не искать заново после переустановки.

---

### Что сделали СЕЙЧАС (2026-08-04) — Риск №2 закрыт

`C:\Users\Admin\.claude` (глобальный конфиг, ~363 МБ) не входит ни в один из трёх синхронизируемых проектов сам по себе — это и был Риск №2. Решение: **не трогать настройки бэкапа Google Диска**, а продублировать критичные файлы оттуда прямо ВНУТРЬ всех трёх проектов, раз они и так синкаются.

Создана папка `CLAUDE_USER_CONFIG_BACKUP\` — идентичная копия лежит сразу в трёх местах: `C:\BattleBot\`, `C:\ASTRO\`, `C:\Nutrition\`. Синхронизации любой ОДНОЙ из трёх папок достаточно, чтобы восстановить всё. Добавлена в `.gitignore` всех трёх репо (проверено `git status --ignored` — не попадёт в коммит).

Внутри (README.md с точными путями восстановления лежит там же):
- `settings.json` — список активных плагинов Claude Code
- `dot-claude.json` — MCP-серверы (в т.ч. `screenshot` у BattleBot), история проектов
- `skills\material-3\` — отдельно поставленный скил (не встроен в CLI)
- `projects\C--BattleBot\memory\`, `projects\C--ASTRO\memory\`, `projects\C--Nutrition\memory\` — вся персистентная память по всем трём проектам, включая `reference_secrets.md` BattleBot (токены GCP/Vercel/NOWPayments/Telegram — см. раздел "BattleBot: GCP/Vercel/GitHub" ниже)

Осознанно НЕ скопировано: `.credentials.json` (логин-токен — секрет, эти три папки живут в git-репозиториях, у BattleBot к тому же публичный GitHub remote — секрету там не место; после переустановки просто `claude` → войти заново, 30 секунд) и сессионная история (~291 МБ, не критична для восстановления функциональности).

**Дальше по списку — то, что ещё стоит сделать перед сносом:**
1. ~~Собрать инсталляторы для программ с ⚠️~~ — не нужно, все инсталляторы (Office, Photoshop, ACDSee, GOM Player Plus и т.д.) уже есть на диске D.
2. **Проверить в приложении Google Диска** (значок в трее → Настройки → Резервное копирование), что папки BattleBot/ASTRO/Nutrition реально в статусе "Синхронизировано", а не "Ожидание"/с ошибками — прямо перед сносом. Особое внимание — что `CLAUDE_USER_CONFIG_BACKUP\` внутри каждой из них тоже долетела (это новые файлы, добавлены только что).

---

### BattleBot: восстановление GCP/Vercel/GitHub — "прокачанных" возможностей

BattleBot — единственный проект с полным автономным циклом деплоя (Клод делает сам, без ручных шагов владельца): пуш на GitHub → релиз бота, GCP SSH → бэкенд, Vercel deploy hook → сайт. Чтобы это не пришлось настраивать заново с нуля:

- **gcloud CLI** — сейчас установлен через `winget install Google.CloudSDK` (это и есть "Google Cloud SDK" в Списке 2). После переустановки — тот же способ, затем `gcloud auth login` (интерактивный OAuth в браузере — Клод не может выполнить это сам, нужно попросить владельца запустить через `! <command>` в чате, паттерн уже отработан).
- **Секреты для GCP/Vercel/Discord/NOWPayments/Telegram** — в открытом виде **нигде в этом файле не пишу** (репозиторий BattleBot публичный на GitHub). Все актуальные значения уже лежат в приватной памяти BattleBot (`reference_secrets.md`) — она включена в `CLAUDE_USER_CONFIG_BACKUP\projects\C--BattleBot\memory\`, то есть защищена тем же файловым бэкапом Google Диска, что и сами проекты.
- **Файлы-носители секретов ТОЛЬКО на диске** (в `.gitignore`, в публичный репозиторий никогда не попадают — их единственная защита это файловый бэкап Google Диска самих папок проектов, а НЕ git):
  - `C:\BattleBot\service_account.json` (Service Account для sync_to_gemini.py)
  - `C:\BattleBot\.claude\settings.local.json`, `C:\ASTRO\.claude\settings.local.json`, `C:\Nutrition\.claude\settings.local.json` (Vercel-токен и др.)
  - `.env` / `.env.local` во всех трёх проектах
  - **Проверено напрямую через Google Drive API (2026-08-04), не на словах:** `settings.local.json` (все три проекта, включая Vercel/Admin-токены) и `service_account.json` (Gemini SA-ключ) реально загружены в облако — нашлись поиском по Google Диску с актуальным содержимым и свежим `modifiedTime`. Секреты синхронизируются уже сейчас, отдельная папка под них не нужна — она была бы либо тоже в `.gitignore` (тот же уровень защиты, что уже есть), либо вне git-репозиториев вообще (тогда Google Диск её и так не видит, если это не внутри одной из трёх папок).
  - **НЕ удалось подтвердить тем же способом:** `.env`/`backend/.env` — поиск по точному имени `.env` в Drive API не находит файлы с ведущей точкой (техническое ограничение поиска, не обязательно означает отсутствие файла). Разово проверить руками на drive.google.com → Компьютеры → [эта машина] → зайти в папку каждого проекта → убедиться, что `.env`/`backend/.env` видны, ДО сноса системы.
  - После восстановления на новой машине — обязательно проверить, что эти файлы реально долетели (не только код). Если какого-то не окажется — значение есть в памяти (`reference_secrets.md`), перевыпускать не придётся, только скопировать вручную из памяти в нужный файл.
- **Полная карта деплоя** (какая команда куда, VM/zone/project id, Vercel deploy hook, `gh release create`) — уже задокументирована в памяти BattleBot (`project_deploy_architecture.md`, `project_gcp_ssh.md`, `feedback_vercel_deploy.md`, `project_gcloud_local_access.md`, `feedback_github_public_private.md`). Она тоже едет вместе с `CLAUDE_USER_CONFIG_BACKUP` — не дублирую здесь, чтобы не разъезжались две копии.
- **GitHub CLI** — уже залогинен (`gh auth status` → `Yevgeniy204566`), но это токен в Windows Credential Manager, переустановка его сотрёт — `gh auth login` заново.

---

### Инструкция: восстановление на чистой машине

1. Установить Windows, драйверы AMD (единый пакет с сайта AMD), базовые браузер + Google Диск.
2. Войти в Google Диск тем же аккаунтом → в настройках "Резервное копирование и синхронизация" вернуть те же папки (Диск предложит их автоматически, если это тот же аккаунт — папки появятся под "Компьютеры" на drive.google.com, либо восстановятся на прежние пути при повторном выборе тех же локальных путей C:\BattleBot, C:\ASTRO, C:\Nutrition, C:\Users\Admin\.claude).
3. Дождаться полной синхронизации (может занять часы на 363+ МБ конфига плюс сами проекты с логами/БД) — не открывать проекты в Claude Code до завершения закачки, иначе можно словить гонку (частично скачанный `.git` или `dev.db`).
4. Поставить рантайм по порядку: Git → Node.js → Python 3.13.5 (с "Add to Path") → Visual Studio Build Tools 2022 → GitHub CLI (`gh auth login`).
5. `npm install -g @anthropic-ai/claude-code @beads/bd`
6. Запустить `claude` из `C:\Nutrition` (или BattleBot/ASTRO) → он должен подхватить восстановленный `C:\Users\Admin\.claude\settings.json` (плагины) и `.claude.json` (MCP BattleBot, история проектов) автоматически. Если файлы не восстановились — плагины ставить вручную по таблице из Списка 1.
7. Войти в Claude Code (`claude login`) — заново, credentials не переносятся.
8. Переустановить Chrome-расширение claude-in-chrome, если нужно.
9. В каждом проекте проверить `git status`, `git log -1`, `bd stats` — убедиться, что репозиторий и база задач не повреждены переносом. Для Nutrition дополнительно свериться с `STATE.md` и `MEMORY.md` — они должны совпадать с тем, что было перед сносом.
10. Проверить `git remote -v` в ASTRO/Nutrition — должны быть приватные `github.com/Yevgeniy204566/astro.git` и `github.com/Yevgeniy204566/nutrition.git`; при желании `git pull` как дополнительная сверка с файловым бэкапом.
