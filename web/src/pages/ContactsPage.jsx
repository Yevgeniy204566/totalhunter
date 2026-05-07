import { useNavigate } from 'react-router-dom'
import { useLang } from '../lang.js'

export default function ContactsPage() {
  const navigate = useNavigate()
  const { lang } = useLang()
  const isRu = lang === 'ru'

  const t = {
    title:    isRu ? 'Контакты' : 'Contact Us',
    back:     isRu ? '← Назад' : '← Back',
    subtitle: isRu
      ? 'Мы отвечаем в течение 48 часов в рабочие дни.'
      : 'We respond within 48 hours on business days.',
    supportTitle:  isRu ? 'Служба поддержки' : 'Support',
    emailLabel:    'Email',
    tgLabel:       'Telegram',
    aboutTitle:    isRu ? 'О сервисе' : 'About the Service',
    aboutText:     isRu
      ? 'Total Hunter — SaaS-бот для автоматического поиска бирж наёмников и сбора склепов в игре Total Battle. Работает по модели предоплаченных алмазных кредитов. Сервис не аффилирован с Plarium Games Ltd.'
      : 'Total Hunter is a SaaS automation bot for locating mercenary exchanges and gathering crypts in the game Total Battle. It operates on a prepaid diamond credit model. The service is not affiliated with Plarium Games Ltd.',
    pricingTitle:  isRu ? 'Тариф' : 'Pricing',
    ultraDesc: isRu ? '5 000 алмазов — $10' : '5,000 diamonds — $10',
    legalTitle: isRu ? 'Юридическая информация' : 'Legal',
    legalLink:  isRu ? 'Условия, политика, возвраты →' : 'Terms, Privacy, Refunds →',
  }

  const card = {
    background: 'var(--card)',
    border: '1px solid var(--outline)',
    borderRadius: 16,
    padding: '28px 32px',
    marginBottom: 20,
  }

  const row = {
    display: 'flex', alignItems: 'center', gap: 14,
    padding: '14px 0', borderBottom: '1px solid var(--outline)',
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', padding: '40px 24px' }}>
      <div style={{ maxWidth: 600, margin: '0 auto' }}>

        <button onClick={() => navigate(-1)} style={{
          background: 'none', border: '1px solid var(--outline)',
          borderRadius: 8, padding: '6px 14px', marginBottom: 32,
          color: 'var(--on-surface2)', fontSize: 13, cursor: 'pointer',
        }}>
          {t.back}
        </button>

        <h1 style={{ fontSize: 36, fontWeight: 800, color: '#fff', marginBottom: 8 }}>{t.title}</h1>
        <p style={{ color: 'var(--on-surface2)', marginBottom: 36, fontSize: 15 }}>{t.subtitle}</p>

        {/* Support */}
        <div style={card}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent)', marginBottom: 16 }}>
            {t.supportTitle}
          </h3>
          <div style={{ ...row }}>
            <span style={{ fontSize: 20 }}>📧</span>
            <div>
              <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: 2 }}>{t.emailLabel}</div>
              <a href="mailto:totalhunter.support@gmail.com" style={{ color: '#fff', fontWeight: 600, fontSize: 15 }}>
                totalhunter.support@gmail.com
              </a>
            </div>
          </div>
          <div style={{ ...row, borderBottom: 'none' }}>
            <span style={{ fontSize: 20 }}>✈️</span>
            <div>
              <div style={{ fontSize: 12, color: 'var(--on-surface2)', marginBottom: 2 }}>{t.tgLabel}</div>
              <a href="https://t.me/TotalHunter_bot" target="_blank" rel="noreferrer"
                style={{ color: 'var(--accent)', fontWeight: 600, fontSize: 15 }}>
                @TotalHunter_bot
              </a>
            </div>
          </div>
        </div>

        {/* About */}
        <div style={card}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--on-surface)', marginBottom: 12 }}>
            {t.aboutTitle}
          </h3>
          <p style={{ color: 'var(--on-surface2)', fontSize: 14, lineHeight: 1.7 }}>{t.aboutText}</p>
        </div>

        {/* Pricing */}
        <div style={card}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--on-surface)', marginBottom: 16 }}>
            {t.pricingTitle}
          </h3>
          {[
            { name: 'Total Hunter', price: '$10', desc: t.ultraDesc, color: '#00CFFF', popular: true },
          ].map((pkg, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 0',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ color: pkg.color, fontWeight: 700, fontSize: 15 }}>{pkg.name}</span>
                {pkg.popular && (
                  <span style={{
                    background: 'rgba(0,207,255,0.15)', color: 'var(--accent)',
                    borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 700,
                  }}>POPULAR</span>
                )}
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontWeight: 800, fontSize: 17, color: '#fff' }}>{pkg.price}</span>
                <span style={{ color: 'var(--on-surface2)', fontSize: 13, marginLeft: 8 }}>{pkg.desc}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Legal link */}
        <div style={{ ...card, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--on-surface)', margin: 0 }}>
            {t.legalTitle}
          </h3>
          <a href="/legal" style={{ color: 'var(--accent)', fontSize: 14, fontWeight: 600 }}>
            {t.legalLink}
          </a>
        </div>

      </div>
    </div>
  )
}
