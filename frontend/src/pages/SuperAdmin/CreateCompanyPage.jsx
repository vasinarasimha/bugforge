import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { superAdminApi } from '../../api/superAdminApi'
import CountryStateSelect from '../../components/CountryStateSelect/CountryStateSelect'
import PhoneInput from '../../components/PhoneInput/PhoneInput'

const TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Kolkata',
  'Asia/Tokyo',
  'Asia/Singapore',
  'Australia/Sydney',
]

export default function CreateCompanyPage() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  // Company Form State
  const [company, setCompany] = useState({
    name: '',
    legal_name: '',
    email: '',
    phone: '',
    website: '',
    address_line_1: '',
    address_line_2: '',
    city: '',
    state: '',
    state_code: '',
    country: '',
    country_code: '',
    timezone: 'UTC',
  })

  // Initial Admin Form State
  const [admin, setAdmin] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    job_title: 'Company Administrator',
    department: 'Executive / IT',
    mobile_country_code: '+91',
    mobile_number: '',
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    // Basic Validation
    if (!company.name.trim()) {
      setError('Company Name is required.')
      return
    }
    if (!admin.first_name.trim() || !admin.last_name.trim()) {
      setError('Initial Administrator first and last name are required.')
      return
    }
    if (!admin.email.trim()) {
      setError('Initial Administrator email is required.')
      return
    }
    if (!admin.password || admin.password.length < 8) {
      setError('Initial Administrator password must be at least 8 characters long.')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        name: company.name.trim(),
        legal_name: company.legal_name.trim() || null,
        email: company.email.trim() || null,
        phone: company.phone.trim() || null,
        website: company.website.trim() || null,
        address_line_1: company.address_line_1.trim() || null,
        address_line_2: company.address_line_2.trim() || null,
        city: company.city.trim() || null,
        state: company.state.trim() || null,
        country: company.country.trim() || null,
        timezone: company.timezone || 'UTC',
        admin: {
          first_name: admin.first_name.trim(),
          last_name: admin.last_name.trim(),
          email: admin.email.trim().toLowerCase(),
          password: admin.password,
          job_title: admin.job_title.trim() || 'Company Administrator',
          department: admin.department.trim() || 'Administration',
          mobile_number: admin.mobile_number ? `${admin.mobile_country_code} ${admin.mobile_number}` : null,
        },
      }

      const res = await superAdminApi.createCompany(payload)
      navigate(`/super-admin/companies/${res.company.id}`, {
        state: { message: `Company "${res.company.name}" created successfully with initial admin!` },
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create company and initial admin.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container-fluid px-4 py-4" style={{ maxWidth: '1200px' }}>
      {/* Breadcrumb & Title */}
      <nav aria-label="breadcrumb" className="mb-2">
        <ol className="breadcrumb mb-0 text-xs">
          <li className="breadcrumb-item"><Link to="/dashboard">Platform</Link></li>
          <li className="breadcrumb-item"><Link to="/super-admin/companies">Companies</Link></li>
          <li className="breadcrumb-item active" aria-current="page">Create Company</li>
        </ol>
      </nav>

      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h1 className="h3 font-bold text-slate-900 mb-1">Onboard New Tenant Company</h1>
          <p className="text-muted text-sm mb-0">
            Provision an isolated tenant environment with default workflow configurations and an initial Company Administrator.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-4" role="alert">
          <i className="bi bi-exclamation-triangle-fill shrink-0 fs-5" />
          <div className="text-sm">{error}</div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="row g-4">
          {/* Section 1: Company Profile */}
          <div className="col-12 col-lg-7">
            <div className="card border-0 shadow-sm rounded-3 p-4 bg-white h-100">
              <div className="d-flex align-items-center gap-2.5 mb-3 pb-2 border-bottom">
                <div className="w-8 h-8 rounded bg-primary-subtle text-primary d-flex align-items-center justify-content-center font-bold">
                  <i className="bi bi-building" />
                </div>
                <div>
                  <h2 className="h6 font-bold text-slate-900 mb-0">Company Profile</h2>
                  <span className="text-xs text-muted">Core organizational details and regional settings</span>
                </div>
              </div>

              <div className="row g-3">
                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">
                    Company Name <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    className="form-control form-control-sm"
                    placeholder="e.g. Acme Corporation"
                    value={company.name}
                    onChange={(e) => setCompany({ ...company, name: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Legal Entity Name</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    placeholder="e.g. Acme Corp Inc., LLC"
                    value={company.legal_name}
                    onChange={(e) => setCompany({ ...company, legal_name: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Corporate Email</label>
                  <input
                    type="email"
                    className="form-control form-control-sm"
                    placeholder="contact@acmecorp.com"
                    value={company.email}
                    onChange={(e) => setCompany({ ...company, email: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Corporate Phone</label>
                  <input
                    type="tel"
                    className="form-control form-control-sm"
                    placeholder="+1 (555) 000-0000"
                    value={company.phone}
                    onChange={(e) => setCompany({ ...company, phone: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Official Website</label>
                  <input
                    type="url"
                    className="form-control form-control-sm"
                    placeholder="https://www.acmecorp.com"
                    value={company.website}
                    onChange={(e) => setCompany({ ...company, website: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Timezone</label>
                  <select
                    className="form-select form-select-sm"
                    value={company.timezone}
                    onChange={(e) => setCompany({ ...company, timezone: e.target.value })}
                  >
                    {TIMEZONES.map((tz) => (
                      <option key={tz} value={tz}>
                        {tz}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="col-12">
                  <label className="form-label text-xs font-semibold text-slate-700">Address Line 1</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    placeholder="123 Innovation Way, Suite 400"
                    value={company.address_line_1}
                    onChange={(e) => setCompany({ ...company, address_line_1: e.target.value })}
                  />
                </div>

                <div className="col-12">
                  <label className="form-label text-xs font-semibold text-slate-700">Address Line 2</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    placeholder="Building B, Floor 3"
                    value={company.address_line_2}
                    onChange={(e) => setCompany({ ...company, address_line_2: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-4">
                  <label className="form-label text-xs font-semibold text-slate-700">City</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    placeholder="San Francisco"
                    value={company.city}
                    onChange={(e) => setCompany({ ...company, city: e.target.value })}
                  />
                </div>

                <div className="col-12 col-md-8">
                  <CountryStateSelect
                    country={company.country}
                    countryCode={company.country_code}
                    state={company.state}
                    stateCode={company.state_code}
                    onChange={({ country, country_code, state, state_code }) =>
                      setCompany({
                        ...company,
                        country,
                        country_code,
                        state,
                        state_code,
                      })
                    }
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Initial Company Administrator */}
          <div className="col-12 col-lg-5">
            <div className="card border-0 shadow-sm rounded-3 p-4 bg-white h-100 d-flex flex-column">
              <div className="d-flex align-items-center gap-2.5 mb-3 pb-2 border-bottom">
                <div className="w-8 h-8 rounded bg-emerald-subtle text-emerald-600 d-flex align-items-center justify-content-center font-bold">
                  <i className="bi bi-person-gear" />
                </div>
                <div>
                  <h2 className="h6 font-bold text-slate-900 mb-0">Initial Company Admin</h2>
                  <span className="text-xs text-muted">First administrative user account for this tenant</span>
                </div>
              </div>

              <div className="row g-3 flex-grow-1">
                <div className="col-12 col-sm-6">
                  <label className="form-label text-xs font-semibold text-slate-700">
                    First Name <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    className="form-control form-control-sm"
                    placeholder="Jane"
                    value={admin.first_name}
                    onChange={(e) => setAdmin({ ...admin, first_name: e.target.value })}
                  />
                </div>

                <div className="col-12 col-sm-6">
                  <label className="form-label text-xs font-semibold text-slate-700">
                    Last Name <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    className="form-control form-control-sm"
                    placeholder="Doe"
                    value={admin.last_name}
                    onChange={(e) => setAdmin({ ...admin, last_name: e.target.value })}
                  />
                </div>

                <div className="col-12">
                  <label className="form-label text-xs font-semibold text-slate-700">
                    Admin Email Address <span className="text-danger">*</span>
                  </label>
                  <input
                    type="email"
                    required
                    className="form-control form-control-sm"
                    placeholder="jane.doe@acmecorp.com"
                    value={admin.email}
                    onChange={(e) => setAdmin({ ...admin, email: e.target.value })}
                  />
                  <span className="text-xs text-muted mt-1 d-block">
                    This email will serve as the initial login credential.
                  </span>
                </div>

                <div className="col-12">
                  <label className="form-label text-xs font-semibold text-slate-700">
                    Temporary Password <span className="text-danger">*</span>
                  </label>
                  <div className="input-group input-group-sm">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      minLength={8}
                      className="form-control"
                      placeholder="Minimum 8 characters"
                      value={admin.password}
                      onChange={(e) => setAdmin({ ...admin, password: e.target.value })}
                    />
                    <button
                      type="button"
                      className="btn btn-outline-secondary border"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      <i className={`bi ${showPassword ? 'bi-eye-slash' : 'bi-eye'}`} />
                    </button>
                  </div>
                </div>

                <div className="col-12 col-sm-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Job Title</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={admin.job_title}
                    onChange={(e) => setAdmin({ ...admin, job_title: e.target.value })}
                  />
                </div>

                <div className="col-12 col-sm-6">
                  <label className="form-label text-xs font-semibold text-slate-700">Department</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={admin.department}
                    onChange={(e) => setAdmin({ ...admin, department: e.target.value })}
                  />
                </div>

                <div className="col-12">
                  <PhoneInput
                    countryCode={admin.mobile_country_code}
                    number={admin.mobile_number}
                    onChangeCountryCode={(code) => setAdmin({ ...admin, mobile_country_code: code })}
                    onChangeNumber={(num) => setAdmin({ ...admin, mobile_number: num })}
                  />
                </div>
              </div>

              {/* Notice Card */}
              <div className="bg-slate-50 border rounded-2 p-3 mt-4 text-xs text-slate-600">
                <i className="bi bi-info-circle text-primary me-1.5" />
                <strong>Atomic Provisioning:</strong> Default statuses (Open, In Progress, Resolved, Verified, Closed) and company settings will be automatically initialized for this tenant.
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="col-12 d-flex justify-content-end gap-3 pt-2">
            <Link to="/super-admin/companies" className="btn btn-outline-secondary px-4">
              Cancel
            </Link>
            <button
              type="submit"
              className="btn btn-primary px-4 d-flex align-items-center gap-2 shadow-sm"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <span className="spinner-border spinner-border-sm" role="status" />
                  <span>Provisioning Company...</span>
                </>
              ) : (
                <>
                  <i className="bi bi-check-circle" />
                  <span>Create Company & Admin</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
