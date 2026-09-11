import React, { useState, useEffect } from 'react'
import { Link, useParams, useLocation, useNavigate } from 'react-router-dom'
import { superAdminApi } from '../../api/superAdminApi'
import AuditActionBadge from '../../components/common/AuditActionBadge'
import CountryStateSelect from '../../components/CountryStateSelect/CountryStateSelect'

export default function CompanyDetailsPage() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()

  const [company, setCompany] = useState(null)
  const [auditLogs, setAuditLogs] = useState([])
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState(location.state?.message || '')
  const [activeTab, setActiveTab] = useState('overview')
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadCompanyData()
  }, [id])

  const loadCompanyData = async () => {
    setLoading(true)
    setError('')
    try {
      const [detailRes, logsRes] = await Promise.all([
        superAdminApi.getCompanyDetail(id),
        superAdminApi.getCompanyAuditLogs(id, 30),
      ])
      setCompany(detailRes)
      setAuditLogs(logsRes || [])
      setEditForm({
        name: detailRes.name || '',
        legal_name: detailRes.legal_name || '',
        email: detailRes.email || '',
        phone: detailRes.phone || '',
        website: detailRes.website || '',
        address_line_1: detailRes.address_line_1 || '',
        address_line_2: detailRes.address_line_2 || '',
        city: detailRes.city || '',
        state: detailRes.state || '',
        country: detailRes.country || '',
        timezone: detailRes.timezone || 'UTC',
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load company details.')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleStatus = async () => {
    if (!company) return
    const newStatus = !company.is_active
    const msg = newStatus
      ? `Reactivate ${company.name}? Users will be able to log in.`
      : `Deactivate ${company.name}? Users cannot log in, but all data is retained.`
    if (!window.confirm(msg)) return

    try {
      const updated = await superAdminApi.toggleCompanyStatus(company.id, newStatus)
      setCompany((prev) => ({ ...prev, is_active: updated.is_active }))
      setSuccessMsg(`Company status successfully updated to ${newStatus ? 'Active' : 'Inactive'}.`)
      // Refresh audit logs
      const logs = await superAdminApi.getCompanyAuditLogs(id, 30)
      setAuditLogs(logs)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update status.')
    }
  }

  const handleSaveEdit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const updated = await superAdminApi.updateCompany(company.id, editForm)
      setCompany((prev) => ({ ...prev, ...updated }))
      setEditing(false)
      setSuccessMsg('Company information updated successfully.')
      const logs = await superAdminApi.getCompanyAuditLogs(id, 30)
      setAuditLogs(logs)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update company.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="container-fluid px-4 py-5 text-center text-muted">
        <div className="spinner-border text-primary mb-3" role="status" />
        <div>Loading company overview...</div>
      </div>
    )
  }

  if (error || !company) {
    return (
      <div className="container-fluid px-4 py-5">
        <div className="alert alert-danger mb-3">{error || 'Company not found.'}</div>
        <Link to="/super-admin/companies" className="btn btn-outline-secondary btn-sm">
          ← Back to Companies
        </Link>
      </div>
    )
  }

  return (
    <div className="container-fluid px-4 py-4" style={{ maxWidth: '1600px' }}>
      {/* Breadcrumb */}
      <nav aria-label="breadcrumb" className="mb-2">
        <ol className="breadcrumb mb-0 text-xs">
          <li className="breadcrumb-item"><Link to="/dashboard">Platform</Link></li>
          <li className="breadcrumb-item"><Link to="/super-admin/companies">Companies</Link></li>
          <li className="breadcrumb-item active" aria-current="page">{company.name}</li>
        </ol>
      </nav>

      {successMsg && (
        <div className="alert alert-success alert-dismissible fade show d-flex align-items-center gap-2 mb-4" role="alert">
          <i className="bi bi-check-circle-fill" />
          <div className="text-sm">{successMsg}</div>
          <button type="button" className="btn-close" onClick={() => setSuccessMsg('')} aria-label="Close" />
        </div>
      )}

      {/* Header Banner */}
      <div className="card border-0 shadow-sm rounded-3 p-4 bg-white mb-4">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
          <div className="d-flex align-items-center gap-3">
            <div className="w-14 h-14 rounded-3 bg-primary-subtle text-primary border border-primary-subtle d-flex align-items-center justify-content-center font-bold fs-3 shrink-0">
              {company.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="d-flex align-items-center gap-2">
                <h1 className="h4 font-bold text-slate-900 mb-0">{company.name}</h1>
                <span className={`badge rounded-pill text-xs px-2.5 py-1 ${company.is_active ? 'bg-success-subtle text-success border border-success-subtle' : 'bg-secondary-subtle text-secondary border border-secondary-subtle'}`}>
                  {company.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              {company.legal_name && <div className="text-xs text-muted mt-0.5">{company.legal_name}</div>}
              <div className="text-xs text-muted mt-1">
                <span className="me-3">Tenant ID: <strong>{company.id}</strong></span>
                <span>Created on: {new Date(company.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          <div className="d-flex align-items-center gap-2">
            <button
              onClick={() => setEditing(!editing)}
              className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1.5 shadow-sm"
            >
              <i className="bi bi-pencil" />
              <span>{editing ? 'Cancel Edit' : 'Edit Company'}</span>
            </button>
            <button
              onClick={handleToggleStatus}
              className={`btn btn-sm d-flex align-items-center gap-1.5 shadow-sm ${company.is_active ? 'btn-outline-danger' : 'btn-outline-success'}`}
            >
              <i className={`bi ${company.is_active ? 'bi-pause-circle' : 'bi-play-circle'}`} />
              <span>{company.is_active ? 'Deactivate Company' : 'Reactivate Company'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Edit Form Modal/Drawer if editing */}
      {editing && (
        <div className="card border-0 shadow-sm rounded-3 p-4 bg-white mb-4 border-start border-4 border-primary">
          <h2 className="h6 font-bold text-slate-800 mb-3">Edit Company Information</h2>
          <form onSubmit={handleSaveEdit}>
            <div className="row g-3">
              <div className="col-12 col-md-6">
                <label className="form-label text-xs font-semibold">Company Name</label>
                <input
                  type="text"
                  required
                  className="form-control form-control-sm"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                />
              </div>
              <div className="col-12 col-md-6">
                <label className="form-label text-xs font-semibold">Legal Entity Name</label>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={editForm.legal_name}
                  onChange={(e) => setEditForm({ ...editForm, legal_name: e.target.value })}
                />
              </div>
              <div className="col-12 col-md-6">
                <label className="form-label text-xs font-semibold">Email</label>
                <input
                  type="email"
                  className="form-control form-control-sm"
                  value={editForm.email}
                  onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                />
              </div>
              <div className="col-12 col-md-6">
                <label className="form-label text-xs font-semibold">Phone</label>
                <input
                  type="tel"
                  className="form-control form-control-sm"
                  value={editForm.phone}
                  onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                />
              </div>
              <div className="col-12 col-md-6">
                <label className="form-label text-xs font-semibold">Website</label>
                <input
                  type="url"
                  className="form-control form-control-sm"
                  value={editForm.website}
                  onChange={(e) => setEditForm({ ...editForm, website: e.target.value })}
                />
              </div>
              <div className="col-12 col-md-6">
                <label className="form-label text-xs font-semibold">Timezone</label>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={editForm.timezone}
                  onChange={(e) => setEditForm({ ...editForm, timezone: e.target.value })}
                />
              </div>
              <div className="col-12 col-md-6">
                <label className="form-label text-xs font-semibold">Address Line 1</label>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={editForm.address_line_1}
                  onChange={(e) => setEditForm({ ...editForm, address_line_1: e.target.value })}
                />
              </div>
              <div className="col-12 col-md-6">
                <label className="form-label text-xs font-semibold">City</label>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={editForm.city}
                  onChange={(e) => setEditForm({ ...editForm, city: e.target.value })}
                />
              </div>
              <div className="col-12 d-flex justify-content-end gap-2 mt-3">
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setEditing(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-sm btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* KPI Cards (Company-Level Aggregates) */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-4 col-xl-2">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white text-center h-100">
            <span className="text-muted text-xs text-uppercase font-semibold">Projects</span>
            <div className="h4 font-bold text-slate-800 my-1">{company.projects_count}</div>
            <span className="text-xs text-emerald-600 font-medium">{company.active_projects_count} active</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white text-center h-100">
            <span className="text-muted text-xs text-uppercase font-semibold">Open Issues</span>
            <div className="h4 font-bold text-blue-600 my-1">{company.open_issues_count}</div>
            <span className="text-xs text-muted">requiring action</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white text-center h-100">
            <span className="text-muted text-xs text-uppercase font-semibold">Resolved Issues</span>
            <div className="h4 font-bold text-emerald-600 my-1">{company.resolved_issues_count}</div>
            <span className="text-xs text-muted">completed</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white text-center h-100">
            <span className="text-muted text-xs text-uppercase font-semibold">Critical Defects</span>
            <div className="h4 font-bold text-danger my-1">{company.critical_issues_count}</div>
            <span className="text-xs text-danger font-medium">high priority</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white text-center h-100">
            <span className="text-muted text-xs text-uppercase font-semibold">Total Employees</span>
            <div className="h4 font-bold text-slate-800 my-1">{company.users_count}</div>
            <span className="text-xs text-muted">registered accounts</span>
          </div>
        </div>

        <div className="col-6 col-md-4 col-xl-2">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white text-center h-100">
            <span className="text-muted text-xs text-uppercase font-semibold">Company Admins</span>
            <div className="h4 font-bold text-indigo-600 my-1">{company.admins_count}</div>
            <span className="text-xs text-muted">tenant admins</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="card border-0 shadow-sm rounded-3 bg-white overflow-hidden">
        <div className="card-header bg-white border-bottom px-4 pt-3 pb-0">
          <ul className="nav nav-tabs card-header-tabs border-0">
            <li className="nav-item">
              <button
                className={`nav-link text-xs font-semibold py-2.5 px-3.5 border-0 ${activeTab === 'overview' ? 'active text-primary border-bottom border-2 border-primary bg-transparent' : 'text-muted'}`}
                onClick={() => setActiveTab('overview')}
              >
                <i className="bi bi-info-circle me-1.5" /> Company Information
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-link text-xs font-semibold py-2.5 px-3.5 border-0 ${activeTab === 'audit' ? 'active text-primary border-bottom border-2 border-primary bg-transparent' : 'text-muted'}`}
                onClick={() => setActiveTab('audit')}
              >
                <i className="bi bi-clock-history me-1.5" /> Audit History ({auditLogs.length})
              </button>
            </li>
          </ul>
        </div>

        <div className="card-body p-4">
          {activeTab === 'overview' && (
            <div className="row g-4">
              <div className="col-12 col-md-6">
                <h3 className="h6 font-bold text-slate-900 mb-3">Corporate & Contact Details</h3>
                <table className="table table-sm text-xs mb-0">
                  <tbody>
                    <tr>
                      <td className="text-muted py-2" style={{ width: '150px' }}>Company Name:</td>
                      <td className="font-semibold py-2">{company.name}</td>
                    </tr>
                    <tr>
                      <td className="text-muted py-2">Legal Name:</td>
                      <td className="py-2">{company.legal_name || '—'}</td>
                    </tr>
                    <tr>
                      <td className="text-muted py-2">Email:</td>
                      <td className="py-2">{company.email || '—'}</td>
                    </tr>
                    <tr>
                      <td className="text-muted py-2">Phone:</td>
                      <td className="py-2">{company.phone || '—'}</td>
                    </tr>
                    <tr>
                      <td className="text-muted py-2">Website:</td>
                      <td className="py-2">
                        {company.website ? (
                          <a href={company.website} target="_blank" rel="noopener noreferrer" className="text-primary">
                            {company.website}
                          </a>
                        ) : '—'}
                      </td>
                    </tr>
                    <tr>
                      <td className="text-muted py-2">Timezone:</td>
                      <td className="py-2">{company.timezone}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="col-12 col-md-6">
                <h3 className="h6 font-bold text-slate-900 mb-3">Physical Address</h3>
                <table className="table table-sm text-xs mb-0">
                  <tbody>
                    <tr>
                      <td className="text-muted py-2" style={{ width: '150px' }}>Address 1:</td>
                      <td className="py-2">{company.address_line_1 || '—'}</td>
                    </tr>
                    <tr>
                      <td className="text-muted py-2">Address 2:</td>
                      <td className="py-2">{company.address_line_2 || '—'}</td>
                    </tr>
                    <tr>
                      <td className="text-muted py-2">City:</td>
                      <td className="py-2">{company.city || '—'}</td>
                    </tr>
                    <tr>
                      <td className="text-muted py-2">State:</td>
                      <td className="py-2">{company.state || '—'}</td>
                    </tr>
                    <tr>
                      <td className="text-muted py-2">Country:</td>
                      <td className="py-2">{company.country || '—'}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'audit' && (
            <div>
              {auditLogs.length === 0 ? (
                <div className="text-center py-4 text-muted text-xs">
                  No configuration changes recorded yet for this company.
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-sm table-hover align-middle text-xs mb-0">
                    <thead className="table-light text-uppercase text-muted">
                      <tr>
                        <th className="py-2">Timestamp</th>
                        <th className="py-2">Action</th>
                        <th className="py-2">Entity</th>
                        <th className="py-2">Modified By</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((log) => (
                        <tr key={log.id}>
                          <td className="py-2 text-muted">{new Date(log.created_at).toLocaleString()}</td>
                          <td className="py-2 font-semibold">
                            <AuditActionBadge action={log.action} showIcon />
                          </td>
                          <td className="py-2 text-muted">{log.entity_type} {log.entity_id ? `(#${log.entity_id})` : ''}</td>
                          <td className="py-2 font-medium">{log.user_name || 'System / Admin'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
