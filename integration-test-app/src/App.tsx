import './App.css'
import { useState } from 'react'
import Tabs from './components/Tabs'
import Home from './pages/Home'
import NotificationsTest from './pages/NotificationsTest'

function App() {
  const [active, setActive] = useState('home')

  const items = [
    { key: 'home', label: 'Home', content: <Home /> },
    { key: 'notifications', label: 'Notifications', content: <NotificationsTest /> },
  ]

  return (
    <Tabs items={items} activeKey={active} onChange={setActive} />
  )
}

export default App
