import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { getPMStats } from '../../services/dashboardService'
import { getFieldLabel } from '../../utils/activityHelper'
import { isIssueUnassignedOver24Hours, isClientFeatureRequest } from '../../components/IssueTable/IssueTable'

const fmt = (n) => (n || 0).toLocaleString()
const timeAgo = (iso) => {
  const s = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

const PRIORITY_COLORS = { Critical: '#ef4444', High: '#f97316', Medium: '#f59e0b', Low: '#10b981' }
const TYPE_COLORS = { Defect: '#ef4444', Task: '#3b82f6', Feature: '#8b5cf6' }
const TYPE_ICONS = { Defect: 'Bug', Task: 'Task', Feature: 'Feat' }
const HEALTH_CONFIG = {
  green: { label: 'Healthy', color: '#10b981', bg: 'rgba(16,185,129,0.10)' },
  amber: { label: 'At Risk', color: '#f59e0b', bg: 'rgba(245,158,11,0.10)' },
  red:   { label: 'Critical', color: '#ef4444', bg: 'rgba(239,68,68,0.10)' },
}

function KpiCard({ icon, label, value, sub, accent, index }) {
  return (
    <div className="pm-kpi" style={{ animationDelay: `${index * 0.08}s` }}>
      <div className="pm-kpi-icon" style={{ background: accent + '18', color: accent }}>{icon}</div>
      <div className="pm-kpi-body">
        <span className="pm-kpi-value">{value}</span>
        <span className="pm-kpi-label">{label}</span>
        {sub && <span className="pm-kpi-sub">{sub}</span>}
      </div>
    </div>
  )
}

function ProjectCard({ proj }) {
  const health = HEALTH_CONFIG[proj.health] || HEALTH_CONFIG.green
  const total = proj.total_issues || 1
  const openPct  = Math.round((proj.open / total) * 100)
  const inPct    = Math.round((proj.in_progress / total) * 100)
  const resPct   = Math.round((proj.resolved / total) * 100)
  return (
    <div className="pm-proj-card">
      <div className="pm-proj-header">
        <div>
          <div className="pm-proj-name">{proj.name}</div>
          <div className="pm-proj-key">{proj.key}</div>
        </div>
        <span className="pm-health-badge" style={{ background: health.bg, color: health.color }}>
          <span className="pm-health-dot" style={{ background: health.color }} />
          {health.label}
        </span>
      </div>

      <div className="pm-mini-bar" title={`Open: ${proj.open} | In Progress: ${proj.in_progress} | Resolved: ${proj.resolved}`}>
        {proj.open > 0 && <div style={{ width: `${openPct}%`, background: '#ef4444' }} />}
        {proj.in_progress > 0 && <div style={{ width: `${inPct}%`, background: '#f59e0b' }} />}
        {proj.resolved > 0 && <div style={{ width: `${resPct}%`, background: '#10b981' }} />}
      </div>

      <div className="pm-proj-counts">
        <span><span className="pm-count-dot" style={{ background: '#ef4444' }} />{proj.open} Open</span>
        <span><span className="pm-count-dot" style={{ background: '#f59e0b' }} />{proj.in_progress} In Progress</span>
        <span><span className="pm-count-dot" style={{ background: '#10b981' }} />{proj.resolved} Resolved</span>
      </div>

      <div className="pm-proj-footer">
        <span>📋 {proj.total_issues} issues</span>
        <span>🏃 {proj.sprint_count} sprint{proj.sprint_count !== 1 ? 's' : ''}</span>
        <span className={`pm-status-pill ${proj.status?.toLowerCase()}`}>{proj.status}</span>
      </div>
    </div>
  )
}

function PriorityBar({ data }) {
  const order = ['Critical', 'High', 'Medium', 'Low']
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1
  return (
    <div className="pm-section-card">
      <h3 className="pm-section-title">
        <i className="bi bi-stars pm-section-icon"></i>
        Priority Distribution
      </h3>
      <div className="pm-priority-bar-wrap">
        {order.map(p => data[p] ? (
          <div
            key={p}
            className="pm-priority-segment"
            style={{ width: `${(data[p] / total) * 100}%`, background: PRIORITY_COLORS[p] }}
            title={`${p}: ${data[p]}`}
          />
        ) : null)}
      </div>
      <div className="pm-priority-legend">
        {order.map(p => data[p] ? (
          <div key={p} className="pm-legend-item">
            <span className="pm-legend-dot" style={{ background: PRIORITY_COLORS[p] }} />
            <span className="pm-legend-label">{p}</span>
            <span className="pm-legend-count">{data[p]}</span>
            <span className="pm-legend-pct">{Math.round(data[p] / total * 100)}%</span>
          </div>
        ) : null)}
      </div>
    </div>
  )
}

function TypeBreakdown({ data }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1
  const order = ['Defect', 'Task', 'Feature']
  return (
    <div className="pm-section-card">
      <h3 className="pm-section-title">
        <i className="bi bi-stars pm-section-icon"></i>
        Issue Type Breakdown
      </h3>
      <div className="pm-type-grid">
        {order.map(t => {
          const count = data[t] || 0
          const pct = Math.round(count / total * 100)
          const color = TYPE_COLORS[t]
          return (
            <div key={t} className="pm-type-card" style={{ borderColor: color + '30' }}>
              <div className="pm-type-ring" style={{ '--ring-color': color, '--ring-pct': pct }}>
                <svg viewBox="0 0 44 44" className="pm-ring-svg">
                  <circle cx="22" cy="22" r="18" fill="none" stroke={color + '20'} strokeWidth="5" />
                  <circle cx="22" cy="22" r="18" fill="none" stroke={color} strokeWidth="5"
                    strokeDasharray={`${pct * 1.131} 113.1`}
                    strokeLinecap="round"
                    transform="rotate(-90 22 22)"
                  />
                </svg>
                <i className="bi bi-stars pm-ring-icon"></i>
              </div>
              <div className="pm-type-name">{t}s</div>
              <div className="pm-type-count" style={{ color }}>{count}</div>
              <div className="pm-type-pct">{pct}%</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function CriticalWatchlist({ issues }) {
  const [expanded, setExpanded] = useState(false)
  const shown = expanded ? issues : issues.slice(0, 6)
  return (
    <div className="pm-section-card pm-watchlist">
      <h3 className="pm-section-title">
        <i className="bi bi-stars pm-section-icon"></i>
        Critical Issues Watchlist
        <span className="pm-badge-red">{issues.length}</span>
      </h3>
      {issues.length === 0 ? (
        <div className="pm-empty">✅ No critical or high-priority open issues</div>
      ) : (
        <>
          <div className="pm-watchlist-table">
            <div className="pm-watchlist-head">
              <span>Key</span><span>Title</span><span>Project</span><span>Priority</span><span>Age</span>
            </div>
            {shown.map(i => {
              const isOverdue = isIssueUnassignedOver24Hours(i)
              const isFeature = isClientFeatureRequest(i)
              return (
                <div
                  key={i.id}
                  className={`pm-watchlist-row ${isOverdue ? 'pm-watchlist-row-overdue' : ''}`}
                  style={isOverdue ? { backgroundColor: 'rgba(254, 242, 242, 0.75)', borderLeft: '3px solid #ef4444' } : {}}
                >
                  <span className="pm-issue-key">{i.issue_key}</span>
                  <span className="pm-issue-title" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    {i.title}
                    {isFeature && (
                      <span
                        style={{
                          fontSize: '0.68rem',
                          fontWeight: 600,
                          padding: '1px 6px',
                          borderRadius: '9999px',
                          background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                          color: '#ffffff',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '3px'
                        }}
                      >
                        <i className="bi bi-stars" style={{ fontSize: '0.65rem' }} /> Client Feature
                      </span>
                    )}
                    {isOverdue && (
                      <span className="badge bg-danger text-white" style={{ fontSize: '0.65rem', fontWeight: 700, padding: '1px 5px' }}>
                        &gt;24h Unassigned
                      </span>
                    )}
                  </span>
                  <span className="pm-issue-proj">{i.project_name}</span>
                  <span className="pm-priority-tag" style={{ color: PRIORITY_COLORS[i.priority_name], background: (PRIORITY_COLORS[i.priority_name] || '#94a3b8') + '18' }}>{i.priority_name}</span>
                  <span className="pm-issue-age">{timeAgo(i.created_at)}</span>
                  <span className="pm-issue-action"><Link to="/issues" state={{ editIssue: i }} className="btn btn-sm btn-outline-primary" style={{ padding: '2px 8px', fontSize: '0.7rem', fontWeight: 'bold' }}>Assign</Link></span>
                </div>
              )
            })}
          </div>
          {issues.length > 6 && (
            <button className="pm-expand-btn" onClick={() => setExpanded(e => !e)}>
              {expanded ? '▲ Show less' : `▼ Show ${issues.length - 6} more`}
            </button>
          )}
        </>
      )}
    </div>
  )
}

function ActivityFeed({ items }) {
  return (
    <div className="pm-section-card">
      <h3 className="pm-section-title">
        <i className="bi bi-stars pm-section-icon"></i>
        Recent Activity
      </h3>
      {items.length === 0 ? (
        <div className="pm-empty">No recent activity recorded.</div>
      ) : (
        <div className="pm-activity-list">
          {items.map(h => (
            <div key={h.id} className="pm-activity-item">
              <div className="pm-activity-dot" />
              <div className="pm-activity-body">
                <strong>{h.user_name || 'User'}</strong> changed <span className="pm-activity-field">{getFieldLabel(h.field_name)}</span>
                {h.old_value && h.old_value !== 'None' && <> from <em>{h.old_value}</em></>}
                {h.new_value && h.new_value !== 'None' && <> to <strong>{h.new_value}</strong></>}
                <span className="pm-activity-time">{timeAgo(h.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ProjectManagerDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getPMStats()
      .then(({ data }) => setStats(data))
      .catch(() => setError('Unable to load Project Manager dashboard.'))
  }, [])

  if (error) return <div className="alert alert-danger m-4">{error}</div>
  if (!stats)  return <p className="page-status">Loading Project Manager dashboard…</p>

  const kpis = [
    { icon: '🗂️', label: 'Active Projects',      value: fmt(stats.active_projects),          sub: 'across all teams',       accent: '#3b82f6' },
    { icon: '🚨', label: 'Critical Open Issues',  value: fmt(stats.critical_open_issues),     sub: 'High + Critical priority', accent: '#ef4444' },
    { icon: '🏃', label: 'Active Sprints',         value: fmt(stats.active_sprints),           sub: 'currently running',      accent: '#10b981' },
    { icon: '✅', label: 'Sprint Completion',      value: `${stats.sprint_completion_rate}%`,  sub: 'resolved / planned',     accent: '#8b5cf6' },
  ]

  return (
    <>
      <style>{`
        .pm-dash { display: flex; flex-direction: column; gap: 28px; }

        .pm-banner {
          background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #1e1b4b 100%);
          border-radius: 20px; padding: 28px 32px;
          display: flex; align-items: center; justify-content: space-between; gap: 20px;
          position: relative; overflow: hidden;
        }
        .pm-banner::before {
          content: ''; position: absolute; inset: 0;
          background: radial-gradient(circle at 80% 50%, rgba(99,102,241,0.25) 0%, transparent 60%);
        }
        .pm-banner-text { position: relative; z-index: 1; }
        .pm-banner-eyebrow { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; color: #818cf8; margin-bottom: 6px; }
        .pm-banner-title { font-size: 1.55rem; font-weight: 800; color: #fff; margin: 0 0 6px; }
        .pm-banner-sub { font-size: 0.875rem; color: #94a3b8; margin: 0; }
        .pm-banner-badge {
          position: relative; z-index: 1; flex-shrink: 0;
          padding: 10px 20px; border-radius: 12px;
          background: rgba(99,102,241,0.20); border: 1px solid rgba(99,102,241,0.30);
          text-align: center;
        }
        .pm-banner-badge-val { font-size: 1.8rem; font-weight: 800; color: #a5b4fc; display: block; }
        .pm-banner-badge-label { font-size: 0.7rem; color: #818cf8; font-weight: 600; }

        .pm-kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
        .pm-kpi {
          background: #fff; border: 1px solid rgba(15,23,42,0.07);
          border-radius: 16px; padding: 18px 20px;
          display: flex; align-items: center; gap: 14px;
          animation: fadeSlideUp .5s ease both;
          transition: box-shadow .2s, transform .2s;
        }
        .pm-kpi:hover { box-shadow: 0 6px 24px rgba(15,23,42,0.10); transform: translateY(-2px); }
        .pm-kpi-icon {
          width: 46px; height: 46px; border-radius: 12px; font-size: 1.3rem;
          display: grid; place-items: center; flex-shrink: 0;
        }
        .pm-kpi-body { display: flex; flex-direction: column; min-width: 0; }
        .pm-kpi-value { font-size: 1.6rem; font-weight: 800; color: #0f172a; line-height: 1; }
        .pm-kpi-label { font-size: 0.8rem; font-weight: 600; color: #64748b; margin-top: 3px; }
        .pm-kpi-sub { font-size: 0.7rem; color: #94a3b8; margin-top: 2px; }

        .pm-section-card {
          background: #fff; border: 1px solid rgba(15,23,42,0.07);
          border-radius: 20px; padding: 22px 24px;
          box-shadow: 0 2px 8px rgba(15,23,42,0.04);
        }
        .pm-section-title {
          font-size: 0.9rem; font-weight: 800; color: #0f172a;
          margin: 0 0 18px; display: flex; align-items: center; gap: 8px;
        }
        .pm-section-icon { font-size: 1rem; }
        .pm-badge-red {
          margin-left: auto; padding: 2px 10px; border-radius: 99px;
          background: rgba(239,68,68,0.10); color: #dc2626;
          font-size: 0.72rem; font-weight: 700;
        }

        .pm-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .pm-grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }

        .pm-proj-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
        .pm-proj-card {
          background: #fff; border: 1px solid rgba(15,23,42,0.07);
          border-radius: 16px; padding: 16px 18px;
          display: flex; flex-direction: column; gap: 10px;
          transition: box-shadow .2s, transform .2s;
        }
        .pm-proj-card:hover { box-shadow: 0 8px 28px rgba(15,23,42,0.09); transform: translateY(-2px); }
        .pm-proj-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
        .pm-proj-name { font-weight: 700; font-size: 0.92rem; color: #0f172a; }
        .pm-proj-key { font-size: 0.7rem; font-weight: 700; color: #94a3b8; font-family: monospace; margin-top: 2px; }
        .pm-health-badge {
          display: inline-flex; align-items: center; gap: 5px;
          padding: 3px 9px; border-radius: 99px; font-size: 0.7rem; font-weight: 700;
          white-space: nowrap; flex-shrink: 0;
        }
        .pm-health-dot { width: 6px; height: 6px; border-radius: 50%; }

        .pm-mini-bar {
          height: 8px; border-radius: 4px; overflow: hidden;
          display: flex; background: rgba(15,23,42,0.06);
        }
        .pm-mini-bar > div { height: 100%; transition: width .4s ease; }

        .pm-proj-counts { display: flex; gap: 12px; font-size: 0.72rem; color: #64748b; flex-wrap: wrap; }
        .pm-count-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 4px; }
        .pm-proj-footer { display: flex; align-items: center; gap: 10px; font-size: 0.72rem; color: #94a3b8; border-top: 1px solid rgba(15,23,42,0.06); padding-top: 8px; flex-wrap: wrap; }
        .pm-status-pill { padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 0.67rem; background: rgba(16,185,129,0.10); color: #059669; }
        .pm-status-pill.inactive { background: rgba(100,116,139,0.10); color: #475569; }

        .pm-priority-bar-wrap {
          height: 14px; border-radius: 7px; overflow: hidden; display: flex;
          margin-bottom: 14px; gap: 2px;
        }
        .pm-priority-segment { height: 100%; transition: width .4s ease; border-radius: 4px; }
        .pm-priority-legend { display: flex; gap: 16px; flex-wrap: wrap; }
        .pm-legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.78rem; }
        .pm-legend-dot { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
        .pm-legend-label { color: #475569; font-weight: 600; }
        .pm-legend-count { color: #0f172a; font-weight: 800; }
        .pm-legend-pct { color: #94a3b8; font-size: 0.7rem; }

        .pm-type-grid { display: flex; gap: 16px; justify-content: space-around; }
        .pm-type-card {
          flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px;
          padding: 16px 12px; border-radius: 14px; border: 1.5px solid;
          background: #fafbfc; transition: box-shadow .2s;
        }
        .pm-type-card:hover { box-shadow: 0 4px 16px rgba(15,23,42,0.08); }
        .pm-type-ring { position: relative; width: 64px; height: 64px; }
        .pm-ring-svg { width: 100%; height: 100%; }
        .pm-ring-icon { position: absolute; inset: 0; display: grid; place-items: center; font-size: 1.3rem; }
        .pm-type-name { font-size: 0.78rem; font-weight: 700; color: #64748b; }
        .pm-type-count { font-size: 1.4rem; font-weight: 800; line-height: 1; }
        .pm-type-pct { font-size: 0.7rem; color: #94a3b8; }

        .pm-watchlist-table { display: flex; flex-direction: column; gap: 0; }
        .pm-watchlist-head {
          display: grid; grid-template-columns: 90px 1fr 120px 90px 70px;
          gap: 10px; padding: 8px 12px;
          font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
          color: #94a3b8; border-bottom: 1px solid rgba(15,23,42,0.07);
        }
        .pm-watchlist-row {
          display: grid; grid-template-columns: 90px 1fr 120px 90px 70px;
          gap: 10px; padding: 10px 12px; border-radius: 8px;
          font-size: 0.82rem; align-items: center;
          transition: background .15s;
        }
        .pm-watchlist-row:hover { background: #f8fafc; }
        .pm-issue-key { font-family: monospace; font-weight: 700; color: #3b82f6; font-size: 0.75rem; }
        .pm-issue-title { color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .pm-issue-proj { color: #64748b; font-size: 0.75rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .pm-priority-tag { padding: 2px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; display: inline-block; }
        .pm-issue-age { color: #94a3b8; font-size: 0.72rem; white-space: nowrap; }
        .pm-expand-btn {
          margin-top: 10px; width: 100%; padding: 8px;
          border: 1px dashed rgba(15,23,42,0.12); border-radius: 8px;
          background: none; cursor: pointer; font-size: 0.78rem; color: #64748b;
          transition: background .2s;
        }
        .pm-expand-btn:hover { background: #f1f5f9; }

        .pm-activity-list { display: flex; flex-direction: column; gap: 10px; }
        .pm-activity-item { display: flex; align-items: flex-start; gap: 12px; }
        .pm-activity-dot { width: 8px; height: 8px; border-radius: 50%; background: #6366f1; flex-shrink: 0; margin-top: 6px; }
        .pm-activity-body { font-size: 0.82rem; color: #475569; line-height: 1.5; }
        .pm-activity-body em { color: #ef4444; font-style: normal; font-weight: 600; }
        .pm-activity-body strong { color: #10b981; font-weight: 700; }
        .pm-activity-field { font-weight: 700; color: #0f172a; }
        .pm-activity-time { margin-left: 8px; font-size: 0.7rem; color: #94a3b8; }

        .pm-empty { text-align: center; padding: 24px; color: #94a3b8; font-size: 0.875rem; }

        @media (max-width: 900px) {
          .pm-kpi-row { grid-template-columns: repeat(2, 1fr); }
          .pm-grid-2 { grid-template-columns: 1fr; }
          .pm-watchlist-head, .pm-watchlist-row { grid-template-columns: 80px 1fr 80px; }
          .pm-watchlist-head span:nth-child(3), .pm-watchlist-row span:nth-child(3),
          .pm-watchlist-head span:nth-child(5), .pm-watchlist-row span:nth-child(5) { display: none; }
          .pm-banner { flex-direction: column; align-items: flex-start; }
        }
        @media (max-width: 600px) {
          .pm-kpi-row { grid-template-columns: 1fr; }
          .pm-type-grid { flex-direction: column; }
        }
      `}</style>

      <div className="pm-dash">
        <div className="pm-banner">
          <div className="pm-banner-text">
            <h2 className="pm-banner-title">Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening'}, {user?.full_name?.split(' ')[0]} 👋</h2>
            <p className="pm-banner-sub">Here's your portfolio health across all projects and sprints.</p>
          </div>
          <div className="pm-banner-badge">
            <span className="pm-banner-badge-val">{fmt(stats.total_issues)}</span>
            <span className="pm-banner-badge-label">Total Issues</span>
          </div>
        </div>

        <div className="pm-kpi-row">
          {kpis.map((k, i) => <KpiCard key={k.label} {...k} index={i} />)}
        </div>

        <div className="pm-section-card">
          <h3 className="pm-section-title">
            <i className="bi bi-stars pm-section-icon"></i>
            Project Health Overview
            <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: '#94a3b8', fontWeight: 400 }}>
              🟢 Healthy ≥60% resolved &nbsp; 🟡 At Risk ≥30% &nbsp; 🔴 Critical &lt;30%
            </span>
          </h3>
          {stats.projects_with_metrics.length === 0 ? (
            <div className="pm-empty">No projects found. Create a project to get started.</div>
          ) : (
            <div className="pm-proj-grid">
              {stats.projects_with_metrics.map(p => <ProjectCard key={p.id} proj={p} />)}
            </div>
          )}
        </div>

        <div className="pm-grid-2">
          <PriorityBar data={stats.issues_by_priority} />
          <TypeBreakdown data={stats.issues_by_type} />
        </div>

        <div className="pm-grid-2">
          <CriticalWatchlist issues={stats.critical_issues} />
          <ActivityFeed items={stats.recent_history} />
        </div>
      </div>
    </>
  )
}