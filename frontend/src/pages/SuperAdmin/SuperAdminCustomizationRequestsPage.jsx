import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { superAdminApi } from '../../api/superAdminApi'
import StatusBadge from '../../components/common/StatusBadge'
import CategoryBadge from '../../components/common/CategoryBadge'

export default function SuperAdminCustomizationRequestsPage() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedRequest, setSelectedRequest] = useState(null)
  const [reviewStatus, setReviewStatus] = useState('Pending')
  const [reviewNotes, setReviewNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadRequests()
  }, [statusFilter])

  const loadRequests = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await superAdminApi.listCustomizationRequests(statusFilter || null)
      setRequests(res || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load customization requests.')
    } finally {
      setLoading(false)
    }
  }

  const handleOpenReview = (req) => {
    setSelectedRequest(req)
    setReviewStatus(req.status || 'Pending')
    setReviewNotes(req.super_admin_notes || '')
  }

  const handleSaveReview = async (e) => {
    e.preventDefault()
    if (!selectedRequest) return

    setSubmitting(true)
    try {
      const updated = await superAdminApi.reviewCustomizationRequest(selectedRequest.id, {
        status: reviewStatus,
        super_admin_notes: reviewNotes.trim() || null,
      })
      setRequests((prev) =>
        prev.map((r) => (r.id === updated.id ? updated : r))
      )
      setSelectedRequest(null)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update customization request.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container-fluid px-4 py-4" style={{ maxWidth: '1600px' }}>
      {/* Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
        <div>
          <nav aria-label="breadcrumb" className="mb-1">
            <ol className="breadcrumb mb-0 text-xs">
              <li className="breadcrumb-item"><Link to="/dashboard">Platform</Link></li>
              <li className="breadcrumb-item active" aria-current="page">Customization Requests</li>
            </ol>
          </nav>
          <h1 className="h3 font-bold text-slate-900 mb-1">Company Customization Requests</h1>
          <p className="text-muted text-sm mb-0">
            Review feature, integration, and workflow customization proposals submitted by Company Administrators.
          </p>
        </div>

        <div className="d-flex gap-2">
          <button
            onClick={loadRequests}
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1.5 shadow-sm"
            disabled={loading}
          >
            <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-4" role="alert">
          <i className="bi bi-exclamation-triangle-fill" />
          <div className="text-sm">{error}</div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="card border-0 shadow-sm rounded-3 p-3 bg-white mb-4">
        <div className="d-flex flex-wrap gap-2 align-items-center">
          <span className="text-xs text-muted font-semibold text-uppercase me-2">Status:</span>
          {['', 'Pending', 'Under Review', 'Approved', 'Rejected', 'Implemented', 'Cancelled'].map((st) => (
            <button
              key={st}
              type="button"
              className={`btn btn-sm rounded-pill px-3 ${statusFilter === st ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => setStatusFilter(st)}
            >
              {st || 'All Requests'}
            </button>
          ))}
        </div>
      </div>

      {/* Requests Table */}
      <div className="card border-0 shadow-sm rounded-3 bg-white overflow-hidden">
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light text-muted text-xs text-uppercase">
              <tr>
                <th className="ps-4 py-3">ID & Title</th>
                <th className="py-3">Company</th>
                <th className="py-3">Requester</th>
                <th className="py-3">Category</th>
                <th className="py-3">Status</th>
                <th className="py-3">Submitted</th>
                <th className="text-end pe-4 py-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="7" className="text-center py-5 text-muted">
                    <div className="spinner-border spinner-border-sm text-primary me-2" role="status" />
                    Loading requests...
                  </td>
                </tr>
              ) : requests.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-5 text-muted">
                    <i className="bi bi-inbox fs-2 text-slate-300 d-block mb-2" />
                    No customization requests matching current filter.
                  </td>
                </tr>
              ) : (
                requests.map((r) => (
                  <tr key={r.id}>
                    <td className="ps-4 py-3">
                      <div className="font-semibold text-slate-900">{r.title}</div>
                      <div className="text-xs text-muted text-truncate" style={{ maxWidth: '350px' }}>
                        {r.description}
                      </div>
                    </td>
                    <td className="py-3">
                      <span className="badge bg-light text-slate-700 border px-2.5 py-1">
                        <i className="bi bi-building me-1 text-muted" />
                        {r.company_name}
                      </span>
                    </td>
                    <td className="py-3 font-medium text-slate-700 text-xs">{r.requester_name}</td>
                    <td className="py-3 text-xs">
                      <CategoryBadge category={r.category} />
                    </td>
                    <td className="py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="py-3 text-xs text-muted">
                      {new Date(r.created_at).toLocaleDateString()}
                    </td>
                    <td className="text-end pe-4 py-3">
                      <button
                        onClick={() => handleOpenReview(r)}
                        className="btn btn-sm btn-outline-primary py-1 px-2.5 text-xs shadow-sm"
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Review Modal */}
      {selectedRequest && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content border-0 shadow-lg rounded-3">
              <div className="modal-header border-bottom py-3 px-4">
                <div>
                  <h2 className="modal-title h5 font-bold text-slate-900 mb-0">Review Customization Request #{selectedRequest.id}</h2>
                  <span className="text-xs text-muted">Requested by {selectedRequest.requester_name} ({selectedRequest.company_name})</span>
                </div>
                <button type="button" className="btn-close" onClick={() => setSelectedRequest(null)} aria-label="Close" />
              </div>

              <form onSubmit={handleSaveReview}>
                <div className="modal-body p-4">
                  <div className="mb-3">
                    <label className="text-xs font-semibold text-muted text-uppercase d-block mb-1">Request Title</label>
                    <div className="font-semibold text-slate-900 p-2.5 bg-light rounded border text-sm">
                      {selectedRequest.title}
                    </div>
                  </div>

                  <div className="mb-3">
                    <label className="text-xs font-semibold text-muted text-uppercase d-block mb-1">Requested Behavior & Requirements</label>
                    <div className="text-slate-800 p-3 bg-light rounded border text-xs whitespace-pre-wrap" style={{ maxHeight: '140px', overflowY: 'auto' }}>
                      {selectedRequest.requested_behavior}
                    </div>
                  </div>

                  <div className="row g-3 mb-3">
                    <div className="col-12 col-sm-6">
                      <label className="form-label text-xs font-semibold text-slate-700">Category</label>
                      <input type="text" readOnly className="form-control form-control-sm bg-light" value={selectedRequest.category} />
                    </div>
                    <div className="col-12 col-sm-6">
                      <label className="form-label text-xs font-semibold text-slate-700">
                        Review Decision <span className="text-danger">*</span>
                      </label>
                      <select
                        className="form-select form-select-sm"
                        value={reviewStatus}
                        onChange={(e) => setReviewStatus(e.target.value)}
                      >
                        <option value="Pending">Pending</option>
                        <option value="Under Review">Under Review</option>
                        <option value="Approved">Approved</option>
                        <option value="Rejected">Rejected</option>
                        <option value="Implemented">Implemented</option>
                        <option value="Cancelled">Cancelled</option>
                      </select>
                    </div>
                  </div>

                  <div className="mb-3">
                    <label className="form-label text-xs font-semibold text-slate-700">
                      Super Admin Notes & Response
                    </label>
                    <textarea
                      rows={3}
                      className="form-control text-xs"
                      placeholder="Add implementation timeline, technical rationale, or questions for Company Admin..."
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                    />
                  </div>
                </div>

                <div className="modal-footer border-top py-2.5 px-4 d-flex justify-content-end gap-2">
                  <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setSelectedRequest(null)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-sm btn-primary px-3 shadow-sm" disabled={submitting}>
                    {submitting ? 'Saving...' : 'Save Decision'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
