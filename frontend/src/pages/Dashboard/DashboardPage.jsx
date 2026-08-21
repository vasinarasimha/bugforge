import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import AdminDashboard from './AdminDashboard'
import DeveloperDashboard from './DeveloperDashboard'
import QADashboard from './QADashboard'
import ReporterDashboard from './ReporterDashboard'

export default function DashboardPage() {
  const { user } = useAuth()
  
  if (!user) return null

  switch (user.role) {
    case 'Admin': return <AdminDashboard />
    case 'Developer': return <DeveloperDashboard />
    case 'QA': return <QADashboard />
    case 'Reporter':
    default:
      return <ReporterDashboard />
  }
}
