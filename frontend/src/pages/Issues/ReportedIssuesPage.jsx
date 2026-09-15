import { useEffect, useState, useMemo } from 'react'
import { useLocation, useSearchParams, useParams } from 'react-router-dom'
import IssueTable, { isClientFeatureRequest } from '../../components/IssueTable/IssueTable'
import Modal from '../../components/Modal/Modal'
import Toast from '../../components/Toast/Toast'
import TroubleshootingModal from '../../components/TroubleshootingModal/TroubleshootingModal'
import IssueTimeline from '../../components/ActivityTimeline/IssueTimeline'
import AITestIntelligence from '../../components/AITestIntelligence/AITestIntelligence'
import SearchableSelect from '../../components/common/SearchableSelect'
import { 
  getIssues, getStatuses, getPriorities, getSeverities, getCategories, getModules,
  createIssue, updateIssue, deleteIssue, uploadFile,
  getIssueAttachments, addIssueAttachment, deleteIssueAttachment,
  getIssueHistory, getIssueComments, addIssueComment, updateIssueStatus, updateIssueAssignee, updateIssueQaAssignee,
  semanticSearch, getSimilarIssues, searchIssues, getIssue,
  assignIssueTeam, qaVerifyIssue, hybridSearch, extractErrorMessage
} from '../../services/issueService'
import { getSprints } from '../../services/sprintService'
import { getProjects } from '../../services/projectService'
import { getTeams } from '../../services/teamService'
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
  const [searchParams, setSearchParams] = useSearchParams()
  const { id: routeIssueId } = useParams()
  const userRole = user?.role || user?.roles?.[0]?.name || ''
  const userRoles = user?.roles?.map(r => r.name) || [userRole]
  const canDeleteIssue = ['Admin', 'Super Admin', 'QA', 'Project Manager'].includes(userRole) || userRoles.some(r => ['Admin', 'Super Admin', 'QA', 'Project Manager'].includes(r))
  const canAccessTestIntelligence = userRoles.some(r => ['Admin', 'Super Admin', 'Project Manager', 'PM', 'Team Leader', 'TL', 'QA'].includes(r))
  const canAssignIssues = userRoles.some(r => ['Admin', 'Super Admin', 'Project Manager', 'PM', 'Team Leader', 'TL', 'QA'].includes(r))
  const isSuperAdmin = userRoles.includes('Super Admin')

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
  const empty = { title: '', description: '', project_id: '', priority_id: '', severity_id: '', category_id: '', module_id: '', status_id: '', assigned_to: null, assigned_qa_id: null, issue_type: 'Bug', environment: '', browser: '', steps_to_reproduce: '', expected_behavior: '', actual_behavior: '', attachment_path: '', sprint_id: '' }

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
  const [statusUpdating, setStatusUpdating] = useState(false)
  const [assigneeUpdating, setAssigneeUpdating] = useState(false)
  const [qaAssigneeUpdating, setQaAssigneeUpdating] = useState(false)

  // Scope filter tabs (All, Customer Requests, Needs Squad Assignment)
  const [activeScopeTab, setActiveScopeTab] = useState(searchParams.get('filter') || 'all')
  const [quickAssignIssue, setQuickAssignIssue] = useState(null)
  const [quickTeamId, setQuickTeamId] = useState('')
  const [toast, setToast] = useState({ message: '', variant: 'success' })

  const bugforgeProject = allProjects.find(p => p.name === 'BugForge' || p.key === 'BF')

  // Semantic search state
  const [similarDefects, setSimilarDefects] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchTimeout, setSearchTimeout] = useState(null)

  // Unified hybrid search in list view
  const [hybridResults, setHybridResults] = useState(null)
  const [hybridLoading, setHybridLoading] = useState(false)

  // Similar defects panel for detail view
  const [detailSimilarDefects, setDetailSimilarDefects] = useState([])
  const [detailSimilarLoading, setDetailSimilarLoading] = useState(false)

  // Resolution assistance state
  const [resolutionAssistanceLoading, setResolutionAssistanceLoading] = useState(false)
  const [resolutionAssistanceData, setResolutionAssistanceData] = useState(null)
  const [resolutionAssistanceError, setResolutionAssistanceError] = useState('')

  // AI Test Intelligence state
  const [showTestIntelligence, setShowTestIntelligence] = useState(false)

  // Troubleshooting modal state
  const [showTroubleshootingModal, setShowTroubleshootingModal] = useState(false)
  const [troubleshootingPayload, setTroubleshootingPayload] = useState(null)

  // Resolve defect modal state
  const [showResolveModal, setShowResolveModal] = useState(false)
  const [resolveForm, setResolveForm] = useState({ root_cause: '', resolution: '', comment: '' })
  const [resolveError, setResolveError] = useState('')
  const [resolving, setResolving] = useState(false)

  // Feature workflow & QA verification state
  const [internalTeams, setInternalTeams] = useState([])
  const [selectedTeamId, setSelectedTeamId] = useState('')
  const [assigningTeam, setAssigningTeam] = useState(false)
  const [qaNotes, setQaNotes] = useState('')
  const [qaVerifying, setQaVerifying] = useState(false)

  const isBug = form.issue_type === 'Bug' || form.issue_type === 'Defect'

  const load = async () => {
    const [issueResult, statusResult, priorityResult, severityResult, categoryResult, moduleResult, projResult, userResult, teamResult] = await Promise.all([
      getIssues(), getStatuses(), getPriorities(), getSeverities(), getCategories(), getModules(), getProjects('', 1000, 0), getUsers('', 1000, 0), getTeams().catch(() => ({ data: [] }))
    ])
    setIssues(issueResult.data)
    setStatuses(statusResult.data)
    setPriorities(priorityResult.data)
    setSeverities(severityResult.data)
    setCategories(categoryResult.data)
    setModules(moduleResult.data)
    setAllProjects(projResult.data)
    setAllUsers(userResult.data?.data || [])
    setInternalTeams(teamResult.data?.data || teamResult.data || [])
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
    const targetIssueId =
      location.state?.issueId ||
      location.state?.editIssueId ||
      routeIssueId ||
      searchParams.get('issueId') ||
      searchParams.get('id')

    if (location.state?.editIssue && statuses.length) {
      open(location.state.editIssue)
      window.history.replaceState({}, document.title)
    } else if (targetIssueId && statuses.length) {
      const found = issues.find(i => String(i.id) === String(targetIssueId))
      if (found) {
        open(found)
      } else {
        getIssue(targetIssueId)
          .then(res => {
            if (res.data) open(res.data)
          })
          .catch(err => {
            console.error('Failed to load issue for notification:', err)
          })
      }
      window.history.replaceState({}, document.title)
    } else if (location.state?.openNewIssue && statuses.length) {
      open()
      window.history.replaceState({}, document.title)
    }
  }, [location.state, routeIssueId, searchParams, statuses.length, issues])

  useEffect(() => {
    const f = searchParams.get('filter')
    if (f) {
      setActiveScopeTab(f)
    } else {
      setActiveScopeTab('all')
    }
  }, [searchParams])

  // Debounced semantic search for similar defects during creation / editing
  useEffect(() => {
    if (searchTimeout) clearTimeout(searchTimeout)

    const timeout = setTimeout(async () => {
      if (form.title?.trim() && form.description?.trim() &&
          form.title.trim().length > 0 && form.description.trim().length >= 20) {
        setSearchLoading(true)
        try {
          const { data } = await searchIssues(
            form.title,
            form.description,
            form.project_id || null,
            editing?.id || null
          )
          // Backend returns [{issue: {...}, similarity: float}]
          const similar = data.filter(item => item.similarity >= 0.60)
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
    return () => { if (searchTimeout) clearTimeout(searchTimeout) }
  }, [form.title, form.description, form.project_id, editing?.id])

  // Load similar defects when editing an existing issue
  useEffect(() => {
    if (editing?.id) {
      setDetailSimilarLoading(true)
      getSimilarIssues(editing.id, form.project_id || editing.project_id)
        .then(r => setDetailSimilarDefects(r.data || []))
        .catch(() => setDetailSimilarDefects([]))
        .finally(() => setDetailSimilarLoading(false))
    } else {
      setDetailSimilarDefects([])
    }
  }, [editing?.id, form.project_id, editing?.project_id])

  // Unified debounced hybrid search in list view (combining keyword and pgvector semantic search)
  useEffect(() => {
    const trimmed = query.trim()
    const projId = project ? Number(project) : null
    const matchedStatus = statuses.find(s => s.name?.toLowerCase() === status.toLowerCase() || String(s.id) === String(status))
    const statusId = matchedStatus ? matchedStatus.id : (status ? Number(status) : null)

    if (!trimmed) {
      setHybridResults(null)
      setHybridLoading(false)
      return
    }

    setHybridLoading(true)
    const timer = setTimeout(async () => {
      try {
        const res = await hybridSearch(trimmed, projId, statusId)
        setHybridResults(res.data || [])
      } catch (err) {
        console.warn('Hybrid search failed, falling back to local filtering:', err)
        setHybridResults(null)
      } finally {
        setHybridLoading(false)
      }
    }, 350)
    return () => clearTimeout(timer)
  }, [query, project, status, statuses])

  const open = (issue = null) => {
    // Reset resolution assistance and QA intelligence when opening a new issue or switching issues
    setResolutionAssistanceLoading(false)
    setResolutionAssistanceData(null)
    setResolutionAssistanceError('')
    setShowTestIntelligence(false)
    setEditing(issue)
    const openStatusId = statuses.find(s => s.name === 'Open')?.id || statuses[0]?.id || ''
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
          assigned_qa_id: issue.assigned_qa_id || null,
          issue_type: issue.issue_type ? BACKEND_TO_FRONTEND_ISSUE_TYPE[issue.issue_type] : 'Bug',
          environment: issue.environment || '',
          browser: issue.browser || '',
          steps_to_reproduce: issue.steps_to_reproduce || '',
          expected_behavior: issue.expected_behavior || '',
          actual_behavior: issue.actual_behavior || '',
          root_cause: issue.root_cause || '',
          resolution: issue.resolution || '',
          attachment_path: issue.attachment_path || '',
          sprint_id: issue.sprint_id || ''
        }
      : { ...empty, status_id: openStatusId, project_id: allProjects[0]?.id || '' }
    )
    setFile(null)
    setAttachments([])
    setSelectedTeamId(issue?.team_id || '')
    setQaNotes('')
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
    setError('')
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
        steps_to_reproduce: (data.steps_to_reproduce && data.steps_to_reproduce !== 'N/A') ? data.steps_to_reproduce : form.steps_to_reproduce,
        expected_behavior: (data.expected_behavior && data.expected_behavior !== 'N/A') ? data.expected_behavior : form.expected_behavior,
        actual_behavior: (data.actual_behavior && data.actual_behavior !== 'N/A') ? data.actual_behavior : form.actual_behavior,
        environment: (data.environment && data.environment !== 'N/A') ? data.environment : form.environment,
        browser: (data.browser && data.browser !== 'N/A') ? data.browser : form.browser,
        root_cause: data.root_cause || form.root_cause,
        resolution: data.resolution || form.resolution,
      })
    } catch (e) {
      setError("AI formatting failed.")
    } finally {
      setFormatting(false)
    }
  }

  const openResolveModal = () => {
    setResolveForm({
      root_cause: form.root_cause || '',
      resolution: form.resolution || '',
      comment: ''
    })
    setResolveError('')
    setShowResolveModal(true)
  }

  const handleConfirmResolve = async () => {
    if (!resolveForm.root_cause?.trim()) {
      setResolveError('Please specify the Root Cause of the defect.')
      return
    }
    if (!resolveForm.resolution?.trim()) {
      setResolveError('Please provide the Resolution details for how this issue was fixed.')
      return
    }

    const resolvedStatus = statuses.find(s => s.name === 'Resolved')
    if (!resolvedStatus) {
      setResolveError('Resolved status not found in system.')
      return
    }

    setResolving(true)
    setResolveError('')
    try {
      if (editing) {
        await updateIssueStatus(editing.id, {
          status_id: resolvedStatus.id,
          root_cause: resolveForm.root_cause.trim(),
          resolution: resolveForm.resolution.trim(),
          comment: resolveForm.comment?.trim() || undefined
        })
        setForm(prev => ({
          ...prev,
          status_id: resolvedStatus.id,
          root_cause: resolveForm.root_cause.trim(),
          resolution: resolveForm.resolution.trim()
        }))
        setEditing(prev => ({
          ...prev,
          status_id: resolvedStatus.id,
          status_name: resolvedStatus.name,
          root_cause: resolveForm.root_cause.trim(),
          resolution: resolveForm.resolution.trim()
        }))
        await load()
      } else {
        setForm(prev => ({
          ...prev,
          status_id: resolvedStatus.id,
          root_cause: resolveForm.root_cause.trim(),
          resolution: resolveForm.resolution.trim()
        }))
      }
      setShowResolveModal(false)
    } catch (err) {
      setResolveError(err.response?.data?.detail || 'Failed to mark issue as resolved.')
    } finally {
      setResolving(false)
    }
  }

  const handleImmediateStatusChange = async (nextStatusIdOrName) => {
    let targetStatus = null
    if (typeof nextStatusIdOrName === 'string' && isNaN(Number(nextStatusIdOrName))) {
      if (nextStatusIdOrName === 'Resolved') {
        openResolveModal()
        return
      }
      targetStatus = statuses.find(x => x.name === nextStatusIdOrName)
    } else {
      targetStatus = statuses.find(x => String(x.id) === String(nextStatusIdOrName))
      if (targetStatus?.name === 'Resolved') {
        openResolveModal()
        return
      }
    }

    if (!targetStatus) return

    if (!editing) {
      setForm(prev => ({ ...prev, status_id: targetStatus.id }))
      return
    }

    setStatusUpdating(true)
    setError('')
    try {
      await updateIssueStatus(editing.id, { status_id: targetStatus.id })
      setForm(prev => ({ ...prev, status_id: targetStatus.id }))
      setEditing(prev => ({ ...prev, status_id: targetStatus.id, status_name: targetStatus.name }))
      setIssues(prev => prev.map(iss => iss.id === editing.id ? { ...iss, status_id: targetStatus.id, status_name: targetStatus.name } : iss))
    } catch (err) {
      console.error("Failed to update status immediately:", err)
      setError(err.response?.data?.detail || 'Failed to update status.')
    } finally {
      setStatusUpdating(false)
    }
  }

  const handleImmediateAssigneeChange = async (nextAssigneeId) => {
    const parsedId = nextAssigneeId ? Number(nextAssigneeId) : null
    if (!editing) {
      setForm(prev => ({ ...prev, assigned_to: parsedId }))
      return
    }

    setAssigneeUpdating(true)
    setError('')
    try {
      await updateIssueAssignee(editing.id, { assigned_to: parsedId })
      const assignedUser = allUsers.find(u => String(u.id) === String(parsedId))
      setForm(prev => ({ ...prev, assigned_to: parsedId }))
      setEditing(prev => ({ ...prev, assigned_to: parsedId, assigned_to_user: assignedUser, assignee: assignedUser?.full_name || null }))
      setIssues(prev => prev.map(iss => iss.id === editing.id ? { ...iss, assigned_to: parsedId, assignee: assignedUser?.full_name || null } : iss))
    } catch (err) {
      console.error("Failed to update assignee immediately:", err)
      setError(err.response?.data?.detail || 'Failed to update assignee.')
    } finally {
      setAssigneeUpdating(false)
    }
  }

  const handleImmediateQaAssigneeChange = async (nextQaId) => {
    const parsedId = nextQaId ? Number(nextQaId) : null
    if (!editing) {
      setForm(prev => ({ ...prev, assigned_qa_id: parsedId }))
      return
    }

    setQaAssigneeUpdating(true)
    setError('')
    try {
      await updateIssueQaAssignee(editing.id, { assigned_qa_id: parsedId })
      const assignedQaUser = allUsers.find(u => String(u.id) === String(parsedId))
      setForm(prev => ({ ...prev, assigned_qa_id: parsedId }))
      setEditing(prev => ({ ...prev, assigned_qa_id: parsedId, assigned_qa_name: assignedQaUser?.full_name || null }))
      setIssues(prev => prev.map(iss => iss.id === editing.id ? { ...iss, assigned_qa_id: parsedId, assigned_qa_name: assignedQaUser?.full_name || null } : iss))
    } catch (err) {
      console.error("Failed to update QA assignee immediately:", err)
      setError(err.response?.data?.detail || 'Failed to update QA assignee.')
    } finally {
      setQaAssigneeUpdating(false)
    }
  }

  const handleAssignTeam = async () => {
    if (!editing || !selectedTeamId) return
    setAssigningTeam(true)
    setError('')
    try {
      const res = await assignIssueTeam(editing.id, { team_id: Number(selectedTeamId) })
      const updatedIssue = res.data
      const assignedTeam = internalTeams.find(t => String(t.id) === String(selectedTeamId))
      const teamName = assignedTeam ? assignedTeam.name : (updatedIssue.team_name || 'the squad')
      setEditing(prev => ({
        ...prev,
        team_id: updatedIssue.team_id,
        team_name: updatedIssue.team_name,
        status_id: updatedIssue.status_id,
        status_name: updatedIssue.status_name,
      }))
      setIssues(prev => prev.map(iss => iss.id === editing.id ? {
        ...iss,
        team_id: updatedIssue.team_id,
        team_name: updatedIssue.team_name,
        status_id: updatedIssue.status_id,
        status_name: updatedIssue.status_name,
      } : iss))
      setToast({
        message: `Customization request assigned to squad "${teamName}" successfully.`,
        variant: 'success'
      })
    } catch (err) {
      console.error("Failed to assign team:", err)
      const errorMsg = extractErrorMessage(err, 'Failed to assign team.')
      setError(errorMsg)
      setToast({ message: errorMsg, variant: 'error' })
    } finally {
      setAssigningTeam(false)
    }
  }

  const handleQAVerify = async (qaState) => {
    if (!editing) return
    setQaVerifying(true)
    setError('')
    try {
      const res = await qaVerifyIssue(editing.id, { qa_state: qaState, notes: qaNotes })
      const updatedIssue = res.data
      setEditing(prev => ({
        ...prev,
        qa_state: updatedIssue.qa_state,
        qa_verified_by_name: updatedIssue.qa_verified_by_name,
        qa_verified_at: updatedIssue.qa_verified_at,
        status_id: updatedIssue.status_id,
        status_name: updatedIssue.status_name,
      }))
      setForm(prev => ({
        ...prev,
        status_id: updatedIssue.status_id,
      }))
      setIssues(prev => prev.map(iss => iss.id === editing.id ? {
        ...iss,
        qa_state: updatedIssue.qa_state,
        status_id: updatedIssue.status_id,
        status_name: updatedIssue.status_name
      } : iss))
      setQaNotes('')
    } catch (err) {
      console.error("Failed to verify QA state:", err)
      setError(err.response?.data?.detail || 'Failed to verify QA state.')
    } finally {
      setQaVerifying(false)
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
      const defaultPriorityId = (priorities.find(s => s.name === 'Medium')?.id || priorities[0]?.id) ?? 1
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
        assigned_qa_id: form.assigned_qa_id ? Number(form.assigned_qa_id) : null,
        attachment_path: currentAttachment,
        status_id: form.status_id ? Number(form.status_id) : defaultStatusId,
        priority_id: form.priority_id ? Number(form.priority_id) : defaultPriorityId,
        severity_id: form.severity_id ? Number(form.severity_id) : defaultSeverityId,
        module_id: form.module_id ? Number(form.module_id) : defaultModuleId,
        category_id: form.category_id ? Number(form.category_id) : defaultCategoryId,
        sprint_id: form.sprint_id ? Number(form.sprint_id) : null,
      }
      if (editing) {
        await updateIssue(editing.id, payload)
        setShowForm(false)
        await load()
      } else if (isBug) {
        // Intercept Bug/Defect creation and launch troubleshooting modal
        console.log("[ReportedIssuesPage] Intercepting Bug save to launch TroubleshootingModal with payload:", payload)
        setTroubleshootingPayload(payload)
        setShowTroubleshootingModal(true)
      } else {
        // Task / Feature creation proceeds directly
        const createRes = await createIssue(payload)
        const createData = createRes.data
        if (createData.similar_issues && createData.similar_issues.length > 0) {
          setSimilarDefects(createData.similar_issues.map(s => ({
            issue: s,
            similarity: s.similarity_score
          })))
        }
        setShowForm(false)
        await load()
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'Unable to save issue.')
    } finally {
      setUploading(false)
    }
  }


  const handleTroubleshootingConfirm = async (createdIssueData) => {
    console.log("[ReportedIssuesPage] Troubleshooting confirmed, issue created:", createdIssueData)
    setShowTroubleshootingModal(false)
    setShowForm(false)
    if (createdIssueData.similar_issues && createdIssueData.similar_issues.length > 0) {
      setSimilarDefects(createdIssueData.similar_issues.map(s => ({
        issue: s,
        similarity: s.similarity_score
      })))
    }
    await load()
  }

  const handleTroubleshootingSkip = async () => {
    console.log("[ReportedIssuesPage] AI skipped, submitting issue directly...")
    setUploading(true)
    try {
      const createRes = await createIssue(troubleshootingPayload)
      const createData = createRes.data
      if (createData.similar_issues && createData.similar_issues.length > 0) {
        setSimilarDefects(createData.similar_issues.map(s => ({
          issue: s,
          similarity: s.similarity_score
        })))
      }
      setShowTroubleshootingModal(false)
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

  const customerRequestsCount = useMemo(() => {
    return issues.filter(i => isClientFeatureRequest(i) || i.requesting_company_id || i.issue_type === 'Feature').length
  }, [issues])

  const unassignedSquadCount = useMemo(() => {
    return issues.filter(i => (isClientFeatureRequest(i) || i.requesting_company_id || i.issue_type === 'Feature') && !i.team_id).length
  }, [issues])

  const statusFilterOptions = useMemo(() => {
    const seen = new Set()
    const opts = []
    for (const s of statuses) {
      const nameKey = (s.name || '').trim().toLowerCase()
      if (!nameKey || seen.has(nameKey)) continue
      seen.add(nameKey)
      opts.push({ value: s.name, label: s.name })
    }
    return opts
  }, [statuses])

  const filtered = useMemo(() => {
    let list = hybridResults !== null ? hybridResults : issues.filter((issue) => {
      const matchStatus =
        !status ||
        String(issue.status_name || '').toLowerCase() === String(status).toLowerCase() ||
        String(issue.status_id) === String(status)
      const matchProject = !project || String(issue.project_id) === String(project)
      const qLower = query.toLowerCase().trim()
      const matchQuery = !qLower ||
        `${issue.key || issue.issue_key || ''} ${issue.title || ''} ${issue.description || ''}`
          .toLowerCase()
          .includes(qLower)
      return matchStatus && matchProject && matchQuery

    })

    if (activeScopeTab === 'customer_requests') {
      list = list.filter(i => isClientFeatureRequest(i) || i.requesting_company_id || i.issue_type === 'Feature')
    } else if (activeScopeTab === 'unassigned_squad') {
      list = list.filter(i => (isClientFeatureRequest(i) || i.requesting_company_id || i.issue_type === 'Feature') && !i.team_id)
    }

    return list
  }, [hybridResults, issues, status, project, query, activeScopeTab])

  const isFormClosedAndReadOnly = editing && (statuses.find(s => String(s.id) === String(editing.status_id))?.name === 'Closed') && !userRoles.includes('Admin') && !userRoles.includes('Super Admin')
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

        /* QA Test Intelligence button */
        .if-qa-btn {
          margin-left: 12px; display: inline-flex; align-items: center; gap: 8px;
          padding: 8px 18px; border-radius: 10px; border: none; cursor: pointer;
          font-size: 0.82rem; font-weight: 600;
          background: linear-gradient(135deg, #059669, #0d9488);
          color: #fff; transition: opacity .2s, transform .15s, box-shadow .2s;
          box-shadow: 0 2px 12px rgba(5,150,105,0.3);
        }
        .if-qa-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); box-shadow: 0 4px 20px rgba(5,150,105,0.4); }
        .if-qa-btn.active {
          background: linear-gradient(135deg, #047857, #0f766e);
          box-shadow: inset 0 2px 4px rgba(0,0,0,0.2), 0 0 0 2px #a7f3d0;
        }
        .if-qa-btn:disabled { opacity: 0.45; cursor: not-allowed; }

        /* Layout */
        .if-layout {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 460px;
          gap: 0;
          min-height: 0;
          align-items: stretch;
        }

        /* Left: form scroll area */
        .if-left {
          padding: 32px 36px;
          border-right: 1px solid rgba(15,23,42,0.07);
          overflow-y: auto;
          display: flex; flex-direction: column; gap: 28px;
        }

        /* Right: timeline & AI assistant */
        .if-right {
          background: #fafbfc;
          padding: 32px 24px;
          display: flex; flex-direction: column;
          gap: 20px;
          overflow-y: auto;
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
          border: 1px solid rgba(15,23,42,0.08);
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 4px 16px rgba(15,23,42,0.05);
          margin-bottom: 20px;
          display: flex;
          flex-direction: column;
          flex-shrink: 0;
        }
        .if-resolution-assistant-header {
          display: flex; align-items: center; gap: 10px;
          padding: 16px 22px;
          background: linear-gradient(135deg, #f8fafc, #f1f5f9);
          border-bottom: 1px solid rgba(15,23,42,0.07);
        }
        .if-resolution-assistant-icon { font-size: 1.15rem; }
        .if-resolution-assistant-title { font-weight: 700; font-size: 0.85rem; letter-spacing: .04em; text-transform: uppercase; color: #475569; }
        .if-resolution-assistant-body { 
          padding: 24px 22px; 
          display: flex; 
          flex-direction: column; 
          gap: 22px; 
          max-height: 720px;
          overflow-y: auto;
          scrollbar-width: thin;
        }
        .if-resolution-assistant-section h4 {
          font-weight: 700; font-size: 0.92rem; color: #0f172a; margin-bottom: 10px;
        }
        .if-resolution-assistant-section ul {
          margin: 0; padding-left: 20px;
        }
        .if-resolution-assistant-section ul li {
          color: #334155; line-height: 1.65; margin-bottom: 4px;
        }
        .if-resolution-assistant-section p {
          color: #334155; line-height: 1.65; margin: 0;
        }
        .if-spinner {
          display: flex; align-items: center; justify-content: center;
        }
        .if-spinner svg { width: 20px; height: 20px; }

        /* Responsive */
        @media (max-width: 1100px) {
          .if-layout { grid-template-columns: 1fr; }
          .if-right { border-top: 1px solid rgba(15,23,42,0.07); border-radius: 0 0 20px 20px; padding: 24px 20px; }
          .if-grid-3 { grid-template-columns: 1fr 1fr; }
          .if-resolution-assistant-card { margin-bottom: 16px !important; }
          .if-resolution-assistant-body { max-height: 550px; }
        }
        @media (max-width: 640px) {
          .if-grid-2, .if-grid-3 { grid-template-columns: 1fr; }
          .if-left { padding: 20px; }
          .if-right { padding: 20px 16px; }
          .if-resolution-assistant-card { margin-bottom: 12px !important; }
          .if-resolution-assistant-body { max-height: 480px; padding: 18px 16px; gap: 16px; }
        }
      `}</style>

      <section className="page-heading" style={{ animation: 'fadeSlideUp .5s ease both', display: 'flex', alignItems: 'flex-start', gap: '24px' }}>
        {showForm && (
          <button className="if-back-btn-icon" style={{ marginTop: '20px', flexShrink: 0 }} onClick={() => setShowForm(false)} title="Back to Issues">
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
          </button>
        )}
        <div style={{ flex: 1 }}>
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
          {/* Quick Scope Filter Tabs for Super Admin / Team Assignment */}
          <div className="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
            <div className="btn-group btn-group-sm p-1 bg-light rounded-3 border">
              <button
                type="button"
                className={`btn btn-sm ${activeScopeTab === 'all' ? 'btn-white bg-white text-dark shadow-xs font-semibold' : 'text-muted border-0'}`}
                onClick={() => { setActiveScopeTab('all'); setSearchParams({}) }}
              >
                All Issues ({issues.length})
              </button>
              <button
                type="button"
                className={`btn btn-sm ${activeScopeTab === 'customer_requests' ? 'btn-white bg-white text-primary shadow-xs font-semibold' : 'text-muted border-0'}`}
                onClick={() => { setActiveScopeTab('customer_requests'); setSearchParams({ filter: 'customer_requests' }) }}
              >
                <i className="bi bi-stars me-1 text-primary" />Customer Requests ({customerRequestsCount})
              </button>
              {unassignedSquadCount > 0 && (
                <button
                  type="button"
                  className={`btn btn-sm ${activeScopeTab === 'unassigned_squad' ? 'btn-white bg-white text-danger shadow-xs font-semibold' : 'text-muted border-0'}`}
                  onClick={() => { setActiveScopeTab('unassigned_squad'); setSearchParams({ filter: 'unassigned_squad' }) }}
                >
                  <i className="bi bi-exclamation-triangle-fill me-1 text-danger" />Needs Squad ({unassignedSquadCount})
                </button>
              )}
            </div>

            {activeScopeTab !== 'all' && (
              <span className="text-xs text-muted">
                Showing <strong>{filtered.length}</strong> {activeScopeTab === 'unassigned_squad' ? 'requests needing squad assignment' : 'customer feature requests'}
              </span>
            )}
          </div>

          <div className="issue-filters" style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div className="search-input" style={{ position: 'relative', flex: 1, minWidth: '280px' }}>
              <span className="input-group-text" style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none', zIndex: 1 }}>
                {hybridLoading ? (
                  <svg style={{ animation: 'spin 1s linear infinite', width: 16, height: 16 }} fill="none" stroke="#3b82f6" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" /></svg>
                ) : (
                  <i className="bi bi-search" />
                )}
              </span>
              <input
                className="form-control"
                style={{ paddingLeft: '44px', height: '42px', borderRadius: '8px' }}
                placeholder="Search issues by ID, title, or describe problem in natural language…"
                value={query}
                autoComplete="off"
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <div style={{ minWidth: '180px' }}>
              <SearchableSelect
                placeholder="All Statuses"
                isClearable
                options={statusFilterOptions}
                value={status || null}
                onChange={(val) => setStatus(val ? String(val) : '')}
              />
            </div>
            <div style={{ minWidth: '200px' }}>
              <SearchableSelect
                placeholder="All Projects"
                isClearable
                options={allProjects.map(p => ({ value: p.id, label: p.name }))}
                value={project ? Number(project) : null}
                onChange={(val) => setProject(val ? String(val) : '')}
              />
            </div>
          </div>
          {error && <div className="alert alert-danger mt-3">{error}</div>}

          <IssueTable
            issues={filtered}
            onEdit={open}
            onDelete={remove}
            canDelete={canDeleteIssue}
            onAssignTeam={isSuperAdmin ? (iss) => {
              setQuickAssignIssue(iss)
              setQuickTeamId(iss.team_id || '')
            } : null}
          />
        </section>
      )}

      {/* ── FORM VIEW ── */}
      {showForm && (
        <div className="panel-card" style={{ padding: 0, overflow: 'hidden', animation: 'fadeSlideUp .4s ease both' }}>

          {/* Top bar */}
          <div className="if-topbar">
            {editing && <span className="if-id-badge"><i className="bi bi-tag" />{editing.issue_key || 'Issue Details'}</span>}
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
              {/* AI Resolution Assistance Button - only for Developer/Project Manager/Admin/Super Admin/TL and when editing a Bug/Defect */}
              {editing && isBug && (userRoles.includes('Developer') || userRoles.includes('Project Manager') || userRoles.includes('Admin') || userRoles.includes('Super Admin') || userRoles.includes('Team Leader')) && (
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

              {/* AI Test Intelligence Button - when editing an issue and role is allowed */}
              {editing && canAccessTestIntelligence && (
                <button 
                  type="button" 
                  className={`if-qa-btn ${showTestIntelligence ? 'active' : ''}`}
                  onClick={() => setShowTestIntelligence(prev => !prev)}
                >
                  🧪 AI Test Intelligence
                </button>
              )}
            </div>
          </div>


          {/* Similar Defect Warning Banner */}
          {similarDefects.length > 0 && (
            <div style={{
              margin: '0 0 0', padding: '16px 20px', borderRadius: '0',
              background: 'linear-gradient(135deg, rgba(245,158,11,0.06), rgba(239,68,68,0.04))',
              borderBottom: '1px solid rgba(245,158,11,0.15)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <span style={{ fontSize: '1.1rem' }}>⚠️</span>
                <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#92400e', textTransform: 'uppercase', letterSpacing: '.03em' }}>
                  Potential Similar Defects Found
                </span>
                {searchLoading && (
                  <svg style={{ animation: 'spin 1s linear infinite', width: 14, height: 14, marginLeft: 4 }} fill="none" stroke="#d97706" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" /></svg>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {similarDefects.map((defectItem, index) => {
                  const item = defectItem.issue || defectItem
                  const sim = defectItem.similarity || defectItem.similarity_score || 0
                  const simPercent = sim > 1 ? sim : Math.round(sim * 100)
                  const label = sim >= 0.85 ? 'Potential Duplicate' : 'Similar Defect'
                  const isDuplicate = sim >= 0.85
                  return (
                    <div key={index} style={{
                      display: 'flex', alignItems: 'center', gap: '12px',
                      padding: '10px 14px', borderRadius: '10px',
                      background: '#fff', border: `1px solid ${isDuplicate ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.15)'}`,
                    }}>
                      <span style={{
                        padding: '3px 10px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700,
                        background: isDuplicate ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)',
                        color: isDuplicate ? '#dc2626' : '#d97706',
                        flexShrink: 0,
                      }}>{simPercent}%</span>
                      <span style={{ fontWeight: 700, color: '#3b82f6', fontSize: '0.82rem', flexShrink: 0 }}>
                        {item.issue_key || '—'}
                      </span>

                      <span style={{ flex: 1, fontWeight: 500, color: '#0f172a', fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.title}
                      </span>
                      <span style={{
                        padding: '2px 8px', borderRadius: '6px',
                        background: '#f1f5f9', color: '#64748b',
                        fontSize: '0.72rem', fontWeight: 600, flexShrink: 0,
                      }}>{item.status_name || 'Unknown'}</span>
                      <span style={{
                        fontSize: '0.72rem', fontWeight: 600, flexShrink: 0,
                        color: isDuplicate ? '#dc2626' : '#d97706',
                      }}>{label}</span>
                    </div>
                  )
                })}
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
              <form id="issue-form" onSubmit={save} autoComplete="off">

                {/* Title */}
                <div className="if-title-wrap">
                  <label className="if-label if-required" style={{ marginBottom: 8, display: 'block' }}>Issue Title</label>
                  <input
                    required
                    className="if-title-input"
                    placeholder="Describe the issue in a single clear sentence…"
                    value={form.title}
                    autoComplete="off"
                    onChange={e => setForm({ ...form, title: e.target.value })}
                  />
                </div>

                {/* Classification */}
                <SectionCard icon="🏷️" title="Classification">
                  <div className="if-grid-2">
                    <FieldGroup label="Project" required hint={!isSuperAdmin && form.issue_type === 'Feature' ? 'Client feature requests are assigned to BugForge' : undefined}>
                      <SearchableSelect
                        placeholder="Select a project..."
                        options={allProjects.map(p => ({ value: p.id, label: p.name }))}
                        value={form.project_id || null}
                        isDisabled={!isSuperAdmin && form.issue_type === 'Feature'}
                        onChange={(val) => setForm({ ...form, project_id: val })}
                      />
                    </FieldGroup>
                    <FieldGroup label="Status" required>
                      {(() => {
                        const canChangeStatus = userRoles.includes('Admin') || userRoles.includes('Super Admin') || userRoles.includes('Project Manager') || userRoles.includes('Team Leader');
                        if (canChangeStatus) {
                          return (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <div style={{ flex: 1 }}>
                                <SearchableSelect
                                  placeholder="Select status..."
                                  options={statuses.map(v => ({ value: v.id, label: v.name }))}
                                  value={form.status_id || null}
                                  isDisabled={statusUpdating}
                                  isClearable={false}
                                  onChange={val => handleImmediateStatusChange(val)}
                                />
                              </div>
                              {statusUpdating && (
                                <svg style={{ animation: 'spin 1s linear infinite', width: 16, height: 16, flexShrink: 0 }} fill="none" stroke="#3b82f6" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" /></svg>
                              )}
                            </div>
                          );
                        }

                        const currentName = statuses.find(s => String(s.id) === String(form.status_id))?.name || (editing ? 'Unknown' : 'Open');
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

                        return (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', height: '44px' }}>
                            <span style={{ fontWeight: 600, color: '#334155', padding: '6px 12px', background: '#e2e8f0', borderRadius: '6px' }}>{currentName}</span>
                            {statusUpdating && (
                              <svg style={{ animation: 'spin 1s linear infinite', width: 16, height: 16 }} fill="none" stroke="#3b82f6" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" /></svg>
                            )}
                            {!statusUpdating && buttons.map(b => (
                              <button type="button" key={b.next} className={`btn btn-sm ${b.btnClass}`} onClick={() => handleImmediateStatusChange(b.next)}>{b.label}</button>
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
                          onClick={() => {
                            const newType = t.value
                            let nextProjectId = form.project_id
                            if (newType === 'Feature' && !isSuperAdmin && bugforgeProject) {
                              nextProjectId = bugforgeProject.id
                            }
                            setForm({ ...form, issue_type: newType, project_id: nextProjectId })
                          }}
                        >
                          <span>{t.icon}</span> {t.value}
                        </button>
                      ))}
                    </div>
                  </FieldGroup>

                  {isBug ? (
                    <div className="if-grid-2">
                      <FieldGroup label="Priority" required>
                        <SearchableSelect
                          placeholder="Select priority…"
                          options={priorities.map(v => ({ value: v.id, label: v.name }))}
                          value={form.priority_id || null}
                          isClearable={false}
                          onChange={val => setForm({ ...form, priority_id: val })}
                        />
                      </FieldGroup>
                      <FieldGroup label="Severity" required>
                        <SearchableSelect
                          placeholder="Select severity…"
                          options={severities.map(v => ({ value: v.id, label: v.name }))}
                          value={form.severity_id || null}
                          isClearable={false}
                          onChange={val => setForm({ ...form, severity_id: val })}
                        />
                      </FieldGroup>
                    </div>
                  ) : (
                    <div className="if-grid-1" style={{ marginBottom: '12px' }}>
                      <FieldGroup label="Priority" required hint="Set priority urgency for this task / feature">
                        <SearchableSelect
                          placeholder="Select priority…"
                          options={priorities.map(v => ({ value: v.id, label: v.name }))}
                          value={form.priority_id || null}
                          isClearable={false}
                          onChange={val => setForm({ ...form, priority_id: val })}
                        />
                      </FieldGroup>
                    </div>
                  )}

                  <div className="if-grid-2" style={{ marginBottom: '12px' }}>
                    <FieldGroup label="Category" hint="Classification area (e.g., UI, Backend, API)">
                      <SearchableSelect
                        placeholder="Select category…"
                        isClearable
                        options={categories.map(c => ({ value: c.id, label: c.name }))}
                        value={form.category_id || null}
                        onChange={val => setForm({ ...form, category_id: val })}
                      />
                    </FieldGroup>
                    <FieldGroup label="Module / Component" hint="Affected subsystem or module">
                      <SearchableSelect
                        placeholder="Select module…"
                        isClearable
                        options={modules.map(m => ({ value: m.id, label: m.name }))}
                        value={form.module_id || null}
                        onChange={val => setForm({ ...form, module_id: val })}
                      />
                    </FieldGroup>
                  </div>
                  
                  <div className="if-grid-2" style={{ marginBottom: '12px' }}>
                    <FieldGroup label="Assign Developer" hint="Developer who should resolve this issue">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ flex: 1 }}>
                          <SearchableSelect
                            placeholder="Unassigned Developer"
                            isClearable
                            options={allUsers.filter(u => u.roles && u.roles.some(r => r.name === 'Developer')).map(u => ({ value: u.id, label: u.full_name }))}
                            value={form.assigned_to || null}
                            isDisabled={assigneeUpdating || userRoles.includes('Developer') || userRoles.includes('QA') || userRoles.includes('Reporter')}
                            onChange={val => handleImmediateAssigneeChange(val)}
                          />
                        </div>
                        {assigneeUpdating && (
                          <svg style={{ animation: 'spin 1s linear infinite', width: 16, height: 16, flexShrink: 0 }} fill="none" stroke="#3b82f6" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" /></svg>
                        )}
                      </div>
                    </FieldGroup>
                    <FieldGroup label="Assign QA" hint="QA engineer to test and verify the fix">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ flex: 1 }}>
                          <SearchableSelect
                            placeholder="Unassigned QA"
                            isClearable
                            options={allUsers.filter(u => u.roles && u.roles.some(r => r.name === 'QA')).map(u => ({ value: u.id, label: u.full_name }))}
                            value={form.assigned_qa_id || null}
                            isDisabled={qaAssigneeUpdating || userRoles.includes('Developer') || userRoles.includes('Reporter')}
                            onChange={val => handleImmediateQaAssigneeChange(val)}
                          />
                        </div>
                        {qaAssigneeUpdating && (
                          <svg style={{ animation: 'spin 1s linear infinite', width: 16, height: 16, flexShrink: 0 }} fill="none" stroke="#3b82f6" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" /></svg>
                        )}
                      </div>
                    </FieldGroup>
                  </div>

                  <div className="if-grid-2">
                    <FieldGroup label="Sprint" hint="Assign this issue to an active sprint.">
                      <SearchableSelect
                        placeholder="No sprint - Backlog"
                        isClearable
                        options={projectSprints.map(s => ({ value: s.id, label: s.name }))}
                        value={form.sprint_id || null}
                        isDisabled={userRoles.includes('Developer') || userRoles.includes('QA') || userRoles.includes('Reporter')}
                        onChange={val => setForm({ ...form, sprint_id: val })}
                      />
                    </FieldGroup>
                  </div>
                </SectionCard>

                {/* Feature Engineering & Workflow Lifecycle Section */}
                {(form.issue_type === 'Feature' || editing?.issue_type === 'Feature' || editing?.requesting_company_name) && (
                  <SectionCard icon="🚀" title="Feature Engineering & Lifecycle">
                    {editing?.requesting_company_name && (
                      <div className="p-3 mb-3 border rounded-3 text-xs d-flex align-items-center justify-content-between" style={{ backgroundColor: '#eff6ff', borderColor: '#bfdbfe' }}>
                        <div className="d-flex align-items-center gap-2">
                          <i className="bi bi-building text-primary font-bold" />
                          <span className="text-slate-800">
                            <strong>Requesting Organization:</strong> <span className="badge bg-primary px-2 py-0.5 ms-1">{editing.requesting_company_name}</span>
                          </span>
                        </div>
                        {editing.reporter_name && (
                          <span className="text-slate-600">
                            Requested by: <strong>{editing.reporter_name}</strong>
                          </span>
                        )}
                      </div>
                    )}

                    <div className="if-grid-2">
                      {/* Internal Team Assignment */}
                      <FieldGroup label="Assigned Internal Team" hint="BugForge squad responsible for implementation">
                        {userRoles.includes('Super Admin') ? (
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <div style={{ flex: 1 }}>
                              <SearchableSelect
                                placeholder="Select internal squad..."
                                isClearable
                                options={internalTeams.map(t => ({ value: t.id, label: t.name }))}
                                value={selectedTeamId || null}
                                isDisabled={assigningTeam}
                                onChange={val => setSelectedTeamId(val || '')}
                              />
                            </div>
                            <button
                              type="button"
                              className="btn btn-sm btn-primary flex-shrink-0"
                              onClick={handleAssignTeam}
                              disabled={assigningTeam || !selectedTeamId || String(selectedTeamId) === String(editing?.team_id)}
                            >
                              {assigningTeam ? 'Assigning...' : 'Assign Team'}
                            </button>
                          </div>
                        ) : (
                          <div className="p-2.5 bg-light rounded border text-sm font-semibold text-slate-800">
                            {editing?.team_name ? `👥 ${editing.team_name}` : 'Unassigned to squad'}
                          </div>
                        )}
                      </FieldGroup>

                      {/* QA Verification State */}
                      <FieldGroup label="QA Verification State" hint="Quality assurance sign-off status">
                        <div className="d-flex align-items-center gap-2" style={{ height: '44px' }}>
                          <span
                            className="badge px-3 py-2 text-xs font-semibold"
                            style={{
                              backgroundColor:
                                editing?.qa_state === 'Passed'
                                  ? '#10b981'
                                  : editing?.qa_state === 'Requires Rework'
                                  ? '#ef4444'
                                  : '#f59e0b',
                              color: '#fff',
                            }}
                          >
                            {editing?.qa_state || 'Pending Verification'}
                          </span>
                          {editing?.qa_verified_by_name && (
                            <span className="text-muted text-xs">
                              Verified by {editing.qa_verified_by_name}
                            </span>
                          )}
                        </div>
                      </FieldGroup>
                    </div>

                    {/* QA Actions for authorized roles */}
                    {editing && (userRoles.includes('QA') || userRoles.includes('Super Admin') || userRoles.includes('Admin') || userRoles.includes('Project Manager') || userRoles.includes('Team Leader')) && (
                      <div className="mt-3 p-3 bg-light rounded-3 border">
                        <label className="text-xs font-semibold text-slate-700 mb-1.5 d-block">
                          QA Sign-off & Verification Decision
                        </label>
                        <div className="mb-2">
                          <input
                            type="text"
                            className="form-control form-control-sm text-xs"
                            placeholder="Add QA test verification notes or rework instructions..."
                            value={qaNotes}
                            onChange={(e) => setQaNotes(e.target.value)}
                          />
                        </div>
                        <div className="d-flex gap-2">
                          <button
                            type="button"
                            className="btn btn-sm btn-success text-xs font-semibold d-flex align-items-center gap-1.5 shadow-sm"
                            onClick={() => handleQAVerify('Passed')}
                            disabled={qaVerifying}
                          >
                            <i className="bi bi-check-circle" />
                            <span>{qaVerifying ? 'Verifying...' : 'Approve & Verify (Passed)'}</span>
                          </button>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-danger text-xs font-semibold d-flex align-items-center gap-1.5 shadow-sm"
                            onClick={() => handleQAVerify('Requires Rework')}
                            disabled={qaVerifying}
                          >
                            <i className="bi bi-arrow-counterclockwise" />
                            <span>{qaVerifying ? 'Updating...' : 'Request Rework'}</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </SectionCard>
                )}

                {/* Description */}
                <SectionCard icon={isBug ? "📝" : "📋"} title={isBug ? "Description" : "Details & Description"}>
                  <FieldGroup label="Summary" required hint={isBug ? "Minimum 20 characters. Be specific about what is broken and where." : "Provide complete requirements or task definition."}>
                    <textarea
                      required className="if-textarea"
                      placeholder={isBug ? "Provide a clear, concise explanation of the issue…" : "Describe the goals, requirements, or scope…"}
                      rows={4}
                      value={form.description}
                      onChange={e => setForm({ ...form, description: e.target.value })}
                    />
                  </FieldGroup>

                  {isBug && (
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
                  )}
                  
                  {isBug && editing && (form.root_cause || form.resolution || ['Resolved', 'Closed'].includes(statuses.find(s => String(s.id) === String(form.status_id))?.name)) && (
                    <div style={{
                      marginTop: '16px',
                      padding: '16px 18px', borderRadius: '12px',
                      background: 'linear-gradient(135deg, rgba(16,185,129,0.06) 0%, rgba(59,130,246,0.04) 100%)',
                      border: '1px solid rgba(16,185,129,0.22)',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                        <span style={{ fontSize: '1.1rem' }}>🛡️</span>
                        <span style={{ fontWeight: 700, fontSize: '0.88rem', color: '#065f46' }}>Resolution Documentation</span>
                        <span style={{
                          marginLeft: 'auto', fontSize: '0.72rem', fontWeight: 700,
                          padding: '2px 8px', borderRadius: '6px',
                          background: '#d1fae5', color: '#047857'
                        }}>
                          {statuses.find(s => String(s.id) === String(form.status_id))?.name || 'Resolved'}
                        </span>
                      </div>
                      <div className="if-grid-2">
                        <FieldGroup label="Root Cause" hint="Technical reason for the defect">
                          <textarea className="if-textarea" placeholder="Describe the underlying cause of the defect..." rows={3}
                            value={form.root_cause} onChange={e => setForm({ ...form, root_cause: e.target.value })} />
                        </FieldGroup>
                        <FieldGroup label="Resolution Fix Details" hint="How this defect was resolved">
                          <textarea className="if-textarea" placeholder="Describe how the defect was resolved..." rows={3}
                            value={form.resolution} onChange={e => setForm({ ...form, resolution: e.target.value })} />
                        </FieldGroup>
                      </div>
                    </div>
                  )}

                  {isBug && editing && !form.root_cause && !form.resolution && !['Resolved', 'Closed'].includes(statuses.find(s => String(s.id) === String(form.status_id))?.name) && (
                    <div className="if-grid-2" style={{ marginTop: '16px' }}>
                      <FieldGroup label="Root Cause (Optional)">
                        <textarea className="if-textarea" placeholder="Describe the underlying cause of the defect..." rows={3}
                          value={form.root_cause} onChange={e => setForm({ ...form, root_cause: e.target.value })} />
                      </FieldGroup>
                      <FieldGroup label="Resolution (Optional)">
                        <textarea className="if-textarea" placeholder="Describe how the defect was resolved..." rows={3}
                          value={form.resolution} onChange={e => setForm({ ...form, resolution: e.target.value })} />
                      </FieldGroup>
                    </div>
                  )}
                </SectionCard>

                {/* Environment */}
                {isBug && (
                  <SectionCard icon="🌐" title="Environment">
                    <div className="if-grid-2">
                      <FieldGroup label="Environment" hint="e.g. Production, Staging, Dev">
                        <input className="if-input" placeholder="Production" value={form.environment} autoComplete="off" onChange={e => setForm({ ...form, environment: e.target.value })} />
                      </FieldGroup>
                      <FieldGroup label="Browser / Device" hint="e.g. Chrome 115, iPhone 14 Pro">
                        <input className="if-input" placeholder="Chrome 115" value={form.browser} autoComplete="off" onChange={e => setForm({ ...form, browser: e.target.value })} />
                      </FieldGroup>
                    </div>
                  </SectionCard>
                )}


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
                              ? <img className="att-thumb" src={`${att.file_path}`} alt={att.filename} />
                              : <div className="att-icon">{fileExt === 'PDF' ? '📄' : fileExt === 'MP4' || fileExt === 'MOV' ? '🎥' : fileExt === 'ZIP' ? '🗜️' : '📁'}</div>
                            }
                            <div className="att-name">{att.filename}</div>
                            {sizeKb && <div className="att-size">{sizeKb}</div>}
                            <a className="att-link" href={`${att.file_path}`} target="_blank" rel="noreferrer">Open ↗</a>
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
                {/* Similar Defects Panel */}
                {detailSimilarLoading ? (
                  <div className="if-resolution-assistant-card" style={{ marginBottom: '16px' }}>
                    <div className="if-resolution-assistant-header">
                      <span className="if-resolution-assistant-icon">🔗</span>
                      <span className="if-resolution-assistant-title">Similar Defects</span>
                    </div>
                    <div className="if-resolution-assistant-body" style={{ padding: '16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '0.85rem' }}>
                        <svg style={{ animation: 'spin 1s linear infinite', width: 14, height: 14 }} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" /></svg>
                        Finding similar defects…
                      </div>
                    </div>
                  </div>
                ) : detailSimilarDefects.length > 0 ? (
                  <div className="if-resolution-assistant-card" style={{ marginBottom: '16px' }}>
                    <div className="if-resolution-assistant-header">
                      <span className="if-resolution-assistant-icon">🔗</span>
                      <span className="if-resolution-assistant-title">Similar Defects ({detailSimilarDefects.length})</span>
                    </div>
                    <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {detailSimilarDefects.map(sim => {
                        const isDuplicate = sim.similarity_label === 'Potential Duplicate'
                        return (
                          <div key={sim.id} style={{
                            padding: '10px 12px', borderRadius: '10px',
                            border: `1px solid ${isDuplicate ? 'rgba(239,68,68,0.15)' : 'rgba(15,23,42,0.07)'}`,
                            background: isDuplicate ? 'rgba(239,68,68,0.02)' : '#fff',
                            cursor: 'pointer', transition: 'all .2s',
                          }}
                          onClick={async () => { 
                            try {
                               const res = await getIssue(sim.id);
                               if (res.data) open(res.data);
                            } catch (e) {
                               console.error("Failed to open similar issue", e);
                            }
                          }}
                          onMouseEnter={e => e.currentTarget.style.boxShadow = '0 2px 8px rgba(15,23,42,0.06)'}
                          onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                              <span style={{
                                padding: '2px 8px', borderRadius: '5px', fontSize: '0.7rem', fontWeight: 700,
                                background: isDuplicate ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)',
                                color: isDuplicate ? '#dc2626' : '#d97706',
                              }}>{sim.similarity_percent}%</span>
                              <span style={{ fontWeight: 700, color: '#3b82f6', fontSize: '0.78rem' }}>{sim.issue_key}</span>
                              <span style={{
                                marginLeft: 'auto', padding: '1px 6px', borderRadius: '4px',
                                background: '#f1f5f9', color: '#64748b', fontSize: '0.68rem', fontWeight: 600,
                              }}>{sim.status_name}</span>
                            </div>
                            <div style={{ fontSize: '0.82rem', fontWeight: 500, color: '#0f172a', lineHeight: 1.4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {sim.title}
                            </div>
                            <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                              {sim.severity_name && <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Severity: {sim.severity_name}</span>}
                              {sim.priority_name && <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Priority: {sim.priority_name}</span>}
                            </div>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: isDuplicate ? '#dc2626' : '#d97706', marginTop: '4px' }}>
                              {sim.similarity_label}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ) : null}

                {/* AI Test Intelligence Card */}
                {showTestIntelligence && canAccessTestIntelligence && (
                  <AITestIntelligence 
                    issueId={editing.id} 
                    onClose={() => setShowTestIntelligence(false)} 
                  />
                )}


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
                      {/* AI Root-Cause Analysis (if available on the issue) */}
                      {resolutionAssistanceData.ai_root_cause && (
                        <div className="if-resolution-assistant-section" style={{
                          marginBottom: '24px', padding: '16px', borderRadius: '12px',
                          background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)',
                          border: '1px solid #bbf7d0'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                            <span style={{ fontSize: '1.2rem' }}>🎯</span>
                            <h4 style={{ margin: 0, color: '#166534', letterSpacing: '0.05em' }}>AI Root Cause Analysis</h4>
                          </div>
                          
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                            <span style={{ fontWeight: 600, color: '#166534', fontSize: '0.85rem' }}>
                              Status: <span style={{ textTransform: 'capitalize' }}>{resolutionAssistanceData.ai_root_cause.status.replace('_', ' ')}</span>
                            </span>
                            <span style={{ fontWeight: 600, color: '#166534', fontSize: '0.85rem' }}>
                              Confidence: {Math.round(resolutionAssistanceData.ai_root_cause.confidence * 100)}%
                            </span>
                          </div>

                          <div style={{ marginBottom: '12px' }}>
                            <strong style={{ display: 'block', color: '#15803d', fontSize: '0.85rem', marginBottom: '4px' }}>Identified Cause:</strong>
                            <div style={{ color: '#14532d', fontSize: '0.95rem', lineHeight: 1.5 }}>
                              {resolutionAssistanceData.ai_root_cause.root_cause}
                            </div>
                          </div>

                          {resolutionAssistanceData.ai_root_cause.evidence && resolutionAssistanceData.ai_root_cause.evidence.length > 0 && (
                            <div style={{ marginBottom: '12px' }}>
                              <strong style={{ display: 'block', color: '#15803d', fontSize: '0.85rem', marginBottom: '4px' }}>Evidence:</strong>
                              <ul style={{ margin: 0, paddingLeft: '20px', color: '#14532d', fontSize: '0.9rem' }}>
                                {resolutionAssistanceData.ai_root_cause.evidence.map((ev, i) => <li key={i}>{ev}</li>)}
                              </ul>
                            </div>
                          )}

                          {resolutionAssistanceData.ai_root_cause.recommended_fix && (
                            <div>
                              <strong style={{ display: 'block', color: '#15803d', fontSize: '0.85rem', marginBottom: '4px' }}>Recommended Fix:</strong>
                              <div style={{ color: '#14532d', fontSize: '0.9rem', lineHeight: 1.5 }}>
                                {resolutionAssistanceData.ai_root_cause.recommended_fix}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {resolutionAssistanceData.historical_resolutions && resolutionAssistanceData.historical_resolutions.length > 0 && (
                        <div className="if-resolution-assistant-section">
                          <h4>Historical Resolutions</h4>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {resolutionAssistanceData.historical_resolutions.map((hr, idx) => (
                              <div key={idx} style={{ padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                  <span style={{ fontWeight: 600, color: '#3b82f6', fontSize: '0.85rem' }}>{hr.defect_id}</span>
                                  <span style={{ fontWeight: 600, color: '#64748b', fontSize: '0.75rem' }}>Similarity: {Math.round(hr.similarity_score * 100)}%</span>
                                </div>
                                <div style={{ marginBottom: '6px', fontSize: '0.85rem' }}>
                                  <strong>Root Cause:</strong> {hr.root_cause || 'N/A'}
                                </div>
                                <div style={{ marginBottom: '6px', fontSize: '0.85rem' }}>
                                  <strong>Resolution:</strong> {hr.resolution || 'N/A'}
                                </div>
                                {hr.relevant_comments && hr.relevant_comments.length > 0 && (
                                  <div style={{ fontSize: '0.8rem', color: '#475569', fontStyle: 'italic', background: '#fff', padding: '8px', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                                    <strong>Comment:</strong> "{hr.relevant_comments[0]}"
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      <div className="if-resolution-assistant-section">
                        <h4>Investigation Areas</h4>
                        <ul>
                          {resolutionAssistanceData.investigation_areas.map((area, index) => (
                            <li key={index}>{area}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="if-resolution-assistant-section">
                        <h4>Possible Causes</h4>
                        <ul>
                          {resolutionAssistanceData.possible_causes.map((cause, index) => (
                            <li key={index}>{cause}</li>
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
                <IssueTimeline 
                  issueId={editing.id} 
                  lookups={{ statuses, priorities, severities, categories, modules, allProjects, allUsers, projectSprints }} 
                />
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

      {/* Resolve Defect Modal */}
      {showResolveModal && (
        <Modal
          title={`Resolve Defect — ${editing?.issue_key || 'Issue'}`}
          primaryLabel={resolving ? 'Saving Resolution…' : 'Confirm & Mark as Resolved'}
          secondaryLabel="Cancel"
          onPrimary={handleConfirmResolve}
          onSecondary={() => setShowResolveModal(false)}
          onClose={() => setShowResolveModal(false)}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <p style={{ margin: 0, fontSize: '0.88rem', color: '#475569', lineHeight: 1.5 }}>
              Documenting the <strong>Root Cause</strong> and <strong>Resolution</strong> enables the AI assistance engine to intelligently guide future developers when similar defects arise.
            </p>
            
            {resolveError && (
              <div style={{ padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#dc2626', fontSize: '0.84rem' }}>
                {resolveError}
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: '0.84rem', color: '#1e293b', marginBottom: '4px' }}>
                Root Cause <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <textarea
                className="if-textarea"
                rows={3}
                placeholder="Explain the underlying technical cause (e.g. Unhandled null pointer in payment callback handler)..."
                value={resolveForm.root_cause}
                onChange={e => setResolveForm({ ...resolveForm, root_cause: e.target.value })}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: '0.84rem', color: '#1e293b', marginBottom: '4px' }}>
                Resolution Details <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <textarea
                className="if-textarea"
                rows={3}
                placeholder="Describe how the defect was resolved (e.g. Added null-check guard and fallback retry logic)..."
                value={resolveForm.resolution}
                onChange={e => setResolveForm({ ...resolveForm, resolution: e.target.value })}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: '0.84rem', color: '#64748b', marginBottom: '4px' }}>
                Resolution Comment (Optional)
              </label>
              <input
                className="if-input"
                placeholder="e.g. Fix merged into main branch under PR #142"
                value={resolveForm.comment}
                autoComplete="off"
                onChange={e => setResolveForm({ ...resolveForm, comment: e.target.value })}
              />
            </div>
          </div>
        </Modal>
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
      {/* Troubleshooting Modal */}
      {showTroubleshootingModal && (
        <TroubleshootingModal
          payload={troubleshootingPayload}
          onConfirm={handleTroubleshootingConfirm}
          onSkip={handleTroubleshootingSkip}
          onClose={() => setShowTroubleshootingModal(false)}
        />
      )}

      {/* Quick Assign Squad Modal (Super Admin) */}
      {quickAssignIssue && (
        <Modal
          title="Assign Customer Request to Internal Squad"
          onClose={() => { setQuickAssignIssue(null); setQuickTeamId('') }}
        >
          <div className="p-1">
            <div className="p-3 mb-3 border rounded-3 bg-light text-xs">
              <div className="d-flex align-items-center justify-content-between mb-2">
                <span className="badge bg-primary px-2 py-1 font-mono">
                  {quickAssignIssue.issue_key || 'Customer Request'}
                </span>

                <span className="badge bg-secondary-subtle text-secondary border">
                  {quickAssignIssue.status_name}
                </span>
              </div>
              <h6 className="font-bold text-slate-900 mb-1" style={{ fontSize: '0.95rem' }}>
                {quickAssignIssue.title}
              </h6>
              {quickAssignIssue.requesting_company_name && (
                <div className="text-muted d-flex align-items-center gap-1.5 mt-1.5">
                  <i className="bi bi-building text-primary" />
                  <span>Requesting Organization: <strong className="text-slate-800">{quickAssignIssue.requesting_company_name}</strong></span>
                </div>
              )}
              {quickAssignIssue.team_name && (
                <div className="text-muted d-flex align-items-center gap-1.5 mt-1">
                  <i className="bi bi-diagram-3 text-indigo-600" />
                  <span>Currently Assigned: <strong className="text-primary">{quickAssignIssue.team_name}</strong></span>
                </div>
              )}
            </div>

            <div className="mb-3">
              <label className="form-label text-sm font-semibold text-slate-800 mb-1">
                Select Internal BugForge Squad <span className="text-danger">*</span>
              </label>
              <SearchableSelect
                placeholder="Choose internal engineering squad..."
                isClearable
                options={internalTeams.map(t => ({ value: t.id, label: t.name }))}
                value={quickTeamId || null}
                isDisabled={assigningTeam}
                onChange={val => setQuickTeamId(val || '')}
              />
              <p className="text-xs text-muted mt-1.5 mb-0">
                <i className="bi bi-info-circle me-1" />
                Assigning an internal squad transitions the feature to <strong>Assigned</strong> and automatically alerts the squad's Project Manager & Team Leader.
              </p>
            </div>

            <div className="d-flex justify-content-end gap-2 pt-3 border-top">
              <button
                type="button"
                className="btn btn-sm btn-light border"
                onClick={() => { setQuickAssignIssue(null); setQuickTeamId('') }}
                disabled={assigningTeam}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-sm btn-primary d-flex align-items-center gap-1.5"
                disabled={assigningTeam || !quickTeamId || String(quickTeamId) === String(quickAssignIssue.team_id)}
                onClick={async () => {
                  setAssigningTeam(true)
                  try {
                    const res = await assignIssueTeam(quickAssignIssue.id, { team_id: Number(quickTeamId) })
                    const updated = res.data
                    const assignedTeam = internalTeams.find(t => String(t.id) === String(quickTeamId))
                    const teamName = assignedTeam ? assignedTeam.name : (updated.team_name || 'the squad')
                    setIssues(prev => prev.map(iss => iss.id === quickAssignIssue.id ? {
                      ...iss,
                      team_id: updated.team_id,
                      team_name: updated.team_name,
                      status_id: updated.status_id,
                      status_name: updated.status_name,
                    } : iss))
                    const requestTitle = quickAssignIssue.title
                    setQuickAssignIssue(null)
                    setQuickTeamId('')
                    setToast({
                      message: `Customization request "${requestTitle}" assigned to squad "${teamName}" successfully.`,
                      variant: 'success'
                    })
                  } catch (err) {
                    const errorMsg = extractErrorMessage(err, 'Failed to assign squad.')
                    setToast({ message: errorMsg, variant: 'error' })
                  } finally {
                    setAssigningTeam(false)
                  }
                }}
              >
                {assigningTeam ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status" />
                    <span>Assigning Squad...</span>
                  </>
                ) : (
                  <>
                    <i className="bi bi-check-lg" />
                    <span>Confirm Squad Assignment</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Global Toast Notification */}
      <Toast
        message={toast.message}
        variant={toast.variant}
        onClose={() => setToast({ message: '', variant: 'success' })}
      />
    </>
  )
}