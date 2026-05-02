export const DASHBOARD = {
  loading: 'Loading...',

  timeAgo: {
    justNow:     'just now',
    minutesAgo: 'min ago',
    hoursAgo:   'h ago',
    daysAgo:    'd ago',
  },

  nav: {
    logout: 'Logout',
    guide:  'Guide',
  },

  profile: {
    title: 'Profile',
    credits:        'Credits',
    refCredits:     'Referrals',
    refCode:        'Ref. code',
    status:         'Status',
    memberSince:    'Member since',
    trialUsed:      'Trial used',
    trialAvailable: '✓ Trial available',
    topUp:          'Top up credits →',
  },

  recentHunts: {
    title:      'Recent Finds',
    empty:      'No hunts yet. Start the bot! ⚔',
    found:      '— found',
    looted:     '+LOOTED',
    allHistory: 'Full history →',
  },

  huntTypes: {
    exchange: 'Exchange',
    crypt:    'Crypt',
  },

  statTiles: {
    exchangesToday: 'Exchanges today',
    cryptsToday:    'Crypts today',
    huntersOnline:  'Hunters online',
  },

  balance: {
    title:          'Balance',
    diamonds:       'Diamonds',
    refBalance:     'Referral balance',
    sectionBadge:   '⬡ Choose your arsenal',
    sectionTitle:   'Top up diamonds',
    sectionSub:     'Payment via Free-Kassa · Instant delivery',
    secureNote:     '🔒 Secure payment · Free-Kassa · Diamonds do not expire',
    featuredBadge: '⭐ Hunter\'s Choice',
    bonusDiamonds: '🎁 bonus diamonds',
    baseDiamonds:  'base ◆',
    forHunt:       'diamonds per hunt',
    buying:         'Redirecting...',
    buyBtn:         'Buy —',
    errorPayment:   'Payment error',
  },

  hunts: {
    title:         'Hunt History',
    statToday:     'Today',
    stat7days:     'Last 7 days',
    statTotal:     'Total hunts',
    colType:       'Type',
    colTime:       'Time',
    empty:         'No hunts yet. Start the bot! ⚔',
    lastRecords:   'last',
    lastRecordsSuffix: 'records',
    exchangeLabel: 'Exchanges',
    cryptLabel:    'Crypts',
  },

  referrals: {
    title:       'Referral Program',
    sub:         'Invite hunters — earn % from their every purchase',
    linkLabel:   '⬡ Your referral link',
    copy:        'Copy',
    copied:      '✓ Copied!',
    codeLabel:   'Code:',
    balanceLabel:'Referral balance',
    transferring:'Transferring...',
    transfer:    'Transfer to balance →',
    howTitle:    'How earnings work',
    levels: [
      { level: 'L1', pct: '10%', desc: 'Direct referrals (invited by you)',   color: 'var(--accent)'      },
      { level: 'L2', pct: '5%',  desc: 'Referrals of your referrals',              color: '#B060FF'             },
      { level: 'L3', pct: '1%',  desc: 'Third chain level',                 color: 'var(--credits-gold)' },
    ],
    perPurchase: 'of every purchase amount',
    note:        'Earnings are generated from every credit purchase in your referral chain. Blocked users are skipped, and the chain continues.',
  },

  transactions: {
    title:    'Transactions',
    colOp:    'Operation',
    colAmount:'Amount',
    colDate:  'Date',
    empty:    'No transactions yet',
    types: {
      purchase:               'Credit purchase',
      credit_use:             'Hunting',
      trial:                  'Trial bonus',
      ref_welcome:            'Ref. welcome',
      ref_earning:            'Ref. accrual',
      ref_transfer:           'Referrals → balance',
      hwid_duplicate_blocked: 'HWID duplicate',
      manual_adjust:          'Adjustment',
    },
  },
}