import React, { createContext, useContext, useEffect, useRef, useState, ReactNode } from 'react'

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
  const [connected, setConnected] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const [autoConnect, setAutoConnect] = useState(true)

  const addLog = (line: string) => {
    const timestamp = new Date().toLocaleTimeString()
    setLogs(prev => [...prev, `[${timestamp}] ${line}`])
  }

  const connect = () => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) return
    
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${location.hostname}:8000/notifications/ws`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      addLog('✅ Connected to WebSocket')
      // Clear any pending reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
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
      
      // Auto-reconnect if autoConnect is enabled and it's not a manual close
      if (autoConnect && event.code !== 1000) {
        addLog('🔄 Auto-reconnecting in 3 seconds...')
        reconnectTimeoutRef.current = setTimeout(() => {
          if (autoConnect) {
            connect()
          }
        }, 3000)
      }
    }
  }

  const disconnect = () => {
    setAutoConnect(false)
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    wsRef.current?.close(1000, 'Manual disconnect')
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

  // Auto-connect on mount and handle page visibility
  useEffect(() => {
    connect()
    
    const handleVisibilityChange = () => {
      if (!document.hidden && !connected && autoConnect) {
        addLog('👁️ Page visible, reconnecting...')
        connect()
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      // Only close on unmount, not on tab switch
      wsRef.current?.close(1000, 'Component unmount')
    }
  }, [])

  const value: WebSocketContextType = {
    connected,
    logs,
    sendMessage,
    addLog
  }

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
