import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { superAdminApi } from '../../api/superAdminApi'

export default function CompaniesPage() {
  const navigate = useNavigate()
  const [companies, setCompanies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [togglingId, setTogglingId] = useState(null)

  useEffect(() => {
    loadCompanies()
  }, [])

  const loadCompanies = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await superAdminApi.listCompanies()
      setCompanies(res || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load companies.')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleStatus = async (company, e) => {
    e.stopPropagation()
    const newStatus = !company.is_active
    const confirmMsg = newStatus
      ? `Are you sure you want to reactivate ${company.name}? Company users will regain access.`
      : `Are you sure you want to deactivate ${company.name}? Users will not be able to log in, but all historical records and data will be safely preserved.`

    if (!window.confirm(confirmMsg)) return

    setTogglingId(company.id)
    try {
      const updated = await superAdminApi.toggleCompanyStatus(company.id, newStatus)
      setCompanies((prev) =>
        prev.map((c) => (c.id === company.id ? { ...c, is_active: updated.is_active } : c))
      )
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to toggle company status.')
    } finally {
      setTogglingId(null)
    }
  }

  const filteredCompanies = companies.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      (c.email && c.email.toLowerCase().includes(search.toLowerCase())) ||
      (c.city && c.city.toLowerCase().includes(search.toLowerCase())) ||
      (c.country && c.country.toLowerCase().includes(search.toLowerCase()))

    if (statusFilter === 'active') return matchesSearch && c.is_active
    if (statusFilter === 'inactive') return matchesSearch && !c.is_active
    return matchesSearch
  })

  return (
    <div className="container-fluid px-4 py-4" style={{ maxWidth: '1600px' }}>
      {/* Page Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
        <div>
          <nav aria-label="breadcrumb" className="mb-1">
            <ol className="breadcrumb mb-0 text-xs">
              <li className="breadcrumb-item"><Link to="/dashboard">Platform</Link></li>
              <li className="breadcrumb-item active" aria-current="page">Companies</li>
            </ol>
          </nav>
          <h1 className="h3 font-bold text-slate-900 mb-1">Company Management</h1>
          <p className="text-muted text-sm mb-0">
            Create, configure, and oversee tenant companies across the BugForge ecosystem.
          </p>
        </div>

        <div className="d-flex gap-2">
          <button
            onClick={loadCompanies}
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
            <i className="bi bi-building-add" />
            <span>New Company</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-4" role="alert">
          <i className="bi bi-exclamation-triangle-fill" />
          <div>{error}</div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="card border-0 shadow-sm rounded-3 p-3 bg-white mb-4">
        <div className="row g-3 align-items-center">
          <div className="col-12 col-md-6 col-lg-5">
            <div className="input-group">
              <span className="input-group-text bg-white border-end-0 text-muted">
                <i className="bi bi-search" />
              </span>
              <input
                type="text"
                className="form-control border-start-0"
                placeholder="Search companies by name, email, city, country..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {search && (
                <button
                  className="btn btn-outline-secondary border-start-0 border"
                  type="button"
                  onClick={() => setSearch('')}
                >
                  <i className="bi bi-x" />
                </button>
              )}
            </div>
          </div>

          <div className="col-12 col-md-6 col-lg-4 d-flex gap-2 align-items-center">
            <span className="text-xs text-muted text-nowrap">Filter Status:</span>
            <div className="btn-group btn-group-sm w-100" role="group">
              <button
                type="button"
                className={`btn ${statusFilter === 'all' ? 'btn-primary' : 'btn-outline-secondary'}`}
                onClick={() => setStatusFilter('all')}
              >
                All ({companies.length})
              </button>
              <button
                type="button"
                className={`btn ${statusFilter === 'active' ? 'btn-success text-white' : 'btn-outline-secondary'}`}
                onClick={() => setStatusFilter('active')}
              >
                Active ({companies.filter((c) => c.is_active).length})
              </button>
              <button
                type="button"
                className={`btn ${statusFilter === 'inactive' ? 'btn-secondary text-white' : 'btn-outline-secondary'}`}
                onClick={() => setStatusFilter('inactive')}
              >
                Inactive ({companies.filter((c) => !c.is_active).length})
              </button>
            </div>
          </div>

          <div className="col-12 col-lg-3 text-lg-end text-muted text-xs">
            Showing <strong>{filteredCompanies.length}</strong> of {companies.length} companies
          </div>
        </div>
      </div>

      {/* Companies Table */}
      <div className="card border-0 shadow-sm rounded-3 bg-white overflow-hidden">
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light text-muted text-xs text-uppercase">
              <tr>
                <th className="ps-4 py-3">Company Details</th>
                <th className="py-3">Contact & Location</th>
                <th className="text-center py-3">Status</th>
                <th className="text-end py-3">Projects</th>
                <th className="text-end py-3">Defects</th>
                <th className="text-end py-3">Users</th>
                <th className="text-end py-3">Admins</th>
                <th className="text-end pe-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="8" className="text-center py-5 text-muted">
                    <div className="spinner-border spinner-border-sm text-primary me-2" role="status" />
                    Loading companies...
                  </td>
                </tr>
              ) : filteredCompanies.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-5 text-muted">
                    <div className="py-4">
                      <i className="bi bi-building fs-1 text-slate-300 d-block mb-2" />
                      <p className="mb-2 font-semibold text-slate-700">No companies found</p>
                      <p className="text-xs text-muted mb-3">No tenant organizations matched your criteria.</p>
                      <Link to="/super-admin/companies/create" className="btn btn-primary btn-sm">
                        <i className="bi bi-plus-lg me-1" /> Create First Company
                      </Link>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredCompanies.map((c) => (
                  <tr
                    key={c.id}
                    className="cursor-pointer transition-colors"
                    onClick={() => navigate(`/super-admin/companies/${c.id}`)}
                  >
                    <td className="ps-4 py-3 font-semibold text-slate-800">
                      <div>
                        <div className="text-slate-900 font-semibold">{c.name}</div>
                        {c.legal_name && <div className="text-xs text-muted">{c.legal_name}</div>}
                        <div className="text-xs text-muted font-normal">
                          Joined {new Date(c.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </td>

                    <td className="py-3">
                      <div className="text-xs text-slate-700">
                        {c.email && (
                          <div>
                            <i className="bi bi-envelope text-muted me-1.5" />
                            {c.email}
                          </div>
                        )}
                        {(c.city || c.country) && (
                          <div className="text-muted mt-0.5">
                            <i className="bi bi-geo-alt text-muted me-1.5" />
                            {[c.city, c.state, c.country].filter(Boolean).join(', ')}
                          </div>
                        )}
                        {c.website && (
                          <div className="text-muted mt-0.5">
                            <i className="bi bi-globe text-muted me-1.5" />
                            <span className="text-truncate d-inline-block" style={{ maxWidth: '180px' }}>
                              {c.website}
                            </span>
                          </div>
                        )}
                      </div>
                    </td>

                    <td className="text-center py-3" onClick={(e) => e.stopPropagation()}>
                      <div className="d-flex flex-column align-items-center gap-1">
                        <span
                          className={`badge rounded-pill text-xs px-2.5 py-1 ${
                            c.is_active
                              ? 'bg-success-subtle text-success border border-success-subtle'
                              : 'bg-secondary-subtle text-secondary border border-secondary-subtle'
                          }`}
                        >
                          {c.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <div className="form-check form-switch mt-1">
                          <input
                            className="form-check-input cursor-pointer"
                            type="checkbox"
                            role="switch"
                            checked={c.is_active}
                            disabled={togglingId === c.id}
                            onChange={(e) => handleToggleStatus(c, e)}
                            title={c.is_active ? 'Click to deactivate company' : 'Click to activate company'}
                          />
                        </div>
                      </div>
                    </td>

                    <td className="text-end py-3 font-semibold text-slate-700">{c.projects_count}</td>
                    <td className="text-end py-3 font-semibold text-slate-700">{c.issues_count}</td>
                    <td className="text-end py-3 font-medium text-slate-600">{c.users_count}</td>
                    <td className="text-end py-3 font-semibold text-blue-600">{c.admins_count}</td>

                    <td className="text-end pe-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <div className="d-flex justify-content-end gap-1.5">
                        <Link
                          to={`/super-admin/companies/${c.id}`}
                          className="btn btn-sm btn-light border py-1 px-2.5 text-xs text-slate-700 shadow-sm"
                          title="View Company Overview"
                        >
                          <i className="bi bi-eye me-1 text-primary" /> Overview
                        </Link>
                      </div>
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
