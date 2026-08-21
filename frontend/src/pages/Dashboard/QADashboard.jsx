import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { getIssues, updateIssue, updateIssueStatus } from '../../services/issueService'
import IssueTable from '../../components/IssueTable/IssueTable'
import StatCard from '../../components/StatCard/StatCard'

export default function QADashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [issues, setIssues] = useState([])
  const [error, setError] = useState('')

  const load = () => {
    getIssues()
      .then(({ data }) => setIssues(data))
      .catch(() => setError('Unable to load QA issues'))
  }

  useEffect(() => { load() }, [])

  const handleAction = async (issue, action) => {
    try {
      if (action === 'resolve') {
        // Technically sending to Reporter or closing. We will Close it for simplicity as per 4-step workflow
        await updateIssueStatus(issue.id, { status_id: 4 }) // 4 = Closed
      } else if (action === 'unresolve') {
        await updateIssueStatus(issue.id, { status_id: 2 }) // 2 = In Progress
      }
      load()
    } catch (e) {
      setError('Failed to update issue status')
    }
  }

  const openIssues = issues.filter(i => i.status_name === 'Open')
  const inProgressIssues = issues.filter(i => i.status_name === 'In Progress')

  // QA focuses on Resolved defects to test/verify
  const resolvedIssues = issues.filter(i => i.status_name === 'Resolved')

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
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {resolvedIssues.map(i => (
                <tr key={i.id}>
                  <td>{i.issue_key}</td>
                  <td>{i.title}</td>
                  <td><span className="badge bg-secondary">{i.priority}</span></td>
                  <td>
                    <button className="btn btn-sm btn-success me-2" onClick={() => handleAction(i, 'resolve')}>Verify (Close)</button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleAction(i, 'unresolve')}>Reject (In Progress)</button>
                  </td>
                </tr>
              ))}
              {resolvedIssues.length === 0 && <tr><td colSpan="4" className="text-center">No resolved defects pending verification.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}