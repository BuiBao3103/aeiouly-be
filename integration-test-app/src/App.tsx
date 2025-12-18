import './App.css'
import { useState } from 'react'
import Tabs from './components/Tabs'
import Home from './pages/Home'
import Login from './pages/Login'
import StreakTest from './pages/StreakTest'
import AuthStatus from './components/AuthStatus'
import { AuthProvider } from './contexts/AuthContext'
import { WebSocketProvider } from './contexts/WebSocketContext'

function App() {
  const [active, setActive] = useState('home')

  const items = [
    { key: 'home', label: 'Home', content: <Home /> },
    { key: 'login', label: 'Login', content: <Login /> },
    { key: 'streak', label: 'Streak Test', content: <StreakTest /> },
  ]

  return (
    <AuthProvider>
    <WebSocketProvider>
      <AuthStatus />
      <Tabs items={items} activeKey={active} onChange={setActive} />
    </WebSocketProvider>
    </AuthProvider>
  )
}

export default App
