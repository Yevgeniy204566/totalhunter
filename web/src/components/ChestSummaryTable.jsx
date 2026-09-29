import { useEffect, useMemo, useRef, useState } from 'react'
import { postPublicPlayerProfile } from '../api.js'

const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']
const TIERS = ['', '5', '6', '7', '8', '9']
const FULL_TROOP = 'G8 S8 M8'

function parseTroop(troop_level) {
  if (!troop_level) return { g: '', s: '', m: '' }
  const mat = troop_level.match(/G(\d+) S(\d+) M(\d+)/)
  return mat ? { g: mat[1], s: mat[2], m: mat[3] } : { g: '', s: '', m: '' }
}

function fmtNum(n) {
  if (n === null || n === undefined) return '—'
  return Number(n).toLocaleString('ru-RU')
}

function hexToRgb(hex) {
  const s = hex.replace('#', '')
  const full = s.length === 3 ? s.split('').map(c => c + c).join('') : s
  const n = parseInt(full, 16)
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 }
}
function rgbToHex({ r, g, b }) {
  return '#' + [r, g, b].map(v => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0')).join('')
}
function lerpColor(hexA, hexB, t) {
  const a = hexToRgb(hexA), b = hexToRgb(hexB)
  return rgbToHex({ r: a.r + (b.r - a.r) * t, g: a.g + (b.g - a.g) * t, b: a.b + (b.b - a.b) * t })
}
function multiLerp(stops, t) {
  const n = stops.length - 1
  const clamped = Math.max(0, Math.min(1, t))
  const scaled = clamped * n
  const idx = Math.min(Math.floor(scaled), n - 1)
  return lerpColor(stops[idx], stops[idx + 1], scaled - idx)
}
function hslToHex(h, s, l) {
  s /= 100; l /= 100
  const k = n => (n + h / 30) % 12
  const a = s * Math.min(l, 1 - l)
  const f = n => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))
  return rgbToHex({ r: 255 * f(0), g: 255 * f(8), b: 255 * f(4) })
}

// Имена по очкам (редизайн владельца 2026-09-28): ярче, без размытого свечения, плавный
// бесшовный блик; путь «норма → легенда» идёт через несколько оттенков, легенды — на лентах.
// 0 → цель: алый → оранжевый
const BELOW_QUOTA_STOPS = ['#FF2D55', '#FF9F0A']
// цель → цель+100к: салатовый → бирюза → голубой → фиолетовый → розовый → глубокая неоновая фуксия
// (не бежевый/жёлтый — скучно; не красный/оранжевый — это цвета «ниже цели»)
const ABOVE_QUOTA_STOPS = ['#3DFF7A', '#1FE5C8', '#4DB5FF', '#A77BFF', '#FF7AD9', '#E01AD6']
// куда уходит бегущая полоска перед легендой — синий, в тон лент легенд
const STRIPE_TO_LEGEND = '#3D6BFF'
// Пороги — во сколько раз игрок перекрыл цель сезона (владелец 2026-09-29): так шкала одинаково
// честная для клана с целью 5к и с целью 50к. От ×1 до ×10 — путь «норма → легенда»;
// Легенды I–XVII: шаг между званиями растёт на 1 каждые два звания (2,2,3,3,4,4,…).
const LEGEND_TIERS = [10, 12, 14, 17, 20, 24, 28, 33, 38, 44, 50, 57, 64, 72, 80, 89, 98]
const LEGEND_START = LEGEND_TIERS[0]

function mixWhite(hex, t) { return lerpColor(hex, '#FFFFFF', t) }

// Цвет пути чуть впереди игрока; после фуксии — к синему миру легенд.
function aheadColor(t) {
  if (t <= 1) return multiLerp(ABOVE_QUOTA_STOPS, t)
  return lerpColor(ABOVE_QUOTA_STOPS[ABOVE_QUOTA_STOPS.length - 1], STRIPE_TO_LEGEND, Math.min(1, (t - 1) / 0.3))
}

// Бегущая полоска — одного цвета, опережает цвет имени (следующий шаг пути), пастельная — не давит
// и не перебивает легенд (владелец 2026-09-29). Плитка фона — 2 ширины текста, края совпадают по
// цвету: полоска повторяется без рывка.
function shimmerGradient(c, t) {
  const h = mixWhite(aheadColor(t + 0.2), 0.45)
  return `linear-gradient(90deg, ${c} 0%, ${c} 22%, ${h} 32%, ${c} 42%, ${c} 72%, ${h} 82%, ${c} 92%, ${c} 100%)`
}

function legendaryGradient(tier, ratio) {
  // цветов перелива: легенда I — 2, … от V — 6
  const n = tier + 2
  // старт с холодных тонов; пара цветов — 120° по кругу (гармонично, не кислотно)
  const base = (160 + (ratio - LEGEND_START) * 12) % 360
  const step = n === 2 ? 120 : 360 / n
  const cols = []
  for (let i = 0; i < n; i++) cols.push(hslToHex((base + i * step) % 360, 100, 64))
  // палитра дважды на плитку 200% — перелив непрерывный
  const all = [...cols, ...cols, cols[0]]
  return `linear-gradient(90deg, ${all.map((c, i) => `${c} ${(i / (all.length - 1) * 100).toFixed(1)}%`).join(', ')})`
}

// Знамёна легенд (владелец 2026-09-29). Правило: оформление только держится или усложняется —
// после «ласточкина хвоста» назад к прямоугольнику нельзя.
// I–III — синяя лента; IV–V — прямой штандарт; VI–VII — ласточкин хвост; VIII–IX — + серебряная
// нить; с X — «камень в оправе» (золото, полоса камня, золотая нить), каждое звание — свой камень;
// с XI — ореол цвета камня; с XVI — ещё золотой волосок снаружи.
// Металл — вертикальный градиент (блик сверху, тень снизу): кайма читается как литая рамка.
const GOLD = 'linear-gradient(180deg, #FFF3C4, #D9A73A 55%, #8A5E14)'
const PLATINUM = 'linear-gradient(180deg, #F2F6FF, #9FB3D9 50%, #3E4F7A)'
const BRONZE = 'linear-gradient(180deg, #F3C18C, #B87333 55%, #5E3514)'
const LIGHT_AZURE = 'linear-gradient(180deg, #D8F0FF, #7FC4FF 55%, #2F6FC4)'
const SILVER_THREAD = '#DCE3EE'
const FIELD_BLUE = '#0B2A6B'
// поле течёт: плитка 200% без стыка
const fieldTile = (a, b) => `linear-gradient(90deg, ${a} 0%, ${b} 25%, ${a} 50%, ${b} 75%, ${a} 100%)`
// Поле у каждого звания своё (владелец 2026-09-29). IV–IX — холодная гамма под золотую раму,
// от лазури к фиолету; с X поле в тон своего камня. Все тёмные — радужное имя должно читаться.
const LEGEND_FIELDS = [
  fieldTile(FIELD_BLUE, '#1F5FC4'), // IV   лазурь
  fieldTile('#0A2A5E', '#0E7490'),  // V    морская волна
  fieldTile('#0B1F4D', '#2D4FD8'),  // VI   ультрамарин
  fieldTile('#0E1B45', '#5B3FC4'),  // VII  аметист
  fieldTile('#0A2540', '#0F8A7A'),  // VIII бирюза
  fieldTile('#101A3A', '#7A2E9E'),  // IX   фиолет
  fieldTile(FIELD_BLUE, '#7A1030'), // X    синий → рубин
  fieldTile('#1E0B3A', '#6B1E7A'),  // XI   пурпур
  fieldTile('#062A2A', '#0F6B55'),  // XII  изумруд
  fieldTile('#0A0C12', '#2A3040'),  // XIII обсидиан
  fieldTile('#2A0E08', '#8A3A10'),  // XIV  тлеющий огонь
  fieldTile('#0A1238', '#2B4FC8'),  // XV   сапфир
  fieldTile('#3A2410', '#1F6FB0'),  // XVI  бронза → лазурь
  fieldTile('#1A0C4A', '#5B3FD0'),  // XVII индиго
]
// камни X и выше — по порядку званий
const LEGEND_STONES = [
  { outer: GOLD, stone: 'linear-gradient(180deg, #F0475E, #A3102A 55%, #4E0512)', halo: '#FF7A8A' },     // X рубин
  { outer: GOLD, stone: 'linear-gradient(180deg, #C25AB2, #761A6A 55%, #340830)', halo: '#E59BDA' },     // XI пурпур
  { outer: GOLD, stone: 'linear-gradient(180deg, #3FD196, #0F7550 55%, #053A26)', halo: '#7BEBBB' },     // XII изумруд
  { outer: GOLD, stone: 'linear-gradient(180deg, #454B5C, #12141C 55%, #000000)', halo: '#A8B0C4' },     // XIII обсидиан
  { outer: GOLD, stone: 'linear-gradient(180deg, #FFC15A, #E0561F 55%, #7A1A08)', halo: '#FFD08A' },     // XIV огонь
  { outer: PLATINUM, stone: 'linear-gradient(180deg, #4A6BD8, #1A2E80 55%, #0A1238)', halo: '#B8CCFF' }, // XV сапфир
  { outer: BRONZE, stone: LIGHT_AZURE, halo: '#9FD6FF' },                                                // XVI бронза и лазурь
  { outer: LIGHT_AZURE, stone: 'linear-gradient(180deg, #6A4FD0, #3A1F8C 55%, #1A0C4A)', halo: '#B9A8FF' },  // XVII индиго
]

function legendBanner(tier) {
  if (tier <= 2) return null
  if (tier <= 8) {
    return {
      shape: tier <= 4 ? 'flag' : 'tail', flow: false, field: LEGEND_FIELDS[tier - 3],
      border: tier >= 7 ? [[GOLD, 2], [FIELD_BLUE, 1], [SILVER_THREAD, 1]] : [[GOLD, 2]],
    }
  }
  const st = LEGEND_STONES[Math.min(tier - 9, LEGEND_STONES.length - 1)]
  let border = [[st.outer, 2], [st.stone, 3], [GOLD, 1]]
  if (tier >= 10) border = [[st.halo, 1], ...border]
  if (tier >= 15) border = [[GOLD, 1], ...border]
  return { shape: 'tail', flow: true, field: LEGEND_FIELDS[Math.min(tier - 3, LEGEND_FIELDS.length - 1)], border }
}

function ImperialBanner({ spec, children }) {
  const field = (
    <span className={`public-imp-field${spec.flow ? ' public-imp-field--flow' : ''}`} style={{ '--imp-field': spec.field }}>
      {children}
    </span>
  )
  // на ласточкином хвосте вырез косой — по бокам кайма шире, иначе на скосе она выглядит тоньше
  const sideK = spec.shape === 'tail' ? 1.6 : 1
  return spec.border.reduceRight((inner, [color, w]) => (
    <span className={`public-imp-layer public-imp-${spec.shape}`} style={{ background: color, padding: `${w}px ${w * sideK}px` }}>
      {inner}
    </span>
  ), field)
}

// Базовый размер имени — CSS-переменная (ПК 17px — на кегль крупнее цифр 16px, телефон 14.5px);
// сверху — прибавка за очки: чем больше набрал, тем крупнее.
function nameSize(extraPx) { return `calc(var(--public-name-base) + ${extraPx.toFixed(2)}px)` }

function nameGradientStyle(player, targets) {
  const quota = targets?.points
  if (!quota) return null
  const ratio = player.points / quota
  if (ratio < 1) {
    return { mode: 'plain', color: multiLerp(BELOW_QUOTA_STOPS, ratio), fontSize: nameSize(0) }
  }
  if (ratio < LEGEND_START) {
    const t = (ratio - 1) / (LEGEND_START - 1)
    return { mode: 'shimmer', backgroundImage: shimmerGradient(multiLerp(ABOVE_QUOTA_STOPS, t), t), fontSize: nameSize(t * 3) }
  }
  const tier = LEGEND_TIERS.filter(x => ratio >= x).length - 1
  return {
    // цветов перелива не больше 6, шрифт растёт до VII — иначе радуга и слишком крупно
    mode: 'legendary', backgroundImage: legendaryGradient(Math.min(tier, 4), ratio),
    fontSize: nameSize(4.5 + Math.min(tier, 6) * 0.4),
    banner: legendBanner(tier),
  }
}

export function renderPlayerName(p, targets) {
  const s = nameGradientStyle(p, targets)
  if (!s) return p.name
  if (s.mode === 'legendary') {
    const text = (
      <span className="public-name-legendary" style={{ backgroundImage: s.backgroundImage, fontSize: s.fontSize }}>
        {p.name}
      </span>
    )
    if (s.banner) return <ImperialBanner spec={s.banner}>{text}</ImperialBanner>
    return <span className="public-name-banner public-name-banner--blue">{text}</span>
  }
  if (s.mode === 'shimmer') {
    return (
      <span className="public-name-shimmer" style={{ backgroundImage: s.backgroundImage, fontSize: s.fontSize }}>
        {p.name}
      </span>
    )
  }
  return <span className="public-name-plain" style={{ color: s.color, fontSize: s.fontSize }}>{p.name}</span>
}

function pointsHitTarget(player, targets) {
  return targets.points != null && player.points >= targets.points
}
// Столбцы квот (владелец 2026-09-26): по одному на квоту из targets.quotas; архив, закрытый
// до квот (нет targets.quotas), — прежний один столбец «Epic-склепы» из quota_chests.
export function quotaColumns(targets, epicLabel) {
  if (Array.isArray(targets?.quotas)) {
    return targets.quotas.map(q => ({
      key: `quota:${q.slot}`, name: q.name, target: q.target,
      personal: q.mode === 'per_player',
      get: p => p.quotas?.[String(q.slot)] ?? 0,
      // личная цель игрока (per_player): считает сервер по уровню Героя
      targetOf: p => (q.mode === 'per_player' ? p.quota_targets?.[String(q.slot)] : q.target),
      partialOf: p => !!p.quota_targets_partial?.[String(q.slot)],
    }))
  }
  return [{ key: 'quota:legacy', name: epicLabel, target: targets?.chests ?? null,
            get: p => p.quota_chests ?? 0 }]
}
function isEpicColumn(typeName) {
  return typeName.includes('Epic')
}

// Среднее по участникам таблицы (входящие п.5): сумма столбца / число игроков в таблице,
// нули входят в расчёт; от сортировки не зависит.
export function columnAverage(players, getValue) {
  if (!players.length) return 0
  return players.reduce((sum, p) => sum + (getValue(p) || 0), 0) / players.length
}

export function sortPlayers(players, sort, chestTypes, quotaCols = []) {
  const qcol = quotaCols.find(c => c.key === sort.key)
  const value = p => sort.key === 'name' ? p.name.toLowerCase()
    : sort.key === 'points' ? p.points
    : sort.key === 'hero' ? (p.hero_level ?? -1)
    : qcol ? qcol.get(p)
    : (p.counts[sort.key] || 0)
  const dir = sort.dir === 'asc' ? 1 : -1
  return [...players].sort((a, b) => {
    const va = value(a), vb = value(b)
    if (va < vb) return -dir
    if (va > vb) return dir
    return b.points - a.points || a.name.localeCompare(b.name)
  })
}

const TABLE_TXT = {
  ru: { player: 'Игрок', points: 'Очки', epic: 'Epic-склепы', avg: 'Среднее', rank: 'Звание', troops: 'Состав', hero: 'Герой',
        hideAvg: 'Скрыть средние', showAvg: 'Показать средние', saveError: 'Ошибка сохранения: ',
        heroCol: 'Герой' },
  en: { player: 'Player', points: 'Points', epic: 'Epic Crypts', avg: 'Average', rank: 'Rank', troops: 'Troops', hero: 'Hero',
        hideAvg: 'Hide averages', showAvg: 'Show averages', saveError: 'Save error: ',
        heroCol: 'Hero' },
}

export default function ChestSummaryTable({ chestTypes, players, targets, editMode = false, collectorSlug, lang = 'en', editButton = null }) {
  const tt = TABLE_TXT[lang] || TABLE_TXT.en
  const quotaCols = useMemo(() => quotaColumns(targets, tt.epic), [targets, tt.epic])
  // По умолчанию — порядок сервера (по очкам). «#» всегда место по очкам, не по текущей сортировке.
  const [sort, setSort] = useState(null)
  const pointsRank = useMemo(() => {
    const m = {}
    players.forEach((p, i) => { m[p.name] = i + 1 })
    return m
  }, [players])
  const shownPlayers = useMemo(
    () => (sort ? sortPlayers(players, sort, chestTypes, quotaCols) : players),
    [players, sort, chestTypes, quotaCols],
  )
  function toggleSort(key) {
    setSort(prev => {
      const firstDir = key === 'name' ? 'asc' : 'desc'
      if (!prev || prev.key !== key) return { key, dir: firstDir }
      return { key, dir: prev.dir === 'desc' ? 'asc' : 'desc' }
    })
  }
  function sortMark(key) {
    if (!sort || sort.key !== key) return <span className="public-sort-mark"> ⇅</span>
    return <span className="public-sort-mark public-sort-mark--on">{sort.dir === 'desc' ? ' ▼' : ' ▲'}</span>
  }
  const fmtAvg = v => v.toFixed(1)
  // Строку средних можно скрыть (владелец 2026-09-26); выбор помнится в этом браузере.
  const [showAvg, setShowAvg] = useState(() => {
    try { return localStorage.getItem('chestShowAvg') !== '0' } catch { return true }
  })
  function toggleAvg() {
    setShowAvg(v => {
      try { localStorage.setItem('chestShowAvg', v ? '0' : '1') } catch { /* приватный режим */ }
      return !v
    })
  }

  // Колонка «Ур. Героя» первой слева, скрываемая (владелец 2026-09-26); выбор помнится в браузере.
  const [showHero, setShowHero] = useState(() => {
    try { return localStorage.getItem('chestShowHero') !== '0' } catch { return true }
  })
  function toggleHero() {
    setShowHero(v => {
      try { localStorage.setItem('chestShowHero', v ? '0' : '1') } catch { /* приватный режим */ }
      return !v
    })
  }

  const tableWrapRef = useRef(null)
  const topScrollRef = useRef(null)
  const [tableScrollWidth, setTableScrollWidth] = useState(0)

  useEffect(() => {
    if (tableWrapRef.current) setTableScrollWidth(tableWrapRef.current.scrollWidth)
  }, [chestTypes, players])

  const [editRows, setEditRows] = useState({})
  const [saving, setSaving] = useState(null)
  const [savedRows, setSavedRows] = useState({})

  useEffect(() => {
    if (!editMode) return
    const init = {}
    players.forEach(p => {
      const { g, s, m } = parseTroop(p.troop_level)
      init[p.name] = { rank: p.rank || '', g, s, m, hero: p.hero_level ?? '' }
    })
    setEditRows(init)
  }, [editMode, players])

  async function handleSave(playerName) {
    const row = editRows[playerName] || {}
    const troop = row.g && row.s && row.m ? `G${row.g} S${row.s} M${row.m}` : null
    setSaving(playerName)
    try {
      const hero = Number(row.hero) || null   // пусто/0 → не задан
      await postPublicPlayerProfile(collectorSlug, playerName, row.rank || null, troop, hero)
      setSavedRows(prev => ({ ...prev, [playerName]: true }))
      setTimeout(() => setSavedRows(prev => { const n = { ...prev }; delete n[playerName]; return n }), 3000)
    } catch (e) {
      alert(tt.saveError + e.message)
    } finally {
      setSaving(null)
    }
  }

  function syncTableFromTopScroll() {
    if (tableWrapRef.current && topScrollRef.current) {
      tableWrapRef.current.scrollLeft = topScrollRef.current.scrollLeft
    }
  }
  // Пока таблицу листают — анимации имён на паузе (владелец 2026-09-28): десятки бликов и
  // переливов тормозили прокрутку на телефонах. Класс напрямую, без setState — без перерисовки.
  const scrollIdleRef = useRef(null)
  function pauseNameAnimations() {
    const el = tableWrapRef.current
    if (!el) return
    el.classList.add('is-scrolling')
    clearTimeout(scrollIdleRef.current)
    scrollIdleRef.current = setTimeout(() => el.classList.remove('is-scrolling'), 200)
  }
  useEffect(() => {
    window.addEventListener('scroll', pauseNameAnimations, { passive: true })
    return () => { window.removeEventListener('scroll', pauseNameAnimations); clearTimeout(scrollIdleRef.current) }
  }, [])

  function syncTopScrollFromTable() {
    pauseNameAnimations()
    if (tableWrapRef.current && topScrollRef.current) {
      topScrollRef.current.scrollLeft = tableWrapRef.current.scrollLeft
    }
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', margin: '0 0 6px' }}>
        {editButton}
        {/* Просто «Герой»: клик прячет/показывает колонку, подсветка = колонка видна (владелец 2026-09-26) */}
        <button type="button" className="public-avg-toggle public-hero-toggle" onClick={toggleHero}
          aria-pressed={showHero}
          style={{ marginRight: 8, ...(showHero ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : {}) }}>
          {tt.heroCol}
        </button>
        <button type="button" className="public-avg-toggle" onClick={toggleAvg}>
          {showAvg ? tt.hideAvg : tt.showAvg}
        </button>
      </div>
      <div
        className="public-table-top-scroll"
        ref={topScrollRef}
        onScroll={syncTableFromTopScroll}
      >
        <div style={{ width: tableScrollWidth, height: 1 }} />
      </div>

      <div className="public-table-wrap" ref={tableWrapRef} onScroll={syncTopScrollFromTable}>
        <table className={`public-table${showHero ? ' with-hero' : ''}`}>
          <thead>
            {showAvg && <tr className="public-avg-row">
              {showHero && <th></th>}
              <th></th>
              <th>{tt.avg}</th>
              {editMode && <th></th>}
              {editMode && <th></th>}
              {editMode && <th></th>}
              <th></th>
              {quotaCols.map(c => (
                <th key={c.key} className="public-epic-cell">{fmtAvg(columnAverage(players, c.get))}</th>
              ))}
              {chestTypes.map(t => (
                <th key={t} className={isEpicColumn(t) ? 'public-epic-cell' : ''}>
                  {fmtAvg(columnAverage(players, p => p.counts[t]))}
                </th>
              ))}
            </tr>}
            <tr className={showAvg ? 'public-head-row' : ''}>
              {showHero && (
                <th className="public-sortable" onClick={() => toggleSort('hero')}>{tt.heroCol}{sortMark('hero')}</th>
              )}
              <th>#</th>
              <th className="public-sortable" onClick={() => toggleSort('name')}>{tt.player}{sortMark('name')}</th>
              {editMode && <th>{tt.rank}</th>}
              {editMode && <th>{tt.troops}</th>}
              {editMode && <th></th>}
              <th className="public-sortable" onClick={() => toggleSort('points')}>{tt.points}{sortMark('points')}</th>
              {quotaCols.map(c => (
                <th key={c.key} className="public-epic-cell public-sortable" onClick={() => toggleSort(c.key)}>
                  <span translate="no" className="notranslate">{c.name}</span>
                  {c.target != null && !c.personal && <span style={{ opacity: 0.6 }}> /{c.target}</span>}
                  {sortMark(c.key)}
                </th>
              ))}
              {chestTypes.map(t => (
                <th key={t} className={`${isEpicColumn(t) ? 'public-epic-cell ' : ''}public-sortable`}
                    onClick={() => toggleSort(t)}>
                  <span translate="no" className="notranslate">{t}</span>{sortMark(t)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shownPlayers.map(p => {
              return (
                <tr key={p.name}>
                  {showHero && <td style={{ textAlign: 'center' }}>{p.hero_level ?? '—'}</td>}
                  <td>{pointsRank[p.name]}</td>
                  <td title={p.name} translate="no" className="notranslate">
                    {renderPlayerName(p, targets)}
                  </td>
                  {editMode && (
                    <td>
                      <select
                        value={editRows[p.name]?.rank || ''}
                        onChange={e => setEditRows(prev => ({
                          ...prev,
                          [p.name]: { ...prev[p.name], rank: e.target.value },
                        }))}
                        style={{ fontSize: 12, padding: '2px 4px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4 }}
                      >
                        {RANKS.map(r => <option key={r} value={r}>{r || '—'}</option>)}
                      </select>
                    </td>
                  )}
                  {editMode && (
                    <td>
                      <div style={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'nowrap' }}>
                        {['g', 's', 'm'].map((k, idx) => (
                          <select
                            key={k}
                            value={editRows[p.name]?.[k] || ''}
                            onChange={e => setEditRows(prev => ({
                              ...prev,
                              [p.name]: { ...prev[p.name], [k]: e.target.value },
                            }))}
                            style={{ fontSize: 11, padding: '2px 2px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4, width: 36 }}
                          >
                            <option value="">{'GSM'[idx]}</option>
                            {TIERS.slice(1).map(v => <option key={v} value={v}>{v}</option>)}
                          </select>
                        ))}
                        {(() => {
                          const { g, s, m } = editRows[p.name] || {}
                          if (!g || !s || !m) return null
                          const val = `G${g} S${s} M${m}`
                          return (
                            <span style={val === FULL_TROOP
                              ? { fontSize: 11, color: '#f9a825', fontWeight: 700, marginLeft: 2 }
                              : { fontSize: 11, color: '#6c7086', marginLeft: 2 }}>
                              {val}
                            </span>
                          )
                        })()}
                        {/* уровень Героя — задел для квоты EM */}
                        <input type="number" min={1} max={999} placeholder={tt.hero}
                          value={editRows[p.name]?.hero ?? ''}
                          onChange={e => setEditRows(prev => ({
                            ...prev,
                            [p.name]: { ...prev[p.name], hero: e.target.value.replace(/\D/g, '').slice(0, 3) },
                          }))}
                          style={{ width: 62, fontSize: 11, padding: '2px 4px', background: '#1e1e2e', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4, marginLeft: 4 }} />
                      </div>
                    </td>
                  )}
                  {editMode && (
                    <td>
                      <button
                        onClick={() => handleSave(p.name)}
                        disabled={saving === p.name}
                        style={{ fontSize: 12, padding: '2px 8px', cursor: 'pointer',
                          background: savedRows[p.name] ? '#1e3a1e' : '#313244',
                          color: savedRows[p.name] ? '#a6e3a1' : '#cdd6f4',
                          border: `1px solid ${savedRows[p.name] ? '#a6e3a1' : '#45475a'}`, borderRadius: 4 }}
                      >
                        {saving === p.name ? '...' : savedRows[p.name] ? '✓' : '💾'}
                      </button>
                    </td>
                  )}
                  <td className={`public-points-cell ${pointsHitTarget(p, targets) ? 'public-cell-hit-target' : ''}`}>
                    {fmtNum(p.points)}
                  </td>
                  {quotaCols.map(c => {
                    const v = c.get(p)
                    if (c.personal) {
                      // Личная цель EM (владелец 2026-09-26): прогресс-бар, % выполнения,
                      // цвет от красного (0%) к зелёному (100%+).
                      const tgt = c.targetOf(p)
                      const pct = tgt ? Math.round((v / tgt) * 100) : (v > 0 ? 100 : 0)
                      const fill = Math.min(pct, 100)
                      return (
                        <td key={c.key} className="public-epic-cell" style={{ minWidth: 120 }}
                            title={c.partialOf(p) ? '?' : ''}>
                          <div style={{ fontSize: 12, marginBottom: 3, whiteSpace: 'nowrap' }}>
                            {v}/{tgt ?? '—'}{c.partialOf(p) ? ' ?' : ''} · <b>{pct}%</b>
                          </div>
                          <div style={{ height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
                            {/* градиент на всю шкалу: видна его часть до текущего процента */}
                            <div style={{ width: `${fill}%`, height: '100%', borderRadius: 3, transition: 'width 0.4s',
                                          background: 'linear-gradient(90deg, #ef4444, #f59e0b, #22c55e)',
                                          backgroundSize: `${fill ? 10000 / fill : 100}% 100%` }} />
                          </div>
                        </td>
                      )
                    }
                    return (
                      <td key={c.key} className={[
                        'public-epic-cell',
                        c.target != null && v >= c.target && 'public-cell-hit-target',
                        v === 0 && 'public-cell-zero',
                      ].filter(Boolean).join(' ')}>
                        {v}
                      </td>
                    )
                  })}
                  {chestTypes.map(t => {
                    const value = p.counts[t] || 0
                    return (
                      <td key={t} className={[
                        isEpicColumn(t) && 'public-epic-cell',
                        value === 0 && 'public-cell-zero',
                      ].filter(Boolean).join(' ')}>
                        {value}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </>
  )
}
