import { Link } from 'react-router-dom'
import { isLoggedIn } from '../auth.js'

// ── Diamond icon (gradient ◆) ────────────────────────────────────────────────
function Diamond({ size = 28, style = {} }) {
  return (
    <span style={{
      fontSize: size, lineHeight: 1,
      background: 'linear-gradient(135deg, #B060FF 0%, #3D7FFF 50%, #00CFFF 100%)',
      WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
      backgroundClip: 'text',
      filter: 'drop-shadow(0 0 8px rgba(61,127,255,0.7))',
      display: 'inline-block', ...style,
    }}>◆</span>
  )
}

const SECTIONS = [
  { id: 'what-is',      label: 'Что такое Total Hunter' },
  { id: 'algorithm',   label: 'Алгоритм поиска' },
  { id: 'requirements',label: 'Требования' },
  { id: 'install',     label: 'Установка' },
  { id: 'calibration', label: 'Калибровка' },
  { id: 'modes',       label: 'Режимы работы' },
  { id: 'credits',     label: 'Алмазы и тарифы' },
  { id: 'referrals',   label: 'Рефералы' },
  { id: 'security',    label: 'Безопасность' },
  { id: 'faq',         label: 'FAQ' },
]

const PACKAGES = [
  { name: 'Lite',  price: '$1',  diamonds: '300',   bonus: '',              color: '#64B5F6' },
  { name: 'Pro',   price: '$5',  diamonds: '2 000', bonus: '+33%',          color: '#3D7FFF' },
  { name: 'Ultra', price: '$10', diamonds: '5 000', bonus: 'МАКС. ВЫГОДА',  color: '#00CFFF', popular: true },
]

const FAQ = [
  { q: 'Можно ли пользоваться компьютером, пока работает бот?',
    a: 'Так как бот управляет курсором мыши и клавиатурой, рекомендуем запускать его в то время, когда вы не пользуетесь ПК, либо использовать отдельный ноутбук.' },
  { q: 'Нужен ли боту доступ к моему игровому паролю?',
    a: 'Нет. Бот работает поверх уже запущенной вами игры. Нам не нужны учётные данные от Total Battle — безопасность вашего аккаунта гарантирована.' },
  { q: 'Что такое HWID и зачем он нужен?',
    a: 'Hardware ID — уникальный «отпечаток» вашего компьютера. Лицензия и бесплатный триал привязываются к железу, чтобы исключить злоупотребления.' },
  { q: 'Можно ли перенести аккаунт на другой ПК?',
    a: 'Да. Зайдите в Личный кабинет → раздел «Устройства», отвяжите старый HWID и авторизуйтесь на новом устройстве.' },
  { q: 'Как работают алмазы при ошибке или сбое интернета?',
    a: 'Алмазы списываются только за успешный результат (нахождение Биржи или отправку Картера в Склеп). Если бот не нашёл объект или произошёл сбой — ваш баланс останется прежним.' },
  { q: 'Могут ли меня забанить?',
    a: 'Мы внедрили все возможные методы маскировки: рандомизация пауз (0.4–0.9 с) и случайное отклонение кликов (±5–8 пкс). Риск минимален, однако любое использование стороннего ПО несёт теоретические риски. Используйте бота разумно.' },
]

function Section({ id, icon, title, children }) {
  return (
    <section id={id} style={{ marginBottom: 64 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: 'rgba(61,127,255,0.1)', border: '1px solid rgba(61,127,255,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0,
        }}>
          {icon}
        </div>
        <h2 style={{ fontSize: 22, fontWeight: 800, color: '#FFFFFF', margin: 0 }}>{title}</h2>
      </div>
      {children}
    </section>
  )
}

function Card({ children, style, glow }) {
  return (
    <div style={{
      background: 'var(--elevated)', border: '1px solid var(--outline)',
      borderRadius: 14, padding: '24px 28px',
      boxShadow: glow ? `0 0 32px ${glow}` : 'none',
      ...style,
    }}>
      {children}
    </div>
  )
}

// Карточка с неоновой рамкой (для симметричных пар)
function NeonCard({ children, color, style }) {
  return (
    <div style={{
      borderRadius: 14, padding: '20px',
      background: `${color}08`,
      border: `1px solid ${color}44`,
      boxShadow: `0 0 18px ${color}18`,
      ...style,
    }}>
      {children}
    </div>
  )
}

function Step({ n, title, desc, note }) {
  return (
    <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
        background: 'rgba(61,127,255,0.15)', border: '1px solid rgba(61,127,255,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontWeight: 700, color: 'var(--accent)',
      }}>{n}</div>
      <div>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{title}</div>
        <div style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.7 }}>{desc}</div>
        {note && (
          <div style={{
            marginTop: 8, padding: '7px 12px', borderRadius: 8, fontSize: 12,
            background: 'rgba(61,127,255,0.07)', border: '1px solid rgba(61,127,255,0.18)',
            color: '#A0B8D8',
          }}>{note}</div>
        )}
      </div>
    </div>
  )
}

function Note({ children }) {
  return (
    <div style={{
      padding: '12px 16px', borderRadius: 10, marginTop: 16,
      background: 'rgba(255,209,102,0.07)', border: '1px solid rgba(255,209,102,0.25)',
      fontSize: 13, color: '#FFD166', lineHeight: 1.6,
    }}>{children}</div>
  )
}

export default function GuidePage() {
  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>

      {/* Nav */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: 'rgba(5,8,16,0.92)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--outline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 32px', height: 64,
        boxShadow: '0 2px 32px var(--accent-glow)',
      }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', fontWeight: 700, fontSize: 18 }}>
          <Diamond size={22} />
          <span style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>Total</span>
          <span style={{ color: '#FFFFFF' }}>Hunter</span>
        </Link>
        <Link to={isLoggedIn() ? '/dashboard' : '/login'} style={{
          padding: '9px 22px', borderRadius: 8, fontSize: 14,
          background: 'var(--accent)', color: '#FFFFFF', fontWeight: 700, textDecoration: 'none',
          boxShadow: '0 0 14px var(--accent-glow)',
        }}>
          {isLoggedIn() ? 'Dashboard →' : 'Войти'}
        </Link>
      </nav>

      {/* Hero */}
      <div style={{
        padding: '64px 24px 48px',
        background: 'radial-gradient(ellipse 80% 50% at 50% 0%, rgba(61,127,255,0.1) 0%, transparent 60%)',
        borderBottom: '1px solid var(--outline)', textAlign: 'center',
      }}>
        <div style={{
          display: 'inline-block', padding: '5px 16px', borderRadius: 20,
          background: 'rgba(61,127,255,0.1)', border: '1px solid rgba(61,127,255,0.3)',
          fontSize: 11, fontWeight: 700, letterSpacing: '1.5px', color: 'var(--accent)',
          textTransform: 'uppercase', marginBottom: 20,
        }}>Документация</div>
        <h1 style={{ fontSize: 'clamp(32px,5vw,54px)', fontWeight: 800, color: '#FFFFFF', marginBottom: 16, letterSpacing: '-1px' }}>
          Руководство пользователя
        </h1>
        <p style={{ fontSize: 17, color: '#C8D8F0', maxWidth: 560, margin: '0 auto', lineHeight: 1.7 }}>
          Полное описание работы Total Hunter — от установки до первой находки.
        </p>
      </div>

      {/* Layout: TOC + Content */}
      <div style={{
        maxWidth: 1060, margin: '0 auto', padding: '48px 24px',
        display: 'grid', gridTemplateColumns: '220px 1fr', gap: 48, alignItems: 'start',
      }}>

        {/* Sidebar TOC */}
        <div style={{ position: 'sticky', top: 80 }}>
          <div style={{ background: 'var(--elevated)', border: '1px solid var(--outline)', borderRadius: 14, padding: '20px' }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '1.5px', color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 16 }}>
              Содержание
            </div>
            {SECTIONS.map(({ id, label }) => (
              <a key={id} href={`#${id}`} style={{
                display: 'block', padding: '7px 10px', borderRadius: 8,
                fontSize: 13, color: 'var(--on-surface2)', textDecoration: 'none', fontWeight: 500,
              }}
              onMouseEnter={e => { e.currentTarget.style.color='#FFFFFF'; e.currentTarget.style.background='rgba(61,127,255,0.08)' }}
              onMouseLeave={e => { e.currentTarget.style.color='var(--on-surface2)'; e.currentTarget.style.background='transparent' }}
              >{label}</a>
            ))}
          </div>
        </div>

        {/* Main content */}
        <div>

          {/* 1. Что такое Total Hunter */}
          <Section id="what-is" icon={<Diamond size={18}/>} title="Что такое Total Hunter">
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.85, marginBottom: 20 }}>
                <strong style={{ color: '#FFFFFF' }}>Total Hunter</strong> — десктопный бот-помощник для автоматизации
                игровых процессов в <strong style={{ color: '#FFFFFF' }}>Total Battle</strong>. Программа берёт на себя
                рутинный поиск и взаимодействие с объектами на карте:
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <NeonCard color="#00CFFF">
                  <div style={{ fontSize: 22, marginBottom: 8 }}>🔍</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 6 }}>Биржа (Exchange)</div>
                  <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>
                    Бот сканирует береговые линии королевств для обнаружения рынков наёмников. При нахождении цели подаёт звуковой сигнал и останавливает поиск.
                  </div>
                </NeonCard>
                <NeonCard color="#B060FF">
                  <div style={{ fontSize: 22, marginBottom: 8 }}>🏆</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 6 }}>Склеп (Crypt)</div>
                  <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>
                    Бот находит в меню выбранные типы склепов (Обычные, Редкие, Эпические) и отправляет вашего «Картера» для сбора, используя ускорения марша.
                  </div>
                </NeonCard>
              </div>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginTop: 20, marginBottom: 0 }}>
                Программа работает поверх браузера или клиента Total Battle, полностью имитируя действия реального пользователя.
              </p>
            </Card>
          </Section>

          {/* 2. Алгоритм поиска */}
          <Section id="algorithm" icon="🧠" title="Алгоритм поиска">
            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 14, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                Smart Coastline Scouting — интеллектуальный сканер побережья
              </div>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 16 }}>
                Для максимально эффективного обхода территорий бот использует уникальный алгоритм <strong style={{ color: '#FFFFFF' }}>«Прибрежная змея»</strong>,
                имитирующий логику опытного разведчика:
              </p>
              {[
                { n: '1', title: 'Анализ местности', desc: 'Бот в реальном времени считывает мини-карту, определяя границы воды и суши.' },
                { n: '2', title: 'Вектор движения', desc: 'Программа вычисляет траекторию, перпендикулярную берегу, для эффективного прочёсывания прибрежных зон.' },
                { n: '3', title: 'Интеллектуальные фазы', desc: 'Homing — движение к цели. Diving — глубокое сканирование территории. Returning — безопасный возврат к берегу.' },
                { n: '4', title: 'Стабилизация (EMA)', desc: 'Система сглаживания убирает «дрожание» курсора, делая движения бота плавными и естественными.' },
              ].map(s => <Step key={s.n} {...s} />)}
              <p style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.7, marginBottom: 0 }}>
                Благодаря двухточечной калибровке, управление автоматически адаптируется под любое разрешение монитора.
              </p>
            </Card>

            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 14, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                Детекция объектов — нейросеть
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                <NeonCard color="#00CFFF">
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>Модель «Биржа»</div>
                  <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>
                    Безошибочно распознаёт рынок наёмников на любом фоне. При обнаружении бот мгновенно реагирует и подаёт сигнал.
                  </div>
                </NeonCard>
                <NeonCard color="#B060FF">
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>Модель «Склепы»</div>
                  <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>
                    Идентифицирует нужные типы склепов для организации непрерывного автоматического сбора.
                  </div>
                </NeonCard>
              </div>
              <p style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.7, marginBottom: 0 }}>
                Как только нейросеть подтверждает цель, бот кликает по объекту, открывает меню и отправляет марш.
              </p>
            </Card>

            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 14, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                Автоматизация сбора Склепов
              </div>
              <Step n="1" title="Обнаружение" desc="Бот находит нужный Склеп через нейросеть и открывает его игровое меню." />
              <Step n="2" title="Расчёт времени"
                desc="Дальность марша: время хода Картера до самого дальнего склепа (в минутах). Ускорение 0–5: каждый уровень сокращает время вдвое." />
              <Step n="3" title="Цикл ожидания"
                desc="Программа рассчитывает время туда+обратно и добавляет Добавочную паузу (до 300 с). Бот ждёт гарантированного возврата Картера." />
              <Step n="4" title="Сброс списка"
                desc="Если список склепов закончился — автоматический сброс через вкладку «Арена», после чего цикл продолжается." />
            </Card>
          </Section>

          {/* 3. Требования */}
          <Section id="requirements" icon="💻" title="Технические требования">
            <Card>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  { param: 'ОС',          value: 'Windows 10 / 11 (64-bit)' },
                  { param: 'Разрешение',  value: '1920×1080 (Full HD) — для идеальной точности' },
                  { param: 'Браузер',     value: 'Chrome, Firefox или официальный клиент Total Battle' },
                  { param: 'ОЗУ',         value: 'от 4 ГБ и выше' },
                  { param: 'Сеть',        value: 'Постоянное соединение (для проверки лицензии)' },
                  { param: 'Аккаунт',     value: 'Активный игровой профиль Total Battle' },
                ].map(({ param, value }) => (
                  <div key={param} style={{
                    display: 'flex', gap: 16, padding: '10px 14px', borderRadius: 8,
                    background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', minWidth: 100, flexShrink: 0 }}>{param}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{value}</div>
                  </div>
                ))}
              </div>
            </Card>
          </Section>

          {/* 4. Установка */}
          <Section id="install" icon="⬇" title="Быстрый старт: Установка и запуск">
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 24 }}>
                Весь процесс от регистрации до первой «охоты» занимает не более <strong style={{ color: '#FFFFFF' }}>5 минут</strong>.
              </p>
              <Step n="1" title="Регистрация" desc="Создайте аккаунт на TotalHunter.pro, используя Google-аккаунт." />
              <Step n="2" title="Бесплатные алмазы"
                desc="Получите 100 бесплатных алмазов в Личном кабинете (Dashboard) — сразу проверьте бота."
                note="Триал выдаётся один раз на устройство (HWID-верификация)" />
              <Step n="3" title="Загрузка" desc="Скачайте TotalHunter.exe по ссылке в личном кабинете." />
              <Step n="4" title="Запуск" desc="Запустите файл. Python и нейросетевые модели уже включены — дополнительная установка не нужна." />
              <Step n="5" title="Авторизация" desc="Войдите в приложение через Google (те же данные, что и на сайте)." />
              <Step n="6" title="Настройка" desc="После входа бот предложит перейти на вкладку КАЛИБРОВКА для адаптации под ваш монитор." />
            </Card>
          </Section>

          {/* 5. Калибровка */}
          <Section id="calibration" icon="🎯" title="Калибровка экрана (Обязательный шаг)">
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 20 }}>
                Необходимо один раз настроить <strong style={{ color: '#FFFFFF' }}>две опорные точки</strong>.
                Откройте игру именно так, как привыкли играть — бот запомнит эти настройки.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 24 }}>
                {[
                  { label: 'Точка A', sublabel: 'Центр мини-карты', color: '#00CFFF',
                    desc: 'Уменьшите зум мини-карты до минимума. Кликните точно по центру прямоугольника мини-карты.',
                    img: '/img/calib_point_a.png' },
                  { label: 'Точка B', sublabel: 'Зона ресурсов — Серебро', color: '#B060FF',
                    desc: 'Найдите иконку Серебра, наведите курсор до появления «+». Кликните точно по символу «+».',
                    img: '/img/calib_point_b.png' },
                ].map(({ label, sublabel, color, desc, img }) => (
                  <NeonCard key={label} color={color}>
                    <div style={{ fontSize: 15, fontWeight: 700, color, marginBottom: 2 }}>{label}</div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--on-surface2)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>{sublabel}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.65, marginBottom: 10 }}>{desc}</div>
                    <img src={img} alt={label} style={{ width: '100%', borderRadius: 8, border: `1px solid ${color}33`, display: 'block' }} />
                  </NeonCard>
                ))}
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 14, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                Шаги калибровки
              </div>
              <Step n="1" title="Откройте игру" desc="Запустите Total Battle: браузер, полный экран или клиент." />
              <Step n="2" title="Вкладка КАЛИБРОВКА" desc="В боте перейдите на вкладку КАЛИБРОВКА." />
              <Step n="3" title="Установите точку A" desc='Уменьшите зум мини-карты. Нажмите «Установить точку A» → кликните по центру мини-карты.' />
              <Step n="4" title="Установите точку B" desc='Найдите иконку Серебра, наведите до появления «+». Нажмите «Установить точку B» → кликните по «+».' />
              <Step n="5" title="Сохраните профиль" desc='Выберите слот и нажмите «Сохранить профиль».' />
              <div style={{
                padding: '12px 16px', borderRadius: 10, marginTop: 8,
                background: 'rgba(61,127,255,0.06)', border: '1px solid rgba(61,127,255,0.15)',
                fontSize: 13, color: '#A0B8D8', lineHeight: 1.7,
              }}>
                💡 <strong style={{ color: '#FFFFFF' }}>3 слота:</strong> Слот 1 — клиент игры, Слот 2 — браузер (вариант 1), Слот 3 — браузер (вариант 2).
              </div>
            </Card>
          </Section>

          {/* 6. Режимы */}
          <Section id="modes" icon="⚡" title="Режимы работы">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <NeonCard color="#00CFFF">
                <div style={{ fontSize: 24, marginBottom: 10 }}>🔍</div>
                <div style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>Охота на Биржи</div>
                <div style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 20, marginBottom: 14, background: 'rgba(0,207,255,0.15)', border: '1px solid rgba(0,207,255,0.3)', fontSize: 12, color: '#00CFFF', fontWeight: 600 }}>
                  5 алмазов / находка
                </div>
                {[
                  { l: 'Логика', t: 'Непрерывное сканирование береговой линии по алгоритму «змейка».' },
                  { l: 'Результат', t: 'Звуковой сигнал + остановка → вы выкупаете войска вручную.' },
                  { l: 'Настройки', t: '«Дальность» 100%, «Скорость» на максимум.' },
                ].map(({ l, t }) => (
                  <div key={l} style={{ marginBottom: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#00CFFF' }}>{l}: </span>
                    <span style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{t}</span>
                  </div>
                ))}
              </NeonCard>
              <NeonCard color="#B060FF">
                <div style={{ fontSize: 24, marginBottom: 10 }}>🏆</div>
                <div style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>Сбор Склепов</div>
                <div style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 20, marginBottom: 14, background: 'rgba(176,96,255,0.15)', border: '1px solid rgba(176,96,255,0.3)', fontSize: 12, color: '#B060FF', fontWeight: 600 }}>
                  1 алмаз / находка
                </div>
                {[
                  { l: 'Логика', t: 'Бот находит склепы в меню и отправляет Картера.' },
                  { l: 'Цикл', t: 'Ждёт возвращения Картера по рассчитанному времени.' },
                  { l: 'Параметры', t: 'Дальность марша (мин) + Ускорение (0–5 уровней).' },
                ].map(({ l, t }) => (
                  <div key={l} style={{ marginBottom: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#B060FF' }}>{l}: </span>
                    <span style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{t}</span>
                  </div>
                ))}
              </NeonCard>
            </div>
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.7, margin: 0 }}>
                <strong style={{ color: '#FFFFFF' }}>Экстренная остановка:</strong> нажмите{' '}
                <kbd style={{ padding: '2px 8px', borderRadius: 5, background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', fontSize: 13, fontWeight: 700 }}>ESC</kbd>
                {' '}— бот мгновенно прекращает все действия.
              </p>
            </Card>
          </Section>

          {/* 7. Алмазы */}
          <Section id="credits" icon={<Diamond size={18}/>} title="Алмазы и тарифы">
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 0 }}>
                В системе Total Hunter используются <strong style={{ color: '#FFFFFF' }}>◆ алмазы</strong> — внутренняя валюта,
                которая расходуется только за успешные действия бота.
              </p>
            </Card>

            {/* Packages — gambling style */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 16 }}>
              {PACKAGES.map(({ name, price, diamonds, bonus, color, popular }) => (
                <div key={name} style={{
                  position: 'relative', borderRadius: 16, padding: '28px 20px', textAlign: 'center',
                  background: popular
                    ? 'linear-gradient(160deg, rgba(0,207,255,0.08) 0%, rgba(61,127,255,0.12) 50%, rgba(176,96,255,0.08) 100%)'
                    : 'var(--elevated)',
                  border: `1px solid ${color}55`,
                  boxShadow: popular ? `0 0 40px ${color}30, 0 0 80px ${color}10` : `0 0 12px ${color}10`,
                }}>
                  {popular && (
                    <div style={{
                      position: 'absolute', top: -14, left: '50%', transform: 'translateX(-50%)',
                      padding: '4px 16px', borderRadius: 20,
                      background: `linear-gradient(90deg, #B060FF, #3D7FFF, #00CFFF)`,
                      color: '#FFF', fontSize: 10, fontWeight: 800, whiteSpace: 'nowrap', letterSpacing: '1px',
                    }}>ЛУЧШИЙ ВЫБОР</div>
                  )}
                  <div style={{ fontSize: 32, fontWeight: 900, color, marginBottom: 2,
                    textShadow: popular ? `0 0 20px ${color}` : 'none' }}>{price}</div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#FFFFFF', marginBottom: 8 }}>{name}</div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, marginBottom: 4 }}>
                    <Diamond size={popular ? 22 : 18} />
                    <span style={{ fontSize: popular ? 28 : 22, fontWeight: 900, color,
                      textShadow: popular ? `0 0 16px ${color}` : 'none' }}>{diamonds}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: bonus ? 12 : 0 }}>алмазов</div>
                  {bonus && (
                    <div style={{
                      display: 'inline-block', padding: '4px 12px', borderRadius: 20,
                      background: `linear-gradient(90deg, ${color}22, ${color}44)`,
                      border: `1px solid ${color}55`, fontSize: 12, color, fontWeight: 800,
                    }}>{bonus}</div>
                  )}
                </div>
              ))}
            </div>

            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 16, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                Расход алмазов
              </div>
              <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', marginBottom: 20 }}>
                {[
                  { label: 'Найдена Биржа', cost: '−5 алмазов', color: '#00CFFF' },
                  { label: 'Сбор Склепа',   cost: '−1 алмаз',   color: '#B060FF' },
                  { label: 'Не найдено',    cost: 'бесплатно',  color: 'var(--on-surface2)' },
                  { label: 'Триал',         cost: '+100 алмазов', color: 'var(--credits-gold)' },
                ].map(({ label, cost, color }) => (
                  <div key={label}>
                    <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color }}>{cost}</div>
                  </div>
                ))}
              </div>
              <Note>
                ⚠ <strong>Бесплатный триал:</strong> каждый новый пользователь получает <strong>100 алмазов</strong> после регистрации.
                Привязка к HWID — один раз на устройство.
              </Note>
            </Card>
          </Section>

          {/* 8. Рефералы */}
          <Section id="referrals" icon="◈" title="Реферальная система">
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 28 }}>
                Приглашайте игроков и получайте <strong style={{ color: '#FFFFFF' }}>процент от каждой их покупки навсегда</strong>.
                Трёхуровневая реферальная цепочка.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 24 }}>
                {[
                  { level: 'L1', pct: '10%', desc: 'Ваши друзья',      color: '#FFD166' },
                  { level: 'L2', pct: '5%',  desc: 'Их рефералы',      color: '#00CFFF' },
                  { level: 'L3', pct: '1%',  desc: 'Следующий круг',   color: '#B060FF' },
                ].map(({ level, pct, desc, color }) => (
                  <div key={level} style={{
                    textAlign: 'center', padding: '24px 12px', borderRadius: 14,
                    background: `${color}0A`, border: `1px solid ${color}44`,
                    boxShadow: `0 0 20px ${color}14`,
                  }}>
                    <div style={{ fontSize: 13, color, fontWeight: 800, letterSpacing: '2px', textTransform: 'uppercase', marginBottom: 10 }}>{level}</div>
                    <div style={{ fontSize: 44, fontWeight: 900, color, lineHeight: 1, marginBottom: 10,
                      textShadow: `0 0 20px ${color}` }}>{pct}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)' }}>{desc}</div>
                  </div>
                ))}
              </div>
              <div style={{
                padding: '14px 16px', borderRadius: 10,
                background: 'rgba(61,127,255,0.06)', border: '1px solid rgba(61,127,255,0.15)',
                fontSize: 13, color: '#A0B8D8', lineHeight: 1.6,
              }}>
                💡 Алмазы зачисляются мгновенно после оплаты реферала.
                Реферальную ссылку найдёте в разделе <strong style={{ color: '#FFFFFF' }}>«Рефералы»</strong> личного кабинета.
              </div>
            </Card>
          </Section>

          {/* 9. Безопасность */}
          <Section id="security" icon="🛡" title="Безопасность и анти-бан">
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 20 }}>
                <strong style={{ color: '#FFFFFF' }}>Total Hunter</strong> спроектирован так, чтобы его действия были неотличимы от поведения опытного игрока:
              </p>
              {[
                { icon: '⏱', title: 'Случайные паузы', desc: 'Между каждым движением — пауза 0.4–0.9 с, генерируется случайным образом.' },
                { icon: '🖱', title: 'Имитация руки', desc: 'Каждый клик имеет случайное смещение ±5–8 пкс — полная имитация человеческой руки.' },
                { icon: '🛑', title: 'Экстренная остановка', desc: 'Клавиша ESC — мгновенная остановка бота и возврат управления вам.' },
                { icon: '🔒', title: 'Прямое взаимодействие', desc: 'Бот работает только с открытым окном игры, без скрытых API-запросов.' },
              ].map(({ icon, title, desc }) => (
                <div key={title} style={{
                  display: 'flex', gap: 14, marginBottom: 14, padding: '14px',
                  borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
                }}>
                  <div style={{ fontSize: 20, flexShrink: 0 }}>{icon}</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{title}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.65 }}>{desc}</div>
                  </div>
                </div>
              ))}
            </Card>
          </Section>

          {/* 10. FAQ */}
          <Section id="faq" icon="❓" title="Часто задаваемые вопросы">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {FAQ.map(({ q, a }) => (
                <Card key={q}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#FFFFFF', marginBottom: 8 }}>{q}</div>
                  <div style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.75 }}>{a}</div>
                </Card>
              ))}
            </div>
          </Section>

          {/* CTA */}
          <div style={{
            textAlign: 'center', padding: '48px 32px',
            background: 'linear-gradient(160deg, rgba(0,207,255,0.06) 0%, rgba(61,127,255,0.08) 50%, rgba(176,96,255,0.06) 100%)',
            border: '1px solid rgba(61,127,255,0.25)', borderRadius: 20,
            boxShadow: '0 0 60px rgba(61,127,255,0.08)',
          }}>
            <Diamond size={48} style={{ marginBottom: 16 }} />
            <div style={{ fontSize: 22, fontWeight: 800, color: '#FFFFFF', marginBottom: 12 }}>
              Готов начать охоту?
            </div>
            <p style={{ fontSize: 14, color: 'var(--on-surface2)', marginBottom: 28, lineHeight: 1.7 }}>
              100 алмазов бесплатно при регистрации. Никакой кредитки не нужно.
            </p>
            <Link to={isLoggedIn() ? '/dashboard' : '/login'} style={{
              display: 'inline-block', padding: '14px 40px', borderRadius: 10,
              background: 'linear-gradient(90deg, #3D7FFF, #00CFFF)',
              color: '#FFFFFF', fontSize: 16, fontWeight: 700, textDecoration: 'none',
              boxShadow: '0 0 30px rgba(0,207,255,0.35)',
            }}>
              {isLoggedIn() ? 'Перейти в Dashboard →' : 'Начать бесплатно →'}
            </Link>
          </div>

        </div>
      </div>
    </div>
  )
}
