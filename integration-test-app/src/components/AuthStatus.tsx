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
  const [lastFetch, setLastFetch] = useState<number>(0)

  const fetchMe = async (force = false) => {
    const now = Date.now()
    // Only fetch if forced or if it's been more than 30 seconds since last fetch
    if (!force && now - lastFetch < 30000) {
      return
    }
    
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
      setLastFetch(now)
    } catch {
      setMe(null)
    } finally {
      setLoading(false)
    }
  }

  // Fetch on mount and when window regains focus
  useEffect(() => {
    fetchMe(true)
    
    const handleFocus = () => {
      fetchMe(true)
    }
    
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        fetchMe(true)
      }
    }
    
    window.addEventListener('focus', handleFocus)
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      window.removeEventListener('focus', handleFocus)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
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


