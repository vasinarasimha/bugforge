import { useEffect, useState } from 'react'
import ProjectTable from '../../components/ProjectTable/ProjectTable'
import Modal from '../../components/Modal/Modal'
import { createProject, deleteProject, getProjects, updateProject, getProjectHistory } from '../../services/projectService'
import { getUsers } from '../../services/authService'
import { getTeams } from '../../services/teamService'
import { useAuth } from '../../hooks/useAuth'
import { getFieldLabel, isIgnoredTimelineField } from '../../utils/activityHelper'
import { useLocation } from 'react-router-dom'
import SearchableSelect from '../../components/common/SearchableSelect'

export default function ProjectsPage() {
  const { user } = useAuth()
  const location = useLocation()

  const userRoles = user?.roles?.map(r => r.name) || []
  const isAdmin = user?.role === 'Admin' || user?.role === 'Super Admin' || userRoles.includes('Admin') || userRoles.includes('Super Admin')
  const isProjectManager = userRoles.includes('Project Manager') || user?.role === 'Project Manager'
  const canEditProjects = isAdmin || isProjectManager
  const canDeleteProjects = isAdmin  // Only Admin can delete per requirements

  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [historyModalProject, setHistoryModalProject] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [users, setUsers] = useState([])
  const [usersLoading, setUsersLoading] = useState(true)
  const [teams, setTeams] = useState([])
  const [teamsLoading, setTeamsLoading] = useState(true)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyRecords, setHistoryRecords] = useState([])
  const emptyForm = {
    project_name: '',
    description: '',
    status: 'Active',
    repository_url: '',
    client_name: '',
    start_date: '',
    end_date: '',
    budget: '',
    tech_stack: '',
    team_id: null
  }
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')

  const selectedTeam = teams.find(t => t.id === form.team_id)

  const loadTeams = async () => {
    try {
      setTeamsLoading(true)
      const { data } = await getTeams()
      setTeams(data || [])
    } catch (err) {
      console.error('Failed to load teams:', err)
      setTeams([])
    } finally {
      setTeamsLoading(false)
    }
  }

  const loadUsers = async () => {
    try {
      setUsersLoading(true)
      const { data } = await getUsers('', 100, 0)
      setUsers(data.data || [])
    } catch (err) {
      console.error('Failed to load users:', err)
      setUsers([])
    } finally {
      setUsersLoading(false)
    }
  }

  const load = async () => {
    try {
      const { data } = await getProjects()
      setProjects(data)
    } catch (err) {
      setError('Unable to load projects.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTeams().catch(() => {})
    loadUsers().catch(() => setError('Unable to load users.'))
    load().catch(() => setError('Unable to load projects.'))
  }, [])

  const open = (project = null) => {
    setEditing(project)
    setForm(project ? {
      project_name: project.name,
      description: project.description,
      status: project.status || 'Active',
      repository_url: project.repository_url || '',
      client_name: project.client_name || '',
      start_date: project.start_date ? project.start_date.split('T')[0] : '',
      end_date: project.end_date ? project.end_date.split('T')[0] : '',
      budget: project.budget || '',
      tech_stack: project.tech_stack || '',
      team_id: project.team_id || null
    } : emptyForm)
    setError('')
    setShowModal(true)
  }

  const save = async (event) => {
    event.preventDefault()
    try {
      const payload = {
        ...form,
        name: form.project_name,
        key: form.project_name.substring(0, 3).toUpperCase() + Math.floor(100 + Math.random() * 900),
        start_date: form.start_date ? new Date(form.start_date).toISOString() : null,
        end_date: form.end_date ? new Date(form.end_date).toISOString() : null,
        team_id: form.team_id || null
      }
      editing ? await updateProject(editing.id, payload) : await createProject(payload)
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

  const viewHistory = async (project) => {
    setHistoryModalProject(project)
    setHistoryRecords([])
    setHistoryLoading(true)
    try {
      const { data } = await getProjectHistory(project.id)
      setHistoryRecords(data)
    } catch (err) {
      console.error('Failed to load project history:', err)
      setError('Unable to load project history.')
    } finally {
      setHistoryLoading(false)
    }
    setShowHistoryModal(true)
  }

  const closeHistoryModal = () => {
    setShowHistoryModal(false)
    setHistoryModalProject(null)
    setHistoryRecords([])
  }

  const filtered = projects.filter((p) =>
    `${p.project_name} ${p.description}`.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <>
      <section className="page-heading" style={{ animation: 'fadeSlideUp .5s ease both' }}>
        <div>
          <h2>Projects</h2>
          <p>Browse project health, defect volume, and open work.</p>
        </div>
        {canEditProjects && (
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
                autoComplete="off"
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>
        </div>
        {error && <div className="alert alert-danger">{error}</div>}
        {loading ? (
            <div className="text-center py-5" style={{ animation: 'fadeSlideUp .5s ease both' }}>
              <div className="spinner-border text-primary" role="status"></div>
              <p className="mt-2 text-muted">Loading projects...</p>
            </div>
          ) : (
            <ProjectTable
              projects={filtered}
              onEdit={open}
              onDelete={remove}
              onViewHistory={viewHistory}
              canEdit={canEditProjects}
              canDelete={canDeleteProjects}
              userRoles={userRoles}
              isAdmin={isAdmin}
              isProjectManager={isProjectManager}
            />
          )}
        </section>

        {/* Edit / Create modal */}
        {showModal && (
          <div className="modal d-block" tabIndex="-1">
            <div className="modal-dialog modal-lg">
              <form className="modal-content" onSubmit={save} autoComplete="off">
              <div className="modal-header">
                <h5 className="modal-title">{editing ? 'Edit Project' : 'New Project'}</h5>
                <button type="button" className="btn-close" onClick={() => setShowModal(false)} />
              </div>
              <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                {error && <div className="alert alert-danger">{error}</div>}
                <style>{`
                  .required::after { content: " *"; color: red; }
                  .form-label { font-weight: 500; font-size: 0.9rem; margin-bottom: 0.25rem; }
                `}</style>

                <div className="row mb-3">
                  <div className="col-md-6">
                    <label className="form-label required">Project Name</label>
                    <input required className="form-control" value={form.project_name} autoComplete="off" onChange={(e) => setForm({ ...form, project_name: e.target.value })} placeholder="e.g. Phoenix Backend" />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label required">Status</label>
                    <SearchableSelect
                      placeholder="Select status..."
                      isClearable={false}
                      options={['Active', 'Archived', 'Completed', 'On Hold'].map((v) => ({ value: v, label: v }))}
                      value={form.status}
                      onChange={(val) => setForm({ ...form, status: val })}
                    />
                  </div>
                </div>

                <div className="mb-3">
                  <label className="form-label required">Description</label>
                  <textarea required className="form-control" rows={3} value={form.description} autoComplete="off" onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="What is this project about?" />
                </div>

                <div className="row mb-3">
                  <div className="col-md-6">
                    <label className="form-label">Client / Customer</label>
                    <input className="form-control" value={form.client_name} autoComplete="off" onChange={(e) => setForm({ ...form, client_name: e.target.value })} placeholder="e.g. ACME Corp" />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Repository URL</label>
                    <input className="form-control" value={form.repository_url} autoComplete="off" onChange={(e) => setForm({ ...form, repository_url: e.target.value })} placeholder="e.g. https://github.com/..." />
                  </div>
                </div>

                <div className="row mb-3">
                  <div className="col-md-6">
                    <label className="form-label">Start Date</label>
                    <input type="date" className="form-control" value={form.start_date} autoComplete="off" onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">End Date</label>
                    <input type="date" className="form-control" value={form.end_date} autoComplete="off" onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
                  </div>
                </div>

                <div className="row mb-3">
                  <div className="col-md-6">
                    <label className="form-label">Budget</label>
                    <input className="form-control" value={form.budget} autoComplete="off" onChange={(e) => setForm({ ...form, budget: e.target.value })} placeholder="e.g. $50,000" />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Tech Stack</label>
                    <input className="form-control" value={form.tech_stack} autoComplete="off" onChange={(e) => setForm({ ...form, tech_stack: e.target.value })} placeholder="e.g. React, Python" />
                  </div>
                </div>

                {/* Assigned Team Select */}
                <div className="row mb-3">
                  <div className="col-12">
                    <label className="form-label">Assigned Team</label>
                    <SearchableSelect
                      placeholder="Select Team to assign to project..."
                      isClearable
                      options={teams.map(t => ({
                        value: t.id,
                        label: `${t.name}${t.team_leader?.full_name ? ` (TL: ${t.team_leader.full_name})` : ''}${t.project_manager?.full_name ? ` | PM: ${t.project_manager.full_name}` : ''}`
                      }))}
                      value={form.team_id || null}
                      onChange={(val) => setForm({ ...form, team_id: val ? parseInt(val) : null })}
                    />
                    {teamsLoading && form.team_id === null && (
                      <div className="text-small text-muted mt-1">Loading teams...</div>
                    )}
                    {selectedTeam && (
                      <div className="p-2.5 mt-2 rounded-3 border bg-light small text-muted d-flex flex-wrap align-items-center gap-3">
                        <div><i className="bi bi-people-fill text-primary me-1" /> Team: <strong className="text-dark">{selectedTeam.name}</strong></div>
                        <div><i className="bi bi-person-badge text-indigo me-1" /> PM: <strong className="text-dark">{selectedTeam.project_manager?.full_name || 'Unassigned'}</strong></div>
                        <div><i className="bi bi-star-fill text-warning me-1" /> TL: <strong className="text-dark">{selectedTeam.team_leader?.full_name || 'Unassigned'}</strong></div>
                        {selectedTeam.member_count > 0 && (
                          <div><i className="bi bi-person-check text-success me-1" /> {selectedTeam.member_count} Member{selectedTeam.member_count > 1 ? 's' : ''}</div>
                        )}
                      </div>
                    )}
                    <div className="form-text text-muted small mt-1">
                      Assigning a team automatically links the project to that team's Project Manager, Team Leader, and Members.
                    </div>
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-light" onClick={() => setShowModal(false)}>Cancel</button>
                {canEditProjects && <button className="btn btn-primary">Save</button>}
              </div>
            </form>
          </div>
        </div>
      )}

      {/* History Modal */}
      {showHistoryModal && (
        <div className="modal d-block" tabIndex="-1">
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Change Log: {historyModalProject?.name}</h5>
                <button type="button" className="btn-close" onClick={closeHistoryModal} />
              </div>
              <div className="modal-body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
                {historyLoading && <div className="text-center py-4">Loading history...</div>}
                {!historyLoading && historyRecords.filter(r => !isIgnoredTimelineField(r.field_name)).length === 0 && (
                  <div className="text-center py-4 text-muted">No change history available for this project.</div>
                )}
                {!historyLoading && historyRecords.filter(r => !isIgnoredTimelineField(r.field_name)).length > 0 && (
                  <div className="table-responsive">
                    <table className="table table-striped table-hover">
                      <thead>
                        <tr>
                          <th>Field Changed</th>
                          <th>Old Value</th>
                          <th>New Value</th>
                          <th>Changed By</th>
                          <th>Changed At</th>
                        </tr>
                      </thead>
                      <tbody>
                        {historyRecords.filter(r => !isIgnoredTimelineField(r.field_name)).map((record) => (
                          <tr key={record.id}>
                            <td>
                              <span className="badge bg-info text-wrap text-capitalize" style={{ maxWidth: '150px' }}>
                                {getFieldLabel(record.field_name)}
                              </span>
                            </td>
                            <td>{record.old_value === null ? '<em>None</em>' : record.old_value}</td>
                            <td>{record.new_value === null ? '<em>None</em>' : record.new_value}</td>
                            <td>{record.user_name || 'System'}</td>
                            <td>{new Date(record.created_at).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline-secondary" onClick={closeHistoryModal}>
                  Close
                </button>
              </div>
            </div>
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