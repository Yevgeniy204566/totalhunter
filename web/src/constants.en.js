export const LANDING = {
  badge:    'Total Battle · Player Assistant',
  heroTitle: 'Total Hunter —',
  heroAccent: 'Automated Scouting',
  heroSub:
    'The bot automatically finds exchanges for hiring mercenaries and collects crypts across the map. ' +
    'Focus on your tasks while the system searches for targets for you.',
  ctaPrimary:   'Start Searching ➔',
  ctaSecondary: 'Instructions',
  statsLabel:   '⬡ Our Players\' Results',
  stats: [
    { key: 'total_exchanges', icon: '', label: 'Exchanges Found',   color: 'var(--accent)' },
    { key: 'total_crypts',    icon: '', label: 'Crypts Collected',  color: '#B060FF'       },
    { key: 'active_hunters',  icon: '', label: 'Players Online',    color: 'var(--credits-gold)' },
  ],
  featuresTitle: 'What the Bot Does',
  featuresSub:   'Automating routine tasks for a comfortable game',
  features: [
    {
      icon: '', color: 'var(--accent)',
      title: 'Find Mercenary Exchanges',
      desc:
        'The bot constantly scans the map to find exchanges where you can buy elite troops. ' +
        'You no longer need to spend hours scrolling the map looking for army packs.',
    },
    {
      icon: '', color: '#B060FF',
      title: 'Collecting Crypts',
      desc:
        'Fully automated crypt searching and collection. ' +
        'The bot finds targets, calculates travel time, and immediately proceeds to the next crypt.',
    },
  ],
  ctaTitle:   'Want to Free Up Your Time?',
  ctaSub:
    'Get 100 free credits upon your first connection. Try the bot in action right now.',
  ctaBtn: 'Start for Free',
}