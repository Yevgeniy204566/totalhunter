export const DASHBOARD = {
  loading: 'Загрузка...',

  timeAgo: {
    justNow:    'только что',
    minutesAgo: 'мин назад',
    hoursAgo:   'ч назад',
    daysAgo:    'дн назад',
  },

  nav: {
    logout: 'Выйти',
    guide:  'Гайд',
  },

  profile: {
    title: 'Профиль',
    credits:        'Кредиты',
    refCredits:     'Рефералы',
    refCode:        'Реф. код',
    status:         'Статус',
    memberSince:    'С нами с',
    trialUsed:      'Триал использован',
    trialAvailable: '✓ Триал доступен',
    topUp:          'Пополнить кредиты →',
  },

  recentHunts: {
    title:      'Последние находки',
    empty:      'Ещё нет охот. Запусти бота! ⚔',
    found:      '— найден',
    looted:     '+ЛУТНУТО',
    allHistory: 'Вся история →',
  },

  huntTypes: {
    exchange: 'Биржа',
    crypt:    'Склеп',
  },

  statTiles: {
    exchangesToday: 'Бирж сегодня',
    cryptsToday:    'Склепов сегодня',
    huntersOnline:  'Охотников онлайн',
  },

  balance: {
    title:         'Баланс',
    diamonds:      'Алмазы',
    refBalance:    'Реферальный баланс',
    sectionBadge:  '⬡ Выбери свой арсенал',
    sectionTitle:  'Пополнение алмазов',
    sectionSub:    'Оплата через Free-Kassa · Зачисление мгновенно',
    secureNote:    '🔒 Безопасная оплата · Free-Kassa · Алмазы не сгорают',
    featuredBadge: '⭐ Выбор охотника',
    bonusDiamonds: '🎁 бонус алмазов',
    baseDiamonds:  'базовых ◆',
    forHunt:       'алмазов на охоту',
    buying:        'Переход...',
    buyBtn:        'Купить —',
    errorPayment:  'Ошибка оплаты',
  },

  hunts: {
    title:         'История охот',
    statToday:     'Сегодня',
    stat7days:     'За 7 дней',
    statTotal:     'Всего охот',
    colType:       'Тип',
    colTime:       'Время',
    empty:         'Охот пока нет. Запусти бота! ⚔',
    lastRecords:   'последние',
    lastRecordsSuffix: 'записей',
    exchangeLabel: 'Биржи',
    cryptLabel:    'Склепы',
  },

  referrals: {
    title:       'Реферальная программа',
    sub:         'Приглашай охотников — получай % от каждой их покупки',
    linkLabel:   '⬡ Твоя реферальная ссылка',
    copy:        'Копировать',
    copied:      '✓ Скопировано!',
    codeLabel:   'Код:',
    balanceLabel:'Реферальный баланс',
    transferring:'Перевод...',
    transfer:    'Перевести на баланс →',
    howTitle:    'Как работают начисления',
    levels: [
      { level: 'L1', pct: '10%', desc: 'Прямые рефералы (твои приглашённые)',   color: 'var(--accent)'       },
      { level: 'L2', pct: '5%',  desc: 'Рефералы твоих рефералов',              color: '#B060FF'             },
      { level: 'L3', pct: '1%',  desc: 'Третий уровень цепочки',                color: 'var(--credits-gold)' },
    ],
    perPurchase: 'от суммы каждой покупки',
    note:        'Начисления идут с каждой покупки кредитов по твоей реферальной цепочке. Заблокированные пользователи пропускаются, цепочка продолжается дальше.',
  },

  transactions: {
    title:    'Транзакции',
    colOp:    'Операция',
    colAmount:'Сумма',
    colDate:  'Дата',
    empty:    'Транзакций пока нет',
    types: {
      purchase:               'Покупка кредитов',
      credit_use:             'Охота',
      trial:                  'Триал-бонус',
      ref_welcome:            'Реф. приветствие',
      ref_earning:            'Реф. начисление',
      ref_transfer:           'Рефералы → баланс',
      hwid_duplicate_blocked: 'HWID дубликат',
      manual_adjust:          'Корректировка',
    },
  },
}
