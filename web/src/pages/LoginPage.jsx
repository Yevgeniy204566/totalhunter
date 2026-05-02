import { GoogleLogin } from '@react-oauth/google'
import { api } from '../api.js'
import { saveToken } from '../auth.js'
import { useNavigate, Link } from 'react-router-dom'
import { useState } from 'react'

function getRefCookie() {
  const match = document.cookie.match(/(?:^|;\s*)th_ref=([^;]+)/)
  return match ? match[1] : null
}

const FEATURES = [
  { icon: '◈', text: 'Авто-охота на Биржи' },
  { icon: '◈', text: 'Поиск Склепов 24/7' },
  { icon: '◈', text: 'Реферальная система' },
]

export default function LoginPage() {
  const navigate  = useNavigate()
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSuccess = async (credentialResponse) => {
    setLoading(true)
    setError(null)
    try {
      const refCode = getRefCookie()
      const data = await api.authGoogle(credentialResponse.credential, refCode)
      saveToken(data.jwt)
      navigate('/dashboard')
    } catch (e) {
      setError('Ошибка входа: ' + e.message)
      setLoading(false)
    }
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
            Войти в кабинет
          </h1>
          <p style={{ fontSize: 14, color: 'var(--on-surface2)', lineHeight: 1.6 }}>
            Используй Google-аккаунт для входа.<br />
            Первый вход — автоматически создаёт аккаунт.
          </p>
        </div>

        {/* Feature pills */}
        <div style={{
          display: 'flex', gap: 8, justifyContent: 'center',
          flexWrap: 'wrap', marginBottom: 32,
        }}>
          {FEATURES.map(({ icon, text }) => (
            <div key={text} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '5px 12px', borderRadius: 20,
              background: 'rgba(61,127,255,0.08)',
              border: '1px solid rgba(61,127,255,0.2)',
              fontSize: 12, color: '#C8D8F0', fontWeight: 500,
            }}>
              <span style={{ fontSize: 13 }}>{icon}</span>
              {text}
            </div>
          ))}
        </div>

        {/* Divider */}
        <div style={{
          height: 1, background: 'var(--outline)', marginBottom: 28,
        }} />

        {/* Google button */}
        <div style={{
          display: 'flex', justifyContent: 'center', marginBottom: 16,
          opacity: loading ? 0.5 : 1,
          pointerEvents: loading ? 'none' : 'auto',
          transition: 'opacity 0.2s',
        }}>
          <GoogleLogin
            onSuccess={handleSuccess}
            onError={() => setError('Ошибка Google авторизации')}
            theme="filled_black"
            size="large"
            width="320"
          />
        </div>

        {loading && (
          <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--accent)', marginBottom: 8 }}>
            Входим...
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
          Продолжая, ты соглашаешься с{' '}
          <Link to="/legal" style={{ color: 'var(--accent)', textDecoration: 'none' }}>условиями использования</Link>
        </p>
      </div>

      {/* Footer links */}
      <div style={{ display: 'flex', gap: 24, marginTop: 28 }}>
        <Link to="/guide" style={{ fontSize: 13, color: 'var(--on-surface2)', textDecoration: 'none' }}>
          Гайд
        </Link>
        <Link to="/legal" style={{ fontSize: 13, color: 'var(--on-surface2)', textDecoration: 'none' }}>
          Legal
        </Link>
        <Link to="/" style={{ fontSize: 13, color: 'var(--on-surface2)', textDecoration: 'none' }}>
          ← На главную
        </Link>
      </div>

    </div>
  )
}
