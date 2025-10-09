import { useEffect, useRef, useState } from 'react'

declare global {
  interface Window {
    google?: any
  }
}

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [msg, setMsg] = useState('')
  const googleBtnRef = useRef<HTMLDivElement | null>(null)

  const login = async () => {
    setMsg('')
    try {
      const res = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: 'include',
      })
      if (!res.ok) {
        const text = await res.text()
        setMsg(`Login failed: ${text}`)
        return
      }
      setMsg('Login success')
      window.dispatchEvent(new CustomEvent('auth:changed', { detail: { status: 'logged_in' } }))
    } catch (e) {
      setMsg('Login error')
    }
  }

  const logout = async () => {
    setMsg('')
    try {
      const res = await fetch('http://localhost:8000/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
      })
      if (!res.ok) {
        const text = await res.text()
        setMsg(`Logout failed: ${text}`)
        return
      }
      setMsg('Logged out')
      window.dispatchEvent(new CustomEvent('auth:changed', { detail: { status: 'logged_out' } }))
    } catch {
      setMsg('Logout error')
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
      const res = await fetch('http://localhost:8000/api/v1/auth/google', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: resp.credential }),
      })
      if (!res.ok) {
        const errText = await res.text().catch(() => '')
        setMsg(`Google login failed: ${errText || res.status}`)
        return
      }
      setMsg('Google login success')
      window.dispatchEvent(new CustomEvent('auth:changed', { detail: { status: 'logged_in' } }))
    } catch (e: any) {
      setMsg(`Google login error: ${e?.message || e}`)
    }
  }

  return (
    <div style={{ padding: 16, maxWidth: 420 }}>
      <h2>Login</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <input placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} />
        <input placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={login}>Login</button>
          <button onClick={logout}>Logout</button>
        </div>
        <div style={{ height: 1, background: '#eee', margin: '8px 0' }} />
        <div ref={googleBtnRef} />
        {msg && <div style={{ fontSize: 12 }}>{msg}</div>}
      </div>
    </div>
  )
}


