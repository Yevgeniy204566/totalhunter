================================================================================
  Total Hunter — Quick Start Guide / Краткое руководство
  total-hunter.com | discord.gg/7dJQdF2pBG
================================================================================

================================================================================
  ENGLISH
================================================================================

1. INSTALLATION
   Step 1. Extract the archive. Right-click TotalHunter.zip ->
           "Extract All..." (or WinRAR / 7-Zip -> "Extract to
           TotalHunter\") into any folder, e.g. C:\TotalHunter.
   Step 2. Open the extracted folder.
   Step 3. Run TotalHunter.exe FROM THIS FOLDER.
   Step 4. Sign in with your Google account.

   IMPORTANT: Do NOT run TotalHunter.exe from inside the archive
   window (WinRAR / 7-Zip / Explorer zip view) - the bot then starts
   from a temporary folder, may crash, and your calibration and
   settings will not be saved. Always extract first, then run from
   the folder.

   Updates are installed automatically on start. Your calibration,
   tuning, crypt and exchange settings are kept - an update never
   overwrites them.

   IMPORTANT: If login/account linking shows "Connection error" even
   though your internet works fine, your antivirus may be silently
   blocking TotalHunter.exe from reaching the internet (the app is not
   digitally signed, so some antivirus products flag it by default).
   Add TotalHunter.exe / TotalHunter folder to your antivirus
   exceptions/allow-list, or temporarily disable the antivirus and
   try again.

   WINDOWS PROTECTION (Windows 10 / 11): The program is not digitally
   signed yet, so Windows may treat it as unknown and block it. This
   is expected and only needs to be set up once:
   - Blue "Windows protected your PC" window -> "More info" ->
     "Run anyway".
   - Windows Defender -> add the program folder to exclusions:
     Windows Security -> Virus & threat protection -> Manage settings
     -> Exclusions -> Add an exclusion -> Folder.
   - Windows 11 only: if you see "An Application Control policy has
     blocked this file" on start, turn off Smart App Control:
     Windows Security -> App & browser control. Windows only lets you
     turn it back on after reinstalling the system.

--------------------------------------------------------------------------------
2. CALIBRATION (one time only)
   Open the game exactly as you will play it (browser or client).

   Point A — Minimap center:
     Zoom the minimap to minimum. Click precisely in the center of the
     minimap rectangle.

   Point B — Resource zone — Silver:
     Find the Silver icon, hover the cursor until "+" appears.
     Click precisely on the "+" symbol.

   Save the profile: Client / Browser 1 / Browser 2

--------------------------------------------------------------------------------
3. CRYPTS
   March range      — 10–600 s (optimal 120 s)
   March speed      — 0–5
   Click speed      — 0.0 s
   Swing 1          — Explore     — 0  (adjust if clicking misses)
   Swing 2          — Speed-up    — 0  (adjust if clicking misses)
   Stop (count)     — auto-stop after N crypts collected
                      (Off / 10 / 20 / 30 / 50 / 80 / 100 / 200)
   Stop hours       — auto-stop after N hours (Off / 1 / 2 / 3 / 4 / 6 / 9 / 12)
   Reset to start   — periodically re-opens the crypt list from the beginning
                      (Off / 10 / 20 / 30 / 60 min). Over a long session the
                      list gradually drifts to farther crypts, increasing
                      march time — this brings it back to the top on a timer,
                      independent of the normal end-of-list reset.
   Collected: N     — live counter above the START button, resets every
                      new session.

   Select crypt types -> scroll map to maximum zoom -> COLLECT CRYPTS

--------------------------------------------------------------------------------
4. CHESTS - collection and clan tracking
   The bot opens clan gifts in the game and records every chest: who
   earned it ("From:") and which event it came from ("Source:"). The
   site turns these records into a season table: points, quotas,
   player ranking and a public page for the whole clan.

   STEP 1. COLLECT WITH THE BOT (Chests tab)
   1. Choose the clan: pick a saved "kingdom - clan" pair from the
      list, or type the kingdom number and clan name and save it
      with the disk button. Chests go to the clan selected at the
      moment you press START.
   2. Open the clan gifts tab in the game and press START. The bot
      collects chests to the end of the list. Collected chests are
      stored on your PC until they are sent.
   3. "SEND TO SERVER" sends everything collected as one batch -
      10 diamonds per send, no matter how many chests are in it.
      With "Auto-send" on, the bot sends by itself when the list ends
      or 5000 chests are collected. After a successful send the
      records are removed from the PC.

   Click speed  - pause between clicks (actual pause is always 0.3+ s
                  due to recognition time)
   Light / Full - OCR languages for player names
                  Light = Latin + Cyrillic (fast)
                  Full  = all 19 languages (slower, for non-Latin names)

   TUNING (if the bot clicks in the wrong place):
     Calibration tab -> Tuning -> select the item -> D-Pad arrows.

   STEP 2. SET UP ON THE SITE (total-hunter.com -> Dashboard -> Chests)
   - The clan appears by itself after the first send from the bot, in
     the dashboard of whoever sent it. To hand control to another
     leader: "Generate transfer code" -> they enter it and press
     "Claim management".
   - Preset: ready chest prices in points for a clan level (T5-T9).
     Pick a preset -> "Load Preset", then adjust points -> "Save".
   - For each chest type set points and "Accounting":
       Not counted - hidden, no points (data is kept)
       Counted     - gives points
       Quota 1-3   - gives points and counts in its quota column
   - Quotas: up to 3 at once (e.g. "Epic Crypts", "EMC"), each with a
     target - how many chests of that kind a player must collect per
     season. A quota counts chests, not points.
   - Players tab: if a nickname was misread, set the "Correct Name" -
     all variants merge into one player.
   - Season: clan time zone, start and end dates, points target ->
     "Save". A chest belongs to the season in which it was collected -
     collect and send before the season ends.
   - Public page: the clan link (e.g. total-hunter.com/c/450/hot) opens
     from a phone without registration.
   - At the end date the season moves to "History" (kept 90 days) and
     the next one starts. "Download statistics (CSV)" exports all
     seasons.

   Full guide with examples: total-hunter.com/guide

--------------------------------------------------------------------------------
5. EXCHANGES
   Work speed    — 0.5–0.9 s
   Step          — 15–19 px
   Dive depth    — 4–6

   Disable the player-cities layer -> scroll map to minimum zoom -> START

   Speaker button (next to the balance): 🔊 = sound on, 🔇 = sound off.
   When off, there is no sound alert for found exchanges (Exchange 1.0,
   2.0 and ROY). The choice is remembered.

--------------------------------------------------------------------------------
6. ANCIENT (tournament roster)
   The Ancient tab is used to track damage quotas in tournament events
   (e.g. The Ancient). It reads the tournament roster from the game screen
   and uploads it to your clan's dashboard on total-hunter.com.

   How to use:
   1. Open the tournament roster in the game (Старший / Ancient menu).
   2. Switch to the Ancient tab in Total Hunter.
   3. Click SCAN — the bot reads all visible rows.
   4. Click SUBMIT to send the data to the server.

   The dashboard shows each member's damage contribution and highlights
   players who have not yet met the minimum quota set by the leader.

--------------------------------------------------------------------------------
7. CALIBRATION TUNING (fine-tuning click positions)
   If the bot clicks slightly off-target (misses buttons), use Tuning:

   1. Open the Calibration tab.
   2. In the Tuning section, select the action you want to fix from the list:
        Calibration        — shows calibration point reference images
        Watchtower icon    — click on the watchtower icon on the map
        Send Carter        — click to send Carter march
        Speed-up (Carter)  — click to speed up Carter march
        Use acceleration   — click to apply march acceleration
        Player name        — chest player-name field
        Source             — chest source field
        Open chests        — chest collection confirm button
   3. The screenshot shows exactly which button is being adjusted.
   4. Use the D-Pad arrows (▲ ▼ ◄ ►) to shift the click position.
      Step: 1px = fine, 5px = coarse.
   5. Click SAVE PROFILE to keep the changes.

--------------------------------------------------------------------------------
8. FAQ
   Bot misses "Explore"?            -> Swing 1 with + / - buttons
   Finds wrong objects?             -> set search accuracy to 0.8
   No credits?                      -> total-hunter.com or Fortune Wheel
   Chest bot clicks wrong button?   -> Calibration tab -> Tuning -> D-Pad
   Bot window does not fit?         -> drag any window edge; scroll with
                                       the vertical/horizontal scrollbars

--------------------------------------------------------------------------------
9. CHANGING THE ALERT SOUND
   The sound that plays when an Exchange or ROY swarm is found is:

     TotalHunter\_internal\Logo_exchange.wav

   To use your own sound:
   1. Prepare a WAV file (PCM, 8-bit or 16-bit, any sample rate).
   2. Open the "_internal" folder next to TotalHunter.exe.
   3. Replace "Logo_exchange.wav" with your file.
      IMPORTANT: keep the filename exactly "Logo_exchange.wav".
   4. Restart TotalHunter.exe.

   If the file is missing or corrupted the bot will fall back to a
   system beep — this is normal.

--------------------------------------------------------------------------------
Full guide : total-hunter.com/guide
Community  : discord.gg/7dJQdF2pBG
Support    : totalhunter.support@gmail.com
================================================================================


================================================================================
  РУССКИЙ
================================================================================

1. УСТАНОВКА
   Шаг 1. Распакуй архив. Правый клик по TotalHunter.zip ->
          «Извлечь всё...» (или WinRAR / 7-Zip -> «Извлечь в
          TotalHunter\») в любую папку, например C:\TotalHunter.
   Шаг 2. Открой распакованную папку.
   Шаг 3. Запусти TotalHunter.exe ИЗ ЭТОЙ ПАПКИ.
   Шаг 4. Войди через Google-аккаунт.

   ВАЖНО: НЕ запускай TotalHunter.exe прямо из окна архива
   (WinRAR / 7-Zip / просмотр zip в Проводнике) — бот стартует из
   временной папки, может упасть, а калибровка и настройки не
   сохранятся. Всегда сначала распаковать, потом запускать из папки.

   Обновления ставятся автоматически при запуске. Калибровка, тюнинг,
   настройки склепов и бирж сохраняются — обновление их не трогает.

   ВАЖНО: Если при входе/привязке аккаунта пишет "Connection error"
   (ошибка соединения), хотя интернет работает — скорее всего,
   антивирус молча блокирует TotalHunter.exe (программа без цифровой
   подписи, некоторые антивирусы блокируют такие .exe по умолчанию).
   Добавь TotalHunter.exe / папку TotalHunter в исключения антивируса,
   либо временно отключи антивирус и попробуй снова.

   ЗАЩИТА WINDOWS (Windows 10 / 11): У программы пока нет цифровой
   подписи, поэтому Windows может принять её за незнакомую и
   заблокировать. Это нормально и настраивается один раз:
   - Синее окно «Windows защитил ваш компьютер» -> «Подробнее» ->
     «Выполнить в любом случае».
   - Windows Defender -> добавь папку с программой в исключения:
     Безопасность Windows -> Защита от вирусов и угроз -> Управление
     настройками -> Исключения -> Добавить исключение -> Папка.
   - Только Windows 11: если при запуске появляется ошибка
     «An Application Control policy has blocked this file», выключи
     «Интеллектуальное управление приложениями»: Безопасность Windows ->
     Управление приложениями/браузером. Включить его обратно Windows
     позволяет только после переустановки системы.

--------------------------------------------------------------------------------
2. КАЛИБРОВКА (один раз)
   Открой игру так, как будешь играть (браузер или клиент).

   Точка A — Центр мини-карты:
     Уменьши зум мини-карты до минимума. Кликни точно по центру
     прямоугольника мини-карты.

   Точка B — Зона ресурсов — Серебро:
     Найди иконку Серебра, наведи курсор до появления «+».
     Кликни точно по символу «+».

   Сохрани профиль: Клиент / Браузер 1 / Браузер 2

--------------------------------------------------------------------------------
3. СКЛЕПЫ
   Дальность марша    — 10–600 с (оптимум 120 с)
   Ускорение марша    — 0–5
   Скорость кликов    — 0.0 с
   Swing 1            — Исследовать — 0  (настрой, если мажет)
   Swing 2            — Ускорение   — 0  (настрой, если мажет)
   Стоп (штуки)       — авто-остановка после N собранных склепов
                        (Выкл / 10 / 20 / 30 / 50 / 80 / 100 / 200)
   Стоп часы          — авто-остановка через N часов
                        (Выкл / 1 / 2 / 3 / 4 / 6 / 9 / 12)
   Сброс в начало     — периодически возвращает список склепов в начало
                        (Выкл / 10 / 20 / 30 / 60 мин). За долгую сессию
                        список постепенно "уезжает" на более дальние склепы,
                        увеличивая время марша — эта настройка возвращает его
                        в начало по таймеру, независимо от обычного сброса
                        по концу списка.
   Собрано склепов: N — живой счётчик над кнопкой СТАРТ, обнуляется в
                        начале каждой новой сессии.

   Выбери типы склепов -> прокрути карту на максимум -> ЗАПУСТИТЬ СБОР СКЛЕПОВ

--------------------------------------------------------------------------------
4. СУНДУКИ — сбор и учёт для клана
   Бот открывает клановые подарки в игре и записывает каждый сундук:
   кто его добыл («From:») и из какого он события («Source:»). Сайт
   превращает эти записи в таблицу сезона: очки, квоты, рейтинг
   игроков и публичную страницу для всего клана.

   ШАГ 1. СБОР В БОТЕ (вкладка Сундуки)
   1. Выбери клан: сохранённую пару «королевство · клан» из списка,
      или впиши номер королевства и название клана и сохрани
      кнопкой с дискетой. Сундуки попадают в тот клан, который был
      выбран в момент нажатия СТАРТ.
   2. Открой в игре вкладку клановых подарков и нажми СТАРТ. Бот
      собирает сундуки до конца списка. Собранное хранится на твоём
      ПК, пока не будет отправлено.
   3. «ОТПРАВИТЬ НА СЕРВЕР» отправляет всё собранное одним пакетом —
      10 алмазов за отправку, сколько бы сундуков в ней ни было.
      С включённой «Авто-отправкой» бот отправляет сам, когда список
      закончился или набралось 5000 сундуков. После успешной отправки
      записи на ПК удаляются.

   Скорость клика — пауза между кликами (реальная пауза всегда 0.3+ с
                    из-за времени распознавания)
   Light / Full   — языки OCR для имён игроков
                    Light = Латиница + Кириллица (быстро)
                    Full  = все 19 языков (медленнее, для нелатинских имён)

   ТЮНИНГ (если бот кликает не туда):
     Вкладка Калибровка -> Тюнинг -> выбери пункт -> стрелки D-Pad.

   ШАГ 2. НАСТРОЙКА НА САЙТЕ (total-hunter.com -> Личный кабинет -> Сундуки)
   - Клан появляется сам после первой отправки из бота — в кабинете у
     того, кто отправил. Передать управление другому лидеру:
     «Сгенерировать код передачи» -> он вводит код у себя и нажимает
     «Принять управление».
   - Пресет: готовые цены сундуков в очках для уровня клана (T5–T9).
     Выбери пресет -> «Загрузить пресет», поправь очки -> «Сохранить».
   - Для каждого типа сундука задай очки и «Учёт»:
       Не в учёте — не показывается, очков не даёт (данные сохраняются)
       В учёте    — даёт очки
       Квота 1–3  — даёт очки и считается в столбце своей квоты
   - Квоты: до 3 одновременно (например «Epic Crypts», «EMC»), у каждой
     цель — сколько сундуков этого вида игрок должен собрать за сезон.
     Квота считает сундуки, а не очки.
   - Вкладка «Игроки»: если ник распознан с ошибкой, укажи «Правильное
     имя» — все варианты сложатся в одного игрока.
   - Сезон: часовой пояс клана, начало и конец, цель по очкам ->
     «Сохранить». Сундук попадает в тот сезон, в который бот его
     собрал — собери и отправь до окончания сезона.
   - Публичная страница: ссылка клана (например
     total-hunter.com/c/450/hot) открывается с телефона без регистрации.
   - В дату окончания сезон уходит в «Историю» (хранится 90 дней) и
     начинается следующий. «Скачать статистику (CSV)» выгружает все
     сезоны.

   Полный гайд с примерами: total-hunter.com/guide

--------------------------------------------------------------------------------
5. БИРЖИ
   Скорость работы  — 0.5–0.9 с
   Шаг              — 15–19 px
   Глубина нырка    — 4–6

   Отключи слой городов -> прокрути карту на минимум -> СТАРТ

   Кнопка-динамик (рядом с балансом): 🔊 — звук включён, 🔇 — выключен.
   Когда выключен, звукового оповещения о найденных биржах нет
   (Биржа 1.0, 2.0 и РОЙ). Выбор запоминается.

--------------------------------------------------------------------------------
6. ДРЕВНИЙ (турнирный ростер)
   Вкладка Древний используется для отслеживания квот урона в турнирных
   ивентах (например, «Древний»). Бот считывает ростер прямо с экрана игры
   и загружает данные в кабинет клана на total-hunter.com.

   Как пользоваться:
   1. Открой меню ростера в игре (Старший / Древний).
   2. Переключись на вкладку Древний в Total Hunter.
   3. Нажми СКАНИРОВАТЬ — бот считает все видимые строки.
   4. Нажми ОТПРАВИТЬ — данные уйдут на сервер.

   В кабинете отображается вклад каждого участника и подсвечиваются
   игроки, которые не выполнили минимальную квоту, заданную лидером.

--------------------------------------------------------------------------------
7. ТЮНИНГ КАЛИБРОВКИ (точная настройка позиций кликов)
   Если бот чуть промахивается по кнопкам — используй Тюнинг:

   1. Открой вкладку Калибровка.
   2. В разделе Тюнинг выбери нужное действие из списка:
        Калибровка         — показывает референсные скрины точек А и Б
        Дозорная башня     — клик по иконке дозорной башни на карте
        Отправка Картера   — клик для отправки марша Картера
        Ускорить (Картер)  — клик ускорения марша Картера
        Использовать ускор — клик применения ускорения марша
        Имя игрока         — поле имени игрока в сундуках
        Источник           — поле источника в сундуках
        Открыть (сундуки)  — кнопка подтверждения сбора сундука
   3. Скриншот показывает именно ту кнопку, которую ты настраиваешь.
   4. D-Pad стрелки (▲ ▼ ◄ ►) сдвигают позицию клика.
      Шаг: 1px — точно, 5px — грубо.
   5. Нажми СОХРАНИТЬ ПРОФИЛЬ.

--------------------------------------------------------------------------------
8. ЧАСТЫЕ ВОПРОСЫ
   Бот мажет по «Исследовать»?     -> Swing 1 кнопками + / -
   Находит не то?                  -> точность поиска 0.8
   Нет кредитов?                   -> total-hunter.com или Колесо Фортуны
   Сундуки кликают не туда?        -> Калибровка -> Тюнинг -> D-Pad
   Окно бота не помещается?        -> потяни окно за любой край;
                                      прокрутка — вертикальная и
                                      горизонтальная полосы

--------------------------------------------------------------------------------
9. КАК ПОМЕНЯТЬ ЗВУК ОПОВЕЩЕНИЯ
   Звук, который играет при нахождении Биржи или роя РОЙ:

     TotalHunter\_internal\Logo_exchange.wav

   Чтобы поставить свой звук:
   1. Подготовь WAV-файл (PCM, 8 или 16 бит, любая частота).
   2. Открой папку "_internal" рядом с TotalHunter.exe.
   3. Замени файл "Logo_exchange.wav" своим файлом.
      ВАЖНО: имя файла должно остаться ровно "Logo_exchange.wav".
   4. Перезапусти TotalHunter.exe.

   Если файл отсутствует или повреждён — бот издаст системный бипер.
   Это нормально, ничего не сломается.

--------------------------------------------------------------------------------
Полный гайд : total-hunter.com/guide
Сообщество  : discord.gg/7dJQdF2pBG
Поддержка   : totalhunter.support@gmail.com
================================================================================
