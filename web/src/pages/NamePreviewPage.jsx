import { useState } from 'react'
import { renderPlayerName } from '../components/ChestSummaryTable.jsx'

// ОБРАЗЕЦ (только локально, /dev/names): весь путь имени из РАБОЧЕГО кода ChestSummaryTable —
// ровно то, что увидит клан на публичной странице.

const QUOTA = 10000
const TARGETS = { points: QUOTA }
const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII']
const TIERS = [10, 12, 14, 17, 20, 24, 28, 33, 38, 44, 50, 57, 64, 72, 80, 89, 98]
const LEGEND_NAMES = ['Феникс', 'DragonSlayer', 'Эльдорадо', 'Imperator', 'Громовержец', 'Цезарь',
  'NightHawk', 'Воевода', 'IronWolf', 'Август', 'Basileus', 'Гвардеец', 'Обсидиан', 'Пламя',
  'Сапфир', 'Бронзовый', 'Индиго']
const LEGEND_NOTES = ['Синяя лента', '〃', '〃', 'Прямой штандарт, золото, поле течёт', '〃',
  'Ласточкин хвост', '〃', '+ серебряная нить', '〃', 'Рубин в золоте', 'Пурпур + ореол',
  'Изумрудная гвардия', 'Обсидиан и золото', 'Огненное золото', 'Платина и сапфир',
  'Бронза и лазурь + золотой волосок', 'Лазурь и индиго, поле индиго']
const PATH = [
  [0.1, '10% цели', 'Новичок'], [0.3, '30% цели', 'Ратник'], [0.5, '50% цели', 'Страж'],
  [0.7, '70% цели', 'Лучник'], [0.9, '90% цели', 'Рыцарь'],
  [1, '×1 цель', 'Витязь'], [1.5, '×1.5', 'Барон'], [2, '×2', 'Граф'], [3, '×3', 'Маркиз'],
  [4, '×4', 'Герцог'], [5, '×5', 'Князь'], [6, '×6', 'Паладин'], [7, '×7', 'Магистр'],
  [8, '×8', 'Полководец'], [9, '×9', 'Маршал'], [9.8, '×9.8', 'Регент'],
]

const CSS = `
.np-page { max-width: 1100px; margin: 0 auto; padding: 24px 16px 80px; color: var(--on-surface); }
.np-page h1 { font-size: 26px; margin: 0 0 6px; }
.np-page h2 { font-size: 20px; margin: 32px 0 10px; }
.np-note { color: var(--on-surface2); font-size: 16px; line-height: 1.5; margin: 0 0 12px; }
.np-rows { background: var(--surface, #12141a); border: 1px solid var(--outline); border-radius: 10px; }
.np-row { display: grid; grid-template-columns: 56px 110px minmax(260px, 1fr) 1fr; align-items: center; gap: 12px;
  padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.08); }
.np-row:last-child { border-bottom: 0; }
.np-rank { font-weight: 700; color: var(--on-surface2); font-size: 16px; }
.np-thr { color: var(--credits-gold); font-weight: 700; font-size: 16px; }
.np-style { color: var(--on-surface2); font-size: 15px; }
.np-variants { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 14px; }
.np-variants button { font-size: 15px; padding: 8px 14px; border-radius: 8px; cursor: pointer;
  background: var(--elevated); color: var(--on-surface); border: 1px solid var(--outline); }
.np-variants button.on { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent) inset; }
@media (max-width: 700px) {
  .np-row { grid-template-columns: 44px 60px 1fr; }
  .np-style { grid-column: 1 / -1; font-size: 14px; }
}
`

function Row({ rank, thr, name, points, note }) {
  return (
    <div className="np-row">
      <span className="np-rank">{rank}</span>
      <span className="np-thr">{thr}</span>
      <span>{renderPlayerName({ name, points }, TARGETS)}</span>
      <span className="np-style">{note}</span>
    </div>
  )
}

export default function NamePreviewPage() {
  const [mobile, setMobile] = useState(false)
  return (
    <div className="np-page public-table" style={{ whiteSpace: 'normal', '--public-name-base': mobile ? '14.5px' : '17px' }}>
      <style>{CSS}</style>
      <h1>Имена игроков: весь путь</h1>
      <p className="np-note">Из рабочего кода. Цель сезона в примере: {QUOTA.toLocaleString('ru-RU')} очков.</p>
      <div className="np-variants">
        <button className={!mobile ? 'on' : ''} onClick={() => setMobile(false)}>Шрифт ПК (17px)</button>
        <button className={mobile ? 'on' : ''} onClick={() => setMobile(true)}>Шрифт телефона (14.5px)</button>
      </div>
      <h2>До легенды</h2>
      <div className="np-rows">
        {PATH.map(([r, label, name]) => (
          <Row key={r} rank={r < 1 ? '—' : '★'} thr={label} name={name} points={r * QUOTA}
            note={`${(r * QUOTA).toLocaleString('ru-RU')} очков`} />
        ))}
      </div>
      <h2>Легенды I–XVII</h2>
      <div className="np-rows">
        {TIERS.map((x, i) => (
          <Row key={x} rank={ROMAN[i]} thr={`×${x}`} name={LEGEND_NAMES[i]} points={(x + 0.5) * QUOTA} note={LEGEND_NOTES[i]} />
        ))}
      </div>
    </div>
  )
}
