export default function LegalPage() {
  return (
    <div className="page-content" style={{ maxWidth: 700 }}>
      <h2 style={{ marginBottom: 8 }}>Legal Information</h2>
      <p className="text-muted" style={{ marginBottom: 24 }}>Last updated: April 2026</p>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 12 }}>Public Offer Agreement</h3>
        <p style={{ color: 'var(--on-surface2)', fontSize: 14, lineHeight: 1.8 }}>
          By purchasing credits or using the Total Hunter service, you agree to these terms.
          The service provides automation tools for the browser game Total Battle.
          Credits are non-refundable once consumed. Unused credits may be refunded within 14 days of purchase.
        </p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 12 }}>Disclaimer — Game Account Risk</h3>
        <p style={{ color: 'var(--on-surface2)', fontSize: 14, lineHeight: 1.8 }}>
          Total Hunter is a third-party tool not affiliated with the game developers.
          Using automation tools may violate the game's Terms of Service.
          <strong style={{ color: 'var(--on-surface)' }}> We accept no responsibility for any game account
          suspensions, bans, or restrictions</strong> that may result from using this service. Use at your own risk.
        </p>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 12 }}>Refund Policy</h3>
        <p style={{ color: 'var(--on-surface2)', fontSize: 14, lineHeight: 1.8 }}>
          Refunds are available for unused credit packages within 14 days of purchase.
          Credits already spent on hunts are non-refundable.
          To request a refund, contact support with your order ID.
        </p>
      </div>
    </div>
  )
}
