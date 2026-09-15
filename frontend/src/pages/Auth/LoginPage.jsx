import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { login } from '../../services/authService'
import Toast from '../../components/Toast/Toast'
import './LoginPage.css'

export default function LoginPage() {
  const navigate = useNavigate()
  const { user, isLoading, signIn } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(true)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [toastMessage, setToastMessage] = useState('')

  // Modals for Register & Recovery info
  const [showRegisterModal, setShowRegisterModal] = useState(false)
  const [showRecoveryModal, setShowRecoveryModal] = useState(false)

  if (isLoading)
    return <p className="page-status">Loading session…</p>
  if (user)
    return <Navigate to="/dashboard" replace />

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      const { data } = await login(form)
      signIn(data)
      setToastMessage('Login successful! Redirecting to workspace…')
      setTimeout(() => navigate('/dashboard', { replace: true }), 100)
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          'Invalid email or password. Please verify your workspace credentials.'
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="split-login-root">
      <Toast message={toastMessage} variant="success" onClose={() => setToastMessage('')} />

      {/* --------------------------------------------------------------------
          Fixed Top Header
          -------------------------------------------------------------------- */}
      <header className="split-login-header">
        <div className="split-login-nav-container">
          <Link to="/" className="split-login-brand font-display">
            <img
              src="/logo.png"
              alt="BugForge Logo"
              style={{ height: '34px', width: 'auto', objectFit: 'contain' }}
            />
          </Link>

          <nav className="split-login-nav-links">
            <Link to="/" className="split-nav-link">
              Back to Home
            </Link>
            <span className="split-nav-link active">Sign In</span>
            <button
              type="button"
              className="split-nav-link"
              onClick={() => setShowRegisterModal(true)}
            >
              Register
            </button>
            <button
              type="button"
              className="split-nav-link"
              onClick={() => setShowRecoveryModal(true)}
            >
              Recovery
            </button>
          </nav>

          <div className="split-header-user-badge">
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
              person
            </span>
          </div>
        </div>
      </header>

      {/* --------------------------------------------------------------------
          Main Split View (70% Visual / 30% Form)
          -------------------------------------------------------------------- */}
      <main className="split-login-main">
        <div className="split-login-container">
          {/* Left 70% Width Area: High-Impact Visual Showcase */}
          <div className="split-visual-panel">
            <div className="split-visual-bg-wrapper">
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAn7v1bwwvvgaRQVEIPLxrpekbCG1yosJEK0EEkwtHdWSFQdqhDXafZjwrhIurt2QB6ru6MQVBmd7iMlHq-cJgTveWosG5yvrFLNxDYLlAsb_x_EcNTOAF566K92OhvB1SU38DqPhfJRdA8xCT0YEppW3dDR4HFKZRygOq-raHkiixAqgdFmBY2M9JtnoDl3D1sidL2YQpEh1_3rvXYtUu-uWIF8A2aUai4j9_LaA7fIWz_QjaC8vzX"
                alt="BugForge Cloud Telemetry Core"
                className="split-visual-bg-img"
              />
              <div className="split-visual-overlay-top" />
              <div className="split-visual-overlay-side" />
              <div className="split-ambient-glow-primary" />
              <div className="split-ambient-glow-tertiary" />
            </div>

            {/* Top Badges */}
            <div className="split-visual-top-row">
              <div className="split-badge-telemetry font-mono">
                <span className="split-badge-ping-dot" />
                <span>Enterprise Telemetry Engine</span>
              </div>
              <div className="split-badge-sre font-mono">
                <span className="material-symbols-outlined" style={{ fontSize: '16px', color: '#38bdf8' }}>
                  memory
                </span>
                <span>SRE Ingest: 1.4M events/s</span>
              </div>
            </div>

            {/* Bottom Copy & Glass Stat Cards */}
            <div className="split-visual-bottom-wrap">
              <div className="split-badge-core font-mono">
                <span className="material-symbols-outlined" style={{ fontSize: '15px', color: '#ffb59a' }}>
                  bolt
                </span>
                <span>v2.1.4 Cloud Forge Core</span>
              </div>

              <h2 className="split-visual-headline font-display">
                Precision Bug Resolution &amp; Sprint Velocity Engine
              </h2>

              <p className="split-visual-lead">
                Harness real-time defect isolation, automated root cause telemetry, and cybernetic issue
                tracking designed for high-velocity engineering teams.
              </p>

              <div className="split-stat-grid font-mono">
                <div className="split-stat-card">
                  <p className="split-stat-label">Mean Time To Triage</p>
                  <p className="split-stat-val font-display">&lt; 90s</p>
                </div>
                <div className="split-stat-card">
                  <p className="split-stat-label">Resolution Surge</p>
                  <p className="split-stat-val font-display" style={{ color: '#34d399' }}>
                    +48.6%
                  </p>
                </div>
                {/* <div className="split-stat-card">
                  <p className="split-stat-label">CI Pipeline Lock</p>
                  <p className="split-stat-val font-display" style={{ color: '#67e8f9' }}>
                    Zero Lag
                  </p>
                </div> */}
              </div>
            </div>
          </div>

          {/* Right 30% Width Area: Authentication Panel */}
          <div className="split-form-panel">
            <div className="split-form-inner">
              <div className="split-form-brand-header">
                <img
                  src="/logo.png"
                  alt="BugForge Logo"
                  style={{ height: '42px', width: 'auto', objectFit: 'contain' }}
                />
              </div>

              <div className="split-form-heading-wrap">
                <h1 className="split-form-title font-display">Sign in</h1>
                <p className="split-form-desc">Enter your workspace credentials to continue.</p>
              </div>

              {error && (
                <div
                  style={{
                    backgroundColor: '#fef2f2',
                    border: '1px solid #fecaca',
                    color: '#991b1b',
                    borderRadius: '10px',
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '1.25rem'
                  }}
                  role="alert"
                >
                  <span className="material-symbols-outlined" style={{ fontSize: '18px', color: '#dc2626' }}>
                    error
                  </span>
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} autoComplete="off">
                <div className="split-form-group">
                  <label className="split-input-label" htmlFor="email">
                    Work Email Address
                  </label>
                  <div className="split-input-wrapper">
                    <span className="material-symbols-outlined split-input-icon">
                      alternate_email
                    </span>
                    <input
                      id="email"
                      type="email"
                      className="split-form-input"
                      placeholder="developer@company.com"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      required
                      autoComplete="email"
                    />
                  </div>
                </div>

                <div className="split-form-group">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <label className="split-input-label" htmlFor="password" style={{ margin: 0 }}>
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() => setShowRecoveryModal(true)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#0050c3',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        padding: 0
                      }}
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="split-input-wrapper">
                    <span className="material-symbols-outlined split-input-icon">
                      lock
                    </span>
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      className="split-form-input"
                      placeholder="••••••••••••"
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      required
                      autoComplete="current-password"
                      style={{ paddingRight: '42px' }}
                    />
                    <button
                      type="button"
                      className="split-input-eye-btn"
                      onClick={() => setShowPassword(!showPassword)}
                      title={showPassword ? 'Hide password' : 'Show password'}
                    >
                      <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
                        {showPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                {/* <div className="split-options-row">
                  <label className="split-checkbox-label">
                    <input
                      type="checkbox"
                      className="split-checkbox-input"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                    />
                    <span>Remember me</span>
                  </label>
                  <span className="split-encryption-badge">TLS 1.3 Encrypted</span>
                </div> */}

                <button
                  type="submit"
                  className="split-btn-submit"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <span
                        className="material-symbols-outlined"
                        style={{ fontSize: '18px', animation: 'bf-pulse 1s infinite' }}
                      >
                        sync
                      </span>
                      <span>Authenticating Workspace...</span>
                    </>
                  ) : (
                    <>
                      <span>Sign In to Workspace</span>
                      <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
                        arrow_forward
                      </span>
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* <div className="split-form-security-footer font-mono">
              <span className="material-symbols-outlined" style={{ fontSize: '16px', color: '#c54500' }}>
                verified_user
              </span>
              <span>Hardware 2FA enforced • SOC2 Type II Certified</span>
            </div> */}
          </div>
        </div>
      </main>

      {/* --------------------------------------------------------------------
          Footer
          -------------------------------------------------------------------- */}
      <footer className="split-login-footer font-mono">
        <div className="split-footer-container">
          <div className="split-footer-status">
            <span className="split-status-pulse-dot" />
            <span>All Systems Operational • Auth Gateway v2.4</span>
          </div>
          <div>© 2025 BugForge Inc. High-velocity issue tracking.</div>
        </div>
      </footer>

      {/* --------------------------------------------------------------------
          Modal: Register Info
          -------------------------------------------------------------------- */}
      {showRegisterModal && (
        <div
          className="flight-deck-modal-backdrop"
          onClick={() => setShowRegisterModal(false)}
        >
          <div
            className="flight-deck-modal-dialog"
            style={{ maxWidth: '480px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header-styled">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="material-symbols-outlined" style={{ color: '#0050c3' }}>
                  badge
                </span>
                <span className="font-display" style={{ fontWeight: 800, fontSize: '1.1rem' }}>
                  Workspace Account Provisioning
                </span>
              </div>
              <button
                className="modal-close-btn"
                onClick={() => setShowRegisterModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="modal-body-styled">
              <p style={{ fontSize: '0.9rem', color: '#49607e', lineHeight: 1.6, marginBottom: '16px' }}>
                Public self-registration is disabled for enterprise workspace security. User accounts,
                team roles, and project permissions are provisioned directly by your organization's
                workspace administrator.
              </p>
              <div
                style={{
                  padding: '12px 14px',
                  borderRadius: '10px',
                  backgroundColor: '#eff4ff',
                  border: '1px solid #c4dcff',
                  fontSize: '0.85rem',
                  color: '#0050c3'
                }}
              >
                <strong>Need an account?</strong> Contact your team lead or company administrator to
                request BugForge workspace access.
              </div>
            </div>
            <div className="modal-footer-styled">
              <button
                className="split-btn-submit"
                style={{ width: 'auto', padding: '8px 20px', height: '40px', fontSize: '0.85rem' }}
                onClick={() => setShowRegisterModal(false)}
              >
                Understood
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------
          Modal: Password Recovery
          -------------------------------------------------------------------- */}
      {showRecoveryModal && (
        <div
          className="flight-deck-modal-backdrop"
          onClick={() => setShowRecoveryModal(false)}
        >
          <div
            className="flight-deck-modal-dialog"
            style={{ maxWidth: '480px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header-styled">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="material-symbols-outlined" style={{ color: '#0050c3' }}>
                  lock_reset
                </span>
                <span className="font-display" style={{ fontWeight: 800, fontSize: '1.1rem' }}>
                  Password Recovery
                </span>
              </div>
              <button
                className="modal-close-btn"
                onClick={() => setShowRecoveryModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="modal-body-styled">
              <p style={{ fontSize: '0.9rem', color: '#49607e', lineHeight: 1.6, marginBottom: '16px' }}>
                BugForge workspaces utilize centralized enterprise identity management. If you forgot your password:
              </p>
              <ol style={{ fontSize: '0.85rem', color: '#334155', paddingLeft: '20px', lineHeight: 1.7, margin: 0 }}>
                <li>Contact your organization's BugForge Administrator.</li>
                <li>Request an identity verification and temporary credential reset.</li>
                <li>If your company uses SAML SSO or LDAP, reset your password via your corporate identity provider.</li>
              </ol>
            </div>
            <div className="modal-footer-styled">
              <button
                className="split-btn-submit"
                style={{ width: 'auto', padding: '8px 20px', height: '40px', fontSize: '0.85rem' }}
                onClick={() => setShowRecoveryModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
