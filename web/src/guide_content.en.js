export const GUIDE = {
  docsBadge: 'Documentation',
  heroTitle: 'User Guide',
  heroSub: 'Complete overview of Total Hunter — from installation to your first haul.',

  toc: [
    { id: 'what-is',      label: 'What is Total Hunter' },
    { id: 'algorithm',    label: 'Search Algorithm' },
    { id: 'requirements', label: 'Requirements' },
    { id: 'install',      label: 'Installation' },
    { id: 'calibration',  label: 'Calibration' },
    { id: 'modes',        label: 'Operating Modes' },
    { id: 'tuning',       label: '⚙ Tuning (Carter)' },
    { id: 'chests',       label: '📦 Chests' },
    { id: 'ancient',      label: '🐲 Ancient' },
    { id: 'roy',          label: 'SWARM System 🐝' },
    { id: 'settings',     label: 'Bot Settings' },
    { id: 'credits',      label: 'Diamonds & Rates' },
    { id: 'referrals',    label: 'Referrals' },
    { id: 'security',     label: 'Security' },
    { id: 'faq',          label: 'FAQ' },
  ],

  packages: [
    { name: 'Lite',  price: '$1',  diamonds: '300',   bonus: '',          color: '#64B5F6' },
    { name: 'Pro',   price: '$5',  diamonds: '2,000', bonus: '+33%',      color: '#3D7FFF' },
    { name: 'Ultra', price: '$10', diamonds: '5,000', bonus: 'MAX VALUE', color: '#00CFFF', popular: true },
  ],

  whatIs: {
    title: 'What is Total Hunter',
    intro: 'Total Hunter is a desktop assistant bot for automating routine tasks in Total Battle. The app handles the mindless searching and clicking, saving your time:',
    exchange: {
      title: 'Exchange Hunting',
      desc: 'The bot scans coastlines looking for mercenary markets. As soon as it finds one — it plays a sound alert and stops, so you have time to buy troops.',
    },
    crypt: {
      title: 'Crypt Farming',
      desc: 'The bot recognizes the crypt types you need (Common, Rare, Epic) and sends Carter to collect automatically, applying march speed-ups on its own.',
    },
    outro: 'The program works on top of your game window (browser or client), fully imitating the clicks and pauses of a real player.',
  },

  algorithm: {
    title: 'How the Bot Sees the Game',
    coastLabel: 'Smart Coastline Scouting',
    coastIntro: 'To avoid wandering the map blindly, the bot uses the "Coastal Snake" algorithm. It mimics the logic of a live scout:',
    coastSteps: [
      { title: 'Terrain Analysis',    desc: 'Reads the mini-map in real-time, identifying where water ends and land begins.' },
      { title: 'Movement Vector',     desc: 'Builds a path strictly perpendicular to the coast, so it never skips a bay.' },
      { title: 'Intelligent Phases',  desc: 'First moves toward the target (Homing), then deep-scans the land (Diving), and safely returns to shore (Returning).' },
      { title: 'Smoothing (EMA)',     desc: 'Smooths the camera movements, eliminating jitter and imitating natural mouse scrolling.' },
    ],
    coastOutro: 'Thanks to initial calibration, the system adapts perfectly to any monitor resolution.',
    yoloLabel: 'Neural Network Vision (YOLO)',
    exchangeModel: { title: 'Exchange Detector', desc: 'Recognizes a mercenary market against any landscape background, even if partially obscured.' },
    cryptModel:    { title: 'Crypt Detector',    desc: 'Tells an Epic crypt from a Common one, ignoring UI clutter and game interface noise.' },
    yoloOutro: 'The moment the neural network locks onto a target, the bot takes over, clicks the object, and runs its built-in scenario.',
    cryptLabel: 'March Automation',
    cryptSteps: [
      { title: 'Detection',     desc: 'Finds the crypt in the search menu and clicks on it.' },
      { title: 'Timing Calc',   desc: 'Calculates march travel time based on distance and your chosen number of speed-ups.' },
      { title: 'Wait Cycle',    desc: 'Waits the exact time (there + back) with a small random buffer, to guarantee Carter\'s return.' },
      { title: 'List Reset',    desc: 'When the crypt list runs out, the bot refreshes it via the "Arena" tab and continues farming.' },
    ],
    cryptNote: '💡 Important: for Crypt farming, zoom the map in to maximum. For Exchange hunting, zoom all the way out and start at the land/water boundary.',
  },

  requirements: {
    title: 'System Requirements',
    rows: [
      { param: 'OS',         value: 'Windows 10 / 11 (64-bit)' },
      { param: 'Resolution', value: '1920×1080 (Full HD) — recommended for ideal click accuracy' },
      { param: 'Platform',   value: 'Chrome, Firefox or the official Total Battle PC client' },
      { param: 'RAM',        value: '4 GB or more' },
      { param: 'Internet',   value: 'Stable connection (required for neural network and balance checks)' },
      { param: 'Account',    value: 'Any active in-game profile' },
    ],
  },

  install: {
    title: 'Quick Start: Installation',
    intro: 'From sign-up to first launch takes no more than 5 minutes. No complex Python setup — everything is already bundled inside.',
    steps: [
      { title: 'Sign Up',        desc: 'Log in at total-hunter.com using your Google account.' },
      { title: 'Free Trial',     desc: 'Your dashboard will instantly show 100 diamonds to test all bot features.', note: 'Trial is issued once per unique device (HWID).' },
      { title: 'Download',       desc: 'Download TotalHunter.exe from your personal dashboard.' },
      { title: 'Launch',         desc: 'Just open the program. It\'s fully portable and ready to run.' },
      { title: 'Log In to Bot',  desc: 'Click "Sign in with Google" inside the app (use the same account as the website).' },
      { title: 'First Setup',    desc: 'Before starting, the bot will ask you to complete Calibration. This is required!' },
    ],
  },

  calibration: {
    title: 'Calibration: Setting the Bot\'s "Eyes" (Required)',
    intro: 'Why is this needed? Everyone has different monitors, window scales, and browsers. To make sure the bot doesn\'t miss buttons, you need to "show" it your game interface coordinates once. Open the game the way you plan to play, and set two points.',
    points: [
      { label: 'Point A', sublabel: 'Mini-map Center',   color: '#00CFFF', desc: 'Zoom the mini-map out to minimum (top-right corner). In the bot, click "Set Point A" and click exactly in the center of the mini-map rectangle.' },
      { label: 'Point B', sublabel: 'Silver "+" button', color: '#B060FF', desc: 'Hover over the Silver panel at the top of the screen until the green plus appears. In the bot, click "Set Point B" and click exactly on that plus sign.' },
    ],
    stepsLabel: 'Steps',
    steps: [
      { title: 'Prepare your window',  desc: 'Open the game and set the window to the size you\'ll use (fullscreen recommended).' },
      { title: 'Open Calibration',     desc: 'Switch to the CALIBRATION tab in the Total Hunter app.' },
      { title: 'Set Point A',          desc: 'Click the center of the mini-map as described above.' },
      { title: 'Set Point B',          desc: 'Click the Silver plus sign.' },
      { title: 'Save to a slot',       desc: 'Choose a free profile (e.g. "Browser 1") and click "Save". Next time the bot will load these coordinates automatically.' },
    ],
    slotsNote: '💡 3 independent profile slots. You can play from a browser and from the official client. Save a separate calibration, slider settings, and click tuning for each. Switching between them takes one second.',
  },

  modes: {
    title: 'Operating Modes',
    exchange: {
      title: 'Exchange Hunting',
      cost: '10 diamonds / find',
      rows: [
        { l: 'How it works', t: 'Continuously scans coastlines, moving the map in a "snake" pattern.' },
        { l: 'Result',       t: 'Once it spots an exchange — it stops and plays a loud sound. You buy the mercenaries yourself.' },
        { l: 'Settings',     t: 'Set the "Range" slider to 100% and speed to maximum.' },
      ],
    },
    crypt: {
      title: 'Crypt Farming',
      cost: '1 diamond / dispatch',
      rows: [
        { l: 'How it works',  t: 'Finds crypts in the search menu, clicks their coordinates, presses "Speed Up", and sends Carter.' },
        { l: 'Smart cycle',   t: 'The bot calculates flight time on its own. It waits for Carter and immediately sends him to the next crypt.' },
        { l: 'Full control',  t: 'You set the max range (in minutes) and how many speed-up levels to apply.' },
      ],
    },
    stopNote: 'Emergency stop: press the ESC key on your keyboard. The bot will freeze instantly.',
  },

  tuning: {
    title: 'Tuning (Auto-Carter)',
    intro: 'This module saves you from manually sending Carter and pressing speed-ups. It works in the background, even while you\'re busy with your own things in the game or running another bot module.',
    botLabel: 'How the bot automates the routine',
    steps: [
      { title: 'Waits for Carter',    desc: 'The bot scans the "Watchtower" icon. As soon as it changes color — Carter is home.', img: '/img/tune_wt_icon.png' },
      { title: 'Sends him out again', desc: 'Opens the captain window and clicks "Explore". Carter immediately flies out again.', img: '/img/tune_carter.png' },
      { title: 'Catches the march',   desc: 'In the active march list the bot finds Carter\'s bar and presses "Speed up".', img: '/img/tune_speed_up.png' },
      { title: 'Applies boosts',      desc: 'Automatically picks the most efficient available accelerator and clicks "Use".', img: '/img/tune_march_accel.png' },
    ],
    note: '💡 The Tuning module has its own toggle in the interface. You can enable it alongside Exchange hunting or Chest collection.',
  },

  chests: {
    title: 'Chests: Clan Statistics',
    intro: 'A duo of desktop bot and web dashboard. The bot auto-clicks through gifts in the game, and the website builds clean analytics for your clan.',
    botLabel: 'Step 1. Data Collection (via Bot)',
    botSteps: [
      { title: 'Auto-open',     desc: 'The bot visits the clan gifts tab and starts opening all available chests one by one.', img: '/img/chest_open.png' },
      { title: 'Read nickname', desc: 'Recognizes the "From:" field to identify which clan member obtained this chest.', img: '/img/chest_sender.png' },
      { title: 'Read type',     desc: 'Recognizes the "Source:" field (event name) to assign the chest the correct point value.', img: '/img/chest_type.png' },
    ],
    webLabel: 'Step 2. Analytics (on the Website)',
    webSteps: [
      { title: 'Management',   desc: 'In the leader dashboard you can set the "value" of each chest in points, set a season goal, and correct player names.' },
      { title: 'Public board', desc: 'Your clan gets its own link (like /chests/clan-name). Any member can open it from their phone and check their progress without registering.' },
    ],
    note: '💡 All history is saved. The leader can close seasons — old data is archived (available for 90 days).',
  },

  ancient: {
    title: 'Ancient: Damage Quota Calculator',
    intro: 'A web tool for clan leaders. Lets you fairly distribute the required Ancient damage quota, accounting for each player\'s actual strength (troops: Guards, Specialists, or Monsters).',
    howLabel: 'How it works (website only)',
    steps: [
      { title: 'Enter parameters', desc: 'The leader enters the total damage required and picks a distribution method (by rank or by army strength).' },
      { title: 'Fair calculation', desc: 'The algorithm weights each player\'s troop strength. Players with tier-9 armies get a higher quota than newcomers with tier-6.' },
      { title: 'Monitoring',       desc: 'The leader gets a color-coded table: instantly see who met their quota and who\'s dragging the clan down.' },
      { title: 'Transparency',     desc: 'Players can check their personal damage quota on the clan\'s public page.', },
    ],
    note: '💡 This module does not require downloading the bot. Everything works in the browser inside your Dashboard.',
  },

  roy: {
    title: 'SWARM: Exchange Radar',
    intro: 'SWARM is a shared player network. Your bot finds exchanges and anonymously submits their coordinates to the common pool. In return, you see coordinates found by others. Works on the principle of "help others — others help you".',

    howTitle: 'SWARM Time Economy',
    howDesc: 'For every map scan session you earn access time at a 1.5× rate. This time is spent when you request fresh coordinates from the pool.',
    howRows: [
      { icon: '⏱', label: '30 sec of your scanning', value: '→ +45 sec SWARM balance' },
      { icon: '📍', label: 'Pressed "Refresh Pool"',  value: '→ −60 sec SWARM balance' },
      { icon: '🔊', label: 'New exchange appeared',   value: '→ bot plays a sound alert' },
    ],

    rulesTitle: 'Anti-Abuse Protection',
    rules: [
      {
        icon: '📅',
        title: 'Active during event only',
        desc: 'Exchanges appear on the map only during "Trade Routes". Outside the event there are no exchanges to scan — SWARM balance is not earned.',
      },
      {
        icon: '🗺',
        title: 'AFK protection',
        desc: 'The bot analyzes mini-map pixels. If it\'s not moving (you\'re standing still) — no time is earned. No free rides — you have to actually fly and search.',
      },
    ],

    useTitle: 'How to Join',
    useSteps: [
      { n: 1, title: 'Activate',        desc: 'Enable the SWARM toggle in the matching bot tab.' },
      { n: 2, title: 'Start searching', desc: 'Press START for Exchange hunting. Your bot will begin contributing to the shared pool.' },
      { n: 3, title: 'Check the pool',  desc: 'Press "Refresh Pool". You\'ll see a list of fresh coordinates from other players (Kingdom, X/Y, fill level).' },
      { n: 4, title: 'React',           desc: 'Heard the sound — refresh the pool immediately and jump to the coordinates. Exchanges don\'t last long.' },
    ],

    note: '💡 If a pool exchange fill level is above 90% — it\'s most likely already been cleared. Only jump to "fresh" spots.',
  },

  settings: {
    title: 'Fine-Tuning the Bot',
    exchangeLabel: 'Settings: Exchange Hunting',
    exchangeNote: 'Main rule: "Scan Frequency" must be less than or equal to "Speed (sec/step)". Otherwise the neural network simply won\'t have time to "look at" the frame between camera jumps.',
    cryptLabel: 'Settings: Crypt Farming',
    cryptNote: 'All slider changes are instantly saved to the current Profile (Browser 1, Client, etc.).',
    optimalLabel: 'Optimal',
    rangeLabel: 'Range',
    exchange: [
      { name: 'Detection Accuracy',  range: '0.1 – 0.9',    optimal: '0.65–0.75', desc: 'How confident the bot must be that it sees an exchange. Too low — it will beep at every rock. Too high — it will miss an exchange in the fog.' },
      { name: 'Scan Frequency',      range: '0.1 – 5.0 s',  optimal: '0.4–0.8 s', desc: 'How often the neural network takes a "screenshot" of the screen. Lower = faster reaction, but higher PC load.' },
      { name: 'Joystick Step',       range: '10 – 20 px',   optimal: '13–16',     desc: 'How many pixels the bot moves the mini-map per step. Bigger step = faster travel, smaller = more thorough search.', highlight: true },
      { name: 'Speed (sec/step)',    range: '0.5 – 5.0 s',  optimal: '1.5–2.5 s', desc: 'Pause after each joystick step. If you have a slow connection and the map doesn\'t load in time — increase this.', highlight: true },
      { name: 'Dive Depth',          range: '1 – 10',       optimal: '3–6',       desc: 'How many screens deep the bot goes inland before turning back.' },
      { name: 'Ocean/Land Boundary', range: '1 – 15 %',     optimal: '3–5 %',    desc: 'What percentage of land must be on the radar for the bot to recognize it as a coastline rather than open ocean.' },
      { name: 'Min Water Body',      range: '100 – 2000 px', optimal: '≈ 500',    desc: 'Helps the bot tell large seas apart from small inland puddles.' },
      { name: 'Return Diagonal',     range: '0.0 – 1.0',    optimal: '0.4–0.6',  desc: 'Return-to-shore trajectory. 0 — straight line, 1 — diagonal.' },
      { name: 'Footprint Memory',    range: '60 – 1200 s',   optimal: '5–15 min', desc: 'How long the bot remembers it has already visited a zone. Prevents going in circles.' },
      { name: 'Return Delta',        range: '0 – 20 px',    optimal: '3–8 px',   desc: 'Offset correction. If the bot consistently returns left of the target on the way back — add a few pixels here.' },
      { name: 'Nav Agility',         range: '10 – 100 %',   optimal: '40–60 %',  desc: 'How sharply the bot changes direction while following coastline curves.' },
    ],
    crypt: [
      { name: 'Detection Accuracy',   range: '0.1 – 0.9',    optimal: '0.65–0.75', desc: 'Confidence threshold for recognizing crypts in the menu.' },
      { name: 'March Acceleration',   range: '0 – 5',        optimal: '2–3',       desc: 'How many times the bot clicks "Speed up march" before dispatching. Make sure you have enough accelerators in stock.', highlight: true },
      { name: 'Break Between Crypts', range: '3 – 300 s',    optimal: '8–15 s',   desc: 'Rest time after Carter has returned home.' },
      { name: 'March Range',          range: '5 – 30 min',   optimal: '10–20 min', desc: 'Critical parameter. The bot won\'t go to a crypt if it takes longer than this to get there.', highlight: true },
      { name: 'Detection Frequency',  range: '0.0 – 4.0 s',  optimal: '0.8–1.5 s', desc: 'Speed at which the bot scrolls through the crypt search menu.' },
      { name: 'Click Tuning (X/Y)',   range: 'X + Y axes',   optimal: '1–5 px',   desc: 'IMPORTANT: If the bot slightly misses buttons (due to font or Windows scaling quirks), you can manually shift its "aim" horizontally (X) and vertically (Y). Configured in the CALIBRATION tab for 4 main buttons.', img: '/img/swing1.png', highlight: true },
      { name: '↳ Adjustment example', range: 'X + Y axes',   optimal: '1–5 px',   desc: 'Screenshots show how axis offsets align the click precisely to the center of the "Speed Up" button in the march window.', img: '/img/swing2.png' },
      { name: 'Click Speed',          range: '−2.0 – +2.0 s', optimal: '0.0 s',  desc: 'Global interface speed. Slide left if your computer is slow and the bot clicks too fast.', highlight: true },
    ],
  },

  credits: {
    title: 'Economy: Diamonds',
    intro: 'All payments use the internal currency — diamonds (◆). You only pay for actual bot results.',
    spendLabel: 'Price List',
    spendRows: [
      { label: 'Exchange Found (sound triggered)', cost: '−10 diamonds', color: '#00CFFF' },
      { label: 'Successfully Sent to Crypt',       cost: '−1 diamond',   color: '#B060FF' },
      { label: 'Searched but found nothing',       cost: 'Free',         color: 'var(--on-surface2)' },
      { label: 'Registration (Trial)',             cost: '+100 diamonds', color: 'var(--credits-gold)' },
    ],
    trialNote: '⚠ Trial is issued automatically on first login. The system remembers your PC\'s HWID, so creating new accounts to abuse it won\'t work.',
    popularLabel: 'BEST VALUE',
  },

  referrals: {
    title: 'Partner Program',
    intro: 'Bring friends to Total Hunter and earn a percentage of their top-ups. Forever. The chain works three levels deep.',
    levels: [
      { level: 'Level 1', pct: '10%', desc: 'Your personal referrals', color: '#FFD166' },
      { level: 'Level 2', pct: '5%',  desc: 'Friends of your friends', color: '#00CFFF' },
      { level: 'Level 3', pct: '1%',  desc: 'Third generation',        color: '#B060FF' },
    ],
    note: '💡 Bonus diamonds land in your account automatically at the moment a referral pays. Your unique link and stats are in your Dashboard.',
  },

  security: {
    title: 'Anti-Ban & Security',
    intro: 'Total Hunter is built so the game\'s servers see it as a real, slightly tired player — not a machine:',
    rows: [
      { icon: '⏱', title: 'Floating Timings', desc: 'Pauses between clicks are never the same (random 0.4 to 0.9 sec).' },
      { icon: '🖱', title: 'Hand Tremor',      desc: 'The bot never clicks the same pixel twice. There\'s always a micro-offset of ±5–8 px.' },
      { icon: '🛑', title: 'Full Control',     desc: 'The bot doesn\'t lock the system permanently. One press of ESC — and it stops instantly.' },
      { icon: '🔒', title: 'Legal Interface',  desc: 'We don\'t hack the game API or inject into memory. The bot simply "watches" your monitor and moves the mouse — just like you.' },
    ],
  },

  faq: {
    title: 'Frequently Asked Questions (FAQ)',
    rows: [
      { q: 'Can I watch YouTube or work while the bot is running?',
        a: 'No. The bot physically controls your cursor. If you touch the mouse, you\'ll throw off its aim. Best to leave the bot running overnight or use a second (old) laptop/PC dedicated to farming.' },
      { q: 'Will the bot steal my game account?',
        a: 'This is technically impossible. The bot has no idea what your Total Battle login or password is. You log in to the game yourself, and the bot simply works on top of the open window.' },
      { q: 'What is HWID and why does it matter?',
        a: 'Hardware ID is your PC\'s unique motherboard number. Trial diamonds and the active session are tied to it to protect the system from multi-accounting.' },
      { q: 'I bought a new computer. How do I transfer the bot?',
        a: 'Go to your Dashboard on the website, open the "Devices" section, click "Unbind current device". Then simply log in to the bot on your new PC.' },
      { q: 'My internet dropped and the bot froze. Did I lose diamonds?',
        a: 'No. Balance is deducted only upon a successful "Send march" click or after an exchange is found. Crashes and idle time are free.' },
      { q: 'Is there a risk of getting banned in the game?',
        a: 'There is always some risk with any clicker tool. However, our masking algorithms ("hand tremor", random pauses) reduce that risk to statistical noise. No bans have been recorded during testing.' },
    ],
  },

  cta: {
    title: 'Ready to Automate the Grind?',
    sub: 'Get 100 diamonds right after registration. No credit card required.',
    btnDashboard: 'Go to Dashboard →',
    btnStart: 'Start for Free →',
  },
}
