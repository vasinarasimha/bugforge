import { useEffect, useState } from 'react'
import IssueTable from '../../components/IssueTable/IssueTable'
import Modal from '../../components/Modal/Modal'
import { createIssue, deleteIssue, getIssues, updateIssue } from '../../services/issueService'
import { getProjects } from '../../services/projectService'
import { formatIssue } from '../../services/aiService'
import { useAuth } from '../../hooks/useAuth'

export default function ReportedIssuesPage() {
  const { user } = useAuth()
  const canDeleteIssue = user?.role === 'Admin' || user?.role === 'QA'
  const empty = { title: '', description: '', project_id: '', priority: 'Medium', status: 'Open', assigned_to: null }

  const [issues, setIssues] = useState([])
  const [projects, setProjects] = useState([])
  const [form, setForm] = useState(empty)
  const [editing, setEditing] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('')
  const [project, setProject] = useState('')
  const [error, setError] = useState('')
  const [formatting, setFormatting] = useState(false)

  const load = async () => {
    const [issueResult, projectResult] = await Promise.all([getIssues(), getProjects()])
    setIssues(issueResult.data)
    setProjects(projectResult.data)
  }

  useEffect(() => { load().catch(() => setError('Unable to load issues.')) }, [])

  const open = (issue = null) => {
    setEditing(issue)
    setForm(issue
      ? { title: issue.title, description: issue.description, project_id: issue.project_id, priority: issue.priority, status: issue.status, assigned_to: issue.assigned_to }
      : empty
    )
    setError('')
    setShowModal(true)
  }

  const handleAIFormat = async () => {
    if (!form.title && !form.description) return
    setFormatting(true)
    try {
      const { data } = await formatIssue({ title: form.title, description: form.description })
      setForm({ ...form, title: data.title, description: data.description, priority: data.priority })
    } catch (e) {
      setError("AI formatting failed.")
    } finally {
      setFormatting(false)
    }
  }

  const save = async (event) => {
    event.preventDefault()
    try {
      const payload = { ...form, project_id: Number(form.project_id), assigned_to: form.assigned_to || null }
      editing ? await updateIssue(editing.id, payload) : await createIssue(payload)
      setShowModal(false)
      await load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Unable to save issue.')
    }
  }

  const remove = (issue) => { setDeleteTarget(issue); setShowDeleteModal(true) }
  const confirmDelete = async () => {
    if (!deleteTarget) return
    await deleteIssue(deleteTarget.id)
    setShowDeleteModal(false)
    setDeleteTarget(null)
    await load()
  }
  const cancelDelete = () => { setShowDeleteModal(false); setDeleteTarget(null) }

  const filtered = issues.filter((issue) =>
    (!status || issue.status === status) &&
    (!project || String(issue.project_id) === project) &&
    (`${issue.id} ${issue.title}`.toLowerCase().includes(query.toLowerCase()))
  )

  return (
    <>
      <section className="page-heading" style={{ animation: 'fadeSlideUp .5s ease both' }}>
        <div>
          <p className="eyebrow">Issue Management</p>
          <h2>Reported Issues</h2>
          <p>Review and follow up on the bugs you have reported.</p>
        </div>
        <button className="btn btn-primary" onClick={() => open()}>
          <i className="bi bi-plus-lg" /> New Issue
        </button>
      </section>

      <section className="panel-card" style={{ animation: 'fadeSlideUp .5s ease .1s both' }}>
        <div className="issue-filters">
          <div className="search-input" style={{ position: 'relative' }}>
            <span className="input-group-text" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none', zIndex: 1 }}>
              <i className="bi bi-search" />
            </span>
            <input
              className="form-control"
              placeholder="Search by ID or title…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <select className="form-select" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option>Open</option>
            <option>In Progress</option>
            <option>Resolved</option>
          </select>
          <select className="form-select" value={project} onChange={(e) => setProject(e.target.value)}>
            <option value="">All projects</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.project_name}</option>)}
          </select>
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        <IssueTable issues={filtered} onEdit={open} onDelete={remove} canDelete={canDeleteIssue} />
      </section>

      {/* Create / Edit modal */}
      {showModal && (
        <div className="modal d-block" tabIndex="-1">
          <div className="modal-dialog">
            <form className="modal-content" onSubmit={save}>
              <div className="modal-header d-flex align-items-center justify-content-between">
                <h5 className="modal-title m-0">{editing ? 'Edit Issue' : 'New Issue'}</h5>
                <div className="d-flex align-items-center gap-2">
                  <button type="button" className="btn btn-sm btn-outline-info" onClick={handleAIFormat} disabled={formatting || !form.title.trim() || !form.description.trim() || form.description.trim().length < 20}>
                    {formatting ? '✨ AI Working...' : '✨ AI Clean & Triage'}
                  </button>
                  <button type="button" className="btn-close m-0" onClick={() => setShowModal(false)} />
                </div>
              </div>
              <div className="modal-body">
                {error && <div className="alert alert-danger">{error}</div>}
                <input required className="form-control mb-3" placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                <textarea required className="form-control mb-3" placeholder="Description" rows={5} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                <select required className="form-select mb-3" value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })}>
                  <option value="">Select project</option>
                  {projects.map((p) => <option key={p.id} value={p.id}>{p.project_name}</option>)}
                </select>
                <select className="form-select" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                  {['Low', 'Medium', 'High', 'Critical'].map((v) => <option key={v}>{v}</option>)}
                </select>
                <select className="form-select" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                  {['Open', 'In Progress', 'Resolved'].map((v) => <option key={v}>{v}</option>)}
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-light" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={!form.title.trim() || !form.description.trim() || form.description.trim().length < 20}>Save</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      {showDeleteModal && (
        <Modal
          title="Delete issue"
          primaryLabel="Delete"
          secondaryLabel="Cancel"
          onPrimary={confirmDelete}
          onSecondary={cancelDelete}
          onClose={cancelDelete}
        >
          <p>Delete issue <strong>"{deleteTarget?.title}"</strong>?</p>
          <p className="text-muted" style={{ marginTop: 6, fontSize: '.88rem' }}>This action cannot be undone.</p>
        </Modal>
      )}
    </>
  )
}
