import { useEffect, useState } from 'react'
import ProjectTable from '../../components/ProjectTable/ProjectTable'
import Modal from '../../components/Modal/Modal'
import { createProject, deleteProject, getProjects, updateProject } from '../../services/projectService'
import { useAuth } from '../../hooks/useAuth'

export default function ProjectsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'Admin'

  const [projects, setProjects] = useState([])
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [form, setForm] = useState({ project_name: '', description: '' })
  const [error, setError] = useState('')

  const load = async () => {
    const { data } = await getProjects()
    setProjects(data)
  }

  useEffect(() => { load().catch(() => setError('Unable to load projects.')) }, [])

  const open = (project = null) => {
    setEditing(project)
    setForm(project ? { project_name: project.project_name, description: project.description } : { project_name: '', description: '' })
    setError('')
    setShowModal(true)
  }

  const save = async (event) => {
    event.preventDefault()
    try {
      editing ? await updateProject(editing.id, form) : await createProject(form)
      setShowModal(false)
      await load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Unable to save project.')
    }
  }

  const remove = (project) => { setDeleteTarget(project); setShowDeleteModal(true) }
  const confirmDelete = async () => {
    if (!deleteTarget) return
    await deleteProject(deleteTarget.id)
    setShowDeleteModal(false)
    setDeleteTarget(null)
    await load()
  }
  const cancelDelete = () => { setShowDeleteModal(false); setDeleteTarget(null) }

  const filtered = projects.filter((p) =>
    `${p.project_name} ${p.description}`.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <>
      <section className="page-heading" style={{ animation: 'fadeSlideUp .5s ease both' }}>
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Projects</h2>
          <p>Browse project health, bug volume, and open work.</p>
        </div>
        {isAdmin && (
          <button className="btn btn-primary" onClick={() => open()}>
            <i className="bi bi-plus-lg" /> New Project
          </button>
        )}
      </section>

      <section className="panel-card" style={{ animation: 'fadeSlideUp .5s ease .1s both' }}>
        <div className="panel-heading">
          <div>
            <h2>All Projects</h2>
            <p>Projects in your workspace.</p>
          </div>
          <div className="issue-filters" style={{ marginBottom: 0 }}>
            <div className="search-input" style={{ position: 'relative' }}>
              <span className="input-group-text" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none', zIndex: 1 }}>
                <i className="bi bi-search" />
              </span>
              <input
                className="form-control"
                style={{ paddingLeft: 38, maxWidth: 280 }}
                placeholder="Search projects…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        <ProjectTable projects={filtered} onEdit={open} onDelete={remove} canEdit={isAdmin} canDelete={isAdmin} />
      </section>

      {/* Edit / Create modal */}
      {showModal && (
        <div className="modal d-block" tabIndex="-1">
          <div className="modal-dialog">
            <form className="modal-content" onSubmit={save}>
              <div className="modal-header">
                <h5 className="modal-title">{editing ? 'Edit Project' : 'New Project'}</h5>
                <button type="button" className="btn-close" onClick={() => setShowModal(false)} />
              </div>
              <div className="modal-body">
                {error && <div className="alert alert-danger">{error}</div>}
                <label className="form-label">Project Name</label>
                <input required className="form-control" value={form.project_name} onChange={(e) => setForm({ ...form, project_name: e.target.value })} placeholder="e.g. Phoenix Backend" />
                <label className="form-label" style={{ marginTop: 14 }}>Description</label>
                <textarea className="form-control" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="What is this project about?" />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-light" onClick={() => setShowModal(false)}>Cancel</button>
                {isAdmin && <button className="btn btn-primary">Save</button>}
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete confirm modal */}
      {showDeleteModal && (
        <Modal
          title="Confirm delete"
          primaryLabel="Delete"
          secondaryLabel="Cancel"
          onPrimary={confirmDelete}
          onSecondary={cancelDelete}
          onClose={cancelDelete}
        >
          <p>Delete project <strong>"{deleteTarget?.project_name}"</strong> and all its issues?</p>
          <p className="text-muted" style={{ marginTop: 6, fontSize: '.88rem' }}>This action cannot be undone.</p>
        </Modal>
      )}
    </>
  )
}
