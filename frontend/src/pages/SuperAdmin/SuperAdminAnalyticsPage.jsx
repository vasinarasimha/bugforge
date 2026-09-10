import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { superAdminApi } from '../../api/superAdminApi'
import SearchableSelect from '../../components/common/SearchableSelect'

export default function SuperAdminAnalyticsPage() {
  const [analytics, setAnalytics] = useState(null)
  const [companies, setCompanies] = useState([])
  const [selectedCompanyId, setSelectedCompanyId] = useState('')
  const [days, setDays] = useState(30)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadCompaniesList()
  }, [])

  useEffect(() => {
    loadAnalytics(selectedCompanyId ? Number(selectedCompanyId) : null, days)
  }, [selectedCompanyId, days])

  const loadCompaniesList = async () => {
    try {
      const res = await superAdminApi.listCompanies()
      setCompanies(res || [])
    } catch {
      setCompanies([])
    }
  }

  const loadAnalytics = async (companyId = null, timeDays = days) => {
    setLoading(true)
    setError('')
    try {
      const res = await superAdminApi.getPlatformAnalytics(companyId, timeDays)
      setAnalytics(res)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load platform analytics.')
    } finally {
      setLoading(false)
    }
  }

  const companyOptions = [
    { value: '', label: '🏢 All Companies (Platform Aggregate)' },
    ...companies.map((c) => ({
      value: c.id,
      label: `${c.name} (${c.is_active ? 'Active' : 'Inactive'})`,
    })),
  ]

  return (
    <div className="container-fluid px-4 py-4" style={{ maxWidth: '1600px' }}>
      {/* Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
        <div>
          <nav aria-label="breadcrumb" className="mb-1">
            <ol className="breadcrumb mb-0 text-xs">
              <li className="breadcrumb-item"><Link to="/dashboard">Platform</Link></li>
              <li className="breadcrumb-item active" aria-current="page">Platform Analytics</li>
            </ol>
          </nav>
          <h1 className="h3 font-bold text-slate-900 mb-1">Platform Analytics</h1>
          <p className="text-muted text-sm mb-0">
            Company-level platform growth, defect resolution velocities, and tenant quality benchmarks.
          </p>
        </div>

        {/* Scope & Date Filters */}
        <div className="d-flex align-items-center gap-3">
          {/* Time Range Pills */}
          <div>
            <label className="form-label text-xs font-semibold text-slate-700 mb-1 d-block">
              Time Range:
            </label>
            <div className="btn-group btn-group-sm" role="group">
              {[7, 30, 90].map((d) => (
                <button
                  key={d}
                  type="button"
                  className={`btn btn-sm ${days === d ? 'btn-primary' : 'btn-outline-secondary'}`}
                  onClick={() => setDays(d)}
                >
                  {d} Days
                </button>
              ))}
            </div>
          </div>

          {/* Company Filter Selector */}
          <div style={{ width: '280px' }}>
            <label className="form-label text-xs font-semibold text-slate-700 mb-1">
              Filter Scope:
            </label>
            <SearchableSelect
              options={companyOptions}
              value={selectedCompanyId}
              onChange={(val) => setSelectedCompanyId(val || '')}
              placeholder="Select company scope..."
              isClearable={false}
            />
          </div>

          <div style={{ marginTop: '22px' }}>
            <button
              onClick={() => loadAnalytics(selectedCompanyId ? Number(selectedCompanyId) : null, days)}
              className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1.5 shadow-sm"
              disabled={loading}
              title="Refresh database metrics"
            >
              <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-4" role="alert">
          <i className="bi bi-exclamation-triangle-fill" />
          <div className="text-sm">{error}</div>
        </div>
      )}

      {/* Overview Cards */}
      <div className="row g-3 mb-4">
        <div className="col-12 col-sm-4">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white h-100">
            <span className="text-muted text-xs text-uppercase font-semibold tracking-wider">Tenant Ecosystem</span>
            <div className="h3 font-bold text-slate-800 my-1">{analytics?.total_companies ?? '—'}</div>
            <div className="text-xs text-muted">
              <span className="text-success font-semibold">{analytics?.active_companies ?? 0} active</span>
              <span className="mx-1">•</span>
              <span>{analytics?.inactive_companies ?? 0} inactive</span>
            </div>
          </div>
        </div>

        <div className="col-12 col-sm-4">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white h-100">
            <span className="text-muted text-xs text-uppercase font-semibold tracking-wider">Total Defects Tracked</span>
            <div className="h3 font-bold text-primary my-1">
              {analytics?.company_metrics?.reduce((acc, m) => acc + m.defects_created, 0) ?? 0}
            </div>
            <div className="text-xs text-muted">Created across selected scope</div>
          </div>
        </div>

        <div className="col-12 col-sm-4">
          <div className="card border-0 shadow-sm rounded-3 p-3 bg-white h-100">
            <span className="text-muted text-xs text-uppercase font-semibold tracking-wider">Defects Resolved</span>
            <div className="h3 font-bold text-emerald-600 my-1">
              {analytics?.company_metrics?.reduce((acc, m) => acc + m.defects_resolved, 0) ?? 0}
            </div>
            <div className="text-xs text-muted">Successfully closed or resolved</div>
          </div>
        </div>
      </div>

      {/* Company Growth Trend (Last 30 Days) */}
      <div className="card border-0 shadow-sm rounded-3 p-4 bg-white mb-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <div>
            <h2 className="h6 font-bold text-slate-900 mb-0">Tenant Company Growth ({days} Days)</h2>
            <span className="text-xs text-muted">Cumulative registered organizations over time</span>
          </div>
        </div>

        <div className="p-3 bg-light rounded-2">
          {loading ? (
            <div className="text-center py-4 text-muted">
              <div className="spinner-border spinner-border-sm text-primary me-2" role="status" />
              Calculating metrics...
            </div>
          ) : !analytics?.growth_trend?.length ? (
            <div className="text-center py-4 text-muted text-xs">No trend data available.</div>
          ) : (
            <div className="d-flex align-items-end justify-content-between gap-2 pt-4" style={{ height: '180px' }}>
              {analytics.growth_trend.map((pt, i) => {
                const max = Math.max(...analytics.growth_trend.map((p) => p.companies_count), 1)
                const heightPercent = Math.max((pt.companies_count / max) * 100, 15)
                return (
                  <div key={i} className="d-flex flex-column align-items-center flex-grow-1" style={{ minWidth: '40px' }}>
                    <span className="text-xs font-bold text-slate-800 mb-1">{pt.companies_count}</span>
                    <div
                      className="w-100 rounded-top bg-primary"
                      style={{
                        height: `${heightPercent}%`,
                        opacity: 0.85,
                        maxWidth: '48px',
                        transition: 'height 0.4s ease',
                      }}
                    />
                    <span className="text-muted text-xs mt-2" style={{ fontSize: '0.72rem' }}>
                      {pt.date.slice(5)}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Company-wise Metrics Table */}
      <div className="card border-0 shadow-sm rounded-3 bg-white overflow-hidden">
        <div className="card-header bg-white border-bottom py-3 px-4">
          <h2 className="h6 font-bold text-slate-900 mb-0">Company Defect & Resolution Volume</h2>
          <span className="text-xs text-muted">
            Aggregated defect metrics and average resolution duration strictly at the company level.
          </span>
        </div>

        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light text-muted text-xs text-uppercase">
              <tr>
                <th className="ps-4 py-3">Tenant Company</th>
                <th className="text-end py-3">Defects Created</th>
                <th className="text-end py-3">Defects Resolved</th>
                <th className="text-end py-3">Open Defects</th>
                <th className="text-end py-3">Critical Defects</th>
                <th className="text-end pe-4 py-3">Avg Resolution Time</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6" className="text-center py-4 text-muted">
                    <div className="spinner-border spinner-border-sm text-primary me-2" role="status" />
                    Loading metrics...
                  </td>
                </tr>
              ) : !analytics?.company_metrics?.length ? (
                <tr>
                  <td colSpan="6" className="text-center py-4 text-muted">
                    No company metrics found.
                  </td>
                </tr>
              ) : (
                analytics.company_metrics.map((m) => (
                  <tr key={m.company_id}>
                    <td className="ps-4 py-3 font-semibold text-slate-800">
                      <div className="d-flex align-items-center gap-2">
                        <div className="w-7 h-7 rounded bg-primary-subtle text-primary d-flex align-items-center justify-content-center font-bold text-xs">
                          {m.company_name.charAt(0).toUpperCase()}
                        </div>
                        <span>{m.company_name}</span>
                      </div>
                    </td>
                    <td className="text-end py-3 font-medium text-slate-700">{m.defects_created}</td>
                    <td className="text-end py-3 font-semibold text-emerald-600">{m.defects_resolved}</td>
                    <td className="text-end py-3 font-semibold text-blue-600">{m.open_defects}</td>
                    <td className="text-end py-3">
                      {m.critical_defects > 0 ? (
                        <span className="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-0.5 rounded-pill">
                          {m.critical_defects}
                        </span>
                      ) : (
                        <span className="text-muted text-xs">0</span>
                      )}
                    </td>
                    <td className="text-end pe-4 py-3 font-semibold text-slate-800">
                      {m.avg_resolution_hours > 0 ? `${m.avg_resolution_hours} hrs` : '—'}
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
