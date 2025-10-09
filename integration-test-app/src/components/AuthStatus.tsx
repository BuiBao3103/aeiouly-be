import { useEffect, useState } from 'react'
import { colors } from '../theme'

type MeResponse = {
  id: number
  username: string
  email?: string
  full_name?: string
  role?: string
}

export default function AuthStatus() {
  const [me, setMe] = useState<MeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const fetchMe = async () => {
    try {
      setLoading(true)
      const res = await fetch('http://localhost:8000/api/v1/auth/me', {
        method: 'GET',
        credentials: 'include',
      })
      if (!res.ok) {
        setMe(null)
        return
      }
      const data = await res.json()
      setMe(data)
    } catch {
      setMe(null)
    } finally {
      setLoading(false)
    }
  }

  // Only fetch when explicitly notified by auth flows
  useEffect(() => {
    const onAuthChanged = () => {
      fetchMe()
    }
    window.addEventListener('auth:changed', onAuthChanged as EventListener)
    return () => {
      window.removeEventListener('auth:changed', onAuthChanged as EventListener)
    }
  }, [])

  return (
    <div
      style={{
        position: 'fixed',
        top: 8,
        left: 8,
        background: colors.overlayBg,
        border: `1px solid ${colors.border}`,
        borderRadius: 6,
        padding: '6px 10px',
        fontSize: 12,
        color: colors.textPrimary,
        zIndex: 1100,
      }}
    >
      {loading ? '...' : me ? `👤 ${me.username}` : '👤 Guest'}
    </div>
  )
}


