import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { login } from '../../services/authService'
import Toast from '../../components/Toast/Toast'

export default function LoginPage() {
  const navigate = useNavigate()
  const { user, isLoading, signIn } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [toastMessage, setToastMessage] = useState('')

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
      setToastMessage('Login successful! Redirecting to dashboard…')
      setTimeout(() => navigate('/dashboard', { replace: true }), 0)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Invalid email or password. Please check your credentials.')
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
            <span className="eyebrow" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', background: 'rgba(37,99,235,0.1)', color: '#2563eb', borderRadius: '999px', fontSize: '0.78rem', fontWeight: 700, marginBottom: '12px' }}>
              <i className="bi bi-shield-check" /> Enterprise Defect Intelligence
            </span>
            <h2>
              Secure your ship cycle with{' '}
              <span className="gradient-text">intelligent defect tracking</span>
            </h2>
            <p>
              A modern workspace for engineering, QA, and product teams to prioritize, assign, and resolve
              defects with AI assistance. Monitor real-time telemetry from backlog to deployment.
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
            <div style={{ textAlign: 'left', marginBottom: '20px' }}>
              <img src="/logo.png" alt="BugForge Logo" style={{ height: 48, objectFit: 'contain' }} />
            </div>
            <h1>Welcome back</h1>
            <p>Sign in to your BugForge workspace to continue.</p>
            {error && (
              <div className="alert alert-danger d-flex align-items-center gap-2 py-2 px-3" role="alert" style={{ borderRadius: '10px', fontSize: '0.85rem' }}>
                <i className="bi bi-exclamation-circle-fill flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            <label>
              <span>Email Address</span>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="developer@company.com"
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
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
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
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <><i className="bi bi-arrow-repeat spin" /> Signing in…</>
              ) : (
                <>Sign in to Workspace <i className="bi bi-arrow-right" /></>
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
