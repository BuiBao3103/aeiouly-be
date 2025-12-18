import React, { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useAuth } from './AuthContext'

interface WebSocketContextType {
  connected: boolean
  logs: string[]
  sendMessage: (message: string) => void
  addLog: (message: string) => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

interface WebSocketProviderProps {
  children: ReactNode
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { user, loading } = useAuth()
  const [connected, setConnected] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  const addLog = (line: string) => {
    const timestamp = new Date().toLocaleTimeString()
    setLogs(prev => [...prev, `[${timestamp}] ${line}`])
  }

  const connect = () => {
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${location.host}/online/ws`
    
    addLog('🔑 Connecting...')
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      addLog('✅ Connected to WebSocket')
    }
    
    ws.onmessage = (ev) => {
      addLog(`📨 ${ev.data}`)
    }
    
    ws.onerror = (error) => {
      addLog('❌ WebSocket error')
      console.error('WebSocket error:', error)
    }
    
    ws.onclose = (event) => {
      setConnected(false)
      addLog(`🔌 Disconnected (code: ${event.code})`)
    }
  }

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect')
      wsRef.current = null
    }
    setConnected(false)
  }

  const sendMessage = (message: string) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      addLog('⚠️ Not connected')
      return
    }
    ws.send(message)
    addLog(`📤 Sent: ${message}`)
  }

  // Connect when user is logged in (cookies will be sent automatically via proxy)
  useEffect(() => {
    // Wait for auth check to complete
    if (loading) return
    
    // If user is logged in, connect WebSocket
    if (user) {
        connect()
      } else {
      // User not logged in, disconnect
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, loading])

  const value: WebSocketContextType = useMemo(() => ({
    connected,
    logs,
    sendMessage,
    addLog
  }), [connected, logs])

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  )
}

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext)
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}
