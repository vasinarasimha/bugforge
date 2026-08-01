import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { login } from '../../services/authService'
import Toast from '../../components/Toast/Toast'

export default function LoginPage() {
  const navigate = useNavigate()
  const { user, isLoading, signIn } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [toastMessage, setToastMessage] = useState('')

  if (isLoading) return <p className="page-status">Loading session…</p>
  if (user) return <Navigate to="/dashboard" replace />

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      const { data } = await login(form)
      signIn(data)
      setToastMessage('Login successful! Redirecting to dashboard…')
      setTimeout(() => navigate('/dashboard', { replace: true }), 700)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to sign in. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page login-page">
      <Toast message={toastMessage} variant="success" onClose={() => setToastMessage('')} />
      <div className="login-split">
        {/* Left — visual panel */}
        <section className="login-visual">
          <div className="login-visual-copy">
            <span className="eyebrow">BugForge</span>
            <h2>
              Secure your ship cycle with{' '}
              <span>smarter bug tracking</span>
            </h2>
            <p>
              A modern workspace for engineering teams to prioritize, assign, and resolve
              issues fast. See everything from backlog to release in one polished interface.
            </p>
            <div className="visual-stats">
              <div>
                <strong>40%</strong>
                <p>Faster issue resolution</p>
              </div>
              <div>
                <strong>3×</strong>
                <p>More predictable releases</p>
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
            <h1>Welcome back</h1>
            <p>Sign in to your BugForge workspace.</p>
            {error && <p className="error-message" role="alert">{error}</p>}
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
                placeholder="••••••••"
                required
              />
            </label>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <><i className="bi bi-arrow-repeat" style={{ animation: 'spin 1s linear infinite' }} /> Signing in…</>
              ) : (
                <>Sign in <i className="bi bi-arrow-right" /></>
              )}
            </button>
            <p className="auth-link">
              New to BugForge? <Link to="/register">Create an account</Link>
            </p>
          </form>
        </section>
      </div>
    </main>
  )
}
