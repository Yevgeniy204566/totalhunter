import { GoogleLogin } from '@react-oauth/google'
import { api } from '../api.js'
import { saveToken } from '../auth.js'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'

export default function LoginPage() {
  const navigate = useNavigate()
  const [error, setError] = useState(null)

  const handleSuccess = async (credentialResponse) => {
    try {
      const data = await api.authGoogle(credentialResponse.credential)
      saveToken(data.jwt)
      navigate('/dashboard')
    } catch (e) {
      setError('Login failed: ' + e.message)
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <div className="card" style={{ textAlign: 'center', maxWidth: 380, width: '100%' }}>
        <h1 style={{ fontSize: 24, marginBottom: 8 }}>Total Hunter</h1>
        <p className="text-muted" style={{ marginBottom: 32 }}>Sign in to access your dashboard</p>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
          <GoogleLogin
            onSuccess={handleSuccess}
            onError={() => setError('Google login failed')}
            theme="filled_black"
            size="large"
            width="320"
          />
        </div>
        {error && <p style={{ color: 'var(--error, #f87171)', fontSize: 13 }}>{error}</p>}
        <div className="separator" />
        <div style={{ display: 'flex', gap: 16, justifyContent: 'center' }}>
          <a href="/guide">Guide</a>
          <a href="/legal">Legal</a>
        </div>
      </div>
    </div>
  )
}
