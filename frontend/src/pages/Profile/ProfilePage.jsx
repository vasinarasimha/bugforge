import { useEffect, useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { getCurrentUser, updateProfile } from '../../services/authService'
import PhoneInput from '../../components/PhoneInput/PhoneInput'
import CountryStateSelect from '../../components/CountryStateSelect/CountryStateSelect'
import Toast from '../../components/Toast/Toast'

export default function ProfilePage() {
  const { user: authUser, signIn } = useAuth()
  const [profile, setProfile] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [toast, setToast] = useState({ message: '', variant: 'success' })
  const [errors, setErrors] = useState({})

  useEffect(() => {
    fetchProfile()
  }, [])

  const fetchProfile = async () => {
    setIsLoading(true)
    try {
      const { data } = await getCurrentUser()
      setProfile(data)
    } catch (err) {
      setToast({
        message: err.response?.data?.detail || 'Failed to load profile details.',
        variant: 'danger',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrors({})
    setIsSaving(true)

    // Basic validation
    if (!profile.full_name || profile.full_name.trim().length < 2) {
      setErrors({ full_name: 'Full name must be at least 2 characters.' })
      setIsSaving(false)
      return
    }

    try {
      const payload = {
        full_name: profile.full_name,
        job_title: profile.job_title || null,
        department: profile.department || null,
        mobile_country_code: profile.mobile_country_code || null,
        mobile_number: profile.mobile_number || null,
        address_line_1: profile.address_line_1 || null,
        address_line_2: profile.address_line_2 || null,
        city: profile.city || null,
        state: profile.state || null,
        state_code: profile.state_code || null,
        country: profile.country || null,
        country_code: profile.country_code || null,
      }

      const { data } = await updateProfile(payload)
      setProfile(data)
      // Update local storage user session if needed
      if (localStorage.getItem('access_token')) {
        signIn({ access_token: localStorage.getItem('access_token'), user: data })
      }
      setToast({ message: 'Profile updated successfully!', variant: 'success' })
    } catch (err) {
      const detail = err.response?.data?.detail
      let errorMsg = 'Failed to update profile.'
      if (Array.isArray(detail)) {
        errorMsg = detail.map((d) => d.msg).join(', ')
      } else if (typeof detail === 'string') {
        errorMsg = detail
      }
      setToast({ message: errorMsg, variant: 'danger' })
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading profile...</span>
        </div>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="alert alert-danger my-4">
        Failed to load profile. Please refresh or sign in again.
      </div>
    )
  }

  const initials = profile.full_name
    ? profile.full_name
        .split(' ')
        .map((p) => p[0])
        .join('')
        .slice(0, 2)
        .toUpperCase()
    : 'BF'

  return (
    <div className="profile-page-container pb-5">
      <Toast
        message={toast.message}
        variant={toast.variant}
        onClose={() => setToast({ message: '', variant: 'success' })}
      />

      {/* Header Banner */}
      <div className="profile-header card mb-4 border-0 shadow-sm" style={{ borderRadius: '16px', overflow: 'hidden', background: '#ffffff' }}>
        <div
          style={{
            background: 'linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%)',
            height: '110px',
            position: 'relative',
          }}
        />
        <div className="card-body px-4 pb-4 pt-0">
          <div className="d-flex flex-column flex-md-row align-items-start align-items-md-center justify-content-between gap-3">
            <div className="d-flex flex-column flex-sm-row align-items-start align-items-sm-center gap-3">
              {/* Floating Avatar */}
              <div
                className="avatar shadow"
                style={{
                  width: '88px',
                  height: '88px',
                  borderRadius: '50%',
                  background: 'var(--primary, #2563eb)',
                  color: '#fff',
                  fontSize: '2rem',
                  fontWeight: 700,
                  display: 'grid',
                  placeItems: 'center',
                  border: '4px solid #ffffff',
                  marginTop: '-44px',
                  flexShrink: 0,
                  boxShadow: '0 4px 14px rgba(0, 0, 0, 0.12)',
                }}
              >
                {initials}
              </div>

              {/* Clean User Info Container entirely on card surface */}
              <div className="pt-2">
                <h2 className="mb-1 fw-bold" style={{ fontSize: '1.5rem', color: '#0f172a', lineHeight: 1.25 }}>
                  {profile.full_name}
                </h2>
                <div className="d-flex flex-wrap align-items-center gap-2">
                  <span className="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1 rounded-pill" style={{ fontWeight: 600 }}>
                    <i className="bi bi-shield-lock me-1" />
                    {profile.role || 'Developer'}
                  </span>
                  {profile.job_title && (
                    <span className="text-secondary small fw-medium">
                      <i className="bi bi-briefcase me-1 text-primary" />
                      {profile.job_title}
                    </span>
                  )}
                  {profile.department && (
                    <span className="text-secondary small fw-medium">
                      <i className="bi bi-building me-1 text-primary" />
                      {profile.department}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="d-flex align-items-center gap-2 pt-2 pt-md-0">
              <span className={`badge ${profile.is_active ? 'bg-success' : 'bg-secondary'} px-3 py-2 rounded-pill`} style={{ fontWeight: 600 }}>
                <i className={`bi bi-${profile.is_active ? 'check-circle' : 'slash-circle'} me-1`} />
                {profile.is_active ? 'Active Account' : 'Inactive'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} autoComplete="off">
        <div className="row g-4">
          {/* Left Column: Personal, Contact & Address */}
          <div className="col-12 col-lg-8">
            {/* Personal Details */}
            <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
              <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
                <h5 className="fw-bold mb-1 d-flex align-items-center gap-2 text-dark">
                  <i className="bi bi-person text-primary" />
                  Personal Information
                </h5>
                <p className="text-muted small mb-0">Your identity and role in the defect tracking workflow.</p>
              </div>
              <div className="card-body px-4 pb-4">
                <div className="row g-3">
                  <div className="col-12">
                    <label className="form-label">
                      Full Name <span className="text-danger">*</span>
                    </label>
                    <input
                      type="text"
                      className={`form-control ${errors.full_name ? 'is-invalid' : ''}`}
                      value={profile.full_name || ''}
                      autoComplete="off"
                      onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                      required
                      style={{ borderRadius: '8px', height: '42px' }}
                    />
                    {errors.full_name && <div className="invalid-feedback">{errors.full_name}</div>}
                  </div>

                  <div className="col-12 col-md-6">
                    <label className="form-label">Job Title / Designation</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. Senior Frontend Engineer"
                      value={profile.job_title || ''}
                      autoComplete="off"
                      onChange={(e) => setProfile({ ...profile, job_title: e.target.value })}
                      style={{ borderRadius: '8px', height: '42px' }}
                    />
                  </div>

                  <div className="col-12 col-md-6">
                    <label className="form-label">Department / Team</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. Core Platform, QA Team"
                      value={profile.department || ''}
                      autoComplete="off"
                      onChange={(e) => setProfile({ ...profile, department: e.target.value })}
                      style={{ borderRadius: '8px', height: '42px' }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Contact Details */}
            <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
              <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
                <h5 className="fw-bold mb-1 d-flex align-items-center gap-2 text-dark">
                  <i className="bi bi-telephone text-primary" />
                  Contact Information
                </h5>
                <p className="text-muted small mb-0">Your verified phone and mobile number.</p>
              </div>
              <div className="card-body px-4 pb-4">
                <label className="form-label">Mobile Number</label>
                <PhoneInput
                  countryCode={profile.mobile_country_code || '+91'}
                  phoneNumber={profile.mobile_number || ''}
                  onChangeCountryCode={(code) => setProfile({ ...profile, mobile_country_code: code })}
                  onChangePhoneNumber={(num) => setProfile({ ...profile, mobile_number: num })}
                />
              </div>
            </div>

            {/* Address Details */}
            <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
              <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
                <h5 className="fw-bold mb-1 d-flex align-items-center gap-2 text-dark">
                  <i className="bi bi-geo-alt text-primary" />
                  Address & Location
                </h5>
                <p className="text-muted small mb-0">Location details for workplace and team alignment.</p>
              </div>
              <div className="card-body px-4 pb-4">
                <div className="row g-3">
                  <div className="col-12">
                    <label className="form-label">Address Line 1</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Street address, building, apartment"
                      value={profile.address_line_1 || ''}
                      autoComplete="off"
                      onChange={(e) => setProfile({ ...profile, address_line_1: e.target.value })}
                      style={{ borderRadius: '8px', height: '42px' }}
                    />
                  </div>

                  <div className="col-12">
                    <label className="form-label">Address Line 2 (Optional)</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Suite, floor, landmark"
                      value={profile.address_line_2 || ''}
                      autoComplete="off"
                      onChange={(e) => setProfile({ ...profile, address_line_2: e.target.value })}
                      style={{ borderRadius: '8px', height: '42px' }}
                    />
                  </div>

                  <div className="col-12 col-md-12">
                    <CountryStateSelect
                      country={profile.country || ''}
                      countryCode={profile.country_code || ''}
                      state={profile.state || ''}
                      stateCode={profile.state_code || ''}
                      onChange={({ country, country_code, state, state_code }) =>
                        setProfile((prev) => ({
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
                      value={profile.city || ''}
                      autoComplete="off"
                      onChange={(e) => setProfile({ ...profile, city: e.target.value })}
                      style={{ borderRadius: '8px', height: '42px' }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Action Bar */}
            <div className="d-flex justify-content-end gap-3 mb-4">
              <button
                type="submit"
                className="btn btn-primary px-4 py-2 d-inline-flex align-items-center gap-2 shadow-sm"
                disabled={isSaving}
                style={{ borderRadius: '10px', fontWeight: 600 }}
              >
                {isSaving ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status" />
                    Saving Changes...
                  </>
                ) : (
                  <>
                    <i className="bi bi-check2-circle fs-5" />
                    Save Profile Changes
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Right Column: Account Security & Admin-managed Information */}
          <div className="col-12 col-lg-4">
            <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
              <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
                <h5 className="fw-bold mb-1 d-flex align-items-center gap-2 text-dark">
                  <i className="bi bi-shield-lock text-warning" />
                  Account Security
                </h5>
                <p className="text-muted small mb-0">Managed by BugForge workspace administrator.</p>
              </div>
              <div className="card-body px-4 pb-4">
                <div className="mb-3">
                  <div className="d-flex justify-content-between align-items-center mb-1">
                    <label className="form-label mb-0 text-muted small fw-bold">EMAIL ADDRESS</label>
                    <span className="badge bg-secondary-subtle text-secondary border" style={{ fontSize: '0.72rem' }}>
                      <i className="bi bi-lock-fill me-1" />
                      Managed by Admin
                    </span>
                  </div>
                  <input
                    type="email"
                    className="form-control bg-light text-muted"
                    value={profile.email || ''}
                    disabled
                    readOnly
                    autoComplete="off"
                    style={{ borderRadius: '8px', height: '42px', cursor: 'not-allowed' }}
                  />
                </div>

                <div className="mb-3">
                  <div className="d-flex justify-content-between align-items-center mb-1">
                    <label className="form-label mb-0 text-muted small fw-bold">ASSIGNED ROLE</label>
                    <span className="badge bg-secondary-subtle text-secondary border" style={{ fontSize: '0.72rem' }}>
                      <i className="bi bi-lock-fill me-1" />
                      Managed by Admin
                    </span>
                  </div>
                  <input
                    type="text"
                    className="form-control bg-light text-muted"
                    value={profile.role || 'Developer'}
                    disabled
                    readOnly
                    autoComplete="off"
                    style={{ borderRadius: '8px', height: '42px', cursor: 'not-allowed' }}
                  />
                </div>

                <div className="mb-3">
                  <div className="d-flex justify-content-between align-items-center mb-1">
                    <label className="form-label mb-0 text-muted small fw-bold">ACCOUNT STATUS</label>
                    <span className="badge bg-secondary-subtle text-secondary border" style={{ fontSize: '0.72rem' }}>
                      <i className="bi bi-lock-fill me-1" />
                      Managed by Admin
                    </span>
                  </div>
                  <input
                    type="text"
                    className="form-control bg-light text-muted"
                    value={profile.is_active ? 'Active' : 'Inactive'}
                    disabled
                    readOnly
                    autoComplete="off"
                    style={{ borderRadius: '8px', height: '42px', cursor: 'not-allowed' }}
                  />
                </div>

                <div className="p-3 bg-light rounded-3 mt-3 border" style={{ fontSize: '0.82rem', color: '#64748b' }}>
                  <div className="d-flex align-items-start gap-2">
                    <i className="bi bi-info-circle-fill text-primary mt-1" />
                    <div>
                      To modify your official email address, security credentials, or role permissions, please contact your workspace administrator.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}
