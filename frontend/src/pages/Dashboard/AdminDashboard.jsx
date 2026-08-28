import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAdminStats } from '../../services/dashboardService'
import ProjectTable from '../../components/ProjectTable/ProjectTable'
import ActivityTimeline from '../../components/ActivityTimeline/ActivityTimeline'
import StatCard from '../../components/StatCard/StatCard'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getAdminStats()
      .then(({ data }) => setStats(data))
      .catch(() => setError('Unable to load admin statistics'))
  }, [])

  if (error) return <div className="alert alert-danger m-4">{error}</div>
  if (!stats) return <p className="page-status">Loading admin dashboard…</p>

  const statCards = [
    { label: 'Total Users', value: stats.total_users, note: 'Registered accounts', icon: 'bi-people-fill', tone: 'primary' },
    { label: 'Total Projects', value: stats.total_projects, note: 'System-wide projects', icon: 'bi-folder-fill', tone: 'info' },
    { label: 'Open Issues', value: stats.open_issues, note: 'Needing attention', icon: 'bi-bug', tone: 'danger' },
    { label: 'Resolved Issues', value: stats.resolved_issues, note: 'Completed successfully', icon: 'bi-check-circle-fill', tone: 'success' },
  ]

  return (
    <div className="role-admin">
      <section className="welcome-banner role-banner">
        <div>
          {/* <p className="eyebrow">Admin Overview</p> */}
          <h2>System Control Center</h2>
          <p>Monitor system health, user distribution, and overall progress.</p>
        </div>
      </section>

      <section className="stats-grid mb-4">
        {statCards.map((s) => <StatCard key={s.label} stat={s} />)}
      </section>

      <section className="content-grid">
        <div className="panel-card">
          <div className="panel-heading">
            <div>
              <h2>Recent Projects</h2>
              <p>Latest active workspaces</p>
            </div>
          </div>
          <ProjectTable projects={stats.latest_projects} onView={(p) => navigate('/projects', { state: { editProject: p } })} />
        </div>
        <div className="panel-card" style={{ padding: '22px' }}>
          <div className="panel-heading">
            <div>
              <h2>System Activity</h2>
              <p>Recent issues across all projects</p>
            </div>
          </div>
          <ActivityTimeline issues={stats.recent_issues} />
        </div>
      </section>
    </div>
  )
}
