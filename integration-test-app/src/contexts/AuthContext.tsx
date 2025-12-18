import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface User {
  id: number
  username: string
  email?: string
  full_name?: string
  role?: string
}

interface AuthContextType {
  user: User | null
  accessToken: string | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  loginWithGoogle: (idToken: string) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const checkAuth = async () => {
    try {
      const res = await fetch('/api/v1/auth/me', {
        method: 'GET',
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setUser(data)
        // With proxy, cookies are sent automatically, so we don't need to store accessToken
        // WebSocket will use cookies for authentication
      } else {
        setUser(null)
        setAccessToken(null)
      }
    } catch {
      setUser(null)
      setAccessToken(null)
    } finally {
      setLoading(false)
    }
  }

  const login = async (username: string, password: string) => {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
      credentials: 'include',
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || 'Login failed')
    }
    const data = await res.json()
    setAccessToken(data.access_token)
    await checkAuth()
  }

  const loginWithGoogle = async (idToken: string) => {
    const res = await fetch('/api/v1/auth/google', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken }),
    })
    if (!res.ok) {
      const errText = await res.text().catch(() => '')
      throw new Error(errText || 'Google login failed')
    }
    const data = await res.json()
    setAccessToken(data.access_token)
    await checkAuth()
  }

  const logout = async () => {
    try {
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
      })
    } catch {
      // Ignore errors
    } finally {
      setUser(null)
      setAccessToken(null)
    }
  }

  // Check auth on mount
  useEffect(() => {
    checkAuth()
  }, [])

  const value: AuthContextType = {
    user,
    accessToken,
    loading,
    login,
    loginWithGoogle,
    logout,
    checkAuth,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

