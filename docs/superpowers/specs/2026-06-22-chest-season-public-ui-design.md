# Сундуки — UI публичной страницы: сезон, таймер, ранг, подсветка (Спека 3 из 3)

Дата: 2026-06-22

## Контекст

Спека 1 добавила хранение настроек сезона и кабинет для их редактирования.
Спека 2 подключила фильтрацию по датам и подсчёт `quota_chests` (только
Epic-склепы, отмеченные кланом как «считать в квоту») на бэкенде, и уже
передаёт в `GET /api/v1/chests/summary/{slug}` всё необходимое: `targets:
{points, chests}`, `period_start`, `period_end`, `timezone_offset_minutes`,
плюс `quota_chests` на каждого игрока. `chest_types` уже отдаётся
отсортированным по убыванию общего количества (сделано раньше, в
`2026-06-20-chest-summary-redesign` — не трогаем, переиспользуем как есть).

Эта спека — чисто фронтенд: `web/src/pages/ChestSummaryPage.jsx` +
`web/src/styles/theme.css`. Backend не меняется.

## Решённые вопросы

- **Критерий «выполнил норму»** — обе цели одновременно (очки **и**
  Epic-квота). Прогресс для цветовой шкалы — `ratio = min(очки/цель_очков,
  epic/цель_epic)` по тем целям, что заданы (если задана только одна —
  ratio считается только по ней). Если ни одна цель не задана — весь
  сезонный UI (шапка, таймер, подсветка, переименование колонки) не
  показывается, страница выглядит как сейчас.
- **Таймер** — считается в часовом поясе клана (`timezone_offset_minutes`),
  не в поясе посетителя: `clanNowMillis = Date.now() + offsetMinutes *
  60000`, `period_end` парсится как наивные wall-clock компоненты (без
  `new Date(string)`, чтобы не словить переинтерпретацию браузером в его
  локальном поясе) и сравнивается напрямую с `clanNowMillis`.
- **Состав колонок таблицы** (уточнено владельцем) — старая колонка «Всего
  сундуков» (`total`, по всем сундукам паттерна) убирается из отображения
  полностью. Итоговый порядок:
  1. `#` — место (по текущей сортировке игроков по очкам убыв.)
  2. `Player`
  3. `Очки` (`points`)
  4. `Epic склепов` (`quota_chests`)
  5. Динамические колонки по `data.chest_types` (уже отсортированы бэкендом
     по убыванию суммарного количества — без изменений)
- Закреплены при горизонтальном скролле: `#` и `Player` (первые две
  колонки), с учётом фона зебры/hover — закреплённые ячейки должны иметь
  непрозрачный фон, совпадающий с фоном своей строки в её текущем
  состоянии (чётная/нечётная/hover), иначе сквозь них будет просвечивать
  контент при скролле.

## Frontend

### `ChestSummaryPage.jsx` — структура

```
<h1 className="gradient-text public-summary-title">{kingdom} / {clan}</h1>

{hasSeasonTargets && (
  <div className="public-season-info">
    <span className="public-season-badge">
      Цель сезона: {targets.points ?? '—'} очков / {targets.chests ?? '—'} Epic-склепов
    </span>
    {timezone_offset_minutes != null && (
      <span className="public-season-badge">Часовой пояс: UTC{offsetLabel}</span>
    )}
    {period_end && <CountdownTimer periodEnd={period_end} offsetMinutes={timezone_offset_minutes ?? 0} />}
  </div>
)}

<div className="public-summary-updated">Последнее обновление: {updatedLabel}</div>
<div className="public-summary-divider" />

<table className="public-table">
  <thead>
    <tr>
      <th>#</th><th>Player</th><th>Очки</th><th>Epic склепов</th>
      {chest_types.map(...)}
    </tr>
  </thead>
  <tbody>
    {players.map((p, i) => (
      <tr className={rowColorClass(p, i, targets)}>
        <td>{i + 1}</td>
        <td>{p.name}</td>
        <td className="public-points-cell">{p.points}</td>
        <td className={p.quota_chests === 0 ? 'public-cell-zero' : ''}>{p.quota_chests}</td>
        {chest_types.map(t => ...)}
      </tr>
    ))}
  </tbody>
</table>
```

`hasSeasonTargets = targets.points != null || targets.chests != null`.

### Таймер — отдельная маленькая функция/компонент в том же файле

Чистая функция вычисления остатка (без React-обвязки она не нуждается в
отдельном файле — компонент маленький, по аналогии с тем, что весь файл и
сейчас один компонент):

```js
function formatRemaining(periodEndIso, offsetMinutes) {
  const [datePart, timePart] = periodEndIso.split('T')
  const [y, mo, d] = datePart.split('-').map(Number)
  const [h, mi, s] = timePart.split(':').map(Number)
  const periodEndMillis = Date.UTC(y, mo - 1, d, h, mi, s || 0)
  const clanNowMillis = Date.now() + offsetMinutes * 60000
  const remaining = periodEndMillis - clanNowMillis
  if (remaining <= 0) return 'Сбор завершён'
  const totalMinutes = Math.floor(remaining / 60000)
  const days = Math.floor(totalMinutes / (24 * 60))
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60)
  const minutes = totalMinutes % 60
  return `Осталось: ${days} дн. ${hours} ч. ${minutes} мин.`
}
```

Компонент `CountdownTimer` держит `useState`+`useEffect` с `setInterval`
(каждые 60 секунд достаточно — никто не ждёт секундной точности на
обзорной странице клана), вызывает `formatRemaining` на каждый тик.

### Цветовая логика строк

```js
function rowColorClass(player, rank, targets) {
  const ratios = []
  if (targets.points) ratios.push(player.points / targets.points)
  if (targets.chests) ratios.push(player.quota_chests / targets.chests)
  if (ratios.length === 0) return ''
  const ratio = Math.min(...ratios)
  if (ratio >= 1 && rank < 3) return 'row-top3'
  if (ratio >= 0.5) return ''
  if (ratio > 0) return 'row-lagging'
  return 'row-danger'
}
```

(`rank` — индекс в уже отсортированном по очкам массиве, `0`-based, `rank
< 3` соответствует местам 1-3.) `targets.points`/`targets.chests`, равные
`0` или `null`, обе ветки `if` пропускают эту цель — деления на ноль не
происходит, цель просто не участвует в `ratios`.

### CSS (`theme.css`)

```css
.public-season-info { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.public-season-badge {
  background: var(--elevated); border: 1px solid var(--outline); border-radius: 8px;
  padding: 6px 12px; font-size: 13px; color: var(--on-surface2);
}
.public-season-timer { color: var(--accent); font-weight: 600; }

.public-table-wrap::-webkit-scrollbar { height: 10px; }
.public-table-wrap::-webkit-scrollbar-track { background: var(--elevated); border-radius: 4px; }
.public-table-wrap::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 4px; }
.public-table-wrap::-webkit-scrollbar-thumb:hover { background: var(--accent-glow); }

.row-top3 td { color: #50C878; font-weight: 600; }
.row-lagging td { color: #FFB347; }
.row-danger td { color: #FF6961; }

.public-table th:nth-child(1), .public-table td:nth-child(1) {
  position: sticky; left: 0; z-index: 2; width: 40px; background: var(--card);
}
.public-table th:nth-child(2), .public-table td:nth-child(2) {
  position: sticky; left: 40px; z-index: 2; background: var(--card);
}
.public-table tbody tr:nth-child(even) td:nth-child(1),
.public-table tbody tr:nth-child(even) td:nth-child(2) { background: #0D1326; }
.public-table tbody tr:hover td:nth-child(1),
.public-table tbody tr:hover td:nth-child(2) { background: var(--accent-glow); }
.public-table tbody tr.row-top3 td:nth-child(1),
.public-table tbody tr.row-top3 td:nth-child(2) { background: var(--card); }
.public-table tbody tr.row-top3:nth-child(even) td:nth-child(1),
.public-table tbody tr.row-top3:nth-child(even) td:nth-child(2) { background: #0D1326; }
```

Последние 4 правила — фон закреплённых ячеек должен оставаться непрозрачным
даже у цветных (`row-top3`/`row-lagging`/`row-danger`) строк; цвет текста
(`color`) уже задан общим правилом `.row-top3 td` и применяется к
закреплённым ячейкам автоматически — переопределяем здесь только `background`,
чтобы цвет фона зебры/обычного ряда был виден сквозь sticky-позиционирование,
а не сквозь него проступали соседние строки.

## Вне рамок

- Любые изменения бэкенда — не нужны, всё нужное уже передаётся.
- Сама колонка `total` (все сундуки паттерна) — данные остаются в ответе
  API на будущее, просто не выводятся в этой таблице.

## Тестирование

- Нет фронтенд-автотестов в репозитории — живая проверка в браузере:
  настроить тестовый сезон через `/dashboard/chests` (даты, цели, отметить
  пару типов «Считать в квоту»), открыть публичную страницу, проверить
  порядок колонок, таймер, цвета строк (искусственно — на тестовом клане
  с маленькими цифрами целей, чтобы реально увидеть все 4 цвета), sticky-
  скролл на узком окне, кастомный скроллбар в Chrome.
