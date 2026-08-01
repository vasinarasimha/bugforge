import { useEffect, useState } from 'react'
import { getAdminStats } from '../../services/dashboardService'
import { summarizeTimeline } from '../../services/aiService'
import ProjectTable from '../../components/ProjectTable/ProjectTable'
import ActivityTimeline from '../../components/ActivityTimeline/ActivityTimeline'
import StatCard from '../../components/StatCard/StatCard'

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')
  const [aiSummary, setAiSummary] = useState(null)
  const [aiLoading, setAiLoading] = useState(false)

  useEffect(() => {
    getAdminStats()
      .then(({ data }) => {
        setStats(data)
        setAiLoading(true)
        summarizeTimeline({ recent_issues: data.recent_issues })
          .then((res) => setAiSummary(res.data.summary))
          .catch(() => setAiSummary("Unable to load AI Insights."))
          .finally(() => setAiLoading(false))
      })
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
          <p className="eyebrow">Admin Overview</p>
          <h2>System Control Center</h2>
          <p>Monitor system health, user distribution, and overall progress.</p>
        </div>
      </section>

      <section className="stats-grid mb-4">
        {statCards.map((s) => <StatCard key={s.label} stat={s} />)}
      </section>

      <section className="mb-4" style={{ animation: 'fadeSlideUp .5s ease .15s both' }}>
        <div className="alert d-flex align-items-center mb-0" style={{ backgroundColor: 'var(--bg-panel)', border: '1px solid var(--border)', color: 'var(--text-main)', borderRadius: '12px', padding: '16px 20px' }}>
          <i className="bi bi-robot fs-4 me-3" style={{ color: 'var(--tone-info)' }} />
          <div>
            <h6 className="mb-1 fw-bold" style={{ color: 'var(--tone-info)' }}>✨ AI Insights</h6>
            <p className="mb-0 text-muted" style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
              {aiLoading ? (
                <><span className="spinner-border spinner-border-sm me-2"/> Analyzing recent activity...</>
              ) : (
                aiSummary
              )}
            </p>
          </div>
        </div>
      </section>

      <section className="content-grid">
        <div className="panel-card">
          <div className="panel-heading">
            <div>
              <h2>Recent Projects</h2>
              <p>Latest active workspaces</p>
            </div>
          </div>
          <ProjectTable projects={stats.latest_projects} />
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
