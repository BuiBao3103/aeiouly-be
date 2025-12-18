import { useState, useEffect } from 'react'
import { colors } from '../theme'
import { useWebSocket } from '../contexts/WebSocketContext'

type WeeklyStreakDay = {
  date: string
  has_streak: boolean
}

type StreakStats = {
  user_id: number
  current_streak: number
  longest_streak: number
  level: string
  next_milestone: number | null
  remaining_to_next_milestone: number
}

type LeaderboardItem = {
  user_id: number
  current_streak: number
  longest_streak: number
}

type WeeklyStreakStatus = {
  current_streak: number
  today_has_streak: boolean
  days: WeeklyStreakDay[]
}

export default function StreakTest() {
  const { connected, logs } = useWebSocket()
  const [stats, setStats] = useState<StreakStats | null>(null)
  const [leaderboard, setLeaderboard] = useState<LeaderboardItem[]>([])
  const [weeklyStatus, setWeeklyStatus] = useState<WeeklyStreakStatus | null>(null)
  const [loading, setLoading] = useState({ stats: false, leaderboard: false, weekly: false })
  const [error, setError] = useState<string | null>(null)

  const fetchStreakStats = async () => {
    setLoading(prev => ({ ...prev, stats: true }))
    setError(null)
    try {
      const response = await fetch('/api/v1/online/streak/stats', {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      } else {
        setError('Failed to fetch streak stats')
      }
    } catch (err) {
      setError('Error fetching streak stats')
    } finally {
      setLoading(prev => ({ ...prev, stats: false }))
    }
  }

  const fetchLeaderboard = async () => {
    setLoading(prev => ({ ...prev, leaderboard: true }))
    setError(null)
    try {
      const response = await fetch('/api/v1/online/streak/leaderboard?limit=10', {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setLeaderboard(data.leaderboard || [])
      } else {
        setError('Failed to fetch leaderboard')
      }
    } catch (err) {
      setError('Error fetching leaderboard')
    } finally {
      setLoading(prev => ({ ...prev, leaderboard: false }))
    }
  }

  const fetchWeeklyStatus = async () => {
    setLoading(prev => ({ ...prev, weekly: true }))
    setError(null)
    try {
      const response = await fetch('/api/v1/online/streak/weekly', {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setWeeklyStatus(data)
      } else {
        setError('Failed to fetch weekly status')
      }
    } catch (err) {
      setError('Error fetching weekly status')
    } finally {
      setLoading(prev => ({ ...prev, weekly: false }))
    }
  }

  const fetchAll = () => {
    fetchStreakStats()
    fetchLeaderboard()
    fetchWeeklyStatus()
  }

  useEffect(() => {
    fetchAll()
  }, [])

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'legend': return '#FFD700'
      case 'diamond': return '#B9F2FF'
      case 'gold': return '#FFD700'
      case 'silver': return '#C0C0C0'
      case 'bronze': return '#CD7F32'
      default: return colors.textSecondary
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('vi-VN', { weekday: 'short', day: 'numeric', month: 'short' })
  }

  return (
    <div style={{ padding: 16, color: colors.textPrimary }}>
      <h2 style={{ color: colors.textAccent, marginBottom: 16 }}>🔥 Streak Test</h2>
      
      {/* Connection Status */}
      <div style={{ 
        display: 'flex', 
        gap: 8, 
        marginBottom: 16,
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        <div style={{
          background: connected ? colors.success : colors.danger,
          color: 'white',
          border: 'none',
          padding: '8px 16px',
          borderRadius: '6px',
          fontSize: '14px',
          fontWeight: 'bold'
        }}>
          {connected ? '✅ WebSocket Connected' : '❌ WebSocket Disconnected'}
        </div>
        
        <button 
          onClick={fetchAll}
          style={{
            background: colors.primary,
            color: 'white',
            border: 'none',
            padding: '8px 16px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          🔄 Refresh All
        </button>
      </div>

      {error && (
        <div style={{ 
          background: colors.danger, 
          color: 'white', 
          padding: '10px', 
          borderRadius: '6px', 
          marginBottom: '16px' 
        }}>
          {error}
        </div>
      )}

      {/* Streak Stats */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ color: colors.textAccent, marginBottom: 12 }}>📊 Your Streak Stats</h3>
        {loading.stats ? (
          <div style={{ padding: 20, textAlign: 'center', color: colors.textSecondary }}>Loading...</div>
        ) : stats ? (
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
            gap: 12,
            marginBottom: 16
          }}>
            <div style={{ 
              background: colors.backgroundSecondary, 
              padding: 16, 
              borderRadius: '8px',
              border: `1px solid ${colors.border}`
            }}>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: colors.primary }}>
                {stats.current_streak}
              </div>
              <div style={{ color: colors.textSecondary }}>Current Streak</div>
            </div>
            
            <div style={{ 
              background: colors.backgroundSecondary, 
              padding: 16, 
              borderRadius: '8px',
              border: `1px solid ${colors.border}`
            }}>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: colors.success }}>
                {stats.longest_streak}
              </div>
              <div style={{ color: colors.textSecondary }}>Longest Streak</div>
            </div>
            
            <div style={{ 
              background: colors.backgroundSecondary, 
              padding: 16, 
              borderRadius: '8px',
              border: `1px solid ${colors.border}`
            }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: getLevelColor(stats.level) }}>
                {stats.level.toUpperCase()}
              </div>
              <div style={{ color: colors.textSecondary }}>Level</div>
            </div>

            {stats.next_milestone && (
              <div style={{ 
                background: colors.backgroundSecondary, 
                padding: 16, 
                borderRadius: '8px',
                border: `1px solid ${colors.border}`
              }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: colors.warning }}>
                  {stats.remaining_to_next_milestone}
                </div>
                <div style={{ color: colors.textSecondary }}>Days to {stats.next_milestone}</div>
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* Weekly Status */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ color: colors.textAccent, marginBottom: 12 }}>📅 Weekly Streak Status</h3>
        {loading.weekly ? (
          <div style={{ padding: 20, textAlign: 'center', color: colors.textSecondary }}>Loading...</div>
        ) : weeklyStatus ? (
          <div>
            <div style={{ 
              background: colors.backgroundSecondary, 
              padding: 16, 
              borderRadius: '8px',
              border: `1px solid ${colors.border}`,
              marginBottom: 16
            }}>
              <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 12 }}>
                <div>
                  <span style={{ color: colors.textSecondary }}>Current Streak: </span>
                  <span style={{ fontSize: '20px', fontWeight: 'bold', color: colors.primary }}>
                    {weeklyStatus.current_streak} days
                  </span>
                </div>
                <div>
                  <span style={{ color: colors.textSecondary }}>Today: </span>
                  <span style={{ 
                    fontSize: '18px', 
                    fontWeight: 'bold', 
                    color: weeklyStatus.today_has_streak ? colors.success : colors.danger 
                  }}>
                    {weeklyStatus.today_has_streak ? '✅ Has streak' : '❌ No streak'}
                  </span>
                </div>
              </div>
            </div>

            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(7, 1fr)', 
              gap: 8
            }}>
              {weeklyStatus.days.map((day, index) => (
                <div 
                  key={index}
                  style={{ 
                    background: day.has_streak ? colors.success : colors.backgroundSecondary,
                    color: day.has_streak ? 'white' : colors.textPrimary,
                    padding: 12, 
                    borderRadius: '8px',
                    border: `1px solid ${day.has_streak ? colors.success : colors.border}`,
                    textAlign: 'center',
                    opacity: day.has_streak ? 1 : 0.6
                  }}
                >
                  <div style={{ fontSize: '12px', marginBottom: 4, opacity: 0.9 }}>
                    {formatDate(day.date)}
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold' }}>
                    {day.has_streak ? '✓' : '○'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      {/* Leaderboard */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ color: colors.textAccent, marginBottom: 12 }}>🏆 Leaderboard</h3>
        {loading.leaderboard ? (
          <div style={{ padding: 20, textAlign: 'center', color: colors.textSecondary }}>Loading...</div>
        ) : leaderboard.length > 0 ? (
          <div style={{ 
            background: colors.backgroundSecondary, 
            padding: 16, 
            borderRadius: '8px',
            border: `1px solid ${colors.border}`
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {leaderboard.map((item, index) => (
                <div 
                  key={item.user_id}
                  style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px',
                    background: index < 3 ? colors.primarySoftBg : 'transparent',
                    borderRadius: '6px',
                    border: index < 3 ? `1px solid ${colors.primarySoftBorder}` : 'none'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ 
                      fontSize: '18px', 
                      fontWeight: 'bold',
                      color: index === 0 ? '#FFD700' : index === 1 ? '#C0C0C0' : index === 2 ? '#CD7F32' : colors.textPrimary,
                      width: 24,
                      textAlign: 'center'
                    }}>
                      {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}.`}
                    </span>
                    <span style={{ color: colors.textPrimary }}>User #{item.user_id}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16 }}>
                    <span style={{ color: colors.textSecondary }}>
                      Current: <strong style={{ color: colors.primary }}>{item.current_streak}</strong>
                    </span>
                    <span style={{ color: colors.textSecondary }}>
                      Longest: <strong style={{ color: colors.success }}>{item.longest_streak}</strong>
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ padding: 20, textAlign: 'center', color: colors.textSecondary }}>
            No leaderboard data
          </div>
        )}
      </div>

      {/* WebSocket Logs */}
      <div>
        <h3 style={{ color: colors.textAccent, marginBottom: 12 }}>📡 WebSocket Messages</h3>
        <div style={{ 
          border: `1px solid ${colors.border}`, 
          padding: 12, 
          height: 200, 
          overflow: 'auto', 
          background: colors.backgroundSecondary,
          borderRadius: '8px',
          fontFamily: 'monospace',
          fontSize: '13px'
        }}>
          {logs.length === 0 ? (
            <div style={{ color: colors.textSecondary, fontStyle: 'italic' }}>
              No messages yet. Connect to start receiving streak notifications...
            </div>
          ) : (
            logs.map((l, i) => (
              <div style={{ 
                color: colors.textPrimary,
                marginBottom: '4px',
                wordBreak: 'break-word'
              }} key={i}>
                {l}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Info Box */}
      <div style={{ 
        marginTop: 16, 
        padding: 12, 
        background: colors.primarySoftBg, 
        borderRadius: '6px',
        border: `1px solid ${colors.primarySoftBorder}`
      }}>
        <p style={{ margin: 0, fontSize: '14px', color: colors.textPrimary }}>
          <strong>💡 How it works:</strong>
        </p>
        <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px', fontSize: '13px', color: colors.textSecondary }}>
          <li>✅ WebSocket auto-connects when you login</li>
          <li>✅ Streak updates when you stay online for 5 minutes (if logged in yesterday)</li>
          <li>✅ You'll receive real-time notifications about streak updates</li>
          <li>✅ Weekly status shows your login activity for the last 7 days</li>
        </ul>
      </div>
    </div>
  )
}

