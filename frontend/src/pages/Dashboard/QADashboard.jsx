import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { getIssues, getStatuses, updateIssue, updateIssueStatus } from '../../services/issueService'
import IssueTable from '../../components/IssueTable/IssueTable'
import StatCard from '../../components/StatCard/StatCard'

export default function QADashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [issues, setIssues] = useState([])
  const [statuses, setStatuses] = useState([])
  const [error, setError] = useState('')

  const load = () => {
    Promise.all([
      getIssues(),
      getStatuses().catch(() => ({ data: [] }))
    ])
      .then(([issuesRes, statusesRes]) => {
        setIssues(issuesRes.data || [])
        setStatuses(statusesRes.data || [])
      })
      .catch(() => setError('Unable to load QA issues'))
  }

  useEffect(() => { load() }, [])

  const handleAction = async (issue, action) => {
    try {
      if (action === 'resolve') {
        const closedStatus = statuses.find(s => s.category === 'closed' || s.name.toLowerCase() === 'closed')
        const targetId = closedStatus ? closedStatus.id : (statuses.find(s => s.is_final)?.id || 4)
        await updateIssueStatus(issue.id, { status_id: targetId })
      } else if (action === 'unresolve') {
        const inProgStatus = statuses.find(s => s.category === 'in_progress' || s.name.toLowerCase() === 'in progress')
        const targetId = inProgStatus ? inProgStatus.id : 2
        await updateIssueStatus(issue.id, { status_id: targetId })
      }
      load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to update issue status')
    }
  }

  const openIssues = issues.filter(i => i.status_name === 'Open')
  const inProgressIssues = issues.filter(i => i.status_name === 'In Progress')

  // QA focuses on Resolved defects to test/verify
  // If a specific QA is assigned, only that QA sees it in their verification queue.
  // If no QA is assigned yet, all QAs see it so they can claim/verify it.
  const resolvedIssues = issues.filter(i => {
    if (i.status_name !== 'Resolved') return false
    if (i.assigned_qa_id) {
      return i.assigned_qa_id === user?.id
    }
    return true
  })

  const statCards = [
    { label: 'Ready for QA', value: resolvedIssues.length, note: 'Defects to test', icon: 'bi-bug-fill', tone: 'primary' },
    { label: 'Open', value: openIssues.length, note: 'Unassigned or new', icon: 'bi-exclamation-circle-fill', tone: 'danger' },
    { label: 'In Progress', value: inProgressIssues.length, note: 'Currently being fixed', icon: 'bi-arrow-repeat', tone: 'warning' }
  ]

  const firstName = user?.full_name?.split(' ')[0] || 'QA'

  return (
    <div className="role-qa">
      <section className="welcome-banner role-banner">
        <div>
          {/* <p className="eyebrow">Quality Assurance</p> */}
          <h2>Verify and Validate, {firstName} </h2>
          <p>Monitor resolved issues and ensure they meet quality standards.</p>
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
            <h2>Resolved Defects Queue</h2>
            <p>Issues fixed by developers awaiting your verification</p>
          </div>
        </div>
        <div className="table-responsive p-3">
          <table className="table table-hover">
            <thead>
              <tr>
                <th>Key</th>
                <th>Title</th>
                <th>Priority</th>
                <th>Assigned QA</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {resolvedIssues.map(i => (
                <tr key={i.id} className={i.is_qa_unassigned_over_1h ? 'table-danger' : ''}>
                  <td>{i.issue_key}</td>
                  <td>
                    {i.title}
                    {i.is_qa_unassigned_over_1h && (
                      <span className="badge bg-danger ms-2" style={{ fontSize: '0.72rem' }}>
                        &gt;1h QA Unassigned
                      </span>
                    )}
                  </td>
                  <td><span className="badge bg-secondary">{i.priority}</span></td>
                  <td>
                    {i.assigned_qa_name ? (
                      <span className="badge bg-primary-subtle text-primary border border-primary-subtle">
                        {i.assigned_qa_id === user?.id ? 'Assigned to You' : i.assigned_qa_name}
                      </span>
                    ) : (
                      <span className="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle">
                        Unassigned
                      </span>
                    )}
                  </td>
                  <td>
                    <button className="btn btn-sm btn-success me-2" onClick={() => handleAction(i, 'resolve')}>Verify (Close)</button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleAction(i, 'unresolve')}>Reject (In Progress)</button>
                  </td>
                </tr>
              ))}
              {resolvedIssues.length === 0 && <tr><td colSpan="5" className="text-center">No resolved defects pending verification.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}