import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { register } from '../../services/authService'
import Modal from '../../components/Modal/Modal'

const roles = ['Admin', 'Developer', 'QA', 'Reporter']

export default function RegisterPage() {
  const navigate = useNavigate()
  const { user, isLoading } = useAuth()
  const [form, setForm] = useState({ full_name: '', email: '', password: '', role: 'Reporter' })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [confirmationVisible, setConfirmationVisible] = useState(false)

  if (isLoading) return <p className="page-status">Loading session…</p>
  if (user) return <Navigate to="/dashboard" replace />

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await register(form)
      setConfirmationVisible(true)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to create the account. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const confirmAndContinue = () => {
    setConfirmationVisible(false)
    navigate('/login', { replace: true })
  }

  return (
    <main className="auth-page login-page">
      {confirmationVisible && (
        <Modal
          title="Account Created Successfully"
          primaryLabel="Continue to Sign In"
          onPrimary={confirmAndContinue}
          onClose={() => setConfirmationVisible(false)}
        >
          <div className="d-flex align-items-center gap-3 py-2">
            <div style={{ width: 44, height: 44, borderRadius: '50%', background: 'rgba(16,185,129,0.12)', color: '#059669', display: 'grid', placeContent: 'center', fontSize: '1.4rem', flexShrink: 0 }}>
              <i className="bi bi-check-circle-fill" />
            </div>
            <div>
              <p style={{ margin: 0, fontWeight: 600, color: '#0f172a' }}>Your BugForge account is ready!</p>
              <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: '#64748b' }}>You can now sign in with your email and password to access your team workspaces.</p>
            </div>
          </div>
        </Modal>
      )}
      <div className="login-split">
        {/* Left — visual panel */}
        <section className="login-visual">
          <div className="login-visual-copy">
            <span className="eyebrow" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', background: 'rgba(37,99,235,0.1)', color: '#2563eb', borderRadius: '999px', fontSize: '0.78rem', fontWeight: 700, marginBottom: '12px' }}>
              <i className="bi bi-rocket-takeoff" /> Join BugForge
            </span>
            <h2>
              Create your account and{' '}
              <span className="gradient-text">own every release</span>
            </h2>
            <p>
              Join product teams that want clear issue ownership, faster resolution, and
              better release rhythm. BugForge gives your team one unified space for defects, sprints,
              and AI-driven resolution assistance.
            </p>
            <div className="visual-stats">
              <div>
                <strong>Trust</strong>
                <p>Built for engineering and QA teams.</p>
              </div>
              <div>
                <strong>Clarity</strong>
                <p>See every issue, assignment, and priority clearly.</p>
              </div>
            </div>
          </div>
          <div className="login-visual-image" aria-hidden="true">
            <div className="shape shape-one" />
            <div className="shape shape-two" />
            <div className="shape shape-three" />
          </div>
        </section>

        {/* Right — form */}
        <section className="login-panel">
          <form className="auth-card" onSubmit={handleSubmit}>
            <div style={{ textAlign: 'left', marginBottom: '20px' }}>
              <img src="/logo.png" alt="BugForge Logo" style={{ height: 48, objectFit: 'contain' }} />
            </div>
            <h1>Create Account</h1>
            <p>Start tracking and resolving defects with BugForge.</p>
            {error && (
              <div className="alert alert-danger d-flex align-items-center gap-2 py-2 px-3" role="alert" style={{ borderRadius: '10px', fontSize: '0.85rem' }}>
                <i className="bi bi-exclamation-circle-fill flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            <label>
              <span>Full Name</span>
              <input
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="Jane Smith"
                minLength="2"
                required
                autoComplete="name"
              />
            </label>
            <label>
              <span>Email Address</span>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="you@company.com"
                required
                autoComplete="email"
              />
            </label>
            <label>
              <span>Password</span>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="Min. 8 characters"
                  minLength="8"
                  required
                  autoComplete="new-password"
                  style={{ paddingRight: '40px', width: '100%' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute', right: '10px', background: 'none', border: 'none',
                    cursor: 'pointer', color: '#94a3b8', padding: '4px', fontSize: '1rem'
                  }}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  <i className={`bi ${showPassword ? 'bi-eye-slash' : 'bi-eye'}`} />
                </button>
              </div>
            </label>
            <label>
              <span>Workspace Role</span>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {roles.map((role) => <option key={role}>{role}</option>)}
              </select>
            </label>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <><i className="bi bi-arrow-repeat spin" /> Creating Account…</>
              ) : (
                <>Create Account <i className="bi bi-arrow-right" /></>
              )}
            </button>
            <p className="auth-link">
              Already registered? <Link to="/login">Sign in to workspace</Link>
            </p>
          </form>
        </section>
      </div>
    </main>
  )
}
