import { useState } from 'react'

const getPriorityColor = (priorityName) => {
  const colors = { Critical: '#ef4444', High: '#f97316', Medium: '#f59e0b', Low: '#10b981' };
  return colors[priorityName] || '#6b7280';
};

const getStatusColor = (statusName) => {
  const colors = { Open: '#ef4444', 'In Progress': '#f59e0b', Resolved: '#10b981', Closed: '#64748b' };
  return colors[statusName] || '#6b7280';
};

export default function IssueTable({ issues = [], onEdit, onDelete, canEdit = true, canDelete = true, onView }) {
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
      <div className="table-responsive">
        <table className="table table-striped align-middle issue-table">
          <thead><tr><th>Issue ID</th><th>Title</th><th>Project</th><th>Priority</th><th>Status</th><th>Reported Date</th><th>Actions</th></tr></thead>
          <tbody>
            {paginatedIssues.length ? paginatedIssues.map((issue) => (
              <tr key={issue.id}>
                <td><strong className="issue-id">RI-{issue.id}</strong></td>
                <td className="issue-title">{issue.title}</td>
                <td>{issue.project_name}</td>
                <td><span className="badge" style={{ backgroundColor: getPriorityColor(issue.priority_name || ''), color: 'white' }}>{issue.priority_name}</span></td>
                <td><span className="badge" style={{ backgroundColor: getStatusColor(issue.status_name || ''), color: 'white' }}>{issue.status_name}</span></td>
                <td>{new Date(issue.created_at).toLocaleDateString()}</td>
                <td>
                  <div className="d-flex gap-1">
                    <button className="btn btn-light btn-sm border" title="View" onClick={() => onView ? onView(issue) : onEdit?.(issue)}><i className="bi bi-eye" /></button>
                    {canEdit && onEdit && <button className="btn btn-light btn-sm border" title="Edit" onClick={() => onEdit(issue)}><i className="bi bi-pencil" /></button>}
                    {canDelete && onDelete && <button className="btn btn-light btn-sm border text-danger" title="Delete" onClick={() => onDelete(issue)}><i className="bi bi-trash" /></button>}
                  </div>
                </td>
              </tr>
            )) : <tr><td colSpan="7" className="text-center text-muted py-4">No issues found.</td></tr>}
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
