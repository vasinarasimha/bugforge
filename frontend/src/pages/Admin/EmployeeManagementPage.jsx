import { useEffect, useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import {
  getEmployees,
  createEmployee,
  updateEmployee,
  deactivateEmployee,
  getRoles,
} from '../../services/employeeService'
import PhoneInput from '../../components/PhoneInput/PhoneInput'
import CountryStateSelect from '../../components/CountryStateSelect/CountryStateSelect'
import Toast from '../../components/Toast/Toast'

const ROLE_BADGE_CLASSES = {
  'Super Admin': 'badge-role-super-admin',
  Admin: 'badge-role-admin',
  Developer: 'badge-role-developer',
  QA: 'badge-role-qa',
  Reporter: 'badge-role-reporter',
  'Project Manager': 'badge-role-pm',
  'Team Leader': 'badge-role-team-leader',
}

export default function EmployeeManagementPage() {
  const { user: currentAdmin } = useAuth()
  const [viewMode, setViewMode] = useState('list') // 'list' | 'edit'
  const [employees, setEmployees] = useState([])
  const [totalEmployees, setTotalEmployees] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedRole, setSelectedRole] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('')
  const [rolesList, setRolesList] = useState([])
  const [toast, setToast] = useState({ message: '', variant: 'success' })

  // Modal States for List View
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showViewModal, setShowViewModal] = useState(false)
  const [showDeactivateModal, setShowDeactivateModal] = useState(false)
  const [selectedEmployee, setSelectedEmployee] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formErrors, setFormErrors] = useState({})

  // Form Data (shared for Create and Edit)
  const initialForm = {
    full_name: '',
    email: '',
    password: '',
    role: 'Developer',
    job_title: '',
    department: '',
    mobile_country_code: '+91',
    mobile_number: '',
    address_line_1: '',
    address_line_2: '',
    city: '',
    state: '',
    state_code: '',
    country: '',
    country_code: '',
    is_active: true,
  }
  const [formData, setFormData] = useState(initialForm)

  useEffect(() => {
    fetchRoles()
  }, [])

  useEffect(() => {
    if (viewMode === 'list') {
      fetchEmployees()
    }
  }, [search, selectedRole, selectedStatus, viewMode])

  const fetchRoles = async () => {
    try {
      const { data } = await getRoles()
      setRolesList(data)
    } catch {
      setRolesList([
        { name: 'Super Admin' },
        { name: 'Admin' },
        { name: 'Developer' },
        { name: 'QA' },
        { name: 'Reporter' },
        { name: 'Project Manager' },
        { name: 'Team Leader' },
      ])
    }
  }

  const fetchEmployees = async () => {
    setIsLoading(true)
    try {
      const params = {
        limit: 100,
        offset: 0,
      }
      if (search.trim()) params.search = search.trim()
      if (selectedRole) params.role = selectedRole
      if (selectedStatus !== '') params.is_active = selectedStatus === 'active'

      const { data } = await getEmployees(params)
      setEmployees(data.data || [])
      setTotalEmployees(data.total || 0)
    } catch (err) {
      setToast({
        message: err.response?.data?.detail || 'Failed to load employees list.',
        variant: 'danger',
      })
    } finally {
      setIsLoading(false)
    }
  }

  // Open Create Modal
  const handleOpenCreate = () => {
    setFormData(initialForm)
    setFormErrors({})
    setShowCreateModal(true)
  }

  // Switch to Full Main Content Edit View
  const handleOpenEdit = (emp) => {
    setSelectedEmployee(emp)
    setFormData({
      full_name: emp.full_name || '',
      email: emp.email || '',
      password: '', // Blank unless admin specifically wants to reset
      role: emp.role || emp.roles?.[0]?.name || 'Developer',
      job_title: emp.job_title || '',
      department: emp.department || '',
      mobile_country_code: emp.mobile_country_code || '+91',
      mobile_number: emp.mobile_number || '',
      address_line_1: emp.address_line_1 || '',
      address_line_2: emp.address_line_2 || '',
      city: emp.city || '',
      state: emp.state || '',
      state_code: emp.state_code || '',
      country: emp.country || '',
      country_code: emp.country_code || '',
      is_active: emp.is_active ?? true,
    })
    setFormErrors({})
    setViewMode('edit')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Back to list view
  const handleBackToList = () => {
    setViewMode('list')
    setSelectedEmployee(null)
    setFormErrors({})
  }

  // Open View Modal
  const handleOpenView = (emp) => {
    setSelectedEmployee(emp)
    setShowViewModal(true)
  }

  // Open Deactivate Modal
  const handleOpenDeactivate = (emp) => {
    setSelectedEmployee(emp)
    setShowDeactivateModal(true)
  }

  // Submit Create Employee
  const handleCreateSubmit = async (e) => {
    e.preventDefault()
    setFormErrors({})
    setIsSubmitting(true)

    const errors = {}
    if (!formData.full_name || formData.full_name.trim().length < 2) {
      errors.full_name = 'Full name must be at least 2 characters.'
    }
    if (!formData.email) {
      errors.email = 'Email address is required.'
    }
    if (!formData.password || formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters long.'
    }
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      setIsSubmitting(false)
      return
    }

    try {
      await createEmployee(formData)
      setShowCreateModal(false)
      setToast({ message: `Employee ${formData.full_name} created successfully!`, variant: 'success' })
      fetchEmployees()
    } catch (err) {
      const detail = err.response?.data?.detail
      let errorMsg = 'Failed to create employee.'
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

  // Submit Edit Employee (Main Content Page)
  const handleEditSubmit = async (e) => {
    e.preventDefault()
    setFormErrors({})
    setIsSubmitting(true)

    if (!formData.full_name || formData.full_name.trim().length < 2) {
      setFormErrors({ full_name: 'Full name must be at least 2 characters.' })
      setIsSubmitting(false)
      return
    }

    try {
      const payload = { ...formData }
      if (!payload.password) delete payload.password // Only send password if admin typed a new one

      await updateEmployee(selectedEmployee.id, payload)
      setToast({ message: `Employee ${formData.full_name} updated successfully!`, variant: 'success' })
      handleBackToList()
    } catch (err) {
      const detail = err.response?.data?.detail
      let errorMsg = 'Failed to update employee.'
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
    if (!selectedEmployee) return
    setIsSubmitting(true)
    try {
      await deactivateEmployee(selectedEmployee.id)
      setShowDeactivateModal(false)
      setToast({
        message: `Employee ${selectedEmployee.full_name} deactivated successfully.`,
        variant: 'success',
      })
      fetchEmployees()
    } catch (err) {
      setToast({
        message: err.response?.data?.detail || 'Failed to deactivate employee.',
        variant: 'danger',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const getInitials = (name) =>
    name
      ? name
          .split(' ')
          .map((p) => p[0])
          .join('')
          .slice(0, 2)
          .toUpperCase()
      : 'EM'

  // ═══════════════════════════════════════════════════════════════════════════
  // VIEW MODE: EDIT EMPLOYEE (MAIN CONTENT AREA)
  // ═══════════════════════════════════════════════════════════════════════════
  if (viewMode === 'edit' && selectedEmployee) {
    return (
      <div className="employee-edit-page-container pb-5">
        <Toast
          message={toast.message}
          variant={toast.variant}
          onClose={() => setToast({ message: '', variant: 'success' })}
        />

        {/* Breadcrumb & Navigation */}
        <div className="mb-3">
          <button
            type="button"
            className="btn btn-link text-decoration-none p-0 d-inline-flex align-items-center gap-2 text-primary fw-medium"
            onClick={handleBackToList}
            style={{ fontSize: '0.92rem' }}
          >
            <i className="bi bi-arrow-left" /> Back to Employee Management
          </button>
        </div>

        {/* Page Header */}
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center gap-3 mb-4">
          <div>
            <h1 className="fw-bold fs-3 mb-1 text-dark d-flex align-items-center gap-2">
              <i className="bi bi-person-gear text-primary" />
              Edit Employee: {selectedEmployee.full_name}
            </h1>
            <p className="text-muted mb-0 small">
              Update administrative roles, security status, and employee profile details.
            </p>
          </div>
          <div className="d-flex align-items-center gap-2">
            <span className="badge bg-light text-dark border px-3 py-2 rounded-pill">
              <i className="bi bi-person-badge me-1 text-primary" />
              {selectedEmployee.department || selectedEmployee.role || 'Member'}
            </span>
          </div>
        </div>

        <form onSubmit={handleEditSubmit} autoComplete="off">
          <div className="row g-4">
            {/* Left Column: Personal, Contact & Address */}
            <div className="col-12 col-lg-8">
              {/* Personal Information */}
              <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
                  <h5 className="fw-bold mb-1 d-flex align-items-center gap-2 text-dark">
                    <i className="bi bi-person text-primary" />
                    Personal Information
                  </h5>
                  <p className="text-muted small mb-0">Identity and workplace designation.</p>
                </div>
                <div className="card-body px-4 pb-4">
                  <div className="row g-3">
                    <div className="col-12">
                      <label className="form-label">
                        Full Name <span className="text-danger">*</span>
                      </label>
                      <input
                        type="text"
                        className={`form-control ${formErrors.full_name ? 'is-invalid' : ''}`}
                        value={formData.full_name}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                        required
                        style={{ borderRadius: '8px', height: '42px' }}
                      />
                      {formErrors.full_name && <div className="invalid-feedback">{formErrors.full_name}</div>}
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label">Job Title / Designation</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Senior QA Engineer"
                        value={formData.job_title}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                        style={{ borderRadius: '8px', height: '42px' }}
                      />
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label">Department / Team</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Quality Assurance, Platform"
                        value={formData.department}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                        style={{ borderRadius: '8px', height: '42px' }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Contact Information */}
              <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
                  <h5 className="fw-bold mb-1 d-flex align-items-center gap-2 text-dark">
                    <i className="bi bi-telephone text-primary" />
                    Contact Information
                  </h5>
                  <p className="text-muted small mb-0">Phone and mobile contact details.</p>
                </div>
                <div className="card-body px-4 pb-4">
                  <label className="form-label">Mobile Number</label>
                  <PhoneInput
                    countryCode={formData.mobile_country_code}
                    phoneNumber={formData.mobile_number}
                    onChangeCountryCode={(code) => setFormData({ ...formData, mobile_country_code: code })}
                    onChangePhoneNumber={(num) => setFormData({ ...formData, mobile_number: num })}
                  />
                </div>
              </div>

              {/* Address Information */}
              <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
                  <h5 className="fw-bold mb-1 d-flex align-items-center gap-2 text-dark">
                    <i className="bi bi-geo-alt text-primary" />
                    Address & Location
                  </h5>
                  <p className="text-muted small mb-0">Office location or residential address.</p>
                </div>
                <div className="card-body px-4 pb-4">
                  <div className="row g-3">
                    <div className="col-12">
                      <label className="form-label">Address Line 1</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Street address, building, apartment"
                        value={formData.address_line_1}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, address_line_1: e.target.value })}
                        style={{ borderRadius: '8px', height: '42px' }}
                      />
                    </div>

                    <div className="col-12">
                      <label className="form-label">Address Line 2 (Optional)</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Suite, floor, landmark"
                        value={formData.address_line_2}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, address_line_2: e.target.value })}
                        style={{ borderRadius: '8px', height: '42px' }}
                      />
                    </div>

                    <div className="col-12">
                      <CountryStateSelect
                        country={formData.country}
                        countryCode={formData.country_code}
                        state={formData.state}
                        stateCode={formData.state_code}
                        onChange={({ country, country_code, state, state_code }) =>
                          setFormData((prev) => ({
                            ...prev,
                            country,
                            country_code,
                            state,
                            state_code,
                          }))
                        }
                      />
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label">City</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Bangalore, Austin, London"
                        value={formData.city}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                        style={{ borderRadius: '8px', height: '42px' }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Administrative Controls & Actions */}
            <div className="col-12 col-lg-4">
              <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
                  <h5 className="fw-bold mb-1 d-flex align-items-center gap-2 text-dark">
                    <i className="bi bi-shield-lock text-danger" />
                    Administrative Controls
                  </h5>
                  <p className="text-muted small mb-0">Role assignment and authentication.</p>
                </div>
                <div className="card-body px-4 pb-4">
                  <div className="mb-3">
                    <label className="form-label fw-medium small">Official Email Address <span className="text-danger">*</span></label>
                    <input
                      type="email"
                      className="form-control"
                      value={formData.email}
                      autoComplete="off"
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      required
                      style={{ borderRadius: '8px', height: '42px' }}
                    />
                  </div>

                  <div className="mb-3">
                    <label className="form-label fw-medium small">Assigned Role <span className="text-danger">*</span></label>
                    <select
                      className="form-select"
                      value={formData.role}
                      onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                      required
                      style={{ borderRadius: '8px', height: '42px' }}
                    >
                      {rolesList.map((r) => (
                        <option key={r.name} value={r.name}>
                          {r.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="mb-3">
                    <label className="form-label fw-medium small">Account Status</label>
                    <select
                      className="form-select"
                      value={formData.is_active ? 'true' : 'false'}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.value === 'true' })}
                      disabled={selectedEmployee.id === currentAdmin?.id}
                      style={{ borderRadius: '8px', height: '42px' }}
                    >
                      <option value="true">Active</option>
                      <option value="false">Inactive / Deactivated</option>
                    </select>
                    {selectedEmployee.id === currentAdmin?.id && (
                      <small className="text-muted d-block mt-1">
                        You cannot deactivate your own active admin account.
                      </small>
                    )}
                  </div>

                  <div className="mb-3">
                    <label className="form-label fw-medium small">Reset Password</label>
                    <input
                      type="password"
                      className="form-control"
                      placeholder="Leave blank to keep unchanged"
                      value={formData.password}
                      autoComplete="off"
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      style={{ borderRadius: '8px', height: '42px' }}
                    />
                    <small className="text-muted" style={{ fontSize: '0.78rem' }}>
                      Enter at least 8 characters only if you wish to reset their password.
                    </small>
                  </div>
                </div>
              </div>

              {/* Action Buttons Panel */}
              <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                <div className="card-body p-4">
                  <div className="d-grid gap-2">
                    <button
                      type="submit"
                      className="btn btn-primary py-2 d-inline-flex justify-content-center align-items-center gap-2"
                      disabled={isSubmitting}
                      style={{ borderRadius: '10px', fontWeight: 600 }}
                    >
                      {isSubmitting ? (
                        <>
                          <span className="spinner-border spinner-border-sm" role="status" />
                          Saving Changes...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-check2-circle fs-5" />
                          Save Changes
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-secondary py-2"
                      onClick={handleBackToList}
                      disabled={isSubmitting}
                      style={{ borderRadius: '10px' }}
                    >
                      Cancel
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

  // ═══════════════════════════════════════════════════════════════════════════
  // VIEW MODE: LIST EMPLOYEES (TABLE)
  // ═══════════════════════════════════════════════════════════════════════════
  return (
    <div className="employee-mgmt-container pb-5">
      <Toast
        message={toast.message}
        variant={toast.variant}
        onClose={() => setToast({ message: '', variant: 'success' })}
      />

      {/* Page Header */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center gap-3 mb-4">
        <div>
          <h1 className="fw-bold fs-3 mb-1 text-dark d-flex align-items-center gap-2">
            <i className="bi bi-people-fill text-primary" />
            Employee Management
          </h1>
          <p className="text-muted mb-0">
            Create, view, edit, assign roles, and manage employee accounts with enterprise role-based access control.
          </p>
        </div>
        <button
          className="btn btn-primary d-inline-flex align-items-center gap-2 shadow-sm px-3 py-2"
          onClick={handleOpenCreate}
          style={{ borderRadius: '10px', fontWeight: 600 }}
        >
          <i className="bi bi-person-plus-fill fs-5" />
          Create Employee
        </button>
      </div>

      {/* Filter and Search Toolbar */}
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
        <div className="card-body p-3">
          <div className="row g-2 align-items-center">
            {/* Search */}
            <div className="col-12 col-md-5">
              <div className="input-group">
                <span
                  className="input-group-text bg-transparent border-end-0 text-muted"
                  style={{ borderRadius: '8px 0 0 8px' }}
                >
                  <i className="bi bi-search" />
                </span>
                <input
                  type="text"
                  className="form-control border-start-0 ps-0"
                  placeholder="Search employees by name, email, department, city..."
                  value={search}
                  autoComplete="off"
                  onChange={(e) => setSearch(e.target.value)}
                  style={{ borderRadius: '0 8px 8px 0', height: '40px' }}
                />
              </div>
            </div>

            {/* Role Filter */}
            <div className="col-6 col-md-3">
              <select
                className="form-select"
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
                style={{ borderRadius: '8px', height: '40px' }}
              >
                <option value="">All Roles</option>
                {rolesList.map((r) => (
                  <option key={r.name} value={r.name}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Filter */}
            <div className="col-6 col-md-2">
              <select
                className="form-select"
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                style={{ borderRadius: '8px', height: '40px' }}
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>

            {/* Count Badge */}
            <div className="col-12 col-md-2 text-md-end text-muted small">
              <strong>{totalEmployees}</strong> {totalEmployees === 1 ? 'employee' : 'employees'} found
            </div>
          </div>
        </div>
      </div>

      {/* Employee List Table */}
      <div className="card border-0 shadow-sm" style={{ borderRadius: '16px', overflow: 'hidden' }}>
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="bg-light text-muted small text-uppercase fw-bold border-bottom">
              <tr>
                <th className="py-3 px-4" style={{ minWidth: '220px' }}>
                  Employee
                </th>
                <th className="py-3 px-3">Email</th>
                <th className="py-3 px-3">Role</th>
                <th className="py-3 px-3">Mobile</th>
                <th className="py-3 px-3">Location</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-4 text-end" style={{ minWidth: '150px' }}>
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan="7" className="text-center py-5">
                    <div className="spinner-border text-primary spinner-border-sm me-2" role="status" />
                    Loading employees...
                  </td>
                </tr>
              ) : employees.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-5 text-muted">
                    <i className="bi bi-people fs-1 d-block mb-2 text-secondary" />
                    No employees found matching the filters.
                  </td>
                </tr>
              ) : (
                employees.map((emp) => {
                  const roleName = emp.role || emp.roles?.[0]?.name || 'Developer'
                  const badgeClass = ROLE_BADGE_CLASSES[roleName] || 'bg-secondary-subtle text-secondary'

                  return (
                    <tr key={emp.id}>
                      {/* Employee Avatar & Name */}
                      <td className="py-3 px-4">
                        <div className="d-flex align-items-center gap-3">
                          <div
                            className="avatar flex-shrink-0"
                            style={{
                              width: '40px',
                              height: '40px',
                              borderRadius: '50%',
                              background: emp.is_active ? 'var(--primary, #2563eb)' : '#94a3b8',
                              color: '#fff',
                              fontWeight: 700,
                              fontSize: '0.85rem',
                              display: 'grid',
                              placeItems: 'center',
                            }}
                          >
                            {getInitials(emp.full_name)}
                          </div>
                          <div>
                            <div className="fw-bold text-dark">{emp.full_name}</div>
                            <div className="text-muted small">
                              {emp.job_title || emp.department || 'Staff Member'}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Email */}
                      <td className="py-3 px-3 text-secondary">{emp.email}</td>

                      {/* High-Contrast Role Badge */}
                      <td className="py-3 px-3">
                        <span
                          className={`badge px-2 py-1 rounded-pill ${badgeClass}`}
                          style={{ fontSize: '0.78rem' }}
                        >
                          {roleName}
                        </span>
                      </td>

                      {/* Mobile */}
                      <td className="py-3 px-3 text-secondary small">
                        {emp.mobile_number ? (
                          <span>
                            {emp.mobile_country_code} {emp.mobile_number}
                          </span>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>

                      {/* Location */}
                      <td className="py-3 px-3 text-secondary small">
                        {emp.city || emp.country ? (
                          <span>{[emp.city, emp.country].filter(Boolean).join(', ')}</span>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-3">
                        <span
                          className={`badge rounded-pill px-2 py-1 ${
                            emp.is_active
                              ? 'bg-success-subtle text-success border border-success-subtle'
                              : 'bg-secondary text-white'
                          }`}
                          style={{ fontSize: '0.75rem' }}
                        >
                          <i className={`bi bi-${emp.is_active ? 'check-circle-fill' : 'dash-circle'} me-1`} />
                          {emp.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-end">
                        <div className="d-inline-flex gap-1">
                          {/* View */}
                          <button
                            className="btn btn-sm btn-outline-secondary"
                            onClick={() => handleOpenView(emp)}
                            title="View Employee Details"
                            style={{ borderRadius: '6px' }}
                          >
                            <i className="bi bi-eye" />
                          </button>

                          {/* Edit (Opens Main Content Page) */}
                          <button
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => handleOpenEdit(emp)}
                            title="Edit Employee"
                            style={{ borderRadius: '6px' }}
                          >
                            <i className="bi bi-pencil" />
                          </button>

                          {/* Deactivate */}
                          {emp.is_active && emp.id !== currentAdmin?.id && (
                            <button
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => handleOpenDeactivate(emp)}
                              title="Deactivate Account"
                              style={{ borderRadius: '6px' }}
                            >
                              <i className="bi bi-person-x" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── CREATE EMPLOYEE MODAL ── */}
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
                  <i className="bi bi-person-plus-fill text-primary" />
                  Create New Employee
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
                    {/* Account Info */}
                    <div className="col-12">
                      <h6 className="fw-bold text-primary mb-2 small text-uppercase">
                        Account Credentials
                      </h6>
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label">
                        Full Name <span className="text-danger">*</span>
                      </label>
                      <input
                        type="text"
                        className={`form-control ${formErrors.full_name ? 'is-invalid' : ''}`}
                        placeholder="e.g. John Doe"
                        value={formData.full_name}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                        required
                        style={{ borderRadius: '8px' }}
                      />
                      {formErrors.full_name && (
                        <div className="invalid-feedback">{formErrors.full_name}</div>
                      )}
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label">
                        Email Address <span className="text-danger">*</span>
                      </label>
                      <input
                        type="email"
                        className={`form-control ${formErrors.email ? 'is-invalid' : ''}`}
                        placeholder="john.doe@company.com"
                        value={formData.email}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        required
                        style={{ borderRadius: '8px' }}
                      />
                      {formErrors.email && (
                        <div className="invalid-feedback">{formErrors.email}</div>
                      )}
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label">
                        Temporary Password <span className="text-danger">*</span>
                      </label>
                      <input
                        type="password"
                        className={`form-control ${formErrors.password ? 'is-invalid' : ''}`}
                        placeholder="Min 8 characters"
                        value={formData.password}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        required
                        style={{ borderRadius: '8px' }}
                      />
                      {formErrors.password && (
                        <div className="invalid-feedback">{formErrors.password}</div>
                      )}
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label">
                        Assign Role <span className="text-danger">*</span>
                      </label>
                      <select
                        className="form-select"
                        value={formData.role}
                        onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                        required
                        style={{ borderRadius: '8px' }}
                      >
                        {rolesList.map((r) => (
                          <option key={r.name} value={r.name}>
                            {r.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Organization Info */}
                    <div className="col-12 mt-4">
                      <h6 className="fw-bold text-primary mb-2 small text-uppercase">
                        Organization & Contact
                      </h6>
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label">Job Title / Designation</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Senior QA Engineer"
                        value={formData.job_title}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                        style={{ borderRadius: '8px' }}
                      />
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label">Department / Team</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Quality Assurance"
                        value={formData.department}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                        style={{ borderRadius: '8px' }}
                      />
                    </div>

                    <div className="col-12">
                      <label className="form-label">Mobile Number</label>
                      <PhoneInput
                        countryCode={formData.mobile_country_code}
                        phoneNumber={formData.mobile_number}
                        onChangeCountryCode={(code) =>
                          setFormData({ ...formData, mobile_country_code: code })
                        }
                        onChangePhoneNumber={(num) =>
                          setFormData({ ...formData, mobile_number: num })
                        }
                      />
                    </div>

                    {/* Address Info */}
                    <div className="col-12 mt-4">
                      <h6 className="fw-bold text-primary mb-2 small text-uppercase">
                        Address & Location
                      </h6>
                    </div>

                    <div className="col-12">
                      <label className="form-label">Address Line 1</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Street address, building"
                        value={formData.address_line_1}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, address_line_1: e.target.value })}
                        style={{ borderRadius: '8px' }}
                      />
                    </div>

                    <div className="col-12">
                      <label className="form-label">Address Line 2 (Optional)</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Suite, floor, landmark"
                        value={formData.address_line_2}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, address_line_2: e.target.value })}
                        style={{ borderRadius: '8px' }}
                      />
                    </div>

                    <div className="col-12">
                      <CountryStateSelect
                        country={formData.country}
                        countryCode={formData.country_code}
                        state={formData.state}
                        stateCode={formData.state_code}
                        onChange={({ country, country_code, state, state_code }) =>
                          setFormData((prev) => ({
                            ...prev,
                            country,
                            country_code,
                            state,
                            state_code,
                          }))
                        }
                      />
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label">City</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="e.g. Bangalore, Austin, London"
                        value={formData.city}
                        autoComplete="off"
                        onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                        style={{ borderRadius: '8px' }}
                      />
                    </div>
                  </div>
                </div>
                <div className="modal-footer border-0 px-4 pb-4">
                  <button
                    type="button"
                    className="btn btn-light"
                    onClick={() => setShowCreateModal(false)}
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary px-4" disabled={isSubmitting}>
                    {isSubmitting ? 'Creating Employee...' : 'Create Employee'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* ── VIEW EMPLOYEE DETAILS MODAL ── */}
      {showViewModal && selectedEmployee && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow-lg" style={{ borderRadius: '16px' }}>
              <div className="modal-header border-0 pb-0 pt-4 px-4">
                <h5 className="modal-title fw-bold text-dark d-flex align-items-center gap-2">
                  <i className="bi bi-person-badge text-primary" />
                  Employee Profile
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowViewModal(false)}
                />
              </div>
              <div className="modal-body px-4 py-3">
                <div className="text-center mb-4">
                  <div
                    className="avatar shadow mx-auto mb-2"
                    style={{
                      width: '64px',
                      height: '64px',
                      borderRadius: '50%',
                      background: selectedEmployee.is_active ? 'var(--primary, #2563eb)' : '#94a3b8',
                      color: '#fff',
                      fontSize: '1.5rem',
                      fontWeight: 700,
                      display: 'grid',
                      placeItems: 'center',
                    }}
                  >
                    {getInitials(selectedEmployee.full_name)}
                  </div>
                  <h5 className="fw-bold mb-0 text-dark">{selectedEmployee.full_name}</h5>
                  <p className="text-muted small mb-2">{selectedEmployee.job_title || 'Staff Member'}</p>
                  <div className="d-flex justify-content-center gap-2">
                    <span
                      className={`badge px-2 py-1 rounded-pill ${
                        ROLE_BADGE_CLASSES[
                          selectedEmployee.role || selectedEmployee.roles?.[0]?.name || 'Developer'
                        ] || 'bg-secondary'
                      }`}
                    >
                      {selectedEmployee.role || selectedEmployee.roles?.[0]?.name || 'Developer'}
                    </span>
                    <span
                      className={`badge rounded-pill px-2 py-1 ${
                        selectedEmployee.is_active ? 'bg-success' : 'bg-secondary'
                      }`}
                    >
                      {selectedEmployee.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>

                <div className="list-group list-group-flush border-top">
                  <div className="list-group-item px-0 py-2 d-flex justify-content-between">
                    <span className="text-muted small">Email</span>
                    <span className="fw-medium small">{selectedEmployee.email}</span>
                  </div>
                  <div className="list-group-item px-0 py-2 d-flex justify-content-between">
                    <span className="text-muted small">Department</span>
                    <span className="fw-medium small">{selectedEmployee.department || '—'}</span>
                  </div>
                  <div className="list-group-item px-0 py-2 d-flex justify-content-between">
                    <span className="text-muted small">Mobile Number</span>
                    <span className="fw-medium small">
                      {selectedEmployee.mobile_number
                        ? `${selectedEmployee.mobile_country_code || ''} ${selectedEmployee.mobile_number}`
                        : '—'}
                    </span>
                  </div>
                  <div className="list-group-item px-0 py-2 d-flex justify-content-between">
                    <span className="text-muted small">Address</span>
                    <span className="fw-medium small text-end" style={{ maxWidth: '60%' }}>
                      {[
                        selectedEmployee.address_line_1,
                        selectedEmployee.address_line_2,
                        selectedEmployee.city,
                        selectedEmployee.state,
                        selectedEmployee.country,
                      ]
                        .filter(Boolean)
                        .join(', ') || '—'}
                    </span>
                  </div>
                  <div className="list-group-item px-0 py-2 d-flex justify-content-between">
                    <span className="text-muted small">Department / Unit</span>
                    <span className="badge bg-light text-dark border">{selectedEmployee.department || 'General'}</span>
                  </div>
                </div>
              </div>
              <div className="modal-footer border-0 px-4 pb-4">
                <button
                  type="button"
                  className="btn btn-outline-primary"
                  onClick={() => {
                    setShowViewModal(false)
                    handleOpenEdit(selectedEmployee)
                  }}
                >
                  <i className="bi bi-pencil me-1" /> Edit Employee
                </button>
                <button
                  type="button"
                  className="btn btn-light"
                  onClick={() => setShowViewModal(false)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── DEACTIVATE / DELETE CONFIRMATION MODAL ── */}
      {showDeactivateModal && selectedEmployee && (
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
                  Deactivate Employee Account
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowDeactivateModal(false)}
                />
              </div>
              <div className="modal-body px-4 py-3">
                <p className="mb-2">
                  Are you sure you want to deactivate the account for{' '}
                  <strong className="text-dark">{selectedEmployee.full_name}</strong> (
                  <code>{selectedEmployee.email}</code>)?
                </p>
                <div
                  className="alert alert-warning d-flex gap-2 py-2 px-3 mb-0"
                  style={{ fontSize: '0.85rem' }}
                >
                  <i className="bi bi-info-circle-fill flex-shrink-0 mt-1" />
                  <div>
                    This will immediately prevent the employee from signing in. All historical
                    defect reports, assignees, and activity history will remain safely preserved.
                  </div>
                </div>
              </div>
              <div className="modal-footer border-0 px-4 pb-4">
                <button
                  type="button"
                  className="btn btn-light"
                  onClick={() => setShowDeactivateModal(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-danger px-4"
                  onClick={handleConfirmDeactivate}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Deactivating...' : 'Deactivate Account'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
