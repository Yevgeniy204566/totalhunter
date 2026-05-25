import { useMeta } from '../hooks/useMeta.js'
import { useLang } from '../lang.js'
import { Link } from 'react-router-dom'

const CONTENT = {
  ru: {
    title:       'Total Hunter — возможности платформы | Рой, склепы, биржи',
    description: 'Система РОЙ, автосбор склепов и поиск бирж наёмников в Total Battle. Как работает автоматизация — подробно.',
    h1:          'Возможности Total Hunter',
    subtitle:    'Три мощных инструмента для автоматизации Total Battle на одной платформе.',

    roy_h2:      'Система РОЙ — коллективный пул бирж',
    roy_p1:      'Система РОЙ — это уникальная механика коллективной разведки. Искатели, запустившие сканирование бирж, автоматически передают найденные координаты в общую базу данных королевства. Любой участник РОЯ видит актуальные координаты бирж в реальном времени — без необходимости самому покупать наёмников или запускать бота.',
    roy_p2:      'Принцип работы прост: нашёл биржу — координаты мгновенно появляются у всех. Игроки с ограниченным временем или бюджетом получают доступ к живым данным от активных охотников королевства. Чем больше участников в РОЕ — тем плотнее покрытие карты и тем быстрее обновляются данные.',
    roy_p3:      'Зелёный кружок рядом с координатами означает: охотник активен прямо сейчас. Серый — зарегистрирован, но не в сети. Это позволяет моментально оценить актуальность данных.',

    crypt_h2:    'Автосбор склепов — детерминированный алгоритм без OCR',
    crypt_p1:    'Модуль сбора склепов использует детерминированный алгоритм с адаптивным ожиданием. Бот не угадывает — он точно знает сколько ждать до следующего склепа, используя формулу T_max / 2^N, где N — глубина вложенности. Это полностью исключает пустые марши и ложные срабатывания.',
    crypt_p2:    'Не требует распознавания текста (OCR) — работает стабильно при любом разрешении экрана, любом качестве шрифтов и в условиях низкого FPS игры. Поддерживает браузерный клиент Total Battle и десктопную версию.',
    crypt_p3:    'Ключевое преимущество: сбор продолжается в фоне без участия игрока. Достаточно запустить бота и переключиться на другие дела — результаты появятся в истории охот.',

    exchange_h2: 'Поиск бирж наёмников — обход по краю королевства',
    exchange_p1: 'Алгоритм поиска бирж построен на принципе "прибрежной змейки": бот движется вдоль береговой линии королевства, максимально покрывая зону появления бирж. Именно у берега появляется большинство бирж наёмников — алгоритм учитывает это и избегает бесполезного сканирования центра карты.',
    exchange_p2: 'Нейросеть YOLO детектирует биржи прямо на скриншоте экрана с высокой точностью. При обнаружении бот автоматически открывает диалог, читает координаты и передаёт их в ROY-базу (если включена система РОЙ) или сохраняет локально.',
    exchange_p3: 'Расход: 10 алмазов за каждую найденную биржу. Все найденные координаты доступны в истории охот в личном кабинете.',

    cta:         'Начать бесплатно — 100 алмазов при регистрации',
    cta_link:    '/download',
    guide_link:  '/guide',
    guide_text:  'Читать гайд по установке',
  },
  en: {
    title:       'Total Hunter — Platform Features | Swarm, Crypts, Exchanges',
    description: 'SWARM system, auto-crypt collection, and mercenary exchange hunting in Total Battle. How automation works — in detail.',
    h1:          'Total Hunter Features',
    subtitle:    'Three powerful tools for Total Battle automation on one platform.',

    roy_h2:      'SWARM System — Collective Exchange Pool',
    roy_p1:      'The SWARM System is a unique collective intelligence mechanic. Scouts who have launched exchange scanning automatically share found coordinates to a shared kingdom database. Any SWARM member sees live exchange coordinates in real time — without needing to buy mercenaries or run the bot themselves.',
    roy_p2:      'The principle is simple: find an exchange — coordinates instantly appear for everyone. Players with limited time or budget get access to live data from active kingdom hunters. The more SWARM members — the denser the map coverage and the faster data updates.',
    roy_p3:      'A green circle next to coordinates means: the hunter is active right now. Grey — registered but offline. This lets you instantly assess data freshness.',

    crypt_h2:    'Auto Crypt Collection — Deterministic Algorithm, No OCR',
    crypt_p1:    'The crypt collection module uses a deterministic algorithm with adaptive waiting. The bot does not guess — it knows exactly how long to wait for the next crypt using the formula T_max / 2^N, where N is nesting depth. This completely eliminates empty marches and false triggers.',
    crypt_p2:    'No text recognition (OCR) required — works stably at any screen resolution, any font quality, and under low game FPS. Supports both browser and desktop versions of Total Battle.',
    crypt_p3:    'Key advantage: collection continues in the background without player involvement. Just launch the bot and switch to other tasks — results appear in the hunt history.',

    exchange_h2: 'Mercenary Exchange Hunting — Coastal Kingdom Sweep',
    exchange_p1: 'The exchange hunting algorithm is built on the "coastal snake" principle: the bot moves along the kingdom\'s coastline, maximally covering the exchange spawn zone. Most mercenary exchanges appear near the coast — the algorithm accounts for this and avoids pointless scanning of the map center.',
    exchange_p2: 'The YOLO neural network detects exchanges directly on screen screenshots with high accuracy. Upon detection, the bot automatically opens the dialog, reads coordinates and forwards them to the ROY base (if SWARM is enabled) or saves them locally.',
    exchange_p3: 'Cost: 10 diamonds per found exchange. All found coordinates are available in the hunt history in your personal account.',

    cta:         'Start free — 100 diamonds on registration',
    cta_link:    '/download',
    guide_link:  '/guide',
    guide_text:  'Read installation guide',
  },
}

export default function FeaturesPage() {
  const { lang } = useLang()
  const t = CONTENT[lang] ?? CONTENT.ru

  useMeta({ title: t.title, description: t.description })

  return (
    <main style={{ maxWidth: 860, margin: '0 auto', padding: '48px 24px 80px', color: '#e8e8e8', fontFamily: 'inherit', lineHeight: 1.7 }}>

      <h1 style={{ fontSize: 'clamp(1.6rem, 4vw, 2.4rem)', fontWeight: 700, color: '#fff', marginBottom: 12 }}>
        {t.h1}
      </h1>
      <p style={{ fontSize: '1.1rem', color: '#aaa', marginBottom: 48 }}>{t.subtitle}</p>

      {/* ROY */}
      <section style={{ marginBottom: 56 }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#c9a227', marginBottom: 16 }}>
          {t.roy_h2}
        </h2>
        <p style={{ marginBottom: 14 }}>{t.roy_p1}</p>
        <p style={{ marginBottom: 14 }}>{t.roy_p2}</p>
        <p style={{ color: '#bbb' }}>{t.roy_p3}</p>
      </section>

      {/* Crypts */}
      <section style={{ marginBottom: 56 }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#c9a227', marginBottom: 16 }}>
          {t.crypt_h2}
        </h2>
        <p style={{ marginBottom: 14 }}>{t.crypt_p1}</p>
        <p style={{ marginBottom: 14 }}>{t.crypt_p2}</p>
        <p style={{ color: '#bbb' }}>{t.crypt_p3}</p>
      </section>

      {/* Exchange */}
      <section style={{ marginBottom: 56 }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#c9a227', marginBottom: 16 }}>
          {t.exchange_h2}
        </h2>
        <p style={{ marginBottom: 14 }}>{t.exchange_p1}</p>
        <p style={{ marginBottom: 14 }}>{t.exchange_p2}</p>
        <p style={{ color: '#bbb' }}>{t.exchange_p3}</p>
      </section>

      {/* CTA */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 16 }}>
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
