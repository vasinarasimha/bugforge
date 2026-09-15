import { useEffect, useState } from 'react'
import { getProjects } from '../../services/projectService'
import {
  getSprints, getSprintStatuses, createSprint, updateSprint,
  deleteSprint, assignIssueToSprint, removeIssueFromSprint
} from '../../services/sprintService'
import { getIssues } from '../../services/issueService'
import SearchableSelect from '../../components/common/SearchableSelect'

const STATUS_STYLE = {
  Planning:  { bg: 'rgba(99,102,241,0.10)', color: '#6366f1', dot: '#6366f1' },
  Active:    { bg: 'rgba(16,185,129,0.10)', color: '#059669', dot: '#10b981' },
  Completed: { bg: 'rgba(100,116,139,0.10)', color: '#475569', dot: '#94a3b8' },
}
const PRIORITY_COLOR = { Low: '#10b981', Medium: '#f59e0b', High: '#ef4444', Critical: '#dc2626' }

const formatDate = (d) => d ? new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A'
const daysLeft = (end) => {
  if (!end) return null
  const diff = Math.ceil((new Date(end) - Date.now()) / 86400000)
  return diff
}

function IssueChip({ issue, inBacklog, onAssign }) {
  return (
    <div className="sp-issue-chip" style={{ border: '1px solid #e2e8f0', padding: '8px', borderRadius: '6px', background: '#f8fafc', flex: 1 }}>
      <div className="d-flex justify-content-between">
        <strong>{issue.issue_key || 'Issue'}</strong>
        <span style={{ color: PRIORITY_COLOR[issue.priority_name] || '#94a3b8', fontSize: '0.8rem', fontWeight: 600 }}>{issue.priority_name}</span>
      </div>
      <div style={{ fontSize: '0.9rem', marginBottom: '4px' }}>{issue.title}</div>
      <div className="d-flex justify-content-between align-items-center">
        <span className="badge bg-secondary">{issue.status_name}</span>
        {inBacklog && (
          <button className="btn btn-sm btn-outline-success p-0 px-2" onClick={onAssign} title="Assign to Sprint">+</button>
        )}
      </div>
    </div>
  )
}

function SprintCard({ sprint, statuses, onEdit, onDelete, onRemoveIssue, onStatusChange }) {
  const statusDef = statuses.find(s => s.id === sprint.status_id)
  const statusName = statusDef ? statusDef.name : 'Unknown'
  const style = STATUS_STYLE[statusName] || STATUS_STYLE.Planning
  const dl = daysLeft(sprint.end_date)
  
  return (
    <div className="card mb-3 shadow-sm border-0">
      <div className="card-header bg-white d-flex justify-content-between align-items-center py-3">
        <div>
          <h5 className="mb-1">{sprint.name}</h5>
          <span className="badge" style={{ backgroundColor: style.bg, color: style.color, border: `1px solid ${style.color}` }}>
            {statusName}
          </span>
          <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
            {formatDate(sprint.start_date)} - {formatDate(sprint.end_date)}
          </span>
        </div>
        <div>
          <button className="btn btn-sm btn-light me-1" onClick={() => onEdit(sprint)}>Edit</button>
          <button className="btn btn-sm btn-outline-danger" onClick={() => onDelete(sprint.id)}>Delete</button>
        </div>
      </div>
      <div className="card-body bg-light">
        {sprint.goal && <p className="text-muted mb-3"><strong>Goal:</strong> {sprint.goal}</p>}
        <h6>Issues ({sprint.issues?.length || 0})</h6>
        <div className="d-flex flex-column gap-2">
          {sprint.issues?.length ? sprint.issues.map(i => (
            <div key={i.id} className="d-flex align-items-center gap-2">
              <IssueChip issue={i} />
              <button className="btn btn-sm btn-danger px-2" onClick={() => onRemoveIssue(sprint.id, i.id)}>x</button>
            </div>
          )) : <p className="text-muted" style={{ fontSize: '0.85rem' }}>No issues in this sprint.</p>}
        </div>
      </div>
    </div>
  )
}

function SprintFormModal({ onClose, onSave, statuses, projects, initial }) {
  console.log(statuses)
  const empty = { name: '', goal: '', status_id: '', start_date: '', end_date: '', project_id: '' }
  const [form, setForm] = useState(initial ? {
    name: initial.name,
    goal: initial.goal || '',
    status_id: initial.status_id,
    start_date: initial.start_date ? initial.start_date.split('T')[0] : '',
    end_date: initial.end_date ? initial.end_date.split('T')[0] : '',
    project_id: initial.project_id,
  } : empty)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true); setError('')
    try {
      const payload = {
        ...form,
        status_id: Number(form.status_id),
        project_id: Number(form.project_id),
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        goal: form.goal || null,
      }
      await onSave(payload)
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save sprint.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1050, display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="card shadow" style={{ width: '500px', maxWidth: '90%' }}>
        <div className="card-header d-flex justify-content-between align-items-center bg-white py-3">
          <h5 className="mb-0">{initial ? 'Edit Sprint' : 'New Sprint'}</h5>
          <button type="button" className="btn-close" onClick={onClose}></button>
        </div>
        <div className="card-body">
          {error && <div className="alert alert-danger p-2">{error}</div>}
          <form onSubmit={submit} autoComplete="off">
            <div className="mb-3">
              <label className="form-label fw-bold">Sprint Name</label>
              <input required className="form-control" value={form.name} autoComplete="off" onChange={e => set('name', e.target.value)} placeholder="e.g. Sprint 1" />
            </div>
            {!initial && (
              <div className="mb-3">
                <label className="form-label fw-bold">Project</label>
                <SearchableSelect
                  placeholder="Select Project"
                  options={projects.map(p => ({ value: p.id, label: p.name }))}
                  value={form.project_id}
                  isClearable={false}
                  onChange={val => set('project_id', val)}
                />
              </div>
            )}
            <div className="mb-3">
              <label className="form-label fw-bold">Status</label>
              <SearchableSelect
                placeholder="Select Status"
                options={statuses.map(s => ({ value: s.id, label: s.name }))}
                value={form.status_id}
                isClearable={false}
                onChange={val => set('status_id', val)}
              />
            </div>
            <div className="row mb-3">
              <div className="col">
                <label className="form-label fw-bold">Start Date</label>
                <input type="date" className="form-control" value={form.start_date} autoComplete="off" onChange={e => set('start_date', e.target.value)} />
              </div>
              <div className="col">
                <label className="form-label fw-bold">End Date</label>
                <input type="date" className="form-control" value={form.end_date} autoComplete="off" onChange={e => set('end_date', e.target.value)} />
              </div>
            </div>
            <div className="mb-4">
              <label className="form-label fw-bold">Goal</label>
              <textarea className="form-control" value={form.goal} autoComplete="off" onChange={e => set('goal', e.target.value)} placeholder="Optional goal..." rows="2" />
            </div>
            <div className="d-flex justify-content-end gap-2">
              <button type="button" className="btn btn-light border" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save Sprint'}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default function SprintPlanningPage() {
  const [allProjects, setAllProjects] = useState([])
  const [projectFilter, setProjectFilter] = useState('')
  const [sprints, setSprints] = useState([])
  const [statuses, setStatuses] = useState([])
  const [allIssues, setAllIssues] = useState([])
  const [backlogSearch, setBacklogSearch] = useState('')
  const [activeSprintId, setActiveSprintId] = useState('')
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editTarget, setEditTarget] = useState(null)

  useEffect(() => {
    fetchData()
  }, [projectFilter])

  const fetchData = async () => {
    try {
      const [projRes, statRes, sprRes, issRes] = await Promise.all([
        getProjects(),
        getSprintStatuses(),
        getSprints(projectFilter || null),
        getIssues(projectFilter || null)
      ])
      setAllProjects(projRes.data || [])
      setStatuses(statRes.data || [])
      setSprints(sprRes.data || [])
      setAllIssues(issRes.data || [])
      if (sprRes.data?.length) setActiveSprintId(sprRes.data[0].id)
    } catch (e) {
      setError('Failed to load sprint data.')
    }
  }

  const handleSave = async (payload) => {
    if (editTarget) {
      await updateSprint(editTarget.id, payload)
    } else {
      await createSprint(payload)
    }
    fetchData()
  }

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this sprint?')) {
      await deleteSprint(id)
      fetchData()
    }
  }

  const handleAssign = async (sprint, issue) => {
    if (!sprint || !issue) return
    try {
      await assignIssueToSprint(sprint.id, issue.id)
      fetchData()
    } catch (e) {
      setError('Failed to assign issue')
    }
  }

  const handleRemove = async (sprintId, issueId) => {
    try {
      await removeIssueFromSprint(sprintId, issueId)
      fetchData()
    } catch (e) {
      setError('Failed to remove issue')
    }
  }

  const handleStatusChange = () => {}

  const assignedIssueIds = new Set(sprints.flatMap(s => (s.issues || []).map(i => i.id)))
  const backlog = allIssues
    .filter(i => !assignedIssueIds.has(i.id))
    .filter(i => !projectFilter || i.project_id === Number(projectFilter))
    .filter(i => !backlogSearch || i.title.toLowerCase().includes(backlogSearch.toLowerCase()))

  return (
    <div style={{ padding: '24px' }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="mb-1">Sprint Planning</h2>
          <p className="text-muted mb-0">Plan and manage your project iterations.</p>
        </div>
        <div className="d-flex gap-3 align-items-center">
          <div style={{ minWidth: '220px' }}>
            <SearchableSelect
              placeholder="All Projects"
              isClearable
              options={allProjects.map(p => ({ value: p.id, label: p.name }))}
              value={projectFilter ? Number(projectFilter) : null}
              onChange={val => setProjectFilter(val ? String(val) : '')}
            />
          </div>
          <button className="btn btn-primary text-nowrap" onClick={() => { setEditTarget(null); setShowModal(true) }}>
            <i className="bi bi-plus-lg me-1"></i> New Sprint
          </button>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="row">
        <div className="col-md-7 col-lg-8">
          <h5 className="mb-3">Sprints <span className="badge bg-secondary rounded-pill ms-2">{sprints.length}</span></h5>
          {sprints.length === 0 ? (
            <div className="text-center p-5 bg-light rounded border border-dashed">
              <h5 className="text-muted">No sprints found</h5>
              <p className="text-muted mb-0">Create a sprint to start planning.</p>
            </div>
          ) : (
            sprints.map(s => (
              <SprintCard
                key={s.id}
                sprint={s}
                statuses={statuses}
                onEdit={(sprint) => { setEditTarget(sprint); setShowModal(true) }}
                onDelete={handleDelete}
                onRemoveIssue={handleRemove}
                onStatusChange={handleStatusChange}
              />
            ))
          )}
        </div>
        <div className="col-md-5 col-lg-4">
          <div className="card border-0 shadow-sm">
            <div className="card-header bg-white py-3 border-bottom-0">
              <h5 className="mb-0 d-flex justify-content-between align-items-center">
                Backlog 
                <span className="badge bg-secondary rounded-pill">{backlog.length}</span>
              </h5>
            </div>
            <div className="card-body pt-0">
              <input 
                type="text" 
                className="form-control mb-3 bg-light" 
                placeholder="Search backlog..." 
                value={backlogSearch} 
                autoComplete="off"
                onChange={e => setBacklogSearch(e.target.value)} 
              />
              {sprints.length > 0 && (
                <div className="mb-3 p-2 bg-light rounded border">
                  <label className="form-label" style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>Assign selected to:</label>
                  <SearchableSelect
                    placeholder="Select Sprint..."
                    isClearable={false}
                    options={sprints.map(s => ({ value: s.id, label: s.name }))}
                    value={activeSprintId}
                    onChange={val => setActiveSprintId(val ? Number(val) : null)}
                  />
                </div>
              )}
              <div style={{ maxHeight: '600px', overflowY: 'auto' }} className="pe-2 custom-scrollbar">
                {backlog.length === 0 ? (
                  <p className="text-muted text-center py-4">No issues in backlog.</p>
                ) : (
                  backlog.map(i => (
                    <div key={i.id} className="d-flex align-items-center gap-2 mb-2">
                      <IssueChip issue={i} />
                      {sprints.length > 0 && (
                        <button 
                          className="btn btn-outline-primary px-2 shadow-sm" 
                          onClick={() => handleAssign(sprints.find(s => s.id === activeSprintId) || sprints[0], i)}
                          disabled={!activeSprintId && sprints.length === 0}
                          title="Assign to selected sprint"
                        >
                          <i className="bi bi-arrow-right"></i>
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {showModal && (
        <SprintFormModal
          initial={editTarget}
          statuses={statuses}
          projects={allProjects}
          onClose={() => { setShowModal(false); setEditTarget(null) }}
          onSave={handleSave}
        />
      )}
    </div>
  )
}
