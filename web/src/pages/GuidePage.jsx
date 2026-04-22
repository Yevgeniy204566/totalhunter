import { Link } from 'react-router-dom'
import { isLoggedIn } from '../auth.js'

const SECTIONS = [
  { id: 'what-is',      label: 'Что такое Total Hunter' },
  { id: 'algorithm',   label: 'Алгоритм поиска' },
  { id: 'requirements',label: 'Требования' },
  { id: 'install',     label: 'Установка' },
  { id: 'calibration', label: 'Калибровка' },
  { id: 'modes',       label: 'Режимы работы' },
  { id: 'credits',     label: 'Экономика и тарифы' },
  { id: 'referrals',   label: 'Рефералы' },
  { id: 'security',    label: 'Безопасность' },
  { id: 'faq',         label: 'FAQ' },
]

const PACKAGES = [
  { name: 'Lite',  price: '$1',  credits: '300',   bonus: '',              color: '#64B5F6' },
  { name: 'Pro',   price: '$5',  credits: '2 000', bonus: '+33%',          color: 'var(--accent)' },
  { name: 'Ultra', price: '$10', credits: '5 000', bonus: '+66% Макс. выгода', color: 'var(--credits-gold)', popular: true },
]

const FAQ = [
  {
    q: 'Можно ли пользоваться компьютером, пока работает бот?',
    a: 'Так как бот управляет курсором мыши и клавиатурой, мы рекомендуем запускать его в то время, когда вы не пользуетесь ПК, либо использовать для этого отдельный ноутбук.',
  },
  {
    q: 'Нужен ли боту доступ к моему игровому паролю?',
    a: 'Нет. Бот работает поверх уже запущенной вами игры. Нам не нужны ваши учётные данные от Total Battle — безопасность вашего аккаунта гарантирована.',
  },
  {
    q: 'Что такое HWID и зачем он нужен?',
    a: 'Hardware ID — это уникальный «отпечаток» вашего компьютера. Лицензия и бесплатный триал привязываются к вашему железу, чтобы исключить злоупотребления и обеспечить честное использование софта.',
  },
  {
    q: 'Можно ли перенести аккаунт на другой ПК?',
    a: 'Да. Если вы сменили компьютер, зайдите в Личный кабинет на сайте в раздел «Устройства», отвяжите старый HWID и авторизуйтесь на новом устройстве.',
  },
  {
    q: 'Как работают кредиты при ошибке или сбое интернета?',
    a: 'Кредиты списываются только за успешный результат (нахождение Биржи или отправку Картера в Склеп). Если бот не нашёл объект или произошёл сбой связи до фиксации цели — ваш баланс останется прежним.',
  },
  {
    q: 'Могут ли меня забанить?',
    a: 'Мы внедрили все возможные методы маскировки (рандомизация пауз, отклонение кликов). Это делает риск минимальным, однако мы обязаны предупредить: любое использование стороннего ПО в играх несёт в себе теоретические риски. Используйте бота разумно.',
  },
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

function Note({ children, color = 'rgba(255,209,102,0.07)', border = 'rgba(255,209,102,0.25)', textColor = '#FFD166' }) {
  return (
    <div style={{
      padding: '12px 16px', borderRadius: 10, marginTop: 16,
      background: color, border: `1px solid ${border}`,
      fontSize: 13, color: textColor, lineHeight: 1.6,
    }}>
      {children}
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

          {/* 1. Что такое Total Hunter */}
          <Section id="what-is" icon="🎮" title="Что такое Total Hunter">
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.85, marginBottom: 20 }}>
                <strong style={{ color: '#FFFFFF' }}>Total Hunter</strong> — это десктопный бот-помощник для автоматизации
                игровых процессов в <strong style={{ color: '#FFFFFF' }}>Total Battle</strong>. Программа берёт на себя
                рутинный поиск и взаимодействие с объектами на карте:
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                {[
                  {
                    icon: '⚔',
                    color: 'var(--accent)',
                    name: 'Биржа (Exchange)',
                    desc: 'Бот сканирует береговые линии королевств для обнаружения рынков наёмников. При нахождении цели подаёт звуковой сигнал и автоматически останавливает поиск.',
                  },
                  {
                    icon: '💀',
                    color: '#B060FF',
                    name: 'Склеп (Crypt)',
                    desc: 'Бот находит в игровом меню выбранные вами типы склепов (Обычные, Редкие или Эпические) и автоматически отправляет на их местоположение вашего «Картера» для сбора, используя ускорения марша.',
                  },
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
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginTop: 20, marginBottom: 0 }}>
                Программа работает поверх окна браузера или официального игрового клиента. Бот полностью имитирует
                действия реального пользователя, управляя курсором мыши и клавиатурой, что обеспечивает
                естественность и безопасность автоматизации.
              </p>
            </Card>
          </Section>

          {/* 2. Алгоритм поиска */}
          <Section id="algorithm" icon="🧠" title="Алгоритм поиска (The Core)">
            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 16, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                2.1 Навигация по карте — CoastalSnakeNavigator
              </div>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 16 }}>
                Для максимально эффективного обхода территорий бот использует уникальный алгоритм <strong style={{ color: '#FFFFFF' }}>«Прибрежная змея»</strong> (CoastalSnakeNavigator),
                который имитирует логику опытного разведчика:
              </p>
              {[
                { n: '1', title: 'Анализ местности', desc: 'Бот в реальном времени считывает мини-карту, определяя границы воды и суши.' },
                { n: '2', title: 'Вектор движения', desc: 'Программа вычисляет траекторию, перпендикулярную берегу, чтобы эффективно прочёсывать прибрежные зоны в поисках Бирж.' },
                { n: '3', title: 'Интеллектуальные фазы', desc: 'Поиск (Homing) — движение к цели с постоянной корректировкой курса. Глубокое сканирование (Diving) — проход вглубь территории. Возврат (Returning) — безопасный выход обратно к береговой линии.' },
                { n: '4', title: 'Стабилизация', desc: 'Система сглаживания (EMA) убирает «дрожание» курсора, делая движения бота плавными и естественными, как у человека.' },
              ].map(s => <Step key={s.n} {...s} />)}
              <p style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.7, marginTop: 8, marginBottom: 0 }}>
                Благодаря двухточечной калибровке, управление джойстиком автоматически адаптируется под любое разрешение вашего монитора.
              </p>
            </Card>

            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 16, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                2.2 Детекция объектов — Нейросеть
              </div>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 16 }}>
                Total Hunter не просто ищет цвета на экране — он «видит» объекты с помощью нейросетевых моделей,
                обученных специально под графику Total Battle:
              </p>
              {[
                { icon: '⚔', color: 'var(--accent)', name: 'Модель «Биржа»', desc: 'Безошибочно распознаёт рынок наёмников на любом фоне. При обнаружении бот мгновенно реагирует и подаёт звуковой сигнал.' },
                { icon: '💀', color: '#B060FF', name: 'Модель «Склепы»', desc: 'Идентифицирует нужные типы склепов для организации непрерывного сбора.' },
              ].map(({ icon, color, name, desc }) => (
                <div key={name} style={{
                  display: 'flex', gap: 14, marginBottom: 14, padding: '14px',
                  borderRadius: 10, background: `${color}0A`, border: `1px solid ${color}22`,
                }}>
                  <div style={{ fontSize: 20, flexShrink: 0 }}>{icon}</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>{name}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{desc}</div>
                  </div>
                </div>
              ))}
              <p style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.7, marginBottom: 0 }}>
                Как только нейросеть подтверждает цель, бот переходит к активным действиям: кликает по объекту, открывает меню и отправляет марш по заданным вами параметрам.
              </p>
            </Card>

            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 16, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                2.3 Автоматизация сбора Склепов
              </div>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 16 }}>
                Процесс сбора полностью автоматизирован и базируется на точных настройках вашего аккаунта:
              </p>
              <Step n="1" title="Обнаружение" desc="Бот находит нужный Склеп на экране с помощью нейросети и открывает его игровое меню." />
              <Step n="2" title="Интеллектуальная система расчёта времени"
                desc="Дальность марша: вы задаёте время (в минутах), которое требуется вашему «Картеру», чтобы дойти до самого дальнего склепа в Королевстве. Ускорение марша: слайдер (0–5) — каждое деление сокращает расчётное время пути ровно в два раза."
              />
              <Step n="3" title="Безопасный цикл ожидания"
                desc="Программа рассчитывает время пути в обе стороны и добавляет Добавочную паузу (до 300 секунд). Это гарантирует, что бот начнёт поиск следующей цели только после того, как Картер гарантированно вернётся в город."
              />
              <Step n="4" title="Сброс списка"
                desc="Если список доступных склепов в меню закончился, бот выполняет автоматический сброс через переход на вкладку «Арена», после чего продолжает цикл поиска."
              />
              <Note>
                ⚠ <strong>Важное условие:</strong> для корректной работы функции на аккаунте должно быть не менее <strong>70 000 единиц масла</strong>. Если запас опустится ниже этого порога, бот автоматически прекратит сбор.
              </Note>
            </Card>
          </Section>

          {/* 3. Технические требования */}
          <Section id="requirements" icon="💻" title="Технические требования">
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 20 }}>
                Для стабильной работы нейросетевых алгоритмов и корректного захвата экрана ваш ПК должен соответствовать следующим характеристикам:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  { param: 'ОС', value: 'Windows 10 / 11 (64-bit)' },
                  { param: 'Разрешение', value: '1920×1080 (Full HD) — для идеальной точности' },
                  { param: 'Браузер', value: 'Chrome, Firefox или официальный клиент Total Battle' },
                  { param: 'ОЗУ', value: 'от 4 ГБ и выше' },
                  { param: 'Сеть', value: 'Постоянное соединение (для проверки лицензии и связи с API)' },
                  { param: 'Аккаунт', value: 'Наличие активного игрового профиля Total Battle' },
                ].map(({ param, value }) => (
                  <div key={param} style={{
                    display: 'flex', gap: 16, alignItems: 'flex-start',
                    padding: '10px 14px', borderRadius: 8,
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
              <Step n="1" title="Регистрация"
                desc="Создайте аккаунт на сайте TotalHunter.pro, используя ваш Google-аккаунт."
              />
              <Step n="2" title="Тестовый период"
                desc="Получите 100 бесплатных кредитов в Личном кабинете (Dashboard), чтобы сразу проверить бота в деле."
                note="Триал выдаётся один раз на устройство (HWID-верификация)"
              />
              <Step n="3" title="Загрузка"
                desc="Скачайте актуальную версию TotalHunter.exe по ссылке в вашем кабинете."
              />
              <Step n="4" title="Запуск"
                desc="Запустите файл. Установка дополнительных библиотек не требуется — Python и нейросетевые модели уже включены в сборку."
              />
              <Step n="5" title="Авторизация"
                desc="Войдите в приложение через Google (используйте те же данные, что и на сайте)."
              />
              <Step n="6" title="Настройка"
                desc="После входа бот сразу предложит перейти на вкладку КАЛИБРОВКА для адаптации под ваш монитор."
              />
            </Card>
          </Section>

          {/* 5. Калибровка */}
          <Section id="calibration" icon="🎯" title="Калибровка экрана (Обязательный шаг)">
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 20 }}>
                Чтобы нейросеть и система навигации точно считывали координаты на вашем мониторе, необходимо один раз
                настроить <strong style={{ color: '#FFFFFF' }}>две опорные точки</strong>. Это адаптирует бота под ваш привычный режим игры.
              </p>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 20 }}>
                <strong style={{ color: '#FFFFFF' }}>Подготовка:</strong> Откройте игру именно так, как вы привыкли в неё играть
                (в окне браузера, в полноэкранном режиме или через клиент). Бот запомнит эти настройки.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 24 }}>
                {[
                  {
                    label: 'Точка A',
                    sublabel: 'Центр мини-карты',
                    desc: 'В игре максимально отдалите зум на мини-карте (уменьшите масштаб до минимума), затем кликните ровно по центру прямоугольника мини-карты.',
                    color: 'var(--accent)',
                  },
                  {
                    label: 'Точка B',
                    sublabel: 'Зона ресурсов — Серебро',
                    desc: 'Найдите в интерфейсе игры иконку Серебра. Наведите на неё курсор, чтобы появился символ «+». Кликните точно по этому символу.',
                    color: '#B060FF',
                  },
                ].map(({ label, sublabel, desc, color }) => (
                  <div key={label} style={{
                    padding: '16px', borderRadius: 12,
                    background: `${color}0D`, border: `1px solid ${color}33`,
                  }}>
                    <div style={{ fontSize: 15, fontWeight: 700, color, marginBottom: 2 }}>{label}</div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--on-surface2)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>{sublabel}</div>
                    <div style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.65 }}>{desc}</div>
                    <img
                      src={label === 'Точка A' ? '/img/calib_point_a.png' : '/img/calib_point_b.png'}
                      alt={label}
                      style={{ marginTop: 12, width: '100%', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)', display: 'block' }}
                    />
                  </div>
                ))}
              </div>

              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 14, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                Шаги калибровки
              </div>
              <Step n="1" title="Откройте игру" desc="Запустите Total Battle именно так, как привыкли играть (браузер, полный экран или клиент)." />
              <Step n="2" title="Вкладка КАЛИБРОВКА" desc="В боте перейдите на вкладку КАЛИБРОВКА." />
              <Step n="3" title="Установите точку A" desc='Уменьшите зум мини-карты до минимума. Нажмите «Установить точку A» → расположите перекрестие по центру мини-карты и кликните.' />
              <Step n="4" title="Установите точку B" desc='Найдите иконку Серебра, наведите курсор до появления «+». Нажмите «Установить точку B» → кликните по символу «+».' />
              <Step n="5" title="Сохраните профиль" desc='Выберите нужный слот и нажмите «Сохранить профиль». Теперь бот полностью синхронизирован с вашим экраном.' />

              <div style={{
                marginTop: 8, padding: '14px 16px', borderRadius: 10,
                background: 'rgba(61,127,255,0.06)', border: '1px solid rgba(61,127,255,0.15)',
                fontSize: 13, color: '#A0B8D8', lineHeight: 1.7,
              }}>
                💡 <strong style={{ color: '#FFFFFF' }}>3 слота памяти:</strong> Слот 1 — клиент игры, Слот 2 — браузер (вариант 1), Слот 3 — браузер (вариант 2). Удобно, если вы играете в разных режимах.
              </div>
            </Card>
          </Section>

          {/* 6. Режимы работы */}
          <Section id="modes" icon="⚡" title="Режимы работы">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
              <Card>
                <div style={{ fontSize: 24, marginBottom: 12 }}>⚔</div>
                <div style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>Охота на Биржи (Exchange)</div>
                <div style={{
                  display: 'inline-block', padding: '3px 10px', borderRadius: 20, marginBottom: 16,
                  background: 'rgba(61,127,255,0.15)', border: '1px solid rgba(61,127,255,0.3)',
                  fontSize: 12, color: 'var(--accent)', fontWeight: 600,
                }}>
                  5 кредитов / находка
                </div>
                {[
                  { label: 'Логика', text: 'Программа непрерывно сканирует береговую линию по алгоритму «змейка».' },
                  { label: 'Результат', text: 'При обнаружении Биржи бот подаёт громкий звуковой сигнал и мгновенно останавливает поиск, чтобы вы могли вручную выкупить нужные войска.' },
                  { label: 'Настройки', text: '«Дальность» — 100% (для полного охвата королевства), «Скорость» — на максимум.' },
                ].map(({ label, text }) => (
                  <div key={label} style={{ marginBottom: 10 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)' }}>{label}: </span>
                    <span style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{text}</span>
                  </div>
                ))}
              </Card>

              <Card>
                <div style={{ fontSize: 24, marginBottom: 12 }}>💀</div>
                <div style={{ fontSize: 17, fontWeight: 700, color: '#FFFFFF', marginBottom: 4 }}>Сбор Склепов (Crypt)</div>
                <div style={{
                  display: 'inline-block', padding: '3px 10px', borderRadius: 20, marginBottom: 16,
                  background: 'rgba(176,96,255,0.15)', border: '1px solid rgba(176,96,255,0.3)',
                  fontSize: 12, color: '#B060FF', fontWeight: 600,
                }}>
                  1 кредит / находка
                </div>
                {[
                  { label: 'Логика', text: 'Бот самостоятельно находит в игровом меню выбранные вами типы склепов и отправляет на них вашего Картера.' },
                  { label: 'Цикл', text: 'После отправки марша бот ждёт возвращения Картера в город (время = Дальность ÷ 2^Ускорение × 2 + ваша пауза), после чего ищет следующую цель.' },
                  { label: 'Параметры', text: '«Дальность марша» (время хода Картера до самой дальней точки в минутах) и «Ускорение» (0–5 уровней).' },
                ].map(({ label, text }) => (
                  <div key={label} style={{ marginBottom: 10 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#B060FF' }}>{label}: </span>
                    <span style={{ fontSize: 13, color: 'var(--on-surface2)', lineHeight: 1.6 }}>{text}</span>
                  </div>
                ))}
                <Note color="rgba(176,96,255,0.07)" border="rgba(176,96,255,0.25)" textColor="#C090FF">
                  Требуется не менее 70 000 единиц масла на аккаунте.
                </Note>
              </Card>
            </div>

            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.7, margin: 0 }}>
                <strong style={{ color: '#FFFFFF' }}>Экстренная остановка:</strong> нажмите <kbd style={{
                  padding: '2px 8px', borderRadius: 5, background: 'rgba(255,255,255,0.1)',
                  border: '1px solid rgba(255,255,255,0.2)', fontSize: 13, fontWeight: 700,
                }}>ESC</kbd> — бот мгновенно прекращает все действия и возвращает управление вам.
              </p>
            </Card>
          </Section>

          {/* 7. Экономика и тарифы */}
          <Section id="credits" icon="💎" title="Экономика и тарифы">
            <Card style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 0 }}>
                В системе Total Hunter используются <strong style={{ color: '#FFFFFF' }}>кредиты</strong> — внутренняя валюта,
                которая расходуется только за успешные действия бота.
              </p>
            </Card>
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
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', marginBottom: 16, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                Расход кредитов
              </div>
              <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', marginBottom: 20 }}>
                {[
                  { label: 'Найдена Биржа', cost: '−5 кредитов', color: 'var(--accent)' },
                  { label: 'Сбор Склепа', cost: '−1 кредит', color: '#B060FF' },
                  { label: 'Объект не найден', cost: 'бесплатно', color: 'var(--on-surface2)' },
                  { label: 'Триал при регистрации', cost: '+100 кредитов', color: 'var(--credits-gold)' },
                ].map(({ label, cost, color }) => (
                  <div key={label}>
                    <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color }}>{cost}</div>
                  </div>
                ))}
              </div>
              <Note>
                ⚠ <strong>Бесплатный период (Trial):</strong> каждый новый пользователь получает <strong>100 бесплатных кредитов</strong> сразу после регистрации.
                Система триала привязана к идентификатору вашего оборудования (HWID) — бесплатный пакет выдаётся один раз на один компьютер.
              </Note>
            </Card>
          </Section>

          {/* 8. Реферальная система */}
          <Section id="referrals" icon="◈" title="Реферальная система (Multi-Level)">
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 24 }}>
                Зарабатывайте вместе с Total Hunter, приглашая других игроков. Вы будете получать <strong style={{ color: '#FFFFFF' }}>процент от каждого пополнения баланса</strong> вашими рефералами на постоянной основе.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
                {[
                  { level: 'L1', pct: '10%', desc: 'Ваши друзья', color: 'var(--credits-gold)' },
                  { level: 'L2', pct: '5%',  desc: 'Рефералы друзей', color: 'var(--accent)' },
                  { level: 'L3', pct: '1%',  desc: 'Следующий круг',  color: '#B060FF' },
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
                padding: '12px 16px', borderRadius: 10,
                background: 'rgba(61,127,255,0.06)', border: '1px solid rgba(61,127,255,0.15)',
                fontSize: 13, color: '#A0B8D8', lineHeight: 1.6,
              }}>
                💡 Реферальные вознаграждения зачисляются на ваш баланс мгновенно в виде кредитов сразу после оплаты заказа вашим рефералом.
                Реферальную ссылку найдёте в разделе <strong style={{ color: '#FFFFFF' }}>«Рефералы»</strong> личного кабинета.
              </div>
            </Card>
          </Section>

          {/* 9. Безопасность */}
          <Section id="security" icon="🛡" title="Безопасность и анти-бан">
            <Card>
              <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.8, marginBottom: 20 }}>
                <strong style={{ color: '#FFFFFF' }}>Total Hunter</strong> спроектирован так, чтобы его действия были неотличимы
                от поведения опытного игрока. Мы используем многоуровневую систему защиты:
              </p>
              {[
                {
                  icon: '⏱',
                  title: 'Случайные паузы',
                  desc: 'Между каждым движением и кликом бот выдерживает паузу от 0.4 до 0.9 секунды, которая генерируется случайным образом.',
                },
                {
                  icon: '🖱',
                  title: 'Имитация руки (Human Click)',
                  desc: 'Бот никогда не кликает в одну и ту же точку дважды. Каждое нажатие имеет случайное смещение в ±5–8 пикселей, что полностью имитирует естественное дрожание человеческой руки.',
                },
                {
                  icon: '🛑',
                  title: 'Экстренная остановка',
                  desc: 'В любой момент вы можете мгновенно остановить работу бота и вернуть управление себе, нажав клавишу ESC.',
                },
                {
                  icon: '🔒',
                  title: 'Прямое взаимодействие',
                  desc: 'Бот работает только с открытым окном игры. Он не использует скрытые API-запросы, которые легко отслеживаются разработчиками игры.',
                },
              ].map(({ icon, title, desc }) => (
                <div key={title} style={{
                  display: 'flex', gap: 14, marginBottom: 16, padding: '14px',
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
            background: 'var(--elevated)', border: '1px solid var(--outline)',
            borderRadius: 20,
            boxShadow: '0 0 48px rgba(61,127,255,0.06)',
          }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: '#FFFFFF', marginBottom: 12 }}>
              Готов начать охоту?
            </div>
            <p style={{ fontSize: 14, color: 'var(--on-surface2)', marginBottom: 28, lineHeight: 1.7 }}>
              100 кредитов бесплатно при регистрации. Никакой кредитки не нужно.
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
