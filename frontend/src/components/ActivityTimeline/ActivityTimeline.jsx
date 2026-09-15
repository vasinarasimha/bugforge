import { isIssueUnassignedOver24Hours, isClientFeatureRequest, formatDateTime } from '../IssueTable/IssueTable'

export default function ActivityTimeline({ issues = [] }) {
  return (
    <section className="panel-card activity-panel">
      <div className="panel-heading">
        <div>
          <h2>Recent Activity</h2>
          <p>Latest issues from your workspace</p>
        </div>
      </div>
      <div className="activity-timeline">
        {issues.length ? (
          issues.map((issue) => {
            const isOverdueUnassigned = isIssueUnassignedOver24Hours(issue)
            const isFeature = isClientFeatureRequest(issue)

            return (
              <div
                className={`activity-item ${isOverdueUnassigned ? 'activity-item-overdue' : ''}`}
                key={issue.id}
                style={isOverdueUnassigned ? {
                  backgroundColor: 'rgba(254, 242, 242, 0.75)',
                  borderLeft: '3px solid #ef4444',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  marginBottom: '8px'
                } : {}}
              >
                <div className="activity-icon text-bg-danger">
                  <i className={isFeature ? "bi bi-stars" : "bi bi-bug-fill"} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    <p style={{ margin: 0 }}>Issue “{issue.title}” reported</p>
                    {isFeature && (
                      <span
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '9999px',
                          background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                          color: '#ffffff',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <i className="bi bi-stars" style={{ fontSize: '0.68rem' }} /> Client Feature
                      </span>
                    )}
                    {isOverdueUnassigned && (
                      <span
                        className="badge bg-danger text-white"
                        style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 6px' }}
                      >
                        &gt;24h Unassigned
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '0.78rem', color: '#64748b' }}>{formatDateTime(issue.created_at)}</span>
                </div>
              </div>
            )
          })
        ) : (
          <p className="text-muted">No recent activity.</p>
        )}
      </div>
    </section>
  )
}
