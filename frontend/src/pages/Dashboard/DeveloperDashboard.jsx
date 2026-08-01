import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { getIssues } from '../../services/issueService'
import IssueTable from '../../components/IssueTable/IssueTable'
import StatCard from '../../components/StatCard/StatCard'

export default function DeveloperDashboard() {
  const { user } = useAuth()
  const [issues, setIssues] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    getIssues()
      .then(({ data }) => setIssues(data.filter(i => i.assigned_to === user.id)))
      .catch(() => setError('Unable to load developer issues'))
  }, [user.id])

  const openIssues = issues.filter(i => i.status === 'Open')
  const inProgressIssues = issues.filter(i => i.status === 'In Progress')
  const resolvedIssues = issues.filter(i => i.status === 'Resolved')

  const statCards = [
    { label: 'Assigned to Me', value: issues.length, note: 'Total issues on your plate', icon: 'bi-person-workspace', tone: 'primary' },
    { label: 'To Do', value: openIssues.length, note: 'Ready to be picked up', icon: 'bi-list-task', tone: 'danger' },
    { label: 'In Progress', value: inProgressIssues.length, note: 'Currently working on', icon: 'bi-arrow-repeat', tone: 'warning' },
    { label: 'Completed', value: resolvedIssues.length, note: 'Resolved by you', icon: 'bi-check-circle-fill', tone: 'success' },
  ]

  const firstName = user?.full_name?.split(' ')[0] || 'Developer'

  return (
    <div className="role-developer">
      <section className="welcome-banner role-banner">
        <div>
          <p className="eyebrow">Developer Board</p>
          <h2>Let's build, {firstName} 💻</h2>
          <p>Track the bugs assigned to you and update their status.</p>
        </div>
        <Link to="/issues" className="btn btn-primary">
          <i className="bi bi-list-check" /> View All Issues
        </Link>
      </section>

      {error && <div className="alert alert-danger m-4">{error}</div>}

      <section className="stats-grid mb-4">
        {statCards.map((s) => <StatCard key={s.label} stat={s} />)}
      </section>

      <section className="panel-card mt-4">
        <div className="panel-heading">
          <div>
            <h2>My Tasks</h2>
            <p>Issues currently assigned to you</p>
          </div>
        </div>
        <IssueTable issues={issues} />
      </section>
    </div>
  )
}
