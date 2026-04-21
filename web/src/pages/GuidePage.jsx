import { Link } from 'react-router-dom'

export default function GuidePage() {
  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh' }}>
      {/* Nav */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: 'rgba(5, 8, 16, 0.92)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--outline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 32px', height: 64,
        boxShadow: '0 2px 32px var(--accent-glow)',
      }}>
        <Link to="/" style={{
          display: 'flex', alignItems: 'center', gap: 10,
          textDecoration: 'none', fontWeight: 700, fontSize: 18,
        }}>
          <span style={{ color: 'var(--accent)', fontSize: 20 }}>⚔</span>
          <span style={{ color: 'var(--accent)', textShadow: '0 0 14px var(--accent-glow)' }}>Total</span>
          <span style={{ color: '#FFFFFF' }}>Hunter</span>
        </Link>
        <Link to="/" style={{
          padding: '8px 16px', borderRadius: 8, fontSize: 14,
          color: 'var(--on-surface2)', border: '1px solid var(--outline)',
          fontWeight: 500,
        }}>
          ← На главную
        </Link>
      </nav>

    <div className="page-content" style={{ maxWidth: 700 }}>
      <h2 style={{ marginBottom: 24, color: '#FFFFFF' }}>Bot Guide</h2>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 12 }}>1. Installation</h3>
        <ol style={{ paddingLeft: 20, lineHeight: 2, color: 'var(--on-surface2)', fontSize: 14 }}>
          <li>Download the bot installer from your registered email</li>
          <li>Run the installer — Python and dependencies are included</li>
          <li>Launch <code>TotalHunter.exe</code></li>
          <li>Click <strong>Claim Trial</strong> to get 300 free credits</li>
        </ol>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 12 }}>2. Calibration</h3>
        <p style={{ color: 'var(--on-surface2)', fontSize: 14, lineHeight: 1.8 }}>
          Go to the <strong>Calibration</strong> tab. Open Total Battle in your browser window.
          Click <strong>Point A</strong> on the joystick center, then <strong>Point B</strong> on the minimap.
          Save the profile.
        </p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 12 }}>3. Running the bot</h3>
        <p style={{ color: 'var(--on-surface2)', fontSize: 14, lineHeight: 1.8 }}>
          Select the hunt mode (Exchanges or Crypts), set the range and acceleration sliders,
          then press <strong>START</strong>. Press <strong>ESC</strong> at any time to stop immediately.
        </p>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 12 }}>4. Credits</h3>
        <p style={{ color: 'var(--on-surface2)', fontSize: 14, lineHeight: 1.8 }}>
          Each found Exchange costs 5 credits. Each found Crypt costs 1 credit.
          Credits are only spent on successful finds. To top up, use the referral system or purchase a package.
        </p>
      </div>
    </div>
    </div>
  )
}
