import { colors } from '../theme'
import { useWebSocket } from '../contexts/WebSocketContext'

export default function NotificationsTest() {
  const { connected, logs, sendMessage, addLog } = useWebSocket()

  const sendPing = () => {
    sendMessage('ping')
  }

  return (
    <div style={{ padding: 16, color: colors.textPrimary }}>
      <h2 style={{ color: colors.textAccent, marginBottom: 16 }}>🔔 Notifications WebSocket Test</h2>
      
      <div style={{ 
        display: 'flex', 
        gap: 8, 
        marginBottom: 16,
        flexWrap: 'wrap'
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
          {connected ? '✅ Connected' : '❌ Disconnected'}
        </div>
        
        <button 
          onClick={sendPing} 
          disabled={!connected}
          style={{
            background: !connected ? colors.secondary : colors.primary,
            color: 'white',
            border: 'none',
            padding: '8px 16px',
            borderRadius: '6px',
            cursor: !connected ? 'not-allowed' : 'pointer',
            fontSize: '14px'
          }}
        >
          📤 Send Ping
        </button>
      </div>
      
      <div style={{ 
        border: `1px solid ${colors.border}`, 
        padding: 12, 
        height: 300, 
        overflow: 'auto', 
        background: colors.backgroundSecondary,
        borderRadius: '8px',
        fontFamily: 'monospace',
        fontSize: '13px'
      }}>
        {logs.length === 0 ? (
          <div style={{ color: colors.textSecondary, fontStyle: 'italic' }}>
            No messages yet. Connect to start receiving notifications...
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
      
      <div style={{ 
        marginTop: 12, 
        padding: 12, 
        background: colors.primarySoftBg, 
        borderRadius: '6px',
        border: `1px solid ${colors.primarySoftBorder}`
      }}>
        <p style={{ margin: 0, fontSize: '14px', color: colors.textPrimary }}>
          <strong>💡 Tips:</strong>
        </p>
        <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px', fontSize: '13px', color: colors.textSecondary }}>
          <li>✅ Auto-connects when app loads</li>
          <li>✅ Auto-reconnects if connection drops</li>
          <li>✅ Stays connected when switching tabs</li>
          <li>✅ Shared across all pages</li>
          <li>✅ Learning notifications every 60 seconds</li>
          <li>💡 Use POST /notifications/broadcast (admin) to push messages</li>
        </ul>
      </div>
    </div>
  )
}


