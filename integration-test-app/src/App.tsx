import './App.css'
import { useState } from 'react'
import Tabs from './components/Tabs'
import Home from './pages/Home'
import NotificationsTest from './pages/NotificationsTest'
import Login from './pages/Login'
import AuthStatus from './components/AuthStatus'

function App() {
  const [active, setActive] = useState('home')

  const items = [
    { key: 'home', label: 'Home', content: <Home /> },
    { key: 'login', label: 'Login', content: <Login /> },
    { key: 'notifications', label: 'Notifications', content: <NotificationsTest /> },
  ]

  return (
    <>
      <AuthStatus />
      <Tabs items={items} activeKey={active} onChange={setActive} />
    </>
  )
}

export default App
