import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import IssueTable from '../../components/IssueTable/IssueTable'
import Modal from '../../components/Modal/Modal'
import IssueTimeline from '../../components/ActivityTimeline/IssueTimeline'
import { createIssue, deleteIssue, getIssues, updateIssue, uploadFile, getStatuses, getPriorities, getSeverities, getIssueAttachments, addIssueAttachment, deleteIssueAttachment, getCategories, getModules } from '../../services/issueService'
import { getSprints } from '../../services/sprintService'
import { getProjects } from '../../services/projectService'
import { formatIssue, getResolutionAssistance } from '../../services/aiService'
import { useAuth } from '../../hooks/useAuth'
import { getUsers } from '../../services/authService'


const ISSUE_TYPES = [
  { value: 'Bug', icon: '🐛', color: '#ef4444', bg: 'rgba(239,68,68,0.09)' },
  { value: 'Task', icon: '✅', color: '#3b82f6', bg: 'rgba(59,130,246,0.09)' },
  { value: 'Feature', icon: '✨', color: '#8b5cf6', bg: 'rgba(139,92,246,0.09)' }
]


function FieldGroup({ label, required, children, hint }) {
  return (
    <div className="if-field-group">
      <label className={`if-label${required ? ' if-required' : ''}`}>{label}</label>
      {children}
      {hint && <p className="if-hint">{hint}</p>}
    </div>
  )
}


function SectionCard({ icon, title, children }) {
  return (
    <div className="if-section">
      <div className="if-section-header">
        <span className="if-section-icon">{icon}</span>
        <span className="if-section-title">{title}</span>
      </div>
      <div className="if-section-body">{children}</div>
    </div>
  )
}


export default function ReportedIssuesPage() {
  const { user } = useAuth()
  const location = useLocation()
  const userRole = user?.role || user?.roles?.[0]?.name || ''
  const userRoles = user?.roles?.map(r => r.name) || [userRole]
  const canDeleteIssue = userRole === 'Admin' || userRole === 'QA' || userRole === 'Project Manager'
  const BACKEND_TO_FRONTEND_ISSUE_TYPE = {
    Defect: 'Bug',
    Task: 'Task',
    Feature: 'Feature'
  }
  const FRONTEND_TO_BACKEND_ISSUE_TYPE = {
    Bug: 'Defect',
    Task: 'Task',
    Feature: 'Feature'
  }
  const empty = { title: '', description: '', project_id: '', priority_id: '', severity_id: '', category_id: '', module_id: '', status_id: '', assigned_to: null, issue_type: 'Bug', environment: '', browser: '', steps_to_reproduce: '', expected_behavior: '', actual_behavior: '', attachment_path: '', sprint_id: '' }

  const [issues, setIssues] = useState([])
  const [statuses, setStatuses] = useState([])
  const [priorities, setPriorities] = useState([])
  const [severities, setSeverities] = useState([])
  const [categories, setCategories] = useState([])
  const [modules, setModules] = useState([])
  const [form, setForm] = useState(empty)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [editing, setEditing] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [query, setQuery] = useState('')
  const [allProjects, setAllProjects] = useState([])
  const [allUsers, setAllUsers] = useState([])
  const [projectSprints, setProjectSprints] = useState([])
  const [status, setStatus] = useState('')
  const [project, setProject] = useState('')
  const [error, setError] = useState('')
  const [formatting, setFormatting] = useState(false)
  const [attachments, setAttachments] = useState([])
  const [attachUploading, setAttachUploading] = useState(false)
  // Semantic search state
  const [similarDefects, setSimilarDefects] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchTimeout, setSearchTimeout] = useState(null)

  // Resolution assistance state
  const [resolutionAssistanceLoading, setResolutionAssistanceLoading] = useState(false)
  const [resolutionAssistanceData, setResolutionAssistanceData] = useState(null)
  const [resolutionAssistanceError, setResolutionAssistanceError] = useState('')

  
  const load = async () => {
    const [issueResult, statusResult, priorityResult, severityResult, categoryResult, moduleResult, projResult, userResult] = await Promise.all([
      getIssues(), getStatuses(), getPriorities(), getSeverities(), getCategories(), getModules(), getProjects('', 1000, 0), getUsers('', 1000, 0)
    ])
    setIssues(issueResult.data)
    setStatuses(statusResult.data)
    setPriorities(priorityResult.data)
    setSeverities(severityResult.data)
    setCategories(categoryResult.data)
    setModules(moduleResult.data)
    setAllProjects(projResult.data)
    setAllUsers(userResult.data?.data || [])
  }

  useEffect(() => { load().catch(() => setError('Unable to load issues.')) }, [])

  useEffect(() => {
    if (form.project_id) {
      getSprints(form.project_id).then(r => setProjectSprints(r.data)).catch(() => setProjectSprints([]))
    } else {
      setProjectSprints([])
    }
  }, [form.project_id])

  useEffect(() => {
    if (location.state?.editIssue && statuses.length) {
      open(location.state.editIssue)
      window.history.replaceState({}, document.title)
    } else if (location.state?.openNewIssue && statuses.length) {
      open()
      window.history.replaceState({}, document.title)
    }
  }, [location.state, statuses.length])

  // Debounced semantic search for similar defects
  useEffect(() => {
    // Clear existing timeout
    if (searchTimeout) {
      clearTimeout(searchTimeout)
    }

    // Set new timeout
    const timeout = setTimeout(async () => {
      // Only search if we have both title and description with minimum length
      if (form.title?.trim() && form.description?.trim() &&
          form.title.trim().length > 0 && form.description.trim().length >= 20) {
        setSearchLoading(true)
        try {
          const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/issues/search`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              title: form.title,
              description: form.description
            })
          })

          if (!response.ok) {
            throw new Error('Failed to search for similar defects')
          }

          const data = await response.json()
          // Filter for defects with similarity > 0.8 (cosine similarity)
          // Backend returns array of objects with {issue, similarity}
          const similar = data
            .map(item => item.similarity > 0.8 ? item : null)
            .filter(item => item !== null)
          setSimilarDefects(similar)
        } catch (err) {
          console.error('Error searching for similar defects:', err)
          setSimilarDefects([])
        } finally {
          setSearchLoading(false)
        }
      } else {
        setSimilarDefects([])
        setSearchLoading(false)
      }
    }, 1000)

    setSearchTimeout(timeout)

    // Cleanup function
    return () => {
      if (searchTimeout) {
        clearTimeout(searchTimeout)
      }
    }
  }, [form.title, form.description])

  const open = (issue = null) => {
    // Reset resolution assistance when opening a new issue or switching issues
    setResolutionAssistanceLoading(false)
    setResolutionAssistanceData(null)
    setResolutionAssistanceError('')
    setEditing(issue)
    setForm(issue
      ? {
          title: issue.title,
          description: issue.description,
          project_id: issue.project_id,
          priority_id: issue.priority_id,
          severity_id: issue.severity_id,
          category_id: issue.category_id,
          module_id: issue.module_id,
          status_id: issue.status_id,
          assigned_to: issue.assigned_to,
          issue_type: issue.issue_type ? BACKEND_TO_FRONTEND_ISSUE_TYPE[issue.issue_type] : 'Bug',
          environment: issue.environment || '',
          browser: issue.browser || '',
          steps_to_reproduce: issue.steps_to_reproduce || '',
          expected_behavior: issue.expected_behavior || '',
          actual_behavior: issue.actual_behavior || '',
          attachment_path: issue.attachment_path || '',
          sprint_id: issue.sprint_id || ''
        }
      : empty
    )
    setFile(null)
    setAttachments([])
    setError('')
    setShowForm(true)
    if (issue) {
      getIssueAttachments(issue.id).then(r => setAttachments(r.data)).catch(() => {})
    }
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleAIFormat = async () => {
    if (!form.title && !form.description) return
    setFormatting(true)
      try {
        const { data } = await formatIssue({ title: form.title, description: form.description })
        const matchingPriority = priorities.find(p => p.name === data.priority)
        const matchingSeverity = severities.find(s => s.name === data.severity)
        setForm({
          ...form,
          title: data.title || form.title,
          description: data.description || form.description,
          priority_id: matchingPriority ? matchingPriority.id : form.priority_id,
          severity_id: matchingSeverity ? matchingSeverity.id : form.severity_id,
          steps_to_reproduce: data.steps_to_reproduce !== 'N/A' ? data.steps_to_reproduce : form.steps_to_reproduce,
          expected_behavior: data.expected_behavior !== 'N/A' ? data.expected_behavior : form.expected_behavior,
          actual_behavior: data.actual_behavior !== 'N/A' ? data.actual_behavior : form.actual_behavior
        })
      } catch (e) {
      setError("AI formatting failed.")
    } finally {
      setFormatting(false)
    }
  }

  const handleGetResolutionAssistance = async () => {
    if (!editing) return
    setResolutionAssistanceLoading(true)
    setResolutionAssistanceError('')
    setResolutionAssistanceData(null)
    try {
      const { data } = await getResolutionAssistance(editing.id)
      setResolutionAssistanceData(data)
    } catch (e) {
      setResolutionAssistanceError(e.response?.data?.detail || 'Failed to get resolution assistance.')
    } finally {
      setResolutionAssistanceLoading(false)
    }
  }

  
  const save = async (event) => {
    event.preventDefault()
    setUploading(true)
    setError('')
    try {
      let currentAttachment = form.attachment_path
      if (file) {
        const uploadRes = await uploadFile(file)
        currentAttachment = uploadRes.data.path
      }
      // Safely get default values with fallbacks
      const defaultProjectId = allProjects[0]?.id ?? 1
      const defaultStatusId = (statuses.find(s => s.name === 'Open')?.id || statuses[0]?.id) ?? 1
      const defaultPriorityId = (priorities.find(p => p.name === 'Medium')?.id || priorities[0]?.id) ?? 1
      const defaultSeverityId = (severities.find(s => s.name === 'Medium')?.id || severities[0]?.id) ?? 1
      const defaultModuleId = modules[0]?.id ?? 1
      const defaultCategoryId = categories[0]?.id ?? 1
      // Convert frontend issue_type to backend issue_type
      const backendIssueType = FRONTEND_TO_BACKEND_ISSUE_TYPE[form.issue_type] || 'Defect'
      const payload = {
        ...form,
        issue_type: backendIssueType,
        project_id: form.project_id ? Number(form.project_id) : defaultProjectId,
        assigned_to: form.assigned_to ? Number(form.assigned_to) : null,
        attachment_path: currentAttachment,
        status_id: form.status_id ? Number(form.status_id) : defaultStatusId,
        priority_id: form.priority_id ? Number(form.priority_id) : defaultPriorityId,
        severity_id: form.severity_id ? Number(form.severity_id) : defaultSeverityId,
        module_id: form.module_id ? Number(form.module_id) : defaultModuleId,
        category_id: form.category_id ? Number(form.category_id) : defaultCategoryId,
        sprint_id: form.sprint_id ? Number(form.sprint_id) : null,
      }
      editing ? await updateIssue(editing.id, payload) : await createIssue(payload)
      setShowForm(false)
      await load()
    } catch (e) {
      setError(e.response?.data?.detail || 'Unable to save issue.')
    } finally {
      setUploading(false)
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
    (!status || String(issue.status_id) === String(status)) &&
    (!project || String(issue.project_id) === project) &&
    (`${issue.id} ${issue.title}`.toLowerCase().includes(query.toLowerCase()))
  )

  const isFormClosedAndReadOnly = editing && (statuses.find(s => String(s.id) === String(editing.status_id))?.name === 'Closed') && !userRoles.includes('Admin')
  const canSubmit = form.title?.trim() && form.description?.trim() && form.description?.trim().length >= 20 && !uploading && !isFormClosedAndReadOnly

  return (
    <>
      <style>{`
        /* ── Issue Form Styles ── */
        .if-page { display: flex; flex-direction: column; gap: 0; }

        /* Top bar */
        .if-topbar {
          display: flex; align-items: center; gap: 16px;
          padding: 20px 28px; background: #fff;
          border-bottom: 1px solid rgba(15,23,42,0.08);
          border-radius: 20px 20px 0 0;
        }
        .if-back-btn {
          display: inline-flex; align-items: center; gap: 8px;
          padding: 8px 16px; border-radius: 10px; border: 1.5px solid rgba(15,23,42,0.12);
          background: #fff; color: #475569; font-size: 0.85rem; font-weight: 600;
          cursor: pointer; transition: all .2s;
        }
        .if-back-btn:hover { background: #f8fafc; border-color: #cbd5e1; color: #1e293b; }
        .if-topbar-title { font-weight: 700; font-size: 1.15rem; color: #0f172a; }
        .if-topbar-sub { font-size: 0.8rem; color: #94a3b8; margin-top: 1px; }
        .if-id-badge {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 4px 12px; border-radius: 8px;
          background: rgba(59,130,246,0.08); color: #3b82f6;
          font-size: 0.78rem; font-weight: 700; letter-spacing: .02em;
        }
        .if-ai-btn {
          margin-left: auto; display: inline-flex; align-items: center; gap: 8px;
          padding: 8px 18px; border-radius: 10px; border: none; cursor: pointer;
          font-size: 0.82rem; font-weight: 600;
          background: linear-gradient(135deg, #f59e0b, #f97316);
          color: #fff; transition: opacity .2s, transform .15s, box-shadow .2s;
          box-shadow: 0 2px 12px rgba(245,158,11,0.3);
        }
        .if-ai-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); box-shadow: 0 4px 20px rgba(245,158,11,0.4); }
        .if-ai-btn:disabled { opacity: 0.45; cursor: not-allowed; }

        /* Assistant button */
        .if-assistant-btn {
          margin-left: 12px; display: inline-flex; align-items: center; gap: 8px;
          padding: 8px 18px; border-radius: 10px; border: none; cursor: pointer;
          font-size: 0.82rem; font-weight: 600;
          background: linear-gradient(135deg, #6366f1, #8b5cf6);
          color: #fff; transition: opacity .2s, transform .15s, box-shadow .2s;
          box-shadow: 0 2px 12px rgba(99,102,241,0.3);
        }
        .if-assistant-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); box-shadow: 0 4px 20px rgba(99,102,241,0.4); }
        .if-assistant-btn:disabled { opacity: 0.45; cursor: not-allowed; }

        /* Layout */
        .if-layout {
          display: grid;
          grid-template-columns: 1fr 420px;
          gap: 0;
          min-height: 0;
        }

        /* Left: form scroll area */
        .if-left {
          padding: 32px 36px;
          border-right: 1px solid rgba(15,23,42,0.07);
          overflow-y: auto;
          display: flex; flex-direction: column; gap: 28px;
        }

        /* Right: timeline */
        .if-right {
          background: #fafbfc;
          padding: 28px 24px;
          display: flex; flex-direction: column;
          overflow-y: auto;
          max-height: calc(100vh - 220px);
        }

        /* Title input hero */
        .if-title-wrap { margin-bottom: 4px; }
        .if-title-input {
          width: 100%; border: none; border-bottom: 2px solid rgba(15,23,42,0.1);
          background: transparent; font-size: 1.45rem; font-weight: 700;
          color: #0f172a; padding: 6px 0 10px; outline: none;
          transition: border-color .2s;
          font-family: 'Space Grotesk', 'Inter', sans-serif;
        }
        .if-title-input:focus { border-bottom-color: #3b82f6; }
        .if-title-input::placeholder { color: #cbd5e1; font-weight: 500; }

        /* Sections */
        .if-section {
          background: #fff;
          border: 1px solid rgba(15,23,42,0.07);
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(15,23,42,0.04);
        }
        .if-section-header {
          display: flex; align-items: center; gap: 10px;
          padding: 14px 20px;
          background: #f8fafc;
          border-bottom: 1px solid rgba(15,23,42,0.06);
        }
        .if-section-icon { font-size: 1rem; }
        .if-section-title { font-weight: 700; font-size: 0.82rem; letter-spacing: .04em; text-transform: uppercase; color: #64748b; }
        .if-section-body { padding: 22px 22px; display: flex; flex-direction: column; gap: 20px; }

        /* Grid inside section body */
        .if-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .if-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }

        /* Field */
        .if-field-group { display: flex; flex-direction: column; gap: 6px; }
        .if-label {
          font-size: 0.78rem; font-weight: 700; letter-spacing: .04em;
          text-transform: uppercase; color: #64748b;
        }
        .if-required::after { content: ' *'; color: #ef4444; }
        .if-hint { font-size: 0.75rem; color: #94a3b8; margin: 0; margin-top: 2px; }

        /* Inputs */
        .if-input, .if-select, .if-textarea {
          width: 100%; padding: 10px 14px; border-radius: 10px;
          border: 1.5px solid rgba(15,23,42,0.10);
          background: #fff; color: #0f172a;
          font-size: 0.9rem; line-height: 1.5;
          outline: none; transition: border-color .2s, box-shadow .2s;
          appearance: none; -webkit-appearance: none;
        }
        .if-input:focus, .if-select:focus, .if-textarea:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59,130,246,0.10);
        }
        .if-input::placeholder, .if-textarea::placeholder { color: #cbd5e1; }

        /* Select arrow */
        .if-select {
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='none' viewBox='0 0 24 24'%3E%3Cpath stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
          background-repeat: no-repeat;
          background-position: right 12px center;
          padding-right: 38px;
          cursor: pointer;
        }

        /* Textarea */
        .if-textarea { resize: vertical; min-height: 90px; }

        /* Type chips */
        .if-type-chips { display: flex; gap: 10px; flex-wrap: wrap; }
        .if-type-chip {
          display: inline-flex; align-items: center; gap: 8px;
          padding: 8px 16px; border-radius: 10px; cursor: pointer;
          border: 2px solid transparent; transition: all .2s;
          font-size: 0.875rem; font-weight: 600; background: #f8fafc;
          color: #475569;
        }
        .if-type-chip:hover { transform: translateY(-1px); }
        .if-type-chip.active { border-color: currentColor; }

        /* File upload area */
        .if-file-drop {
          border: 2px dashed rgba(15,23,42,0.12); border-radius: 12px;
          padding: 24px; text-align: center; cursor: pointer;
          transition: all .2s; background: #fafbfc;
          position: relative;
        }
        .if-file-drop:hover { border-color: #3b82f6; background: rgba(59,130,246,0.03); }
        .if-file-drop input[type=file] {
          position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
        }
        .if-file-icon { font-size: 1.6rem; margin-bottom: 6px; }
        .if-file-label { font-size: 0.85rem; font-weight: 600; color: #3b82f6; }
        .if-file-sub { font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }
        .if-file-chosen { font-size: 0.82rem; color: #10b981; font-weight: 600; margin-top: 6px; }

        /* Footer bar */
        .if-footer {
          display: flex; align-items: center; justify-content: flex-end; gap: 12px;
          padding: 18px 28px; background: #fff;
          border-top: 1px solid rgba(15,23,42,0.08);
          border-radius: 0 0 20px 20px;
        }
        .if-back-btn-icon {
          display: inline-flex; align-items: center; justify-content: center;
          width: 42px; height: 42px; border-radius: 50%;
          border: none;
          background: rgba(15,23,42,0.06);
          color: #475569;
          cursor: pointer; transition: all .2s ease;
        }
        .if-back-btn-icon:hover {
          background: rgba(15,23,42,0.12);
          color: #0f172a;
          transform: translateX(-3px);
        }
        .if-cancel-btn {
          padding: 10px 22px; border-radius: 10px;
          border: 1.5px solid rgba(15,23,42,0.12);
          background: #fff; color: #64748b; font-size: 0.88rem; font-weight: 600;
          cursor: pointer; transition: all .2s;
        }
        .if-cancel-btn:hover { background: #f8fafc; border-color: #cbd5e1; color: #1e293b; }
        .if-save-btn {
          padding: 10px 28px; border-radius: 10px; border: none; cursor: pointer;
          font-size: 0.88rem; font-weight: 700; letter-spacing: .01em;
          background: linear-gradient(135deg, #3b82f6, #6366f1);
          color: #fff; transition: all .2s;
          box-shadow: 0 4px 14px rgba(59,130,246,0.35);
          display: inline-flex; align-items: center; gap: 8px;
        }
        .if-save-btn:hover:not(:disabled) { translate: translateY(-1px); box-shadow: 0 6px 20px rgba(59,130,246,0.45); }
        .if-save-btn:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }
        .if-progress { font-size: 0.78rem; color: #94a3b8; margin-right: auto; }

        /* Error */
        .if-error {
          display: flex; align-items: center; gap: 10px;
          padding: 12px 16px; border-radius: 10px;
          background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2);
          color: #dc2626; font-size: 0.875rem; font-weight: 500;
          margin: 0 28px 0;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        /* AI Resolution Assistance Card */
        .if-resolution-assistant-card {
          background: #fff;
          border: 1px solid rgba(15,23,42,0.07);
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(15,23,42,0.04);
          margin-bottom: 24px;
        }
        .if-resolution-assistant-header {
          display: flex; align-items: center; gap: 10px;
          padding: 14px 20px;
          background: #f8fafc;
          border-bottom: 1px solid rgba(15,23,42,0.06);
        }
        .if-resolution-assistant-icon { font-size: 1rem; }
        .if-resolution-assistant-title { font-weight: 700; font-size: 0.82rem; letter-spacing: .04em; text-transform: uppercase; color: #64748b; }
        .if-resolution-assistant-body { padding: 22px 22px; display: flex; flex-direction: column; gap: 20px; }
        .if-resolution-assistant-section h4 {
          font-weight: 700; font-size: 0.9rem; color: #0f172a; margin-bottom: 8px;
        }
        .if-resolution-assistant-section ul {
          margin: 0; padding-left: 20px;
        }
        .if-resolution-assistant-section ul li {
          color: #475569; line-height: 1.6;
        }
        .if-resolution-assistant-section p {
          color: #475569; line-height: 1.6;
        }
        .if-spinner {
          display: flex; align-items: center; justify-content: center;
        }
        .if-spinner svg { width: 20px; height: 20px; }

        /* Responsive */
        @media (max-width: 1100px) {
          .if-layout { grid-template-columns: 1fr; }
          .if-right { border-top: 1px solid rgba(15,23,42,0.07); max-height: 500px; border-radius: 0 0 20px 20px; }
          .if-grid-3 { grid-template-columns: 1fr 1fr; }
          .if-resolution-assistant-card { margin-bottom: 16px !important; }
        }
        @media (max-width: 640px) {
          .if-grid-2, .if-grid-3 { grid-template-columns: 1fr; }
          .if-left { padding: 20px; }
          .if-resolution-assistant-card { margin-bottom: 12px !important; }
          .if-right { max-height: 400px; }
        }
        /* Ensure AI Resolution Assistance section has proper spacing */
        .if-resolution-assistant-card {
          margin-bottom: 24px;
          min-height: 0; /* Prevent flex-shrink issues */
        }
        /* Prevent IssueTimeline from overriding AI assistance content */
        .if-right {
          display: flex;
          flex-direction: column;
        }
        .if-resolution-assistant-card {
          flex-shrink: 0; /* Prevent the card from shrinking */
        }
      `}</style>

      <section className="page-heading" style={{ animation: 'fadeSlideUp .5s ease both', display: 'flex', alignItems: 'flex-start', gap: '24px' }}>
        {showForm && (
          <button className="if-back-btn-icon" style={{ marginTop: '20px', flexShrink: 0 }} onClick={() => setShowForm(false)} title="Back to Issues">
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
          </button>
        )}
        <div style={{ flex: 1 }}>
          {/* <p className="eyebrow">Issue Management</p> */}
          <h2>{showForm ? (editing ? 'Edit Issue' : 'New Issue') : 'Reported Issues'}</h2>
          <p>{showForm ? 'Fill in the details below to document the issue.' : 'Review and follow up on the bugs you have reported.'}</p>
        </div>
        {!showForm && (
          <button className="btn btn-primary" style={{ flexShrink: 0 }} onClick={() => open()}>
            <i className="bi bi-plus-lg" /> New Issue
          </button>
        )}
      </section>

      {/* ── LIST VIEW ── */}
      {!showForm && (
        <section className="panel-card" style={{ animation: 'fadeSlideUp .5s ease .1s both' }}>
          <div className="issue-filters">
            <div className="search-input" style={{ position: 'relative' }}>
              <span className="input-group-text" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none', zIndex: 1 }}>
                <i className="bi bi-search" />
              </span>
              <input className="form-control" style={{ paddingLeft: '60px' }} placeholder="Search by ID or title…" value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <select className="if-select" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All statuses</option>
              {statuses.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <div style={{ width: '220px' }}>
              <select className="if-select"
                value={project}
                onChange={(e) => setProject(e.target.value)}
                placeholder="All projects"
              >
                <option value="">All projects</option>
                {allProjects.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {error && <div className="alert alert-danger">{error}</div>}
          <IssueTable issues={filtered} onEdit={open} onDelete={remove} canDelete={canDeleteIssue} />
        </section>
      )}

      {/* ── FORM VIEW ── */}
      {showForm && (
        <div className="panel-card" style={{ padding: 0, overflow: 'hidden', animation: 'fadeSlideUp .4s ease both' }}>

          {/* Top bar */}
          <div className="if-topbar">
            {editing && <span className="if-id-badge"><i className="bi bi-hash" />Issue #{editing.id}</span>}
            <div>
              {/* <div className="if-topbar-title">{editing ? editing.title : 'Create New Issue'}</div> */}
              <div className="if-topbar-sub">{editing ? 'Edit issue details and activity below' : 'Document a new defect, task, or feature request'}</div>
            </div>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <button type="button" className="if-ai-btn" onClick={handleAIFormat}
                disabled={formatting || !form.title?.trim() || !form.description?.trim() || form.description?.trim().length < 20}>
                {formatting ? (
                  <>
                    <svg style={{ animation: 'spin 1s linear infinite', width: 14, height: 14 }} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                    </svg>
                    AI Working…
                  </>
                ) : <>✨ AI Clean & Triage</>}
              </button>
                            {/* AI Resolution Assistance Button - only for Developer/Project Manager and when editing an issue */}
              {editing && (userRoles.includes('Developer') || userRoles.includes('Project Manager')) && (
                <button type="button" className="if-assistant-btn" onClick={handleGetResolutionAssistance}
                  disabled={resolutionAssistanceLoading}>
                  {resolutionAssistanceLoading ? (
                    <>
                      <svg style={{ animation: 'spin 1s linear infinite', width: 14, height: 14 }} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                        <path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                      </svg>
                      Getting assistance…
                    </>
                  ) : <>🤖 AI Resolution Assistance</>}
                </button>
              )}
            </div>
          </div>

          {/* Similar Defect Warning Banner */}
          {similarDefects.length > 0 && (
            <div className="alert alert-warning" style={{ margin: '16px 0', padding: '12px 16px', borderRadius: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm0-14a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0 6a1 1 0 1 0 0 2 1 1 0 0 0 0-2z" />
                </svg>
                <div>
                  <strong>⚠️ Similar Defect Found:</strong>
                  {similarDefects.map((defectItem, index) => (
                    <div key={index} style={{ marginLeft: '8px', fontSize: '0.875rem' }}>
                      <a href={`/${defectItem.issue.id}`} target="_blank" rel="noreferrer" style={{ color: '#dc2626', textDecoration: 'underline' }}>
                        DEF-{defectItem.issue.issue_key}
                      </a>
                      (Similarity: {Math.round(defectItem.similarity * 100)}%)
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Error banner */}
          {isFormClosedAndReadOnly && (
            <div className="alert alert-secondary m-4">This issue is Closed and cannot be modified.</div>
          )}
          {error && (
            <div className="if-error" style={{ marginTop: 16 }}>
              <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12" y2="16" />
              </svg>
              {error}
            </div>
          )}

          {/* Body: left form + right timeline */}
          <div className="if-layout">

            {/* ── LEFT: Form ── */}
            <div className="if-left">
              <form id="issue-form" onSubmit={save}>

                {/* Title */}
                <div className="if-title-wrap">
                  <label className="if-label if-required" style={{ marginBottom: 8, display: 'block' }}>Issue Title</label>
                  <input
                    required
                    className="if-title-input"
                    placeholder="Describe the issue in a single clear sentence…"
                    value={form.title}
                    onChange={e => setForm({ ...form, title: e.target.value })}
                  />
                </div>

                {/* Classification */}
                <SectionCard icon="🏷️" title="Classification">
                  <div className="if-grid-2">
                    <FieldGroup label="Project" required>
                      <select className="if-select"
                        required
                        value={form.project_id || ''}
                        onChange={(e) => setForm({ ...form, project_id: e.target.value })}
                        placeholder="Select a project..."
                      >
                        <option value="">Select a project...</option>
                        {allProjects.map(p => (
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
                        ))}
                      </select>
                    </FieldGroup>
                    <FieldGroup label="Status" required>
                      {(() => {
                        const canChangeStatus = userRoles.includes('Admin') || userRoles.includes('Project Manager');
                        if (canChangeStatus) {
                          return (
                            <select required className="if-select" value={form.status_id || ''} onChange={e => setForm({ ...form, status_id: e.target.value })}>
                              {/* <option value="">Select status...</option> */}
                              {statuses.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                            </select>
                          );
                        }

                        const currentName = statuses.find(s => String(s.id) === String(form.status_id))?.name || 'Unknown';
                        const isDev = userRoles.includes('Developer');
                        const isQA = userRoles.includes('QA');
                        const isReporterRole = userRoles.includes('Reporter');
                        const assignedToMe = editing?.assigned_to === user?.id;

                        let buttons = [];
                        if (isDev && assignedToMe && currentName === 'Open') {
                          buttons.push({ label: 'Start Work', next: 'In Progress', btnClass: 'btn-primary' });
                        }
                        if (isDev && assignedToMe && currentName === 'In Progress') {
                          buttons.push({ label: 'Mark as Resolved', next: 'Resolved', btnClass: 'btn-success' });
                        }
                        if (isQA && currentName === 'Resolved') {
                          buttons.push({ label: 'Verified', next: 'Closed', btnClass: 'btn-success' });
                          buttons.push({ label: 'Unresolved', next: 'In Progress', btnClass: 'btn-danger' });
                        }
                        if (isReporterRole && currentName === 'Verified') {
                          buttons.push({ label: 'Closed (Resolved)', next: 'Closed', btnClass: 'btn-secondary' });
                          buttons.push({ label: 'Unresolved', next: 'In Progress', btnClass: 'btn-danger' });
                        }

                        const setStatusName = (name) => {
                          const s = statuses.find(x => x.name === name);
                          if (s) setForm({ ...form, status_id: s.id });
                        };

                        return (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', height: '44px' }}>
                            <span style={{ fontWeight: 600, color: '#334155', padding: '6px 12px', background: '#e2e8f0', borderRadius: '6px' }}>{currentName}</span>
                            {buttons.map(b => (
                              <button type="button" key={b.next} className={`btn btn-sm ${b.btnClass}`} onClick={() => setStatusName(b.next)}>{b.label}</button>
                            ))}
                          </div>
                        );
                      })()}
                    </FieldGroup>
                  </div>

                  <FieldGroup label="Issue Type" required>
                    <div className="if-type-chips">
                      {ISSUE_TYPES.map(t => (
                        <button
                          key={t.value} type="button"
                          className={`if-type-chip${form.issue_type === t.value ? ' active' : ''}`}
                          style={form.issue_type === t.value ? { background: t.bg, color: t.color, borderColor: t.color } : {}}
                          onClick={() => setForm({ ...form, issue_type: t.value })}
                        >
                          <span>{t.icon}</span> {t.value}
                        </button>
                      ))}
                    </div>
                  </FieldGroup>

                  <div className="if-grid-2">
                    <FieldGroup label="Priority" required>
                      <select required className="if-select" value={form.priority_id || ''} onChange={e => setForm({ ...form, priority_id: e.target.value })}>
                        <option value="">Select priority…</option>
                        {priorities.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                      </select>
                    </FieldGroup>
                    <FieldGroup label="Severity" required>
                      <select required className="if-select" value={form.severity_id || ''} onChange={e => setForm({ ...form, severity_id: e.target.value })}>
                        <option value="">Select severity…</option>
                        {severities.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                      </select>
                    </FieldGroup>
                  </div>
                  
                  <div className="if-grid-2">
                    <FieldGroup label="Sprint" hint="Assign this issue to an active sprint.">
                      <select className="if-select"
                        value={form.sprint_id || ''}
                        onChange={(e) => setForm({ ...form, sprint_id: e.target.value })}
                        placeholder="No sprint - Backlog"
                        disabled={userRoles.includes('Developer') || userRoles.includes('QA') || userRoles.includes('Reporter')}
                      >
                        <option value="">No sprint - Backlog</option>
                        {projectSprints.map(s => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                      </select>
                    </FieldGroup>
                    <FieldGroup label="Assignee" hint="Who should resolve this issue?">
                      <select className="if-select"
                        value={form.assigned_to || ''}
                        onChange={(e) => {
                          const val = e.target.value;
                          setForm({ ...form, assigned_to: val ? val : null });
                        }}
                        placeholder="Unassigned"
                        disabled={userRoles.includes('Developer') || userRoles.includes('QA') || userRoles.includes('Reporter')}
                      >
                        <option value="">Unassigned</option>
                        {allUsers.map(u => (
                          <option key={u.id} value={u.id}>
                            {u.full_name}
                          </option>
                        ))}
                      </select>
                    </FieldGroup>
                  </div>
                </SectionCard>

                {/* Description */}
                <SectionCard icon="📝" title="Description">
                  <FieldGroup label="Summary" required hint="Minimum 20 characters. Be specific about what is broken and where.">
                    <textarea
                      required className="if-textarea"
                      placeholder="Provide a clear, concise explanation of the issue…"
                      rows={4}
                      value={form.description}
                      onChange={e => setForm({ ...form, description: e.target.value })}
                    />
                  </FieldGroup>
                  <div className="if-grid-3">
                    <FieldGroup label="Steps to Reproduce">
                      <textarea className="if-textarea" placeholder={"1. Navigate to...\n2. Click on...\n3. Observe..."} rows={4}
                        value={form.steps_to_reproduce} onChange={e => setForm({ ...form, steps_to_reproduce: e.target.value })} />
                    </FieldGroup>
                    <FieldGroup label="Expected Behavior">
                      <textarea className="if-textarea" placeholder="Describe what should happen…" rows={4}
                        value={form.expected_behavior} onChange={e => setForm({ ...form, expected_behavior: e.target.value })} />
                    </FieldGroup>
                    <FieldGroup label="Actual Behavior">
                      <textarea className="if-textarea" placeholder="Describe what actually happens…" rows={4}
                        value={form.actual_behavior} onChange={e => setForm({ ...form, actual_behavior: e.target.value })} />
                    </FieldGroup>
                  </div>
                </SectionCard>

                {/* Environment */}
                <SectionCard icon="🌐" title="Environment">
                  <div className="if-grid-2">
                    <FieldGroup label="Environment" hint="e.g. Production, Staging, Dev">
                      <input className="if-input" placeholder="Production" value={form.environment} onChange={e => setForm({ ...form, environment: e.target.value })} />
                    </FieldGroup>
                    <FieldGroup label="Browser / Device" hint="e.g. Chrome 115, iPhone 14 Pro">
                      <input className="if-input" placeholder="Chrome 115" value={form.browser} onChange={e => setForm({ ...form, browser: e.target.value })} />
                    </FieldGroup>
                  </div>
                </SectionCard>

                {/* Attachments — multi-file gallery */}
                <SectionCard icon="📎" title="Attachments">
                  <style>{`
                    .att-gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
                    .att-card {
                      position: relative; border-radius: 12px;
                      border: 1px solid rgba(15,23,42,0.08); background: #f8fafc;
                      padding: 12px 12px 10px; display: flex; flex-direction: column;
                      align-items: center; gap: 6px; transition: box-shadow .2s;
                    }
                    .att-card:hover { box-shadow: 0 4px 16px rgba(15,23,42,0.08); }
                    .att-thumb { width: 100%; height: 80px; border-radius: 8px; object-fit: cover; display: block; }
                    .att-icon { font-size: 2rem; }
                    .att-name { font-size: 0.72rem; font-weight: 600; color: #475569; text-align: center; word-break: break-all; }
                    .att-size { font-size: 0.66rem; color: #94a3b8; }
                    .att-del {
                      position: absolute; top: 6px; right: 6px;
                      width: 22px; height: 22px; border-radius: 50%; border: none; cursor: pointer;
                      background: rgba(239,68,68,0.90); color: #fff;
                      display: grid; place-items: center; opacity: 0; transition: opacity .2s;
                    }
                    .att-card:hover .att-del { opacity: 1; }
                    .att-link { font-size: 0.7rem; color: #3b82f6; font-weight: 600; text-decoration: none; }
                    .att-link:hover { text-decoration: underline; }
                    .att-uploading { display: flex; align-items: center; gap: 6px; font-size: 0.78rem; color: #94a3b8; padding: 8px 0; }
                  `}</style>

                  {/* Existing gallery */}
                  {attachments.length > 0 && (
                    <div className="att-gallery" style={{ marginBottom: 14 }}>
                      {attachments.map(att => {
                        const isImage = att.mime_type?.startsWith('image/')
                        const fileExt = att.filename.split('.').pop()?.toUpperCase() || 'FILE'
                        const sizeKb = att.file_size ? (att.file_size / 1024).toFixed(0) + ' KB' : ''
                        return (
                          <div key={att.id} className="att-card">
                            {isImage
                              ? <img className="att-thumb" src={`http://localhost:8000${att.file_path}`} alt={att.filename} />
                              : <div className="att-icon">{fileExt === 'PDF' ? '📄' : fileExt === 'MP4' || fileExt === 'MOV' ? '🎥' : fileExt === 'ZIP' ? '🗜️' : '📁'}</div>
                            }
                            <div className="att-name">{att.filename}</div>
                            {sizeKb && <div className="att-size">{sizeKb}</div>}
                            <a className="att-link" href={`http://localhost:8000${att.file_path}`} target="_blank" rel="noreferrer">Open ↗</a>
                            <button className="att-del" type="button" title="Delete attachment"
                              onClick={async () => {
                                try {
                                  await deleteIssueAttachment(editing.id, att.id)
                                  setAttachments(a => a.filter(x => x.id !== att.id))
                                } catch { setError('Failed to delete attachment.') }
                              }}
                            >
                              <svg width="10" height="10" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" d="M6 18L18 6M6 6l12 12"/></svg>
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  )}

                  {/* Upload drop zone */}
                  <div className="if-file-drop" style={{ position: 'relative' }}>
                    <input type="file"
                      style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer', width: '100%', height: '100%' }}
                      onChange={async (e) => {
                        const f = e.target.files[0]
                        if (!f) return
                        if (editing) {
                          setAttachUploading(true)
                          try {
                            const res = await addIssueAttachment(editing.id, f)
                            setAttachments(prev => [...prev, res.data])
                          } catch { setError('Upload failed.') }
                          finally { setAttachUploading(false); e.target.value = '' }
                        } else {
                          setFile(f)
                        }
                      }}
                    />
                    <div className="if-file-icon">📁</div>
                    <div className="if-file-label">
                      {attachUploading ? 'Uploading…' : (file ? file.name : 'Click or drag to add a file')}
                    </div>
                    <div className="if-file-sub">
                      {editing ? 'Files are saved instantly. Screenshots, videos, logs — up to 20MB each.' : 'File will be attached once the issue is saved.'}
                    </div>
                    {file && !editing && <div className="if-file-chosen">✓ {file.name} will upload on save</div>}
                    {attachUploading && (
                      <div className="att-uploading">
                        <svg style={{ animation: 'spin 1s linear infinite', width: 12, height: 12 }} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/></svg>
                        Uploading file…
                      </div>
                    )}
                  </div>
                </SectionCard>

              </form>
            </div>

            {/* ── RIGHT: Activity Timeline ── */}
            {editing && (
              <div className="if-right">
                {/* AI Resolution Assistance Card */}
                {resolutionAssistanceLoading ? (
                  <div className="if-resolution-assistant-card" style={{ marginBottom: '24px' }}>
                    <div className="if-resolution-assistant-header">
                      <span className="if-resolution-assistant-icon">🤖</span>
                      <span className="if-resolution-assistant-title">AI Resolution Assistance</span>
                    </div>
                    <div className="if-resolution-assistant-body">
                      <div className="if-spinner">
                        <svg style={{ animation: 'spin 1s linear infinite', width: 20, height: 20 }} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                          <path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                        </svg>
                        Loading…
                      </div>
                    </div>
                  </div>
                ) : resolutionAssistanceError ? (
                  <div className="if-resolution-assistant-card if-error" style={{ marginBottom: '24px' }}>
                    <div className="if-resolution-assistant-header">
                      <span className="if-resolution-assistant-icon">🤖</span>
                      <span className="if-resolution-assistant-title">AI Resolution Assistance</span>
                    </div>
                    <div className="if-resolution-assistant-body">
                      {resolutionAssistanceError}
                    </div>
                  </div>
                ) : resolutionAssistanceData ? (
                  <div className="if-resolution-assistant-card" style={{ marginBottom: '24px' }}>
                    <div className="if-resolution-assistant-header">
                      <span className="if-resolution-assistant-icon">🤖</span>
                      <span className="if-resolution-assistant-title">AI Resolution Assistance</span>
                    </div>
                    <div className="if-resolution-assistant-body">
                      <div className="if-resolution-assistant-section">
                        <h4>Investigation Areas</h4>
                        <ul>
                          {resolutionAssistanceData.investigation_areas.map((area, index) => (
                            <li key={index}>• {area}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="if-resolution-assistant-section">
                        <h4>Possible Causes</h4>
                        <ul>
                          {resolutionAssistanceData.possible_causes.map((cause, index) => (
                            <li key={index}>• {cause}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="if-resolution-assistant-section">
                        <h4>Suggested Resolution</h4>
                        <p>{resolutionAssistanceData.suggested_resolution}</p>
                      </div>
                      {resolutionAssistanceData.similar_defects_summary && (
                        <div className="if-resolution-assistant-section">
                          <h4>Similar Defects Summary</h4>
                          <p>{resolutionAssistanceData.similar_defects_summary}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ) : null}
                <IssueTimeline issueId={editing.id} />
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="if-footer">
            {!canSubmit && form.description?.trim().length > 0 && form.description?.trim().length < 20 && (
              <span className="if-progress">{20 - form.description?.trim().length} more characters needed in description</span>
            )}
            <button type="button" className="if-cancel-btn" onClick={() => setShowForm(false)} disabled={uploading}>Cancel</button>
            <button type="submit" form="issue-form" className="if-save-btn" disabled={!canSubmit}>
              {uploading ? (
                <>
                  <svg style={{ animation: 'spin 1s linear infinite', width: 14, height: 14 }} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                  </svg>
                  Saving…
                </>
              ) : (
                <>
                  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  {editing ? 'Update Issue' : 'Create Issue'}
                </>
              )}
            </button>
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