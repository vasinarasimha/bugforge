import { useState, useEffect, useMemo } from 'react'
import {
  getTeams,
  getTeam,
  createTeam,
  updateTeam,
  deactivateTeam,
  getAvailableLeaders,
  getAvailableMembers,
  getTeamStats,
} from '../../services/teamService'

export default function TeamManagementPage() {
  const [teams, setTeams] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all') // 'all', 'active', 'inactive'

  // Team Insights stats
  const [teamStats, setTeamStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)

  // View state: 'list' | 'edit'
  const [viewMode, setViewMode] = useState('list')
  const [selectedTeam, setSelectedTeam] = useState(null)

  // Meta data for dropdowns
  const [availableLeaders, setAvailableLeaders] = useState([])
  const [availableMembers, setAvailableMembers] = useState([])
  const [memberSearch, setMemberSearch] = useState('')

  // Form State for Create & Edit
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    team_leader_id: '',
    project_manager_id: '',
    member_ids: [],
    is_active: true,
  })
  const [formErrors, setFormErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showViewModal, setShowViewModal] = useState(false)
  const [showDeactivateModal, setShowDeactivateModal] = useState(false)

  // Toast alerts
  const [toast, setToast] = useState(null)

  // Load team insights statistics (Total Users, Total Teams, Assigned, Unassigned)
  const fetchStats = async () => {
    setStatsLoading(true)
    try {
      const res = await getTeamStats()
      setTeamStats(res.data || null)
    } catch (err) {
      console.error('Failed to load team stats:', err)
    } finally {
      setStatsLoading(false)
    }
  }

  // Load all teams
  const fetchTeams = async () => {
    setLoading(true)
    try {
      const res = await getTeams()
      setTeams(res.data || [])
    } catch (err) {
      console.error('Failed to load teams:', err)
      setToast({ message: 'Failed to load teams from server.', variant: 'danger' })
    } finally {
      setLoading(false)
    }
  }

  // Load available TLs and members
  const fetchMeta = async (excludeTeamId = null) => {
    try {
      const [leadersRes, membersRes] = await Promise.all([
        getAvailableLeaders(excludeTeamId),
        getAvailableMembers(),
      ])
      setAvailableLeaders(leadersRes.data || [])
      setAvailableMembers(membersRes.data || [])
    } catch (err) {
      console.error('Failed to load team metadata:', err)
    }
  }

  useEffect(() => {
    fetchTeams()
    fetchMeta()
    fetchStats()
  }, [])

  // Auto-dismiss toast after 4 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  // Filtered teams list
  const filteredTeams = useMemo(() => {
    return teams.filter((t) => {
      const matchesSearch =
        searchQuery === '' ||
        t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.description && t.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (t.team_leader?.full_name &&
          t.team_leader.full_name.toLowerCase().includes(searchQuery.toLowerCase()))

      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && t.is_active) ||
        (statusFilter === 'inactive' && !t.is_active)

      return matchesSearch && matchesStatus
    })
  }, [teams, searchQuery, statusFilter])

  // PM list derived from available employees (or any active user with PM role)
  const pmOptions = useMemo(() => {
    return availableMembers.filter((m) => m.role === 'Project Manager')
  }, [availableMembers])

  // Filter available members in member selector search
  const filteredAvailableMembers = useMemo(() => {
    if (!memberSearch.trim()) return availableMembers
    const q = memberSearch.toLowerCase()
    return availableMembers.filter(
      (m) =>
        m.full_name.toLowerCase().includes(q) ||
        m.email.toLowerCase().includes(q) ||
        m.role.toLowerCase().includes(q) ||
        (m.department && m.department.toLowerCase().includes(q)),
    )
  }, [availableMembers, memberSearch])

  // Open Create Modal
  const handleOpenCreate = () => {
    fetchMeta(null)
    setFormData({
      name: '',
      description: '',
      team_leader_id: '',
      project_manager_id: '',
      member_ids: [],
      is_active: true,
    })
    setFormErrors({})
    setMemberSearch('')
    setShowCreateModal(true)
  }

  // Switch to Full Main Content Edit View
  const handleOpenEdit = (team) => {
    setSelectedTeam(team)
    fetchMeta(team.id)
    const existingMemberIds = (team.members || []).map((m) => m.user_id)
    setFormData({
      name: team.name || '',
      description: team.description || '',
      team_leader_id: team.team_leader_id ? String(team.team_leader_id) : '',
      project_manager_id: team.project_manager_id ? String(team.project_manager_id) : '',
      member_ids: existingMemberIds,
      is_active: team.is_active ?? true,
    })
    setFormErrors({})
    setMemberSearch('')
    setViewMode('edit')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Back to list view
  const handleBackToList = () => {
    setViewMode('list')
    setSelectedTeam(null)
    setFormErrors({})
  }

  // Open View Modal
  const handleOpenView = async (team) => {
    setSelectedTeam(team)
    setShowViewModal(true)
    try {
      const res = await getTeam(team.id)
      setSelectedTeam(res.data)
    } catch {
      // fallback to existing team object
    }
  }

  // Open Deactivate Modal
  const handleOpenDeactivate = (team) => {
    setSelectedTeam(team)
    setShowDeactivateModal(true)
  }

  // Toggle member assignment
  const handleToggleMember = (userId) => {
    setFormData((prev) => {
      const current = prev.member_ids || []
      if (current.includes(userId)) {
        return { ...prev, member_ids: current.filter((id) => id !== userId) }
      } else {
        return { ...prev, member_ids: [...current, userId] }
      }
    })
  }

  // Submit Create Team
  const handleCreateSubmit = async (e) => {
    e.preventDefault()
    setFormErrors({})
    setIsSubmitting(true)

    const errors = {}
    if (!formData.name || formData.name.trim().length < 2) {
      errors.name = 'Team name must be at least 2 characters.'
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      setIsSubmitting(false)
      return
    }

    try {
      const payload = {
        name: formData.name.trim(),
        description: formData.description?.trim() || null,
        team_leader_id: formData.team_leader_id ? Number(formData.team_leader_id) : null,
        project_manager_id: formData.project_manager_id ? Number(formData.project_manager_id) : null,
        member_ids: formData.member_ids,
        is_active: formData.is_active,
      }

      await createTeam(payload)
      setShowCreateModal(false)
      setToast({ message: `Team '${formData.name}' created successfully!`, variant: 'success' })
      fetchTeams()
      fetchMeta()
      fetchStats()
    } catch (err) {
      const detail = err.response?.data?.detail
      let errorMsg = 'Failed to create team.'
      if (Array.isArray(detail)) {
        errorMsg = detail.map((d) => d.msg).join(', ')
      } else if (typeof detail === 'string') {
        errorMsg = detail
      }
      setToast({ message: errorMsg, variant: 'danger' })
    } finally {
      setIsSubmitting(false)
    }
  }

  // Submit Edit Team
  const handleEditSubmit = async (e) => {
    e.preventDefault()
    setFormErrors({})
    setIsSubmitting(true)

    if (!formData.name || formData.name.trim().length < 2) {
      setFormErrors({ name: 'Team name must be at least 2 characters.' })
      setIsSubmitting(false)
      return
    }

    try {
      const payload = {
        name: formData.name.trim(),
        description: formData.description?.trim() || null,
        team_leader_id: formData.team_leader_id ? Number(formData.team_leader_id) : null,
        project_manager_id: formData.project_manager_id ? Number(formData.project_manager_id) : null,
        member_ids: formData.member_ids,
        is_active: formData.is_active,
      }

      await updateTeam(selectedTeam.id, payload)
      setToast({ message: `Team '${formData.name}' updated successfully!`, variant: 'success' })
      setViewMode('list')
      fetchTeams()
      fetchMeta()
      fetchStats()
    } catch (err) {
      const detail = err.response?.data?.detail
      let errorMsg = 'Failed to update team.'
      if (Array.isArray(detail)) {
        errorMsg = detail.map((d) => d.msg).join(', ')
      } else if (typeof detail === 'string') {
        errorMsg = detail
      }
      setToast({ message: errorMsg, variant: 'danger' })
    } finally {
      setIsSubmitting(false)
    }
  }

  // Confirm Deactivation
  const handleConfirmDeactivate = async () => {
    if (!selectedTeam) return
    setIsSubmitting(true)
    try {
      await deactivateTeam(selectedTeam.id)
      setShowDeactivateModal(false)
      setToast({ message: `Team '${selectedTeam.name}' deactivated.`, variant: 'warning' })
      fetchTeams()
      fetchMeta()
      fetchStats()
    } catch (err) {
      setToast({
        message: err.response?.data?.detail || 'Failed to deactivate team.',
        variant: 'danger',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  // ─────────────────────────────────────────────────────────────
  // RENDER: FULL MAIN CONTENT EDIT VIEW
  // ─────────────────────────────────────────────────────────────
  if (viewMode === 'edit' && selectedTeam) {
    return (
      <div className="container-fluid py-4" style={{ maxWidth: '1200px' }}>
        {/* Toast Alert */}
        {toast && (
          <div
            className={`alert alert-${toast.variant} alert-dismissible fade show shadow-sm mb-4`}
            role="alert"
          >
            <strong>{toast.message}</strong>
            <button type="button" className="btn-close" onClick={() => setToast(null)} />
          </div>
        )}

        {/* Top Breadcrumb Navigation */}
        <div className="d-flex align-items-center justify-content-between mb-4">
          <button
            type="button"
            className="btn btn-outline-secondary d-inline-flex align-items-center gap-2"
            onClick={handleBackToList}
            style={{ borderRadius: '10px' }}
          >
            <i className="bi bi-arrow-left" />
            <span>Back to Team Management</span>
          </button>

          <div className="d-flex align-items-center gap-2">
            <span
              className={`badge px-3 py-2 ${
                formData.is_active
                  ? 'bg-success-subtle text-success border border-success'
                  : 'bg-secondary-subtle text-secondary border'
              }`}
              style={{ borderRadius: '20px', fontSize: '0.85rem' }}
            >
              {formData.is_active ? '● Active Team' : '○ Inactive Team'}
            </span>
          </div>
        </div>

        {/* Main Edit Form */}
        <form onSubmit={handleEditSubmit} autoComplete="off">
          <div className="row g-4">
            {/* Left Column: Team Details & Leadership */}
            <div className="col-12 col-lg-7">
              <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
                  <h5 className="fw-bold mb-1 d-flex align-items-center gap-2 text-dark">
                    <i className="bi bi-diagram-3-fill text-primary" />
                    Team Information
                  </h5>
                  <p className="text-muted small mb-0">General details and leadership assignments.</p>
                </div>
                <div className="card-body px-4 pb-4">
                  <div className="row g-3">
                    <div className="col-12">
                      <label className="form-label fw-medium small">
                        Team Name <span className="text-danger">*</span>
                      </label>
                      <input
                        type="text"
                        className={`form-control ${formErrors.name ? 'is-invalid' : ''}`}
                        placeholder="e.g. Core Engineering, Mobile Guild, DevOps Team"
                        value={formData.name}
                        autoComplete="off"
                        onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                        style={{ borderRadius: '8px', height: '42px' }}
                      />
                      {formErrors.name && (
                        <div className="invalid-feedback">{formErrors.name}</div>
                      )}
                    </div>

                    <div className="col-12">
                      <label className="form-label fw-medium small">Description</label>
                      <textarea
                        className="form-control"
                        rows={3}
                        placeholder="Purpose, responsibilities, and scope of this team..."
                        value={formData.description}
                        autoComplete="off"
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, description: e.target.value }))
                        }
                        style={{ borderRadius: '8px' }}
                      />
                    </div>

                    {/* Team Leader Assignment (Unique constraint note) */}
                    <div className="col-12 col-md-6">
                      <label className="form-label fw-medium small d-flex justify-content-between">
                        <span>Team Leader</span>
                        <span className="text-muted" style={{ fontSize: '0.75rem' }}>1 team max</span>
                      </label>
                      <select
                        className="form-select"
                        value={formData.team_leader_id}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, team_leader_id: e.target.value }))
                        }
                        style={{ borderRadius: '8px', height: '42px' }}
                      >
                        <option value="">-- No Team Leader Assigned --</option>
                        {/* Include current assigned leader if editing */}
                        {selectedTeam.team_leader && (
                          <option value={selectedTeam.team_leader.id}>
                            {selectedTeam.team_leader.full_name} ({selectedTeam.team_leader.email}) [Current]
                          </option>
                        )}
                        {availableLeaders
                          .filter((l) => l.id !== selectedTeam.team_leader_id)
                          .map((l) => (
                            <option key={l.id} value={l.id}>
                              {l.full_name} ({l.email})
                            </option>
                          ))}
                      </select>
                      <small className="text-muted d-block mt-1" style={{ fontSize: '0.75rem' }}>
                        A Team Leader can lead only ONE team across the organization.
                      </small>
                    </div>

                    {/* Project Manager Assignment (Multiple teams allowed) */}
                    <div className="col-12 col-md-6">
                      <label className="form-label fw-medium small d-flex justify-content-between">
                        <span>Project Manager (PM)</span>
                        <span className="text-muted" style={{ fontSize: '0.75rem' }}>Multi-team OK</span>
                      </label>
                      <select
                        className="form-select"
                        value={formData.project_manager_id}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, project_manager_id: e.target.value }))
                        }
                        style={{ borderRadius: '8px', height: '42px' }}
                      >
                        <option value="">-- No Project Manager Assigned --</option>
                        {pmOptions.map((pm) => (
                          <option key={pm.id} value={pm.id}>
                            {pm.full_name} ({pm.email})
                          </option>
                        ))}
                      </select>
                      <small className="text-muted d-block mt-1" style={{ fontSize: '0.75rem' }}>
                        A Project Manager can oversee multiple teams.
                      </small>
                    </div>

                    <div className="col-12 mt-3">
                      <div className="form-check form-switch">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id="editIsActive"
                          checked={formData.is_active}
                          onChange={(e) =>
                            setFormData((prev) => ({ ...prev, is_active: e.target.checked }))
                          }
                        />
                        <label className="form-check-label fw-medium small" htmlFor="editIsActive">
                          Active Team Status (Available for assignments and defect tracking)
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Team Members Roster */}
            <div className="col-12 col-lg-5">
              <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2 d-flex justify-content-between align-items-center">
                  <div>
                    <h5 className="fw-bold mb-1 d-flex align-items-center gap-2 text-dark">
                      <i className="bi bi-people-fill text-primary" />
                      Team Members ({formData.member_ids.length})
                    </h5>
                    <p className="text-muted small mb-0">Select engineers and team contributors.</p>
                  </div>
                </div>
                <div className="card-body px-4 pb-4">
                  {/* Search members */}
                  <div className="input-group mb-3">
                    <span className="input-group-text bg-light border-end-0">
                      <i className="bi bi-search text-muted" />
                    </span>
                    <input
                      type="text"
                      className="form-control bg-light border-start-0"
                      placeholder="Search employees to assign..."
                      value={memberSearch}
                      autoComplete="off"
                      onChange={(e) => setMemberSearch(e.target.value)}
                      style={{ fontSize: '0.88rem' }}
                    />
                  </div>

                  {/* Member Selection List */}
                  <div
                    className="custom-scrollbar border rounded p-2"
                    style={{ maxHeight: '360px', overflowY: 'auto', backgroundColor: '#fafbfc' }}
                  >
                    {filteredAvailableMembers.length === 0 ? (
                      <p className="text-muted text-center py-4 small mb-0">
                        No matching employees found.
                      </p>
                    ) : (
                      filteredAvailableMembers.map((emp) => {
                        const isSelected = formData.member_ids.includes(emp.id)
                        return (
                          <div
                            key={emp.id}
                            onClick={() => handleToggleMember(emp.id)}
                            className={`d-flex align-items-center justify-content-between p-2 mb-1 rounded ${
                              isSelected
                                ? 'bg-primary-subtle border border-primary text-primary-emphasis'
                                : 'bg-white border'
                            }`}
                            style={{ cursor: 'pointer', transition: 'all .15s ease' }}
                          >
                            <div className="d-flex align-items-center gap-2 overflow-hidden">
                              <input
                                type="checkbox"
                                className="form-check-input mt-0"
                                checked={isSelected}
                                onChange={() => {}}
                                style={{ pointerEvents: 'none' }}
                              />
                              <div
                                className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center flex-shrink-0"
                                style={{ width: 28, height: 28, fontSize: '0.75rem', fontWeight: 700 }}
                              >
                                {emp.full_name.charAt(0).toUpperCase()}
                              </div>
                              <div className="text-truncate">
                                <div className="fw-semibold small text-truncate">{emp.full_name}</div>
                                <div className="text-muted text-truncate" style={{ fontSize: '0.72rem' }}>
                                  {emp.role} • {emp.email}
                                </div>
                              </div>
                            </div>

                            {emp.current_team_name && emp.current_team_id !== selectedTeam.id && (
                              <span
                                className="badge bg-secondary-subtle text-secondary border flex-shrink-0"
                                style={{ fontSize: '0.68rem' }}
                              >
                                In: {emp.current_team_name}
                              </span>
                            )}
                          </div>
                        )
                      })
                    )}
                  </div>

                  {/* Actions */}
                  <div className="d-flex justify-content-end gap-2 mt-4 pt-3 border-top">
                    <button
                      type="button"
                      className="btn btn-light border px-4"
                      onClick={handleBackToList}
                      style={{ borderRadius: '10px' }}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="btn btn-primary px-4 d-inline-flex align-items-center gap-2 shadow-sm"
                      disabled={isSubmitting}
                      style={{ borderRadius: '10px', fontWeight: 600 }}
                    >
                      {isSubmitting ? (
                        <>
                          <span className="spinner-border spinner-border-sm" role="status" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-check-lg" />
                          Save Changes
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </form>
      </div>
    )
  }

  // ─────────────────────────────────────────────────────────────
  // RENDER: LIST VIEW
  // ─────────────────────────────────────────────────────────────
  return (
    <div className="container-fluid py-4" style={{ maxWidth: '1350px' }}>
      {/* Toast Alert */}
      {toast && (
        <div
          className={`alert alert-${toast.variant} alert-dismissible fade show shadow-sm mb-4`}
          role="alert"
        >
          <strong>{toast.message}</strong>
          <button type="button" className="btn-close" onClick={() => setToast(null)} />
        </div>
      )}

      {/* Header Bar */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span
              className="badge bg-primary-subtle text-primary border border-primary px-2 py-1"
              style={{ fontSize: '0.75rem', fontWeight: 600 }}
            >
              ADMINISTRATION
            </span>
            <span className="text-muted small">Organization Structure</span>
          </div>
          <h2 className="fw-bold mb-1 text-dark">Team Management</h2>
          <p className="text-muted small mb-0">
            Create and organize agile engineering teams, assign dedicated Team Leaders, and manage cross-functional members.
          </p>
        </div>

        <div className="d-flex align-items-center gap-2">
          <button
            type="button"
            className="btn btn-primary px-3 py-2 d-inline-flex align-items-center gap-2 shadow-sm"
            onClick={handleOpenCreate}
            style={{ borderRadius: '10px', fontWeight: 600 }}
          >
            <i className="bi bi-plus-lg" />
            <span>Create Team</span>
          </button>
        </div>
      </div>

      {/* ── Workforce & Team Insights KPI Grid ── */}
      <div className="row g-3 mb-4">
        {/* Total Users / Eligible Employees */}
        <div className="col-12 col-sm-6 col-xl-3">
          <div
            className="card border-0 shadow-sm h-100 p-3"
            style={{ borderRadius: '14px', borderLeft: '4px solid #2563eb' }}
          >
            <div className="d-flex align-items-center justify-content-between">
              <div>
                <span className="text-muted small fw-bold text-uppercase d-block mb-1">
                  Total Users
                </span>
                <h3 className="fw-bold text-dark mb-0">
                  {statsLoading ? (
                    <span className="spinner-border spinner-border-sm text-primary" />
                  ) : (
                    teamStats?.total_users ?? 0
                  )}
                </h3>
                <small className="text-muted">Eligible real employees</small>
              </div>
              <div
                className="rounded-3 bg-primary-subtle text-primary d-flex align-items-center justify-content-center"
                style={{ width: 46, height: 46, fontSize: '1.3rem' }}
              >
                <i className="bi bi-people-fill" />
              </div>
            </div>
          </div>
        </div>

        {/* Total Teams */}
        <div className="col-12 col-sm-6 col-xl-3">
          <div
            className="card border-0 shadow-sm h-100 p-3"
            style={{ borderRadius: '14px', borderLeft: '4px solid #7c3aed' }}
          >
            <div className="d-flex align-items-center justify-content-between">
              <div>
                <span className="text-muted small fw-bold text-uppercase d-block mb-1">
                  Total Teams
                </span>
                <h3 className="fw-bold text-dark mb-0">
                  {statsLoading ? (
                    <span className="spinner-border spinner-border-sm text-primary" />
                  ) : (
                    teamStats?.total_teams ?? teams.length
                  )}
                </h3>
                <small className="text-muted">
                  {teamStats?.active_teams ?? teams.filter((t) => t.is_active).length} active
                </small>
              </div>
              <div
                className="rounded-3 bg-purple-subtle d-flex align-items-center justify-content-center"
                style={{
                  width: 46,
                  height: 46,
                  fontSize: '1.3rem',
                  backgroundColor: '#f3e8ff',
                  color: '#7c3aed',
                }}
              >
                <i className="bi bi-diagram-3-fill" />
              </div>
            </div>
          </div>
        </div>

        {/* Assigned Members */}
        <div className="col-12 col-sm-6 col-xl-3">
          <div
            className="card border-0 shadow-sm h-100 p-3"
            style={{ borderRadius: '14px', borderLeft: '4px solid #10b981' }}
          >
            <div className="d-flex align-items-center justify-content-between">
              <div>
                <span className="text-muted small fw-bold text-uppercase d-block mb-1">
                  Assigned Members
                </span>
                <h3 className="fw-bold text-success mb-0">
                  {statsLoading ? (
                    <span className="spinner-border spinner-border-sm text-success" />
                  ) : (
                    teamStats?.assigned_members ?? 0
                  )}
                </h3>
                <small className="text-muted">In active teams</small>
              </div>
              <div
                className="rounded-3 bg-success-subtle text-success d-flex align-items-center justify-content-center"
                style={{ width: 46, height: 46, fontSize: '1.3rem' }}
              >
                <i className="bi bi-person-check-fill" />
              </div>
            </div>
          </div>
        </div>

        {/* Unassigned Employees */}
        <div className="col-12 col-sm-6 col-xl-3">
          <div
            className="card border-0 shadow-sm h-100 p-3"
            style={{ borderRadius: '14px', borderLeft: '4px solid #f59e0b' }}
          >
            <div className="d-flex align-items-center justify-content-between">
              <div>
                <span className="text-muted small fw-bold text-uppercase d-block mb-1">
                  Unassigned Staff
                </span>
                <h3 className="fw-bold text-warning mb-0">
                  {statsLoading ? (
                    <span className="spinner-border spinner-border-sm text-warning" />
                  ) : (
                    teamStats?.unassigned_users ?? 0
                  )}
                </h3>
                <small className="text-muted">Available for assignment</small>
              </div>
              <div
                className="rounded-3 bg-warning-subtle text-warning d-flex align-items-center justify-content-center"
                style={{ width: 46, height: 46, fontSize: '1.3rem' }}
              >
                <i className="bi bi-person-dash-fill" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '14px' }}>
        <div className="card-body p-3">
          <div className="row g-2 align-items-center">
            <div className="col-12 col-md-6 col-lg-5">
              <div className="input-group">
                <span className="input-group-text bg-transparent border-end-0 text-muted">
                  <i className="bi bi-search" />
                </span>
                <input
                  type="text"
                  className="form-control border-start-0"
                  placeholder="Search teams by name, description, or Team Leader..."
                  value={searchQuery}
                  autoComplete="off"
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ borderRadius: '0 8px 8px 0' }}
                />
              </div>
            </div>

            <div className="col-6 col-md-3 col-lg-2">
              <select
                className="form-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                style={{ borderRadius: '8px' }}
              >
                <option value="all">All Statuses</option>
                <option value="active">Active Only</option>
                <option value="inactive">Inactive Only</option>
              </select>
            </div>

            <div className="col-6 col-md-3 col-lg-5 text-end text-muted small">
              Showing <strong>{filteredTeams.length}</strong> of <strong>{teams.length}</strong> teams
            </div>
          </div>
        </div>
      </div>

      {/* Teams Grid / Table */}
      <div className="card border-0 shadow-sm" style={{ borderRadius: '16px', overflow: 'hidden' }}>
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead style={{ backgroundColor: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
              <tr>
                <th className="py-3 px-4 text-secondary small fw-bold text-uppercase">Team</th>
                <th className="py-3 px-4 text-secondary small fw-bold text-uppercase">Team Leader</th>
                <th className="py-3 px-4 text-secondary small fw-bold text-uppercase">Project Manager</th>
                <th className="py-3 px-4 text-secondary small fw-bold text-uppercase text-center">Members</th>
                <th className="py-3 px-4 text-secondary small fw-bold text-uppercase text-center">Status</th>
                <th className="py-3 px-4 text-secondary small fw-bold text-uppercase text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6" className="text-center py-5 text-muted">
                    <div className="spinner-border spinner-border-sm text-primary me-2" role="status" />
                    Loading teams...
                  </td>
                </tr>
              ) : filteredTeams.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center py-5 text-muted">
                    <i className="bi bi-diagram-3 fs-2 d-block mb-2 text-secondary" />
                    No teams found matching your filters.
                  </td>
                </tr>
              ) : (
                filteredTeams.map((team) => (
                  <tr key={team.id}>
                    {/* Team Name & Description */}
                    <td className="py-3 px-4">
                      <div className="d-flex align-items-center gap-3">
                        <div
                          className="rounded-3 bg-primary-subtle text-primary d-flex align-items-center justify-content-center flex-shrink-0"
                          style={{ width: 42, height: 42, fontWeight: 700, fontSize: '1rem' }}
                        >
                          <i className="bi bi-diagram-3-fill" />
                        </div>
                        <div>
                          <div className="fw-bold text-dark">{team.name}</div>
                          <div className="text-muted small text-truncate" style={{ maxWidth: '280px' }}>
                            {team.description || 'No description provided.'}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Team Leader */}
                    <td className="py-3 px-4">
                      {team.team_leader ? (
                        <div className="d-flex align-items-center gap-2">
                          <div
                            className="rounded-circle bg-purple text-white d-flex align-items-center justify-content-center flex-shrink-0"
                            style={{
                              width: 28,
                              height: 28,
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              backgroundColor: '#7c3aed',
                            }}
                          >
                            {team.team_leader.full_name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="fw-semibold small text-dark">{team.team_leader.full_name}</div>
                            <div className="text-muted" style={{ fontSize: '0.72rem' }}>
                              {team.team_leader.email}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <span className="text-muted small italic">Unassigned</span>
                      )}
                    </td>

                    {/* Project Manager */}
                    <td className="py-3 px-4">
                      {team.project_manager ? (
                        <div className="d-flex align-items-center gap-2">
                          <div
                            className="rounded-circle bg-indigo text-white d-flex align-items-center justify-content-center flex-shrink-0"
                            style={{
                              width: 28,
                              height: 28,
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              backgroundColor: '#4f46e5',
                            }}
                          >
                            {team.project_manager.full_name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="fw-semibold small text-dark">{team.project_manager.full_name}</div>
                            <div className="text-muted" style={{ fontSize: '0.72rem' }}>
                              {team.project_manager.email}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <span className="text-muted small italic">Unassigned</span>
                      )}
                    </td>

                    {/* Members Count */}
                    <td className="py-3 px-4 text-center">
                      <span
                        className="badge bg-primary-subtle text-primary border border-primary px-3 py-1"
                        style={{ borderRadius: '20px', fontSize: '0.82rem', fontWeight: 600 }}
                      >
                        {team.member_count} Members
                      </span>
                    </td>

                    {/* Status */}
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`badge px-2 py-1 ${
                          team.is_active
                            ? 'bg-success-subtle text-success border border-success'
                            : 'bg-secondary-subtle text-secondary border'
                        }`}
                        style={{ borderRadius: '6px', fontSize: '0.75rem' }}
                      >
                        {team.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-end">
                      <div className="btn-group btn-group-sm">
                        <button
                          type="button"
                          className="btn btn-outline-secondary"
                          title="View Team Details & Members"
                          onClick={() => handleOpenView(team)}
                        >
                          <i className="bi bi-eye" />
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-primary"
                          title="Edit Team"
                          onClick={() => handleOpenEdit(team)}
                        >
                          <i className="bi bi-pencil" />
                        </button>
                        {team.is_active && (
                          <button
                            type="button"
                            className="btn btn-outline-danger"
                            title="Deactivate Team"
                            onClick={() => handleOpenDeactivate(team)}
                          >
                            <i className="bi bi-slash-circle" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── CREATE TEAM MODAL ── */}
      {showCreateModal && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
            <div className="modal-content border-0 shadow-lg" style={{ borderRadius: '16px' }}>
              <div className="modal-header border-0 pb-0 pt-4 px-4">
                <h5 className="modal-title fw-bold text-dark d-flex align-items-center gap-2">
                  <i className="bi bi-diagram-3-fill text-primary" />
                  Create New Team
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowCreateModal(false)}
                />
              </div>
              <form onSubmit={handleCreateSubmit} autoComplete="off">
                <div className="modal-body px-4 py-3">
                  <div className="row g-3">
                    <div className="col-12">
                      <label className="form-label fw-medium small">
                        Team Name <span className="text-danger">*</span>
                      </label>
                      <input
                        type="text"
                        className={`form-control ${formErrors.name ? 'is-invalid' : ''}`}
                        placeholder="e.g. Phoenix Backend, Core Quality Guild"
                        value={formData.name}
                        autoComplete="off"
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, name: e.target.value }))
                        }
                        style={{ borderRadius: '8px', height: '42px' }}
                      />
                      {formErrors.name && (
                        <div className="invalid-feedback">{formErrors.name}</div>
                      )}
                    </div>

                    <div className="col-12">
                      <label className="form-label fw-medium small">Description</label>
                      <textarea
                        className="form-control"
                        rows={2}
                        placeholder="Primary defect tracking and engineering responsibilities..."
                        value={formData.description}
                        autoComplete="off"
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, description: e.target.value }))
                        }
                        style={{ borderRadius: '8px' }}
                      />
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label fw-medium small d-flex justify-content-between">
                        <span>Team Leader</span>
                        <span className="text-muted" style={{ fontSize: '0.75rem' }}>1 team max</span>
                      </label>
                      <select
                        className="form-select"
                        value={formData.team_leader_id}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, team_leader_id: e.target.value }))
                        }
                        style={{ borderRadius: '8px', height: '42px' }}
                      >
                        <option value="">-- No Team Leader Assigned --</option>
                        {availableLeaders.map((l) => (
                          <option key={l.id} value={l.id}>
                            {l.full_name} ({l.email})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label fw-medium small d-flex justify-content-between">
                        <span>Project Manager (PM)</span>
                        <span className="text-muted" style={{ fontSize: '0.75rem' }}>Multi-team OK</span>
                      </label>
                      <select
                        className="form-select"
                        value={formData.project_manager_id}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, project_manager_id: e.target.value }))
                        }
                        style={{ borderRadius: '8px', height: '42px' }}
                      >
                        <option value="">-- No Project Manager Assigned --</option>
                        {pmOptions.map((pm) => (
                          <option key={pm.id} value={pm.id}>
                            {pm.full_name} ({pm.email})
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Team Members Assignment */}
                    <div className="col-12 mt-3">
                      <label className="form-label fw-medium small">
                        Assign Initial Members ({formData.member_ids.length} selected)
                      </label>
                      <input
                        type="text"
                        className="form-control form-control-sm mb-2"
                        placeholder="Search employees by name, role, or email..."
                        value={memberSearch}
                        autoComplete="off"
                        onChange={(e) => setMemberSearch(e.target.value)}
                        style={{ borderRadius: '6px' }}
                      />
                      <div
                        className="custom-scrollbar border rounded p-2"
                        style={{ maxHeight: '200px', overflowY: 'auto', backgroundColor: '#f8fafc' }}
                      >
                        {filteredAvailableMembers.length === 0 ? (
                          <p className="text-muted text-center py-3 small mb-0">No employees available.</p>
                        ) : (
                          filteredAvailableMembers.map((emp) => {
                            const isChecked = formData.member_ids.includes(emp.id)
                            return (
                              <div
                                key={emp.id}
                                onClick={() => handleToggleMember(emp.id)}
                                className={`d-flex align-items-center justify-content-between p-2 mb-1 rounded ${
                                  isChecked ? 'bg-primary-subtle border border-primary' : 'bg-white border'
                                }`}
                                style={{ cursor: 'pointer' }}
                              >
                                <div className="d-flex align-items-center gap-2">
                                  <input
                                    type="checkbox"
                                    className="form-check-input mt-0"
                                    checked={isChecked}
                                    onChange={() => {}}
                                    style={{ pointerEvents: 'none' }}
                                  />
                                  <span className="small fw-semibold">{emp.full_name}</span>
                                  <span className="text-muted" style={{ fontSize: '0.75rem' }}>
                                    ({emp.role})
                                  </span>
                                </div>
                                {emp.current_team_name && (
                                  <span
                                    className="badge bg-secondary-subtle text-secondary border"
                                    style={{ fontSize: '0.68rem' }}
                                  >
                                    In: {emp.current_team_name}
                                  </span>
                                )}
                              </div>
                            )
                          })
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="modal-footer border-0 px-4 pb-4">
                  <button
                    type="button"
                    className="btn btn-light border px-4"
                    onClick={() => setShowCreateModal(false)}
                    style={{ borderRadius: '8px' }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary px-4 shadow-sm"
                    disabled={isSubmitting}
                    style={{ borderRadius: '8px', fontWeight: 600 }}
                  >
                    {isSubmitting ? 'Creating Team...' : 'Create Team'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* ── VIEW TEAM DETAILS MODAL ── */}
      {showViewModal && selectedTeam && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
            <div className="modal-content border-0 shadow-lg" style={{ borderRadius: '16px' }}>
              <div className="modal-header border-0 pb-0 pt-4 px-4">
                <div className="d-flex align-items-center gap-3">
                  <div
                    className="rounded-3 bg-primary text-white d-flex align-items-center justify-content-center"
                    style={{ width: 44, height: 44, fontSize: '1.2rem' }}
                  >
                    <i className="bi bi-diagram-3-fill" />
                  </div>
                  <div>
                    <h5 className="modal-title fw-bold text-dark mb-0">{selectedTeam.name}</h5>
                    <span className="text-muted small">
                      {selectedTeam.description || 'No description provided.'}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowViewModal(false)}
                />
              </div>

              <div className="modal-body px-4 py-3">
                <div className="row g-3 mb-4">
                  <div className="col-md-6">
                    <div className="p-3 bg-light rounded-3 border">
                      <div className="text-muted small fw-semibold text-uppercase mb-1">
                        Team Leader
                      </div>
                      {selectedTeam.team_leader ? (
                        <div className="fw-bold text-dark d-flex align-items-center gap-2">
                          <i className="bi bi-person-badge-fill text-purple" />
                          {selectedTeam.team_leader.full_name}
                          <span className="text-muted small fw-normal">
                            ({selectedTeam.team_leader.email})
                          </span>
                        </div>
                      ) : (
                        <span className="text-muted small">No Team Leader Assigned</span>
                      )}
                    </div>
                  </div>

                  <div className="col-md-6">
                    <div className="p-3 bg-light rounded-3 border">
                      <div className="text-muted small fw-semibold text-uppercase mb-1">
                        Project Manager
                      </div>
                      {selectedTeam.project_manager ? (
                        <div className="fw-bold text-dark d-flex align-items-center gap-2">
                          <i className="bi bi-briefcase-fill text-indigo" />
                          {selectedTeam.project_manager.full_name}
                          <span className="text-muted small fw-normal">
                            ({selectedTeam.project_manager.email})
                          </span>
                        </div>
                      ) : (
                        <span className="text-muted small">No Project Manager Assigned</span>
                      )}
                    </div>
                  </div>
                </div>

                <h6 className="fw-bold text-dark mb-2">
                  Team Members ({selectedTeam.members ? selectedTeam.members.length : 0})
                </h6>

                <div className="table-responsive border rounded-3">
                  <table className="table table-sm table-hover mb-0">
                    <thead className="table-light">
                      <tr>
                        <th className="py-2 px-3">Name</th>
                        <th className="py-2 px-3">Email</th>
                        <th className="py-2 px-3">Role</th>
                        <th className="py-2 px-3">Department</th>
                      </tr>
                    </thead>
                    <tbody>
                      {!selectedTeam.members || selectedTeam.members.length === 0 ? (
                        <tr>
                          <td colSpan="4" className="text-center py-3 text-muted">
                            No members assigned to this team yet.
                          </td>
                        </tr>
                      ) : (
                        selectedTeam.members.map((m) => (
                          <tr key={m.id}>
                            <td className="py-2 px-3 fw-semibold text-dark">{m.full_name}</td>
                            <td className="py-2 px-3 text-muted">{m.email}</td>
                            <td className="py-2 px-3">
                              <span className="badge bg-light text-dark border">{m.role}</span>
                            </td>
                            <td className="py-2 px-3 text-muted">{m.department || '—'}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="modal-footer border-0 px-4 pb-4">
                <button
                  type="button"
                  className="btn btn-light border px-4"
                  onClick={() => setShowViewModal(false)}
                  style={{ borderRadius: '8px' }}
                >
                  Close
                </button>
                <button
                  type="button"
                  className="btn btn-primary px-4 shadow-sm"
                  onClick={() => {
                    setShowViewModal(false)
                    handleOpenEdit(selectedTeam)
                  }}
                  style={{ borderRadius: '8px', fontWeight: 600 }}
                >
                  Edit Team
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── DEACTIVATE TEAM CONFIRMATION MODAL ── */}
      {showDeactivateModal && selectedTeam && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow-lg" style={{ borderRadius: '16px' }}>
              <div className="modal-header border-0 pb-0 pt-4 px-4">
                <h5 className="modal-title fw-bold text-danger d-flex align-items-center gap-2">
                  <i className="bi bi-exclamation-triangle-fill" />
                  Deactivate Team
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowDeactivateModal(false)}
                />
              </div>
              <div className="modal-body px-4 py-3">
                <p className="mb-2">
                  Are you sure you want to deactivate team <strong>{selectedTeam.name}</strong>?
                </p>
                <p className="text-muted small mb-0">
                  Deactivated teams will no longer appear in active project assignments. Existing defect history and resolution logs remain preserved.
                </p>
              </div>
              <div className="modal-footer border-0 px-4 pb-4">
                <button
                  type="button"
                  className="btn btn-light border px-4"
                  onClick={() => setShowDeactivateModal(false)}
                  style={{ borderRadius: '8px' }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-danger px-4 shadow-sm"
                  disabled={isSubmitting}
                  onClick={handleConfirmDeactivate}
                  style={{ borderRadius: '8px', fontWeight: 600 }}
                >
                  {isSubmitting ? 'Deactivating...' : 'Confirm Deactivate'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
