import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export default function HomePage() {
  const { user, isLoading } = useAuth()

  if (isLoading) return <p className="page-status">Loading session…</p>
  if (user) return <Navigate to="/dashboard" replace />

  return (
    <main className="home-page">
      {/* Minimal nav */}
      <nav className="home-nav">
        <div className="brand">
          <img src="/logo.png" alt="BugForge Logo" style={{ height: 80, objectFit: 'contain' }} />
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <Link className="btn btn-outline-primary btn-sm" to="/login">Sign in</Link>
          <Link className="btn btn-primary btn-sm" to="/register">Get started</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero-section">
        <div className="hero-copy">
          <span className="hero-badge">
            <i className="bi bi-stars" />
            Issue Tracking Reimagined
          </span>
          <h1>
            Track issues, ship faster,{' '}
            <span className="gradient-text">stay aligned.</span>
          </h1>
          <p>
            BugForge helps engineering, QA, and product teams turn chaos into clarity.
            Manage bugs, monitor progress, and collaborate from one elegant workspace.
          </p>
          <div className="hero-actions">
            <Link className="hero-button btn-primary-hero" to="/register">
              <i className="bi bi-rocket-takeoff" />
              Start for free
            </Link>
            <Link className="hero-button btn-outline-hero" to="/login">
              Sign in
              <i className="bi bi-arrow-right" />
            </Link>
          </div>
        </div>

        <div className="hero-summary-card">
          <div className="hero-summary-item">
            <strong>Why BugForge?</strong>
            <p>Because every bug deserves fast resolution, clear ownership, and fewer distractions.</p>
          </div>
          <div className="hero-summary-item">
            <strong>The problem we solve</strong>
            <p>Unstructured tracking, unclear handoffs, and slow triage lead to wasted time.</p>
          </div>
          <div className="hero-summary-item">
            <strong>How it helps</strong>
            <p>Centralize bugs, prioritize what matters, and give teams one place to move forward.</p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features-section">
        <div className="feature-card feature-primary">
          <div className="feature-icon"><i className="bi bi-lightning-charge-fill" /></div>
          <h2>Built for fast-moving teams</h2>
          <p>See issue status, assignments, and progress in a glance — without hunting across tools.</p>
        </div>
        <div className="feature-card feature-secondary">
          <div className="feature-icon"><i className="bi bi-people-fill" /></div>
          <h2>Collaborate with confidence</h2>
          <p>Share context, link issues to projects, and keep stakeholders aligned on every release.</p>
        </div>
        <div className="feature-card feature-tertiary">
          <div className="feature-icon"><i className="bi bi-graph-up-arrow" /></div>
          <h2>Improve quality over time</h2>
          <p>Track recurring issues, surface bottlenecks, and continuously reduce bug backlog overhead.</p>
        </div>
      </section>
    </main>
  )
}
