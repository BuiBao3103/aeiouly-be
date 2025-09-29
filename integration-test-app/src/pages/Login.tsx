import { useState } from 'react'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [msg, setMsg] = useState('')

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
    } catch {
      setMsg('Logout error')
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
        {msg && <div style={{ fontSize: 12 }}>{msg}</div>}
      </div>
    </div>
  )
}


