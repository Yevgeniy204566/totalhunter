import { useNavigate } from 'react-router-dom'
import { useLang } from '../lang.js'

const Section = ({ title, children }) => (
  <div className="card" style={{ marginBottom: 20 }}>
    <h3 style={{ marginBottom: 16, color: 'var(--on-surface)', fontSize: 17, fontWeight: 700 }}>
      {title}
    </h3>
    <div style={{ color: 'var(--on-surface2)', fontSize: 14, lineHeight: 1.85 }}>
      {children}
    </div>
  </div>
)

const P = ({ children }) => <p style={{ marginBottom: 12 }}>{children}</p>
const H4 = ({ children }) => (
  <p style={{ fontWeight: 700, color: 'var(--on-surface)', marginBottom: 6, marginTop: 16 }}>{children}</p>
)
const UL = ({ items }) => (
  <ul style={{ paddingLeft: 20, marginBottom: 12 }}>
    {items.map((it, i) => <li key={i} style={{ marginBottom: 6 }}>{it}</li>)}
  </ul>
)
const Hl = ({ children }) => (
  <strong style={{ color: 'var(--on-surface)' }}>{children}</strong>
)
const Accent = ({ children }) => (
  <strong style={{ color: 'var(--accent)' }}>{children}</strong>
)
const Warn = ({ children }) => (
  <strong style={{ color: '#FF6B6B' }}>{children}</strong>
)

function ContentEN() {
  return (
    <>
      <Section title="1. Terms of Service (Public Offer Agreement)">
        <H4>1.1 Parties</H4>
        <P>
          This Agreement is concluded between <Hl>Total Hunter</Hl> (hereinafter «Service», «We») and any
          individual or legal entity (hereinafter «User») who accesses or uses the Total Hunter website
          and software available at <Accent>total-hunter.com</Accent>.
        </P>
        <P>
          By registering an account, downloading the application, or purchasing diamonds (credits),
          you confirm that you have read, understood, and accepted all terms of this Agreement in full.
          If you do not agree with any part of these terms, you must immediately stop using the Service.
        </P>

        <H4>1.2 Subject of the Agreement</H4>
        <P>
          The Service provides the User with access to a desktop automation assistant («Bot») designed
          for use with the online game Total Battle. The Bot automates routine in-game actions including
          scanning the game map for mercenary exchanges and dispatching units to crypts.
          The Service operates on a prepaid credit (diamond) model.
        </P>

        <H4>1.3 User Registration and Account</H4>
        <UL items={[
          'Registration is performed via Google OAuth. By registering, the User authorizes Total Hunter to store their Google account email address for identification purposes.',
          'Each account is tied to a unique Hardware ID (HWID) — a cryptographic fingerprint of the User\'s device. One free trial (100 diamonds) is issued per device.',
          'The User is solely responsible for maintaining the confidentiality of their account.',
          'The User must be at least 18 years of age, or the minimum legal age in their jurisdiction, to register.',
          'One person may not register multiple accounts to obtain additional free trials. Such accounts will be permanently suspended without refund.',
        ]} />

        <H4>1.4 Diamond Credit System</H4>
        <P>
          Total Hunter uses an internal virtual currency called <Hl>◆ Diamonds</Hl>.
          Diamonds are a prepaid service token and carry no monetary value outside the Service.
          Diamond consumption occurs only on successful bot actions:
        </P>
        <UL items={[
          '−10 diamonds: Mercenary Exchange successfully located.',
          '−1 diamond: Crypt successfully dispatched to Carter.',
          '0 diamonds: No target found, search interrupted, or connection error — no charge.',
        ]} />
        <P>
          Diamonds do not expire. Purchased diamonds remain on the User's account indefinitely
          unless the account is terminated for a violation of these Terms.
        </P>

        <H4>1.5 Acceptable Use</H4>
        <P>The User agrees NOT to:</P>
        <UL items={[
          'Share, resell, or transfer their account credentials or HWID binding to third parties.',
          'Attempt to reverse-engineer, decompile, or modify the Total Hunter application.',
          'Use automated scripts or tools to manipulate the diamond balance or bypass the licensing system.',
          'Create multiple accounts to abuse the free trial system.',
          'Use the Service for any purpose that violates applicable law.',
        ]} />

        <H4>1.6 Service Availability</H4>
        <P>
          The Service is provided «as is». We make reasonable efforts to ensure uptime but do not
          guarantee 100% availability. Scheduled or emergency maintenance may occur without prior notice.
          No diamond compensation is provided for downtime unless it exceeds 72 consecutive hours.
        </P>

        <H4>1.7 Termination</H4>
        <P>
          We reserve the right to suspend or permanently terminate a User's account, without refund,
          in cases of: fraud, abuse of the trial system, violation of acceptable use terms, or
          chargebacks initiated against legitimate purchases. The User may close their account at
          any time by contacting support.
        </P>
      </Section>

      <Section title="2. Privacy Policy">
        <H4>2.1 Data We Collect</H4>
        <UL items={[
          'Email address — obtained from Google OAuth at registration, used solely for account identification and login.',
          'Hardware ID (HWID) — a one-way SHA-256 hash of your network adapter MAC address. We store only the hash, never the raw MAC address.',
          'Usage data — timestamps of bot sessions, diamond transactions, hunt results (aggregated). No game screen recordings or screenshots are stored.',
          'IP address — logged for security and abuse prevention purposes only.',
        ]} />

        <H4>2.2 Data We Do NOT Collect</H4>
        <UL items={[
          'Your Total Battle game login, password, or game account credentials — never requested, never stored.',
          'Screen content or visual data from your game session.',
          'Payment card numbers or banking details — all payments are processed by NOWPayments. We never see or store your payment credentials.',
        ]} />

        <H4>2.3 How We Use Your Data</H4>
        <UL items={[
          'To authenticate your account and verify licensing (HWID + email).',
          'To process diamond transactions and maintain balance history.',
          'To calculate referral rewards and track multi-level referral chains.',
          'To send transactional notifications (purchase confirmations, low balance alerts) if you have opted in.',
          'To detect and prevent fraud and abuse.',
        ]} />

        <H4>2.4 Data Retention</H4>
        <P>
          Account data is retained for the lifetime of the account plus 90 days after deletion.
          Transaction logs are retained for 36 months to comply with financial record-keeping requirements.
          After account deletion, all personal data is purged from active systems within 30 days.
        </P>

        <H4>2.5 Third-Party Services</H4>
        <UL items={[
          'Google OAuth — authentication provider. Subject to Google\'s Privacy Policy.',
          'NOWPayments — cryptocurrency payment processing. Subject to NOWPayments\' Privacy Policy.',
          'Google Cloud Platform (GCP) — server infrastructure. Data is stored in the US region.',
          'Vercel — website hosting. No personal data is processed by Vercel.',
        ]} />

        <H4>2.6 Your Rights</H4>
        <P>
          You have the right to: access a copy of your personal data, request correction of inaccurate data,
          request deletion of your account and associated data, and withdraw consent for optional communications.
          To exercise these rights, contact us at <Accent>totalhunter.support@gmail.com</Accent>.
        </P>

        <H4>2.7 Cookies</H4>
        <P>
          The website uses only essential cookies: a session authentication token stored in localStorage
          (not a cookie, no tracking) and a language preference key. We do not use advertising cookies
          or third-party tracking pixels.
        </P>
      </Section>

      <Section title="3. Game Account Risk Disclaimer">
        <P>
          <Hl>Total Hunter is an independent third-party tool and is not affiliated with, endorsed by,
          or in any way officially connected with Plarium Games Ltd.</Hl> — the developer of Total Battle —
          or any of its subsidiaries.
        </P>
        <P>
          The use of automation software may violate the Terms of Service of Total Battle.
          Plarium Games reserves the right to take action against accounts that use third-party
          automation tools, including but not limited to: temporary suspension, permanent ban,
          or removal of in-game progress and assets.
        </P>
        <P><Warn>By using Total Hunter, you acknowledge and accept that:</Warn></P>
        <UL items={[
          'You use this software entirely at your own risk.',
          'Total Hunter and its developers accept zero liability for any game account restrictions, suspensions, permanent bans, or loss of in-game progress resulting from the use of this software.',
          'No refunds will be issued on the grounds of a game account ban.',
          'We strongly recommend using the bot on secondary or alternate game accounts when first testing.',
        ]} />
        <P>
          We have implemented industry-standard anti-detection measures: randomized action delays
          (0.4–0.9 seconds), randomized click offsets (±5–8 pixels), and direct window interaction
          without API manipulation. However, no automation software can guarantee zero detection risk.
        </P>
      </Section>

      <Section title="4. Refund & Payment Policy">
        <H4>4.1 Accepted Payment Methods</H4>
        <P>
          Payments are processed exclusively through <Hl>NOWPayments</Hl> — a non-custodial
          cryptocurrency payment processor. Accepted currencies include: USDT (TRC-20 / ERC-20),
          Bitcoin (BTC), Ethereum (ETH), BNB, and other major cryptocurrencies supported by NOWPayments.
          All transactions are secured by SSL/TLS encryption.
        </P>
        <P>
          <Warn>Important:</Warn> Cryptocurrency transactions are <Hl>irreversible by nature</Hl>.
          Once a payment is confirmed on the blockchain, it cannot be reversed by the sender or the Service.
          Diamonds are credited automatically upon payment confirmation.
        </P>

        <H4>4.2 Refund Eligibility</H4>
        <P>A refund of unused diamonds may be requested if ALL of the following conditions are met:</P>
        <UL items={[
          'The refund request is submitted within 14 calendar days of the purchase date.',
          'The purchased diamond package is at least 50% unused (diamonds have not been spent on hunts).',
          'The account has not been suspended for a Terms of Service violation.',
          'No chargeback has been initiated for the same transaction.',
        ]} />

        <H4>4.3 Non-Refundable Items</H4>
        <UL items={[
          'Diamonds that have been consumed by successful bot actions (exchange finds or crypt dispatches).',
          'Free trial diamonds (100 diamonds upon registration).',
          'Referral reward diamonds.',
          'Any purchase made more than 14 days prior to the refund request.',
          'Partial packages where more than 50% of diamonds have been spent.',
        ]} />

        <H4>4.4 How to Request a Refund</H4>
        <P>
          To initiate a refund, send an email to <Accent>totalhunter.support@gmail.com</Accent> with the
          subject line «Refund Request» and include:
        </P>
        <UL items={[
          'Your registered email address.',
          'The order/transaction ID from Free-Kassa (found in your Dashboard → Transactions).',
          'Date and amount of the purchase.',
          'Reason for the refund request.',
        ]} />
        <P>
          Refund requests are reviewed within 3 business days. Approved refunds are returned
          to the original payment method within 5–10 business days depending on the payment provider.
        </P>

        <H4>4.5 Chargebacks</H4>
        <P>
          Initiating a chargeback or payment dispute with your bank without first contacting our
          support will result in immediate permanent account suspension. We actively contest fraudulent
          chargebacks with full transaction evidence.
        </P>
      </Section>

      <Section title="5. Contact Information">
        <P>
          If you have any questions regarding this Legal Information, our Terms of Service,
          Privacy Policy, or need assistance with a refund, please contact us:
        </P>
        <UL items={[
          'Email: totalhunter.support@gmail.com',
          'Telegram: @TotalHunter_bot',
          'Website: https://total-hunter.com',
          'Response time: within 48 hours on business days',
        ]} />
        <P>
          We reserve the right to update this document at any time. Continued use of the Service
          after changes are published constitutes acceptance of the updated terms.
          Material changes will be announced on the website homepage.
        </P>
      </Section>
    </>
  )
}

function ContentRU() {
  return (
    <>
      <Section title="1. Условия использования (Публичная оферта)">
        <H4>1.1 Стороны договора</H4>
        <P>
          Настоящее Соглашение заключается между <Hl>Total Hunter</Hl> (далее — «Сервис», «Мы») и любым
          физическим или юридическим лицом (далее — «Пользователь»), которое получает доступ
          к сайту и программному обеспечению Total Hunter по адресу <Accent>total-hunter.com</Accent>.
        </P>
        <P>
          Регистрируя аккаунт, загружая приложение или приобретая алмазы (кредиты), вы подтверждаете,
          что прочитали, поняли и приняли все условия настоящего Соглашения в полном объёме.
          Если вы не согласны с какой-либо частью условий, вы обязаны немедленно прекратить
          использование Сервиса.
        </P>

        <H4>1.2 Предмет договора</H4>
        <P>
          Сервис предоставляет Пользователю доступ к десктопному боту-помощнику, предназначенному
          для использования в онлайн-игре Total Battle. Бот автоматизирует рутинные игровые действия:
          сканирование карты для поиска бирж наёмников и отправку отрядов в склепы.
          Сервис работает по модели предоплаченных кредитов (алмазов).
        </P>

        <H4>1.3 Регистрация и аккаунт пользователя</H4>
        <UL items={[
          'Регистрация осуществляется через Google OAuth. Регистрируясь, Пользователь разрешает Total Hunter хранить адрес электронной почты Google-аккаунта для целей идентификации.',
          'Каждый аккаунт привязан к уникальному Hardware ID (HWID) — криптографическому идентификатору устройства Пользователя. Один бесплатный триал (100 алмазов) выдаётся на одно устройство.',
          'Пользователь несёт единоличную ответственность за сохранность данных своего аккаунта.',
          'Для регистрации Пользователь должен быть не моложе 18 лет или достичь минимального законного возраста в своей стране.',
          'Одно лицо не вправе регистрировать несколько аккаунтов для получения дополнительных триалов. Такие аккаунты будут заблокированы навсегда без возврата средств.',
        ]} />

        <H4>1.4 Система алмазных кредитов</H4>
        <P>
          В Total Hunter используется внутренняя виртуальная валюта <Hl>◆ Алмазы</Hl>.
          Алмазы являются предоплаченным сервисным токеном и не имеют денежной ценности за пределами Сервиса.
          Списание алмазов происходит только за успешные действия бота:
        </P>
        <UL items={[
          '−10 алмазов: успешно найдена биржа наёмников.',
          '−1 алмаз: Картер успешно отправлен в склеп.',
          '0 алмазов: цель не найдена, поиск прерван или ошибка соединения — списания нет.',
        ]} />
        <P>
          Алмазы не имеют срока действия. Приобретённые алмазы остаются на аккаунте Пользователя
          бессрочно, за исключением случаев блокировки аккаунта за нарушение настоящих Условий.
        </P>

        <H4>1.5 Допустимое использование</H4>
        <P>Пользователь обязуется НЕ:</P>
        <UL items={[
          'Передавать, перепродавать или уступать данные аккаунта или привязку HWID третьим лицам.',
          'Предпринимать попытки реверс-инжиниринга, декомпиляции или модификации приложения Total Hunter.',
          'Использовать автоматизированные скрипты или инструменты для манипуляции балансом алмазов или обхода системы лицензирования.',
          'Создавать несколько аккаунтов для злоупотребления системой бесплатного триала.',
          'Использовать Сервис в каких-либо целях, нарушающих применимое законодательство.',
        ]} />

        <H4>1.6 Доступность Сервиса</H4>
        <P>
          Сервис предоставляется «как есть». Мы прилагаем разумные усилия для обеспечения бесперебойной
          работы, однако не гарантируем 100% доступности. Плановые или аварийные технические работы
          могут проводиться без предварительного уведомления. Компенсация алмазами за простой
          не предусмотрена, если его продолжительность не превысила 72 часов подряд.
        </P>

        <H4>1.7 Прекращение действия аккаунта</H4>
        <P>
          Мы оставляем за собой право приостановить или навсегда заблокировать аккаунт Пользователя
          без возврата средств в случаях: мошенничества, злоупотребления триальной системой,
          нарушения условий допустимого использования или инициирования чарджбэка по законным покупкам.
          Пользователь может закрыть свой аккаунт в любое время, обратившись в службу поддержки.
        </P>
      </Section>

      <Section title="2. Политика конфиденциальности">
        <H4>2.1 Данные, которые мы собираем</H4>
        <UL items={[
          'Адрес электронной почты — получен через Google OAuth при регистрации, используется исключительно для идентификации аккаунта и входа в систему.',
          'Hardware ID (HWID) — односторонний SHA-256 хэш MAC-адреса сетевого адаптера. Мы храним только хэш, но не исходный MAC-адрес.',
          'Данные об использовании — временны́е метки сессий бота, транзакции с алмазами, результаты охот (агрегированно). Записи экрана и скриншоты вашей игровой сессии не сохраняются.',
          'IP-адрес — фиксируется исключительно в целях безопасности и предотвращения злоупотреблений.',
        ]} />

        <H4>2.2 Данные, которые мы НЕ собираем</H4>
        <UL items={[
          'Логин, пароль или учётные данные вашего игрового аккаунта Total Battle — никогда не запрашиваются и не хранятся.',
          'Содержимое экрана или визуальные данные из вашей игровой сессии.',
          'Номера банковских карт или банковские реквизиты — все платежи обрабатываются NOWPayments. Мы никогда не видим и не храним ваши платёжные данные.',
        ]} />

        <H4>2.3 Как мы используем ваши данные</H4>
        <UL items={[
          'Для аутентификации аккаунта и проверки лицензии (HWID + email).',
          'Для обработки транзакций с алмазами и ведения истории баланса.',
          'Для расчёта реферальных вознаграждений и отслеживания многоуровневых реферальных цепочек.',
          'Для отправки транзакционных уведомлений (подтверждения покупок, оповещения о низком балансе) при условии вашего согласия.',
          'Для обнаружения и предотвращения мошенничества и злоупотреблений.',
        ]} />

        <H4>2.4 Сроки хранения данных</H4>
        <P>
          Данные аккаунта хранятся в течение всего срока его существования плюс 90 дней после удаления.
          Журналы транзакций хранятся 36 месяцев для соответствия требованиям финансовой отчётности.
          После удаления аккаунта все персональные данные удаляются из активных систем в течение 30 дней.
        </P>

        <H4>2.5 Сторонние сервисы</H4>
        <UL items={[
          'Google OAuth — провайдер аутентификации. Подпадает под Политику конфиденциальности Google.',
          'NOWPayments — обработка криптовалютных платежей. Подпадает под Политику конфиденциальности NOWPayments.',
          'Google Cloud Platform (GCP) — серверная инфраструктура. Данные хранятся в регионе США.',
          'Vercel — хостинг сайта. Персональные данные через Vercel не обрабатываются.',
        ]} />

        <H4>2.6 Ваши права</H4>
        <P>
          Вы имеете право: получить копию своих персональных данных, запросить исправление
          недостоверных данных, запросить удаление аккаунта и связанных данных, а также отозвать
          согласие на получение необязательных сообщений. Для реализации этих прав обратитесь к нам:
          {' '}<Accent>totalhunter.support@gmail.com</Accent>.
        </P>

        <H4>2.7 Файлы Cookie</H4>
        <P>
          Сайт использует только необходимые идентификаторы: токен аутентификации сессии,
          хранящийся в localStorage (не файл cookie, без отслеживания), и ключ языкового
          предпочтения. Рекламные файлы cookie и сторонние трекинговые пиксели не используются.
        </P>
      </Section>

      <Section title="3. Отказ от ответственности (риск игрового аккаунта)">
        <P>
          <Hl>Total Hunter — независимый сторонний инструмент, не аффилированный, не одобренный
          и никак официально не связанный с Plarium Games Ltd.</Hl> — разработчиком Total Battle —
          или какими-либо его дочерними компаниями.
        </P>
        <P>
          Использование программ автоматизации может нарушать Условия предоставления услуг Total Battle.
          Plarium Games оставляет за собой право предпринимать меры в отношении аккаунтов,
          использующих сторонние инструменты автоматизации, включая: временную блокировку,
          перманентный бан или удаление игрового прогресса и активов.
        </P>
        <P><Warn>Используя Total Hunter, вы признаёте и принимаете, что:</Warn></P>
        <UL items={[
          'Вы используете данное программное обеспечение исключительно на свой риск.',
          'Total Hunter и его разработчики не несут никакой ответственности за любые ограничения игрового аккаунта, временные или постоянные блокировки, а также потерю игрового прогресса и ресурсов в результате использования данного программного обеспечения.',
          'Возврат средств по причине блокировки игрового аккаунта не производится.',
          'Мы настоятельно рекомендуем сначала тестировать бота на дополнительных или альтернативных игровых аккаунтах.',
        ]} />
        <P>
          Нами внедрены современные методы антидетекта: рандомизация задержек между действиями
          (0,4–0,9 секунды), случайное смещение кликов (±5–8 пикселей) и прямое взаимодействие
          с окном игры без API-манипуляций. Тем не менее ни одно программное обеспечение
          для автоматизации не может гарантировать нулевой риск обнаружения.
        </P>
      </Section>

      <Section title="4. Политика возврата и оплаты">
        <H4>4.1 Принимаемые способы оплаты</H4>
        <P>
          Платежи обрабатываются исключительно через <Hl>NOWPayments</Hl> — некастодиальный
          процессор криптовалютных платежей. Поддерживаемые валюты: USDT (TRC-20 / ERC-20),
          Bitcoin (BTC), Ethereum (ETH), BNB и другие криптовалюты, поддерживаемые NOWPayments.
          Все транзакции защищены шифрованием SSL/TLS.
        </P>
        <P>
          <Warn>Важно:</Warn> Криптовалютные транзакции <Hl>необратимы по своей природе</Hl>.
          После подтверждения платежа в блокчейне он не может быть отменён ни отправителем, ни Сервисом.
          Алмазы начисляются автоматически после подтверждения оплаты.
        </P>

        <H4>4.2 Условия возврата</H4>
        <P>Возврат неиспользованных алмазов возможен при выполнении ВСЕХ следующих условий:</P>
        <UL items={[
          'Запрос на возврат подан в течение 14 календарных дней с даты покупки.',
          'Приобретённый пакет алмазов использован менее чем на 50% (алмазы не потрачены на охоты).',
          'Аккаунт не был заблокирован за нарушение настоящих Условий.',
          'Чарджбэк по данной транзакции не был инициирован.',
        ]} />

        <H4>4.3 Невозвратные позиции</H4>
        <UL items={[
          'Алмазы, израсходованные в результате успешных действий бота (нахождение биржи или отправка Картера в склеп).',
          'Бесплатные триальные алмазы (100 алмазов при регистрации).',
          'Алмазы, начисленные по реферальной программе.',
          'Любая покупка, совершённая более 14 дней назад.',
          'Частичные пакеты, из которых потрачено более 50% алмазов.',
        ]} />

        <H4>4.4 Как запросить возврат</H4>
        <P>
          Для инициирования возврата отправьте письмо на <Accent>totalhunter.support@gmail.com</Accent>{' '}
          с темой «Refund Request» и укажите:
        </P>
        <UL items={[
          'Адрес электронной почты, указанный при регистрации.',
          'ID заказа/транзакции из Free-Kassa (находится в Dashboard → Транзакции).',
          'Дату и сумму покупки.',
          'Причину запроса возврата.',
        ]} />
        <P>
          Запросы на возврат рассматриваются в течение 3 рабочих дней. Одобренные возвраты
          поступают на исходный способ оплаты в течение 5–10 рабочих дней в зависимости
          от платёжного провайдера.
        </P>

        <H4>4.5 Чарджбэки</H4>
        <P>
          Инициирование чарджбэка или платёжного спора через банк без предварительного обращения
          в нашу службу поддержки влечёт немедленную перманентную блокировку аккаунта.
          Мы активно оспариваем мошеннические чарджбэки, предоставляя полные доказательства транзакций.
        </P>
      </Section>

      <Section title="5. Контактная информация">
        <P>
          По всем вопросам, касающимся данного раздела, Условий использования, Политики
          конфиденциальности или возврата средств, обращайтесь к нам:
        </P>
        <UL items={[
          'Email: totalhunter.support@gmail.com',
          'Telegram: @TotalHunter_bot',
          'Сайт: https://total-hunter.com',
          'Время ответа: в течение 48 часов в рабочие дни',
        ]} />
        <P>
          Мы оставляем за собой право обновлять данный документ в любое время. Продолжение
          использования Сервиса после публикации изменений означает согласие с обновлёнными условиями.
          О существенных изменениях будет сообщено на главной странице сайта.
        </P>
      </Section>
    </>
  )
}

export default function LegalPage() {
  const navigate = useNavigate()
  const { lang, toggle } = useLang()

  const isRu = lang === 'ru'
  const updated = isRu ? 'Последнее обновление: 2 мая 2026' : 'Last updated: May 2, 2026'
  const title   = isRu ? 'Правовая информация' : 'Legal Information'
  const backBtn = isRu ? '← Назад' : '← Back'
  const langBtn = isRu ? 'EN' : 'RU'

  return (
    <div className="page-content" style={{ maxWidth: 760 }}>

      {/* ── Top bar: Back + Language ─────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            background: 'none', border: '1px solid var(--outline)',
            borderRadius: 8, padding: '6px 14px',
            color: 'var(--on-surface2)', fontSize: 13, cursor: 'pointer',
            transition: 'color 0.15s, border-color 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--on-surface)'; e.currentTarget.style.borderColor = 'var(--accent)' }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--on-surface2)'; e.currentTarget.style.borderColor = 'var(--outline)' }}
        >
          {backBtn}
        </button>

        <button
          onClick={toggle}
          style={{
            background: 'rgba(61,127,255,0.08)', border: '1px solid rgba(61,127,255,0.25)',
            borderRadius: 8, padding: '6px 16px',
            color: 'var(--accent)', fontSize: 13, fontWeight: 700, cursor: 'pointer',
          }}
        >
          {langBtn}
        </button>
      </div>

      <h2 style={{ marginBottom: 4 }}>{title}</h2>
      <p className="text-muted" style={{ marginBottom: 28 }}>{updated}</p>

      {isRu ? <ContentRU /> : <ContentEN />}
    </div>
  )
}
