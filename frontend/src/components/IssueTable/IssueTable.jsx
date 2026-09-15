import { useState } from 'react'

const getPriorityColor = (priorityName) => {
  const colors = { Critical: '#ef4444', High: '#f97316', Medium: '#f59e0b', Low: '#10b981' };
  return colors[priorityName] || '#6b7280';
};

const getStatusColor = (statusName) => {
  const colors = { Open: '#ef4444', 'In Progress': '#f59e0b', Resolved: '#10b981', Closed: '#64748b' };
  return colors[statusName] || '#6b7280';
};

export const formatDateTime = (dateStr) => {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '—'
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(d)
}

export const isIssueUnassignedOver24Hours = (issue) => {
  if (!issue) return false
  if (issue.is_unassigned_over_24h !== undefined) return Boolean(issue.is_unassigned_over_24h)
  if (issue.isUnassignedOver24Hours !== undefined) return Boolean(issue.isUnassignedOver24Hours)
  if (issue.assigned_to) return false
  if (!issue.created_at) return false
  const created = new Date(issue.created_at).getTime()
  if (isNaN(created)) return false
  return (Date.now() - created) > 24 * 60 * 60 * 1000
}

export const isIssueQaUnassignedOver1Hour = (issue) => {
  if (!issue) return false
  if (issue.is_qa_unassigned_over_1h !== undefined) return Boolean(issue.is_qa_unassigned_over_1h)
  if (issue.isQaUnassignedOver1Hour !== undefined) return Boolean(issue.isQaUnassignedOver1Hour)
  if (issue.assigned_qa_id) return false

  const statusName = issue.status_name || (typeof issue.status === 'string' ? issue.status : issue.status?.name) || ''
  const isResolved = statusName === 'Resolved' || Boolean(issue.developer_fixed_at)
  if (!isResolved || statusName === 'Closed' || statusName === 'Verified') return false

  const fixTimeStr = issue.developer_fixed_at || issue.updated_at
  if (!fixTimeStr) return false
  const fixTime = new Date(fixTimeStr).getTime()
  if (isNaN(fixTime)) return false
  return (Date.now() - fixTime) > 1 * 60 * 60 * 1000
}

export const isClientFeatureRequest = (issue) => {
  if (!issue || issue.issue_type !== 'Feature') return false
  return Boolean(
    issue.requesting_company_id ||
    issue.requesting_company_name ||
    issue.project_name === 'BugForge' ||
    issue.project_name?.includes('BugForge')
  )
}

export default function IssueTable({ issues = [], onEdit, onDelete, canEdit = true, canDelete = true, onView, onAssignTeam }) {
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  const totalPages = Math.ceil(issues.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const paginatedIssues = issues.slice(startIndex, startIndex + itemsPerPage)

  const goToPage = (page) => {
    if (page >= 1 && page <= totalPages) setCurrentPage(page)
  }

  return (
    <>
      <style>{`
        .issue-table tbody tr.row-overdue-unassigned {
          background-color: rgba(239, 68, 68, 0.06) !important;
          border-left: 4px solid #ef4444 !important;
          transition: background-color 0.15s ease;
        }
        .issue-table tbody tr.row-overdue-unassigned:hover {
          background-color: rgba(239, 68, 68, 0.12) !important;
        }
        .issue-table tbody tr.row-bugforge-project {
          background: linear-gradient(90deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.03) 100%) !important;
          border-left: 4px solid #6366f1 !important;
          transition: background-color 0.15s ease;
        }
        .issue-table tbody tr.row-bugforge-project:hover {
          background: linear-gradient(90deg, rgba(99, 102, 241, 0.14) 0%, rgba(139, 92, 246, 0.06) 100%) !important;
        }
        .issue-table tbody tr.row-bugforge-project.row-overdue-unassigned {
          background-color: rgba(239, 68, 68, 0.08) !important;
          border-left: 4px solid #ef4444 !important;
        }
        .issue-table tbody tr:not(.row-overdue-unassigned):not(.row-bugforge-project) {
          border-left: 4px solid transparent;
        }
        .badge-overdue-alert {
          background-color: rgba(239, 68, 68, 0.12);
          color: #dc2626;
          border: 1px solid rgba(239, 68, 68, 0.28);
          font-size: 0.68rem;
          font-weight: 600;
          padding: 3px 7px;
          border-radius: 9999px;
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }
        .badge-bf-feature {
          background-color: rgba(99, 102, 241, 0.14);
          color: #4f46e5;
          border: 1px solid rgba(99, 102, 241, 0.35);
          font-size: 0.68rem;
          font-weight: 700;
          padding: 2.5px 7px;
          border-radius: 9999px;
          display: inline-flex;
          align-items: center;
          gap: 3.5px;
        }
        .badge-bf-defect {
          background-color: rgba(225, 29, 72, 0.12);
          color: #be123c;
          border: 1px solid rgba(225, 29, 72, 0.32);
          font-size: 0.68rem;
          font-weight: 700;
          padding: 2.5px 7px;
          border-radius: 9999px;
          display: inline-flex;
          align-items: center;
          gap: 3.5px;
        }
        .badge-bf-task {
          background-color: rgba(14, 165, 233, 0.12);
          color: #0369a1;
          border: 1px solid rgba(14, 165, 233, 0.32);
          font-size: 0.68rem;
          font-weight: 700;
          padding: 2.5px 7px;
          border-radius: 9999px;
          display: inline-flex;
          align-items: center;
          gap: 3.5px;
        }
        .badge-client-company {
          background-color: rgba(79, 70, 229, 0.08);
          color: #4338ca;
          border: 1px solid rgba(79, 70, 229, 0.22);
          font-size: 0.68rem;
          font-weight: 600;
          padding: 2.5px 7px;
          border-radius: 9999px;
          display: inline-flex;
          align-items: center;
          gap: 3.5px;
        }
        .dev-badge-assigned {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 3px 8px;
          background: rgba(16, 185, 129, 0.10);
          color: #065f46;
          border: 1px solid rgba(16, 185, 129, 0.25);
          border-radius: 6px;
          font-size: 0.78rem;
          font-weight: 600;
          max-width: 150px;
        }
        .dev-badge-unassigned {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 3px 8px;
          background: rgba(148, 163, 184, 0.12);
          color: #64748b;
          border: 1px dashed rgba(148, 163, 184, 0.4);
          border-radius: 6px;
          font-size: 0.78rem;
          font-weight: 500;
        }
        .qa-badge-assigned {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 3px 8px;
          background: rgba(139, 92, 246, 0.10);
          color: #6d28d9;
          border: 1px solid rgba(139, 92, 246, 0.25);
          border-radius: 6px;
          font-size: 0.78rem;
          font-weight: 600;
          max-width: 150px;
        }
        .qa-badge-unassigned {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 3px 8px;
          background: rgba(148, 163, 184, 0.12);
          color: #64748b;
          border: 1px dashed rgba(148, 163, 184, 0.4);
          border-radius: 6px;
          font-size: 0.78rem;
          font-weight: 500;
        }
      `}</style>

      <div className="table-responsive">
        <table className="table table-hover align-middle issue-table">
          <thead>
            <tr>
              <th>Issue Key</th>
              <th>Title</th>
              <th>Project</th>
              <th>Assigned Developer</th>
              <th>Assigned QA</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedIssues.length ? paginatedIssues.map((issue) => {
              const isDevOverdue = isIssueUnassignedOver24Hours(issue)
              const isQaOverdue = isIssueQaUnassignedOver1Hour(issue)
              const isOverdue = isDevOverdue || isQaOverdue
              const isFeature = issue.issue_type === 'Feature'
              const isDefect = issue.issue_type === 'Defect' || issue.issue_type === 'Bug'
              const isTask = issue.issue_type === 'Task'
              const isClientFeature = Boolean(issue.requesting_company_id)
              const isBugForgeProject = issue.project_name === 'BugForge' || issue.issue_key?.startsWith('BF-') || issue.project_key === 'BF' || isClientFeature

              return (
                <tr
                  key={issue.id}
                  className={`${isOverdue ? 'row-overdue-unassigned' : ''} ${isBugForgeProject ? 'row-bugforge-project' : ''}`}
                >
                  <td>
                    <div className="d-flex flex-column align-items-start gap-1">
                      <div className="d-flex align-items-center gap-1.5 flex-wrap">
                        <strong className="issue-id">{issue.issue_key || '—'}</strong>
                        {isBugForgeProject && (
                          <span
                            className={isFeature ? 'badge-bf-feature' : isDefect ? 'badge-bf-defect' : 'badge-bf-task'}
                            title={`BugForge Platform ${issue.issue_type}`}
                          >
                            <i className={`bi ${isFeature ? 'bi-stars' : isDefect ? 'bi-bug-fill' : 'bi-check2-circle'}`} />
                            {isFeature ? 'BugForge Feature' : isDefect ? 'BugForge Defect' : 'BugForge Task'}
                          </span>
                        )}
                        {issue.requesting_company_name && (
                          <span className="badge-client-company" title={`Client customization request from ${issue.requesting_company_name}`}>
                            <i className="bi bi-building" /> {issue.requesting_company_name}
                          </span>
                        )}
                        {isDevOverdue && (
                          <span className="badge-overdue-alert" title="Issue waiting for developer assignment > 24 hours">
                            <i className="bi bi-clock-history" /> &gt;24h Unassigned
                          </span>
                        )}
                        {isQaOverdue && (
                          <span className="badge-overdue-alert" title="Issue fixed by developer waiting for QA assignment > 1 hour">
                            <i className="bi bi-clock-history" /> &gt;1h QA Unassigned
                          </span>
                        )}
                      </div>
                    </div>
                  </td>

                  <td className="issue-title">
                    <div>{issue.title}</div>
                    <div className="d-flex align-items-center gap-2 mt-1 flex-wrap">
                      {issue.requesting_company_name && (
                        <span className="text-muted" style={{ fontSize: '0.72rem' }}>
                          <i className="bi bi-building me-1" />{issue.requesting_company_name}
                        </span>
                      )}
                      {(isFeature || isClientFeature || isBugForgeProject) && (
                        issue.team_name ? (
                          <span className="badge px-2 py-0.5 rounded-pill" style={{ fontSize: '0.68rem', backgroundColor: '#e0e7ff', color: '#3730a3', border: '1px solid #c7d2fe' }}>
                            <i className="bi bi-diagram-3-fill me-1" />{issue.team_name}
                          </span>
                        ) : (
                          <span className="badge px-2 py-0.5 rounded-pill" style={{ fontSize: '0.68rem', backgroundColor: '#fef3c7', color: '#92400e', border: '1px solid #fde68a' }}>
                            <i className="bi bi-exclamation-circle me-1" />No Squad
                          </span>
                        )
                      )}
                    </div>
                  </td>
                  <td>{issue.project_name || '—'}</td>
                  <td>
                    {issue.assignee ? (
                      <span className="dev-badge-assigned" title={issue.assignee}>
                        <i className="bi bi-person-check" />
                        <span className="text-truncate">{issue.assignee}</span>
                      </span>
                    ) : (
                      <span className="dev-badge-unassigned" title="No developer assigned yet">
                        <i className="bi bi-person-dash" /> Unassigned
                      </span>
                    )}
                  </td>
                  <td>
                    {issue.assigned_qa_name || issue.assigned_qa?.full_name ? (
                      <span className="qa-badge-assigned" title={issue.assigned_qa_name || issue.assigned_qa?.full_name}>
                        <i className="bi bi-shield-check" />
                        <span className="text-truncate">{issue.assigned_qa_name || issue.assigned_qa?.full_name}</span>
                      </span>
                    ) : (
                      <span className="qa-badge-unassigned" title="No QA assigned yet">
                        <i className="bi bi-shield-x" /> Unassigned
                      </span>
                    )}
                  </td>
                  <td>
                    <span className="badge" style={{ backgroundColor: getPriorityColor(issue.priority_name || ''), color: 'white' }}>
                      {issue.priority_name || '—'}
                    </span>
                  </td>
                  <td>
                    <span className="badge" style={{ backgroundColor: getStatusColor(issue.status_name || ''), color: 'white' }}>
                      {issue.status_name || '—'}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.82rem', color: '#475569', whiteSpace: 'nowrap' }}>
                    {formatDateTime(issue.created_at)}
                  </td>
                  <td>
                    <div className="d-flex gap-1 align-items-center">
                      {onAssignTeam && (isFeature || isClientFeature || isBugForgeProject) && (
                        <button
                          type="button"
                          className="btn btn-outline-primary btn-sm border d-inline-flex align-items-center gap-1"
                          title={issue.team_name ? `Change squad: ${issue.team_name}` : "Assign internal squad"}
                          onClick={() => onAssignTeam(issue)}
                          style={{ fontSize: '0.75rem', padding: '3px 8px', whiteSpace: 'nowrap' }}
                        >
                          <i className="bi bi-diagram-3-fill" />
                          <span>{issue.team_name ? 'Reassign' : 'Assign Squad'}</span>
                        </button>
                      )}
                      <button className="btn btn-light btn-sm border" title="View" onClick={() => onView ? onView(issue) : onEdit?.(issue)}>
                        <i className="bi bi-eye" />
                      </button>
                      {canEdit && onEdit && (
                        <button className="btn btn-light btn-sm border" title="Edit" onClick={() => onEdit(issue)}>
                          <i className="bi bi-pencil" />
                        </button>
                      )}
                      {canDelete && onDelete && (
                        <button className="btn btn-light btn-sm border text-danger" title="Delete" onClick={() => onDelete(issue)}>
                          <i className="bi bi-trash" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            }) : (
              <tr><td colSpan="8" className="text-center text-muted py-4">No issues found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="d-flex justify-content-between align-items-center mt-3">
          <span className="text-muted" style={{ fontSize: '0.9rem' }}>
            Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, issues.length)} of {issues.length} entries
          </span>
          <nav aria-label="Page navigation">
            <ul className="pagination pagination-sm mb-0">
              <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                <button className="page-link" onClick={() => goToPage(currentPage - 1)}>Previous</button>
              </li>
              {[...Array(totalPages)].map((_, i) => (
                <li key={i} className={`page-item ${currentPage === i + 1 ? 'active' : ''}`}>
                  <button className="page-link" onClick={() => goToPage(i + 1)}>{i + 1}</button>
                </li>
              ))}
              <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                <button className="page-link" onClick={() => goToPage(currentPage + 1)}>Next</button>
              </li>
            </ul>
          </nav>
        </div>
      )}
    </>
  )
}
