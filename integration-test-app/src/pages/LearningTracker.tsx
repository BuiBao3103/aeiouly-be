import React, { useState, useEffect } from 'react'
import { colors } from '../theme'

interface LearningStats {
  total_minutes: number
  total_sessions: number
  average_session_minutes: number
  current_active_session?: {
    id: number
    session_start: string
    is_active: boolean
  }
}

interface DailyStats {
  date: string
  total_minutes: number
  session_count: number
}

const LearningTracker: React.FC = () => {
  const [stats, setStats] = useState<LearningStats | null>(null)
  const [dailyStats, setDailyStats] = useState<DailyStats[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])

  const fetchStats = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('http://localhost:8000/api/v1/analytics/learning/stats', {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      } else {
        setError('Failed to fetch learning stats')
      }
    } catch (err) {
      setError('Error fetching learning stats')
    } finally {
      setLoading(false)
    }
  }

  const fetchDailyStats = async (date: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/analytics/learning/daily?target_date=${date}`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setDailyStats([data])
      }
    } catch (err) {
      console.error('Error fetching daily stats:', err)
    }
  }

  const startLearningSession = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/analytics/learning/start', {
        method: 'POST',
        credentials: 'include'
      })
      if (response.ok) {
        await fetchStats()
      }
    } catch (err) {
      setError('Failed to start learning session')
    }
  }

  const endLearningSession = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/analytics/learning/end', {
        method: 'POST',
        credentials: 'include'
      })
      if (response.ok) {
        await fetchStats()
      }
    } catch (err) {
      setError('Failed to end learning session')
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  useEffect(() => {
    fetchDailyStats(selectedDate)
  }, [selectedDate])

  const formatMinutes = (minutes: number) => {
    const hours = Math.floor(minutes / 60)
    const mins = Math.floor(minutes % 60)
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('vi-VN')
  }

  return (
    <div style={{ padding: '20px', color: colors.textPrimary }}>
      <h2 style={{ color: colors.textAccent, marginBottom: '20px' }}>📚 Learning Tracker</h2>
      
      {error && (
        <div style={{ 
          background: colors.danger, 
          color: 'white', 
          padding: '10px', 
          borderRadius: '4px', 
          marginBottom: '20px' 
        }}>
          {error}
        </div>
      )}

      {loading && (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          Loading...
        </div>
      )}

      {stats && (
        <div style={{ marginBottom: '30px' }}>
          <h3 style={{ color: colors.textAccent }}>📊 Overall Statistics</h3>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
            gap: '15px',
            marginBottom: '20px'
          }}>
            <div style={{ 
              background: colors.backgroundSecondary, 
              padding: '15px', 
              borderRadius: '8px',
              border: `1px solid ${colors.border}`
            }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: colors.primary }}>
                {formatMinutes(stats.total_minutes)}
              </div>
              <div style={{ color: colors.textSecondary }}>Total Study Time</div>
            </div>
            
            <div style={{ 
              background: colors.backgroundSecondary, 
              padding: '15px', 
              borderRadius: '8px',
              border: `1px solid ${colors.border}`
            }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: colors.success }}>
                {stats.total_sessions}
              </div>
              <div style={{ color: colors.textSecondary }}>Total Sessions</div>
            </div>
            
            <div style={{ 
              background: colors.backgroundSecondary, 
              padding: '15px', 
              borderRadius: '8px',
              border: `1px solid ${colors.border}`
            }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: colors.warning }}>
                {formatMinutes(stats.average_session_minutes)}
              </div>
              <div style={{ color: colors.textSecondary }}>Avg Session</div>
            </div>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ color: colors.textAccent }}>Current Session</h4>
            {stats.current_active_session ? (
              <div style={{ 
                background: colors.success, 
                color: 'white', 
                padding: '10px', 
                borderRadius: '4px',
                display: 'inline-block'
              }}>
                ✅ Active since {new Date(stats.current_active_session.session_start).toLocaleString('vi-VN')}
              </div>
            ) : (
              <div style={{ 
                background: colors.secondary, 
                color: 'white', 
                padding: '10px', 
                borderRadius: '4px',
                display: 'inline-block'
              }}>
                ⏸️ No active session
              </div>
            )}
          </div>

          <div style={{ marginBottom: '20px' }}>
            <button
              onClick={startLearningSession}
              disabled={!!stats.current_active_session}
              style={{
                background: stats.current_active_session ? colors.secondary : colors.success,
                color: 'white',
                border: 'none',
                padding: '10px 20px',
                borderRadius: '4px',
                marginRight: '10px',
                cursor: stats.current_active_session ? 'not-allowed' : 'pointer'
              }}
            >
              Start Learning
            </button>
            
            <button
              onClick={endLearningSession}
              disabled={!stats.current_active_session}
              style={{
                background: !stats.current_active_session ? colors.secondary : colors.danger,
                color: 'white',
                border: 'none',
                padding: '10px 20px',
                borderRadius: '4px',
                cursor: !stats.current_active_session ? 'not-allowed' : 'pointer'
              }}
            >
              End Learning
            </button>
          </div>
        </div>
      )}

      <div>
        <h3 style={{ color: colors.textAccent }}>📅 Daily Statistics</h3>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ marginRight: '10px' }}>Select Date:</label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            style={{
              padding: '8px',
              border: `1px solid ${colors.border}`,
              borderRadius: '4px'
            }}
          />
        </div>
        
        {dailyStats.map((day, index) => (
          <div key={index} style={{ 
            background: colors.backgroundSecondary, 
            padding: '15px', 
            borderRadius: '8px',
            border: `1px solid ${colors.border}`
          }}>
            <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px' }}>
              {formatDate(day.date)}
            </div>
            <div style={{ display: 'flex', gap: '20px' }}>
              <div>
                <span style={{ color: colors.textSecondary }}>Study Time: </span>
                <span style={{ fontWeight: 'bold', color: colors.primary }}>
                  {formatMinutes(day.total_minutes)}
                </span>
              </div>
              <div>
                <span style={{ color: colors.textSecondary }}>Sessions: </span>
                <span style={{ fontWeight: 'bold', color: colors.success }}>
                  {day.session_count}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default LearningTracker
