import { useGoogleLogin } from '@react-oauth/google'
import { api } from '../api.js'
import { saveToken } from '../auth.js'
import { useNavigate } from 'react-router-dom'

export default function LoginPage() {
  const navigate = useNavigate()

  const login = useGoogleLogin({
    onSuccess: async ({ credential }) => {
      try {
        const data = await api.authGoogle(credential)
        saveToken(data.jwt)
        navigate('/dashboard')
      } catch (e) {
        alert('Login failed: ' + e.message)
      }
    },
    flow: 'implicit',
  })

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <div className="card" style={{ textAlign: 'center', maxWidth: 380, width: '100%' }}>
        <h1 style={{ fontSize: 24, marginBottom: 8 }}>Total Hunter</h1>
        <p className="text-muted" style={{ marginBottom: 32 }}>Sign in to access your dashboard</p>
        <button className="btn-primary" onClick={() => login()} style={{ width: '100%', padding: '12px' }}>
          Continue with Google
        </button>
        <div className="separator" />
        <div style={{ display: 'flex', gap: 16, justifyContent: 'center' }}>
          <a href="/guide">Guide</a>
          <a href="/legal">Legal</a>
        </div>
      </div>
    </div>
  )
}
