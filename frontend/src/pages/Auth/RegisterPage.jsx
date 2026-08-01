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
      setError(requestError.response?.data?.detail || 'Unable to create the account.')
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
          title="Account created"
          primaryLabel="Continue to login"
          onPrimary={confirmAndContinue}
          onClose={() => setConfirmationVisible(false)}
        >
          <p>Your account has been successfully created. You can now sign in and start using BugForge.</p>
        </Modal>
      )}
      <div className="login-split">
        {/* Left — visual panel */}
        <section className="login-visual">
          <div className="login-visual-copy">
            <span className="eyebrow">Get started</span>
            <h2>
              Create your BugForge account and{' '}
              <span>own every release.</span>
            </h2>
            <p>
              Join product teams that want clear issue ownership, faster resolution, and
              better release rhythm. BugForge gives your team one space for bugs, projects,
              and collaboration.
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
            <div style={{ textAlign: 'left', marginBottom: '24px' }}>
              <img src="/logo.png" alt="BugForge Logo" style={{ height: 120, objectFit: 'contain' }} />
            </div>
            <h1>Create account</h1>
            <p>Start tracking work with BugForge.</p>
            {error && <p className="error-message" role="alert">{error}</p>}
            <label>
              <span>Full name</span>
              <input
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="Jane Smith"
                minLength="2"
                required
              />
            </label>
            <label>
              <span>Email</span>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="you@company.com"
                required
              />
            </label>
            <label>
              <span>Password</span>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Min. 8 characters"
                minLength="8"
                required
              />
            </label>
            <label>
              <span>Role</span>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {roles.map((role) => <option key={role}>{role}</option>)}
              </select>
            </label>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>Creating account…</>
              ) : (
                <>Create account <i className="bi bi-arrow-right" /></>
              )}
            </button>
            <p className="auth-link">
              Already registered? <Link to="/login">Sign in</Link>
            </p>
          </form>
        </section>
      </div>
    </main>
  )
}
