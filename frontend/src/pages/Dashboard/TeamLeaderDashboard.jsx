import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { getTLStats } from '../../services/dashboardService'

const fmt = (n) => (n || 0).toLocaleString()
const timeAgo = (iso) => {
  const s = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}
const initials = (name) => name?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() || '?'
const avatarColor = (name) => {
  const colors = ['#6366f1','#3b82f6','#10b981','#f59e0b','#8b5cf6','#ef4444','#14b8a6','#f97316']
  let hash = 0; for (const c of (name || '')) hash = c.charCodeAt(0) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

const STATUS_COLORS = { Open: '#ef4444', 'In Progress': '#f59e0b', Resolved: '#10b981', Closed: '#64748b' }
const TYPE_COLORS = { Defect: '#ef4444', Task: '#3b82f6', Feature: '#8b5cf6' }
const TYPE_ICONS = { Defect: 'Bug', Task: 'Task', Feature: 'Feat' }

function KpiCard({ icon, label, value, sub, accent, index }) {
  return (
    <div className="tl-kpi" style={{ animationDelay: `${index * 0.08}s` }}>
      <div className="tl-kpi-icon" style={{ background: accent + '18', color: accent }}>{icon}</div>
      <div className="tl-kpi-body">
        <span className="tl-kpi-value">{value}</span>
        <span className="tl-kpi-label">{label}</span>
        {sub && <span className="tl-kpi-sub">{sub}</span>}
      </div>
    </div>
  )
}

function WorkloadRow({ member, maxTotal }) {
  const { open, in_progress, resolved, total, full_name } = member
  const openPct   = total ? Math.round(open / total * 100) : 0
  const inPct     = total ? Math.round(in_progress / total * 100) : 0
  const resPct    = total ? Math.round(resolved / total * 100) : 0
  const barWidth  = maxTotal ? (total / maxTotal) * 100 : 0

  const load = total >= 8 ? 'overloaded' : total >= 4 ? 'balanced' : 'available'
  const loadConfig = {
    overloaded: { label: 'Overloaded', color: '#ef4444', bg: 'rgba(239,68,68,0.10)' },
    balanced:   { label: 'Balanced',   color: '#f59e0b', bg: 'rgba(245,158,11,0.10)' },
    available:  { label: 'Available',  color: '#10b981', bg: 'rgba(16,185,129,0.10)' },
  }[load]

  const color = avatarColor(full_name)
  return (
    <div className="tl-member-row">
      <div className="tl-member-avatar" style={{ background: color + '22', color }}>
        {initials(full_name)}
      </div>
      <div className="tl-member-info">
        <div className="tl-member-name">{full_name}</div>
        <div className="tl-member-counts">
          <span style={{ color: '#ef4444' }}>{open} open</span>
          <span style={{ color: '#f59e0b' }}>{in_progress} in progress</span>
          <span style={{ color: '#10b981' }}>{resolved} resolved</span>
        </div>
      </div>
      <div className="tl-member-bar-wrap">
        <div className="tl-member-bar" style={{ width: `${barWidth}%` }}>
          <div style={{ width: `${openPct}%`, background: '#ef4444' }} />
          <div style={{ width: `${inPct}%`, background: '#f59e0b' }} />
          <div style={{ width: `${resPct}%`, background: '#10b981' }} />
        </div>
      </div>
      <div className="tl-member-total">{total}</div>
      <span className="tl-load-badge" style={{ background: loadConfig.bg, color: loadConfig.color }}>
        {loadConfig.label}
      </span>
    </div>
  )
}

function SprintCard({ sprint }) {
  const pct = sprint.progress_pct
  const days = sprint.days_left
  const barColor = pct >= 70 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#ef4444'
  return (
    <div className="tl-sprint-card">
      <div className="tl-sprint-header">
        <div>
          <div className="tl-sprint-name">{sprint.name}</div>
          <div className="tl-sprint-dates">
            {sprint.start_date} → {sprint.end_date || '—'}
          </div>
        </div>
        {days !== null && (
          <span className={`tl-days-badge ${days < 0 ? 'overdue' : days <= 3 ? 'urgent' : ''}`}>
            {days < 0 ? `${Math.abs(days)}d overdue` : `${days}d left`}
          </span>
        )}
      </div>
      <div className="tl-sprint-progress-wrap">
        <div className="tl-sprint-track">
          <div className="tl-sprint-fill" style={{ width: `${pct}%`, background: barColor }} />
        </div>
        <span className="tl-sprint-pct" style={{ color: barColor }}>{pct}%</span>
      </div>
      <div className="tl-sprint-meta">
        <span>✅ {sprint.resolved_issues} resolved</span>
        <span>📋 {sprint.total_issues} total</span>
      </div>
    </div>
  )
}

function StatusDistribution({ data }) {
  const order = ['Open', 'In Progress', 'Resolved', 'Closed']
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1
  return (
    <div className="tl-section-card">
      <h3 className="tl-section-title">
        <i className="bi bi-stars tl-section-icon"></i>
        Issues by Status
      </h3>
      <div className="tl-status-list">
        {order.map(s => {
          const count = data[s] || 0
          const pct = Math.round(count / total * 100)
          return (
            <div key={s} className="tl-status-row">
              <div className="tl-status-label">
                <span className="tl-status-dot" style={{ background: STATUS_COLORS[s] || '#94a3b8' }} />
                {s}
              </div>
              <div className="tl-status-bar-wrap">
                <div className="tl-status-bar" style={{ width: `${pct}%`, background: STATUS_COLORS[s] || '#94a3b8' }} />
              </div>
              <div className="tl-status-count">{count}</div>
              <div className="tl-status-pct">{pct}%</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function TypeDistribution({ data }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1
  const order = ['Defect', 'Task', 'Feature']
  return (
    <div className="tl-section-card">
      <h3 className="tl-section-title">
        <i className="bi bi-stars tl-section-icon"></i>
        Issue Type Mix
      </h3>
      <div className="tl-type-bar">
        {order.map(t => (
          <div key={t}
            className="tl-type-segment"
            style={{ width: `${(data[t] || 0) / total * 100}%`, background: TYPE_COLORS[t] }}
            title={`${t}: ${data[t] || 0}`}
          />
        ))}
      </div>
      <div className="tl-type-pills">
        {order.map(t => {
          const count = data[t] || 0
          const pct = Math.round(count / total * 100)
          return (
            <div key={t} className="tl-type-pill" style={{ borderColor: TYPE_COLORS[t] + '30', background: TYPE_COLORS[t] + '0a' }}>
              <span><i className='bi bi-record-circle'></i></span>
              <div>
                <div className="tl-type-pill-name">{t}s</div>
                <div className="tl-type-pill-count" style={{ color: TYPE_COLORS[t] }}>{count} <span className="tl-type-pill-pct">({pct}%)</span></div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function RecentFeed({ issues }) {
  const STATUS_BG = { Open: 'rgba(239,68,68,0.10)', 'In Progress': 'rgba(245,158,11,0.10)', Resolved: 'rgba(16,185,129,0.10)', Closed: 'rgba(100,116,139,0.10)' }
  return (
    <div className="tl-section-card">
      <h3 className="tl-section-title">
        <i className="bi bi-stars tl-section-icon"></i>
        Recent Team Activity
      </h3>
      {issues.length === 0 ? (
        <div className="tl-empty">No recent issues.</div>
      ) : (
        <div className="tl-feed-list">
          {issues.map(i => (
            <div key={i.id} className="tl-feed-item">
              <span className="tl-feed-type">{TYPE_ICONS[i.issue_type] || '📋'}</span>
              <div className="tl-feed-body">
                <div className="tl-feed-title">
                  <span className="tl-feed-key">{i.issue_key}</span>
                  {i.title}
                </div>
                <div className="tl-feed-meta">
                  <span>{i.project_name}</span>
                  {i.reporter_name && <span>by {i.reporter_name}</span>}
                  <span className="tl-feed-time">{timeAgo(i.updated_at)}</span>
                </div>
              </div>
              <span className="tl-status-tag" style={{ color: STATUS_COLORS[i.status_name], background: STATUS_BG[i.status_name] || 'rgba(15,23,42,0.06)' }}>
                {i.status_name}
              </span>
              <span className="pm-issue-action" style={{ marginLeft: '12px' }}>
                <Link to="/issues" state={{ editIssue: i }} className="btn btn-sm btn-outline-primary" style={{ padding: '2px 8px', fontSize: '0.7rem', fontWeight: 'bold' }}>Assign</Link>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function TeamLeaderDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getTLStats()
      .then(({ data }) => setStats(data))
      .catch(() => setError('Unable to load Team Leader dashboard.'))
  }, [])

  if (error) return <div className="alert alert-danger m-4">{error}</div>
  if (!stats)  return <p className="page-status">Loading Team Leader dashboard…</p>

  const maxTotal = Math.max(...(stats.team_workload.map(m => m.total)), 1)

  const kpis = [
    { icon: '👥', label: 'Team Members',     value: fmt(stats.team_size),           sub: 'with active issues',      accent: '#6366f1' },
    { icon: '⚡', label: 'In Progress',       value: fmt(stats.in_progress_issues),  sub: 'currently being worked',  accent: '#f59e0b' },
    { icon: '🐛', label: 'Open Issues',       value: fmt(stats.open_issues),         sub: 'awaiting assignment',     accent: '#ef4444' },
    { icon: '✅', label: 'Resolved',          value: fmt(stats.resolved_issues),     sub: 'completed successfully',  accent: '#10b981' },
  ]

  return (
    <>
      <style>{`
        .tl-dash { display: flex; flex-direction: column; gap: 24px; }

        .tl-banner {
          background: linear-gradient(135deg, #064e3b 0%, #065f46 50%, #1e3a5f 100%);
          border-radius: 20px; padding: 28px 32px;
          display: flex; align-items: center; justify-content: space-between; gap: 20px;
          position: relative; overflow: hidden;
        }
        .tl-banner::before {
          content: ''; position: absolute; inset: 0;
          background: radial-gradient(circle at 80% 50%, rgba(16,185,129,0.20) 0%, transparent 60%);
        }
        .tl-banner-text { position: relative; z-index: 1; }
        .tl-banner-eyebrow { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; color: #6ee7b7; margin-bottom: 6px; }
        .tl-banner-title { font-size: 1.55rem; font-weight: 800; color: #fff; margin: 0 0 6px; }
        .tl-banner-sub { font-size: 0.875rem; color: #a7f3d0; margin: 0; }
        .tl-banner-stats {
          position: relative; z-index: 1; display: flex; gap: 20px; flex-shrink: 0;
        }
        .tl-banner-stat {
          padding: 10px 18px; border-radius: 12px; text-align: center;
          background: rgba(16,185,129,0.20); border: 1px solid rgba(16,185,129,0.30);
        }
        .tl-banner-stat-val { font-size: 1.6rem; font-weight: 800; color: #6ee7b7; display: block; line-height: 1; }
        .tl-banner-stat-label { font-size: 0.68rem; color: #a7f3d0; font-weight: 600; margin-top: 4px; display: block; }

        .tl-kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
        .tl-kpi {
          background: #fff; border: 1px solid rgba(15,23,42,0.07);
          border-radius: 16px; padding: 18px 20px;
          display: flex; align-items: center; gap: 14px;
          animation: fadeSlideUp .5s ease both;
          transition: box-shadow .2s, transform .2s;
        }
        .tl-kpi:hover { box-shadow: 0 6px 24px rgba(15,23,42,0.10); transform: translateY(-2px); }
        .tl-kpi-icon { width: 46px; height: 46px; border-radius: 12px; font-size: 1.3rem; display: grid; place-items: center; flex-shrink: 0; }
        .tl-kpi-body { display: flex; flex-direction: column; min-width: 0; }
        .tl-kpi-value { font-size: 1.6rem; font-weight: 800; color: #0f172a; line-height: 1; }
        .tl-kpi-label { font-size: 0.8rem; font-weight: 600; color: #64748b; margin-top: 3px; }
        .tl-kpi-sub { font-size: 0.7rem; color: #94a3b8; margin-top: 2px; }

        .tl-section-card {
          background: #fff; border: 1px solid rgba(15,23,42,0.07);
          border-radius: 20px; padding: 22px 24px;
          box-shadow: 0 2px 8px rgba(15,23,42,0.04);
        }
        .tl-section-title { font-size: 0.9rem; font-weight: 800; color: #0f172a; margin: 0 0 18px; display: flex; align-items: center; gap: 8px; }
        .tl-section-icon { font-size: 1rem; }

        .tl-workload-list { display: flex; flex-direction: column; gap: 10px; }
        .tl-member-row {
          display: grid; grid-template-columns: 40px 200px 1fr 40px 100px;
          align-items: center; gap: 12px;
          padding: 10px 12px; border-radius: 10px;
          transition: background .15s;
        }
        .tl-member-row:hover { background: #f8fafc; }
        .tl-member-avatar {
          width: 36px; height: 36px; border-radius: 10px;
          font-size: 0.72rem; font-weight: 800; display: grid; place-items: center;
          flex-shrink: 0;
        }
        .tl-member-info { min-width: 0; }
        .tl-member-name { font-weight: 700; font-size: 0.875rem; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .tl-member-counts { display: flex; gap: 10px; font-size: 0.7rem; font-weight: 600; margin-top: 2px; }
        .tl-member-bar-wrap { height: 10px; background: rgba(15,23,42,0.06); border-radius: 5px; overflow: hidden; }
        .tl-member-bar { height: 100%; display: flex; border-radius: 5px; overflow: hidden; transition: width .4s ease; }
        .tl-member-bar > div { height: 100%; }
        .tl-member-total { font-weight: 800; font-size: 0.9rem; color: #0f172a; text-align: right; }
        .tl-load-badge { padding: 3px 10px; border-radius: 99px; font-size: 0.7rem; font-weight: 700; text-align: center; white-space: nowrap; }

        .tl-sprint-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
        .tl-sprint-card {
          border: 1px solid rgba(15,23,42,0.08); border-radius: 14px;
          padding: 14px 16px; display: flex; flex-direction: column; gap: 10px;
          transition: box-shadow .2s;
        }
        .tl-sprint-card:hover { box-shadow: 0 4px 16px rgba(15,23,42,0.08); }
        .tl-sprint-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
        .tl-sprint-name { font-weight: 700; font-size: 0.875rem; color: #0f172a; }
        .tl-sprint-dates { font-size: 0.7rem; color: #94a3b8; margin-top: 2px; }
        .tl-days-badge {
          padding: 3px 9px; border-radius: 8px; font-size: 0.7rem; font-weight: 700;
          background: rgba(16,185,129,0.10); color: #059669; white-space: nowrap; flex-shrink: 0;
        }
        .tl-days-badge.urgent { background: rgba(245,158,11,0.10); color: #d97706; }
        .tl-days-badge.overdue { background: rgba(239,68,68,0.10); color: #dc2626; }
        .tl-sprint-progress-wrap { display: flex; align-items: center; gap: 10px; }
        .tl-sprint-track { flex: 1; height: 8px; border-radius: 4px; background: rgba(15,23,42,0.06); overflow: hidden; }
        .tl-sprint-fill { height: 100%; border-radius: 4px; transition: width .5s ease; }
        .tl-sprint-pct { font-weight: 800; font-size: 0.85rem; flex-shrink: 0; min-width: 36px; text-align: right; }
        .tl-sprint-meta { display: flex; gap: 12px; font-size: 0.72rem; color: #94a3b8; }

        .tl-status-list { display: flex; flex-direction: column; gap: 10px; }
        .tl-status-row { display: grid; grid-template-columns: 100px 1fr 40px 40px; align-items: center; gap: 10px; }
        .tl-status-label { display: flex; align-items: center; gap: 6px; font-size: 0.8rem; font-weight: 600; color: #475569; }
        .tl-status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
        .tl-status-bar-wrap { height: 8px; background: rgba(15,23,42,0.06); border-radius: 4px; overflow: hidden; }
        .tl-status-bar { height: 100%; border-radius: 4px; transition: width .4s ease; }
        .tl-status-count { font-weight: 800; font-size: 0.82rem; color: #0f172a; text-align: right; }
        .tl-status-pct { font-size: 0.72rem; color: #94a3b8; text-align: right; }

        .tl-type-bar {
          height: 12px; border-radius: 6px; overflow: hidden; display: flex; gap: 2px;
          margin-bottom: 14px;
        }
        .tl-type-segment { height: 100%; border-radius: 4px; transition: width .4s ease; }
        .tl-type-pills { display: flex; gap: 12px; }
        .tl-type-pill {
          flex: 1; display: flex; align-items: center; gap: 10px;
          padding: 12px 14px; border-radius: 12px; border: 1.5px solid;
          transition: box-shadow .2s;
        }
        .tl-type-pill:hover { box-shadow: 0 4px 14px rgba(15,23,42,0.08); }
        .tl-type-pill > span { font-size: 1.3rem; flex-shrink: 0; }
        .tl-type-pill-name { font-size: 0.72rem; font-weight: 700; color: #64748b; }
        .tl-type-pill-count { font-size: 1rem; font-weight: 800; color: #0f172a; }
        .tl-type-pill-pct { font-size: 0.7rem; color: #94a3b8; font-weight: 400; }

        .tl-feed-list { display: flex; flex-direction: column; gap: 6px; }
        .tl-feed-item {
          display: flex; align-items: center; gap: 10px; padding: 9px 10px;
          border-radius: 10px; transition: background .15s;
        }
        .tl-feed-item:hover { background: #f8fafc; }
        .tl-feed-type { font-size: 1rem; flex-shrink: 0; }
        .tl-feed-body { flex: 1; min-width: 0; }
        .tl-feed-title { font-size: 0.82rem; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .tl-feed-key { font-family: monospace; font-weight: 700; color: #3b82f6; font-size: 0.75rem; margin-right: 6px; }
        .tl-feed-meta { display: flex; gap: 10px; font-size: 0.7rem; color: #94a3b8; margin-top: 2px; }
        .tl-feed-time { margin-left: auto; }
        .tl-status-tag { padding: 3px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; white-space: nowrap; flex-shrink: 0; }

        .tl-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .tl-empty { text-align: center; padding: 24px; color: #94a3b8; font-size: 0.875rem; }

        .tl-workload-header {
          display: grid; grid-template-columns: 40px 200px 1fr 40px 100px;
          gap: 12px; padding: 0 12px 8px;
          font-size: 0.67rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
          color: #94a3b8; border-bottom: 1px solid rgba(15,23,42,0.07); margin-bottom: 4px;
        }

        @media (max-width: 1024px) {
          .tl-member-row, .tl-workload-header { grid-template-columns: 40px 1fr 1fr 40px; }
          .tl-member-row > :nth-child(5), .tl-workload-header > :nth-child(5) { display: none; }
        }
        @media (max-width: 900px) {
          .tl-kpi-row { grid-template-columns: repeat(2, 1fr); }
          .tl-grid-2 { grid-template-columns: 1fr; }
          .tl-banner { flex-direction: column; align-items: flex-start; }
          .tl-type-pills { flex-direction: column; }
          .tl-member-row, .tl-workload-header { grid-template-columns: 40px 1fr 40px; }
          .tl-member-row > :nth-child(3), .tl-workload-header > :nth-child(3) { display: none; }
        }
        @media (max-width: 600px) {
          .tl-kpi-row { grid-template-columns: 1fr; }
        }
      `}</style>

      <div className="tl-dash">
        <div className="tl-banner">
          <div className="tl-banner-text">
            <h2 className="tl-banner-title">Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening'}, {user?.full_name?.split(' ')[0]} 👋</h2>
            <p className="tl-banner-sub">Your team's workload, sprint progress, and issue distribution at a glance.</p>
          </div>
          <div className="tl-banner-stats">
            <div className="tl-banner-stat">
              <span className="tl-banner-stat-val">{fmt(stats.total_issues)}</span>
              <span className="tl-banner-stat-label">Total Issues</span>
            </div>
            <div className="tl-banner-stat">
              <span className="tl-banner-stat-val">{stats.active_sprints.length}</span>
              <span className="tl-banner-stat-label">Active Sprints</span>
            </div>
          </div>
        </div>

        <div className="tl-kpi-row">
          {kpis.map((k, i) => <KpiCard key={k.label} {...k} index={i} />)}
        </div>

        <div className="tl-section-card">
          <h3 className="tl-section-title">
            <i className="bi bi-stars tl-section-icon"></i>
            Team Workload Distribution
            <span style={{ marginLeft: 'auto', display: 'flex', gap: '12px', fontSize: '0.7rem', fontWeight: 400, color: '#94a3b8' }}>
              <span><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: '#ef4444', marginRight: 4 }}/>Open</span>
              <span><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: '#f59e0b', marginRight: 4 }}/>In Progress</span>
              <span><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: '#10b981', marginRight: 4 }}/>Resolved</span>
            </span>
          </h3>
          {stats.team_workload.length === 0 ? (
            <div className="tl-empty">No issues have been assigned to team members yet.</div>
          ) : (
            <div className="tl-workload-list">
              <div className="tl-workload-header">
                <span />
                <span>Member</span>
                <span>Workload</span>
                <span style={{ textAlign: 'right' }}>Total</span>
                <span>Status</span>
              </div>
              {stats.team_workload.map(m => (
                <WorkloadRow key={m.user_id} member={m} maxTotal={maxTotal} />
              ))}
            </div>
          )}
        </div>

        <div className="tl-section-card">
          <h3 className="tl-section-title">
            <i className="bi bi-stars tl-section-icon"></i>
            Active Sprint Progress
          </h3>
          {stats.active_sprints.length === 0 ? (
            <div className="tl-empty">No active sprints. Go to Sprint Planning to activate one.</div>
          ) : (
            <div className="tl-sprint-grid">
              {stats.active_sprints.map(s => <SprintCard key={s.id} sprint={s} />)}
            </div>
          )}
        </div>

        <div className="tl-grid-2">
          <StatusDistribution data={stats.issues_by_status} />
          <TypeDistribution data={stats.issues_by_type} />
        </div>

        <RecentFeed issues={stats.recent_issues} />
      </div>
    </>
  )
}