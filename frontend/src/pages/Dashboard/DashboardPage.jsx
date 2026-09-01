import { useAuth } from '../../hooks/useAuth'
import AdminDashboard from './AdminDashboard'
import ProjectManagerDashboard from './ProjectManagerDashboard'
import TeamLeaderDashboard from './TeamLeaderDashboard'
import DeveloperDashboard from './DeveloperDashboard'
import QADashboard from './QADashboard'
import ReporterDashboard from './ReporterDashboard'

export default function DashboardPage() {
  const { user } = useAuth()
  
  if (!user) return null

  const primaryRole = user.role || user.roles?.[0]?.name

  switch (primaryRole) {
    case 'Admin':
      return <AdminDashboard />
    case 'Project Manager':
      return <ProjectManagerDashboard />
    case 'Team Leader':
      return <TeamLeaderDashboard />
    case 'Developer':
      return <DeveloperDashboard />
    case 'QA':
      return <QADashboard />
    case 'Reporter':
    default:
      return <ReporterDashboard />
  }
}
