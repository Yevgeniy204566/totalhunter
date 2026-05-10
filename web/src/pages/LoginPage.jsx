import { GoogleLogin } from '@react-oauth/google'
import { api } from '../api.js'
import { saveToken } from '../auth.js'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'

const _API_BASE = import.meta.env.VITE_API_URL || '/api'
const _isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent)

function getRefCookie() {
  const match = document.cookie.match(/(?:^|;\s*)th_ref=([^;]+)/)
  return match ? match[1] : null
}

export default function LoginPage() {
  const navigate  = useNavigate()
  const [searchParams] = useSearchParams()
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const { lang } = useLang()
  const T = lang === 'ru' ? D_RU.login : D_EN.login

  // Mobile redirect flow: Google → backend callback → /login?token=JWT
  useEffect(() => {
    const token = searchParams.get('token')
    const err   = searchParams.get('error')
    if (token) {
      saveToken(token)
      navigate('/dashboard', { replace: true })
      return
    }
    if (err) {
      console.error('[OAuth] redirect error:', err)
      setError((T.loginError || 'Auth error: ') + err)
    }
  }, [])

  const handleSuccess = async (credentialResponse) => {
    setLoading(true)
    setError(null)
    try {
      const refCode = getRefCookie()
      const data = await api.authGoogle(credentialResponse.credential, refCode)
      saveToken(data.jwt)
      navigate('/dashboard')
    } catch (e) {
      console.error('[OAuth] popup flow error:', e)
      setError(T.loginError + e.message)
      setLoading(false)
    }
  }

  const handleMobileLogin = () => {
    const refCode = getRefCookie()
    const qs = refCode ? `?ref_code=${encodeURIComponent(refCode)}` : ''
    window.location.href = `${_API_BASE}/web/auth/google/start${qs}`
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: `
        radial-gradient(ellipse 80% 60% at 50% 20%, rgba(61,127,255,0.12) 0%, transparent 60%),
        radial-gradient(ellipse 50% 50% at 80% 80%, rgba(176,96,255,0.07) 0%, transparent 60%),
        var(--bg)
      `,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '24px',
      fontFamily: 'Inter, sans-serif',
    }}>

      {/* Grid overlay */}
      <div style={{
        position: 'fixed', inset: 0, opacity: 0.025, pointerEvents: 'none',
        backgroundImage:
          'linear-gradient(var(--outline) 1px, transparent 1px), linear-gradient(90deg, var(--outline) 1px, transparent 1px)',
        backgroundSize: '48px 48px',
      }} />

      {/* Logo */}
      <Link to="/" style={{
        display: 'flex', alignItems: 'center', gap: 10,
        fontWeight: 700, fontSize: 20, textDecoration: 'none',
        marginBottom: 40,
      }}>
        <span style={{ fontSize: 24, color: 'var(--accent)' }}>⚔</span>
        <span style={{ color: 'var(--accent)', textShadow: '0 0 18px var(--accent-glow)' }}>Total</span>
        <span style={{ color: '#FFFFFF' }}>Hunter</span>
      </Link>

      {/* Card */}
      <div style={{
        background: 'var(--elevated)',
        border: '1px solid var(--outline)',
        borderRadius: 20,
        padding: '40px 36px',
        width: '100%', maxWidth: 420,
        boxShadow: '0 0 60px rgba(61,127,255,0.08), 0 24px 48px rgba(0,0,0,0.4)',
        position: 'relative',
      }}>
        {/* Top accent line */}
        <div style={{
          position: 'absolute', top: 0, left: '20%', right: '20%', height: 2,
          background: 'linear-gradient(90deg, transparent, var(--accent), transparent)',
          borderRadius: '0 0 4px 4px',
        }} />

        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{
            fontSize: 26, fontWeight: 800, color: '#FFFFFF',
            marginBottom: 10, letterSpacing: '-0.5px',
          }}>
            {T.title}
          </h1>
          <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.6 }}>
            {T.sub}
          </p>
        </div>

        {/* Feature pills */}
        <div style={{
          display: 'flex', gap: 8, justifyContent: 'center',
          flexWrap: 'wrap', marginBottom: 32,
        }}>
          {T.features.map((text) => (
            <div key={text} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '5px 12px', borderRadius: 20,
              background: 'rgba(61,127,255,0.08)',
              border: '1px solid rgba(61,127,255,0.2)',
              fontSize: 12, color: '#C8D8F0', fontWeight: 500,
            }}>
              <span style={{ fontSize: 13 }}>◈</span>
              {text}
            </div>
          ))}
        </div>

        {/* Divider */}
        <div style={{
          height: 1, background: 'var(--outline)', marginBottom: 28,
        }} />

        {/* Google button — popup (desktop) or redirect (mobile) */}
        <div style={{
          display: 'flex', justifyContent: 'center', marginBottom: 16,
          opacity: loading ? 0.5 : 1,
          pointerEvents: loading ? 'none' : 'auto',
          transition: 'opacity 0.2s',
        }}>
          {_isMobile ? (
            <button
              onClick={handleMobileLogin}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                width: 320, padding: '10px 16px', borderRadius: 8,
                background: '#131314', border: '1px solid #444',
                color: '#fff', fontSize: 15, fontWeight: 500,
                cursor: 'pointer', justifyContent: 'center',
              }}
            >
              <svg width="20" height="20" viewBox="0 0 48 48">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
              </svg>
              {T.signInGoogle || 'Sign in with Google'}
            </button>
          ) : (
            <GoogleLogin
              onSuccess={handleSuccess}
              onError={() => setError(T.googleError)}
              theme="filled_black"
              size="large"
              width="320"
            />
          )}
        </div>

        {loading && (
          <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--accent)', marginBottom: 8 }}>
            {T.signingIn}
          </div>
        )}

        {error && (
          <div style={{
            padding: '10px 14px', borderRadius: 8, marginBottom: 8,
            background: 'rgba(255,80,80,0.08)',
            border: '1px solid rgba(255,80,80,0.25)',
            color: 'var(--error-text)', fontSize: 13, textAlign: 'center',
          }}>
            {error}
          </div>
        )}

        <p style={{
          textAlign: 'center', fontSize: 11, color: 'var(--on-surface2)',
          lineHeight: 1.6, marginTop: 20,
        }}>
          {T.legal}{' '}
          <Link to="/legal" style={{ color: 'var(--accent)', textDecoration: 'none' }}>{T.legalLink}</Link>
        </p>
      </div>

      {/* Footer links */}
      <div style={{ display: 'flex', gap: 24, marginTop: 28 }}>
        <Link to="/guide" style={{ fontSize: 13, color: 'var(--on-surface2)', textDecoration: 'none' }}>
          {T.guide}
        </Link>
        <Link to="/legal" style={{ fontSize: 13, color: 'var(--on-surface2)', textDecoration: 'none' }}>
          Legal
        </Link>
        <Link to="/" style={{ fontSize: 13, color: 'var(--on-surface2)', textDecoration: 'none' }}>
          {T.home}
        </Link>
      </div>

    </div>
  )
}
