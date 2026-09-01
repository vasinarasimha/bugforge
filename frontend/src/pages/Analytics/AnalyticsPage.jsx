import { useState, useEffect, useMemo } from 'react'
import { getAnalyticsOverview } from '../../services/analyticsService'
import { getProjects } from '../../services/projectService'
import { getTeams } from '../../services/teamService'
import { useAuth } from '../../hooks/useAuth'

// Helper for SVG donut slice calculations
function createDonutArcs(items, total, radius, innerRadius, cx, cy) {
  if (!total || total === 0 || !items.length) return []
  let accumulatedAngle = -Math.PI / 2

  return items.map((item) => {
    const fraction = item.count / total
    const angle = fraction * 2 * Math.PI
    const startAngle = accumulatedAngle
    const endAngle = accumulatedAngle + angle
    accumulatedAngle = endAngle

    const x1 = cx + radius * Math.cos(startAngle)
    const y1 = cy + radius * Math.sin(startAngle)
    const x2 = cx + radius * Math.cos(endAngle)
    const y2 = cy + radius * Math.sin(endAngle)

    const ix1 = cx + innerRadius * Math.cos(endAngle)
    const iy1 = cy + innerRadius * Math.sin(endAngle)
    const ix2 = cx + innerRadius * Math.cos(startAngle)
    const iy2 = cy + innerRadius * Math.sin(startAngle)

    const largeArc = angle > Math.PI ? 1 : 0
    const d = `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} L ${ix1} ${iy1} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${ix2} ${iy2} Z`

    return { ...item, d }
  })
}

export default function AnalyticsPage() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState('')
  const [selectedTeam, setSelectedTeam] = useState('')
  const [days, setDays] = useState(30)
  const [hoveredTrendIndex, setHoveredTrendIndex] = useState(null)

  // Load project options for filter dropdown
  useEffect(() => {
    getProjects()
      .then((res) => setProjects(res.data || []))
      .catch(() => setProjects([]))
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const projId = selectedProject ? Number(selectedProject) : null
      const teamId = selectedTeam ? Number(selectedTeam) : null
      const res = await getAnalyticsOverview(projId, teamId, days)
      setData(res.data)
    } catch (err) {
      console.error('Analytics load error:', err)
      setError(err.response?.data?.detail || 'Unable to load analytics metrics from the database.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [selectedProject, selectedTeam, days])

  const kpis = data?.kpis
  const trends = data?.defect_trends || []
  const severities = data?.severity_distribution || []
  const statuses = data?.status_distribution || []
  const categories = data?.category_distribution || []
  const workloads = data?.developer_workload || []
  const devPerf = data?.developer_performance
  const resolutionMetrics = data?.resolution_metrics
  const scopeTeams = data?.scope_teams || []
  const role = data?.user_role || user?.role || 'Developer'
  const scopeTitle = data?.scope_title || 'Analytics & Performance'
  const isEmptyScope = Boolean(data?.is_empty_scope)
  const emptyScopeMessage = data?.empty_scope_message || 'No defect metrics available.'

  const totalDefects = kpis?.total_defects || 0
  const statusArcs = createDonutArcs(statuses, totalDefects, 70, 46, 85, 85)
  const severityArcs = createDonutArcs(severities, totalDefects, 70, 46, 85, 85)

  // Trend coordinates
  const maxTrendVal = Math.max(...trends.map((t) => Math.max(t.created_count, t.resolved_count)), 1)
  const chartW = 560
  const chartH = 180
  const padX = 36
  const padY = 24
  const plotW = chartW - padX * 2
  const plotH = chartH - padY * 2

  const getX = (idx) => padX + (idx / Math.max(trends.length - 1, 1)) * plotW
  const getY = (val) => chartH - padY - (val / maxTrendVal) * plotH

  const createdPoints = trends.map((t, i) => `${getX(i)},${getY(t.created_count)}`).join(' ')
  const resolvedPoints = trends.map((t, i) => `${getX(i)},${getY(t.resolved_count)}`).join(' ')

  const createdArea =
    trends.length > 0
      ? `M ${getX(0)},${chartH - padY} ` +
        trends.map((t, i) => `L ${getX(i)},${getY(t.created_count)}`).join(' ') +
        ` L ${getX(trends.length - 1)},${chartH - padY} Z`
      : ''

  // Subtitle per role
  const getRoleSubtitle = () => {
    switch (role) {
      case 'Admin':
        return 'Organization-wide defect lifecycle metrics, cross-team performance, and telemetry.'
      case 'Project Manager':
        return 'Combined and individual performance across all engineering teams under your management.'
      case 'Team Leader':
        return 'Team engineering workload, resolution velocity, and defect distribution for your team.'
      case 'Developer':
        return 'Personal defect resolution rate, assigned issue status, resolution time, and aging analysis.'
      case 'QA':
        return 'Quality assurance tracking, reported issue statuses, and verification turnaround metrics.'
      case 'Reporter':
        return 'Overview of defects you reported and their current progress through the resolution lifecycle.'
      default:
        return 'Comprehensive defect lifecycle metrics and telemetry.'
    }
  }

  return (
    <div className="analytics-page">
      {/* ── Top Header Toolbar ── */}
      <section className="analytics-header">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span
              className="badge bg-primary-subtle text-primary border border-primary px-2 py-1"
              style={{ fontSize: '0.75rem', fontWeight: 600 }}
            >
              {role.toUpperCase()} SCOPE
            </span>
            <span className="text-muted small">
              <i className="bi bi-shield-check text-success" /> Server-side Telemetry
            </span>
          </div>
          <h2>{scopeTitle}</h2>
          <p>{getRoleSubtitle()}</p>
        </div>

        <div className="analytics-toolbar">
          {/* Team Filter for PM or Admin (when scope teams available) */}
          {(role === 'Project Manager' || role === 'Admin') && scopeTeams.length > 0 && (
            <div className="analytics-select-wrap">
              <i className="bi bi-diagram-3" />
              <select
                value={selectedTeam}
                onChange={(e) => setSelectedTeam(e.target.value)}
                className="analytics-select"
              >
                <option value="">
                  {role === 'Project Manager' ? 'All Managed Teams (Combined)' : 'All Teams (Org-Wide)'}
                </option>
                {scopeTeams.map((t) => (
                  <option key={t.team_id} value={t.team_id}>
                    {t.team_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Project Selector */}
          <div className="analytics-select-wrap">
            <i className="bi bi-folder" />
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="analytics-select"
            >
              <option value="">All Authorized Projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.key ? `[${p.key}] ` : ''}
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Time Range Pills */}
          <div className="analytics-pill-group">
            {[7, 30, 90].map((d) => (
              <button
                key={d}
                type="button"
                className={`analytics-pill-btn ${days === d ? 'active' : ''}`}
                onClick={() => setDays(d)}
              >
                {d} Days
              </button>
            ))}
          </div>

          {/* Refresh Button */}
          <button
            type="button"
            className="analytics-refresh-btn"
            onClick={loadData}
            disabled={loading}
            title="Refresh database metrics"
          >
            <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`} />
          </button>
        </div>
      </section>

      {error && (
        <div className="alert alert-danger d-flex align-items-center gap-2 mb-4" role="alert">
          <i className="bi bi-exclamation-triangle-fill" />
          <span>{error}</span>
        </div>
      )}

      {/* Empty State Banner when no team or no defects exist */}
      {isEmptyScope && !loading && (
        <div
          className="card border-0 shadow-sm mb-4 text-center p-5"
          style={{ borderRadius: '16px', backgroundColor: '#f8fafc', border: '1.5px dashed #cbd5e1' }}
        >
          <div className="py-2">
            <i className="bi bi-info-circle text-primary fs-1 d-block mb-3" />
            <h4 className="fw-bold text-dark mb-1">{emptyScopeMessage}</h4>
            <p className="text-muted small mb-0" style={{ maxWidth: '500px', margin: '0 auto' }}>
              {role === 'Team Leader' || role === 'Project Manager'
                ? 'Contact your System Administrator to be assigned to your active team.'
                : 'As you create, triage, or work on assigned defects, your telemetry and metrics will update in real time.'}
            </p>
          </div>
        </div>
      )}

      {/* ── KPI Stat Cards ── */}
      <section className="analytics-kpi-grid">
        <div className="analytics-kpi-card tone-primary">
          <div className="kpi-icon-wrap">
            <i className="bi bi-bug-fill" />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">
              {role === 'Developer'
                ? 'My Assigned Defects'
                : role === 'Reporter'
                ? 'My Reported Defects'
                : 'Total Defects'}
            </span>
            <span className="kpi-value">{loading ? '—' : kpis?.total_defects ?? 0}</span>
            <span className="kpi-sub">
              {role === 'Developer' ? 'Assigned to your queue' : 'Scoped defect volume'}
            </span>
          </div>
        </div>

        <div className="analytics-kpi-card tone-warning">
          <div className="kpi-icon-wrap">
            <i className="bi bi-exclamation-circle" />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">Open Defects</span>
            <span className="kpi-value">{loading ? '—' : kpis?.open_defects ?? 0}</span>
            <span className="kpi-sub">Awaiting fix / triage</span>
          </div>
        </div>

        <div className="analytics-kpi-card tone-purple">
          <div className="kpi-icon-wrap">
            <i className="bi bi-arrow-repeat" />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">In Progress</span>
            <span className="kpi-value">{loading ? '—' : kpis?.in_progress_defects ?? 0}</span>
            <span className="kpi-sub">Actively being worked on</span>
          </div>
        </div>

        <div className="analytics-kpi-card tone-success">
          <div className="kpi-icon-wrap">
            <i className="bi bi-check2-circle" />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">Resolved</span>
            <span className="kpi-value">{loading ? '—' : kpis?.resolved_defects ?? 0}</span>
            <span className="kpi-sub">Fix implemented</span>
          </div>
        </div>

        <div className="analytics-kpi-card tone-slate">
          <div className="kpi-icon-wrap">
            <i className="bi bi-archive" />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">Closed</span>
            <span className="kpi-value">{loading ? '—' : kpis?.closed_defects ?? 0}</span>
            <span className="kpi-sub">Verified & complete</span>
          </div>
        </div>

        <div className="analytics-kpi-card tone-indigo">
          <div className="kpi-icon-wrap">
            <i className="bi bi-stopwatch" />
          </div>
          <div className="kpi-content">
            <span className="kpi-label">Avg Resolution Time</span>
            <span className="kpi-value kpi-value-sm">
              {loading ? '—' : resolutionMetrics?.formatted || 'No data'}
            </span>
            <span className="kpi-sub">
              {resolutionMetrics?.sample_size
                ? `From ${resolutionMetrics.sample_size} resolved defects`
                : 'No resolution data yet'}
            </span>
          </div>
        </div>
      </section>

      {/* ── PM / ADMIN: Managed Team Performance Cards ── */}
      {(role === 'Project Manager' || role === 'Admin') && scopeTeams.length > 0 && !selectedTeam && (
        <section className="mb-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
              <h4 className="fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                <i className="bi bi-diagram-3-fill text-primary" />
                {role === 'Project Manager' ? 'Managed Teams Overview' : 'Team Performance Comparison'}
              </h4>
              <p className="text-muted small mb-0">
                Comparative defect health and resolution rates across teams.
              </p>
            </div>
            <div className="card-body px-4 pb-4">
              <div className="row g-3">
                {scopeTeams.map((team) => (
                  <div key={team.team_id} className="col-12 col-md-6 col-lg-4">
                    <div
                      className="p-3 rounded-3 border bg-white shadow-sm h-100 d-flex flex-column justify-content-between"
                      style={{ transition: 'transform .15s ease' }}
                    >
                      <div>
                        <div className="d-flex justify-content-between align-items-start mb-2">
                          <h6 className="fw-bold text-dark mb-0">{team.team_name}</h6>
                          <span
                            className="badge bg-primary-subtle text-primary border border-primary"
                            style={{ fontSize: '0.7rem' }}
                          >
                            {team.member_count} Members
                          </span>
                        </div>
                        <div className="text-muted small mb-3">
                          Leader: <strong>{team.team_leader_name || 'Unassigned'}</strong>
                        </div>
                      </div>

                      <div>
                        <div className="d-flex justify-content-between small text-muted mb-1">
                          <span>Resolution Rate:</span>
                          <strong className="text-success">{team.resolution_rate_percentage}%</strong>
                        </div>
                        <div className="progress mb-3" style={{ height: '6px' }}>
                          <div
                            className="progress-bar bg-success"
                            style={{ width: `${team.resolution_rate_percentage}%` }}
                          />
                        </div>

                        <div className="d-flex justify-content-between text-center border-top pt-2">
                          <div>
                            <div className="fw-bold text-dark small">{team.total_defects}</div>
                            <div className="text-muted" style={{ fontSize: '0.7rem' }}>Total</div>
                          </div>
                          <div>
                            <div className="fw-bold text-warning small">{team.open_defects}</div>
                            <div className="text-muted" style={{ fontSize: '0.7rem' }}>Open</div>
                          </div>
                          <div>
                            <div className="fw-bold text-success small">{team.resolved_defects}</div>
                            <div className="text-muted" style={{ fontSize: '0.7rem' }}>Resolved</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ── Row 1: Defect Trend Chart & Status Breakdown ── */}
      <section className="analytics-grid-two">
        {/* Trend Area Chart */}
        <div className="analytics-panel">
          <div className="panel-header">
            <div>
              <h3>Defect Activity Trends</h3>
              <p>Daily volume of created vs. resolved defects over the last {days} days</p>
            </div>
            <div className="trend-legend">
              <span className="legend-item">
                <span className="legend-dot created" /> Created
              </span>
              <span className="legend-item">
                <span className="legend-dot resolved" /> Resolved
              </span>
            </div>
          </div>

          <div className="chart-container">
            {trends.length === 0 || totalDefects === 0 ? (
              <div className="analytics-empty">
                <i className="bi bi-calendar-x" />
                <p>No defect activity recorded in the selected date range.</p>
              </div>
            ) : (
              <div style={{ width: '100%', position: 'relative' }}>
                <svg
                  viewBox={`0 0 ${chartW} ${chartH}`}
                  className="trend-svg"
                  style={{ width: '100%', height: 'auto', overflow: 'visible' }}
                >
                  <defs>
                    <linearGradient id="createdGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Grid Lines */}
                  {[0, 0.25, 0.5, 0.75, 1].map((p, idx) => {
                    const y = chartH - padY - p * plotH
                    return (
                      <g key={idx}>
                        <line
                          x1={padX}
                          y1={y}
                          x2={chartW - padX}
                          y2={y}
                          stroke="rgba(148,163,184,0.18)"
                          strokeDasharray="3 3"
                        />
                        <text x={padX - 8} y={y + 3} textAnchor="end" fontSize="10" fill="#94a3b8">
                          {Math.round(p * maxTrendVal)}
                        </text>
                      </g>
                    )
                  })}

                  {/* Area fill */}
                  {createdArea && <path d={createdArea} fill="url(#createdGrad)" />}

                  {/* Lines */}
                  {createdPoints && (
                    <polyline
                      fill="none"
                      stroke="#3b82f6"
                      strokeWidth="2.5"
                      points={createdPoints}
                      strokeLinecap="round"
                    />
                  )}
                  {resolvedPoints && (
                    <polyline
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2.5"
                      points={resolvedPoints}
                      strokeLinecap="round"
                    />
                  )}

                  {/* Points & Hover Interactivity */}
                  {trends.map((t, idx) => {
                    const cx = getX(idx)
                    const cyCreated = getY(t.created_count)
                    const cyResolved = getY(t.resolved_count)
                    const isHovered = hoveredTrendIndex === idx

                    return (
                      <g
                        key={idx}
                        onMouseEnter={() => setHoveredTrendIndex(idx)}
                        onMouseLeave={() => setHoveredTrendIndex(null)}
                      >
                        {/* Hover bar */}
                        <line
                          x1={cx}
                          y1={padY}
                          x2={cx}
                          y2={chartH - padY}
                          stroke={isHovered ? 'rgba(59,130,246,0.3)' : 'transparent'}
                          strokeWidth="12"
                        />
                        <circle
                          cx={cx}
                          cy={cyCreated}
                          r={isHovered ? 5 : 3}
                          fill="#3b82f6"
                          stroke="#fff"
                          strokeWidth="1.5"
                        />
                        <circle
                          cx={cx}
                          cy={cyResolved}
                          r={isHovered ? 5 : 3}
                          fill="#10b981"
                          stroke="#fff"
                          strokeWidth="1.5"
                        />
                      </g>
                    )
                  })}

                  {/* X Axis Labels */}
                  {trends.map((t, idx) => {
                    if (idx % Math.ceil(trends.length / 6) === 0 || idx === trends.length - 1) {
                      return (
                        <text
                          key={idx}
                          x={getX(idx)}
                          y={chartH - 4}
                          textAnchor="middle"
                          fontSize="10"
                          fill="#94a3b8"
                        >
                          {t.date.slice(5)}
                        </text>
                      )
                    }
                    return null
                  })}
                </svg>

                {/* Hover Tooltip */}
                {hoveredTrendIndex !== null && trends[hoveredTrendIndex] && (
                  <div
                    className="trend-tooltip"
                    style={{
                      left: `${(getX(hoveredTrendIndex) / chartW) * 100}%`,
                      top: '10px',
                    }}
                  >
                    <strong>{trends[hoveredTrendIndex].date}</strong>
                    <div>
                      <span style={{ color: '#3b82f6' }}>● Created:</span>{' '}
                      {trends[hoveredTrendIndex].created_count}
                    </div>
                    <div>
                      <span style={{ color: '#10b981' }}>● Resolved:</span>{' '}
                      {trends[hoveredTrendIndex].resolved_count}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Status Breakdown */}
        <div className="analytics-panel">
          <div className="panel-header">
            <div>
              <h3>Defects by Status</h3>
              <p>Distribution across defect workflow lifecycle</p>
            </div>
          </div>

          <div className="donut-panel-body">
            {totalDefects === 0 ? (
              <div className="analytics-empty">
                <i className="bi bi-pie-chart" />
                <p>No status data available.</p>
              </div>
            ) : (
              <>
                <div className="donut-graphic">
                  <svg viewBox="0 0 170 170" width="140" height="140">
                    {statusArcs.map((arc, idx) => (
                      <path
                        key={idx}
                        d={arc.d}
                        fill={arc.color}
                        style={{ transition: 'opacity .2s', cursor: 'pointer' }}
                        opacity="0.92"
                      />
                    ))}
                    <text
                      x="85"
                      y="80"
                      textAnchor="middle"
                      fontSize="18"
                      fontWeight="700"
                      fill="#0f172a"
                    >
                      {totalDefects}
                    </text>
                    <text x="85" y="96" textAnchor="middle" fontSize="10" fill="#64748b">
                      Defects
                    </text>
                  </svg>
                </div>

                <div className="donut-legend">
                  {statuses.map((st) => (
                    <div key={st.name} className="donut-legend-row">
                      <span className="donut-legend-indicator" style={{ background: st.color }} />
                      <span className="donut-legend-name">{st.name}</span>
                      <span className="donut-legend-count">{st.count}</span>
                      <span className="donut-legend-pct">{st.percentage}%</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ── Row 2: Severity & Category Breakdown ── */}
      <section className="analytics-grid-two">
        {/* Severity Breakdown */}
        <div className="analytics-panel">
          <div className="panel-header">
            <div>
              <h3>Defects by Severity</h3>
              <p>Impact assessment: Critical, High, Medium, and Low</p>
            </div>
          </div>

          <div className="donut-panel-body">
            {totalDefects === 0 ? (
              <div className="analytics-empty">
                <i className="bi bi-shield-slash" />
                <p>No severity data available.</p>
              </div>
            ) : (
              <>
                <div className="donut-graphic">
                  <svg viewBox="0 0 170 170" width="140" height="140">
                    {severityArcs.map((arc, idx) => (
                      <path
                        key={idx}
                        d={arc.d}
                        fill={arc.color}
                        style={{ transition: 'opacity .2s', cursor: 'pointer' }}
                        opacity="0.92"
                      />
                    ))}
                    <text
                      x="85"
                      y="80"
                      textAnchor="middle"
                      fontSize="18"
                      fontWeight="700"
                      fill="#0f172a"
                    >
                      {kpis?.critical_open_defects ?? 0}
                    </text>
                    <text
                      x="85"
                      y="96"
                      textAnchor="middle"
                      fontSize="10"
                      fill="#ef4444"
                      fontWeight="600"
                    >
                      Crit Open
                    </text>
                  </svg>
                </div>

                <div className="donut-legend">
                  {severities.map((sev) => (
                    <div key={sev.name} className="donut-legend-row">
                      <span className="donut-legend-indicator" style={{ background: sev.color }} />
                      <span className="donut-legend-name">{sev.name}</span>
                      <span className="donut-legend-count">{sev.count}</span>
                      <span className="donut-legend-pct">{sev.percentage}%</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Category Breakdown (Horizontal Bars) */}
        <div className="analytics-panel">
          <div className="panel-header">
            <div>
              <h3>Defects by Category</h3>
              <p>Functional distribution across defect types and subsystems</p>
            </div>
          </div>

          <div className="category-bars-body">
            {categories.length === 0 || totalDefects === 0 ? (
              <div className="analytics-empty">
                <i className="bi bi-tags" />
                <p>No categories assigned yet.</p>
              </div>
            ) : (
              <div className="category-list">
                {categories.map((cat, idx) => (
                  <div key={cat.name} className="category-row">
                    <div className="category-row-meta">
                      <span className="category-name">{cat.name}</span>
                      <span className="category-val">
                        {cat.count} ({cat.percentage}%)
                      </span>
                    </div>
                    <div className="category-bar-track">
                      <div
                        className="category-bar-fill"
                        style={{
                          width: `${Math.max(cat.percentage, 4)}%`,
                          background: `hsl(${idx * 45 + 210}, 80%, 55%)`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── DEVELOPER SPECIFIC: DEVELOPER PERFORMANCE SECTION ── */}
      {role === 'Developer' && devPerf && (
        <section className="mb-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-transparent border-0 pt-4 px-4 pb-2">
              <h4 className="fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                <i className="bi bi-speedometer2 text-primary" />
                Developer Performance Telemetry
              </h4>
              <p className="text-muted small mb-0">
                Personal resolution rate, turnaround speed, and active queue aging.
              </p>
            </div>
            <div className="card-body px-4 pb-4">
              {/* Performance Stats Cards */}
              <div className="row g-3 mb-4">
                <div className="col-12 col-md-3">
                  <div className="p-3 bg-light rounded-3 border text-center">
                    <div className="text-muted small fw-semibold text-uppercase mb-1">
                      Resolution Rate
                    </div>
                    <div className="fs-3 fw-bold text-success">
                      {devPerf.resolution_rate_percentage}%
                    </div>
                    <div className="text-muted small">
                      {devPerf.resolved_defects + devPerf.closed_defects} of{' '}
                      {devPerf.my_assigned_defects} done
                    </div>
                  </div>
                </div>

                <div className="col-12 col-md-3">
                  <div className="p-3 bg-light rounded-3 border text-center">
                    <div className="text-muted small fw-semibold text-uppercase mb-1">
                      High / Critical In Queue
                    </div>
                    <div className="fs-3 fw-bold text-danger">
                      {devPerf.critical_assigned + devPerf.high_assigned}
                    </div>
                    <div className="text-muted small">
                      {devPerf.critical_assigned} Critical • {devPerf.high_assigned} High
                    </div>
                  </div>
                </div>

                <div className="col-12 col-md-3">
                  <div className="p-3 bg-light rounded-3 border text-center">
                    <div className="text-muted small fw-semibold text-uppercase mb-1">
                      Avg Turnaround Speed
                    </div>
                    <div className="fs-3 fw-bold text-primary">
                      {devPerf.avg_resolution_time_formatted}
                    </div>
                    <div className="text-muted small">Database lifecycle timestamps</div>
                  </div>
                </div>

                <div className="col-12 col-md-3">
                  <div className="p-3 bg-light rounded-3 border text-center">
                    <div className="text-muted small fw-semibold text-uppercase mb-1">
                      Active In Queue
                    </div>
                    <div className="fs-3 fw-bold text-warning">
                      {devPerf.open_defects + devPerf.in_progress_defects}
                    </div>
                    <div className="text-muted small">
                      {devPerf.open_defects} Open • {devPerf.in_progress_defects} In Progress
                    </div>
                  </div>
                </div>
              </div>

              <div className="row g-4">
                {/* Aging Open Defects */}
                <div className="col-12 col-lg-6">
                  <h6 className="fw-bold text-dark mb-2 d-flex align-items-center gap-2">
                    <i className="bi bi-hourglass-split text-warning" />
                    Aging Open Defects (Requires Attention)
                  </h6>
                  <div className="table-responsive border rounded-3">
                    <table className="table table-sm table-hover mb-0">
                      <thead className="table-light">
                        <tr>
                          <th className="py-2 px-3">Key</th>
                          <th className="py-2 px-3">Title</th>
                          <th className="py-2 px-3">Severity</th>
                          <th className="py-2 px-3 text-end">Days Open</th>
                        </tr>
                      </thead>
                      <tbody>
                        {devPerf.aging_defects.length === 0 ? (
                          <tr>
                            <td colSpan="4" className="text-center py-3 text-muted small">
                              🎉 No open aging defects in your queue!
                            </td>
                          </tr>
                        ) : (
                          devPerf.aging_defects.map((iss) => (
                            <tr key={iss.id}>
                              <td className="py-2 px-3 fw-bold text-primary small">
                                {iss.issue_key}
                              </td>
                              <td
                                className="py-2 px-3 text-truncate small"
                                style={{ maxWidth: '180px' }}
                                title={iss.title}
                              >
                                {iss.title}
                              </td>
                              <td className="py-2 px-3">
                                <span
                                  className={`badge ${
                                    iss.severity === 'Critical'
                                      ? 'bg-danger'
                                      : iss.severity === 'High'
                                      ? 'bg-warning text-dark'
                                      : 'bg-secondary'
                                  }`}
                                  style={{ fontSize: '0.68rem' }}
                                >
                                  {iss.severity}
                                </span>
                              </td>
                              <td className="py-2 px-3 text-end fw-semibold small text-danger">
                                {iss.days_open} days
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Recently Resolved */}
                <div className="col-12 col-lg-6">
                  <h6 className="fw-bold text-dark mb-2 d-flex align-items-center gap-2">
                    <i className="bi bi-check-circle-fill text-success" />
                    Recently Resolved Defects
                  </h6>
                  <div className="table-responsive border rounded-3">
                    <table className="table table-sm table-hover mb-0">
                      <thead className="table-light">
                        <tr>
                          <th className="py-2 px-3">Key</th>
                          <th className="py-2 px-3">Title</th>
                          <th className="py-2 px-3">Severity</th>
                          <th className="py-2 px-3 text-end">Resolved</th>
                        </tr>
                      </thead>
                      <tbody>
                        {devPerf.recently_resolved.length === 0 ? (
                          <tr>
                            <td colSpan="4" className="text-center py-3 text-muted small">
                              No resolved defects logged yet.
                            </td>
                          </tr>
                        ) : (
                          devPerf.recently_resolved.map((iss) => (
                            <tr key={iss.id}>
                              <td className="py-2 px-3 fw-bold text-primary small">
                                {iss.issue_key}
                              </td>
                              <td
                                className="py-2 px-3 text-truncate small"
                                style={{ maxWidth: '180px' }}
                                title={iss.title}
                              >
                                {iss.title}
                              </td>
                              <td className="py-2 px-3">
                                <span
                                  className="badge bg-success"
                                  style={{ fontSize: '0.68rem' }}
                                >
                                  {iss.severity}
                                </span>
                              </td>
                              <td className="py-2 px-3 text-end text-muted small">
                                {iss.updated_at ? iss.updated_at.slice(0, 10) : '—'}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ── ADMIN / PM / TL: DEVELOPER WORKLOAD SECTION ── */}
      {role !== 'Developer' && (
        <section className="analytics-grid-two">
          {/* Developer Workload */}
          <div className="analytics-panel">
            <div className="panel-header">
              <div>
                <h3>Team Engineering Workload</h3>
                <p>Active and resolved defect distribution per team engineer</p>
              </div>
            </div>

            <div className="workload-body">
              {workloads.length === 0 ? (
                <div className="analytics-empty">
                  <i className="bi bi-person-x" />
                  <p>No team engineers with assigned defects found.</p>
                </div>
              ) : (
                <div className="workload-list">
                  {workloads.map((dev) => {
                    const activeCount = dev.open + dev.in_progress
                    return (
                      <div key={dev.developer_id} className="workload-item">
                        <div className="workload-meta">
                          <div className="workload-user">
                            <div className="workload-avatar">
                              {dev.developer_name
                                ? dev.developer_name.charAt(0).toUpperCase()
                                : 'D'}
                            </div>
                            <div>
                              <strong>{dev.developer_name}</strong>
                              <span>{dev.email}</span>
                            </div>
                          </div>
                          <div className="workload-counts">
                            <span
                              className="badge-workload active"
                              title="Active (Open + In Progress)"
                            >
                              {activeCount} Active
                            </span>
                            <span
                              className="badge-workload resolved"
                              title="Resolved / Closed"
                            >
                              {dev.resolved + dev.closed} Done
                            </span>
                            <span className="badge-workload total" title="Total Assigned">
                              {dev.total_assigned} Total
                            </span>
                          </div>
                        </div>

                        {/* Multi-segment workload progress bar */}
                        <div className="workload-progress-bar">
                          {dev.total_assigned > 0 ? (
                            <>
                              <div
                                style={{
                                  width: `${(dev.open / dev.total_assigned) * 100}%`,
                                  background: '#3b82f6',
                                }}
                                title={`Open: ${dev.open}`}
                              />
                              <div
                                style={{
                                  width: `${(dev.in_progress / dev.total_assigned) * 100}%`,
                                  background: '#8b5cf6',
                                }}
                                title={`In Progress: ${dev.in_progress}`}
                              />
                              <div
                                style={{
                                  width: `${(dev.resolved / dev.total_assigned) * 100}%`,
                                  background: '#10b981',
                                }}
                                title={`Resolved: ${dev.resolved}`}
                              />
                              <div
                                style={{
                                  width: `${(dev.closed / dev.total_assigned) * 100}%`,
                                  background: '#64748b',
                                }}
                                title={`Closed: ${dev.closed}`}
                              />
                            </>
                          ) : (
                            <div style={{ width: '100%', background: '#e2e8f0' }} />
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Resolution Efficiency & Timestamp Telemetry */}
          <div className="analytics-panel">
            <div className="panel-header">
              <div>
                <h3>Resolution Efficiency Telemetry</h3>
                <p>Calculated directly from verified defect creation and resolution timestamps</p>
              </div>
            </div>

            <div className="resolution-panel-body">
              <div className="res-stat-card">
                <div className="res-stat-icon">
                  <i className="bi bi-clock-history" />
                </div>
                <div>
                  <span className="res-stat-label">Average Resolution Time</span>
                  <span className="res-stat-val">
                    {resolutionMetrics?.formatted || 'No data'}
                  </span>
                  <span className="res-stat-sub">
                    Calculated from database lifecycle elapsed timestamps
                  </span>
                </div>
              </div>

              <div className="res-metrics-grid">
                <div className="res-sub-card">
                  <span className="res-sub-label">Sample Size</span>
                  <strong className="res-sub-val">
                    {resolutionMetrics?.sample_size ?? 0} defects
                  </strong>
                  <span className="res-sub-note">Resolved / Closed</span>
                </div>

                <div className="res-sub-card">
                  <span className="res-sub-label">Fastest Resolution</span>
                  <strong className="res-sub-val">
                    {resolutionMetrics?.min_hours !== null &&
                    resolutionMetrics?.min_hours !== undefined
                      ? `${resolutionMetrics.min_hours} hrs`
                      : '—'}
                  </strong>
                  <span className="res-sub-note">Best turn-around</span>
                </div>

                <div className="res-sub-card">
                  <span className="res-sub-label">Slowest Resolution</span>
                  <strong className="res-sub-val">
                    {resolutionMetrics?.max_hours !== null &&
                    resolutionMetrics?.max_hours !== undefined
                      ? `${resolutionMetrics.max_hours} hrs`
                      : '—'}
                  </strong>
                  <span className="res-sub-note">Max turn-around</span>
                </div>
              </div>

              <div className="res-doc-note">
                <i className="bi bi-info-circle-fill" />
                <span>
                  Timestamp fidelity: Measured from <code>created_at</code> to verified{' '}
                  <code>updated_at</code> when transitioned to <em>Resolved</em> or <em>Closed</em>{' '}
                  status.
                </span>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
