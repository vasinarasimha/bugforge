import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import Sidebar from '../components/Sidebar/Sidebar'
import Navbar from '../components/Navbar/Navbar'
import { useAuth } from '../hooks/useAuth'

const titles = { '/dashboard': 'Dashboard', '/analytics': 'Analytics & Insights', '/projects': 'Projects', '/sprints': 'Sprints', '/issues': 'Reported Issues' }

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  console.log('DashboardLayout location:', location.pathname) // DEBUG
  const logout = () => { signOut(); navigate('/login', { replace: true }) }
  return <div className="dashboard-shell"><Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} onLogout={logout} /><main className="app-main"><Navbar title={titles[location.pathname] || 'Dashboard'} onMenu={() => setSidebarOpen(true)} /><div className="page-content"><Outlet /></div></main></div>
}
