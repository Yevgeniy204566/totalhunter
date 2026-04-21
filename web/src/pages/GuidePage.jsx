import { Link } from 'react-router-dom'
import { isLoggedIn } from '../auth.js'

const SECTIONS = [
  { id: 'how-it-works', label: 'Как работает' },
  { id: 'install',      label: 'Установка' },
  { id: 'calibration',  label: 'Калибровка' },
  { id: 'modes',        label: 'Режимы охоты' },
  { id: 'credits',      label: 'Кредиты' },
  { id: 'referrals',    label: 'Рефералы' },
  { id: 'faq',          label: 'FAQ' },
]

const PACKAGES = [
  { name: 'Lite',  price: '$1',  credits: '300',   bonus: '',     color: '#64B5F6' },
  { name: 'Pro',   price: '$5',  credits: '2 000', bonus: '+33%', color: 'var(--accent)' },
  { name: 'Ultra', price: '$10', credits: '5 000', bonus: '+66%', color: 'var(--credits-gold)', popular: true },
]

const FAQ = [
  { q: 'Нужно ли оставлять компьютер включённым?',
    a: 'Да. Бот управляет мышью в реальном времени — компьютер должен быть активен и экран разблокирован.' },
  { q: 'Что такое HWID и зачем он нужен?',
    a: 'Hardware ID — уникальный идентификатор твоего компьютера. Триал (300 кредитов) выдаётся один раз на устройство для защиты от злоупотреблений.' },
  { q: 'Кредиты тратятся при ошибке бота?',
    a: 'Нет. Кредиты списываются только при подтверждённой находке объекта. Сканирование и повторные попытки — бесплатно.' },
  { q: 'Можно перенести аккаунт на другой ПК?',
    a: 'Да. В личном кабинете → раздел «Устройства» можно отвязать старое устройство и привязать новое.' },
  { q: 'Могут забанить за использование бота?',
    a: 'Бот имитирует действия человека с рандомными паузами (0.4–0.9 с) и смещением кликов (±5–8 пx). Риск минимален, но ненулевой — используй осознанно.' },
]

function Section({ id, icon, title, children }) {
  return (
    <section id={id} style={{ marginBottom: 64 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: 'rgba(61,127,255,0.1)', border: '1px solid rgba(61,127,255,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
          flexShrink: 0,
        }}>
          {icon}
        </div>
        <h2 style={{ fontSize: 22, fontWeight: 800, color: '#FFFFFF', margin: 0 }}>{title}</h2>
      </div>
      {children}
    </section>
  )
}

function Card({ children, style }) {
  return (
    <div style={{
      background: 'var(--elevated)', border: '1px solid var(--outline)',
      borderRadius: 14, padding: '24px 28px', ...style,
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
      }}>
        {n}
      </div>
      <div>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{title}</div>
        <div style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.7 }}>{desc}</div>
        {note && (
          <div style={{
            marginTop: 8, padding: '7px 12px', borderRadius: 8, fontSize: 12,
            background: 'rgba(61,127,255,0.07)', border: '1px solid rgba(61,127,255,0.18)',
            color: '#A0B8D8',
          }}>
            {note}
          </div>
        )}
      </div>
    </div>
  )
}

export default function GuidePage() {
  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>

      {/* Nav */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: 'rgba(5, 8, 16, 0.92)',
        backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--outline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 32px', height: 64,
        boxShadow: '0 2px 32px var(--accent-glow)',
      }}>
        <Link to="/" style={{
          display: 'flex', alignItems: 'center', gap: 10,
          textDecoration: 'none', fontWeight: 700, fontSize: 18,
        }}>
          <span style={{ color: 'var(--accent)', fontSize: 20 }}>⚔</span>
          <span style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>Total</span>
          <span style={{ color: '#FFFFFF' }}>Hunter</span>
        </Link>
        <Link
          to={isLoggedIn() ? '/dashboard' : '/login'}
          style={{
            padding: '9px 22px', borderRadius: 8, fontSize: 14,
            background: 'var(--accent)', color: '#FFFFFF',
            fontWeight: 700, textDecoration: 'none',
            boxShadow: '0 0 14px var(--accent-glow)',
          }}
        >
          {isLoggedIn() ? 'Dashboard →' : 'Войти'}
        </Link>
      </nav>

      {/* Hero */}
      <div style={{
        padding: '64px 24px 48px',
        background: 'radial-gradient(ellipse 80% 50% at 50% 0%, rgba(61,127,255,0.1) 0%, transparent 60%)',
        borderBottom: '1px solid var(--outline)',
        textAlign: 'center',
      }}>
        <div style={{
          display: 'inline-block', padding: '5px 16px', borderRadius: 20,
          background: 'rgba(61,127,255,0.1)', border: '1px solid rgba(61,127,255,0.3)',
          fontSize: 11, fontWeight: 700, letterSpacing: '1.5px',
          color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 20,
        }}>
          Документация
        </div>
        <h1 style={{
          fontSize: 'clamp(32px, 5vw, 54px)', fontWeight: 800,
          color: '#FFFFFF', marginBottom: 16, letterSpacing: '-1px',
        }}>
          Руководство пользователя
        </h1>
        <p style={{
          fontSize: 17, color: '#C8D8F0', maxWidth: 560, margin: '0 auto',
          lineHeight: 1.7,
        }}>
          Полное описание работы Total Hunter — от установки до первой находки.
        </p>
      </div>

      {/* Layout: TOC + Content */}
      <div style={{
        maxWidth: 1060, margin: '0 auto', padding: '48px 24px',
        display: 'grid', gridTemplateColumns: '220px 1fr', gap: 48,
        alignItems: 'start',
      }}>

        {/* Sidebar TOC */}
        <div style={{ position: 'sticky', top: 80 }}>
          <div style={{
            background: 'var(--elevated)', border: '1px solid var(--outline)',
            borderRadius: 14, padding: '20px',
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '1.5px', color: 'var(--accent)', textTransform: 'uppercase', marginBottom: 16 }}>
              Содержание
            </div>
            {SECTIONS.map(({ id, label }) => (
              <a key={id} href={`#${id}`} style={{
                display: 'block', padding: '7px 10px', borderRadius: 8,
                fontSize: 13, color: 'var(--on-surface2)', textDecoration: 'none',
                fontWeight: 500, transition: 'color 0.15s, background 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = '#FFFFFF'; e.currentTarget.style.background = 'rgba(61,127,255,0.08)' }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--on-surface2)'; e.currentTarget.style.background = 'transparent' }}
              >
                {label}
              </a>
            ))}
          </div>
        </div>

        {/* Main content */}
        <div>

          {/* 1. How it works */}
          <Section id="how-it-works" icon="🧠" title="Как работает Total Hunter">
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.85, marginBottom: 20 }}>
                Total Hunter — десктопный бот-помощник для игры <strong style={{ color: '#FFFFFF' }}>Total Battle</strong>.
                Он автоматически сканирует карту королевства и находит два типа объектов с добычей:
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                {[
                  { icon: '⚔', color: 'var(--accent)', name: 'Биржа (Exchange)', desc: 'Точка обмена редких ресурсов. Появляется случайно. Кто первый — тот победил.' },
                  { icon: '💀', color: '#B060FF', name: 'Склеп (Crypt)', desc: 'Тёмная локация с богатой добычей. Требует марша армии и ожидания.' },
                ].map(({ icon, color, name, desc }) => (
                  <div key={name} style={{
                    padding: '16px', borderRadius: 12,
                    background: `${color}0D`, border: `1px solid ${color}33`,
                  }}>
                    <div style={{ fontSize: 22, marginBottom: 8 }}>{icon}</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 6 }}>{name}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{desc}</div>
                  </div>
                ))}
              </div>
            </Card>
            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 14, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                Алгоритм навигации
              </div>
              {[
                { step: '1', text: 'Читает мини-карту (120×120 px) через захват экрана' },
                { step: '2', text: 'Находит центроид воды → вычисляет направление к берегу' },
                { step: '3', text: 'Движется перпендикулярно берегу, покрывая карту «змейкой»' },
                { step: '4', text: 'YOLOv8 нейросеть детектирует Биржи и Склепы на экране' },
                { step: '5', text: 'При находке — кликает, атакует, списывает кредиты' },
              ].map(({ step, text }) => (
                <div key={step} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 12 }}>
                  <div style={{
                    width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
                    background: 'rgba(61,127,255,0.15)', border: '1px solid rgba(61,127,255,0.3)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 11, fontWeight: 700, color: 'var(--accent)',
                  }}>{step}</div>
                  <div style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.6, paddingTop: 3 }}>{text}</div>
                </div>
              ))}
            </Card>
          </Section>

          {/* 2. Install */}
          <Section id="install" icon="⬇" title="Установка">
            <Card>
              <div style={{
                padding: '12px 16px', borderRadius: 10, marginBottom: 24,
                background: 'rgba(255,209,102,0.07)', border: '1px solid rgba(255,209,102,0.25)',
                fontSize: 13, color: '#FFD166',
              }}>
                ⚠ Требования: Windows 10/11 x64 · Разрешение 1920×1080 · 4 ГБ RAM · Активный аккаунт Total Battle
              </div>
              <Step n="1" title="Регистрация"
                desc="Зайди на totalhunter.pro и войди через Google-аккаунт. Аккаунт создаётся автоматически."
              />
              <Step n="2" title="Триал кредиты"
                desc="В Dashboard нажми «Получить триал» — 300 бесплатных кредитов зачисляются мгновенно."
                note="Триал выдаётся один раз на устройство (HWID-верификация)"
              />
              <Step n="3" title="Скачай бот"
                desc="Ссылка на TotalHunter.exe появится в личном кабинете после активации триала."
              />
              <Step n="4" title="Запусти"
                desc="Дважды кликни по TotalHunter.exe. Python и все зависимости включены — дополнительная установка не нужна."
              />
              <Step n="5" title="Авторизация в боте"
                desc="При первом запуске введи тот же Google-аккаунт. Бот подключится к серверу и загрузит твои кредиты."
              />
            </Card>
          </Section>

          {/* 3. Calibration */}
          <Section id="calibration" icon="🎯" title="Калибровка">
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 20 }}>
                Калибровка нужна один раз — бот должен знать, где на твоём экране джойстик и мини-карта.
                Займёт <strong style={{ color: '#FFFFFF' }}>30 секунд</strong>.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 20 }}>
                {[
                  { label: 'Точка A', desc: 'Центр джойстика — круглая кнопка управления картой (обычно внизу слева)', color: 'var(--accent)' },
                  { label: 'Точка B', desc: 'Правый верхний угол мини-карты', color: '#B060FF' },
                ].map(({ label, desc, color }) => (
                  <div key={label} style={{
                    padding: '16px', borderRadius: 12,
                    background: `${color}0D`, border: `1px solid ${color}33`,
                  }}>
                    <div style={{ fontSize: 15, fontWeight: 700, color, marginBottom: 8 }}>{label}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{desc}</div>
                    {/* Место для скриншота */}
                    <div style={{
                      marginTop: 12, height: 80, borderRadius: 8,
                      background: 'rgba(255,255,255,0.03)', border: '1px dashed rgba(255,255,255,0.1)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, color: 'rgba(255,255,255,0.2)',
                    }}>
                      [скриншот]
                    </div>
                  </div>
                ))}
              </div>
              <Step n="1" title="Открой игру" desc="Запусти Total Battle в браузере (полный экран или без границ окна)." />
              <Step n="2" title="Вкладка КАЛИБРОВКА" desc="В боте перейди на вкладку КАЛИБРОВКА." />
              <Step n="3" title="Установи точку A" desc='Нажми "Установить точку A" → кликни на центр джойстика в игре.' />
              <Step n="4" title="Установи точку B" desc='Нажми "Установить точку B" → кликни на правый верхний угол мини-карты.' />
              <Step n="5" title="Сохрани профиль" desc='Нажми "Сохранить профиль". Калибровка запомнится навсегда.' />
            </Card>
          </Section>

          {/* 4. Modes */}
          <Section id="modes" icon="⚡" title="Режимы охоты">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              {[
                {
                  icon: '⚔', color: 'var(--accent)', name: 'Биржи',
                  cost: '5 кредитов / находка',
                  params: ['Дальность: чем выше — шире зона поиска', 'Скорость: рекомендуется максимум'],
                  tip: 'Биржи — редкие. Выставь скорость на максимум, чтобы не уступить другим игрокам.',
                },
                {
                  icon: '💀', color: '#B060FF', name: 'Склепы',
                  cost: '1 кредит / находка',
                  params: ['Дальность марша: минимальное расстояние до склепа', 'Ускорение 0–5: уровень ускорения армии'],
                  tip: 'Склепы дешевле. Хороший режим для фарма когда бирж мало.',
                },
              ].map(({ icon, color, name, cost, params, tip }) => (
                <Card key={name}>
                  <div style={{ fontSize: 24, marginBottom: 12 }}>{icon}</div>
                  <div style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF', marginBottom: 6 }}>{name}</div>
                  <div style={{
                    display: 'inline-block', padding: '3px 10px', borderRadius: 20,
                    background: `${color}15`, border: `1px solid ${color}33`,
                    fontSize: 12, color, fontWeight: 600, marginBottom: 16,
                  }}>
                    {cost}
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--on-surface2)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>
                    Параметры
                  </div>
                  {params.map(p => (
                    <div key={p} style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.7 }}>· {p}</div>
                  ))}
                  <div style={{
                    marginTop: 16, padding: '10px 12px', borderRadius: 8,
                    background: 'rgba(61,127,255,0.06)', border: '1px solid rgba(61,127,255,0.15)',
                    fontSize: 12, color: '#A0B8D8', lineHeight: 1.6,
                  }}>
                    💡 {tip}
                  </div>
                </Card>
              ))}
            </div>
            <Card style={{ marginTop: 14 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.7, margin: 0 }}>
                <strong style={{ color: '#FFFFFF' }}>Экстренная остановка:</strong> нажми <kbd style={{
                  padding: '2px 8px', borderRadius: 5, background: 'rgba(255,255,255,0.1)',
                  border: '1px solid rgba(255,255,255,0.2)', fontSize: 13, fontWeight: 700,
                }}>ESC</kbd> — бот немедленно прекращает все действия.
              </p>
            </Card>
          </Section>

          {/* 5. Credits */}
          <Section id="credits" icon="💎" title="Кредиты и пакеты">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 16 }}>
              {PACKAGES.map(({ name, price, credits, bonus, color, popular }) => (
                <Card key={name} style={{
                  textAlign: 'center', position: 'relative',
                  border: popular ? `1px solid ${color}55` : '1px solid var(--outline)',
                  boxShadow: popular ? `0 0 24px ${color}18` : 'none',
                }}>
                  {popular && (
                    <div style={{
                      position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                      padding: '3px 12px', borderRadius: 20,
                      background: color, color: '#000', fontSize: 10, fontWeight: 800,
                      whiteSpace: 'nowrap', letterSpacing: '0.5px',
                    }}>
                      ЛУЧШИЙ ВЫБОР
                    </div>
                  )}
                  <div style={{ fontSize: 28, fontWeight: 800, color, marginBottom: 4 }}>{price}</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{name}</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color, marginBottom: 4 }}>{credits}</div>
                  <div style={{ fontSize: 12, color: 'var(--on-surface2)' }}>кредитов</div>
                  {bonus && (
                    <div style={{
                      marginTop: 10, padding: '3px 10px', borderRadius: 20, display: 'inline-block',
                      background: `${color}18`, border: `1px solid ${color}33`,
                      fontSize: 12, color, fontWeight: 700,
                    }}>
                      {bonus}
                    </div>
                  )}
                </Card>
              ))}
            </div>
            <Card>
              <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
                {[
                  { label: 'Биржа найдена', cost: '−5 кредитов', color: 'var(--accent)' },
                  { label: 'Склеп найден', cost: '−1 кредит', color: '#B060FF' },
                  { label: 'Объект не найден', cost: 'бесплатно', color: 'var(--on-surface2)' },
                  { label: 'Триал при регистрации', cost: '+300 кредитов', color: 'var(--credits-gold)' },
                ].map(({ label, cost, color }) => (
                  <div key={label}>
                    <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color }}>{cost}</div>
                  </div>
                ))}
              </div>
            </Card>
          </Section>

          {/* 6. Referrals */}
          <Section id="referrals" icon="◈" title="Реферальная система">
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 24 }}>
                Приглашай друзей и получай <strong style={{ color: '#FFFFFF' }}>процент от каждой их покупки навсегда</strong>.
                Реферальная система работает на 3 уровня.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                {[
                  { level: 'L1', pct: '10%', desc: 'Прямые рефералы', color: 'var(--credits-gold)' },
                  { level: 'L2', pct: '5%',  desc: 'Рефералы реферала', color: 'var(--accent)' },
                  { level: 'L3', pct: '1%',  desc: '3-й уровень',       color: '#B060FF' },
                ].map(({ level, pct, desc, color }) => (
                  <div key={level} style={{
                    textAlign: 'center', padding: '20px 12px',
                    borderRadius: 12, background: `${color}0D`,
                    border: `1px solid ${color}33`,
                  }}>
                    <div style={{ fontSize: 11, color, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', marginBottom: 8 }}>{level}</div>
                    <div style={{ fontSize: 32, fontWeight: 800, color, lineHeight: 1, marginBottom: 8 }}>{pct}</div>
                    <div style={{ fontSize: 12, color: 'var(--on-surface2)' }}>{desc}</div>
                  </div>
                ))}
              </div>
              <div style={{
                marginTop: 20, padding: '12px 16px', borderRadius: 10,
                background: 'rgba(61,127,255,0.06)', border: '1px solid rgba(61,127,255,0.15)',
                fontSize: 13, color: '#A0B8D8', lineHeight: 1.6,
              }}>
                💡 Реферальную ссылку найдёшь в разделе <strong style={{ color: '#FFFFFF' }}>«Рефералы»</strong> личного кабинета.
                Кредиты зачисляются автоматически сразу после покупки реферала.
              </div>
            </Card>
          </Section>

          {/* 7. FAQ */}
          <Section id="faq" icon="❓" title="Частые вопросы">
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
            background: 'var(--elevated)', border: '1px solid var(--outline)',
            borderRadius: 20,
            boxShadow: '0 0 48px rgba(61,127,255,0.06)',
          }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: '#FFFFFF', marginBottom: 12 }}>
              Готов начать охоту?
            </div>
            <p style={{ fontSize: 14, color: 'var(--on-surface2)', marginBottom: 28, lineHeight: 1.7 }}>
              300 кредитов бесплатно при регистрации. Никакой кредитки не нужно.
            </p>
            <Link
              to={isLoggedIn() ? '/dashboard' : '/login'}
              style={{
                display: 'inline-block', padding: '14px 40px', borderRadius: 10,
                background: 'var(--accent)', color: '#FFFFFF',
                fontSize: 16, fontWeight: 700, textDecoration: 'none',
                boxShadow: '0 0 24px var(--accent-glow)',
              }}
            >
              {isLoggedIn() ? 'Перейти в Dashboard →' : 'Начать бесплатно →'}
            </Link>
          </div>

        </div>
      </div>
    </div>
  )
}
