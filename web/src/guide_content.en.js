export const GUIDE = {
  docsBadge: 'Documentation',
  heroTitle: 'User Guide',
  heroSub: 'Complete overview of Total Hunter operations — from installation to your first find.',

  toc: [
    { id: 'what-is',      label: 'What is Total Hunter' },
    { id: 'algorithm',    label: 'Search Algorithm' },
    { id: 'requirements', label: 'Requirements' },
    { id: 'install',      label: 'Installation' },
    { id: 'calibration',  label: 'Calibration' },
    { id: 'modes',        label: 'Operating Modes' },
    { id: 'roy',          label: 'SWARM System 🐝' },
    { id: 'settings',     label: 'Bot Settings' },
    { id: 'credits',      label: 'Diamonds & Rates' },
    { id: 'referrals',    label: 'Referrals' },
    { id: 'security',     label: 'Security' },
    { id: 'faq',          label: 'FAQ' },
  ],

  packages: [
    { name: 'Lite',  price: '$1',  diamonds: '300',   bonus: '',             color: '#64B5F6' },
    { name: 'Pro',   price: '$5',  diamonds: '2,000', bonus: '+33%',         color: '#3D7FFF' },
    { name: 'Ultra', price: '$10', diamonds: '5,000', bonus: 'MAX VALUE',    color: '#00CFFF', popular: true },
  ],

  whatIs: {
    title: 'What is Total Hunter',
    intro: 'Total Hunter is a desktop assistant bot designed to automate routine processes in Total Battle. The program handles searching and interacting with map objects:',
    exchange: {
      title: 'Mercenary Exchange',
      desc: 'The bot scans kingdom coastlines to discover mercenary markets. Upon finding a target, it plays a sound signal and stops the search.',
    },
    crypt: {
      title: 'Crypts',
      desc: 'The bot identifies selected crypt types (Common, Rare, Epic) and dispatches your "Carter" for gathering, utilizing march speed-ups with high precision.',
    },
    outro: 'The program runs on top of your browser or the Total Battle client, fully mimicking real user actions.',
  },

  algorithm: {
    title: 'Search Algorithm',
    coastLabel: 'Smart Coastline Scouting — Intelligent Shoreline Scanner',
    coastIntro: 'For maximum efficiency, the bot uses a unique "Coastal Snake" algorithm that mimics the logic of an experienced scout:',
    coastSteps: [
      { title: 'Terrain Analysis',     desc: 'The bot reads the mini-map in real-time, identifying water and land boundaries.' },
      { title: 'Movement Vector',      desc: 'The program calculates a trajectory perpendicular to the shore for effective coastal area combing.' },
      { title: 'Intelligent Phases',   desc: 'Homing — moving to the target area. Diving — deep territory scanning. Returning — safe return to the shoreline.' },
      { title: 'Stabilization (EMA)',  desc: 'A smoothing system removes cursor "jitter," making the bot\'s movements smooth and natural.' },
    ],
    coastOutro: 'Thanks to two-point calibration, the controls automatically adapt to any monitor resolution.',
    yoloLabel: 'Object Detection — Neural Network',
    exchangeModel: { title: 'Exchange Model', desc: 'Accurately recognizes mercenary markets on any background. The bot reacts instantly and alerts you upon detection.' },
    cryptModel:     { title: 'Crypts Model', desc: 'Identifies specific crypt types for continuous automated gathering.' },
    yoloOutro: 'As soon as the neural network confirms the target, the bot clicks the object, opens the menu, and dispatches the march.',
    cryptLabel: 'Automated Crypt Gathering',
    cryptSteps: [
      { title: 'Detection',    desc: 'The bot locates the required Crypt via the neural network and opens its in-game menu.' },
      { title: 'Travel Calculation', desc: 'March Range: Carter\'s travel time to the farthest crypt (in minutes). Speed-up 0–5: each level halves the travel time mathematically.' },
      { title: 'Wait Cycle',   desc: 'The program calculates the "there and back" time and adds a safety buffer (up to 300s). It waits for Carter\'s guaranteed return.' },
      { title: 'List Reset',   desc: 'If the crypt list is exhausted, it automatically resets via the "Arena" tab, continuing the cycle.' },
    ],
    cryptNote: '💡 To find Crypts, zoom in the map to the maximum. To find Exchanges, start at the land/water boundary with the map fully zoomed out.',
  },

  requirements: {
    title: 'Technical Requirements',
    rows: [
      { param: 'OS',         value: 'Windows 10 / 11 (64-bit)' },
      { param: 'Resolution', value: '1920×1080 (Full HD) — for ideal precision' },
      { param: 'Browser',    value: 'Chrome, Firefox, or the official Total Battle client' },
      { param: 'RAM',        value: '4 GB or higher' },
      { param: 'Network',    value: 'Stable internet connection (for license verification)' },
      { param: 'Account',    value: 'Active Total Battle game profile' },
    ],
  },

  install: {
    title: 'Quick Start: Install & Launch',
    intro: 'The process from registration to your first "hunt" takes less than 5 minutes.',
    steps: [
      { title: 'Registration',       desc: 'Create an account at total-hunter.com using your Google account.' },
      { title: 'Free Diamonds',      desc: 'Receive 100 free diamonds in your Dashboard to test the bot immediately.' , note: 'Trial is issued once per device (HWID-verified)' },
      { title: 'Download',           desc: 'Download TotalHunter.exe via the link in your personal dashboard.' },
      { title: 'Launch',             desc: 'Run the file. Python and neural network models are already included — no additional installation required.' },
      { title: 'Authorization',      desc: 'Log in to the app via Google (using the same credentials as the website).' },
      { title: 'Configuration',      desc: 'After logging in, the bot will prompt you to go to the CALIBRATION tab to adapt to your monitor.' },
    ],
  },

  calibration: {
    title: 'Screen Calibration (Mandatory Step)',
    intro: 'You need to set two reference points once. Open the game exactly as you usually play — the bot will remember these settings.',
    points: [
      { label: 'Point A', sublabel: 'Mini-map Center',         color: '#00CFFF', desc: 'Zoom out the mini-map to the minimum. Click exactly in the center of the mini-map rectangle.' },
      { label: 'Point B', sublabel: 'Resource Zone — Silver', color: '#B060FF', desc: 'Locate the Silver icon, hover until the "+" appears. Click exactly on the "+" symbol.' },
    ],
    stepsLabel: 'Calibration Steps',
    steps: [
      { title: 'Open the Game',       desc: 'Launch Total Battle: browser (full screen) or the desktop client.' },
      { title: 'CALIBRATION Tab',    desc: 'In the bot, navigate to the CALIBRATION tab.' },
      { title: 'Set Point A',        desc: 'Zoom out the mini-map. Click "Set Point A" → click the center of the mini-map.' },
      { title: 'Set Point B',        desc: 'Locate the Silver icon, hover for the "+". Click "Set Point B" → click the "+" symbol.' },
      { title: 'Save Profile',       desc: 'Select a slot and click "Save Profile".' },
    ],
    slotsNote: '💡 3 Profiles: Client — native game client, Browser 1 / Browser 2 — Chrome or Firefox. Each profile stores the full configuration: calibration, crypt selection, all sliders and click fine-tuning. Switching profiles loads everything instantly.',
  },

  modes: {
    title: 'Operating Modes',
    exchange: {
      title: 'Exchange Hunting',
      cost: '10 diamonds / find',
      rows: [
        { l: 'Logic',    t: 'Continuous coastline scanning using the "Snake" algorithm.' },
        { l: 'Result',   t: 'Audio signal + search stop → you purchase troops manually.' },
        { l: 'Settings', t: "Range 100%, Speed set to maximum." },
      ],
    },
    crypt: {
      title: 'Crypt Gathering',
      cost: '1 diamond / find',
      rows: [
        { l: 'Logic',      t: 'The bot finds crypts in the menu via neural network and dispatches Carter with coordinate-based clicks.' },
        { l: 'Cycle',      t: 'Waits for Carter\'s return based on calculated travel time.' },
        { l: 'Parameters', t: 'March Range (min) + Speed-up (0–5 levels) + Swing click fine-tuning.' },
        { l: 'Profiles',   t: 'Each profile stores individual settings for different accounts — switching is instant.' },
      ],
    },
    stopNote: 'Emergency Stop: Press ESC — the bot will instantly cease all actions.',
  },

  roy: {
    title: 'SWARM System — Shared Exchange Pool',
    intro: 'SWARM is a voluntary reconnaissance network for Total Hunter users. While your bot scans the map and finds exchanges, it automatically shares their coordinates with the common pool. In return, you receive coordinates from other participants. The more you scan — the more you get.',

    howTitle: 'How balance accumulates',
    howDesc: 'Every 30 seconds of active scanning earns you 45 seconds of SWARM access balance — a 1.5× coefficient. This is your reward for contributing to the shared network. Accumulated time is spent each time you request coordinates from the pool.',
    howRows: [
      { icon: '⏱', label: '30 sec of scanning',  value: '→ +45 sec balance (×1.5)' },
      { icon: '📍', label: 'Pool request',         value: '→ −60 sec balance' },
      { icon: '🔊', label: 'New coordinates',      value: '→ sound notification' },
    ],

    rulesTitle: 'Two conditions for earning balance',
    rules: [
      {
        icon: '📅',
        title: 'Only during the "Trade Routes" event',
        desc: 'Exchanges appear on the map on a strict schedule: once every 5 days for 24 hours. Outside this window there are no exchanges — nothing to scan, no balance earned. The countdown to the next event is displayed in the bot under the "Exchange" and "SWARM" tabs.',
      },
      {
        icon: '🗺',
        title: 'The map must actually be moving',
        desc: 'Every 30 seconds the bot compares two mini-map snapshots. If the image hasn\'t changed (game is closed, bot is idle, or the desktop is showing) — the scan is not counted. This protection prevents balance farming without real work.',
      },
    ],

    useTitle: 'How to use SWARM',
    useSteps: [
      { n: 1, title: 'Enable the SWARM toggle',        desc: 'In the bot\'s "SWARM" tab, activate the switch. The bot will automatically start sending discovered coordinates to the pool.' },
      { n: 2, title: 'Start the Exchange hunt',        desc: 'Press "START" — either in the "Exchange" tab or directly in "SWARM". It\'s the same bot, the same button.' },
      { n: 3, title: 'Check the coordinate pool',      desc: 'Click "Refresh pool" — a list of active exchanges from other participants will appear, showing kingdom, X/Y coordinates, fill level, and last update time.' },
      { n: 4, title: 'React to the sound notification', desc: 'When new coordinates appear in the pool, the bot will play a sound. Refresh the list and check fresh positions immediately.' },
    ],

    note: '💡 A coordinate stays in the pool for 20 minutes. An exchange lasts 2–5 minutes after appearing — act fast. Fill ≥90% means the exchange has already been cleared.',
  },

  settings: {
    title: 'Bot Settings',
    exchangeLabel: 'EXCHANGES tab — neural network & navigation',
    exchangeNote: 'Exchange detection accuracy — 80%. Important: "Scan Frequency" must be ≤ "Speed (sec/step)" — the neural network must finish processing each frame before the bot takes the next step.',
    cryptLabel: 'CRYPTS tab — collection parameters',
    cryptNote: 'Crypt detection accuracy — 30%. This is normal: crypts are small and partially obscured by the game UI. All settings are saved to the active profile — create separate profiles for different accounts.',
    optimalLabel: 'Optimal',
    rangeLabel: 'Range',
    exchange: [
      { name: 'Detection Accuracy',   range: '0.1 – 0.9', optimal: '0.65–0.75', desc: 'YOLO confidence threshold. Lower = more false positives, higher = missed exchanges at screen edges.' },
      { name: 'Scan Frequency',       range: '0.1 – 5.0 s', optimal: '0.4–0.8 s', desc: 'Pause between scan frames. Lower = faster, but the neural network may miss a still-loading screen.' },
      { name: 'Joystick Step',        range: '10 – 20 px', optimal: '13–16', desc: 'Joystick step size in pixels. Smaller = more precise dive and return, larger = faster map movement.' },
      { name: 'Speed (sec/step)',     range: '0.5 – 5.0 s', optimal: '1.5–2.5 s', desc: 'Wait after each joystick step. Lower = faster sweep, but the map may not finish rendering.' },
      { name: 'Dive Depth',           range: '1 – 10', optimal: '3–6', desc: 'How many screens deep to dive inland. More = covers distant areas, less = compact dive.' },
      { name: 'Ocean/Land Boundary',  range: '1 – 15 %', optimal: '3–5 %', desc: 'Min land % on minimap. Below this the bot treats the area as open ocean and turns around.' },
      { name: 'Min Water Body',       range: '100 – 2000 px', optimal: '≈ 500', desc: 'Min water body size on minimap for coastline detection. Lower = catches rivers, higher = open water only.' },
      { name: 'Return Diagonal',      range: '0.0 – 1.0', optimal: '0.4–0.6', desc: 'Diagonal fraction during beacon return. 0 = horizontal only, 1 = full diagonal.' },
      { name: 'Footprint Memory',     range: '60 – 1200 s', optimal: '5–15 min', desc: 'TTL of visited-zone marks. Lower = bot revisits sooner, higher = avoids repeats longer.' },
      { name: 'Return Delta',         range: '0 – 20 px', optimal: '3–8 px', desc: 'Rightward offset during beacon return. Compensates drift — increase if bot consistently returns left of beacon.' },
      { name: 'Nav Agility',          range: '10 – 100 %', optimal: '40–60 %', desc: 'Navigator angle smoothing factor. Lower = smooth glide, higher = snaps sharply to coastline.' },
    ],
    crypt: [
      { name: 'Detection Accuracy',   range: '0.1 – 0.9', optimal: '0.65–0.75', desc: 'YOLO confidence for crypts. Lower = false captures, higher = risk of missing a rare crypt.' },
      { name: 'March Acceleration',   range: '0 – 5', optimal: '2–3', desc: 'Number of "Accelerate" clicks before sending Carter. More = faster army, but requires enough accelerators.' },
      { name: 'Break Between Crypts', range: '3 – 300 s', optimal: '8–15 s', desc: 'Pause after Carter returns before the next crypt. Increase if the army does not recover in time.' },
      { name: 'March Range',          range: '5 – 30 min', optimal: '10–20 min', desc: 'Max Carter march time (T_max). Wait time = T_max / 2^N, where N is the number of accelerations.' },
      { name: 'Detection Frequency',  range: '0.0 – 4.0 s', optimal: '0.8–1.5 s', desc: 'Pause between scrolls during crypt search. Lower = faster scan, higher = more accurate frame processing.' },
      { name: 'Swing 1 — Study',       range: '± buttons', optimal: '0', desc: 'Vertical fine-tuning for the "Study" button click. If the click misses the button, press "+" or "−" in 5px steps until it lands correctly.' },
      { name: 'Swing 2 — Speed Up',    range: '± buttons', optimal: '0', desc: 'Vertical fine-tuning for the "Use" button in the speed-up window. Works independently from Swing 1.' },
      { name: 'Click Speed',           range: '−2.0 – +2.0 s', optimal: '0.0 s', desc: 'Adjusts the pause between bot actions. Right = faster (less pause), left = slower. Does not affect march time or neural network.' },
    ],
  },

  credits: {
    title: 'Diamonds & Rates',
    intro: 'Total Hunter uses ◆ diamonds — an internal currency consumed only for successful bot actions.',
    spendLabel: 'Diamond Consumption',
    spendRows: [
      { label: 'Exchange Found', cost: '−10 diamonds', color: '#00CFFF' },
      { label: 'Crypt Gathered',  cost: '−1 diamond',   color: '#B060FF' },
      { label: 'Nothing Found',    cost: 'Free',         color: 'var(--on-surface2)' },
      { label: 'Trial',            cost: '+100 diamonds', color: 'var(--credits-gold)' },
    ],
    trialNote: '⚠ Free Trial: Every new user receives 100 diamonds upon registration. Tied to HWID — once per device.',
    popularLabel: 'BEST CHOICE',
  },

  referrals: {
    title: 'Referral System',
    intro: 'Invite players and receive a percentage of their every purchase forever. Features a three-level referral chain.',
    levels: [
      { level: 'L1', pct: '10%', desc: 'Your friends',    color: '#FFD166' },
      { level: 'L2', pct: '5%',  desc: 'Their referrals', color: '#00CFFF' },
      { level: 'L3', pct: '1%',  desc: 'Next circle',     color: '#B060FF' },
    ],
    note: '💡 Diamonds are credited instantly after a referral\'s payment. Find your link in the "Referrals" section of the Dashboard.',
  },

  security: {
    title: 'Security & Anti-Ban',
    intro: 'Total Hunter is designed so its actions are indistinguishable from an experienced player:',
    rows: [
      { icon: '⏱', title: 'Random Pauses',      desc: 'A random pause of 0.4–0.9s is generated between every action.' },
      { icon: '🖱', title: 'Hand Imitation',       desc: 'Every click has a random offset of ±5–8px — full human hand simulation.' },
      { icon: '🛑', title: 'Emergency Stop',    desc: 'The ESC key instantly stops the bot and returns control to you.' },
      { icon: '🔒', title: 'Direct Interaction', desc: 'The bot works only with the open game window, without hidden API requests.' },
    ],
  },

  faq: {
    title: 'Frequently Asked Questions',
    rows: [
      { q: 'Can I use my computer while the bot is running?',
        a: 'Since the bot controls the mouse and keyboard, we recommend running it when you are not using the PC or using a separate laptop.' },
      { q: 'Does the bot need my game password?',
        a: 'No. The bot runs on top of the game you have already launched. we do not need your Total Battle credentials — your account security is guaranteed.' },
      { q: 'What is HWID and why is it needed?',
        a: 'Hardware ID is a unique "fingerprint" of your computer. Licenses and free trials are tied to your hardware to prevent abuse.' },
      { q: 'Can I move my account to another PC?',
        a: 'Yes. Go to the Dashboard → "Devices" section, unbind the old HWID, and log in on the new device.' },
      { q: 'How do diamonds work during errors or internet outages?',
        a: 'Diamonds are only deducted for a successful result (finding an Exchange or dispatching Carter). If the bot finds nothing or a crash occurs, your balance remains unchanged.' },
      { q: 'Can I get banned?',
        a: 'We have implemented all possible masking methods: randomized pauses (0.4–0.9s) and random click offsets (±5–8px). The risk is minimal; however, any third-party software carries theoretical risks. Use the bot wisely.' },
    ],
  },

  cta: {
    title: 'Ready to Start the Hunt?',
    sub: '100 free diamonds upon registration. No credit card required.',
    btnDashboard: 'Go to Dashboard →',
    btnStart: 'Start for Free →',
  },
}