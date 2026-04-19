export default function GuidePage() {
  return (
    <div className="page-content" style={{ maxWidth: 700 }}>
      <h2 style={{ marginBottom: 24 }}>Bot Guide</h2>

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
  )
}
