export const DOWNLOAD = {
  badge:       'Windows · v1.0',
  title:       'Download Total Hunter',
  subtitle:    'Install the bot in 2 minutes and start farming exchanges and crypts automatically.',
  btnDownload: 'Download TotalHunter.zip',
  btnGuide:    'Installation Guide',
  sysTitle:    'System Requirements',
  sysItems: [
    { icon: '🖥', label: 'Windows 10 / 11 (64-bit)' },
    { icon: '💾', label: '~1.5 GB free disk space' },
    { icon: '🌐', label: 'Internet connection' },
    { icon: '🎮', label: 'Total Battle (browser or client)' },
  ],
  stepsTitle: 'How to Install',
  steps: [
    { n: '1', text: 'Download TotalHunter.zip and extract it to any folder.' },
    { n: '2', text: 'Run TotalHunter.exe — Windows Defender may ask for permission, click "Run anyway".' },
    { n: '3', text: 'Sign in with Google and link your device in the dashboard.' },
  ],
  noteTitle: 'First Launch',
  noteText:  'First 100 diamonds are free. Sign in with Google, no credit card required.',
  backHome:  '← Back to Home',
}

export const LANDING = {
  badge:      'Total Battle · Automation',
  heroTitle:  'Total Hunter —',
  heroAccent: 'Smart Search and Automation in Total Battle',
  heroSub:
    'Tired of spending hours scrolling the map for exchanges and manually timing Carter\'s marches? ' +
    'Total Hunter finds mercenary exchanges and sends Carter to crypts — automatically, without you.',
  ctaPrimary:   'Try for Free ➔',
  ctaSecondary: 'Guide',
  statsLabel:   '⬡ Total Hunter Players\' Results',
  stats: [
    { key: 'total_exchanges', label: 'Exchanges Found',   color: 'var(--accent)' },
    { key: 'total_crypts',    label: 'Crypts Collected',  color: '#B060FF'       },
    { key: 'active_hunters',  label: 'Players Online',    color: 'var(--credits-gold)' },
  ],
  featuresTitle: 'What Total Hunter Solves',
  featuresSub:   'Not a clicker — a full scout with a neural network',
  features: [
    {
      icon: '🏪', color: 'var(--accent)',
      title: 'Mercenary Exchanges — Never Miss One',
      desc:
        'The bot scans kingdom coastlines 24/7 and wakes you with a sound signal the moment it finds an exchange. ' +
        'No more hours at the monitor — just an alert and buying your army.',
    },
    {
      icon: '⚰️', color: '#B060FF',
      title: 'Crypts Farm While You Sleep',
      desc:
        'Full cycle without you: found crypt → sent Carter → calculated return time → repeated. ' +
        'Elite resources accumulate around the clock.',
    },
  ],
  ctaTitle: 'Want to Keep Up With the Top Players?',
  ctaSub:
    'First 100 diamonds are free. No credit card required. Ready to launch in 5 minutes.',
  ctaBtn: 'Start for Free',
}
