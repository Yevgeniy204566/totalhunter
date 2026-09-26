export const DOWNLOAD = {
  badge:       'Windows 10 / 11',
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
  warning: {
    title: '⚠️ Important before installing',
    defenderText: 'Windows Defender may block the bot from working. Before installing, we recommend adding the program and its folder to Windows Defender exclusions.',
    calibrationText: 'The bot cannot be launched until all 13 calibration points are completed.',
  },
  stepsTitle: 'How to Install',
  steps: [
    { n: '1', text: 'Install the program.' },
    { n: '2', text: 'If needed, add the program and its folder to Windows Defender exclusions.' },
    { n: '3', text: 'Sign in with Google and link your device in the dashboard.' },
    { n: '4', text: 'Run calibration and complete all 13 points.' },
    { n: '5', text: 'Only launch the bot after calibration is fully complete.' },
  ],
  noteTitle: 'First Launch',
  noteText:  'First 300 diamonds are free. Sign in with Google, no credit card required.',
  backHome:  '← Back to Home',
}

export const LANDING = {
  badge:      'Total Battle · Automation',
  heroTitle:  'Total Hunter —',
  heroAccent: 'Smart Search and Automation in Total Battle',
  heroSub:
    'Tired of spending hours scrolling the map for exchanges and manually timing Carter\'s marches? ' +
    'Total Hunter finds mercenary exchanges, sends Carter to crypts and tracks your clan’s chests — automatically, without you.',
  ctaPrimary:   'Try for Free ➔',
  ctaSecondary: 'Guide',
  statsLabel:   '⬡ Total Hunter Players\' Results',
  stats: [
    { key: 'total_exchanges', label: 'Exchanges Found',   color: 'var(--accent)' },
    { key: 'total_crypts',    label: 'Crypts Collected',  color: '#B060FF'       },
    { key: 'active_hunters',  label: 'Players Online',    color: 'var(--credits-gold)' },
  ],
  featuresTitle: 'What Total Hunter Does',
  featuresSub:   'Not a clicker — a full scout with a neural network',
  playersTitle:  'For Players',
  features: [
    {
      icon: '🏪', color: '#3D7FFF',
      title: 'Mercenary Exchanges',
      desc:
        'Two modes: "Snake" follows the coast and wakes you with a sound signal on a find, ' +
        '"Scanner 2.0" captures the map fast while a neural network processes frames in the background.',
    },
    {
      icon: '⚰️', color: '#B060FF',
      title: 'Crypts Without You',
      desc:
        'Pick the crypt types — the bot finds a crypt, sends Carter, calculates the march return time and repeats. ' +
        'Auto-stop by number of crypts or by time.',
    },
    {
      icon: '🐝', color: '#FFD166',
      title: 'SWARM — Shared Exchange Pool',
      desc:
        'Exchange coordinates found by kingdom hunters go into a shared pool. ' +
        'Fresh finds appear on the SWARM page in real time.',
    },
    {
      icon: '👁', color: '#22D3EE',
      title: 'Sees the Game Like a Human',
      desc:
        'The bot works from the screen image, on top of the browser or the official game client. ' +
        'No game login or password needed. Calibrates to any monitor.',
    },
  ],
  clanTitle: 'For Clans',
  clanSub:   "Track every player's contribution — for leaders and treasurers",
  clanFeatures: [
    {
      icon: '📦', color: '#F59E0B',
      title: 'Chest Collection by the Bot',
      desc:
        'The bot opens gift chests one by one, reads the sender and chest type, ' +
        'and uploads the whole list to the site in one batch. Every chest is counted.',
    },
    {
      icon: '🏆', color: '#4ADE80',
      title: 'Clan Table on the Site',
      desc:
        'A public clan link: seasons with dates, points per chest type, targets, ' +
        'ranking by points, target achievers highlighted, season archive.',
    },
    {
      icon: '🐲', color: '#F87171',
      title: 'Ancient',
      desc:
        'Clan roster with ranks and troop composition, an Ancient damage quota calculator, ' +
        'and a public roster page for the clan.',
    },
  ],
  techTitle: 'Under the Hood',
  tech: [
    { icon: '🧠', text: 'YOLO neural network finds objects on the map' },
    { icon: '🔤', text: 'Text recognition (OCR) reads names and chests' },
    { icon: '🎯', text: 'Two-point calibration — any resolution' },
    { icon: '💻', text: 'Runs on your PC' },
  ],
  ctaTitle: 'Want to Keep Up With the Top Players?',
  ctaSub:
    'First 300 diamonds are free. No credit card required. Ready to launch in 5 minutes.',
  ctaBtn: 'Start for Free',
}
