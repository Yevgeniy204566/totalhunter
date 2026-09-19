# Публикация находок Биржи 2.0 в РОЙ — План, часть 28: сайт, деплой (гейт), SPEC→PLAN check

> Индекс, цель, архитектура, Global Constraints и карта файлов — в [`exchange-scout-roy-publication-plan-24.md`](exchange-scout-roy-publication-plan-24.md). Исполнять inline, **без субагентов** (золотое правило `CLAUDE.md` §4); код — только после одобрения плана владельцем.
> Задачи этой части: Task 5, Task 6. Части плана: [25](exchange-scout-roy-publication-plan-model-25.md) · [26](exchange-scout-roy-publication-plan-post-endpoint-26.md) · [27](exchange-scout-roy-publication-plan-read-client-27.md) · [28](exchange-scout-roy-publication-plan-web-deploy-check-28.md). Спека: `docs/superpowers/specs/exchange-scout-roy-publication-design-01.md` (файлы 01–06).

---

### Task 5: Блок «Находки Биржи 2.0» на странице РОЙ

**Invariant:** P-10 (блок, загрузка при открытии + кнопка «Обновить»), P-11 (тексты только фактами, RU/EN).
**Existing:** `web/src/pages/RoyPage.jsx` — `API_BASE` (:5), `isRu` (:19-20), список королевств (:84-142), подсказка (:171-180). Существующие
`useEffect`, список королевств и SSE не редактируются — только добавления.

**Files:** Modify `web/src/pages/RoyPage.jsx`.

- [ ] **Step 1:** после `const [connected, setConnected] = useState(false)` добавить состояние:
  `const [finds, setFinds] = useState(null)` (`null` — ещё не загружено), `const [findsError, setFindsError] = useState(false)`.
- [ ] **Step 2:** добавить функцию и отдельный `useEffect` (не трогать существующий):

```jsx
  const loadFinds = () => {
    fetch(`${API_BASE}/roy/scout-finds`)
      .then(r => r.json())
      .then(d => { setFinds(d.finds || []); setFindsError(false) })
      .catch(() => setFindsError(true))
  }
  useEffect(() => { loadFinds() }, [])
```

- [ ] **Step 3:** между `{/* ── Legend ── */}` и `{/* ── Hint ── */}` вставить блок (стили — те же CSS-переменные, что у соседних карточек):

```jsx
      {/* ── Scout finds (Exchange 2.0) ── */}
      <div style={{
        background: 'var(--card)', borderRadius: 14, border: '1px solid var(--outline)',
        padding: '16px 20px', marginBottom: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--on-surface)' }}>
            {isRu ? 'Находки Биржи 2.0' : 'Exchange 2.0 finds'}
          </span>
          <button onClick={loadFinds} style={{
            background: 'transparent', border: '1px solid var(--outline)', color: 'var(--on-surface2)',
            borderRadius: 8, padding: '4px 12px', fontSize: 12, cursor: 'pointer',
          }}>{isRu ? 'Обновить' : 'Refresh'}</button>
        </div>
        <p style={{ fontSize: 12, color: 'var(--on-surface2)', lineHeight: 1.55, margin: '8px 0 12px' }}>
          {isRu
            ? 'Примерное расположение: позиция экрана бота в момент кадра, не точные координаты биржи. Запись показывается 30 минут после публикации.'
            : 'Approximate location: the bot screen position at the moment of the frame, not the exact exchange coordinates. An entry is shown for 30 minutes after publication.'}
        </p>
        {findsError ? (
          <div style={{ fontSize: 13, color: 'var(--on-surface2)' }}>
            {isRu ? 'Не удалось загрузить находки.' : 'Failed to load finds.'}
          </div>
        ) : finds === null ? null : finds.length === 0 ? (
          <div style={{ fontSize: 13, color: 'var(--on-surface2)' }}>
            {isRu ? 'Сейчас находок нет.' : 'No finds right now.'}
          </div>
        ) : finds.map((f, i) => (
          <div key={i} style={{
            display: 'flex', gap: 14, padding: '8px 0', fontSize: 13,
            borderTop: i === 0 ? 'none' : '1px solid var(--outline)', color: 'var(--on-surface)',
          }}>
            <span style={{ fontWeight: 700 }}>K {f.kingdom}</span>
            <span>X {f.x} · Y {f.y}</span>
            <span style={{ marginLeft: 'auto', color: 'var(--on-surface2)' }}>
              {new Date(f.found_at).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>
```

- [ ] **Step 4: Verify** `cd web && npm run build` → успешная сборка без ошибок (`vite build` + `prerender.mjs`); `npm run lint -- src/pages/RoyPage.jsx`.
- [ ] **Step 5: Ручная проверка PT-13** (после Task 6): открыть `/roy` — блок виден, пустое состояние, кнопка «Обновить»,
  тексты RU/EN (переключатель языка), список королевств выше не изменился.
- [ ] **Step 6: Commit** `git add web/src/pages/RoyPage.jsx` → `git commit -m "feat(web): блок находок Биржи 2.0 на странице РОЙ"`.

---

### Task 6 (ГЕЙТ — только после явного «да» владельца): деплой

Деплой необратим и внешний — выполняется по карте деплоя `CLAUDE.md`, порядок: сервер → сайт.

- [ ] **Step 1: Полный прогон** `cd server && python -m pytest -q` и `python -m pytest test_roy_scout_client.py -q` — всё зелёное.
- [ ] **Step 2: Сервер (GCP).** `git push origin main`; на сервере: `cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ &&
  sudo git pull origin main`. Миграция — **вручную** (Alembic на GCP падает без `DATABASE_URL`, память `project_server_architecture`):
  создать таблицу через `sudo -u postgres psql -d totalhunter` теми же DDL, что в миграции (id SERIAL PK, kingdom/x/y INTEGER NOT NULL,
  reporter_hwid VARCHAR(16) NOT NULL, found_at TIMESTAMPTZ NOT NULL DEFAULT now(), индексы на kingdom и found_at),
  `UPDATE alembic_version SET version_num='s3c4o5u6t7f8' WHERE version_num='b1a2c3k4s5e6';`,
  `GRANT ALL PRIVILEGES ON TABLE roy_scout_finds TO hunter;` и на её sequence. SQL передавать через base64
  (память `project_gcloud_local_access`). Затем `sudo systemctl restart totalhunter`.
- [ ] **Step 3: Проверка сервера.** `curl -s https://api.total-hunter.com/roy/scout-finds` → `{"finds":[]}`; существующий
  `curl -s https://api.total-hunter.com/roy/kingdoms` отвечает как раньше.
- [ ] **Step 4: Сайт.** По §6.5 `CLAUDE.md`: push + deploy hook + alias (все 3 шага).
- [ ] **Step 5: Проверка сайта** — PT-13 на `https://total-hunter.com/roy`.

---

## SPEC→PLAN consistency check

| Контракт спеки | Покрыт задачей | Тест |
|---|---|---|
| P-01 порядок списание→OCR→публикация | **НЕ в этом плане** — план consumer'а (Часть A/B) | PT-01, PT-02 там |
| P-02 только K/X/Y (x, y в диапазоне Integer), hwid не наружу | T2 (схема с `Field(ge,le)`), T3 (select колонок) | PT-03, PT-04 |
| P-03 отдельная таблица/эндпоинт | T1, T2 | PT-05 |
| P-04 без лимита/дедупа | T2 | PT-06 (concurrent-колонка спеки не проверяется: SQLite `StaticPool` = одно соединение; состояния между вызовами нет по построению) |
| P-05 валидация hwid/kingdom/x/y | T2 | PT-07, PT-08 |
| P-06 kingdom=0 → без публикации; K фиксируется при создании результата, не перечитывается из GUI | T4 (kingdom — параметр метода; проверка ≤0); фиксация K — план consumer'а | PT-09; PT-18 в плане consumer'а |
| P-07 не блокирует consumer | T4 | PT-10 |
| P-08 сбой проглатывается | T4 | PT-11 |
| P-09 публичный список без hwid | T3 | PT-04, PT-12 |
| P-10, P-11 сайт, тексты | T5 | PT-13 (ручной) |
| P-12 1.0 не тронута | T2–T4 (только добавления) | PT-14: `tests/test_roy.py` в шагах T2/T3 |
| P-13 срок 30 мин | T2 (очистка), T3 (фильтр) | PT-15, PT-16, PT-16 (граница) |

Отклонение от спеки: Concurrent-колонка PT-06 не проверяется (см. таблицу) — ограничение тестовой среды (SQLite `StaticPool`), не изменение контракта. PT-15 (файл 27, read-сторона `>`) проверяет границы точно (29:59 видна; 30:00 и 30:01 нет) через зафиксированные часы `roy.datetime`. PT-16 (файл 26, delete-на-INSERT сторона `<=`) — отдельный код с собственным сравнением, поэтому границу 30:00 покрывает отдельный тест `test_scout_find_insert_deletes_expired_at_exact_boundary` (frozen clock, 29:59/30:00/30:01) сверх исходного `test_scout_find_insert_deletes_expired` (31 мин/5 мин, общий случай) — read-сторона и delete-на-insert-сторона используют разные операторы (`>` vs `<=`) и не защищают границу друг друга.

## Самопроверка плана

- Плейсхолдеров нет: все шаги содержат код/команды.
- Согласованность имён: `RoyScoutFind`, `SCOUT_FIND_TTL_MIN`, `ScoutFindRequest`, `report_scout_find`, `/roy/scout-find`,
  `/roy/scout-finds` — одинаковы во всех задачах.
- Серверная часть (Task 1–3) ПРОВЕРЕНА 2026-09-18 во временной копии `server/` (репозиторий не менялся): 14 новых + 14 существующих тестов `test_roy.py` — 28 passed; мутации проверены: `int` вместо `StrictInt` роняет 2 теста, `>=` вместо `>` в границе TTL роняет тест PT-15. Сравнение aware-datetime в SQLite и зафиксированные часы работают.
- Не проверено до реализации: клиентская часть (Task 4) и сайт (Task 5), `npm run build`, применение миграции на GCP.
