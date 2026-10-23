import { useMemo, useState } from 'react'
import {
  DEFAULT_SETTINGS as EMC_DEFAULTS, computeRow, clampMultiplier, MULTIPLIER_MIN, MULTIPLIER_MAX,
} from '../lib/emcQuota.js'
import TierPresetEditor from './TierPresetEditor.jsx'
import { posToK, kToPos, solveK, presetMixW } from '../lib/mixer.js'
import {
  DEFAULT_SETTINGS as SCALE_DEFAULTS, CRYPT_TYPES, EMC_TYPES, EMC_FOUR, EPIC_CRYPTS,
  weightKey, weightAt, normAt, cryptsNormAt, countAt, emcCountAt, emcOthersTotal, typeTab,
} from '../lib/heroQuota.js'

// «Пульт» (владелец 2026-10-20/21): единый центр персональных настроек. Вкладки Crypts / EMC, колонка на
// тип сундука из «Учёта» клана, фейдер: середина = рассчитанное значение (×1), вверх — больше, вниз —
// меньше; зелёная точка — вкл/выкл тип. Слева выбираются ступени Героя (можно несколько): правка
// применяется ко всем отмеченным; «Все уровни» — множитель пропорционально на каждую ступень.
// Переключатель «Очки/Количество» меняет, что двигают фейдеры. Фейдер логарифмический: ×0.1 … ×1 … ×3.

const TXT = {
  ru: {
    tabCrypts: 'Crypts', tabEmc: 'EMC',
    points: 'Очки', count: 'Количество',
    allLevels: 'Все уровни', hero: 'Герой',
    master: 'Общий', masterCryptsPoints: 'Норма', masterEmcCount: 'Все монстры',
    enable: 'Персонализированный учёт по уровню Героя',
    off: 'Сейчас выключено: нормы игроков фиксированные, из настроек сезона. Включите переключатель, чтобы настраивать нормы по уровням Героя.',
    sample: 'Пример для Героя',
    reset: 'Двойной щелчок по ползунку — вернуть расчётное значение',
    mute: 'Вкл/выкл: выключенный тип не считается',
    abs: 'Значение: сотрите и впишите своё число (0 — выключить тип)',
    manual: 'В нормах клана штук для этого типа нет — впишите число вручную (пусто = 0)',
    calc: 'расчёт',
    countNote: 'Эпик-склепы: ориентир клана ÷ число включённых эпик-типов. Rare/Common/Citadel: в нормах клана штук нет — впишите число вручную при желании.',
    save: '💾 Сохранить настройки', saved: 'Сохраняет всё, что настроено на этой вкладке, как настройку сезона — её видят игроки на публичной странице.',
    dirtyOn: '● Есть несохранённые изменения', dirtyOff: '✓ Всё сохранено',
    summary: 'Герой {h}: норма «Всего» {total} · Crypts {crypts} · EMC {emc} шт.',
    editing: 'Правим: {what}',
    scopeAllTitle: 'Вы правите: «Все уровни»',
    scopeAllText: 'Число, которое вы задаёте (очки или количество), считается для уровня Героя из поля «Пример для Героя» ({h}). Остальные уровни Героя меняются в той же пропорции: форма шкалы сохраняется, слабым Героям по-прежнему меньше, сильным больше. Пример: сундук на Герое 400 даёт 135 очков, на Герое 300 — 150. Вы поставили 160 для Героя 400 — на Герое 300 станет 180.',
    scopeDivTitle: 'Вы правите только: {what}',
    scopeDivText: 'Число, которое вы задаёте (очки или количество), — итоговое значение именно для выбранных уровней Героя. Остальные уровни не меняются, поэтому на границе с соседним уровнем получится «ступенька»: например, 135 очков на Героях 390–399, 160 на 400–409 и снова 135 на 410–419.',
    mixed: 'у выбранных уровней значения разные — ползунок задаст одинаковое',
    noTypes: 'В «Учёте» клана пока нет сундуков этой группы — показаны типы шкалы по умолчанию.',
    presets: 'Наборы настроек очков', presetName: 'Название', slot: 'Слот', empty: 'пусто', saveSlot: 'Сохранить набор', load: 'Загрузить набор',
    presetHint: 'Набор сохраняет всё, что вы настроили на этой вкладке: положения ползунков, числа по эпическим монстрам и свои правки пресетов T5–T9. Общие пресеты T5–T9 не меняются никогда: ваши правки лежат отдельно, в трёх слотах можно держать три своих варианта. «Сохранить настройки» выше применяет текущие значения к сезону; сохранение в набор тоже записывает сезон.',
    loaded: 'Набор загружен. Нажмите «Сохранить настройки», чтобы применить к сезону.',
    savedPreset: 'Набор сохранён.',
    help: 'Как работают личные нормы игроков',
    helpText: [
      'Вкладка «Общие нормы клана» (быстрая настройка) — одни нормы на весь клан: названия, очки за сундук, «Учёт». Она остаётся всегда и питает колонку «Очки» в таблице игроков.',
      '«Личные нормы игроков» включаются переключателем «Персонализированный учёт по уровню Героя» на квоте Crypts и/или EMC. Тогда нормы игрока считаются по уровню его Героя: чем ниже Герой, тем больше очков за сундук и меньше норма, и наоборот. Шкала построена по данным реальных кланов и рассчитана на уровни Героя 100–600. Учёт ведётся за 2 недели (сезон — 14 дней).',
      'Здесь — те сундуки, которые клан держит в «Учёте». Вкладка EMC — только сундуки со статусом «Квота 2»; вкладка Crypts — «Квота 1» и «В учёте» (учитываются без квоты). Для сундуков вне шкалы (например, свои события) за основу берутся очки из вкладки «Общие нормы клана».',
      'У каждого сундука есть ползунок и число под ним — это одно и то же: двигаете ползунок — число меняется, вписываете число — ползунок встаёт сам. Середина ползунка — рассчитанное значение, вверх — больше, вниз — меньше. Число можно стереть и вписать любое своё (0 выключает сундук). Зелёная точка тоже выключает сундук.',
      '«Очки» — сколько очков даёт сундук. «Количество» — сколько штук ждут от игрока: у эпик-склепов — ориентир клана, у эпических монстров — данные кланов ELDORADO и Берсерки.',
      'Два способа править. «Все уровни»: вы задаёте число для выбранного «Примера для Героя», остальные уровни меняются в той же пропорции. Или отметьте один или несколько уровней Героя: тогда число действует только для них, остальные уровни не затрагиваются (на границе будет ступенька). Одинаково для «Очки» и «Количество».',
      'Наборы настроек очков — 3 слота: сохраните свои настройки и загрузите позже.',
    ],
  },
  en: {
    tabCrypts: 'Crypts', tabEmc: 'EMC',
    points: 'Points', count: 'Count',
    allLevels: 'All levels', hero: 'Hero',
    master: 'Master', masterCryptsPoints: 'Norm', masterEmcCount: 'All monsters',
    enable: 'Personalized accounting by Hero level',
    off: 'Currently off: player norms are fixed from the season settings. Turn the switch on to set norms by Hero level.',
    sample: 'Example for Hero',
    reset: 'Double-click a slider to return the calculated value',
    mute: 'On/off: a muted type is not counted',
    abs: 'Value: erase and type your own number (0 turns the type off)',
    manual: 'The clan norms give no count for this type — type a number (empty = 0)',
    calc: 'calc.',
    countNote: 'Epic crypts: the clan guideline ÷ number of enabled epic types. Rare/Common/Citadel: the clan norms give no counts — type a number if you wish.',
    save: '💾 Save settings', saved: 'Saves everything set on this tab as the season setting — players see it on the public page.',
    dirtyOn: '● Unsaved changes', dirtyOff: '✓ All saved',
    summary: 'Hero {h}: Total norm {total} · Crypts {crypts} · EMC {emc} pcs',
    editing: 'Editing: {what}',
    scopeAllTitle: 'You are editing: All levels',
    scopeAllText: 'The number you set (points or count) applies to the Hero level from the "Example for Hero" field ({h}). Other Hero levels follow in the same proportion: the shape of the scale is kept, weaker Heroes still get less, stronger ones more. Example: a chest gives 135 points at Hero 400 and 150 at Hero 300. You set 160 for Hero 400 — at Hero 300 it becomes 180.',
    scopeDivTitle: 'You are editing only: {what}',
    scopeDivText: 'The number you set (points or count) is the final value for the chosen Hero levels only. Other levels stay as they are, so there will be a step at the border with the neighbouring level: for example 135 points at Heroes 390–399, 160 at 400–409 and 135 again at 410–419.',
    mixed: 'selected levels have different values — the slider will set them equal',
    noTypes: "The clan's accounting has no chests of this group yet — showing the default scale types.",
    presets: 'Point settings sets', presetName: 'Name', slot: 'Slot', empty: 'empty', saveSlot: 'Save set', load: 'Load set',
    presetHint: "A set stores everything you configured on this tab: slider positions, numbers for epic monsters and your edits of the T5–T9 presets. The shared T5–T9 presets never change: your edits are kept separately, and the three slots hold three of your own variants. 'Save settings' above applies the current values to the season; saving to a set also saves the season.",
    loaded: "Set loaded. Press 'Save settings' to apply it to the season.",
    savedPreset: 'Preset saved.',
    help: 'How personal player norms work',
    helpText: [
      'The \'Clan-wide norms\' tab (quick setup) holds one set of norms for the whole clan: names, points per chest, accounting. It always stays and feeds the \'Points\' column of the player table.',
      '\'Personal player norms\' are turned on by the \'Personalized accounting by Hero level\' switch on the Crypts and/or EMC quota. A player\'s norms are then calculated by the player\'s Hero level: the lower the Hero, the more points per chest and the smaller the norm, and vice versa. The scale is built from real clan data and covers Hero levels 100–600. Accounting covers 2 weeks (a season is 14 days).',
      'This tab shows the chests the clan keeps in accounting. The EMC tab holds only chests with the \'Quota 2\' status; the Crypts tab holds \'Quota 1\' and \'Counted\' (counted without a quota). For chests outside the scale (e.g. custom events) the base is the points from the \'Clan-wide norms\' tab.',
      'Every chest has a slider and a number below it — they are the same thing: move the slider and the number changes, type a number and the slider follows. The middle of the slider is the calculated value, up is more, down is less. You can erase the number and type your own (0 turns the chest off). The green dot also turns a chest off.',
      '\'Points\' is how many points a chest gives. \'Count\' is how many pieces are expected from a player: epic crypts — the clan guideline, epic monsters — data of the clans ELDORADO and Berserki.',
      'Two ways to edit. \'All levels\': you set a number for the chosen \'Example for Hero\', and other levels follow in the same proportion. Or tick one or several Hero levels: then the number applies only to them and other levels are untouched (there will be a step at the border). Same for Points and Count.',
      'Sets of point settings — 3 slots: save your settings and load them later.',
    ],
  },
}

const MONSTERS = [['hydra', 'Hydra', 'Epic Fire Hydra'], ['undead', 'Undead', 'Epic Undead'],
  ['arachna', 'Arachna', 'Epic Arachne'], ['shadow', 'Shadow City', 'Epic Shadow City']]
const GROUPS = [100, 200, 300, 400, 500].map(g => ({
  g, bands: Array.from({ length: g === 500 ? 11 : 10 }, (_, i) => g + i * 10),
}))
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

function Fader({ k, onK, abs, onAbs, calc, on, onToggle, title, disabled, manual, tt }) {
  // Число вводится свободно (владелец 2026-10-21): пока поле в фокусе, показываем то, что набирает человек
  // (можно стереть всё и набрать заново), результат применяем на каждый валидный набор.
  const [draft, setDraft] = useState(null)
  const type = e => {
    const v = e.target.value.replace(',', '.')
    if (!/^\d*\.?\d*$/.test(v)) return
    setDraft(v)
    if (v === '') { if (manual) onAbs(''); return }
    if (v !== '.') onAbs(Number(v))
  }
  return (
    <div className={`mixer-col${disabled ? ' mixer-col--disabled' : ''}${on === false ? ' mixer-col--muted' : ''}`}>
      <div className="mixer-name" title={title}>{title}</div>
      {onToggle
        ? <button type="button" className={`mixer-dot${on === false ? ' mixer-dot--off' : ''}`} title={tt.mute}
            onClick={onToggle} disabled={disabled} />
        : <span className="mixer-dot-gap" />}
      <div className="mixer-rail" title={manual ? tt.manual : tt.reset}>
        <input type="range" className="mixer-range" min={0} max={1000} value={kToPos(k)}
          disabled={disabled || manual} onChange={e => onK(posToK(Number(e.target.value)))}
          onDoubleClick={() => onK(1)} />
      </div>
      <input className="input-dark mixer-k" type="text" inputMode="decimal" value={draft ?? abs} disabled={disabled}
        title={manual ? tt.manual : `${tt.abs} · ${tt.calc}: ${calc}`} onChange={type} onFocus={e => e.target.select()}
        onBlur={() => setDraft(null)} />
    </div>
  )
}

export default function MixerTab({ lang = 'ru', personal, onPersonal, quotas, onQuotas, onSave, types = [], allChestTypes = null, dirty = false, clanPresets = null }) {
  const t = TXT[lang] || TXT.ru
  const [tab, setTab] = useState('crypts')
  const [mode, setMode] = useState('points')
  const [sel, setSel] = useState(() => new Set(['all']))
  const [sample, setSample] = useState(400)
  const [presetName, setPresetName] = useState('')
  const [presetSlot, setPresetSlot] = useState('1')
  const [note, setNote] = useState('')

  const emcQ = quotas.find(q => q.slot === 2)
  const emc = useMemo(() => ({ ...structuredClone(EMC_DEFAULTS), ...(emcQ?.emc || {}) }), [emcQ])
  const mix = personal.mix || {}
  const flag = tab === 'crypts' ? 'crypts' : 'emc'
  const enabled = !!personal[flag]
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

  // Типы клана для вкладки (EMC — только «Квота 2»; Crypts — «Квота 1» и «В учёте»); нет сундуков группы —
  // типы шкалы по умолчанию
  const own = useMemo(() => {
    const seen = new Set()
    return types.filter(x => typeTab(x.id, x.slot) === tab).map(x => ({ ...x, key: weightKey(x.id) }))
      .filter(x => (seen.has(x.key) ? false : seen.add(x.key)))
  }, [types, tab])
  const fallback = own.length === 0
  const list = sortTypes(fallback
    ? (tab === 'crypts' ? CRYPT_TYPES : EMC_TYPES).map(id => ({ id, key: id, label: id, points: 0 }))
    : own, tab)

  const pointsCol = x => {
    const e = mix.w?.[x.key]
    const clan = x.points || 0
    const calc = k => {
      const entry = withK(e, k)
      const m = { ...mix, w: { ...(mix.w || {}), [x.key]: entry } }
      const scaled = weightAt(x.key, exHero, { ...scale, mix: m })
      if (scaled != null) return scaled
      // тип вне шкалы: базой служат очки клана из «Сундуков»
      return Math.round(clan * clampMultiplier(entry.all) * clampMultiplier(entry.bands?.[bands[0]]))
    }
    return { key: x.key, title: titleOf(x), e, path: 'w', calc,
      base: weightAt(x.key, exHero, SCALE_DEFAULTS) ?? clan }
  }
  const countCol = x => {
    const e = mix.c?.[x.key]
    const isEmc = tab === 'emc'
    const fn = isEmc ? emcCountAt : countAt
    const zeroBase = !isEmc && !EPIC_CRYPTS.includes(x.key)
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

  // Общий фейдер: Crypts — норма; EMC/«Количество» — общий множитель монстров; EMC/«Очки» общего нет
  const master = tab === 'crypts'
    ? { title: t.masterCryptsPoints, k: personal.norm ?? 1, onK: k => setPersonal({ norm: k }),
        calc: k => normAt(exHero, { ...scale, norm: k }), base: normAt(exHero, SCALE_DEFAULTS), fmt: true }
    : mode === 'count'
      ? { title: t.masterEmcCount, k: emc.global ?? 1, onK: k => setEmc({ ...emc, global: k }),
          calc: k => computeRow(exHero, { ...emc, global: k }).emc, base: computeRow(exHero).emc }
      : null

  const absProps = c => {
    if (c.manual) {
      return { abs: c.manualValue ?? '', calcText: c.base, onAbs: v => c.onSet(v === '' ? null : Math.max(0, Number(v) || 0)) }
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
  const emcTotal = computeRow(exHero, emc).emc + emcOthersTotal(emcMeta, exHero, scale, emc)
  const summary = t.summary.replace('{h}', exHero).replace('{total}', fmt(normAt(exHero, scale)))
    .replace('{crypts}', fmt(cryptsNormAt(exHero, emc, scale))).replace('{emc}', emcTotal)
  const editing = isAll ? t.allLevels : bands.map(bandLabel).join(', ')
  const summaryNode = summary

  return (
    <div className="mixer">
      <details className="mixer-help">
        <summary>{t.help}</summary>
        {t.helpText.map((line, i) => <p key={i} className="emc-text mixer-help-text">{line}</p>)}
      </details>

      <div className="chest-tabs chest-tabs--pill">
        {[['crypts', t.tabCrypts], ['emc', t.tabEmc]].map(([id, label]) => (
          <button key={id} type="button" className={`chest-tab chest-tab--pill ${tab === id ? 'chest-tab--active' : ''}`}
            onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>

      <div className="mixer-bar">
        <label className="quota-check">
          <input type="checkbox" checked={enabled} onChange={e => setPersonal({ [flag]: e.target.checked })} />
          {t.enable}
        </label>
        <div className="mixer-switch">
          {[['points', t.points], ['count', t.count]].map(([id, label]) => (
            <button key={id} type="button" className={`chest-pill-btn chest-pill-btn--sm${mode === id ? ' chest-pill-btn--green' : ''}`}
              onClick={() => setMode(id)}>{label}</button>
          ))}
        </div>
        {isAll && (
          <label className="mixer-pick">
            <span>{t.sample}</span>
            <input className="input-dark emc-level-input" type="number" min={100} max={600} value={sample}
              onChange={e => setSample(e.target.value)} />
          </label>
        )}
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

      {!enabled && <p className="emc-text"><small>{t.off}</small></p>}
      {fallback && <p className="emc-text"><small>{t.noTypes}</small></p>}
      <div className="pult-scope" role="note">
        <b>{isAll ? t.scopeAllTitle : t.scopeDivTitle.replace('{what}', `${t.hero} ${editing}`)}</b>
        <p>{isAll ? t.scopeAllText.replace('{h}', exHero) : t.scopeDivText}</p>
      </div>
      {cols.some(c => c.mixed) && <p className="emc-text"><small>⚠ {t.mixed}</small></p>}
      {tab === 'crypts' && mode === 'count' && <p className="emc-text"><small>{t.countNote}</small></p>}

      <div className={`mixer-board${enabled ? '' : ' mixer-board--off'}`}>
        <div className="mixer-cols">
          {cols.map(c => {
            const a = absProps(c)
            return (
              <Fader key={c.key} tt={t} title={c.title} k={c.k} onK={c.onK} on={c.on} onToggle={c.onToggle}
                abs={a.abs} onAbs={a.onAbs} calc={a.calcText} manual={c.manual} disabled={!enabled} />
            )
          })}
        </div>
        <div className="mixer-master">
          {master
            ? (() => {
              const a = absProps(master)
              return <Fader tt={t} title={master.title} k={master.k} onK={master.onK} abs={a.abs} onAbs={a.onAbs}
                calc={a.calcText} disabled={!enabled} />
            })()
            : <div className="mixer-name">{t.master}</div>}
        </div>
      </div>

      <section className="pult-card pult-card--main">
        <div className="pult-hero">
          <span className="pult-hero-label">{t.hero}</span>
          {isAll ? (
            <input className="input-dark pult-hero-input" type="number" min={100} max={600} value={sample}
              aria-label={t.sample} onChange={e => setSample(e.target.value)} />
          ) : (
            <>
              <b className="pult-hero-badge">{editing}</b>
              <button type="button" className="pult-link-btn" onClick={() => setSel(new Set(['all']))}>{t.allLevels}</button>
            </>
          )}
        </div>
        <div className="pult-summary">{summaryNode}</div>
        <div className="pult-actions">
          <button type="button" className="chest-pill-btn chest-pill-btn--primary" onClick={() => onSave()}>{t.save}</button>
          <b className={dirty ? 'mixer-dirty' : 'mixer-clean'}>{dirty ? t.dirtyOn : t.dirtyOff}</b>
        </div>
        <p className="pult-hint">{t.saved}</p>
      </section>

      {!hasTiers && (
        <section className="pult-card">
          <h3>{t.presets}</h3>
          <div className="pult-actions">{setsControls}</div>
          <p className="pult-hint">{t.presetHint}</p>
          {note && <p className="pult-flash">{note}</p>}
        </section>
      )}

      <TierPresetEditor lang={lang} clanPresets={clanPresets} personal={personal} onPersonal={onPersonal}
        onLoad={loadClanPreset}
        sets={setsControls} setsTitle={t.presets} setsHint={t.presetHint} setsNote={note}
        catalogItems={allChestTypes || [...new Set([...CRYPT_TYPES, ...EMC_TYPES, ...types.map(x => x.id)])].map(id => ({ id, label: id }))} />
    </div>
  )
}
