import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { superAdminApi } from '../../api/superAdminApi'
import StatusBadge from '../../components/common/StatusBadge'

export default function SuperAdminDashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await superAdminApi.getPlatformDashboard()
      setData(res)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load platform dashboard.')
    } finally {
      setLoading(false)
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
                      <div className="d-flex align-items-center gap-2.5">
                        <div className="w-8 h-8 rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center font-bold text-xs">
                          {c.company_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-slate-900 font-semibold">{c.company_name}</div>
                          <div className="text-xs text-muted">ID: {c.company_id}</div>
                        </div>
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
    </div>
  )
}
