import { useMeta } from '../hooks/useMeta.js'
import { useLang } from '../lang.js'
import { Link } from 'react-router-dom'

/* ─── Reusable layout helpers ───────────────────────────────── */

function Section({ children, style }) {
  return (
    <section style={{ marginBottom: 72, ...style }}>
      {children}
    </section>
  )
}

function SectionTitle({ children }) {
  return (
    <h2 style={{ fontSize: '1.45rem', fontWeight: 700, color: '#c9a227', marginBottom: 18, display: 'flex', alignItems: 'center', gap: 10 }}>
      {children}
    </h2>
  )
}

function Para({ children, muted }) {
  return (
    <p style={{ marginBottom: 14, color: muted ? '#aaa' : '#dde' }}>
      {children}
    </p>
  )
}

function Divider() {
  return <div style={{ height: 1, background: 'rgba(201,162,39,0.15)', margin: '64px 0' }} />
}

function ScreenRow({ screens }) {
  return (
    <div style={{
      display: 'flex', gap: 12, flexWrap: 'wrap', margin: '20px 0',
    }}>
      {screens.map(({ src, caption }, i) => (
        <figure key={i} style={{ margin: 0, flex: '1 1 200px', minWidth: 0 }}>
          <img
            src={src} alt={caption}
            style={{
              width: '100%', borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.1)',
              boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
              display: 'block',
            }}
          />
          <figcaption style={{
            fontSize: 11, color: '#888', textAlign: 'center',
            marginTop: 6, lineHeight: 1.3,
          }}>
            {caption}
          </figcaption>
        </figure>
      ))}
    </div>
  )
}

function StepList({ steps }) {
  return (
    <ol style={{ margin: '16px 0', paddingLeft: 0, listStyle: 'none' }}>
      {steps.map((s, i) => (
        <li key={i} style={{ display: 'flex', gap: 14, marginBottom: 14, alignItems: 'flex-start' }}>
          <span style={{
            flexShrink: 0, width: 26, height: 26, borderRadius: '50%',
            background: 'rgba(201,162,39,0.18)', border: '1px solid rgba(201,162,39,0.4)',
            color: '#c9a227', fontSize: 13, fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>{i + 1}</span>
          <span style={{ color: '#dde', lineHeight: 1.6 }}>{s}</span>
        </li>
      ))}
    </ol>
  )
}

/* ─── Content ───────────────────────────────────────────────── */

const CONTENT = {
  ru: {
    title:       'Total Hunter — возможности платформы',
    description: 'Тюнинг Картера, автосбор сундуков, учёт Древнего, система РОЙ, склепы и биржи в Total Battle.',
    h1:          'Возможности Total Hunter',
    subtitle:    'Шесть модулей для автоматизации Total Battle — от рутины до клановой аналитики.',

    /* Tuning */
    tune_h2:   '⚙ Тюнинг — автоматизация рутины',
    tune_p1:   'Модуль Тюнинг берёт на себя самые однообразные повторяющиеся действия: отправку Картера и ускорение его маршей. Вам остаётся только играть — бот сделает рутину в фоне.',
    tune_steps: [
      'Бот видит иконку Дозорной башни в панели города и понимает, что Картер вернулся с разведки.',
      'Открывает экран капитанов и нажимает «Исследовать» — Картер снова уходит на разведку.',
      'Пока марш идёт — бот отслеживает его в списке маршей. Видит «Speed up» и открывает панель ускорений.',
      'Автоматически выбирает лучший доступный ускоритель и нажимает «Использовать» — марш завершается быстрее.',
    ],
    tune_screens: [
      { src: '/img/tune_wt_icon.png',    caption: '① Иконка Дозорной башни — сигнал что Картер вернулся' },
      { src: '/img/tune_carter.png',     caption: '② Экран капитанов — бот нажимает «Исследовать»' },
      { src: '/img/tune_speed_up.png',   caption: '③ Список маршей — кнопка Speed up Картера' },
      { src: '/img/tune_march_accel.png',caption: '④ Панель ускорений — бот выбирает и применяет ускоритель' },
    ],
    tune_note: 'Тюнинг работает параллельно с поиском бирж и сбором склепов, не прерывая их.',

    /* Chests */
    chest_h2:   '📦 Сундуки — автоматический учёт клановых подарков',
    chest_p1:   'Модуль Сундуки читает подарки в «Мой клан → Триумфальные подарки», автоматически открывает их и отправляет данные на сервер клана. Лидер клана видит статистику по каждому игроку в реальном времени — кто сколько сундуков принёс и из каких ивентов.',
    chest_steps: [
      'Бот переходит в список кланового подарка «Triumphal Gifts» и находит непрочитанные сундуки.',
      'OCR считывает имя отправителя (поле «From:») — именно так сундук привязывается к конкретному участнику клана.',
      'OCR считывает источник сундука (поле «Source:») — это тип ивента, определяет ценность сундука по таблице очков.',
      'Бот нажимает «Open» — сундук открыт, данные уходят на сервер. Лидер видит обновление мгновенно.',
    ],
    chest_screens: [
      { src: '/img/chest_open.png',   caption: '① Кнопка «Open» — бот открывает каждый сундук' },
      { src: '/img/chest_sender.png', caption: '② «From: Имя» — OCR читает отправителя' },
      { src: '/img/chest_type.png',   caption: '③ «Source: Ивент» — OCR определяет тип сундука' },
    ],
    chest_p2:   'Публичная страница клана показывает сводную таблицу: очки, количество сундуков, прогресс к цели сезона — для каждого участника. История предыдущих сезонов хранится 90 дней.',

    /* Ancient */
    ancient_h2:  '🐲 Древний — контроль квоты урона по клану',
    ancient_p1:  'Модуль Древний помогает лидерам контролировать вклад каждого участника в атаку на клановое чудовище. Руководитель задаёт цель урона — система автоматически рассчитывает индивидуальные квоты исходя из уровня войск каждого игрока.',
    ancient_steps_title: 'Как это работает:',
    ancient_steps: [
      'Лидер клана задаёт общий целевой урон за ивент и тип распределения (равномерно / по силе войск).',
      'Система рассчитывает индивидуальную норму для каждого участника — с учётом уровня войск (G/S/M тиры).',
      'В таблице руководителя видно кто уже выполнил норму, кто в процессе, а кто не начинал — цветом и числами.',
      'Публичная страница клана отображает прогресс в реальном времени — участники сами видят свою норму.',
    ],
    ancient_note: 'Модуль не требует отдельного бота — данные вносятся лидером клана через веб-кабинет.',

    /* ROY */
    roy_h2:   '👥 РОЙ — коллективный пул бирж',
    roy_p1:   'Система РОЙ — уникальная механика коллективной разведки. Охотники, запустившие сканирование бирж, автоматически передают найденные координаты в общую базу королевства. Любой участник РОЯ видит актуальные биржи в реальном времени — без необходимости покупать наёмников самому.',
    roy_p2:   'Чем больше активных охотников в королевстве — тем плотнее покрытие карты. Зелёный кружок рядом с координатами: охотник активен прямо сейчас. Серый — зарегистрирован, но не в сети.',
    roy_p3:   'Расход: 1 алмаз в минуту пока бот ищет. Доход для охотника: 10 алмазов за каждую найденную биржу — участие в РОЕ может полностью покрыть расходы.',

    /* Crypts */
    crypt_h2:  '💀 Склепы — детерминированный сбор без OCR',
    crypt_p1:  'Алгоритм использует формулу T_max / 2ᴺ для точного расчёта времени ожидания — бот не угадывает, а знает когда именно появится следующий склеп. Пустые марши исключены.',
    crypt_p2:  'Не требует OCR — работает при любом разрешении экрана, качестве шрифтов и уровне FPS. Поддерживает браузерную и десктопную версии Total Battle.',
    crypt_p3:  'Сбор продолжается в фоне без участия игрока. Запустил — переключился на другое.',

    /* Exchange */
    exchange_h2: '⚔ Биржи — обход по краю королевства',
    exchange_p1: 'Алгоритм «прибрежной змейки» движется вдоль береговой линии — именно там появляется большинство бирж. Центр карты намеренно пропускается, чтобы не тратить алмазы впустую.',
    exchange_p2: 'Нейросеть YOLO детектирует биржи прямо на скриншоте. При обнаружении бот читает координаты и мгновенно передаёт их в РОЙ-базу (если система РОЙ включена).',
    exchange_p3: 'Расход: 10 алмазов за каждую найденную биржу. Координаты хранятся в истории охот личного кабинета.',

    cta:        'Начать бесплатно — 100 алмазов при регистрации',
    cta_link:   '/download',
    guide_link: '/guide',
    guide_text: 'Читать гайд по установке',
  },

  en: {
    title:       'Total Hunter — Platform Features',
    description: 'Carter tuning, auto chest tracking, Ancient quota, SWARM system, crypts and exchanges in Total Battle.',
    h1:          'Total Hunter Features',
    subtitle:    'Six modules for Total Battle automation — from daily routine to clan analytics.',

    tune_h2:   '⚙ Tuning — routine automation',
    tune_p1:   'The Tuning module handles the most repetitive tasks: sending Carter on exploration and speeding up his marches. You just play — the bot handles the grind in the background.',
    tune_steps: [
      'The bot spots the Watchtower icon in the city panel — Carter has returned from exploration.',
      'It opens the captains screen and clicks "Explore" — Carter is dispatched again immediately.',
      'While the march is active, the bot watches the march list. It finds the "Speed up" button and opens the speedup panel.',
      'It automatically selects the best available speedup and clicks "Use" — march finishes faster.',
    ],
    tune_screens: [
      { src: '/img/tune_wt_icon.png',    caption: '① Watchtower icon — Carter has returned' },
      { src: '/img/tune_carter.png',     caption: '② Captains screen — bot clicks "Explore"' },
      { src: '/img/tune_speed_up.png',   caption: '③ March list — Speed up button for Carter' },
      { src: '/img/tune_march_accel.png',caption: '④ Speedup panel — bot selects and applies it' },
    ],
    tune_note: 'Tuning runs in parallel with exchange hunting and crypt collection without interrupting them.',

    chest_h2:   '📦 Chests — automatic clan gift tracking',
    chest_p1:   'The Chests module reads clan gifts in "My Clan → Triumphal Gifts", opens them automatically, and sends the data to the clan server. The clan leader sees per-player statistics in real time — who brought how many chests and from which events.',
    chest_steps: [
      'The bot opens the "Triumphal Gifts" list and finds unopened chests.',
      'OCR reads the sender name (the "From:" field) — this is how each chest is linked to a specific clan member.',
      'OCR reads the chest source (the "Source:" field) — the event type determines chest value in the scoring table.',
      'The bot clicks "Open" — chest is opened, data is sent to the server instantly.',
    ],
    chest_screens: [
      { src: '/img/chest_open.png',   caption: '① "Open" button — bot opens every chest' },
      { src: '/img/chest_sender.png', caption: '② "From: Name" — OCR reads the sender' },
      { src: '/img/chest_type.png',   caption: '③ "Source: Event" — OCR identifies the chest type' },
    ],
    chest_p2:   'The clan public page shows a summary table: points, chest count, season progress — for each member. History of previous seasons is kept for 90 days.',

    ancient_h2:  '🐲 Ancient — clan damage quota tracking',
    ancient_p1:  'The Ancient module helps leaders track each member\'s contribution to the clan creature attack. The leader sets a damage goal — the system automatically calculates individual quotas based on each player\'s troop level.',
    ancient_steps_title: 'How it works:',
    ancient_steps: [
      'The clan leader sets the total target damage for the event and the distribution method (equal / by troop strength).',
      'The system calculates an individual quota for each member — accounting for troop tiers (G/S/M).',
      'The leader\'s table shows who has met their quota, who is on track, and who hasn\'t started — by color and numbers.',
      'The clan public page shows real-time progress — members can see their own quota.',
    ],
    ancient_note: 'No separate bot required — data is entered by the clan leader through the web dashboard.',

    roy_h2:   '👥 SWARM — collective exchange pool',
    roy_p1:   'The SWARM System is a unique collective intelligence mechanic. Hunters running exchange scans automatically share coordinates to a shared kingdom database. Any SWARM member sees live exchanges in real time — without buying mercenaries themselves.',
    roy_p2:   'More active hunters = denser map coverage. Green circle next to coordinates: hunter is active right now. Grey — registered but offline.',
    roy_p3:   'Cost: 1 diamond per minute while scanning. Revenue for hunters: 10 diamonds per found exchange — SWARM participation can fully cover costs.',

    crypt_h2:  '💀 Crypts — deterministic collection, no OCR',
    crypt_p1:  'The algorithm uses the T_max / 2ᴺ formula for precise timing — the bot knows exactly when the next crypt appears. Empty marches are eliminated.',
    crypt_p2:  'No OCR required — works at any screen resolution, font quality, or FPS. Supports both browser and desktop versions of Total Battle.',
    crypt_p3:  'Collection runs in the background without player involvement. Just start it and switch to something else.',

    exchange_h2: '⚔ Exchanges — coastal kingdom sweep',
    exchange_p1: 'The "coastal snake" algorithm moves along the coastline — most exchanges appear near the shore. The map center is intentionally skipped to avoid wasting diamonds.',
    exchange_p2: 'The YOLO neural network detects exchanges directly on screen. Upon detection, coordinates are read and instantly forwarded to the SWARM pool (if enabled).',
    exchange_p3: 'Cost: 10 diamonds per found exchange. Coordinates are stored in the hunt history in your account.',

    cta:        'Start free — 100 diamonds on registration',
    cta_link:   '/download',
    guide_link: '/guide',
    guide_text: 'Read installation guide',
  },
}

export default function FeaturesPage() {
  const { lang } = useLang()
  const t = CONTENT[lang] ?? CONTENT.ru

  useMeta({ title: t.title, description: t.description })

  return (
    <main style={{ maxWidth: 880, margin: '0 auto', padding: '48px 24px 80px', color: '#e8e8e8', fontFamily: 'inherit', lineHeight: 1.7 }}>

      <h1 style={{ fontSize: 'clamp(1.6rem, 4vw, 2.4rem)', fontWeight: 700, color: '#fff', marginBottom: 10 }}>
        {t.h1}
      </h1>
      <p style={{ fontSize: '1.05rem', color: '#aaa', marginBottom: 52 }}>{t.subtitle}</p>

      {/* ── Тюнинг ─────────────────────────────────────────────── */}
      <Section>
        <SectionTitle>{t.tune_h2}</SectionTitle>
        <Para>{t.tune_p1}</Para>
        <StepList steps={t.tune_steps} />
        <ScreenRow screens={t.tune_screens} />
        <Para muted>{t.tune_note}</Para>
      </Section>

      <Divider />

      {/* ── Сундуки ─────────────────────────────────────────────── */}
      <Section>
        <SectionTitle>{t.chest_h2}</SectionTitle>
        <Para>{t.chest_p1}</Para>
        <StepList steps={t.chest_steps} />
        <ScreenRow screens={t.chest_screens} />
        <Para muted>{t.chest_p2}</Para>
      </Section>

      <Divider />

      {/* ── Древний ─────────────────────────────────────────────── */}
      <Section>
        <SectionTitle>{t.ancient_h2}</SectionTitle>
        <Para>{t.ancient_p1}</Para>
        <StepList steps={t.ancient_steps} />
        <Para muted>{t.ancient_note}</Para>
      </Section>

      <Divider />

      {/* ── РОЙ ─────────────────────────────────────────────────── */}
      <Section>
        <SectionTitle>{t.roy_h2}</SectionTitle>
        <Para>{t.roy_p1}</Para>
        <Para>{t.roy_p2}</Para>
        <Para muted>{t.roy_p3}</Para>
      </Section>

      <Divider />

      {/* ── Склепы ──────────────────────────────────────────────── */}
      <Section>
        <SectionTitle>{t.crypt_h2}</SectionTitle>
        <Para>{t.crypt_p1}</Para>
        <Para>{t.crypt_p2}</Para>
        <Para muted>{t.crypt_p3}</Para>
      </Section>

      <Divider />

      {/* ── Биржи ───────────────────────────────────────────────── */}
      <Section>
        <SectionTitle>{t.exchange_h2}</SectionTitle>
        <Para>{t.exchange_p1}</Para>
        <Para>{t.exchange_p2}</Para>
        <Para muted>{t.exchange_p3}</Para>
      </Section>

      {/* ── CTA ─────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 8 }}>
        <Link to={t.cta_link} style={{
          display: 'inline-block', padding: '14px 32px',
          background: '#c9a227', color: '#111', borderRadius: 8,
          fontWeight: 700, fontSize: '1rem', textDecoration: 'none',
        }}>
          {t.cta}
        </Link>
        <Link to={t.guide_link} style={{
          display: 'inline-block', padding: '14px 32px',
          border: '1px solid #555', color: '#ccc', borderRadius: 8,
          fontWeight: 500, fontSize: '1rem', textDecoration: 'none',
        }}>
          {t.guide_text}
        </Link>
      </div>
    </main>
  )
}
