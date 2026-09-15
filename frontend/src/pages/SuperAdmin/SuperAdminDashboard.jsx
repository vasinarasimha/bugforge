import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { superAdminApi } from '../../api/superAdminApi'
import StatusBadge from '../../components/common/StatusBadge'
import SearchableSelect from '../../components/common/SearchableSelect'
import Modal from '../../components/Modal/Modal'
import Toast from '../../components/Toast/Toast'
import { getIssues, assignIssueTeam, extractErrorMessage } from '../../services/issueService'
import { getTeams } from '../../services/teamService'
import { formatDateTime } from '../../components/IssueTable/IssueTable'

export default function SuperAdminDashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')

  const [customerRequests, setCustomerRequests] = useState([])
  const [internalTeams, setInternalTeams] = useState([])
  const [assignModalIssue, setAssignModalIssue] = useState(null)
  const [selectedTeamId, setSelectedTeamId] = useState('')
  const [assigningTeam, setAssigningTeam] = useState(false)
  const [toast, setToast] = useState({ message: '', variant: 'success' })

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    setLoading(true)
    setError('')
    try {
      const [dashRes, issuesRes, teamsRes] = await Promise.all([
        superAdminApi.getPlatformDashboard(),
        getIssues({ issue_type: 'Feature' }).catch(() => ({ data: [] })),
        getTeams().catch(() => ({ data: [] })),
      ])
      setData(dashRes)
      const allFeats = issuesRes.data || []
      const custFeats = allFeats.filter(i => i.requesting_company_id || i.issue_type === 'Feature')
      setCustomerRequests(custFeats)
      setInternalTeams(teamsRes.data?.data || teamsRes.data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load platform dashboard.')
    } finally {
      setLoading(false)
    }
  }

  const handleAssignTeam = async () => {
    if (!assignModalIssue || !selectedTeamId) return
    setAssigningTeam(true)
    const requestTitle = assignModalIssue.title
    const teamObj = internalTeams.find(t => String(t.id) === String(selectedTeamId))
    const teamName = teamObj?.name || 'Assigned Squad'
    try {
      const res = await assignIssueTeam(assignModalIssue.id, { team_id: Number(selectedTeamId) })
      const updated = res.data
      const finalTeamName = updated?.team_name || teamName
      setCustomerRequests(prev => prev.map(iss => iss.id === assignModalIssue.id ? {
        ...iss,
        team_id: updated.team_id,
        team_name: updated.team_name,
        status_id: updated.status_id,
        status_name: updated.status_name,
      } : iss))
      setAssignModalIssue(null)
      setSelectedTeamId('')
      setToast({
        message: `Customization request "${requestTitle}" assigned to squad "${finalTeamName}" successfully.`,
        variant: 'success'
      })
    } catch (err) {
      const errorMsg = extractErrorMessage(err, 'Failed to assign squad.')
      setToast({ message: errorMsg, variant: 'error' })
    } finally {
      setAssigningTeam(false)
    }
  }

  const filteredCompanies = (data?.companies_activity || []).filter((c) =>
    c.company_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="container-fluid px-4 py-4" style={{ maxWidth: '1600px' }}>
      {/* Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-primary-subtle text-primary border border-primary-subtle px-2.5 py-1 rounded-pill text-xs font-semibold">
              <i className="bi bi-shield-check me-1" /> Platform Administration
            </span>
          </div>
          <h1 className="h3 font-bold text-slate-900 mb-1">Super Admin Dashboard</h1>
          <p className="text-muted text-sm mb-0">
            Platform-wide tenant overview, company health, and cross-company operational volume.
          </p>
        </div>

        <div className="d-flex gap-2">
          <button
            onClick={loadDashboard}
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1.5 shadow-sm"
            disabled={loading}
          >
            <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <Link
            to="/super-admin/companies/create"
            className="btn btn-primary btn-sm d-flex align-items-center gap-1.5 shadow-sm"
          >
            <i className="bi bi-plus-lg" />
            <span>Create Company</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-4" role="alert">
          <i className="bi bi-exclamation-triangle-fill" />
          <div>{error}</div>
        </div>
      )}

      {/* KPI Cards (Strictly Company-Level Aggregates) */}
      <div className="row g-3 mb-4">
        <div className="col-12 col-sm-6 col-xl-3">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white h-100">
            <div className="d-flex align-items-center justify-content-between mb-2">
              <span className="text-muted text-xs text-uppercase font-semibold tracking-wider">Total Companies</span>
              <div className="w-9 h-9 rounded-2 bg-blue-50 text-primary d-flex align-items-center justify-content-center">
                <i className="bi bi-building fs-5" />
              </div>
            </div>
            <div className="d-flex align-items-baseline gap-2">
              <h2 className="h3 font-bold mb-0 text-slate-800">{data?.total_companies ?? '—'}</h2>
              <span className="text-xs text-muted">tenants</span>
            </div>
            <div className="mt-2 text-xs text-success d-flex align-items-center gap-1">
              <i className="bi bi-check-circle" />
              <span>{data?.active_companies ?? 0} active</span>
              <span className="text-muted mx-1">•</span>
              <span className="text-secondary">{data?.inactive_companies ?? 0} inactive</span>
            </div>
          </div>
        </div>

        <div className="col-12 col-sm-6 col-xl-3">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white h-100">
            <div className="d-flex align-items-center justify-content-between mb-2">
              <span className="text-muted text-xs text-uppercase font-semibold tracking-wider">New Companies (7d / 30d)</span>
              <div className="w-9 h-9 rounded-2 bg-emerald-50 text-emerald-600 d-flex align-items-center justify-content-center">
                <i className="bi bi-graph-up-arrow fs-5" />
              </div>
            </div>
            <div className="d-flex align-items-baseline gap-2">
              <h2 className="h3 font-bold mb-0 text-emerald-600">+{data?.new_companies_last_7_days ?? 0}</h2>
              <span className="text-xs text-muted">last 7 days</span>
            </div>
            <div className="mt-2 text-xs text-muted">
              +{data?.new_companies_last_30_days ?? 0} onboarded in last 30 days
            </div>
          </div>
        </div>

        <div className="col-12 col-sm-6 col-xl-3">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white h-100">
            <div className="d-flex align-items-center justify-content-between mb-2">
              <span className="text-muted text-xs text-uppercase font-semibold tracking-wider">Platform Projects</span>
              <div className="w-9 h-9 rounded-2 bg-indigo-50 text-indigo-600 d-flex align-items-center justify-content-center">
                <i className="bi bi-folder-check fs-5" />
              </div>
            </div>
            <div className="d-flex align-items-baseline gap-2">
              <h2 className="h3 font-bold mb-0 text-slate-800">{data?.total_platform_projects ?? '—'}</h2>
              <span className="text-xs text-muted">active projects</span>
            </div>
            <div className="mt-2 text-xs text-muted">
              Across all registered tenant companies
            </div>
          </div>
        </div>

        <div className="col-12 col-sm-6 col-xl-3">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white h-100">
            <div className="d-flex align-items-center justify-content-between mb-2">
              <span className="text-muted text-xs text-uppercase font-semibold tracking-wider">Platform Total Issues</span>
              <div className="w-9 h-9 rounded-2 bg-amber-50 text-amber-600 d-flex align-items-center justify-content-center">
                <i className="bi bi-bug fs-5" />
              </div>
            </div>
            <div className="d-flex align-items-baseline gap-2">
              <h2 className="h3 font-bold mb-0 text-slate-800">{data?.total_platform_issues ?? '—'}</h2>
              <span className="text-xs text-muted">total tracked</span>
            </div>
            <div className="mt-2 text-xs text-muted">
              Platform-wide defect tracking volume
            </div>
          </div>
        </div>
      </div>

      {/* Customer Requests & Squad Assignment */}
      <div className="card border-0 shadow-sm rounded-3 bg-white overflow-hidden mb-4">
        <div className="card-header bg-white border-bottom py-3 px-4 d-flex flex-wrap justify-content-between align-items-center gap-3">
          <div className="d-flex align-items-center gap-2">
            <div className="w-9 h-9 rounded-2 bg-indigo-50 text-indigo-600 d-flex align-items-center justify-content-center">
              <i className="bi bi-stars fs-5" />
            </div>
            <div>
              <div className="d-flex align-items-center gap-2">
                <h2 className="h6 font-bold text-slate-800 mb-0">Customer Feature Requests &amp; Squad Assignment</h2>
                {customerRequests.filter(r => !r.team_id).length > 0 && (
                  <span className="badge bg-warning-subtle text-warning border border-warning-subtle rounded-pill text-xs">
                    {customerRequests.filter(r => !r.team_id).length} unassigned squad
                  </span>
                )}
              </div>
              <p className="text-muted text-xs mb-0">
                Direct platform control to review tenant feature submissions and assign internal BugForge engineering squads.
              </p>
            </div>
          </div>
          <div className="d-flex align-items-center gap-2">
            <Link to="/issues?filter=customer_requests" className="btn btn-outline-primary btn-sm text-nowrap d-flex align-items-center gap-1.5">
              <span>View All Customer Requests</span>
              <i className="bi bi-arrow-right" />
            </Link>
          </div>
        </div>

        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light text-muted text-xs text-uppercase">
              <tr>
                <th className="ps-4 py-3">Request / Issue</th>
                <th className="py-3">Client Company</th>
                <th className="py-3">Status</th>
                <th className="py-3">Assigned Squad</th>
                <th className="py-3">Created</th>
                <th className="text-end pe-4 py-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6" className="text-center py-4 text-muted">
                    <div className="spinner-border spinner-border-sm text-primary me-2" role="status" />
                    Loading customer requests...
                  </td>
                </tr>
              ) : customerRequests.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center py-4 text-muted">
                    <i className="bi bi-inbox fs-4 d-block mb-1 text-slate-400" />
                    No customer feature requests found.
                  </td>
                </tr>
              ) : (
                customerRequests.slice(0, 5).map((req) => (
                  <tr key={req.id}>
                    <td className="ps-4 py-3">
                      <div className="d-flex align-items-center gap-2">
                        <Link
                          to={`/issues/${req.id}`}
                          className="font-semibold text-slate-800 text-decoration-none hover:text-primary"
                        >
                          {req.issue_key || 'Customization Request'}
                        </Link>
                        <span className="badge px-2 py-0.5 rounded-pill text-xs font-normal" style={{ backgroundColor: 'rgba(99, 102, 241, 0.12)', color: '#4f46e5', border: '1px solid rgba(99, 102, 241, 0.28)' }}>
                          <i className="bi bi-stars me-1" />Feature
                        </span>
                      </div>
                      <div className="text-xs text-slate-600 font-medium text-truncate" style={{ maxWidth: '340px' }} title={req.title}>
                        {req.title}
                      </div>
                    </td>
                    <td className="py-3">
                      <span className="d-inline-flex align-items-center gap-1.5 text-xs text-slate-700 font-medium">
                        <i className="bi bi-building text-muted" />
                        {req.requesting_company_name || req.company_name || 'External Client'}
                      </span>
                    </td>
                    <td className="py-3">
                      <StatusBadge status={req.status_name || 'Open'} size="sm" />
                    </td>
                    <td className="py-3">
                      {req.team_name ? (
                        <span className="badge px-2.5 py-1 rounded-pill d-inline-flex align-items-center gap-1" style={{ fontSize: '0.75rem', backgroundColor: '#e0e7ff', color: '#3730a3', border: '1px solid #c7d2fe' }}>
                          <i className="bi bi-diagram-3-fill" />
                          <span>{req.team_name}</span>
                        </span>
                      ) : (
                        <span className="badge px-2.5 py-1 rounded-pill d-inline-flex align-items-center gap-1" style={{ fontSize: '0.75rem', backgroundColor: '#fef3c7', color: '#92400e', border: '1px solid #fde68a' }}>
                          <i className="bi bi-exclamation-circle" />
                          <span>Unassigned Squad</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-xs text-muted" style={{ whiteSpace: 'nowrap' }}>
                      {formatDateTime(req.created_at)}
                    </td>
                    <td className="text-end pe-4 py-3">
                      <button
                        type="button"
                        onClick={() => {
                          setAssignModalIssue(req)
                          setSelectedTeamId(req.team_id ? String(req.team_id) : '')
                        }}
                        className={`btn btn-sm ${req.team_name ? 'btn-outline-secondary' : 'btn-primary'} py-1 px-2.5 text-xs d-inline-flex align-items-center gap-1 shadow-sm`}
                      >
                        <i className="bi bi-diagram-3" />
                        <span>{req.team_name ? 'Reassign' : 'Assign Squad'}</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Company Activity Overview Table */}
      <div className="card border-0 shadow-sm rounded-3 bg-white overflow-hidden">
        <div className="card-header bg-white border-bottom py-3 px-4 d-flex flex-wrap justify-content-between align-items-center gap-3">
          <div>
            <h2 className="h6 font-bold text-slate-800 mb-0">Company Activity Breakdown</h2>
            <p className="text-muted text-xs mb-0">
              Aggregated defect volume and project metrics summarized per tenant company.
            </p>
          </div>
          <div className="d-flex align-items-center gap-2">
            <div className="input-group input-group-sm" style={{ width: '240px' }}>
              <span className="input-group-text bg-light border-end-0 text-muted">
                <i className="bi bi-search" />
              </span>
              <input
                type="text"
                className="form-control border-start-0 bg-light"
                placeholder="Search companies..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Link to="/super-admin/companies" className="btn btn-outline-primary btn-sm text-nowrap">
              View All Companies
            </Link>
          </div>
        </div>

        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light text-muted text-xs text-uppercase">
              <tr>
                <th className="ps-4 py-3">Company</th>
                <th className="py-3">Status</th>
                <th className="text-end py-3">Projects</th>
                <th className="text-end py-3">Open Issues</th>
                <th className="text-end py-3">Resolved Issues</th>
                <th className="text-end py-3">Critical Issues</th>
                <th className="text-end py-3">Total Issues</th>
                <th className="text-end pe-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="8" className="text-center py-5 text-muted">
                    <div className="spinner-border spinner-border-sm text-primary me-2" role="status" />
                    Loading platform metrics...
                  </td>
                </tr>
              ) : filteredCompanies.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-5 text-muted">
                    No companies matching your search.
                  </td>
                </tr>
              ) : (
                filteredCompanies.map((c) => (
                  <tr key={c.company_id} className="cursor-pointer" onClick={() => navigate(`/super-admin/companies/${c.company_id}`)}>
                    <td className="ps-4 py-3 font-semibold text-slate-800">
                      <div>
                        <div className="text-slate-900 font-semibold">{c.company_name}</div>
                        <div className="text-xs text-muted">{c.domain || 'Client Tenant'}</div>
                      </div>
                    </td>
                    <td className="py-3">
                      <span className={`badge rounded-pill text-xs px-2.5 py-1 ${c.is_active ? 'bg-success-subtle text-success border border-success-subtle' : 'bg-secondary-subtle text-secondary border border-secondary-subtle'}`}>
                        {c.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="text-end py-3 font-medium text-slate-700">{c.projects_count}</td>
                    <td className="text-end py-3 font-semibold text-blue-600">{c.open_issues}</td>
                    <td className="text-end py-3 font-semibold text-emerald-600">{c.resolved_issues}</td>
                    <td className="text-end py-3">
                      {c.critical_issues > 0 ? (
                        <span className="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-0.5 rounded-pill">
                          {c.critical_issues}
                        </span>
                      ) : (
                        <span className="text-muted text-xs">0</span>
                      )}
                    </td>
                    <td className="text-end py-3 font-bold text-slate-900">{c.total_issues}</td>
                    <td className="text-end pe-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <Link
                        to={`/super-admin/companies/${c.company_id}`}
                        className="btn btn-sm btn-light border py-1 px-2.5 text-xs text-slate-700"
                      >
                        Details <i className="bi bi-chevron-right ms-1 text-muted" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quick Assign Squad Modal */}
      {assignModalIssue && (
        <Modal
          isOpen={!!assignModalIssue}
          onClose={() => setAssignModalIssue(null)}
          title={`Assign BugForge Squad — ${assignModalIssue.issue_key || 'Customization Request'}`}
        >
          <div className="p-3">
            <p className="text-sm text-slate-600 mb-3">
              Assign an internal BugForge engineering squad to take ownership of this customer request:
              <br />
              <strong className="text-slate-800">{assignModalIssue.title}</strong>
            </p>
            <div className="mb-4">
              <label className="form-label text-xs font-semibold text-muted text-uppercase mb-1">
                Select BugForge Internal Squad
              </label>
              <SearchableSelect
                options={internalTeams.map((t) => ({ value: String(t.id), label: t.name }))}
                value={selectedTeamId ? String(selectedTeamId) : ''}
                onChange={(val) => setSelectedTeamId(val)}
                placeholder="Search and select squad..."
              />
              <div className="form-text text-xs text-muted mt-1.5">
                Assigning an internal squad changes the issue workflow state to <strong>Under Review</strong> and grants squad members access to implement it.
              </div>
            </div>
            <div className="d-flex justify-content-end gap-2 pt-2 border-top">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setAssignModalIssue(null)}
                disabled={assigningTeam}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm d-flex align-items-center gap-1.5"
                onClick={handleAssignTeam}
                disabled={!selectedTeamId || assigningTeam}
              >
                {assigningTeam ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status" />
                    <span>Assigning Squad...</span>
                  </>
                ) : (
                  <>
                    <i className="bi bi-check2-circle" />
                    <span>Confirm Squad Assignment</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Toast Notification */}
      <Toast
        message={toast.message}
        variant={toast.variant}
        onClose={() => setToast({ message: '', variant: 'success' })}
      />
    </div>
  )
}
