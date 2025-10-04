import './App.css'
import { useState } from 'react'
import Tabs from './components/Tabs'
import Home from './pages/Home'
import NotificationsTest from './pages/NotificationsTest'
import Login from './pages/Login'
import LearningTracker from './pages/LearningTracker'
import AuthStatus from './components/AuthStatus'
import { WebSocketProvider } from './contexts/WebSocketContext'

function App() {
  const [active, setActive] = useState('home')

  const items = [
    { key: 'home', label: 'Home', content: <Home /> },
    { key: 'login', label: 'Login', content: <Login /> },
    { key: 'notifications', label: 'Notifications', content: <NotificationsTest /> },
    { key: 'learning', label: 'Learning Tracker', content: <LearningTracker /> },
  ]

  return (
    <WebSocketProvider>
      <AuthStatus />
      <Tabs items={items} activeKey={active} onChange={setActive} />
    </WebSocketProvider>
  )
}

export default App
