import { useEffect, useRef, useState } from 'react'

export default function NotificationsTest() {
  const [logs, setLogs] = useState<string[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const appendLog = (line: string) => setLogs(prev => [...prev, line])

  const connect = () => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) return
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${location.hostname}:8000/notifications/ws`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      appendLog('[open] Connected')
    }
    ws.onmessage = (ev) => {
      appendLog(`[message] ${ev.data}`)
    }
    ws.onerror = () => {
      appendLog('[error] WebSocket error')
    }
    ws.onclose = () => {
      setConnected(false)
      appendLog('[close] Disconnected')
    }
  }

  const disconnect = () => {
    wsRef.current?.close()
  }

  const sendPing = () => {
    const ws = wsRef.current
    if (!ws) {
      appendLog('[warn] Not connected')
      return
    }
    ws.send('ping')
  }

  useEffect(() => {
    return () => wsRef.current?.close()
  }, [])

  return (
    <div style={{ padding: 16 }}>
      <h2>Notifications WebSocket Test</h2>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button onClick={connect} disabled={connected}>Connect</button>
        <button onClick={disconnect} disabled={!connected}>Disconnect</button>
        <button onClick={sendPing} disabled={!connected}>Send ping</button>
      </div>
      <div style={{ border: '1px solid #ccc', padding: 8, height: 260, overflow: 'auto', background: '#fafafa' }}>
        {logs.map((l, i) => (
          <div style={{ color: 'black' }} key={i}>{l}</div>
        ))}
      </div>
      <p style={{ marginTop: 8 }}>Use POST /notifications/broadcast (admin) to push messages here.</p>
    </div>
  )
}


