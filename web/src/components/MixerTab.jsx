import { useEffect, useMemo, useRef, useState } from 'react'
import {
  DEFAULT_SETTINGS as EMC_DEFAULTS, computeRow, clampMultiplier, MULTIPLIER_MIN, MULTIPLIER_MAX,
} from '../lib/emcQuota.js'
import TierPresetEditor from './TierPresetEditor.jsx'
import CurveEditor from './CurveEditor.jsx'
import { pointsLines, countLines, writeBands } from '../lib/curveLines.js'
import { posToK, kToPos, solveK, presetMixW } from '../lib/mixer.js'
import {
  DEFAULT_SETTINGS as SCALE_DEFAULTS, CRYPT_TYPES, EMC_TYPES, EMC_FOUR, EPIC_CRYPTS,
  weightKey, weightAt, fallbackWeight, countAt, emcCountAt, emcOthersTotal, typeTab, epicCountTotal,
} from '../lib/heroQuota.js'

// «Пульт» (владелец 2026-10-20/21): единый центр персональных настроек. Вкладки Crypts / EMC, колонка на
// тип сундука из «Учёта» клана, фейдер: середина = рассчитанное значение (×1), вверх — больше, вниз —
// меньше; зелёная точка — вкл/выкл тип. Слева выбираются ступени Героя (можно несколько): правка
// применяется ко всем отмеченным; «Все уровни» — множитель пропорционально на каждую ступень.
// Переключатель «Очки/Количество» меняет, что двигают фейдеры. Фейдер логарифмический: ×0.1 … ×1 … ×3.

const TXT = {
  ru: {
    points: 'Очки', count: 'Количество',
    allLevels: 'Все уровни', hero: 'Герой',
    consoleCrypts: 'Склепы и цитадели', consoleEmc: 'Epic Monster Chests',
    addChest: '+ Добавить сундук', addPick: 'Выберите сундук', addOk: 'Добавить', addCancel: 'Отмена',
    chestAdded: 'Сундук добавлен в учёт. Чтобы сохранить, нажмите «Сохранить настройки».',
    gCryptsTip: 'Главный фейдер склепов и цитаделей: двигает очки всех сундуков этого пульта сразу. Число — сумма очков за по одному сундуку каждого типа',
    gEmcTip: 'Главный фейдер EMC: двигает очки всех эпических монстров сразу. Число — сумма очков за по одному монстру каждого типа',
    fineTip: 'Точная подстройка: −/+ 1% от текущего значения; удерживайте кнопку — значение идёт непрерывно',
    resetMaster: 'Сброс', resetMasterTip: 'Вернуть все фейдеры этого пульта в исходное положение (по центру) в выбранном режиме. Выключенные типы остаются',
    mCrypts: 'Склепы', mCryptsTip: 'Норма эпик-склепов (все типы склепов вместе): число штук на игрока',
    mEmc: 'EMC', mEmcTip: 'Норма EMC (все эпические монстры вместе, включая Chimera): число штук на игрока',
    enable: 'Персонализированный учёт по уровню Героя',
    off: 'Выключено: нормы игроков фиксированные, из настроек сезона. Включите переключатель выше, чтобы настраивать нормы по уровням Героя.',
    sample: 'Пример для Героя',
    reset: 'Двойной щелчок по ползунку — вернуть расчётное значение',
    mute: 'Зелёный — участвует в подсчёте, красный — не участвует (выключен или значение 0). Нажмите, чтобы включить или выключить',
    abs: 'Значение: сотрите и впишите своё число (0 — выключить тип)',
    manual: 'В нормах клана штук для этого типа нет. По умолчанию 0 — ручка по центру; двигайте её вверх (до 200) или впишите число вручную; двойной щелчок — сбросить в 0',
    calc: 'расчёт',
    countNote: 'Эпик-склепы: общая норма клана делится поровну между включёнными типами эпик-склепов. Для Rare, Common и Citadel штук в норме нет — впишите число сами, если нужно.',
    save: '💾 Сохранить настройки', saved: 'Применяет настройки пультов к сезону. Игроки видят результат на публичной странице.',
    dirtyOn: '● Есть несохранённые изменения', dirtyOff: '✓ Всё сохранено',
    editing: 'Правим: {what}',
    scopeAllTitle: 'Вы правите: «Все уровни»',
    scopeAllText: 'Число (очки или количество) вы задаёте для уровня Героя из поля «Пример для Героя» ({h}). Остальные уровни меняются в той же пропорции. Пример: на Герое 400 сундук даёт 135 очков, на Герое 300 — 150. Вы поставили 160 на Герое 400 — на Герое 300 станет 180.',
    scopeDivTitle: 'Вы правите только: {what}',
    scopeDivText: 'Число (очки или количество) действует только для выбранных уровней Героя. Остальные уровни не меняются, на границе будет «ступенька»: 135 на Героях 390–399, 160 на 400–409, снова 135 на 410–419.',
    mixed: 'у выбранных уровней значения разные — ползунок задаст одинаковое',
    noTypes: 'В «Учёте» клана пока нет сундуков этой группы — показаны типы шкалы по умолчанию.',
    presets: 'Наборы настроек очков', presetName: 'Название', slot: 'Слот', empty: 'пусто', saveSlot: 'Сохранить набор', load: 'Загрузить набор',
    presetHint: 'Набор — запись всех настроек пультов: ползунки, числа и ваши правки пресетов T5–T9. Три слота — три ваших варианта. «Сохранить набор» записывает настройки в слот и сразу применяет их к сезону. «Загрузить набор» возвращает записанные настройки на страницу — затем нажмите «Сохранить настройки». Общие пресеты T5–T9 не меняются.',
    loaded: 'Набор загружен. Чтобы применить его к сезону, нажмите «Сохранить настройки».',
    savedPreset: 'Набор сохранён.',
    help: 'Как работают личные нормы игроков',
    helpText: [
      'Вкладка «Общие нормы клана» — одни нормы на весь клан: названия, очки за сундук, «Учёт». Она питает колонку «Очки» в таблице игроков.',
      'Эта вкладка включается переключателем «Персонализированный учёт по уровню Героя» на квоте Crypts и/или EMC. Тогда нормы игрока зависят от его Героя: чем ниже Герой, тем больше очков за сундук и меньше норма. Шкала построена по данным реальных кланов, уровни Героя 100–600, сезон 14 дней.',
      'Здесь — сундуки из «Учёта» клана. Пульт EMC — со статусом «Квота 2», пульт Crypts — «Квота 1» и «В учёте». Для сундуков вне шкалы за основу берутся очки из «Общих норм клана».',
      'У каждого сундука — ползунок и число под ним, это одно и то же. Двигаете ползунок — число меняется; вписываете число — ползунок встаёт сам. Середина — расчётное значение. 0 или зелёная точка выключают сундук.',
      '«Очки» — сколько очков даёт сундук. «Количество» — сколько штук ждут от игрока.',
      'Править можно двумя способами. «Все уровни»: число для «Примера для Героя», остальные уровни меняются пропорционально. Выбранные уровни Героя: число действует только для них.',
      'Наборы настроек очков — 3 слота для ваших вариантов настроек.',
    ],
  },
  en: {
    points: 'Points', count: 'Count',
    allLevels: 'All levels', hero: 'Hero',
    consoleCrypts: 'Crypts and citadels', consoleEmc: 'Epic Monster Chests',
    addChest: '+ Add chest', addPick: 'Pick a chest', addOk: 'Add', addCancel: 'Cancel',
    chestAdded: "Chest added to the accounting. Press 'Save settings' to keep it.",
    gCryptsTip: 'Crypts and citadels master fader: moves the points of every chest of this console at once. The number is the sum of points for one chest of each type',
    gEmcTip: 'EMC master fader: moves the points of every epic monster at once. The number is the sum of points for one monster of each type',
    fineTip: 'Fine tuning: −/+ 1% of the current multiplier; hold a button to keep going',
    resetMaster: 'Reset', resetMasterTip: 'Return every fader of this console to the start position (centre) in the chosen mode. Muted types stay',
    mCrypts: 'Crypts', mCryptsTip: 'Epic crypts norm (all crypt types together): multiplier and pieces per player',
    mEmc: 'EMC', mEmcTip: 'EMC norm (all epic monsters together, including Chimera): multiplier and pieces per player',
    enable: 'Personalized accounting by Hero level',
    off: 'Off: player norms are fixed from the season settings. Turn the switch above on to set norms by Hero level.',
    sample: 'Example for Hero',
    reset: 'Double-click a slider to return the calculated value',
    mute: 'Green — counted, red — not counted (off or value 0). Click to turn on or off',
    abs: 'Value: erase and type your own number (0 turns the type off)',
    manual: 'The clan norms give no count for this type. The default is 0 — the handle sits in the centre; move it up (to 200) or type a number; double-click resets to 0',
    calc: 'calc.',
    countNote: 'Epic crypts: the clan total norm is split equally between the enabled epic crypt types. Rare, Common and Citadel have no counts in the norm — type a number yourself if needed.',
    save: '💾 Save settings', saved: 'Applies the consoles\' settings to the season. Players see the result on the public page.',
    dirtyOn: '● Unsaved changes', dirtyOff: '✓ All saved',
    editing: 'Editing: {what}',
    scopeAllTitle: 'You are editing: All levels',
    scopeAllText: 'You set the number (points or count) for the Hero level from the "Example for Hero" field ({h}). Other levels change in the same proportion. Example: a chest gives 135 points at Hero 400 and 150 at Hero 300. You set 160 at Hero 400 — at Hero 300 it becomes 180.',
    scopeDivTitle: 'You are editing only: {what}',
    scopeDivText: 'The number (points or count) applies only to the chosen Hero levels. Other levels do not change, so there is a step at the border: 135 at Heroes 390–399, 160 at 400–409, 135 again at 410–419.',
    mixed: 'selected levels have different values — the slider will set them equal',
    noTypes: "The clan's accounting has no chests of this group yet — showing the default scale types.",
    presets: 'Point settings sets', presetName: 'Name', slot: 'Slot', empty: 'empty', saveSlot: 'Save set', load: 'Load set',
    presetHint: "A set is a record of all settings of the consoles: sliders, numbers and your edits of the T5–T9 presets. Three slots hold three variants of yours. 'Save set' writes the settings to the slot and applies them to the season right away. 'Load set' brings the recorded settings back to the page — then press 'Save settings'. The shared T5–T9 presets never change.",
    loaded: "Set loaded. To apply it to the season, press 'Save settings'.",
    savedPreset: 'Preset saved.',
    help: 'How personal player norms work',
    helpText: [
      "The 'Clan-wide norms' tab holds one set of norms for the whole clan: names, points per chest, accounting. It feeds the 'Points' column of the player table.",
      "This tab is turned on by the 'Personalized accounting by Hero level' switch on the Crypts and/or EMC quota. A player's norms then depend on their Hero: the lower the Hero, the more points per chest and the smaller the norm. The scale is built from real clan data, Hero levels 100–600, a season is 14 days.",
      "This tab shows the chests from the clan's accounting. The EMC console holds 'Quota 2' chests, the Crypts console holds 'Quota 1' and 'Counted'. For chests outside the scale the base is the points from 'Clan-wide norms'.",
      "Every chest has a slider and a number below it — they are the same thing. Move the slider and the number changes; type a number and the slider follows. The middle is the calculated value. 0 or the green dot turns the chest off.",
      "'Points' is how many points a chest gives. 'Count' is how many pieces are expected from a player.",
      "There are two ways to edit. 'All levels': a number for the chosen 'Example for Hero', other levels change proportionally. Chosen Hero levels: the number applies only to them.",
      "Sets of point settings — 3 slots for your variants of settings.",
    ],
  },
}

const MONSTERS = [['hydra', 'Hydra', 'Epic Fire Hydra'], ['undead', 'Undead', 'Epic Undead'],
  ['arachna', 'Arachna', 'Epic Arachne'], ['shadow', 'Shadow City', 'Epic Shadow City']]
const GROUPS = [100, 200, 300, 400, 500].map(g => ({
  g, bands: Array.from({ length: g === 500 ? 11 : 10 }, (_, i) => g + i * 10),
}))
const MANUAL_MAX = 200
const fmt = n => Number(n).toLocaleString('ru-RU')
const bandLabel = h => { const n = Number(h); return n >= 600 ? `${n}` : `${n}–${n + 9}` }

// Название колонки — полностью, как во вкладке «Сундуки»: «Своё название», иначе «Официальный сундук».
const titleOf = x => x.label

// Порядок колонок по группам (владелец 2026-10-21): эпические, редкие, цитадели, обычные, прочие;
// внутри группы — уровень по убыванию. Эпические монстры: четыре с историей, затем остальные по названию.
const GROUP_RANK = id => (/^Epic Crypt/.test(id) ? 0 : /^Rare Crypt/.test(id) ? 1 : /Citadel/.test(id) ? 2
  : /^Common Crypt/.test(id) ? 3 : 4)
const levelOf = id => Number((id.match(/(\d+)\s*$/) || [0, 0])[1])
const FOUR_ORDER = ['Epic Fire Hydra', 'Epic Undead', 'Epic Arachne', 'Epic Shadow City']
function sortTypes(list, tab) {
  return [...list].sort((a, b) => {
    if (tab === 'emc') {
      const ia = FOUR_ORDER.indexOf(a.id), ib = FOUR_ORDER.indexOf(b.id)
      if (ia !== ib) return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib)
      return a.label.localeCompare(b.label)
    }
    return GROUP_RANK(a.id) - GROUP_RANK(b.id) || levelOf(b.id) - levelOf(a.id) || a.label.localeCompare(b.label)
  })
}

// Ручки точной подстройки главного фейдера (владелец 2026-10-24): ±1% от текущего множителя (0,1% убрано по просьбе),
// при удержании кнопки — повтор. Актуальные k/onK берём из ref: за время удержания фейдер перерисовывается.
function FineKnobs({ k, onK, disabled, tt }) {
  const ref = useRef({ k, onK })
  ref.current = { k, onK }
  const timers = useRef({ start: null, tick: null })
  const stop = () => { clearTimeout(timers.current.start); clearInterval(timers.current.tick) }
  useEffect(() => stop, [])
  const nudge = d => {
    const next = ref.current.k * (1 + d)
    ref.current.onK(Math.round(Math.min(MULTIPLIER_MAX, Math.max(MULTIPLIER_MIN, next)) * 10000) / 10000)
  }
  const hold = d => e => {
    e.preventDefault()
    stop()
    nudge(d)
    timers.current.start = setTimeout(() => { timers.current.tick = setInterval(() => nudge(d), 70) }, 380)
  }
  const knobs = [['−1%', -0.01], ['+1%', 0.01]]
  return (
    <div className="mixer-fine" title={tt.fineTip}>
      {knobs.map(([label, d]) => (
        <button key={label} type="button" className="mixer-fine-btn" disabled={disabled}
          onPointerDown={hold(d)} onPointerUp={stop} onPointerLeave={stop} onPointerCancel={stop}
          onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); nudge(d) } }}>{label}</button>
      ))}
    </div>
  )
}

function Fader({ k, onK, abs, onAbs, calc, on, onToggle, title, disabled, manual, tt, master = false, accent, tip, onReset, resetOff, mk = 1 }) {
  // Число вводится свободно (владелец 2026-10-21): пока поле в фокусе, показываем то, что набирает человек
  // (можно стереть всё и набрать заново), результат применяем на каждый валидный набор.
  const [draft, setDraft] = useState(null)
  // светодиод: зелёный — тип участвует в подсчёте, красный — выключен кнопкой или значение 0
  const counted = on !== false && Number(abs) > 0
  // главный фейдер группы сдвинут — ручки группы идут за ним, а числа под ними крупнее и подсвечены (владелец 2026-10-26)
  const lifted = !master && Math.abs(mk - 1) > 1e-9
  const type = e => {
    const v = e.target.value.replace(',', '.')
    if (!/^\d*\.?\d*$/.test(v)) return
    setDraft(v)
    if (v === '') { if (manual) onAbs(''); return }
    if (v !== '.') onAbs(Number(v))
  }
  return (
    <div className={`mixer-col${master ? ' mixer-col--master' : ''}${lifted ? ' mixer-col--lift' : ''}${disabled ? ' mixer-col--disabled' : ''}${on === false ? ' mixer-col--muted' : ''}`}
         style={accent ? { '--mc': accent } : undefined}>
      <div className="mixer-name" title={tip || title}>{title}</div>
      {onToggle
        ? <button type="button" className={`mixer-dot${counted ? '' : ' mixer-dot--off'}`} title={tt.mute}
            onClick={onToggle} disabled={disabled} />
        : <span className="mixer-dot-gap" />}
      <div className="mixer-rail" title={manual ? tt.manual : tt.reset}>
        {manual ? (
          // у типа нет базы в нормах клана — ползунок двигает число штук напрямую (0…MANUAL_MAX), больше можно вписать
          <input type="range" className="mixer-range" min={0} max={1000} value={500 + Math.min(500, Math.round((Number(abs) || 0) / MANUAL_MAX * 500))}
            disabled={disabled} onChange={e => onAbs(Math.max(0, Math.round((Number(e.target.value) - 500) / 500 * MANUAL_MAX)))}
            onDoubleClick={() => onAbs('')} />
        ) : (
          <input type="range" className="mixer-range" min={0} max={1000} value={kToPos(k * mk)}
            disabled={disabled} onChange={e => onK(posToK(Number(e.target.value)) / mk)}
            onDoubleClick={() => onK(1)} />
        )}
      </div>
      <input className="input-dark mixer-k" type="text" inputMode="decimal" value={draft ?? abs} disabled={disabled}
        title={manual ? tt.manual : `${tt.abs} · ${tt.calc}: ${calc}`} onChange={type} onFocus={e => e.target.select()}
        onBlur={() => setDraft(null)} />
      {master && <FineKnobs k={k} onK={onK} disabled={disabled} tt={tt} />}
      {master && onReset && (
        <button type="button" className="mixer-fine-btn mixer-reset-btn" title={tt.resetMasterTip}
          disabled={disabled || (resetOff ?? Math.abs(k - 1) < 1e-9)} onClick={onReset}>{tt.resetMaster}</button>
      )}
    </div>
  )
}

export default function MixerTab({ lang = 'ru', personal, onPersonal, quotas, onQuotas, onSave, types = [], allChestTypes = null, dirty = false, clanPresets = null, quotaEditor = null, onAddChest = null }) {
  const t = TXT[lang] || TXT.ru
  // режим «Очки/Количество» — свой у каждого пульта (владелец 2026-10-26)
  const [modes, setModes] = useState({ crypts: 'points', emc: 'points' })
  const [sel, setSel] = useState(() => new Set(['all']))
  const [sample, setSample] = useState(400)
  const [presetName, setPresetName] = useState('')
  const [presetSlot, setPresetSlot] = useState('1')
  const [note, setNote] = useState('')
  const [adding, setAdding] = useState(null) // { tab, id } — выбор сундука для добавления в пульт

  const emcQ = quotas.find(q => q.slot === 2)
  const emc = useMemo(() => ({ ...structuredClone(EMC_DEFAULTS), ...(emcQ?.emc || {}) }), [emcQ])
  const mix = personal.mix || {}
  const isAll = sel.has('all')
  const bands = [...sel].filter(x => x !== 'all').sort((a, b) => a - b)
  // Опорный Герой: для «Все уровни» — поле «Пример»; для одной ступени — её середина (+5); для группы — среднее
  // по отмеченным ступеням (200–299 → 250); если среднее попало в неотмеченную ступень (несмежный выбор) —
  // ближайшая отмеченная.
  const exHero = (() => {
    if (isAll) return Number(sample) || 400
    const nums = bands.map(Number)
    if (!nums.length) return 405
    if (nums.length === 1) return nums[0] + 5
    const mean = nums.reduce((a, b) => a + b, 0) / nums.length + 5
    if (nums.includes(Math.floor(mean / 10) * 10)) return Math.round(mean)
    return nums.reduce((best, n) => (Math.abs(n + 5 - mean) < Math.abs(best + 5 - mean) ? n : best), nums[0]) + 5
  })()
  const scale = { ...SCALE_DEFAULTS, norm: personal.norm, weights: personal.weights, ranges: personal.ranges, mix }

  const setPersonal = patch => onPersonal({ ...personal, ...patch })
  const setEmc = next => onQuotas(quotas.map(q => (q.slot === 2 ? { ...q, emc: next } : q)))
  const setMixEntry = (path, id, patch) => {
    const next = { ...(mix[path]?.[id] || {}), ...patch }
    if (next.set === null) delete next.set
    setPersonal({ mix: { ...mix, [path]: { ...(mix[path] || {}), [id]: next } } })
  }

  // Выбор ступеней Героя: «Все уровни» исключает конкретные ступени и наоборот
  const toggleBand = h => setSel(prev => {
    const n = new Set([...prev].filter(x => x !== 'all'))
    const key = String(h)
    if (n.has(key)) n.delete(key); else n.add(key)
    return n.size ? n : new Set(['all'])
  })
  const toggleGroup = group => setSel(prev => {
    const keys = group.bands.map(String)
    const n = new Set([...prev].filter(x => x !== 'all'))
    const full = keys.every(k => n.has(k))
    keys.forEach(k => (full ? n.delete(k) : n.add(k)))
    return n.size ? n : new Set(['all'])
  })

  // значение фейдера для текущего выбора ступеней
  const entryVals = entry => (isAll ? [entry?.all ?? 1] : bands.map(b => entry?.bands?.[b] ?? 1))
  const entryK = entry => entryVals(entry)[0]
  const isMixed = entry => new Set(entryVals(entry)).size > 1
  const withK = (entry, k) => (isAll ? { ...(entry || {}), all: k }
    : { ...(entry || {}), bands: { ...(entry?.bands || {}), ...Object.fromEntries(bands.map(b => [b, k])) } })

  // Один пульт на группу: Crypts — «Квота 1» и «В учёте», EMC — только «Квота 2»; нет сундуков группы —
  // типы шкалы по умолчанию. Вкладок больше нет: обе консоли на странице сразу.
  const pointsCol = x => {
    const e = mix.w?.[x.key]
    const clan = x.points || 0
    const calc = k => {
      const entry = withK(e, k)
      const m = { ...mix, w: { ...(mix.w || {}), [x.key]: entry } }
      const scaled = weightAt(x.key, exHero, { ...scale, mix: m })
      if (scaled != null) return scaled
      // тип вне шкалы: базой служат очки клана из «Сундуков» — считает та же функция, что и публичный счёт
      return fallbackWeight({ id: x.key, slot: x.slot, points: clan }, exHero, { ...scale, mix: m })
    }
    return { key: x.key, title: titleOf(x), e, path: 'w', calc,
      base: weightAt(x.key, exHero, SCALE_DEFAULTS) ?? clan }
  }

  function buildBoard(tab) {
    const mode = modes[tab]
    const seen = new Set()
    const own = types.filter(x => typeTab(x.id, x.slot) === tab).map(x => ({ ...x, key: weightKey(x.id) }))
      .filter(x => (seen.has(x.key) ? false : seen.add(x.key)))
    const fallback = own.length === 0
    const list = sortTypes(fallback
      ? (tab === 'crypts' ? CRYPT_TYPES : EMC_TYPES).map(id => ({ id, key: id, label: id, points: 0 }))
      : own, tab)

    const countCol = x => {
      const e = mix.c?.[x.key]
      const isEmc = tab === 'emc'
      const fn = isEmc ? emcCountAt : countAt
      const zeroBase = !isEmc && !CRYPT_TYPES.includes(x.key)
      return {
        key: x.key, title: titleOf(x), e, path: 'c', manual: zeroBase,
        calc: k => fn(x.key, exHero, { ...scale, mix: { ...mix, c: { ...(mix.c || {}), [x.key]: withK(e, k) } } }, emc),
        base: fn(x.key, exHero, SCALE_DEFAULTS, emc),
      }
    }

    const raw = []
    if (mode === 'points') raw.push(...list.map(pointsCol))
    else if (tab === 'crypts') raw.push(...list.map(countCol))
    else raw.push(...list.filter(x => !(x.key in EMC_FOUR)).map(countCol))

    const cols = raw.map(c => ({
      key: c.key, title: c.title, on: c.e?.on !== false, k: entryK(c.e), calc: c.calc, base: c.base,
      mixed: isMixed(c.e), manual: c.manual, manualValue: c.e?.set,
      onK: k => setMixEntry(c.path, c.key, { ...withK(c.e, k), ...(c.e?.on === false ? { on: true } : {}) }),
      onToggle: () => setMixEntry(c.path, c.key, { on: c.e?.on === false }),
      onSet: v => setMixEntry(c.path, c.key, { set: v }),
    }))

    // четыре монстра с историей клана — рычаги EMC (монстр × ступень), остальные — mix.c
    if (tab === 'emc' && mode === 'count') {
      const keys = ['finalH', 'finalU', 'finalA', 'finalS']
      const baseRow = computeRow(exHero)
      const present = new Set(list.map(x => x.key))
      const four = []
      MONSTERS.forEach(([key, label, id], i) => {
        if (!fallback && !present.has(id)) return
        const isOff = (emc.off || []).includes(key)
        const valsOf = () => (isAll ? [emc.monsters?.[key] ?? 1] : bands.map(b => emc.cells?.[key]?.[b] ?? 1))
        const withEmcK = k => (isAll
          ? { ...emc, monsters: { ...emc.monsters, [key]: k } }
          : { ...emc, cells: { ...(emc.cells || {}), [key]: { ...(emc.cells?.[key] || {}), ...Object.fromEntries(bands.map(b => [b, k])) } } })
        four.push({
          key, title: label, on: !isOff, k: valsOf()[0], mixed: new Set(valsOf()).size > 1,
          calc: k => computeRow(exHero, withEmcK(k))[keys[i]], base: baseRow[keys[i]],
          onK: k => setEmc({ ...withEmcK(k), off: (emc.off || []).filter(x => x !== key) }),
          onToggle: () => setEmc({ ...emc, off: isOff ? emc.off.filter(x => x !== key) : [...(emc.off || []), key] }),
        })
      })
      cols.unshift(...four)
    }
    return { tab, title: tab === 'crypts' ? t.consoleCrypts : t.consoleEmc, enabled: !!personal[tab], fallback, cols, master: groupMaster(tab, list), ownIds: new Set(types.map(x => x.id)),
      lines: mode === 'points' ? pointsLines(list.map(x => ({ key: x.key, title: titleOf(x) })), scale)
        : countLines(tab, list.map(x => ({ key: x.key, title: titleOf(x) })), scale, emc) }
  }

  const absProps = c => {
    if (c.manual) {
      return { abs: c.manualValue ?? '', calcText: c.base, onAbs: v => c.onSet(v === '' ? null : Math.min(9999, Math.round(Math.max(0, Number(v) || 0)))) }
    }
    return {
      abs: c.calc(c.k),
      onAbs: num => {
        if (num === 0) { if (c.on !== false && c.onToggle) c.onToggle(); return }
        if (!(c.calc(MULTIPLIER_MAX) > 0)) return
        c.onK(solveK(c.calc, num, MULTIPLIER_MIN, MULTIPLIER_MAX))
      },
      calcText: c.fmt ? fmt(c.base) : c.base,
    }
  }

  const presets = personal.presets || {}
  const slotLabel = slot => `${slot}. ${presets[slot]?.name || t.empty}`
  const pickSlot = slot => { setPresetSlot(slot); setPresetName(presets[slot]?.name || ''); setNote('') }
  const savePreset = () => {
    const slot = presetSlot
    const next = {
      ...personal,
      presets: { ...presets, [slot]: { name: (presetName.trim() || presets[slot]?.name || `${t.slot} ${slot}`).slice(0, 30),
        norm: personal.norm ?? 1, weights: personal.weights ?? 1, mix, emc, tier_presets: personal.tier_presets || {} } },
    }
    onPersonal(next)
    setNote(t.savedPreset)
    onSave(next)
  }
  const loadPreset = () => {
    const p = presets[presetSlot]
    if (!p) return
    // набор, сохранённый до появления правок пресетов, их не трогает
    onPersonal({ ...personal, norm: p.norm ?? 1, weights: p.weights ?? 1, mix: p.mix || {},
      tier_presets: p.tier_presets ?? personal.tier_presets ?? {} })
    if (p.emc) setEmc({ ...structuredClone(EMC_DEFAULTS), ...p.emc })
    setNote(t.loaded)
  }

  // Пресет клана → очки за сундук (владелец 2026-10-21): по всем типам «Учёта», обеих вкладок
  // items — пресет вместе с правками клана из редактора ниже; возвращает, сколько типов изменено
  const loadClanPreset = items => {
    if (!items) return 0
    const seen = new Set()
    const all = types.map(x => ({ ...x, key: weightKey(x.id) })).filter(x => (seen.has(x.key) ? false : seen.add(x.key)))
    const calcFor = x => pointsCol(x).calc
    const w = presetMixW(items, all, mix.w, { calcFor, withK, keyOf: weightKey })
    const changed = Object.keys(w).filter(k => w[k] !== mix.w?.[k]).length
    setPersonal({ mix: { ...mix, w } })
    return changed
  }

  // Нижняя строка редактора пресета (как в классических окнах): выбор набора, название, «Сохранить» / «Загрузить»
  const hasTiers = ['T5', 'T6', 'T7', 'T8', 'T9'].some(n => clanPresets?.[n])
  const setsControls = (
    <>
      <select className="input-dark pult-select" value={presetSlot} aria-label={t.presets} onChange={e => pickSlot(e.target.value)}>
        {['1', '2', '3'].map(slot => <option key={slot} value={slot}>{slotLabel(slot)}</option>)}
      </select>
      <input className="input-dark pult-name" maxLength={30} placeholder={t.presetName} value={presetName}
        onChange={e => setPresetName(e.target.value)} />
      <button type="button" className="chest-pill-btn" onClick={savePreset}>{t.saveSlot}</button>
      <button type="button" className="chest-pill-btn" disabled={!presets[presetSlot]} onClick={loadPreset}>{t.load}</button>
    </>
  )

  const emcMeta = Object.fromEntries(types.map(x => [x.id, { id: x.id, slot: typeTab(x.id, x.slot) === 'emc' ? 2 : x.slot }]))
  // Три главных фейдера (владелец 2026-10-24) — те же три столбца публичной страницы: Склепы, EMC, Очки.
  // Это вид сверху над уже существующими множителями: mix.epic.all (норма эпик-склепов, все типы склепов),
  // emc.global (все эпические монстры, включая Chimera) и personal.norm (итоговая норма очков).
  // Сколько штук/очков получается для Героя «Примера», показывает число под ползунком; можно вписать своё.
  const mixEpic = mix.epic || {}
  const emcAll = (model, sc) => computeRow(exHero, model).emc + emcOthersTotal(emcMeta, exHero, sc, model)
  // Главный фейдер каждой консоли (владелец 2026-10-26): справа от своего пульта, двигает все сундуки группы.
  // «Очки»: множитель очков типов группы (mix.g); «Количество»: склепы — норма эпик-склепов (mix.epic),
  // EMC — все эпические монстры вместе, включая Chimera (emc.global). Число под ползунком — что получается для Героя «Примера».
  const mixG = mix.g || {}
  const groupMaster = (tab, list) => {
    const mode = modes[tab]
    const isC = tab === 'crypts'
    const accent = isC ? 'var(--epic-purple)' : '#4ADE80'
    const title = isC ? t.mCrypts : t.mEmc
    const disabled = !personal[tab]
    const keys = list.map(x => x.key)
    const dev = e => !!e && (Math.abs((e.all ?? 1) - 1) > 1e-9 || Object.keys(e.bands || {}).length > 0)
    // фейдеры типов этого пульта — в центр (поправки «все уровни» и ступеней убираются); mute и вписанные числа остаются
    const cleanKeys = (obj, clearSet = false) => ({ ...(obj || {}), ...Object.fromEntries(keys.filter(k => obj?.[k]).map(k => [k, { ...obj[k], all: 1, bands: {}, ...(clearSet ? { set: null } : {}) }])) })
    if (mode === 'points') {
      const sumAt = k => {
        const m = { ...mix, g: { ...mixG, [tab]: { ...(mixG[tab] || {}), all: k } } }
        return list.reduce((sum, x) => (mix.w?.[x.key]?.on === false ? sum
          : sum + (weightAt(x.key, exHero, { ...scale, mix: m }) ?? Math.round((x.points || 0) * k))), 0)
      }
      const setG = patch => setPersonal({ mix: { ...mix, g: { ...mixG, [tab]: { ...(mixG[tab] || {}), ...patch } } } })
      return { id: tab, title, tip: isC ? t.gCryptsTip : t.gEmcTip, accent, disabled,
        k: mixG[tab]?.all ?? 1, onK: k => setG({ all: k }),
        resetOff: !(keys.some(k => dev(mix.w?.[k])) || Math.abs((mixG[tab]?.all ?? 1) - 1) > 1e-9),
        onReset: () => { const { [tab]: _drop, ...rest } = mixG; setPersonal({ mix: { ...mix, w: cleanKeys(mix.w), g: rest } }) },
        // число под фейдером — сумма очков за по одному сундуку каждого включённого типа пульта для Героя «Примера»
        calc: sumAt, base: sumAt(1) }
    }
    if (isC) {
      return { id: tab, title, tip: t.mCryptsTip, accent, disabled,
        k: mixEpic.all ?? 1, onK: k => setPersonal({ mix: { ...mix, epic: { ...mixEpic, all: k } } }),
        resetOff: !(keys.some(k => dev(mix.c?.[k]) || mix.c?.[k]?.set != null) || dev(mix.epic)),
        onReset: () => { const { epic, ...rest } = mix; setPersonal({ mix: { ...rest, c: cleanKeys(mix.c, true) } }) },
        calc: k => epicCountTotal(exHero, { ...scale, mix: { ...mix, epic: { ...mixEpic, all: k } } }),
        base: epicCountTotal(exHero, SCALE_DEFAULTS) }
    }
    return { id: tab, title, tip: t.mEmcTip, accent, disabled,
      k: emc.global ?? 1, onK: k => setEmc({ ...emc, global: k }),
      resetOff: !(keys.some(k => dev(mix.c?.[k]) || mix.c?.[k]?.set != null) || (emc.global ?? 1) !== 1
        || MONSTERS.some(([m]) => Math.abs((emc.monsters?.[m] ?? 1) - 1) > 1e-9)
        || Object.values(emc.cells || {}).some(c => Object.keys(c || {}).length > 0)),
      onReset: () => {
        setPersonal({ mix: { ...mix, c: cleanKeys(mix.c, true) } })
        setEmc({ ...emc, global: 1, monsters: { hydra: 1, undead: 1, arachna: 1, shadow: 1 }, cells: {} })
      },
      calc: k => emcAll({ ...emc, global: k }, scale), base: emcAll(EMC_DEFAULTS, SCALE_DEFAULTS) }
  }
  // Поправки ступеней с графика: очки — mix.w, штуки — mix.c, четыре монстра EMC — emc.cells
  const applyBands = (line, bands) => {
    const next = writeBands({ mix, emc }, line.target, bands)
    if (line.target.path === 'cell') setEmc(next.emc)
    else setPersonal({ mix: next.mix })
  }
  const resetLines = lines => {
    let st = { mix, emc }
    lines.filter(l => Object.keys(l.bands || {}).length > 0).forEach(l => { st = writeBands(st, l.target, {}) })
    if (st.mix !== mix) setPersonal({ mix: st.mix })
    if (st.emc !== emc) setEmc(st.emc)
  }
  // Какие сундуки можно добавить в пульт: весь каталог клана, кроме уже стоящих в учёте; сначала подходящие по названию
  const addCandidates = b => {
    const mine = /Crypt|Citadel/i
    const have = new Set([...b.ownIds].map(weightKey))
    return (allChestTypes || [...CRYPT_TYPES, ...EMC_TYPES].map(id => ({ id, label: id })))
      .filter(o => !have.has(weightKey(o.id)))
      .sort((x, y) => ((mine.test(y.id) ? 1 : 0) - (mine.test(x.id) ? 1 : 0)) * (b.tab === 'crypts' ? 1 : -1) || x.label.localeCompare(y.label))
  }
  const boards = ['crypts', 'emc'].map(buildBoard)
  const editing = isAll ? t.allLevels : bands.map(bandLabel).join(', ')

  return (
    <div className="mixer">
      <details className="mixer-help">
        <summary>{t.help}</summary>
        {t.helpText.map((line, i) => <p key={i} className="emc-text mixer-help-text">{line}</p>)}
      </details>

      {quotaEditor && <section className="mixer-quotas">{quotaEditor}</section>}

      <TierPresetEditor lang={lang} clanPresets={clanPresets} personal={personal} onPersonal={onPersonal} sets={setsControls} setsNote={note}
        onLoad={loadClanPreset}
        setsTitle={t.presets} setsHint={t.presetHint}
        catalogItems={allChestTypes || [...new Set([...CRYPT_TYPES, ...EMC_TYPES, ...types.map(x => x.id)])].map(id => ({ id, label: id }))} />


      {/* Герой — первым делом: выбрали Героя/ступени и сразу двигаем главные фейдеры ниже (владелец 2026-10-24) */}
      <section className="mixer-hero-card">
        <div className="mixer-hero-row">
          <span className="pult-hero-label">{t.hero}</span>
          {isAll ? (
            <input className="input-dark pult-hero-input" type="number" min={100} max={600} value={sample}
              aria-label={t.sample} title={t.sample} onChange={e => setSample(e.target.value)} />
          ) : (
            <>
              <b className="pult-hero-badge">{editing}</b>
              <button type="button" className="pult-link-btn" onClick={() => setSel(new Set(['all']))}>{t.allLevels}</button>
            </>
          )}
          <div className="mixer-hero-actions">
            <b className={dirty ? 'mixer-dirty' : 'mixer-clean'}>{dirty ? t.dirtyOn : t.dirtyOff}</b>
            <button type="button" className="chest-pill-btn chest-pill-btn--primary" onClick={() => onSave()}>{t.save}</button>
          </div>
        </div>
        <div className="mixer-levels">
        <label className="mixer-all">
          <input type="checkbox" checked={isAll} onChange={() => setSel(new Set(['all']))} />
          <b>{t.allLevels}</b>
        </label>
        <div className="mixer-grid">
          {GROUPS.map(group => {
            const keys = group.bands.map(String)
            const full = !isAll && keys.every(k => sel.has(k))
            return (
              <div key={group.g} className="mixer-group">
                <label className="mixer-group-head">
                  <input type="checkbox" checked={full} onChange={() => toggleGroup(group)} />
                  <b>{group.g}+</b>
                </label>
                {group.bands.map(h => (
                  <label key={h} className="mixer-band">
                    <input type="checkbox" checked={!isAll && sel.has(String(h))} onChange={() => toggleBand(h)} />
                    <span>{bandLabel(h)}</span>
                  </label>
                ))}
              </div>
            )
          })}
        </div>
      </div>
      </section>

      <div className="pult-scope" role="note">
        <b>{isAll ? t.scopeAllTitle : t.scopeDivTitle.replace('{what}', `${t.hero} ${editing}`)}</b>
        <p>{isAll ? t.scopeAllText.replace('{h}', exHero) : t.scopeDivText}</p>
      </div>

      {/* Два пульта один под другим (владелец 2026-10-26): справа у каждого свой главный фейдер, он двигает все сундуки своей группы */}
      {boards.map(b => {
        const ma = absProps(b.master)
        return (
          <section key={b.tab} className="mixer-console" aria-label={b.title}>
            <div className="mixer-console-head">
              <h3 className="mixer-console-title">{b.title}</h3>
              <div className="mixer-switch">
                {[['points', t.points], ['count', t.count]].map(([id, label]) => (
                  <button key={id} type="button" className={`chest-pill-btn chest-pill-btn--sm${modes[b.tab] === id ? ' chest-pill-btn--green' : ''}`}
                    onClick={() => setModes({ ...modes, [b.tab]: id })}>{label}</button>
                ))}
              </div>
              {onAddChest && (adding?.tab === b.tab ? (
                <span className="mixer-add">
                  <select className="input-dark" value={adding.id} onChange={e => setAdding({ tab: b.tab, id: e.target.value })} aria-label={t.addChest}>
                    <option value="">{t.addPick}</option>
                    {addCandidates(b).map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
                  </select>
                  <button type="button" className="chest-pill-btn chest-pill-btn--primary" disabled={!adding.id}
                    onClick={() => { onAddChest(b.tab, adding.id, weightAt(adding.id, exHero, SCALE_DEFAULTS) ?? 0); setAdding(null); setNote(t.chestAdded) }}>{t.addOk}</button>
                  <button type="button" className="pult-link-btn" onClick={() => setAdding(null)}>{t.addCancel}</button>
                </span>
              ) : (
                <button type="button" className="chest-pill-btn" onClick={() => setAdding({ tab: b.tab, id: '' })}>{t.addChest}</button>
              ))}
              <label className="quota-check">
                <input type="checkbox" checked={b.enabled} onChange={e => setPersonal({ [b.tab]: e.target.checked })} />
                {t.enable}
              </label>
            </div>
            {!b.enabled && <p className="emc-text"><small>{t.off}</small></p>}
            {b.fallback && <p className="emc-text"><small>{t.noTypes}</small></p>}
            {b.cols.some(c => c.mixed) && <p className="emc-text"><small>⚠ {t.mixed}</small></p>}
            {b.tab === 'crypts' && modes.crypts === 'count' && <p className="emc-text"><small>{t.countNote}</small></p>}
            <div className={`mixer-board${b.enabled ? '' : ' mixer-board--off'}`}>
              <div className="mixer-cols">
                {b.cols.map(c => {
                  const a = absProps(c)
                  return (
                    <Fader key={c.key} tt={t} title={c.title} k={c.k} onK={c.onK} on={c.on} onToggle={c.onToggle}
                      mk={c.manual ? 1 : b.master.k} accent={!c.manual && Math.abs(b.master.k - 1) > 1e-9 ? b.master.accent : undefined}
                      abs={a.abs} onAbs={a.onAbs} calc={a.calcText} manual={c.manual} disabled={!b.enabled} />
                  )
                })}
              </div>
              <div className="mixer-master">
                <Fader tt={t} master accent={b.master.accent} tip={b.master.tip} title={b.master.title} k={b.master.k} onK={b.master.onK}
                  abs={ma.abs} onAbs={ma.onAbs} calc={ma.calcText} disabled={b.master.disabled} onReset={b.master.onReset} resetOff={b.master.resetOff} />
              </div>
            </div>
            <CurveEditor lang={lang} mode={modes[b.tab]} lines={b.lines} disabled={!b.enabled}
              onBands={applyBands} onResetAll={() => resetLines(b.lines)}
              hasLines={b.lines.some(l => Object.keys(l.bands || {}).length > 0)}
              footer={<>{setsControls}</>} note={note} />
          </section>
        )
      })}

      <section className="pult-card pult-card--main">
        <div className="pult-actions">
          <button type="button" className="chest-pill-btn chest-pill-btn--primary" onClick={() => onSave()}>{t.save}</button>
          <b className={dirty ? 'mixer-dirty' : 'mixer-clean'}>{dirty ? t.dirtyOn : t.dirtyOff}</b>
        </div>
        <p className="pult-hint">{t.saved}</p>
      </section>

    </div>
  )
}
