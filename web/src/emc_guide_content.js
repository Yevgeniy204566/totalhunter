// Подробное описание квоты EMC для игроков и руководителей. Только факты о том, как это
// реально работает; числа в примерах взяты из базовой таблицы (Герой 400 → 19/10/3/4 = 36,
// Герой 385 → 16/9/3/4 = 32, общий ×1.2 на Герое 400 → 23/11/4/5 = 43).
export const EMC_GUIDE = {
  ru: {
    title: 'Как это работает — подробно',
    intro: 'EMC (Epic Monster Chests) — квота на сундуки четырёх эпических монстров: Hydra, Undead, Arachna и Shadow City. Она личная: чем выше уровень Героя игрока, тем больше сундуков от него ждут. Квота считается на сезон 2 недели (14 дней).',
    sections: [
      {
        title: '1. Что такое квота EMC и зачем она',
        paragraphs: [
          'У каждого игрока своя норма: сколько сундуков каждого из четырёх монстров он должен принести за сезон. Норма зависит от уровня его Героя — у сильного Героя больше шансов быстро добить монстра, поэтому и ждут от него больше.',
          'Итоговая норма EMC — это сумма четырёх норм по монстрам. В таблице клана у игрока видны пять полос: по одной на каждого монстра и одна общая — EMC.',
        ],
      },
      {
        title: '2. Как считается ваша норма',
        paragraphs: [
          'Для каждого уровня Героя от 100 до 600 в таблице есть своя строка: сколько сундуков Hydra, Undead, Arachna и Shadow City ждут от игрока. Строки идут с шагом 10 уровней. Если ваш Герой между ступенями (например, 385), значения берутся плавно между соседними ступенями — резких скачков нет.',
          'Пример: Герой 400 — норма 19 Hydra, 10 Undead, 3 Arachna, 4 Shadow City, всего 36 EMC. Герой 385 — 16 Hydra, 9 Undead, 3 Arachna, 4 Shadow City, всего 32 EMC.',
          'Дробные значения округляются один раз в самом конце, отдельно по каждому монстру; EMC — сумма четырёх уже округлённых чисел.',
          'Ниже 100 уровня считается как 100, выше 600 — как 600. Если Герой в таблице игроков не указан, норма считается по Герою 400 и помечается знаком «?» — укажите Героя, и норма станет точной.',
          'База таблицы построена по реальным данным клана за полный сезон. Значения предварительные: их можно уточнять по статистике следующих сезонов.',
        ],
      },
      {
        title: '3. Как читать полосы в таблице клана',
        paragraphs: [
          'В каждой ячейке написано «принесено/норма · процент» и под этим — тёмная полоса. Чем меньше выполнено, тем уже полоса и ближе её цвет к красному; чем ближе к норме — тем зеленее. Выполненная норма — полная зелёная полоса.',
          'Если принесено больше нормы, процент показывается как есть (например, 147%), а полоса остаётся полной: заливка выше 100% не растёт.',
          'Если норма по монстру равна нулю (так бывает у слабых Героев для редких монстров), ничего приносить не нужно — полоса сразу зелёная.',
          'Тот же расчёт видно на отдельной вкладке «Квота EMC» публичной страницы: там вся таблица норм по уровням Героя.',
        ],
      },
      {
        title: '4. Что засчитывается в EMC',
        paragraphs: [
          'В счёт EMC идут все сундуки, у которых в настройках сундуков выбрано «Квота» с названием EMC. Берутся сундуки, которые бот собрал за время сезона: сундук попадает в тот сезон, в котором он был собран.',
          'У каждого сундука в списке сундуков клана есть «Учёт»: «Не в учёте», «В учёте (очки)» или «Квота 1/2/3». Только вариант «Квота» с нужным номером даёт вклад в EMC. «В учёте» даёт только очки, «Не в учёте» скрывает сундук из таблицы — но данные не теряются, и если позже включить учёт, сундук появится в сезоне.',
          'Один сундук может одновременно дать очки и засчитаться в квоту.',
        ],
      },
      {
        title: '5. Все возможные комбинации',
        paragraphs: ['Что произойдёт у игрока в разных ситуациях (пример для Героя 400: норма 19 Hydra, 10 Undead, 3 Arachna, 4 Shadow City, всего 36):'],
        cases: [
          { name: 'Все четыре монстра в норме', text: 'Все четыре полосы полные, EMC — 100%. Квота выполнена.' },
          { name: 'Один монстр сделан с запасом, другие не добраны', text: 'Добор одного монстра за счёт другого в колонке EMC засчитывается. Например, 30 Hydra, 4 Undead, 1 Arachna, 1 Shadow City — это 36 сундуков, и EMC — 100%, хотя полосы Undead, Arachna и Shadow City не полные. Полосы по отдельным монстрам друг друга не компенсируют: у кого не добрано — остаётся неполная.' },
          { name: 'Перебор по одному монстру', text: 'Сверх нормы засчитывается в общий EMC без ограничений: процент больше 100 показывается как есть.' },
          { name: 'Недобор по всем монстрам', text: 'Полосы неполные и красноватые. Чем ближе к норме, тем зеленее. Пока EMC меньше 100%, квота не выполнена.' },
          { name: 'Норма монстра равна 0', text: 'Для этого монстра ничего приносить не нужно, полоса зелёная. Принесённые сундуки всё равно идут в общий EMC.' },
          { name: 'Герой не указан', text: 'Норма считается по Герою 400 и помечается «?». После указания Героя цель пересчитывается.' },
          { name: 'Герой вырос во время сезона', text: 'Норма считается по текущему уровню Героя, поэтому цель пересчитается. Если нужно зафиксировать, какой Герой был, смотрите архив: он хранит значения на момент закрытия сезона.' },
        ],
      },
      {
        title: '6. Новый сундук: что будет, если его добавить',
        paragraphs: ['Если в списке сундуков клана появляется новый вид сундука (например, от нового эпического монстра), то зависит от того, что выбрать в «Учёте»:'],
        cases: [
          { name: 'Выбрана квота EMC', text: 'Сундук идёт в общий счёт EMC всех игроков, независимо от уровня Героя. Норма при этом не растёт — она по-прежнему сумма четырёх монстров, а своей нормы и своей полосы у нового монстра нет. Поэтому такие сундуки помогают выполнить EMC быстрее. Например, при норме 36 у игрока 36 сундуков четырёх монстров и ещё 5 новых — это 41 из 36, то есть 114%.' },
          { name: 'Выбрано «В учёте»', text: 'Сундук даёт только очки и в EMC не попадает.' },
          { name: 'Выбрано «Не в учёте»', text: 'Сундук скрыт из таблицы и не считается ни в очки, ни в квоту. Данные сохраняются.' },
          { name: 'Название содержит Hydra, Undead, Arachna или Shadow', text: 'Полоса для монстра подбирается по названию столбца. Если в таблице два столбца с одним и тем же словом (например, «Hydra» и «Epic Fire Hydra»), оба сравниваются с одной и той же нормой Hydra.' },
        ],
      },
      {
        title: '7. Множители: как усилить или ослабить квоту',
        paragraphs: [
          'Исходная таблица не меняется. Поверх неё хозяин ростера может включить три множителя: общий (на всю квоту), по каждому монстру и по диапазону уровней Героя. Допустимые значения — от 0.1 до 3.0, пустое поле считается как 1.00.',
          'Порядок расчёта всегда один: таблица → множитель диапазона уровней → множитель монстра → общий множитель → округление. Пример: общий ×1.2 для Героя 400 даёт 23 Hydra, 11 Undead, 4 Arachna, 5 Shadow City, всего 43 EMC.',
          'Меняйте множители по одному: они перемножаются, и эффект быстро накапливается.',
        ],
      },
      {
        title: '8. Что происходит при закрытии сезона',
        paragraphs: [
          'Когда сезон закрывается (по времени или хозяином ростера досрочно), итоги уходят в архив — вкладка «История». Вместе с итогами сохраняются настройки квоты и множители на этот момент, поэтому прошлые сезоны не меняются, даже если позже поправить таблицу.',
          'В новом сезоне считаются только сундуки, собранные в его период; настройки квоты остаются, пока хозяин ростера их не изменит.',
        ],
      },
      {
        title: '9. Для хозяина ростера: как включить и настроить',
        paragraphs: [
          '1) В карточке квоты включите переключатель «Личная цель по уровню Героя». 2) На этой вкладке задайте множители и посмотрите, как меняется таблица. 3) Выберите квоту и нажмите «Применить к сезону» — на публичной странице появятся полосы прогресса и вкладка «Квота EMC». Применение не обнуляет сундуки и не начинает новый сезон; вместе с ним сохраняются и остальные настройки сезона из формы выше.',
          'Таблицу можно скачать в CSV и отправить клану для обсуждения. Менять множители и квоты может только хозяин ростера (тот, кто его создал): руководитель ростера помогает вести игроков, но настройки сезона не меняет.',
        ],
      },
    ],
  },
  en: {
    title: 'How it works — in detail',
    intro: 'EMC (Epic Monster Chests) is a quota for chests from four epic monsters: Hydra, Undead, Arachna and Shadow City. It is personal: the higher a player\'s Hero level, the more chests are expected. The quota is for a 2-week (14-day) season.',
    sections: [
      {
        title: '1. What the EMC quota is for',
        paragraphs: [
          'Every player has their own target: how many chests of each of the four monsters they should bring in a season. The target depends on the Hero level — a stronger Hero finishes monsters faster, so more is expected.',
          'The total EMC target is the sum of the four monster targets. In the clan table a player has five bars: one per monster and one overall — EMC.',
        ],
      },
      {
        title: '2. How your target is calculated',
        paragraphs: [
          'For every Hero level from 100 to 600 the table has a row: how many Hydra, Undead, Arachna and Shadow City chests are expected. Rows go in steps of 10 levels. If your Hero is between steps (for example 385) the values are interpolated smoothly between the neighbouring steps — no sudden jumps.',
          'Example: Hero 400 — target 19 Hydra, 10 Undead, 3 Arachna, 4 Shadow City, 36 EMC total. Hero 385 — 16 Hydra, 9 Undead, 3 Arachna, 4 Shadow City, 32 EMC total.',
          'Fractional values are rounded once at the very end, separately per monster; EMC is the sum of the four rounded numbers.',
          'Below level 100 counts as 100, above 600 as 600. If a player has no Hero level set, the target uses Hero 400 and is marked "?" — enter the Hero level and the target becomes exact.',
          'The table base is built from real clan data for a full season. Values are preliminary and can be refined from the statistics of later seasons.',
        ],
      },
      {
        title: '3. How to read the bars in the clan table',
        paragraphs: [
          'Each cell shows "brought/target · percent" and a dark bar below. The less is done, the shorter the bar and the closer its color is to red; the closer to the target, the greener. A completed target is a full green bar.',
          'If more than the target is brought, the percent is shown as is (for example 147%), and the bar stays full: the fill does not grow above 100%.',
          'If a monster target is zero (it happens for weak Heroes with rare monsters), nothing needs to be brought — the bar is green right away.',
          'The same calculation is shown on the separate "EMC quota" tab of the public page: the whole table of targets by Hero level.',
        ],
      },
      {
        title: '4. What counts toward EMC',
        paragraphs: [
          'EMC counts all chests whose "Accounting" is set to the quota named EMC. Chests collected by the bot during the season are counted: a chest belongs to the season in which it was collected.',
          'Every chest in the clan chest list has "Accounting": "Not counted", "Counted (points)" or "Quota 1/2/3". Only "Quota" with the right number contributes to EMC. "Counted" gives points only; "Not counted" hides the chest from the table — but the data is not lost, and if counting is turned on later, the chest appears in the season.',
          'A single chest can give points and count toward a quota at the same time.',
        ],
      },
      {
        title: '5. All possible combinations',
        paragraphs: ['What happens to a player in different situations (example for Hero 400: target 19 Hydra, 10 Undead, 3 Arachna, 4 Shadow City, 36 total):'],
        cases: [
          { name: 'All four monsters at target', text: 'All four bars are full, EMC is 100%. The quota is complete.' },
          { name: 'One monster over target, others short', text: 'Making up one monster with another counts in the EMC column. For example 30 Hydra, 4 Undead, 1 Arachna, 1 Shadow City is 36 chests, and EMC is 100% even though the Undead, Arachna and Shadow City bars are not full. Per-monster bars do not compensate each other: whoever is short stays incomplete.' },
          { name: 'Overfilling one monster', text: 'Anything above the target counts toward the total EMC without limit: a percent above 100 is shown as is.' },
          { name: 'Short on all monsters', text: 'Bars are incomplete and reddish. The closer to the target, the greener. While EMC is below 100%, the quota is not complete.' },
          { name: 'Monster target is 0', text: 'Nothing needs to be brought for that monster, the bar is green. Chests brought anyway count toward the total EMC.' },
          { name: 'Hero level not set', text: 'The target uses Hero 400 and is marked "?". After the Hero level is entered the target is recalculated.' },
          { name: 'Hero level grew during the season', text: 'The target uses the current Hero level, so it is recalculated. To see which Hero was at the time, check the archive: it keeps the values at the moment the season closed.' },
        ],
      },
      {
        title: '6. A new chest: what happens when it is added',
        paragraphs: ['When a new chest type appears in the clan chest list (for example from a new epic monster), the result depends on what is chosen in "Accounting":'],
        cases: [
          { name: 'Quota EMC is chosen', text: 'The chest counts toward the total EMC of all players, regardless of the Hero level. The target does not grow — it is still the sum of the four monsters, and the new monster has no target and no bar of its own. So such chests help complete EMC faster. For example, with a target of 36, a player with 36 chests of the four monsters and 5 new ones has 41 of 36, which is 114%.' },
          { name: '"Counted" is chosen', text: 'The chest gives points only and does not count toward EMC.' },
          { name: '"Not counted" is chosen', text: 'The chest is hidden from the table and counts neither for points nor for the quota. The data is kept.' },
          { name: 'Name contains Hydra, Undead, Arachna or Shadow', text: 'The monster bar is matched by the column name. If the table has two columns with the same word (for example "Hydra" and "Epic Fire Hydra"), both are compared with the same Hydra target.' },
        ],
      },
      {
        title: '7. Multipliers: how to raise or lower the quota',
        paragraphs: [
          'The original table stays unchanged. On top of it the roster owner can enable three multipliers: global (the whole quota), per monster and by Hero level range. Allowed values are 0.1 to 3.0; an empty field counts as 1.00.',
          'The order of calculation is always the same: table → level range multiplier → monster multiplier → global multiplier → rounding. Example: global ×1.2 for Hero 400 gives 23 Hydra, 11 Undead, 4 Arachna, 5 Shadow City, 43 EMC total.',
          'Change multipliers one at a time: they multiply together and the effect adds up quickly.',
        ],
      },
      {
        title: '8. What happens when a season closes',
        paragraphs: [
          'When a season closes (by time or early by the roster owner), the results go to the archive — the "History" tab. The quota settings and multipliers at that moment are saved with the results, so past seasons do not change even if the table is edited later.',
          'A new season counts only chests collected during its period; the quota settings stay until the roster owner changes them.',
        ],
      },
      {
        title: '9. For the roster owner: how to enable and set up',
        paragraphs: [
          '1) In the quota card turn on the "Personal target by Hero level" switch. 2) On this tab set the multipliers and see how the table changes. 3) Choose the quota and press "Apply to season" — progress bars and the "EMC quota" tab appear on the public page. Applying does not reset chests and does not start a new season; the other season settings from the form above are saved with it.',
          'The table can be downloaded as CSV and sent to the clan for discussion. Only the roster owner (who created it) can change multipliers and quotas: a roster manager helps run the players but does not change season settings.',
        ],
      },
    ],
  },
}
