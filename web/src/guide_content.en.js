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
    { id: 'tuning',       label: '⚙ Sending Carter' },
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
    { name: 'Scout',  price: '$3',  diamonds: '1,000', bonus: '',          color: '#64B5F6' },
    { name: 'Hunter', price: '$5',  diamonds: '2,000', bonus: '+20%',      color: '#3D7FFF' },
    { name: 'Ultra', price: '$10', diamonds: '5,000', bonus: 'MAX VALUE', color: '#00CFFF', popular: true },
  ],

  whatIs: {
    title: 'What is Total Hunter',
    intro: 'Total Hunter is a desktop assistant bot for automating routine tasks in Total Battle. The app handles the mindless searching and clicking, saving your time:',
    exchange: {
      title: 'Exchange Hunting',
      desc: 'Two modes. "Snake" scans coastlines and, once it finds a mercenary market, plays a sound alert and stops so you have time to buy troops. "Scanner 2.0" captures the map fast while a neural network processes frames in the background; finds go to the SWARM.',
    },
    crypt: {
      title: 'Crypt Farming',
      desc: 'The bot recognizes the crypt types you need (Common, Rare, Epic) and sends Carter to collect automatically, applying march speed-ups on its own.',
    },
    outro: 'For clans, the bot collects chests from clan gifts, and the website keeps the clan table and the Ancient calculator (see sections below). The program works on top of your game window (browser or client), imitating the clicks and pauses of a real player.',
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
      { param: 'Internet',   value: 'Stable connection (account and diamond balance checks; the neural network runs on your PC)' },
      { param: 'Account',    value: 'Any active in-game profile' },
    ],
  },

  install: {
    title: 'Quick Start: Installation',
    intro: 'From sign-up to first launch takes no more than 5 minutes. No complex Python setup — everything is already bundled inside.',
    steps: [
      { title: 'Sign Up',        desc: 'Log in at total-hunter.com using your Google account.' },
      { title: 'Free Trial',     desc: 'In the bot, click "Get 300 trials" — you get 300 diamonds to test all bot features.', note: 'Trial is issued once per unique device (HWID).' },
      { title: 'Download',       desc: 'Download TotalHunter.zip from the website and extract it to any folder. Do not run the program from inside the archive.' },
      { title: 'Windows Defender', desc: 'If needed, add the program and its folder to Windows Defender exclusions — otherwise it may interfere with the bot.' },
      { title: 'Launch',         desc: 'Open TotalHunter.exe from the extracted folder. No installation required.' },
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
      { title: 'Choose a profile',     desc: 'At the top of the tab pick a profile (Client, Browser 1 or Browser 2).' },
      { title: 'Set Points A and B',   desc: 'In the target list click "1. Point A" and mark the mini-map center, then "2. Point B" and the Silver plus sign.' },
      { title: 'Other targets',        desc: 'Click targets 3–13 one by one and use the arrows below the list to line up the bot\'s aim with the game buttons.' },
      { title: 'Save',                 desc: 'Click "Save" at the top of the tab. Next time the bot will load these settings automatically.' },
    ],
    slotsNote: '💡 3 independent profile slots. You can play from a browser and from the official client. Save a separate calibration, slider settings, and click tuning for each. Switching between them takes one second.',
  },

  modes: {
    title: 'Operating Modes',
    exchange: {
      title: 'Exchange Hunting',
      cost: '10 diamonds / find',
      rows: [
        { l: 'How it works', t: '"Snake" continuously scans coastlines by moving the map; "Scanner 2.0" captures the map fast and processes frames with a neural network in the background.' },
        { l: 'Result',       t: 'Once it spots an exchange — it stops and plays a loud sound. You buy the mercenaries yourself.' },
        { l: 'Settings',     t: 'See "Fine-Tuning the Bot" below for details.' },
      ],
    },
    crypt: {
      title: 'Crypt Farming',
      cost: '1 diamond / dispatch',
      rows: [
        { l: 'How it works',  t: 'Finds crypts in the search menu, clicks their coordinates, presses "Speed Up", and sends Carter.' },
        { l: 'Smart cycle',   t: 'The bot calculates flight time on its own. It waits for Carter and immediately sends him to the next crypt.' },
        { l: 'Full control',  t: 'You set the max march range (in seconds), the number of speed-ups, and auto-stop by crypt count or time.' },
      ],
    },
    stopNote: 'Emergency stop: press the ESC key on your keyboard. The bot will freeze instantly.',
  },

  tuning: {
    title: 'How the Bot Sends Carter',
    intro: 'In Crypts mode the bot sends Carter and presses the speed-ups itself — you don\'t have to do it by hand. Click accuracy on these buttons is set up in the Calibration tab.',
    botLabel: 'How the bot automates the routine',
    steps: [
      { title: 'Waits for Carter',    desc: 'The bot scans the "Watchtower" icon. As soon as it changes color — Carter is home.', img: '/img/tune_wt_icon.png' },
      { title: 'Sends him out again', desc: 'Opens the captain window and clicks "Explore". Carter immediately flies out again.', img: '/img/tune_carter.png' },
      { title: 'Catches the march',   desc: 'In the active march list the bot finds Carter\'s bar and presses "Speed up".', img: '/img/tune_speed_up.png' },
      { title: 'Applies boosts',      desc: 'Automatically picks the most efficient available accelerator and clicks "Use".', img: '/img/tune_march_accel.png' },
    ],
    note: '💡 Crypts, Chests and "Scanner 2.0" never run at the same time — the bot makes sure the modes don\'t interfere with each other.',
  },

  chests: {
    title: 'Chests: clan tracking',
    intro: 'The bot opens clan gifts in the game and records every chest: who earned it and which event it came from. The site turns these records into a season table: points, quotas, player ranking and a public page for the whole clan.',
    botLabel: 'Step 1. Collect with the bot',
    botSteps: [
      { title: 'Auto-open', desc: 'The bot goes to the clan gifts tab and opens all available chests one by one.', img: '/img/chest_open.png' },
      { title: 'Nickname', desc: 'Reads the "From:" field — which clan member earned the chest.', img: '/img/chest_sender.png' },
      { title: 'Chest type', desc: 'Reads the "Source:" field — which event the chest came from; points depend on it.', img: '/img/chest_type.png' },
    ],
    botHowLabel: 'How to start collecting',
    botHow: [
      { title: 'Choose the clan', desc: 'In the bot "Chests" tab pick a saved "kingdom · clan" pair from the list, or type the kingdom number and clan name and save it with 💾. Chests go to the clan selected at the moment you press START.' },
      { title: 'START', desc: 'Open the clan gifts tab in the game and press START. The bot collects chests to the end of the list. Collected chests are stored on your PC until they are sent.' },
      { title: 'Sending', desc: '"SEND TO SERVER" sends everything collected as one batch — 10 diamonds per send, no matter how many chests are in it. With "Auto-send" on, the bot sends by itself when the list ends or 5000 chests are collected. After a successful send the records are removed from the PC.' },
    ],
    webLabel: 'Step 2. Set up on the site (Dashboard → Chests)',
    webSteps: [
      { title: 'The clan appears by itself', desc: 'After the first send from the bot the clan appears in the dashboard of whoever sent it. To hand control to another leader, use "Generate transfer code"; they enter it and press "Claim management".' },
      { title: 'Preset — ready-made points', desc: 'A preset is a ready template of chest prices in points for a clan level (T5–T9), so you do not have to price dozens of chests by hand. T9 is the working setup of an experienced clan, T5–T8 is a basic crypt set. Pick a preset and press "Load Preset": known chests get their points, missing ones are added as "Counted". The preset does not change the "Accounting" of chests you already set. Then adjust points to your clan rules and press "Save".' },
      { title: 'Clan language', desc: 'The language used for chest names in the clan table.' },
      { title: 'Points and "Accounting" per chest', desc: 'For each chest type set points and choose "Accounting": "Not counted" — hidden, no points; "Counted" — gives points; "Quota 1–3" — gives points and is also counted in its quota column.' },
      { title: 'Season quotas', desc: 'Up to 3 quotas at once, e.g. "Epic Crypts" and "EMC" (Epic Monster Chests). Each has a name and a target: how many chests of that kind a player must collect per season.' },
      { title: 'Players', desc: '"Players" tab: if the bot misread a nickname, set the "Correct Name" — all variants merge into one player. You can also add a player manually and fill in rank, troops and Hero level.' },
      { title: 'Season', desc: 'Set the clan time zone, period start and end and the points target, then press "Save". Dates and targets can be changed after the start — the table recalculates.' },
      { title: 'Public page', desc: 'The clan gets its own link like total-hunter.com/c/450/hot. Members open it from a phone without registering: sort by any column, Russian/English. With "Enter troops" players fill in their rank, troops and Hero level themselves.' },
      { title: 'End of season', desc: 'On the end date the season moves to "History" automatically (kept for 90 days) and the next season of the same length starts. To finish earlier use "Close Season Early". "Download statistics (CSV)" exports all seasons for analysis in Excel/Google Sheets.' },
    ],
    exampleLabel: 'Example: points and quotas',
    example: {
      intro: 'Chest setup in the dashboard:',
      setupHead: ['Chest', 'Points', 'Accounting'],
      setup: [
        ['Epic Crypt 30', '80', 'Quota 1 "Epic Crypts"'],
        ['Rare Crypt 30', '65', 'Counted'],
        ['Epic Basilisk', '30', 'Quota 2 "EMC"'],
        ['Common Crypt 25', '5', 'Not counted'],
      ],
      collected: 'The player collected: 3 × Epic Crypt 30, 2 × Rare Crypt 30, 4 × Epic Basilisk, 10 × Common Crypt 25.',
      resultHead: ['Player', 'Points', 'Epic Crypts /20', 'EMC /50'],
      result: ['Player', '490', '3', '4'],
      explain: 'Points: 3×80 + 2×65 + 4×30 = 490. Common Crypt 25 is "Not counted" — no points and not shown in the table. Quota columns count chests, not points: Epic Crypts — 3 of 20, EMC — 4 of 50.',
    },
    nuancesLabel: 'Details',
    nuances: [
      { title: 'Target (points)', desc: 'The nickname colour shows progress: below target — from red to yellow, target reached — the name shimmers, far above target — "legendary" colour and larger font. Ranking is by points.' },
      { title: 'A quota counts chests, not points', desc: 'Points are the sum over all counted chests. A quota is a separate counter of one kind of chest. One chest can give points and count towards a quota at the same time.' },
      { title: 'Personal quota by Hero level', desc: 'A quota can use "Personal target by Hero level" (meant for EMC): a stronger Hero gets a higher target, a weaker one — lower. The quota target is the norm for a typical player with Hero level H₀; k is how many % the target changes per 100 Hero levels. Without a Hero level a player gets the base target marked "?". The formula is temporary and will be refined from season statistics.' },
      { title: 'The bot counts every chest', desc: '"Not counted" only hides a chest from the table — the data is kept. If you turn counting on later, those chests appear in the season.' },
      { title: 'Season follows collection time', desc: 'A chest belongs to the season in which the bot collected it. To get everything into a season, collect and send before it ends.' },
    ],
    note: '💡 All history is kept: closed seasons stay in the archive for 90 days.',
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
      { name: 'Dive Depth',          range: '1 – 10 (Scanner 2.0: up to 50)',       optimal: '3–6',       desc: 'How many screens deep the bot goes inland before turning back.' },
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
      { name: 'March Range',          range: '10 – 600 s',   optimal: '120 s', desc: 'Critical parameter. The bot won\'t go to a crypt if it takes longer than this to get there.', highlight: true },
      { name: 'Stop (count)',         range: 'Off / 10–200', optimal: 'as needed', desc: 'Automatically stops collection after N crypts have been collected this session.' },
      { name: 'Stop (hours)',         range: 'Off / 1–12 h', optimal: 'as needed', desc: 'Automatically stops collection N hours after the session started.' },
      { name: 'Reset to Start',       range: 'Off / 10–60 min', optimal: '20 min', desc: 'Over a long session the crypt list gradually drifts down, increasing march distance. This periodically resets the list back to the top (the same "Arena x2" trick used at the normal end of the list) — independently of it.', highlight: true },
      { name: 'Detection Frequency',  range: '0.0 – 4.0 s',  optimal: '0.8–1.5 s', desc: 'Speed at which the bot scrolls through the crypt search menu.' },
      { name: 'Click Tuning (X/Y)',   range: 'X + Y axes',   optimal: '1–5 px',   desc: 'IMPORTANT: If the bot slightly misses buttons (due to font or Windows scaling quirks), you can manually shift its "aim" horizontally (X) and vertically (Y). Configured in the CALIBRATION tab: click the target in the list and move the aim with the arrows.', img: '/img/swing1.png', highlight: true },
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
      { label: 'Uploaded chests to the site (per batch)', cost: '−10 diamonds', color: '#F59E0B' },
      { label: 'Searched but found nothing',       cost: 'Free',         color: 'var(--on-surface2)' },
      { label: 'Registration (Trial)',             cost: '+300 diamonds', color: 'var(--credits-gold)' },
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
      { icon: '⏱', title: 'Floating Timings', desc: 'Pauses between clicks are never the same — a random length every time.' },
      { icon: '🖱', title: 'Hand Tremor',      desc: 'The bot never clicks the same pixel twice — there is always a small random offset.' },
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
        a: 'Go to your Dashboard on the website and click "Unbind device" in the "Devices" block. Then simply log in to the bot on your new PC.' },
      { q: 'My internet dropped and the bot froze. Did I lose diamonds?',
        a: 'No. Balance is deducted only upon a successful "Send march" click or after an exchange is found. Crashes and idle time are free.' },
      { q: 'Is there a risk of getting banned in the game?',
        a: 'There is always some risk with any clicker tool. However, our masking algorithms ("hand tremor", random pauses) reduce that risk to statistical noise. No bans have been recorded during testing.' },
    ],
  },

  cta: {
    title: 'Ready to Automate the Grind?',
    sub: 'Get 300 diamonds right after registration. No credit card required.',
    btnDashboard: 'Go to Dashboard →',
    btnStart: 'Start for Free →',
  },
}
