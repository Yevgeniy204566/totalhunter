import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

export default function RefPage() {
  const { code } = useParams()
  const navigate = useNavigate()

  useEffect(() => {
    if (code) {
      const expires = new Date()
      expires.setDate(expires.getDate() + 30)
      document.cookie = `th_ref=${code}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`
    }
    navigate('/login', { replace: true })
  }, [code, navigate])

  return null
}
