export const LANDING = {
  badge:    'Total Battle · Автоматизация',
  heroTitle: 'Total Hunter —',
  heroAccent: 'Эволюция охоты',
  heroSub:
    'Автоматический фарм ресурсов на карте: биржи, склепы, маршруты — ' +
    'бот работает, пока ты отдыхаешь.',
  ctaPrimary:   'Начать охоту ⚔',
  ctaSecondary: 'Как это работает',
  statsLabel:   '⬡ Статистика за всё время',
  stats: [
    { key: 'total_exchanges', icon: '⚔', label: 'Бирж зачищено',   color: 'var(--accent)' },
    { key: 'total_crypts',    icon: '💀', label: 'Склепов зачищено', color: '#B060FF'       },
    { key: 'active_hunters',  icon: '◈',  label: 'Охотников онлайн', color: 'var(--credits-gold)' },
  ],
  featuresTitle: 'Что умеет бот',
  featuresSub:   'Полная автоматизация двух ключевых механик Total Battle',
  features: [
    {
      icon: '⚔', color: 'var(--accent)',
      title: 'Биржи ресурсов',
      desc:
        'Бот сканирует карту по спирали, находит и атакует биржи. ' +
        'Умная CoastalSnake-навигация огибает берега.',
    },
    {
      icon: '💀', color: '#B060FF',
      title: 'Слепые склепы',
      desc:
        'Детерминированный маршрут в склепы Даркнета без OCR. ' +
        'Рассчитывает время марша по формуле и возвращается точно в срок.',
    },
    {
      icon: '◈', color: 'var(--credits-gold)',
      title: 'Облачный кабинет',
      desc:
        'Статистика охот, реферальная система, пополнение кредитов — ' +
        'всё доступно с любого устройства.',
    },
  ],
  ctaTitle:   'Готов к охоте?',
  ctaSub:
    '100 кредитов бесплатно при первом подключении устройства. Никакой кредитной карты.',
  ctaBtn: 'Попробовать бесплатно',
}
