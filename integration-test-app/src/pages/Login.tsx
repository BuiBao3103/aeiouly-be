import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

declare global {
  interface Window {
    google?: any
  }
}

export default function Login() {
  const { login, loginWithGoogle, logout, user } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [msg, setMsg] = useState('')
  const googleBtnRef = useRef<HTMLDivElement | null>(null)

  const handleLogin = async () => {
    setMsg('')
    try {
      await login(username, password)
      setMsg('Login success')
    } catch (e: any) {
      setMsg(`Login failed: ${e?.message || 'Login error'}`)
    }
  }

  const handleLogout = async () => {
    setMsg('')
    try {
      await logout()
      setMsg('Logged out')
    } catch (e: any) {
      setMsg(`Logout error: ${e?.message || 'Logout error'}`)
    }
  }

  useEffect(() => {
    const id = 'google-identity'
    if (document.getElementById(id)) {
      initGoogle()
      return
    }
    const s = document.createElement('script')
    s.src = 'https://accounts.google.com/gsi/client'
    s.async = true
    s.defer = true
    s.id = id
    s.onload = initGoogle
    document.head.appendChild(s)
  }, [])

  function initGoogle() {
    if (!window.google) return
    const clientId = (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID || ''
    if (!clientId) {
      setMsg('Missing VITE_GOOGLE_CLIENT_ID')
      return
    }
    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: handleGoogleCredential,
    })
    if (googleBtnRef.current) {
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'pill',
        width: 280,
      })
    }
  }

  async function handleGoogleCredential(resp: { credential: string }) {
    try {
      setMsg('Signing in with Google...')
      await loginWithGoogle(resp.credential)
      setMsg('Google login success')
    } catch (e: any) {
      setMsg(`Google login error: ${e?.message || e}`)
    }
  }

  return (
    <div style={{ padding: 16, maxWidth: 420 }}>
      <h2>Login</h2>
      {user && <div style={{ marginBottom: 8, fontSize: 14 }}>Logged in as: {user.username}</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <input placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} />
        <input placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={handleLogin}>Login</button>
          <button onClick={handleLogout}>Logout</button>
        </div>
        <div style={{ height: 1, background: '#eee', margin: '8px 0' }} />
        <div ref={googleBtnRef} />
        {msg && <div style={{ fontSize: 12 }}>{msg}</div>}
      </div>
    </div>
  )
}
