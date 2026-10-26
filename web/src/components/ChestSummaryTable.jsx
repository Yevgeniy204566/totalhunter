import { useEffect, useMemo, useRef, useState } from 'react'
import { postPublicPlayerProfile } from '../api.js'
import { computeRow } from '../lib/emcQuota.js'
import {
  scoreOf, normAt, epicCountTotal, epicCryptsOf, emcCountAt, emcOthersTotal, countAt, typeTab, weightKey,
  EPIC_CRYPTS, EMC_FOUR, DEFAULT_HERO,
} from '../lib/heroQuota.js'

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
// Игрок без указанного Героя считается по «типичному» Герою 400 со знаком «?» (как у per_player).
const EMC_DEFAULT_HERO = 400
function emcModel(targets) {
  const q = (targets?.quotas || []).find(x => x.mode === 'emc_table')
  return q ? (q.emc || {}) : null
}
// Столбец сундука → индекс монстра в модели EMC (Hydra, Undead, Arachna/Arachne, Shadow City).
function monsterIndex(typeName) {
  const n = typeName.toLowerCase()
  if (n.includes('hydra')) return 0
  if (n.includes('undead')) return 1
  if (n.includes('arach')) return 2
  if (n.includes('shadow')) return 3
  return -1
}
function emcRowOf(player, model) {
  return computeRow(player.hero_level || EMC_DEFAULT_HERO, model)
}
export function quotaColumns(targets, epicLabel, typeMeta = null) {
  if (Array.isArray(targets?.quotas)) {
    // «Персонализированный учёт по Герою» — тумблер на каждой квоте (targets.personal.crypts/emc);
    // шкала очков — lib/heroQuota.js. У архива без chest_type_meta веса неизвестны: Crypts — как
    // обычная квота (по штукам), «Всего» не показываем.
    const pers = targets.personal || {}
    const scale = { norm: pers.norm, weights: pers.weights, ranges: pers.ranges, mix: pers.mix }
    const cols = targets.quotas.map(q => {
      // Crypts при персонализации — эпик-склепы суммой (обязательная норма клана): цель по Герою из шкалы,
      // фейдеры пульта её меняют (владелец 2026-10-21). Очки сезона остаются отдельным столбцом «Очки».
      const epicPersonal = q.slot === 1 && !!pers.crypts && !!typeMeta
      return {
        key: `quota:${q.slot}`, name: q.name, target: q.target,
        personal: epicPersonal || q.mode === 'per_player' || q.mode === 'emc_table',
        get: p => (epicPersonal ? epicCryptsOf(p.counts, typeMeta) : p.quotas?.[String(q.slot)] ?? 0),
        // личная цель игрока: Crypts — штуки эпик-склепов по Герою, EMC — штуки по таблице уровней и
        // рычагам клана (lib/emcQuota.js), per_player — старые архивы (считал сервер)
        targetOf: p => (epicPersonal ? epicCountTotal(p.hero_level || DEFAULT_HERO, scale)
          : q.mode === 'emc_table' ? emcRowOf(p, q.emc || {}).emc
            + (typeMeta ? emcOthersTotal(typeMeta, p.hero_level || DEFAULT_HERO, scale, q.emc) : 0)
          : q.mode === 'per_player' ? p.quota_targets?.[String(q.slot)] : q.target),
        partialOf: p => (epicPersonal || q.mode === 'emc_table' ? !p.hero_level
          : !!p.quota_targets_partial?.[String(q.slot)]),
      }
    })
    return cols
  }
  return [{ key: 'quota:legacy', name: epicLabel, target: targets?.chests ?? null,
            get: p => p.quota_chests ?? 0 }]
}
function isEpicColumn(typeName) {
  return typeName.includes('Epic')
}

// Среднее по участникам таблицы (входящие п.5): сумма столбца / число игроков в таблице,
// нули входят в расчёт; от сортировки не зависит.
// Полоса прогресса (владелец 2026-10-06): без градиента, как условное форматирование в Excel —
// подчёркивает данные, а не привлекает взгляд. Заливка = принесено/цель; цвет один, тёмный и
// приглушённый: почти пусто — тусклый красный, к ста процентам зеленеет; выполненная квота —
// полная тёмно-зелёная полоса. Без подсветки; цифры — обычным начертанием, не светлым цветом.
// Заливка всей ячейки (владелец 2026-10-19): палитра от фиолетового к неоново-зелёному
// (красный «вырви глаз»). Ноль — тёмный тихий фиолет, почти фон; к ста процентам светлеет и
// насыщается через синий и бирюзовый до неоново-зелёного.
function barColor(pct) {
  const k = Math.min(Math.max(pct, 0), 100) / 100
  // Заливка еле заметная (владелец 2026-10-21): чуть светлее фона строки, чтобы таблица читалась;
  // от тихого фиолетового к тихому зелёному, насыщенность и яркость минимальны
  const hue = Math.round(260 - k * 110)
  const sat = Math.round(18 + k * 10)
  const light = Math.round(12 + k * 4)
  return `hsl(${hue} ${sat}% ${light}%)`
}
// Ячейка = целый прогресс-бар (владелец 2026-10-20): заливка слева направо на pct% ширины всей
// ячейки, остальное — тёмный фон; цвет заливки по той же палитре, что и раньше.
function barBackground(pct) {
  const w = Math.min(Math.max(pct, 0), 100)
  return `linear-gradient(to right, ${barColor(pct)} ${w}%, rgba(255,255,255,0.025) ${w}%)`
}
// Уровень Героя на щите: заливка слева направо, свой градиент на каждую сотню (владелец 2026-10-24).
const HERO_BANDS = [
  { max: 300, from: '#C9A227', to: '#5C3A17', dark: '#3A220B', light: '#E0C25A' },
  { max: 400, from: '#7FA82E', to: '#174D2A', dark: '#0A2C14', light: '#A6CB5C' },
  { max: 500, from: '#4FA3D6', to: '#172A66', dark: '#0A1640', light: '#82BFE6' },
  { max: 600, from: '#B3186E', to: '#2A0B4F', dark: '#16032B', light: '#D45FA2' },
]
function heroBand(level) {
  if (!level || level < 100) return -1
  const i = HERO_BANDS.findIndex(b => level <= b.max)
  return i === -1 ? HERO_BANDS.length - 1 : i
}
// Градиенты объявлены один раз на таблицу; щиты ссылаются на них по id.
function HeroShieldDefs() {
  return (
    <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true" focusable="false">
      <defs>
        {HERO_BANDS.map((b, i) => (
          <linearGradient key={i} id={`hero-shield-${i}`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor={b.from} /><stop offset="1" stopColor={b.to} />
          </linearGradient>
        ))}
        <linearGradient id="hero-shield-none" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#4B5563" /><stop offset="1" stopColor="#1F2937" />
        </linearGradient>
      </defs>
    </svg>
  )
}
function HeroShield({ level }) {
  const band = heroBand(level)
  // рамка щита — светлее заливки в её тоне; контур цифр — тёмный тон того же цвета (владелец 2026-10-24)
  const dark = band === -1 ? '#1F2937' : HERO_BANDS[band].dark
  const light = band === -1 ? '#6B7280' : HERO_BANDS[band].light
  const fill = band === -1 ? 'url(#hero-shield-none)' : `url(#hero-shield-${band})`
  return (
    <svg className="hero-shield" viewBox="0 0 40 46" role="img" aria-label={level ? String(level) : '—'}>
      <path d="M20 1.5 L37.5 7.5 V23 C37.5 33 29.5 40 20 44.5 C10.5 40 2.5 33 2.5 23 V7.5 Z"
            fill={fill} stroke={light} strokeWidth="2" strokeLinejoin="round" />
      <path d="M20 6 L33.5 10.5 V23 C33.5 31 27 36.8 20 40.4 C13 36.8 6.5 31 6.5 23 V10.5 Z"
            fill="none" stroke={dark} strokeOpacity="0.45" strokeWidth="1" />
      <text x="20" y="27" textAnchor="middle" fontSize={level >= 100 ? 14 : 16} fontWeight="800"
            fill="#fff" stroke={dark} strokeWidth="2" strokeLinejoin="round" paintOrder="stroke"
            style={{ fontFamily: 'inherit' }}>{level || '—'}</text>
    </svg>
  )
}

function ProgressCell({ value, target, partial, hint = '', showPct = false, className = 'public-epic-cell', minWidth = 96 }) {
  const pct = target ? Math.round((value / target) * 100) : 100
  return (
    <td className={className} title={partial ? hint : ''}
        style={{ minWidth, textAlign: 'center', background: barBackground(pct), transition: 'background 0.4s' }}>
      <div style={{ fontSize: 14, whiteSpace: 'nowrap', fontWeight: 400, color: 'var(--on-surface)' }}>
        {fmtNum(value)}/{target == null ? '—' : fmtNum(target)}{partial ? <span style={{ opacity: 0.6 }}>*</span> : ''}
      </div>
      {showPct && (
        <div style={{ fontSize: 12, marginTop: 2, fontWeight: 400, letterSpacing: '0.3px', color: 'var(--on-surface2)' }}>
          {pct}%
        </div>
      )}
    </td>
  )
}

// Три главных столбца (владелец 2026-10-21, макет «Лидерборд»): широкая ячейка «факт / цель», под ней тонкая
// полоса и процент справа. Цвет заливки — прежний путь от фиолетового к зелёному по проценту, на 100% и выше
// — #287A50 (HSL 147 51% 32%). Ширина заливки обрезается на 100%, сам процент показывается как есть.
const BAR_DONE = '#287A50'
function barFillColor(pct) {
  const k = Math.min(Math.max(pct, 0), 100) / 100
  if (k >= 1) return BAR_DONE
  return `hsl(${Math.round(260 - k * 113)} ${Math.round(45 + k * 6)}% ${Math.round(40 - k * 8)}%)`
}
function MainIcon({ kind }) {
  const common = { width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2,
    strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true, className: 'public-main-icon' }
  if (kind === 'star') return <svg {...common} fill="currentColor"><path d="M12 2l3 6.9 7.5.7-5.7 5 1.7 7.4L12 18l-6.5 4 1.7-7.4-5.7-5 7.5-.7z" /></svg>
  // Цветные значки (владелец 2026-10-24): сундук с драгоценностями нарисован здесь, дракончик — Twemoji 🐲
  // (CC-BY 4.0, https://github.com/jdecked/twemoji), файл public/icons/dragon.svg
  if (kind === 'chest') return (
    <svg className="public-main-icon public-main-chest" viewBox="0 0 32 32" aria-hidden="true"
         strokeLinejoin="round" strokeLinecap="round" strokeWidth="1.1" stroke="#3B220C">
      <path d="M5.5 15 L7.5 5 H24.5 L26.5 15 Z" fill="#7A4A1E" />
      <ellipse cx="16" cy="15" rx="11.5" ry="3" fill="#FFD54A" />
      <polygon points="9,13 12,8.5 15,13 12,16" fill="#E0245E" />
      <polygon points="15,12 18,6.5 21,12 18,15.5" fill="#2EA8FF" />
      <polygon points="20,13.5 22.5,10 25,13.5 22.5,16.5" fill="#2EC46A" />
      <circle cx="7.5" cy="14.5" r="2" fill="#FFE27A" />
      <circle cx="26" cy="14.8" r="1.8" fill="#FFE27A" />
      <path d="M4 15.5 H28 V27 a2 2 0 0 1 -2 2 H6 a2 2 0 0 1 -2 -2 Z" fill="#A0652D" />
      <rect x="4" y="15.5" width="24" height="3.6" fill="#F2C94C" />
      <rect x="7.5" y="19" width="2.6" height="10" fill="#F2C94C" />
      <rect x="21.9" y="19" width="2.6" height="10" fill="#F2C94C" />
      <rect x="13" y="17.5" width="6" height="7" rx="1.2" fill="#FFE27A" />
      <circle cx="16" cy="20.6" r="1.1" fill="#3B220C" stroke="none" />
      <rect x="15.4" y="21" width="1.2" height="2.6" fill="#3B220C" stroke="none" />
    </svg>
  )
  if (kind === 'dragon') return <img className="public-main-icon public-main-dragon" src="/icons/dragon.svg" alt="" aria-hidden="true" />
  return <svg {...common}><path d="M3 21h18M5 21V10M19 21V10M9 21V10M15 21V10M2 10l10-6 10 6z" /></svg>
}
function BarCell({ value, target, partial, hint = '' }) {
  const pct = target ? Math.round((value / target) * 100) : 0
  const w = Math.min(Math.max(pct, 0), 100)
  return (
    <td className="public-bar-cell" title={partial ? hint : ''}>
      <div className="public-bar-top">
        <span className="public-bar-val">{fmtNum(value)}</span>
        <span className="public-bar-tgt"> / {target == null ? '—' : fmtNum(target)}{partial ? '*' : ''}</span>
      </div>
      <div className="public-bar-row">
        <div className="public-bar-track"><div className="public-bar-fill" style={{ width: `${w}%`, background: barFillColor(pct) }} /></div>
        <span className="public-bar-pct">{target ? `${pct}%` : ''}</span>
      </div>
    </td>
  )
}

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
  // Три главных столбца (владелец 2026-10-21): две сортировки — «успеваемость» (sort.mode 'pct': факт / цель
  // игрока) и «абсолютная» (sort.mode 'abs': максимум по числу). Без mode — прежнее поведение.
  const main = sort.mode && (sort.key === 'points' || qcol)
  const get = sort.key === 'points' ? (p => p.points) : qcol?.get
  const ratio = p => {
    const t = sort.key === 'points' ? p.pointsTarget : qcol.targetOf?.(p)
    return t ? get(p) / t : 0
  }
  const val = main ? (sort.mode === 'abs' ? get : ratio) : value
  const dir = sort.dir === 'asc' ? 1 : -1
  return [...players].sort((a, b) => {
    const va = val(a), vb = val(b)
    if (va < vb) return -dir
    if (va > vb) return dir
    // при равенстве — по абсолютным очкам, потом по проценту нормы (владелец 2026-10-24)
    return b.points - a.points || (b.pointsPct ?? 0) - (a.pointsPct ?? 0) || a.name.localeCompare(b.name)
  })
}

const TABLE_TXT = {
  ru: { total: 'Всего', player: 'Игрок', points: 'Очки', epic: 'Epic-склепы', avg: 'Среднее', rank: 'Звание', troops: 'Состав', hero: 'Герой',
        hideAvg: 'Скрыть средние', showAvg: 'Показать средние', saveError: 'Ошибка сохранения: ',
        sortPct: 'Сортировка по успеваемости: выполнение нормы своего Героя, %', sortAbs: 'Сортировка по абсолютному значению: максимум в числах', abs: 'абс.', pctShort: '% нормы', heroCol: 'Герой', partialHint: 'Уровень Героя не указан — цель посчитана по Герою 400' },
  en: { total: 'Total', player: 'Player', points: 'Points', epic: 'Epic Crypts', avg: 'Average', rank: 'Rank', troops: 'Troops', hero: 'Hero',
        hideAvg: 'Hide averages', showAvg: 'Show averages', saveError: 'Save error: ',
        sortPct: 'Sort by performance: % of the own Hero norm', sortAbs: 'Sort by absolute value: highest numbers', abs: 'abs.', pctShort: '% of norm', heroCol: 'Hero', partialHint: 'Hero level not set — target is calculated for Hero 400' },
}

// Узкий экран (телефон/планшет): закреплённые колонки выносятся из прокручиваемой области в свой блок слева.
function useNarrow(query = '(max-width: 900px)') {
  const [narrow, setNarrow] = useState(() => typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia(query).matches)
  useEffect(() => {
    if (!window.matchMedia) return undefined
    const mq = window.matchMedia(query)
    const on = () => setNarrow(mq.matches)
    on()
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [query])
  return narrow
}

export default function ChestSummaryTable({ chestTypes, chestTypeMeta = null, players: rawPlayers, targets, editMode = false, collectorSlug, lang = 'en', editButton = null }) {
  const tt = TABLE_TXT[lang] || TABLE_TXT.en
  const quotaCols = useMemo(() => quotaColumns(targets, tt.epic, chestTypeMeta), [targets, tt.epic, chestTypeMeta])
  const emc = useMemo(() => emcModel(targets), [targets])
  const typeMeta = chestTypeMeta
  const pers = targets?.personal || {}
  const personalCrypts = !!pers.crypts
  const personalEmc = !!pers.emc
  const scale = useMemo(() => ({ norm: pers.norm, weights: pers.weights, ranges: pers.ranges, mix: pers.mix }), [pers])
  const emcLevers = (targets?.quotas || []).find(q => q.slot === 2)?.emc
  // Столбец «Очки» — единая сумма всех сундуков в учёте (склепы + EMC + прочие). Когда включена
  // персонализация (владелец 2026-10-21), считаем её по шкале очков для Героя игрока и сравниваем с
  // нормой по Герою; иначе — прежние очки клана и общая цель сезона.
  const pointsPersonal = (personalCrypts || personalEmc) && !!typeMeta
  const players = useMemo(() => {
    // без личных норм порядок и место «#» — тоже строго по очкам (сервер так и отдаёт, но старые архивы сезонов могли храниться иначе):
    // лидер всегда с самым высоким оформлением имени (владелец 2026-10-24)
    if (!pointsPersonal) return [...rawPlayers].sort((a, b) => b.points - a.points || a.name.localeCompare(b.name))
    return rawPlayers.map(p => ({
      ...p, clanPoints: p.points,
      points: scoreOf(p.counts, typeMeta, p.hero_level, scale).score,
      pointsTarget: normAt(p.hero_level || DEFAULT_HERO, scale),
    })).map(p => ({ ...p, pointsPct: p.pointsTarget ? p.points / p.pointsTarget : 0 }))
      // порядок и место «#» — по АБСОЛЮТНЫМ очкам (владелец 2026-10-24): слабый Герой, перекрывший свою малую норму, не должен
      // обгонять сильного — клану нужны богатые сундуки. «Успеваемость» (очки / норма) — отдельная сортировка по клику на заголовок.
      .sort((a, b) => b.points - a.points || b.pointsPct - a.pointsPct || a.name.localeCompare(b.name))
  }, [rawPlayers, pointsPersonal, typeMeta, scale])
  // Цвет, размер и знамя имени идут от АБСОЛЮТНЫХ очков игрока (владелец 2026-10-24): очки ÷ одна общая цель сезона клана.
  // Раньше при личных нормах делили на норму Героя игрока, и слабый Герой, перекрывший малую норму, выглядел круче сильного
  // с большим числом очков. Нет общей цели сезона — берём норму стандартного Героя 400 (одна на всех).
  const nameTargets = useMemo(() => (pointsPersonal
    ? { ...targets, points: targets?.points || normAt(DEFAULT_HERO, scale) }
    : targets), [pointsPersonal, targets, scale])
  // Три главных столбца = прежние «Очки», Crypts-квота и EMC в прежнем порядке (владелец 2026-10-21);
  // меняется только вид ячейки. Столбцы типов сундуков идут после них.
  const mainCols = useMemo(() => {
    if (!pointsPersonal) return null
    return [
      { key: 'points', name: tt.points, icon: 'star', get: p => p.points, targetOf: p => p.pointsTarget, partialOf: p => !p.hero_level },
      ...quotaCols.map(c => ({ ...c, icon: c.key === 'quota:2' ? 'dragon' : 'chest' })),
    ]
  }, [pointsPersonal, quotaCols, tt])
  // По умолчанию — порядок сервера (по очкам). «#» всегда место по очкам, не по текущей сортировке.
  const [sort, setSort] = useState(() => (pointsPersonal ? { key: 'points', mode: 'abs', dir: 'desc' } : null))
  const pointsRank = useMemo(() => {
    const m = {}
    players.forEach((p, i) => { m[p.name] = i + 1 })
    return m
  }, [players])
  const shownPlayers = useMemo(
    () => (sort ? sortPlayers(players, sort, chestTypes, quotaCols) : players),
    [players, sort, chestTypes, quotaCols],
  )
  function toggleSort(key, mode) {
    setSort(prev => {
      const firstDir = key === 'name' ? 'asc' : 'desc'
      if (!prev || prev.key !== key || prev.mode !== mode) return { key, mode, dir: firstDir }
      return { key, mode, dir: prev.dir === 'desc' ? 'asc' : 'desc' }
    })
  }
  function sortMark(key, mode) {
    if (!sort || sort.key !== key || sort.mode !== mode) return <span className="public-sort-mark"> ⇅</span>
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

  const narrow = useNarrow()
  const split = narrow && !editMode
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

  const renderHead = part => (
          <thead>
            {showAvg && <tr className="public-avg-row">
              {part !== 'data' && <><th></th><th></th><th>{tt.avg}</th></>}
              {editMode && <th></th>}
              {editMode && <th></th>}
              {editMode && <th></th>}
              {part !== 'fixed' && (<>
              {mainCols
                ? mainCols.map(c => <th key={c.key} className="public-main-th">{fmtAvg(columnAverage(players, c.get))}</th>)
                : <>
                  <th></th>
                  {quotaCols.map(c => (
                    <th key={c.key} className="public-epic-cell">{fmtAvg(columnAverage(players, c.get))}</th>
                  ))}
                </>}
              {chestTypes.map(t => (
                <th key={t} className={isEpicColumn(t) ? 'public-epic-cell' : ''}>
                  {fmtAvg(columnAverage(players, p => p.counts[t]))}
                </th>
              ))}
              </>)}
            </tr>}
            <tr className={showAvg ? 'public-head-row' : ''}>
              {part !== 'data' && (<>
              <th className="public-num-cell">#</th>
              <th className="public-sortable public-hero-cell" onClick={() => toggleSort('hero')}>{tt.heroCol}{sortMark('hero')}</th>
              <th className="public-sortable public-name-cell" onClick={() => toggleSort('name')}>{tt.player}{sortMark('name')}</th>
              </>)}
              {editMode && <th>{tt.rank}</th>}
              {editMode && <th>{tt.troops}</th>}
              {editMode && <th></th>}
              {part !== 'fixed' && (<>
              {mainCols
                ? mainCols.map(c => (
                  <th key={c.key} className="public-main-th">
                    <div className="public-main-head">
                      <span className="public-sortable" title={tt.sortAbs} onClick={() => toggleSort(c.key, 'abs')}>
                        <MainIcon kind={c.icon} />
                        <span translate="no" className="notranslate">{c.name}</span>{sortMark(c.key, 'abs')}
                      </span>
                      <span className="public-sortable public-main-abs" title={tt.sortPct} onClick={() => toggleSort(c.key, 'pct')}>
                        {tt.pctShort}{sortMark(c.key, 'pct')}
                      </span>
                    </div>
                  </th>
                ))
                : <>
                  <th className="public-sortable" onClick={() => toggleSort('points')}>{tt.points}{sortMark('points')}</th>
                  {quotaCols.map(c => (
                    <th key={c.key} className="public-epic-cell public-sortable" onClick={() => toggleSort(c.key)}>
                      <span translate="no" className="notranslate">{c.name}</span>
                      {c.target != null && !c.personal && <span style={{ opacity: 0.6 }}> /{fmtNum(c.target)}</span>}
                      {sortMark(c.key)}
                    </th>
                  ))}
                </>}
              {chestTypes.map(t => (
                <th key={t} className={`${isEpicColumn(t) ? 'public-epic-cell ' : ''}public-sortable`}
                    onClick={() => toggleSort(t)}>
                  <span translate="no" className="notranslate">{t}</span>{sortMark(t)}
                </th>
              ))}
              </>)}
            </tr>
          </thead>
  )
  const renderRow = (p, part) => (
                <tr key={p.name}>
                  {part !== 'data' && (<>
                  <td className="public-num-cell">{pointsRank[p.name]}</td>
                  <td className="public-hero-cell"><HeroShield level={p.hero_level} /></td>
                  <td title={p.name} translate="no" className="notranslate public-name-cell">
                    {renderPlayerName(p, nameTargets)}
                  </td>
                  </>)}
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
                  {part !== 'fixed' && (<>
                  {mainCols
                    ? mainCols.map(c => (
                      <BarCell key={c.key} value={c.get(p)} target={c.targetOf(p)} partial={c.partialOf(p)} hint={tt.partialHint} />
                    ))
                    : <>
                      {pointsPersonal
                        ? <ProgressCell value={p.points} target={p.pointsTarget} partial={!p.hero_level} hint={tt.partialHint}
                                        showPct minWidth={120} className="public-points-cell" />
                        : (
                          <td className={`public-points-cell ${pointsHitTarget(p, targets) ? 'public-cell-hit-target' : ''}`}>
                            {fmtNum(p.points)}
                          </td>
                        )}
                      {quotaCols.map(c => {
                        const v = c.get(p)
                        if (c.personal) {
                          return <ProgressCell key={c.key} value={v} target={c.targetOf(p)} partial={c.partialOf(p)} hint={tt.partialHint}
                                               showPct minWidth={120} />
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
                    </>}
                  {chestTypes.map(t => {
                    const value = p.counts[t] || 0
                    const meta = typeMeta?.[t]
                    // Типы с целью по штукам из пульта (те же правила, что во вкладке «Пульт»): склепы вне эпиков —
                    // если число задано вручную; эпические монстры вне четырёх и свои события слота EMC
                    // (эпик-склепы идут итогом в колонке Crypts, четыре монстра — ниже по своей таблице)
                    if (meta) {
                      const kind = typeTab(meta.id, meta.slot)
                      const hero = p.hero_level || DEFAULT_HERO
                      let need = 0
                      if (personalCrypts && kind === 'crypts' && !EPIC_CRYPTS.includes(weightKey(meta.id))) {
                        need = countAt(meta.id, hero, scale)
                      } else if (personalEmc && kind === 'emc' && !(meta.id in EMC_FOUR)) {
                        need = emcCountAt(meta.id, hero, scale, emcLevers)
                      }
                      if (need > 0) {
                        return <ProgressCell key={t} value={value} partial={!p.hero_level} hint={tt.partialHint} target={need} />
                      }
                    }
                    const mi = emc ? monsterIndex(t) : -1
                    if (mi >= 0) {
                      const row = emcRowOf(p, emc)
                      return <ProgressCell key={t} value={value} partial={!p.hero_level} hint={tt.partialHint}
                                           target={[row.finalH, row.finalU, row.finalA, row.finalS][mi]} />
                    }
                    return (
                      <td key={t} className={[
                        isEpicColumn(t) && 'public-epic-cell',
                        value === 0 && 'public-cell-zero',
                      ].filter(Boolean).join(' ')}>
                        {value}
                      </td>
                    )
                  })}
                  </>)}
                </tr>
  )

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', margin: '0 0 6px' }}>
        {editButton}
        <button type="button" className="public-avg-toggle" onClick={toggleAvg}>
          {showAvg ? tt.hideAvg : tt.showAvg}
        </button>
      </div>
      <HeroShieldDefs />
      <div
        className="public-table-top-scroll"
        ref={topScrollRef}
        onScroll={syncTableFromTopScroll}
      >
        <div style={{ width: tableScrollWidth, height: 1 }} />
      </div>

      <div className="public-table-wrap" ref={tableWrapRef} onScroll={syncTopScrollFromTable}>
        {split ? (
          <div className="public-split">
            <div className="public-split-left">
              <table className="public-table public-table--fixed">
                {renderHead('fixed')}
                <tbody>{shownPlayers.map(p => renderRow(p, 'fixed'))}</tbody>
              </table>
            </div>
            <table className="public-table public-table--data">
              {renderHead('data')}
              <tbody>{shownPlayers.map(p => renderRow(p, 'data'))}</tbody>
            </table>
          </div>
        ) : (
          <table className="public-table">
            {renderHead('all')}
            <tbody>{shownPlayers.map(p => renderRow(p, 'all'))}</tbody>
          </table>
        )}
      </div>
    </>
  )
}
