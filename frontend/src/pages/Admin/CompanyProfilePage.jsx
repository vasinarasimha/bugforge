import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { companyApi } from '../../api/companyApi'
import StatusBadge from '../../components/common/StatusBadge'
import CategoryBadge from '../../components/common/CategoryBadge'
import AuditActionBadge from '../../components/common/AuditActionBadge'
import CountryStateSelect from '../../components/CountryStateSelect/CountryStateSelect'

const COLOR_PRESETS = [
  '#3b82f6', '#8b5cf6', '#10b981', '#06b6d4', '#64748b',
  '#f59e0b', '#ef4444', '#ec4899', '#6366f1', '#14b8a6',
]

export default function CompanyProfilePage({ initialTab: propTab }) {
  const location = useLocation()
  const tabFromQuery = new URLSearchParams(location.search).get('tab')
  const [activeTab, setActiveTab] = useState(propTab || tabFromQuery || 'profile')

  useEffect(() => {
    if (propTab) {
      setActiveTab(propTab)
    } else if (tabFromQuery) {
      setActiveTab(tabFromQuery)
    }
  }, [propTab, tabFromQuery])
  const [profile, setProfile] = useState(null)
  const [settings, setSettings] = useState(null)
  const [statuses, setStatuses] = useState([])
  const [requests, setRequests] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  // Edit Profile State
  const [profileForm, setProfileForm] = useState({})
  const [savingProfile, setSavingProfile] = useState(false)

  // Status Modal State
  const [showStatusModal, setShowStatusModal] = useState(false)
  const [editingStatus, setEditingStatus] = useState(null)
  const [statusForm, setStatusForm] = useState({
    name: '',
    category: 'open',
    color: '#3b82f6',
    order_index: 0,
    is_initial: false,
    is_final: false,
  })
  const [savingStatus, setSavingStatus] = useState(false)

  // Customization Request Modal State
  const [showRequestModal, setShowRequestModal] = useState(false)
  const [requestForm, setRequestForm] = useState({
    title: '',
    category: 'Workflow',
    description: '',
    requested_behavior: '',
  })
  const [submittingRequest, setSubmittingRequest] = useState(false)

  // Settings Save State
  const [savingSettings, setSavingSettings] = useState(false)

  useEffect(() => {
    loadAllData()
  }, [])

  const loadAllData = async () => {
    setLoading(true)
    setError('')
    try {
      const [pRes, sRes, stRes, reqRes, logsRes] = await Promise.all([
        companyApi.getProfile(),
        companyApi.getSettings(),
        companyApi.listStatuses(),
        companyApi.listRequests(),
        companyApi.listAuditLogs(40),
      ])
      setProfile(pRes)
      setProfileForm(pRes || {})
      setSettings(sRes?.settings || {})
      setStatuses(stRes || [])
      setRequests(reqRes || [])
      setAuditLogs(logsRes || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load company configuration.')
    } finally {
      setLoading(false)
    }
  }

  // ── Save Profile ──
  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setSavingProfile(true)
    setSuccessMsg('')
    try {
      const updated = await companyApi.updateProfile(profileForm)
      setProfile(updated)
      setSuccessMsg('Company profile updated successfully.')
      const logs = await companyApi.listAuditLogs(40)
      setAuditLogs(logs)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update company profile.')
    } finally {
      setSavingProfile(false)
    }
  }

  // ── Save Status (Add or Edit) ──
  const handleOpenStatusModal = (statusObj = null) => {
    if (statusObj) {
      setEditingStatus(statusObj)
      setStatusForm({
        name: statusObj.name,
        category: statusObj.category || 'open',
        color: statusObj.color || '#3b82f6',
        order_index: statusObj.order_index ?? 0,
        is_initial: statusObj.is_initial || false,
        is_final: statusObj.is_final || false,
      })
    } else {
      setEditingStatus(null)
      setStatusForm({
        name: '',
        category: 'open',
        color: '#3b82f6',
        order_index: statuses.length + 1,
        is_initial: false,
        is_final: false,
      })
    }
    setShowStatusModal(true)
  }

  const handleSaveStatus = async (e) => {
    e.preventDefault()
    setSavingStatus(true)
    try {
      if (editingStatus) {
        await companyApi.updateStatus(editingStatus.id, statusForm)
        setSuccessMsg(`Status "${statusForm.name}" updated successfully.`)
      } else {
        await companyApi.createStatus(statusForm)
        setSuccessMsg(`Status "${statusForm.name}" created and now available across all company workflows!`)
      }
      setShowStatusModal(false)
      const [newStatuses, newLogs] = await Promise.all([
        companyApi.listStatuses(),
        companyApi.listAuditLogs(40),
      ])
      setStatuses(newStatuses)
      setAuditLogs(newLogs)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to save status.')
    } finally {
      setSavingStatus(false)
    }
  }

  // ── Delete or Deactivate Status ──
  const handleDeleteStatus = async (statusObj) => {
    const hasIssues = statusObj.issue_count > 0
    const confirmPrompt = hasIssues
      ? `Notice: ${statusObj.issue_count} issue(s) currently use status "${statusObj.name}".\n\nIt will be DEACTIVATED so new issues cannot select it, while all historical records retain it.\n\nProceed?`
      : `Are you sure you want to permanently delete status "${statusObj.name}"? No issues currently use this status.`

    if (!window.confirm(confirmPrompt)) return

    try {
      const res = await companyApi.deleteOrDeactivateStatus(statusObj.id)
      setSuccessMsg(res.message)
      const [newStatuses, newLogs] = await Promise.all([
        companyApi.listStatuses(),
        companyApi.listAuditLogs(40),
      ])
      setStatuses(newStatuses)
      setAuditLogs(newLogs)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete or deactivate status.')
    }
  }

  // ── Toggle Status Active ──
  const handleToggleStatusActive = async (statusObj) => {
    const newActive = !statusObj.is_active
    try {
      await companyApi.updateStatus(statusObj.id, { is_active: newActive })
      setStatuses((prev) =>
        prev.map((s) => (s.id === statusObj.id ? { ...s, is_active: newActive } : s))
      )
      setSuccessMsg(`Status "${statusObj.name}" is now ${newActive ? 'active' : 'inactive'}.`)
      const logs = await companyApi.listAuditLogs(40)
      setAuditLogs(logs)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update status state.')
    }
  }

  // ── Save Settings ──
  const handleSaveSettings = async () => {
    setSavingSettings(true)
    setSuccessMsg('')
    try {
      const res = await companyApi.updateSettings(settings)
      setSettings(res.settings)
      setSuccessMsg('Company settings and workflow preferences saved successfully.')
      const logs = await companyApi.listAuditLogs(40)
      setAuditLogs(logs)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update settings.')
    } finally {
      setSavingSettings(false)
    }
  }

  // ── Submit Customization Request ──
  const handleSubmitRequest = async (e) => {
    e.preventDefault()
    setSubmittingRequest(true)
    try {
      await companyApi.submitRequest(requestForm)
      setSuccessMsg('Your customization request was submitted to the Super Admin team.')
      setShowRequestModal(false)
      setRequestForm({
        title: '',
        category: 'Workflow',
        description: '',
        requested_behavior: '',
      })
      const [newRequests, newLogs] = await Promise.all([
        companyApi.listRequests(),
        companyApi.listAuditLogs(40),
      ])
      setRequests(newRequests)
      setAuditLogs(newLogs)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to submit customization request.')
    } finally {
      setSubmittingRequest(false)
    }
  }

  if (loading) {
    return (
      <div className="container-fluid px-4 py-5 text-center text-muted">
        <div className="spinner-border text-primary mb-3" role="status" />
        <div>Loading company profile and configuration...</div>
      </div>
    )
  }

  return (
    <div className="container-fluid px-4 py-4" style={{ maxWidth: '1600px' }}>
      {/* Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-primary-subtle text-primary border border-primary-subtle px-2.5 py-1 rounded-pill text-xs font-semibold">
              <i className="bi bi-gear-wide-connected me-1" /> Tenant Settings
            </span>
          </div>
          <h1 className="h3 font-bold text-slate-900 mb-1">{profile?.name || 'Company Profile'}</h1>
          <p className="text-muted text-sm mb-0">
            Configure dynamic issue statuses, workflows, regional settings, and platform feature toggles.
          </p>
        </div>

        <div className="d-flex gap-2">
          <button
            onClick={() => setShowRequestModal(true)}
            className="btn btn-outline-primary btn-sm d-flex align-items-center gap-1.5 shadow-sm"
          >
            <i className="bi bi-lightbulb" />
            <span>Request New Feature</span>
          </button>
        </div>
      </div>

      {successMsg && (
        <div className="alert alert-success alert-dismissible fade show d-flex align-items-center gap-2 mb-4" role="alert">
          <i className="bi bi-check-circle-fill" />
          <div className="text-sm">{successMsg}</div>
          <button type="button" className="btn-close" onClick={() => setSuccessMsg('')} aria-label="Close" />
        </div>
      )}

      {error && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-4" role="alert">
          <i className="bi bi-exclamation-triangle-fill" />
          <div className="text-sm">{error}</div>
        </div>
      )}

      {/* Main Tabs Container */}
      <div className="card border-0 shadow-sm rounded-3 bg-white overflow-hidden">
        <div className="card-header bg-white border-bottom px-4 pt-3 pb-0">
          <ul className="nav nav-tabs card-header-tabs border-0">
            <li className="nav-item">
              <button
                className={`nav-link text-xs font-semibold py-2.5 px-3.5 border-0 ${activeTab === 'profile' ? 'active text-primary border-bottom border-2 border-primary bg-transparent' : 'text-muted'}`}
                onClick={() => setActiveTab('profile')}
              >
                <i className="bi bi-building me-1.5" /> Company Profile
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-link text-xs font-semibold py-2.5 px-3.5 border-0 ${activeTab === 'statuses' ? 'active text-primary border-bottom border-2 border-primary bg-transparent' : 'text-muted'}`}
                onClick={() => setActiveTab('statuses')}
              >
                <i className="bi bi-diagram-2 me-1.5" /> Issue Workflows & Statuses ({statuses.length})
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-link text-xs font-semibold py-2.5 px-3.5 border-0 ${activeTab === 'settings' ? 'active text-primary border-bottom border-2 border-primary bg-transparent' : 'text-muted'}`}
                onClick={() => setActiveTab('settings')}
              >
                <i className="bi bi-sliders me-1.5" /> Workflow Defaults & Features
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-link text-xs font-semibold py-2.5 px-3.5 border-0 ${activeTab === 'requests' ? 'active text-primary border-bottom border-2 border-primary bg-transparent' : 'text-muted'}`}
                onClick={() => setActiveTab('requests')}
              >
                <i className="bi bi-lightbulb me-1.5" /> Customization Requests ({requests.length})
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
          {/* TAB 1: Company Profile */}
          {activeTab === 'profile' && (
            <form onSubmit={handleSaveProfile}>
              <div className="row g-3" style={{ maxWidth: '900px' }}>
                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Company Name</label>
                  <input
                    type="text"
                    required
                    className="form-control form-control-sm"
                    value={profileForm.name || ''}
                    onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Legal Name</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={profileForm.legal_name || ''}
                    onChange={(e) => setProfileForm({ ...profileForm, legal_name: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Corporate Email</label>
                  <input
                    type="email"
                    className="form-control form-control-sm"
                    value={profileForm.email || ''}
                    onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Phone</label>
                  <input
                    type="tel"
                    className="form-control form-control-sm"
                    value={profileForm.phone || ''}
                    onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Website</label>
                  <input
                    type="url"
                    className="form-control form-control-sm"
                    value={profileForm.website || ''}
                    onChange={(e) => setProfileForm({ ...profileForm, website: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Timezone</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={profileForm.timezone || ''}
                    onChange={(e) => setProfileForm({ ...profileForm, timezone: e.target.value })}
                  />
                </div>

                <div className="col-12">
                  <label className="form-label text-xs font-semibold text-slate-700">Address Line 1</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={profileForm.address_line_1 || ''}
                    onChange={(e) => setProfileForm({ ...profileForm, address_line_1: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-4">
                  <label className="form-label text-xs font-semibold text-slate-700">City</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={profileForm.city || ''}
                    onChange={(e) => setProfileForm({ ...profileForm, city: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-8">
                  <CountryStateSelect
                    country={profileForm.country || ''}
                    countryCode={profileForm.country_code || ''}
                    state={profileForm.state || ''}
                    stateCode={profileForm.state_code || ''}
                    onChange={({ country, country_code, state, state_code }) =>
                      setProfileForm({
                        ...profileForm,
                        country,
                        country_code,
                        state,
                        state_code,
                      })
                    }
                  />
                </div>

                <div className="col-12 d-flex justify-content-end mt-4">
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm px-4 shadow-sm"
                    disabled={savingProfile}
                  >
                    {savingProfile ? 'Saving...' : 'Save Profile Changes'}
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* TAB 2: Issue Workflows & Dynamic Statuses */}
          {activeTab === 'statuses' && (
            <div>
              <div className="d-flex justify-content-between align-items-center mb-3">
                <div>
                  <h2 className="h6 font-bold text-slate-900 mb-0">Customizable Issue Statuses</h2>
                  <p className="text-muted text-xs mb-0">
                    Define, reorder, and activate the exact lifecycle statuses used across defect tracking.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleOpenStatusModal()}
                  className="btn btn-primary btn-sm d-flex align-items-center gap-1.5 shadow-sm"
                >
                  <i className="bi bi-plus-lg" />
                  <span>Add Status</span>
                </button>
              </div>

              <div className="table-responsive border rounded-3">
                <table className="table table-hover align-middle mb-0 text-sm">
                  <thead className="table-light text-muted text-xs text-uppercase">
                    <tr>
                      <th className="ps-4 py-3">Order</th>
                      <th className="py-3">Status Name & Badge</th>
                      <th className="py-3">Category</th>
                      <th className="py-3">Initial / Final</th>
                      <th className="py-3 text-center">Active</th>
                      <th className="py-3 text-end">Issues Referencing</th>
                      <th className="py-3 text-end pe-4">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statuses.map((s) => (
                      <tr key={s.id} className={!s.is_active ? 'opacity-75 bg-light' : ''}>
                        <td className="ps-4 py-3 font-semibold text-muted text-xs">
                          #{s.order_index}
                        </td>
                        <td className="py-3">
                          <div className="d-flex align-items-center gap-2">
                            <StatusBadge status={s} />
                            {!s.is_active && (
                              <span className="badge bg-secondary-subtle text-secondary border text-xs">
                                Inactive
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3">
                          <CategoryBadge category={s.category} />
                        </td>
                        <td className="py-3 text-xs">
                          {s.is_initial && (
                            <span className="badge bg-primary-subtle text-primary me-1">Initial Status</span>
                          )}
                          {s.is_final && (
                            <span className="badge bg-dark-subtle text-dark">Resolution / Final</span>
                          )}
                          {!s.is_initial && !s.is_final && <span className="text-muted">—</span>}
                        </td>
                        <td className="py-3 text-center">
                          <div className="form-check form-switch d-inline-block">
                            <input
                              className="form-check-input cursor-pointer"
                              type="checkbox"
                              role="switch"
                              checked={s.is_active}
                              onChange={() => handleToggleStatusActive(s)}
                              title={s.is_active ? 'Deactivate for new issues' : 'Activate for issues'}
                            />
                          </div>
                        </td>
                        <td className="py-3 text-end font-semibold text-slate-700">
                          {s.issue_count}
                        </td>
                        <td className="py-3 text-end pe-4">
                          <div className="d-flex justify-content-end gap-1.5">
                            <button
                              type="button"
                              onClick={() => handleOpenStatusModal(s)}
                              className="btn btn-sm btn-light border py-1 px-2.5 text-xs text-slate-700"
                            >
                              <i className="bi bi-pencil me-1" /> Edit
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteStatus(s)}
                              className="btn btn-sm btn-outline-danger py-1 px-2 text-xs"
                              title={s.issue_count > 0 ? 'Deactivate with dependency warning' : 'Delete status'}
                            >
                              <i className="bi bi-trash" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: Workflow Defaults & Features */}
          {activeTab === 'settings' && (
            <div style={{ maxWidth: '900px' }}>
              <div className="d-flex justify-content-between align-items-center mb-4 pb-2 border-bottom">
                <div>
                  <h2 className="h6 font-bold text-slate-900 mb-0">Workflow Rules & Platform Capabilities</h2>
                  <span className="text-xs text-muted">Customize resolution requirements and intelligent feature toggles</span>
                </div>
                <button
                  type="button"
                  onClick={handleSaveSettings}
                  disabled={savingSettings}
                  className="btn btn-primary btn-sm px-4 shadow-sm"
                >
                  {savingSettings ? 'Saving...' : 'Save Configuration'}
                </button>
              </div>

              <div className="row g-4">
                {/* Workflow Rules */}
                <div className="col-12">
                  <h3 className="text-xs font-bold text-slate-700 text-uppercase tracking-wider mb-2">
                    Resolution & Quality Gates
                  </h3>
                  <div className="card p-3 border rounded-2 bg-light">
                    <div className="form-check form-switch mb-3">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="reqResNotes"
                        checked={settings?.workflow?.require_resolution_notes ?? true}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            workflow: { ...settings?.workflow, require_resolution_notes: e.target.checked },
                          })
                        }
                      />
                      <label className="form-check-label text-xs font-semibold text-slate-800" htmlFor="reqResNotes">
                        Mandatory Resolution Notes
                      </label>
                      <div className="text-xs text-muted">
                        Require developers to provide concrete fix and resolution notes before moving a defect to Resolved.
                      </div>
                    </div>

                    <div className="form-check form-switch">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="reqRootCause"
                        checked={settings?.workflow?.require_root_cause ?? true}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            workflow: { ...settings?.workflow, require_root_cause: e.target.checked },
                          })
                        }
                      />
                      <label className="form-check-label text-xs font-semibold text-slate-800" htmlFor="reqRootCause">
                        Mandatory Root-Cause Categorization
                      </label>
                      <div className="text-xs text-muted">
                        Require identification of root causes (e.g. Logic Error, Race Condition) during defect lifecycle.
                      </div>
                    </div>
                  </div>
                </div>

                {/* Feature Toggles */}
                <div className="col-12">
                  <h3 className="text-xs font-bold text-slate-700 text-uppercase tracking-wider mb-2">
                    Intelligent Platform Features
                  </h3>
                  <div className="card p-3 border rounded-2 bg-light">
                    <div className="form-check form-switch mb-3">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="featAiRootCause"
                        checked={settings?.features?.ai_root_cause_analysis ?? true}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            features: { ...settings?.features, ai_root_cause_analysis: e.target.checked },
                          })
                        }
                      />
                      <label className="form-check-label text-xs font-semibold text-slate-800" htmlFor="featAiRootCause">
                        AI Root-Cause Troubleshooting & Hypotheses
                      </label>
                      <div className="text-xs text-muted">
                        Enable intelligent hypothesis generation and multi-step diagnostic questions during defect creation.
                      </div>
                    </div>

                    <div className="form-check form-switch mb-3">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="featSemanticSearch"
                        checked={settings?.features?.semantic_search ?? true}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            features: { ...settings?.features, semantic_search: e.target.checked },
                          })
                        }
                      />
                      <label className="form-check-label text-xs font-semibold text-slate-800" htmlFor="featSemanticSearch">
                        Hybrid & Semantic Vector Search
                      </label>
                      <div className="text-xs text-muted">
                        Combine keyword matching with pgvector embeddings for natural-language search across company issues.
                      </div>
                    </div>

                    <div className="form-check form-switch">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="featDuplicateDetection"
                        checked={settings?.features?.duplicate_detection ?? true}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            features: { ...settings?.features, duplicate_detection: e.target.checked },
                          })
                        }
                      />
                      <label className="form-check-label text-xs font-semibold text-slate-800" htmlFor="featDuplicateDetection">
                        Real-time Similar & Duplicate Defect Warning
                      </label>
                      <div className="text-xs text-muted">
                        Alert reporters when a defect with matching semantic patterns already exists in the company backlog.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: Customization Requests */}
          {activeTab === 'requests' && (
            <div>
              <div className="d-flex justify-content-between align-items-center mb-3">
                <div>
                  <h2 className="h6 font-bold text-slate-900 mb-0">Feature & Customization Requests</h2>
                  <p className="text-muted text-xs mb-0">
                    Proposals submitted to the platform Super Admin for new workflows or custom platform integrations.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowRequestModal(true)}
                  className="btn btn-primary btn-sm d-flex align-items-center gap-1.5 shadow-sm"
                >
                  <i className="bi bi-plus-lg" />
                  <span>New Request</span>
                </button>
              </div>

              {requests.length === 0 ? (
                <div className="text-center py-5 border rounded-3 text-muted">
                  <i className="bi bi-lightbulb fs-2 text-slate-300 d-block mb-2" />
                  <p className="font-semibold text-slate-700 mb-1">No customization requests yet</p>
                  <p className="text-xs text-muted mb-3">
                    Need new platform behavior that requires custom engineering? Submit a formal proposal.
                  </p>
                  <button
                    type="button"
                    onClick={() => setShowRequestModal(true)}
                    className="btn btn-primary btn-sm"
                  >
                    Submit First Request
                  </button>
                </div>
              ) : (
                <div className="table-responsive border rounded-3">
                  <table className="table table-hover align-middle mb-0 text-xs">
                    <thead className="table-light text-muted text-uppercase">
                      <tr>
                        <th className="ps-4 py-3">Title & Summary</th>
                        <th className="py-3">Category</th>
                        <th className="py-3">Status</th>
                        <th className="py-3">Super Admin Response</th>
                        <th className="py-3 text-end pe-4">Submitted</th>
                      </tr>
                    </thead>
                    <tbody>
                      {requests.map((r) => (
                        <tr key={r.id}>
                          <td className="ps-4 py-3">
                            <div className="font-semibold text-slate-900 text-sm">{r.title}</div>
                            <div className="text-muted mt-0.5">{r.description}</div>
                          </td>
                          <td className="py-3">
                            <CategoryBadge category={r.category} />
                          </td>
                          <td className="py-3">
                            <StatusBadge status={r.status} />
                          </td>
                          <td className="py-3" style={{ maxWidth: '300px' }}>
                            {r.super_admin_notes ? (
                              <div className="p-2 bg-light border rounded text-slate-800">
                                <i className="bi bi-chat-quote-fill text-primary me-1" />
                                {r.super_admin_notes}
                              </div>
                            ) : (
                              <span className="text-muted italic">Awaiting review</span>
                            )}
                          </td>
                          <td className="py-3 text-end pe-4 text-muted">
                            {new Date(r.created_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 5: Audit Log */}
          {activeTab === 'audit' && (
            <div>
              {auditLogs.length === 0 ? (
                <div className="text-center py-5 border rounded-3 text-muted text-xs">
                  No configuration audit events recorded yet.
                </div>
              ) : (
                <div className="table-responsive border rounded-3">
                  <table className="table table-sm table-hover align-middle mb-0 text-xs">
                    <thead className="table-light text-muted text-uppercase">
                      <tr>
                        <th className="ps-4 py-2.5">Timestamp</th>
                        <th className="py-2.5">Action</th>
                        <th className="py-2.5">Target Entity</th>
                        <th className="py-2.5">Changed By</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((log) => (
                        <tr key={log.id}>
                          <td className="ps-4 py-2 text-muted">{new Date(log.created_at).toLocaleString()}</td>
                          <td className="py-2 font-semibold">
                            <AuditActionBadge action={log.action} showIcon />
                          </td>
                          <td className="py-2 text-muted">{log.entity_type} {log.entity_id ? `(#${log.entity_id})` : ''}</td>
                          <td className="py-2 font-medium">{log.user_name || 'Admin'}</td>
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

      {/* Status Modal (Create / Edit) */}
      {showStatusModal && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow-lg rounded-3">
              <div className="modal-header border-bottom py-3 px-4">
                <h2 className="modal-title h6 font-bold text-slate-900 mb-0">
                  {editingStatus ? `Edit Status: ${editingStatus.name}` : 'Add Company Issue Status'}
                </h2>
                <button type="button" className="btn-close" onClick={() => setShowStatusModal(false)} aria-label="Close" />
              </div>
              <form onSubmit={handleSaveStatus}>
                <div className="modal-body p-4">
                  <div className="mb-3">
                    <label className="form-label text-xs font-semibold text-slate-700">
                      Status Display Name <span className="text-danger">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      className="form-control form-control-sm"
                      placeholder="e.g. QA Testing, Security Review"
                      value={statusForm.name}
                      onChange={(e) => setStatusForm({ ...statusForm, name: e.target.value })}
                    />
                  </div>

                  <div className="row g-3 mb-3">
                    <div className="col-6">
                      <label className="form-label text-xs font-semibold text-slate-700">Category</label>
                      <select
                        className="form-select form-select-sm"
                        value={statusForm.category}
                        onChange={(e) => setStatusForm({ ...statusForm, category: e.target.value })}
                      >
                        <option value="open">Open (Initial / Backlog)</option>
                        <option value="in_progress">In Progress (Active Work)</option>
                        <option value="resolved">Resolved (Fix Complete)</option>
                        <option value="closed">Closed (Verified / Final)</option>
                      </select>
                    </div>

                    <div className="col-6">
                      <label className="form-label text-xs font-semibold text-slate-700">Order Index</label>
                      <input
                        type="number"
                        min="0"
                        className="form-control form-control-sm"
                        value={statusForm.order_index}
                        onChange={(e) => setStatusForm({ ...statusForm, order_index: parseInt(e.target.value) || 0 })}
                      />
                    </div>
                  </div>

                  {/* Color Palette */}
                  <div className="mb-3">
                    <label className="form-label text-xs font-semibold text-slate-700 d-block mb-1.5">
                      Badge Color
                    </label>
                    <div className="d-flex align-items-center gap-2 mb-2">
                      {COLOR_PRESETS.map((c) => (
                        <button
                          key={c}
                          type="button"
                          className="w-6 h-6 rounded-circle border-0 cursor-pointer"
                          style={{
                            backgroundColor: c,
                            outline: statusForm.color === c ? `2px solid ${c}` : 'none',
                            outlineOffset: '2px',
                          }}
                          onClick={() => setStatusForm({ ...statusForm, color: c })}
                        />
                      ))}
                    </div>
                    <div className="d-flex align-items-center gap-2">
                      <input
                        type="color"
                        className="form-control form-control-color border-0 p-0"
                        style={{ width: '32px', height: '32px' }}
                        value={statusForm.color}
                        onChange={(e) => setStatusForm({ ...statusForm, color: e.target.value })}
                      />
                      <span className="text-xs text-muted font-mono">{statusForm.color}</span>
                    </div>
                  </div>

                  {/* Initial / Final Flags */}
                  <div className="card p-3 bg-light border rounded-2 mb-2">
                    <div className="form-check mb-2">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="chkIsInitial"
                        checked={statusForm.is_initial}
                        onChange={(e) => setStatusForm({ ...statusForm, is_initial: e.target.checked })}
                      />
                      <label className="form-check-label text-xs font-semibold text-slate-800" htmlFor="chkIsInitial">
                        Default Initial Status for Newly Reported Issues
                      </label>
                    </div>

                    <div className="form-check">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="chkIsFinal"
                        checked={statusForm.is_final}
                        onChange={(e) => setStatusForm({ ...statusForm, is_final: e.target.checked })}
                      />
                      <label className="form-check-label text-xs font-semibold text-slate-800" htmlFor="chkIsFinal">
                        Terminal Status (Treated as Closed in Analytics)
                      </label>
                    </div>
                  </div>
                </div>

                <div className="modal-footer border-top py-2.5 px-4 d-flex justify-content-end gap-2">
                  <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setShowStatusModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-sm btn-primary px-3 shadow-sm" disabled={savingStatus}>
                    {savingStatus ? 'Saving...' : 'Save Status'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Customization Request Modal */}
      {showRequestModal && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content border-0 shadow-lg rounded-3">
              <div className="modal-header border-bottom py-3 px-4">
                <h2 className="modal-title h6 font-bold text-slate-900 mb-0">Submit Customization Request</h2>
                <button type="button" className="btn-close" onClick={() => setShowRequestModal(false)} aria-label="Close" />
              </div>
              <form onSubmit={handleSubmitRequest}>
                <div className="modal-body p-4">
                  <div className="alert alert-info py-2 px-3 text-xs mb-3">
                    <i className="bi bi-info-circle-fill me-1.5" />
                    <strong>Note:</strong> Configuration allows customizing statuses and defaults. If your team requires new platform logic (e.g. third-party webhooks, custom verification gates), submit your requirement here to the Super Admin platform team.
                  </div>

                  <div className="row g-3 mb-3">
                    <div className="col-12 col-sm-8">
                      <label className="form-label text-xs font-semibold text-slate-700">
                        Proposal Title <span className="text-danger">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        className="form-control form-control-sm"
                        placeholder="e.g. Automated CI/CD Webhook on Verified Status"
                        value={requestForm.title}
                        onChange={(e) => setRequestForm({ ...requestForm, title: e.target.value })}
                      />
                    </div>
                    <div className="col-12 col-sm-4">
                      <label className="form-label text-xs font-semibold text-slate-700">Category</label>
                      <select
                        className="form-select form-select-sm"
                        value={requestForm.category}
                        onChange={(e) => setRequestForm({ ...requestForm, category: e.target.value })}
                      >
                        <option value="Workflow">Workflow</option>
                        <option value="Integration">Integration</option>
                        <option value="Security">Security</option>
                        <option value="Reporting">Reporting</option>
                        <option value="AI Intelligence">AI Intelligence</option>
                      </select>
                    </div>
                  </div>

                  <div className="mb-3">
                    <label className="form-label text-xs font-semibold text-slate-700">
                      Problem Statement / Context <span className="text-danger">*</span>
                    </label>
                    <textarea
                      rows={3}
                      required
                      className="form-control text-xs"
                      placeholder="Describe the current operational limitation or business rationale..."
                      value={requestForm.description}
                      onChange={(e) => setRequestForm({ ...requestForm, description: e.target.value })}
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label text-xs font-semibold text-slate-700">
                      Desired Platform Behavior & Logic <span className="text-danger">*</span>
                    </label>
                    <textarea
                      rows={4}
                      required
                      className="form-control text-xs"
                      placeholder="Specify the exact trigger, expected system behavior, conditions, and outcome..."
                      value={requestForm.requested_behavior}
                      onChange={(e) => setRequestForm({ ...requestForm, requested_behavior: e.target.value })}
                    />
                  </div>
                </div>

                <div className="modal-footer border-top py-2.5 px-4 d-flex justify-content-end gap-2">
                  <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setShowRequestModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-sm btn-primary px-3 shadow-sm" disabled={submittingRequest}>
                    {submittingRequest ? 'Submitting...' : 'Submit Proposal'}
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
