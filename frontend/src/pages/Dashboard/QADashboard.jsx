import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { getIssues } from '../../services/issueService'
import IssueTable from '../../components/IssueTable/IssueTable'
import StatCard from '../../components/StatCard/StatCard'

export default function QADashboard() {
  const { user } = useAuth()
  const [issues, setIssues] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    getIssues()
      .then(({ data }) => setIssues(data))
      .catch(() => setError('Unable to load QA issues'))
  }, [])

  const openIssues = issues.filter(i => i.status === 'Open')
  const inProgressIssues = issues.filter(i => i.status === 'In Progress')
  const criticalIssues = issues.filter(i => i.priority === 'Critical')
  
  // QA focuses on open and in-progress bugs to test/verify
  const activeIssues = issues.filter(i => i.status !== 'Resolved')

  const statCards = [
    { label: 'Active Queue', value: activeIssues.length, note: 'Bugs to track and verify', icon: 'bi-bug-fill', tone: 'primary' },
    { label: 'Open', value: openIssues.length, note: 'Unassigned or new', icon: 'bi-exclamation-circle-fill', tone: 'danger' },
    { label: 'In Progress', value: inProgressIssues.length, note: 'Currently being fixed', icon: 'bi-arrow-repeat', tone: 'warning' },
    { label: 'Critical Priority', value: criticalIssues.length, note: 'System-breaking issues', icon: 'bi-shield-fill-exclamation', tone: 'danger' },
  ]

  const firstName = user?.full_name?.split(' ')[0] || 'QA'

  return (
    <div className="role-qa">
      <section className="welcome-banner role-banner">
        <div>
          <p className="eyebrow">Quality Assurance</p>
          <h2>Verify and Validate, {firstName} 🔍</h2>
          <p>Monitor active issues and ensure they meet quality standards.</p>
        </div>
        <Link to="/issues" className="btn btn-primary">
          <i className="bi bi-funnel-fill" /> Browse All Issues
        </Link>
      </section>

      {error && <div className="alert alert-danger m-4">{error}</div>}

      <section className="stats-grid mb-4">
        {statCards.map((s) => <StatCard key={s.label} stat={s} />)}
      </section>

      <section className="panel-card mt-4">
        <div className="panel-heading">
          <div>
            <h2>Active QA Queue</h2>
            <p>All unresolved issues requiring verification</p>
          </div>
        </div>
        <IssueTable issues={activeIssues} />
      </section>
    </div>
  )
}
