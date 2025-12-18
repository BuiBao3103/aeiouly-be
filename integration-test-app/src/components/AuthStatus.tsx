import { colors } from '../theme'
import { useAuth } from '../contexts/AuthContext'

export default function AuthStatus() {
  const { user, loading } = useAuth()

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
      {loading ? '...' : user ? `👤 ${user.username}` : '👤 Guest'}
    </div>
  )
}
