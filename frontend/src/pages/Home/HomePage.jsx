import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import './HomePage.css'

const INITIAL_CARDS = [
  {
    id: 'BF-1092',
    title: 'Checkout token rate limiter loop',
    column: 'backlog',
    priority: 'P0 BLOCKER',
    badgeType: 'p0',
    mutations: '4 mutations',
    tag: 'Auto-triaged',
    branch: 'fix/rate-limit-leak',
    milestone: '2.4',
    reporter: 'Sentry Telemetry',
    assignee: { name: 'A. Lee', initials: 'AL' },
    details: 'Excessive 429 retries exhausting redis connection pool on checkout submit endpoint.',
    telemetry: 'Trace: TokenLimiterMiddleware:44 -> PoolTimeout'
  },
  {
    id: 'BF-1098',
    title: 'SVG avatar cache misaligned',
    column: 'backlog',
    priority: 'P2 DEFECT',
    badgeType: 'p2',
    mutations: '1-click repro',
    tag: 'Client UI',
    branch: 'fix/svg-avatar-cache',
    milestone: '2.4',
    reporter: 'Sarah QA',
    assignee: { name: 'J. Doe', initials: 'JD' },
    details: 'ViewBox scale discrepancy causes 2px clip on high-DPI retina mobile viewports.',
    telemetry: 'Chrome v128 / iOS 17.4 Safari viewport repro attached'
  },
  {
    id: 'BF-1088',
    title: 'Redis lease mutex lock contention',
    column: 'debug',
    priority: 'INVESTIGATING',
    badgeType: 'debug',
    mutations: 'VS Code live',
    tag: 'fix/auth-deadlock-lease',
    branch: 'fix/auth-deadlock-lease',
    milestone: '2.4',
    reporter: 'DevOps Sentinel',
    assignee: { name: 'M. Kovacs', initials: 'MK' },
    details: 'Deadlock condition when token refresher and session invalidator race for lease key.',
    telemetry: 'Thread dump: 14 goroutines blocked on sync.Mutex'
  },
  {
    id: 'BF-1076',
    title: 'CORS preflight failure on cluster-EU',
    column: 'done',
    priority: 'PR MERGED',
    badgeType: 'done',
    mutations: 'Regression 0/28',
    tag: 'MTTR: 14m',
    branch: 'fix/cors-preflight-eu',
    milestone: '2.4',
    reporter: 'EU Gateway Monitor',
    assignee: { name: 'S. Khan', initials: 'SK' },
    details: 'Options header omitted from ingress gateway route rules during region rollover.',
    telemetry: 'PR #418 merged into main; smoke suite 28/28 passed'
  }
]

export default function HomePage() {
  const { user } = useAuth()

  // State for Interactive Kanban
  const [cards, setCards] = useState(INITIAL_CARDS)
  const [selectedTicket, setSelectedTicket] = useState(null)
  const [activeMilestone, setActiveMilestone] = useState('2.4')
  const [telemetrySeconds, setTelemetrySeconds] = useState(4)
  const [velocityGain, setVelocityGain] = useState(41.8)

  // State for Defect Matrix Heatmap (Bento Module A)
  const [activeSeverity, setActiveSeverity] = useState('p0')

  // State for Terminal Repro Simulator (Bento Module B)
  const [terminalState, setTerminalState] = useState('idle') // idle | running | done

  // State for Blocker Radar (Bento Module C)
  const [slackPingSent, setSlackPingSent] = useState(false)

  // State for Interactive Tour / Walkthrough Modal
  const [showTourModal, setShowTourModal] = useState(false)
  const [activeTourTab, setActiveTourTab] = useState('kanban')

  // Live telemetry sync ticker simulation
  useEffect(() => {
    const timer = setInterval(() => {
      setTelemetrySeconds((prev) => {
        if (prev >= 12) return 1
        return prev + 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Advance ticket column
  const handleAdvanceTicket = (ticketId, e) => {
    if (e) e.stopPropagation()
    setCards((prev) =>
      prev.map((card) => {
        if (card.id !== ticketId) return card
        let nextCol = card.column
        let nextPriority = card.priority
        let nextBadge = card.badgeType

        if (card.column === 'backlog') {
          nextCol = 'debug'
          nextPriority = 'INVESTIGATING'
          nextBadge = 'debug'
        } else if (card.column === 'debug') {
          nextCol = 'done'
          nextPriority = 'PR MERGED'
          nextBadge = 'done'
          setVelocityGain((v) => Number((v + 3.4).toFixed(1)))
        } else {
          nextCol = 'backlog'
          nextPriority = 'P0 BLOCKER'
          nextBadge = 'p0'
        }

        const updated = { ...card, column: nextCol, priority: nextPriority, badgeType: nextBadge }
        if (selectedTicket && selectedTicket.id === ticketId) {
          setSelectedTicket(updated)
        }
        return updated
      })
    )
  }

  // Filtered cards based on milestone toggle
  const displayedCards = cards.filter(
    (card) => activeMilestone === 'all' || card.milestone === activeMilestone
  )

  const backlogCards = displayedCards.filter((c) => c.column === 'backlog')
  const debugCards = displayedCards.filter((c) => c.column === 'debug')
  const doneCards = displayedCards.filter((c) => c.column === 'done')

  // Terminal Runner Simulation
  const handleRunTerminal = () => {
    setTerminalState('running')
    setTimeout(() => {
      setTerminalState('done')
    }, 1600)
  }

  const primaryTargetUrl = user ? '/dashboard' : '/login'
  const sprintTargetUrl = user ? '/sprints' : '/login'

  return (
    <div className="home-flight-deck">
      {/* --------------------------------------------------------------------
          Sticky Flight Deck Header
          -------------------------------------------------------------------- */}
      <header className="flight-deck-header">
        <div className="flight-deck-nav-container">
          <Link to="/" className="brand-link">
            <img
              src="/logo.png"
              alt="BugForge Logo"
              style={{ height: '36px', width: 'auto', objectFit: 'contain' }}
            />
          </Link>

          <nav className="desktop-nav-links">
            <a href="#sprint-boards" className="nav-anchor active">
              <span className="nav-indicator-dot"></span>
              <span>Sprint Boards</span>
            </a>
            <a href="#defect-triage" className="nav-anchor">Defect Triage</a>
            <a href="#pipeline" className="nav-anchor">Pipeline</a>
            <a href="#comparison" className="nav-anchor">Comparison</a>
          </nav>

          <div className="nav-actions">
            <button
              className="btn-nav-demo"
              onClick={() => setShowTourModal(true)}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>
                smart_display
              </span>
              <span>Live Tour</span>
            </button>

            <Link className="btn-nav-cta" to={primaryTargetUrl}>
              <span>{user ? 'Open Workspace' : 'Start Sprint Free'}</span>
              <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>
                arrow_forward
              </span>
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* ------------------------------------------------------------------
            Hero Section: Asymmetrical Layout + Interactive Kanban Flight Deck
            ------------------------------------------------------------------ */}
        <section className="hero-deck-section grid-mesh" id="sprint-boards">
          <div className="ambient-glow-hero"></div>

          <div className="hero-deck-container">
            <div className="hero-grid">
              {/* Left Column: Hero Copy */}
              <div>
                <div className="hero-pill-badge font-mono">
                  <span className="hero-pill-dot"></span>
                  <span>Sprint Flight Deck 3.0</span>
                  <span style={{ color: '#93c5fd' }}>/</span>
                  <span style={{ color: '#475569', fontWeight: 500 }}>Reactive Kanban</span>
                </div>

                <h1 className="hero-headline font-display">
                  Turn Defect Chaos into{' '}
                  <span className="gradient-text-stitch">Shipping Momentum.</span>
                </h1>

                <p className="hero-lead">
                  Eliminate triage backlogs, detect blocked sprint pipelines before standup, and pass
                  deterministic bug replays straight to engineers' IDE branches without manual form clutter.
                </p>

                <div className="hero-actions-group">
                  <Link to={sprintTargetUrl} className="btn-hero-primary">
                    <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
                      view_kanban
                    </span>
                    <span>Launch Sprint Board</span>
                  </Link>

                  <button
                    className="btn-hero-secondary"
                    onClick={() => setShowTourModal(true)}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: '18px', color: 'var(--bf-cobalt)' }}>
                      play_circle
                    </span>
                    <span>Explore Interactive Deck</span>
                  </button>
                </div>

                <div className="hero-trust-row font-mono">
                  <div className="trust-item">
                    <span className="material-symbols-outlined" style={{ color: '#059669', fontSize: '16px' }}>
                      check_circle
                    </span>
                    <span>GitLab &amp; GitHub Sync</span>
                  </div>
                  <div className="trust-item">
                    <span className="material-symbols-outlined" style={{ color: '#059669', fontSize: '16px' }}>
                      check_circle
                    </span>
                    <span>No Credit Card Required</span>
                  </div>
                </div>
              </div>

              {/* Right Column: Live Interactive Mini Kanban Flight Deck */}
              <div id="flight-deck">
                <div className="flight-deck-board-card">
                  {/* Chrome Header */}
                  <div className="deck-chrome-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div className="chrome-dots">
                        <div className="chrome-dot"></div>
                        <div className="chrome-dot"></div>
                        <div className="chrome-dot"></div>
                      </div>
                      <div className="chrome-title-group">
                        <span className="material-symbols-outlined" style={{ color: 'var(--bf-forge)', fontSize: '16px' }}>
                          space_dashboard
                        </span>
                        <span className="chrome-sprint-title font-display">
                          Sprint 42: Core Payment &amp; Auth
                        </span>
                      </div>
                    </div>

                    <div className="burn-status-badge font-mono">
                      <span className="burn-pulse-dot"></span>
                      <span>Sprint Burn: Optimal</span>
                    </div>
                  </div>

                  {/* 3 Kanban Columns */}
                  <div className="kanban-columns-grid">
                    {/* Column 1: Sprint Backlog */}
                    <div className="kanban-col">
                      <div className="col-header">
                        <div className="col-title-group">
                          <span className="col-indicator-dot" style={{ backgroundColor: '#94a3b8' }}></span>
                          <span className="col-title font-display">Sprint Backlog</span>
                        </div>
                        <span className="col-count-pill font-mono">{backlogCards.length}</span>
                      </div>

                      <div className="col-cards-container">
                        {backlogCards.map((card) => (
                          <div
                            key={card.id}
                            className={`kanban-ticket-card ${card.badgeType === 'p0' ? 'card-featured' : ''}`}
                            onClick={() => setSelectedTicket(card)}
                          >
                            <div className="ticket-top-row">
                              <span className={card.badgeType === 'p0' ? 'badge-p0 font-mono' : 'badge-p2 font-mono'}>
                                {card.priority}
                              </span>
                              <span className="ticket-id font-mono">#{card.id}</span>
                            </div>
                            <div className="ticket-title">{card.title}</div>
                            <div className="ticket-footer font-mono">
                              <span>{card.tag}</span>
                              <span
                                style={{ color: 'var(--bf-forge)', fontWeight: 600, cursor: 'pointer' }}
                                onClick={(e) => handleAdvanceTicket(card.id, e)}
                                title="Advance to next column"
                              >
                                Move →
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Column 2: In Active Debug */}
                    <div className="kanban-col">
                      <div className="col-header">
                        <div className="col-title-group">
                          <span className="col-indicator-dot" style={{ backgroundColor: 'var(--bf-cobalt)' }}></span>
                          <span className="col-title font-display" style={{ color: 'var(--bf-forge)' }}>
                            In Active Debug
                          </span>
                        </div>
                        <span className="col-count-pill font-mono" style={{ backgroundColor: '#dbeafe', color: 'var(--bf-forge)' }}>
                          {debugCards.length}
                        </span>
                      </div>

                      <div className="col-cards-container">
                        {debugCards.map((card) => (
                          <div
                            key={card.id}
                            className="kanban-ticket-card card-active-debug"
                            onClick={() => setSelectedTicket(card)}
                          >
                            <div className="ticket-top-row">
                              <span className="badge-debug font-mono">{card.priority}</span>
                              <span className="ticket-id font-mono" style={{ color: 'var(--bf-forge)', fontWeight: 700 }}>
                                #{card.id}
                              </span>
                            </div>
                            <div className="ticket-title">{card.title}</div>

                            <div className="ticket-branch-tag font-mono">
                              <span className="material-symbols-outlined" style={{ fontSize: '13px', color: 'var(--bf-forge)' }}>
                                fork_right
                              </span>
                              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {card.branch}
                              </span>
                            </div>

                            <div className="ticket-footer font-mono">
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span className="avatar-chip">{card.assignee.initials}</span>
                                <span>{card.assignee.name}</span>
                              </div>
                              <span
                                style={{ color: '#047857', fontWeight: 700, cursor: 'pointer' }}
                                onClick={(e) => handleAdvanceTicket(card.id, e)}
                                title="Mark PR Merged"
                              >
                                Merge ✓
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Column 3: QA Verification & Done */}
                    <div className="kanban-col">
                      <div className="col-header">
                        <div className="col-title-group">
                          <span className="col-indicator-dot" style={{ backgroundColor: '#10b981' }}></span>
                          <span className="col-title font-display" style={{ color: '#047857' }}>
                            QA Verification
                          </span>
                        </div>
                        <span className="col-count-pill font-mono" style={{ backgroundColor: '#d1fae5', color: '#065f46' }}>
                          Done ({doneCards.length})
                        </span>
                      </div>

                      <div className="col-cards-container">
                        {doneCards.map((card) => (
                          <div
                            key={card.id}
                            className="kanban-ticket-card card-done"
                            onClick={() => setSelectedTicket(card)}
                          >
                            <div className="ticket-top-row">
                              <span className="badge-done font-mono">
                                <span className="material-symbols-outlined" style={{ fontSize: '12px' }}>check</span>
                                {card.priority}
                              </span>
                              <span className="ticket-id font-mono">#{card.id}</span>
                            </div>
                            <div className="ticket-title title-done">{card.title}</div>
                            <div className="ticket-footer font-mono">
                              <span>{card.tag}</span>
                              <span style={{ color: '#059669', fontWeight: 600 }}>{card.mutations}</span>
                            </div>
                          </div>
                        ))}

                        {/* Velocity Metric pill inside Done column */}
                        <div className="deck-velocity-strip">
                          <div className="velocity-label font-mono">Sprint Velocity Gain</div>
                          <div className="velocity-value font-display">+{velocityGain}% vs last sprint</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Board Bottom Controls */}
                  <div className="deck-bottom-control-strip font-mono">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>Filter:</span>
                      <button
                        className="filter-btn"
                        onClick={() => setActiveMilestone(activeMilestone === '2.4' ? 'all' : '2.4')}
                      >
                        <strong>
                          {activeMilestone === '2.4' ? 'Active Milestone (Release 2.4)' : 'All Items'}
                        </strong>
                      </button>
                      <button
                        className="filter-btn"
                        onClick={() => {
                          setCards(INITIAL_CARDS)
                          setVelocityGain(41.8)
                        }}
                        title="Reset interactive cards"
                      >
                        Reset
                      </button>
                    </div>

                    <span style={{ color: 'var(--bf-slate-400)' }}>
                      Telemetry synced {telemetrySeconds}s ago
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            Key Metric Strip: 4 Crisp Floating Cards
            ------------------------------------------------------------------ */}
        <section className="metrics-strip-section">
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-header">
                <span className="metric-tag font-mono">Velocity Boost</span>
                <span className="material-symbols-outlined" style={{ color: 'var(--bf-forge)', fontSize: '20px' }}>
                  speed
                </span>
              </div>
              <div className="metric-value font-display">3x</div>
              <p className="metric-subtitle font-mono">Faster release cycles</p>
            </div>

            <div className="metric-card">
              <div className="metric-header">
                <span className="metric-tag font-mono">Automated Triage</span>
                <span className="material-symbols-outlined" style={{ color: 'var(--bf-cobalt)', fontSize: '20px' }}>
                  auto_fix_high
                </span>
              </div>
              <div className="metric-value font-display" style={{ color: 'var(--bf-forge)' }}>99.4%</div>
              <p className="metric-subtitle font-mono">Zero missing stack info</p>
            </div>

            <div className="metric-card">
              <div className="metric-header">
                <span className="metric-tag font-mono">Admin Overhead</span>
                <span className="material-symbols-outlined" style={{ color: 'var(--bf-flame)', fontSize: '20px' }}>
                  timer_off
                </span>
              </div>
              <div className="metric-value font-display" style={{ color: 'var(--bf-flame)' }}>0%</div>
              <p className="metric-subtitle font-mono">No manual field entry</p>
            </div>

            <div className="metric-card">
              <div className="metric-header">
                <span className="metric-tag font-mono">Enterprise Standard</span>
                <span className="material-symbols-outlined" style={{ color: '#059669', fontSize: '20px' }}>
                  verified_user
                </span>
              </div>
              <div className="metric-value font-display" style={{ fontSize: '1.75rem' }}>SOC2 Type II</div>
              <p className="metric-subtitle font-mono">Continuous compliance</p>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            Feature Highlights Bento: 3 Rich Dynamic Modules
            ------------------------------------------------------------------ */}
        <section className="bento-section" id="defect-triage">
          <div className="hero-deck-container">
            <div className="bento-header-wrap">
              <div className="bento-badge font-mono">
                <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>
                  dashboard_customize
                </span>
                <span>Flight Deck Modules</span>
              </div>
              <h2 className="section-title font-display">Precision Workflow Instruments</h2>
              <p className="section-subtitle">
                Engineered specifically to remove friction between issue detection, developer triage,
                and verified deployment.
              </p>
            </div>

            <div className="bento-grid">
              {/* Card A: Real-Time Defect Matrix */}
              <div className="bento-card">
                <div>
                  <div className="bento-icon-box" style={{ backgroundColor: 'var(--bf-azure-soft)', color: 'var(--bf-forge)', border: '1px solid var(--bf-border-tone)' }}>
                    <span className="material-symbols-outlined" style={{ fontSize: '22px' }}>
                      grid_view
                    </span>
                  </div>
                  <h3 className="bento-card-title font-display">Real-time Defect Matrix</h3>
                  <p className="bento-card-desc">
                    Instant severity vs. impact heatmap. Stop guessing which crash matters—BugForge automatically sorts issues by blast radius and user impact.
                  </p>

                  {/* Interactive Heatmap Selector */}
                  <div className="heatmap-widget font-mono">
                    <div className="heatmap-label">Interactive Severity Filter</div>
                    <div className="heatmap-cells-row">
                      <button
                        className={`heatmap-btn ${activeSeverity === 'p0' ? 'active' : ''}`}
                        style={{
                          backgroundColor: activeSeverity === 'p0' ? '#ffe4e6' : '#fff1f2',
                          color: '#9f1239',
                          borderColor: activeSeverity === 'p0' ? '#fda4af' : 'transparent'
                        }}
                        onClick={() => setActiveSeverity('p0')}
                      >
                        P0 Critical
                        <br />
                        <span style={{ fontSize: '9px', fontWeight: 400 }}>2 Active</span>
                      </button>

                      <button
                        className={`heatmap-btn ${activeSeverity === 'p1' ? 'active' : ''}`}
                        style={{
                          backgroundColor: activeSeverity === 'p1' ? '#fef3c7' : '#fffbeb',
                          color: '#92400e',
                          borderColor: activeSeverity === 'p1' ? '#fcd34d' : 'transparent'
                        }}
                        onClick={() => setActiveSeverity('p1')}
                      >
                        P1 High
                        <br />
                        <span style={{ fontSize: '9px', fontWeight: 400 }}>5 Pending</span>
                      </button>

                      <button
                        className={`heatmap-btn ${activeSeverity === 'p2' ? 'active' : ''}`}
                        style={{
                          backgroundColor: activeSeverity === 'p2' ? '#dbeafe' : '#eff6ff',
                          color: 'var(--bf-forge)',
                          borderColor: activeSeverity === 'p2' ? '#93c5fd' : 'transparent'
                        }}
                        onClick={() => setActiveSeverity('p2')}
                      >
                        P2 Minor
                        <br />
                        <span style={{ fontSize: '9px', fontWeight: 400 }}>14 Logged</span>
                      </button>
                    </div>

                    <div className="heatmap-preview-box">
                      {activeSeverity === 'p0' && 'Blast Radius: 4,120 active checkout sessions affected • P0 Hotfix deployed'}
                      {activeSeverity === 'p1' && 'Blast Radius: 180 enterprise teams affected • Pending reviewer assignment'}
                      {activeSeverity === 'p2' && 'Blast Radius: Visual viewport cosmetic defect • Scheduled for next sprint cycle'}
                    </div>
                  </div>
                </div>

                <div className="bento-card-footer" style={{ color: 'var(--bf-forge)' }}>
                  <span>Dynamic prioritization</span>
                  <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
                    north_east
                  </span>
                </div>
              </div>

              {/* Card B: Automated QA-to-Dev Pipeline */}
              <div className="bento-card" id="pipeline">
                <div>
                  <div className="bento-icon-box" style={{ backgroundColor: '#eff6ff', color: 'var(--bf-cobalt)', border: '1px solid #dbeafe' }}>
                    <span className="material-symbols-outlined" style={{ fontSize: '22px' }}>
                      alt_route
                    </span>
                  </div>
                  <h3 className="bento-card-title font-display">Automated QA-to-Dev Pipeline</h3>
                  <p className="bento-card-desc">
                    1-click repro links and sandboxed containers reproduce crashes in under 30 seconds. No more "Works on my machine" back-and-forths.
                  </p>

                  {/* Interactive Terminal Sandbox Simulator */}
                  <div className="terminal-simulator font-mono">
                    <div className="terminal-header">
                      <span>Repro Sandbox</span>
                      <span style={{ color: terminalState === 'running' ? '#f59e0b' : '#34d399' }}>
                        {terminalState === 'running' ? 'EXECUTING...' : 'READY'}
                      </span>
                    </div>
                    <div className="terminal-cmd">$ bugforge repro 1088</div>
                    <div className="terminal-output">
                      Spinning up Docker container with verified browser state...
                    </div>
                    {terminalState === 'done' && (
                      <div className="terminal-success">
                        ✔ Environment matched in 1.4s (Playwright ready)
                      </div>
                    )}
                    <button
                      className="terminal-btn-run font-mono"
                      onClick={handleRunTerminal}
                      disabled={terminalState === 'running'}
                    >
                      {terminalState === 'running' ? 'Simulating container...' : '▶ Run Repro Sandbox'}
                    </button>
                  </div>
                </div>

                <div className="bento-card-footer" style={{ color: 'var(--bf-cobalt)' }}>
                  <span>Zero reproduction ambiguity</span>
                  <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
                    north_east
                  </span>
                </div>
              </div>

              {/* Card C: Live Blocker Radar */}
              <div className="bento-card" id="integrations">
                <div>
                  <div className="bento-icon-box" style={{ backgroundColor: '#fff7ed', color: 'var(--bf-flame)', border: '1px solid #ffedd5' }}>
                    <span className="material-symbols-outlined" style={{ fontSize: '22px' }}>
                      radar
                    </span>
                  </div>
                  <h3 className="bento-card-title font-display">Live Blocker Radar</h3>
                  <p className="bento-card-desc">
                    Proactive sprint risk alerts ping team channels before dependencies stall code reviews or deployment milestones.
                  </p>

                  {/* Live Interactive Blocker Alert */}
                  <div className="radar-alert-card">
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <span className="material-symbols-outlined" style={{ color: '#b45309', fontSize: '18px', marginTop: '2px' }}>
                        warning
                      </span>
                      <div style={{ flex: 1 }}>
                        <div className="radar-title">Sprint Bottleneck Alert</div>
                        <div className="radar-detail">
                          PR #312 waiting on auth-lease fix for 18h. Assigned to @sarah-backend.
                        </div>
                        <button
                          className="radar-btn-ping"
                          onClick={() => setSlackPingSent(true)}
                        >
                          {slackPingSent ? '✓ Slack Alert Dispatched to #backend-infra' : '⚡ Dispatch Slack Ping'}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bento-card-footer" style={{ color: 'var(--bf-flame)' }}>
                  <span>Proactive risk resolution</span>
                  <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
                    north_east
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            "The Shift": Direct Before / After Comparison Table
            ------------------------------------------------------------------ */}
        <section className="comparison-section" id="comparison">
          <div className="hero-deck-container">
            <div style={{ textAlign: 'center', maxWidth: '640px', margin: '0 auto 3.5rem' }}>
              <div className="bento-badge font-mono">The Shift</div>
              <h2 className="section-title font-display">
                Bloated Legacy Boards vs. BugForge Flight Deck
              </h2>
              <p className="section-subtitle">
                Experience what happens when issue tracking operates with reactive developer velocity
                instead of spreadsheet bureaucracy.
              </p>
            </div>

            <div className="comparison-grid">
              {/* Legacy Boards */}
              <div className="comparison-card">
                <div>
                  <div className="comparison-card-header">
                    <div className="comparison-card-title font-display" style={{ color: '#334155' }}>
                      <span className="material-symbols-outlined" style={{ color: '#94a3b8' }}>table_rows</span>
                      <span>Bloated Legacy Boards</span>
                    </div>
                    <span className="font-mono" style={{ fontSize: '0.72rem', fontWeight: 600, padding: '4px 10px', borderRadius: '6px', backgroundColor: '#f1f5f9', color: '#475569' }}>
                      High Friction
                    </span>
                  </div>

                  <ul className="comparison-list">
                    <li className="comparison-item">
                      <span className="material-symbols-outlined" style={{ color: '#f43f5e', fontSize: '18px', marginTop: '2px' }}>close</span>
                      <span><strong>Manual card dragging:</strong> Devs waste standup time moving cards across cluttered columns.</span>
                    </li>
                    <li className="comparison-item">
                      <span className="material-symbols-outlined" style={{ color: '#f43f5e', fontSize: '18px', marginTop: '2px' }}>close</span>
                      <span><strong>Missing reproduction steps:</strong> QA tickets lack HAR files, state snapshots, and console dumps.</span>
                    </li>
                    <li className="comparison-item">
                      <span className="material-symbols-outlined" style={{ color: '#f43f5e', fontSize: '18px', marginTop: '2px' }}>close</span>
                      <span><strong>Detached from Git:</strong> Status updates depend on human memory rather than merged pull requests.</span>
                    </li>
                    <li className="comparison-item">
                      <span className="material-symbols-outlined" style={{ color: '#f43f5e', fontSize: '18px', marginTop: '2px' }}>close</span>
                      <span><strong>Bloated enterprise plugins:</strong> Sluggish UI loads that take 4 seconds every time you click an issue.</span>
                    </li>
                  </ul>
                </div>

                <div className="comparison-footer font-mono" style={{ color: '#64748b' }}>
                  <span>Sprint Overhead: ~6 hrs/dev/sprint</span>
                  <span style={{ color: '#e11d48', fontWeight: 700 }}>Productivity Drain</span>
                </div>
              </div>

              {/* BugForge Reactive Board */}
              <div className="comparison-card card-reactive">
                <div className="comparison-badge-accent"></div>

                <div style={{ position: 'relative', zIndex: 1 }}>
                  <div className="comparison-card-header">
                    <div className="comparison-card-title font-display" style={{ color: 'var(--bf-deep-navy)' }}>
                      <span className="material-symbols-outlined" style={{ color: 'var(--bf-forge)' }}>flight_takeoff</span>
                      <span>BugForge Reactive Board</span>
                    </div>
                    <span className="font-mono" style={{ fontSize: '0.72rem', fontWeight: 700, padding: '4px 10px', borderRadius: '6px', backgroundColor: 'var(--bf-forge)', color: '#ffffff' }}>
                      Autonomous
                    </span>
                  </div>

                  <ul className="comparison-list">
                    <li className="comparison-item">
                      <span className="material-symbols-outlined" style={{ color: '#059669', fontSize: '18px', marginTop: '2px' }}>check_circle</span>
                      <span style={{ color: 'var(--bf-deep-navy)' }}><strong>Autonomous transitions:</strong> Cards advance in real time as branches are cut, pushed, and merged.</span>
                    </li>
                    <li className="comparison-item">
                      <span className="material-symbols-outlined" style={{ color: '#059669', fontSize: '18px', marginTop: '2px' }}>check_circle</span>
                      <span style={{ color: 'var(--bf-deep-navy)' }}><strong>Built-in deterministic replay:</strong> Every ticket includes isolated container repro and DOM telemetry.</span>
                    </li>
                    <li className="comparison-item">
                      <span className="material-symbols-outlined" style={{ color: '#059669', fontSize: '18px', marginTop: '2px' }}>check_circle</span>
                      <span style={{ color: 'var(--bf-deep-navy)' }}><strong>Bi-directional Git sync:</strong> PR merges automatically execute regression verification and close tickets.</span>
                    </li>
                    <li className="comparison-item">
                      <span className="material-symbols-outlined" style={{ color: '#059669', fontSize: '18px', marginTop: '2px' }}>check_circle</span>
                      <span style={{ color: 'var(--bf-deep-navy)' }}><strong>Sub-50ms reactive speed:</strong> Instant keyboard-driven navigation built straight for modern velocity.</span>
                    </li>
                  </ul>
                </div>

                <div className="comparison-footer font-mono" style={{ position: 'relative', zIndex: 1, color: 'var(--bf-forge)' }}>
                  <span>Sprint Overhead: 0 mins</span>
                  <span style={{ color: '#047857', fontWeight: 800 }}>Pure Flow State</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            Conversion Banner Section
            ------------------------------------------------------------------ */}
        <section className="cta-banner-section" id="start-sprint">
          <div className="hero-deck-container">
            <div className="cta-banner-card">
              <div className="cta-ambient-glow-1"></div>
              <div className="cta-ambient-glow-2"></div>

              <div className="cta-banner-content">
                <div className="cta-pill font-mono">
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#34d399' }}></span>
                  <span>Instant Setup in &lt; 2 Minutes</span>
                </div>

                <h2 className="cta-headline font-display">Forge your next sprint without defects.</h2>
                <p className="cta-lead">
                  Instant setup with GitHub, GitLab &amp; Slack. Connect your engineering repositories
                  and experience zero-friction bug resolution today.
                </p>

                <div className="cta-btn-group">
                  <Link to={primaryTargetUrl} className="cta-primary-btn">
                    <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>rocket_launch</span>
                    <span>Start Free Sprint</span>
                  </Link>

                  <button
                    className="cta-secondary-btn"
                    onClick={() => setShowTourModal(true)}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>play_arrow</span>
                    <span>Watch 2-Min Walkthrough</span>
                  </button>
                </div>

                <div className="cta-perks-row font-mono">
                  <span>✓ Unlimited Repositories</span>
                  <span style={{ color: '#475569' }}>•</span>
                  <span>✓ Native Slack &amp; Discord Alerts</span>
                  <span style={{ color: '#475569' }}>•</span>
                  <span>✓ Zero Setup Fees</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* --------------------------------------------------------------------
          Professional Flight Deck Footer
          -------------------------------------------------------------------- */}
      <footer className="flight-deck-footer font-mono">
        <div className="hero-deck-container">
          <div className="footer-top-row">
            <div className="footer-brand-wrap">
              <img
                src="/logo.png"
                alt="BugForge Logo"
                style={{ height: '30px', width: 'auto', objectFit: 'contain' }}
              />
              <div style={{ height: '16px', width: '1px', backgroundColor: '#cbd5e1' }}></div>
              <span className="footer-tagline">Sprint Flight Deck &amp; Defect Triage</span>
            </div>

            <div className="status-indicator-pill">
              <span style={{ position: 'relative', display: 'flex', width: '8px', height: '8px' }}>
                <span style={{ position: 'absolute', width: '100%', height: '100%', borderRadius: '50%', backgroundColor: '#34d399', opacity: 0.75, animation: 'bf-pulse 1.5s infinite' }}></span>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }}></span>
              </span>
              <span>Flight Deck Engine: 99.99% Operational</span>
            </div>
          </div>

          <div className="footer-bottom-row">
            <div className="footer-nav-links">
              <a href="#sprint-boards" className="footer-link">Sprint Boards</a>
              <a href="#defect-triage" className="footer-link">Defect Triage</a>
              <a href="#pipeline" className="footer-link">Pipeline</a>
              <a href="#comparison" className="footer-link">Comparison</a>
              <a href="https://github.com" target="_blank" rel="noreferrer" className="footer-link">GitHub</a>
            </div>

            <p style={{ margin: 0 }}>© {new Date().getFullYear()} BugForge Inc. Precision Code-First Issue Resolution.</p>
          </div>
        </div>
      </footer>

      {/* --------------------------------------------------------------------
          Modal 1: Interactive Issue Inspector
          -------------------------------------------------------------------- */}
      {selectedTicket && (
        <div className="flight-deck-modal-backdrop" onClick={() => setSelectedTicket(null)}>
          <div className="flight-deck-modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-styled">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="font-mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--bf-forge)' }}>
                  #{selectedTicket.id}
                </span>
                <span className={`badge-${selectedTicket.badgeType} font-mono`}>
                  {selectedTicket.priority}
                </span>
              </div>
              <button className="modal-close-btn" onClick={() => setSelectedTicket(null)}>✕</button>
            </div>

            <div className="modal-body-styled">
              <h3 className="font-display" style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--bf-deep-navy)', marginBottom: '12px' }}>
                {selectedTicket.title}
              </h3>

              <p style={{ fontSize: '0.9rem', color: 'var(--bf-slate-600)', lineHeight: 1.6, marginBottom: '16px' }}>
                {selectedTicket.details}
              </p>

              <div style={{ padding: '12px', borderRadius: '10px', backgroundColor: '#f8fafc', border: '1px solid var(--bf-border-tone)', marginBottom: '16px' }}>
                <div className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--bf-slate-500)', textTransform: 'uppercase', marginBottom: '6px' }}>
                  Deterministic Telemetry
                </div>
                <code className="font-mono" style={{ fontSize: '0.75rem', color: '#0f172a' }}>
                  {selectedTicket.telemetry}
                </code>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', fontSize: '0.8rem' }}>
                <div>
                  <span style={{ color: 'var(--bf-slate-500)' }}>Active Branch:</span>
                  <div className="font-mono" style={{ fontWeight: 600, color: 'var(--bf-forge)', marginTop: '2px' }}>
                    {selectedTicket.branch}
                  </div>
                </div>
                <div>
                  <span style={{ color: 'var(--bf-slate-500)' }}>Assigned Engineer:</span>
                  <div style={{ fontWeight: 600, color: 'var(--bf-deep-navy)', marginTop: '2px' }}>
                    {selectedTicket.assignee.name}
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer-styled">
              <button
                className="btn-hero-secondary"
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                onClick={() => setSelectedTicket(null)}
              >
                Close
              </button>
              <button
                className="btn-hero-primary"
                style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                onClick={() => handleAdvanceTicket(selectedTicket.id)}
              >
                Advance to Next Stage →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------
          Modal 2: Interactive Product Tour Walkthrough
          -------------------------------------------------------------------- */}
      {showTourModal && (
        <div className="flight-deck-modal-backdrop" onClick={() => setShowTourModal(false)}>
          <div className="flight-deck-modal-dialog" style={{ maxWidth: '720px' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-styled">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="material-symbols-outlined" style={{ color: 'var(--bf-forge)' }}>
                  flight_takeoff
                </span>
                <span className="font-display" style={{ fontWeight: 800, fontSize: '1.1rem' }}>
                  BugForge Flight Deck Tour
                </span>
              </div>
              <button className="modal-close-btn" onClick={() => setShowTourModal(false)}>✕</button>
            </div>

            <div className="modal-body-styled">
              {/* Tour Navigation Tabs */}
              <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--bf-slate-100)', paddingBottom: '12px', marginBottom: '20px' }}>
                <button
                  className={`filter-btn ${activeTourTab === 'kanban' ? 'active' : ''}`}
                  style={{
                    backgroundColor: activeTourTab === 'kanban' ? 'var(--bf-forge)' : 'transparent',
                    color: activeTourTab === 'kanban' ? '#ffffff' : 'var(--bf-slate-600)',
                    fontWeight: 600
                  }}
                  onClick={() => setActiveTourTab('kanban')}
                >
                  1. Reactive Kanban
                </button>
                <button
                  className={`filter-btn ${activeTourTab === 'repro' ? 'active' : ''}`}
                  style={{
                    backgroundColor: activeTourTab === 'repro' ? 'var(--bf-forge)' : 'transparent',
                    color: activeTourTab === 'repro' ? '#ffffff' : 'var(--bf-slate-600)',
                    fontWeight: 600
                  }}
                  onClick={() => setActiveTourTab('repro')}
                >
                  2. Auto Telemetry Repro
                </button>
                <button
                  className={`filter-btn ${activeTourTab === 'git' ? 'active' : ''}`}
                  style={{
                    backgroundColor: activeTourTab === 'git' ? 'var(--bf-forge)' : 'transparent',
                    color: activeTourTab === 'git' ? '#ffffff' : 'var(--bf-slate-600)',
                    fontWeight: 600
                  }}
                  onClick={() => setActiveTourTab('git')}
                >
                  3. Autonomous Git Sync
                </button>
              </div>

              {/* Tour Tab Content */}
              {activeTourTab === 'kanban' && (
                <div>
                  <h4 className="font-display" style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '8px' }}>
                    Zero-Latency Sprint Navigation
                  </h4>
                  <p style={{ fontSize: '0.88rem', color: 'var(--bf-slate-600)', lineHeight: 1.6 }}>
                    Unlike traditional bloated issue trackers that take seconds to render a single card,
                    BugForge is built with reactive keyboard accelerators, sub-50ms live updates, and direct sprint cycle synchronizations.
                  </p>
                  <div style={{ marginTop: '16px', padding: '14px', borderRadius: '12px', backgroundColor: 'var(--bf-azure-light)', border: '1px solid var(--bf-border-tone)' }}>
                    <div className="font-mono" style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--bf-forge)' }}>
                      Key Features:
                    </div>
                    <ul style={{ fontSize: '0.8rem', color: 'var(--bf-slate-700)', paddingLeft: '20px', marginTop: '6px', marginBottom: 0 }}>
                      <li>Instant card advancement tied directly to PR lifecycle</li>
                      <li>Live burn-down velocity calculations without manual reports</li>
                      <li>Single-click filter by active sprint milestones</li>
                    </ul>
                  </div>
                </div>
              )}

              {activeTourTab === 'repro' && (
                <div>
                  <h4 className="font-display" style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '8px' }}>
                    Deterministic Container Replays
                  </h4>
                  <p style={{ fontSize: '0.88rem', color: 'var(--bf-slate-600)', lineHeight: 1.6 }}>
                    Tired of bugs that can't be reproduced? BugForge automatically encapsulates the user's browser DOM state,
                    network HAR replay, and console telemetry into an ephemeral container ready for inspection.
                  </p>
                  <div style={{ marginTop: '16px', padding: '14px', borderRadius: '12px', backgroundColor: '#0f172a', color: '#e2e8f0', fontFamily: 'monospace', fontSize: '0.78rem' }}>
                    <span style={{ color: '#38bdf8' }}>$ bugforge repro 1088 --ide=vscode</span>
                    <div style={{ color: '#94a3b8', marginTop: '6px' }}>Launching Playwright debug session with recorded state...</div>
                    <div style={{ color: '#34d399', marginTop: '4px' }}>✔ Breakpoint hit on TokenLimiterMiddleware.ts:44</div>
                  </div>
                </div>
              )}

              {activeTourTab === 'git' && (
                <div>
                  <h4 className="font-display" style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '8px' }}>
                    Autonomous Git CI/CD Sync
                  </h4>
                  <p style={{ fontSize: '0.88rem', color: 'var(--bf-slate-600)', lineHeight: 1.6 }}>
                    No engineer should spend standup moving cards. BugForge links to GitHub &amp; GitLab webhooks.
                    When a pull request references an issue ID, status transitions, reviewer assignees, and merge verifications happen automatically.
                  </p>
                  <div style={{ marginTop: '16px', padding: '14px', borderRadius: '12px', backgroundColor: '#ecfdf5', border: '1px solid #a7f3d0' }}>
                    <span className="font-mono" style={{ fontSize: '0.8rem', fontWeight: 700, color: '#047857' }}>
                      Verified Flow State: 0 minutes spent on administrative status updates.
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer-styled">
              <Link to={primaryTargetUrl} className="btn-hero-primary" style={{ padding: '10px 20px', fontSize: '0.88rem' }}>
                Get Started with BugForge →
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
