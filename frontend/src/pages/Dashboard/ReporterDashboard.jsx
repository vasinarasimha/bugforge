import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { getDashboardStatistics } from '../../services/dashboardService'
import { getProjects } from '../../services/projectService'
import { createIssue, getIssues } from '../../services/issueService'
import StatCard from '../../components/StatCard/StatCard'
import ProjectTable from '../../components/ProjectTable/ProjectTable'
import ActivityTimeline from '../../components/ActivityTimeline/ActivityTimeline'

export default function ReporterDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [dashboard, setDashboard] = useState(null)
  const [modal, setModal] = useState(null)
  const [projects, setProjects] = useState([])
  const [myIssues, setMyIssues] = useState([])
  const [issueForm, setIssueForm] = useState({ title: '', description: '', project_id: '', priority: 'Medium', status: 'Open' })

  const refresh = () => {
    getDashboardStatistics()
      .then(({ data }) => setDashboard(data))
      .catch(() => setDashboard({ latest_projects: [], recent_issues: [] }))
      
    getIssues()
      .then(({ data }) => setMyIssues(data.filter(i => i.reporter_id === user.id)))
      .catch(() => {})
  }

  useEffect(() => { refresh() }, [])

  const openIssue = async () => {
    const { data } = await getProjects()
    setProjects(data)
    setModal('issue')
  }

  const saveIssue = async (event) => {
    event.preventDefault()
    await createIssue({ ...issueForm, project_id: Number(issueForm.project_id) })
    setModal(null)
    setIssueForm({ title: '', description: '', project_id: '', priority: 'Medium', status: 'Open' })
    refresh()
  }

  const stats = [
    { label: 'My Reported Defects', value: myIssues.length, note: 'Issues you created', icon: 'bi-bug', tone: 'danger' },
    { label: 'Total Projects', value: dashboard?.total_projects || 0, note: 'Available to report in', icon: 'bi-folder2-open', tone: 'primary' },
    { label: 'Issues In Progress', value: dashboard?.total_in_progress || 0, note: 'System-wide active work', icon: 'bi-arrow-repeat', tone: 'warning' },
    { label: 'Resolved Issues', value: dashboard?.total_resolved || 0, note: 'System-wide resolved', icon: 'bi-check2-circle', tone: 'success' },
  ]

  const firstName = user?.full_name?.split(' ')[0] || 'Reporter'

  return (
    <div className="role-reporter">
      {/* Welcome banner */}
      <section className="welcome-banner role-banner">
        <div>
          {/* <p className="eyebrow">Reporter Workspace</p> */}
          <h2>Welcome back, {firstName} 👋</h2>
          <p>Track your reported issues and monitor project progress from one place.</p>
        </div>
        <button className="btn btn-primary" onClick={openIssue}>
          <i className="bi bi-plus-lg" /> Report New Issue
        </button>
      </section>

      {/* Stat cards */}
      <section className="stats-grid mb-4">
        {stats.map((stat) => <StatCard key={stat.label} stat={stat} />)}
      </section>

      {/* Content grid */}
      <section className="content-grid">
        <div className="panel-card">
          <div className="panel-heading">
            <div>
              <h2>Project Overview</h2>
              <p>A snapshot of projects in your workspace.</p>
            </div>
            <Link to="/projects" className="btn btn-outline-primary btn-sm">View all</Link>
          </div>
          <ProjectTable projects={dashboard?.latest_projects} onView={(p) => navigate('/projects', { state: { editProject: p } })} />
        </div>
        <div className="panel-card" style={{ padding: '22px' }}>
          <div className="panel-heading">
            <div>
              <h2>My Recent Reports</h2>
              <p>The latest defects you've reported</p>
            </div>
          </div>
          <ActivityTimeline issues={myIssues.slice(0, 5)} />
        </div>
      </section>

      {/* New issue modal */}
      {modal === 'issue' && (
        <div className="modal d-block">
          <div className="modal-dialog">
            <form className="modal-content" onSubmit={saveIssue} autoComplete="off">
              <div className="modal-header">
                <h5 className="modal-title">New Issue</h5>
                <button type="button" className="btn-close" onClick={() => setModal(null)} />
              </div>
              <div className="modal-body">
                <input required className="form-control" placeholder="Title" value={issueForm.title} autoComplete="off" onChange={(e) => setIssueForm({ ...issueForm, title: e.target.value })} />
                <textarea required className="form-control" placeholder="Description" value={issueForm.description} autoComplete="off" onChange={(e) => setIssueForm({ ...issueForm, description: e.target.value })} />
                <select required className="if-select" value={issueForm.project_id} onChange={(e) => setIssueForm({ ...issueForm, project_id: e.target.value })}>
                  <option value="">Select project</option>
                  {projects.map((p) => <option key={p.id} value={p.id}>{p.project_name}</option>)}
                </select>
                <select className="if-select" value={issueForm.priority} onChange={(e) => setIssueForm({ ...issueForm, priority: e.target.value })}>
                  {['Low', 'Medium', 'High', 'Critical'].map((v) => <option key={v}>{v}</option>)}
                </select>
                <select className="if-select" value={issueForm.status} onChange={(e) => setIssueForm({ ...issueForm, status: e.target.value })}>
                  {['Open', 'In Progress', 'Resolved'].map((v) => <option key={v}>{v}</option>)}
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-light" onClick={() => setModal(null)}>Cancel</button>
                <button className="btn btn-primary">Save Issue</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
