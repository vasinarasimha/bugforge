import { useState } from 'react'
import Modal from '../Modal/Modal'

const formatDate = (date) => new Date(date).toLocaleDateString()

const getProjectStatusColor = (status) => {
  const colors = {
    Active: '#10b981',
    Completed: '#10b981',
    'On Hold': '#f59e0b',
    Archived: '#6b7280'
  };
  return colors[status] || '#6b7280';
};

export default function ProjectTable({ projects = [], onEdit, onDelete, canEdit = true, canDelete = true, onView }) {
  const [viewing, setViewing] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  const totalPages = Math.ceil(projects.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const paginatedProjects = projects.slice(startIndex, startIndex + itemsPerPage)

  const goToPage = (page) => {
    if (page >= 1 && page <= totalPages) setCurrentPage(page)
  }

  return (
    <>
      <div className="table-responsive">
        <table className="table table-striped align-middle project-table">
          <thead>
            <tr><th>Project Name</th><th>Client</th><th>Status</th><th>Start Date</th><th>Created Date</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {paginatedProjects.length ? paginatedProjects.map((project) => (
              <tr key={project.id}>
                <td><strong>{project.name}</strong></td>
                <td>{project.client_name || '-'}</td>
                <td><span className="badge" style={{ backgroundColor: getProjectStatusColor(project.status || ''), color: 'white' }}>{project.status || 'Active'}</span></td>
                <td>{project.start_date ? formatDate(project.start_date) : '-'}</td>
                <td>{formatDate(project.created_at)}</td>
                <td>
                  <div className="d-flex gap-1">
                    <button className="btn btn-outline-primary btn-sm" onClick={() => onView ? onView(project) : setViewing(project)}>
                      View <i className="bi bi-eye" />
                    </button>
                    {canEdit && onEdit && (
                      <button className="btn btn-light border btn-sm" onClick={() => onEdit(project)} title="Edit">
                        <i className="bi bi-pencil" />
                      </button>
                    )}
                    {canDelete && onDelete && (
                      <button className="btn btn-light border btn-sm text-danger" onClick={() => onDelete(project)} title="Delete">
                        <i className="bi bi-trash" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            )) : <tr><td colSpan="6" className="text-center text-muted py-4">No projects found.</td></tr>}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="d-flex justify-content-between align-items-center mt-3">
          <span className="text-muted" style={{ fontSize: '0.9rem' }}>
            Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, projects.length)} of {projects.length} entries
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
      
      {viewing && (
        <Modal
          title={`Project: ${viewing.name}`}
          primaryLabel="Close"
          onPrimary={() => setViewing(null)}
          onClose={() => setViewing(null)}
          sizeClass="modal-lg"
        >
          <div className="mb-3">
            <h6 className="text-muted mb-1">Description</h6>
            <p>{viewing.description || 'No description provided.'}</p>
          </div>
          <div className="row mb-3">
            <div className="col-6">
              <h6 className="text-muted mb-1">Status</h6>
              <p><span className="badge" style={{ backgroundColor: getProjectStatusColor(viewing.status || ''), color: 'white' }}>{viewing.status || 'Active'}</span></p>
            </div>
            <div className="col-6">
              <h6 className="text-muted mb-1">Client</h6>
              <p>{viewing.client_name || 'N/A'}</p>
            </div>
          </div>
          <div className="row mb-3">
            <div className="col-6">
              <h6 className="text-muted mb-1">Repository</h6>
              <p>{viewing.repository_url ? <a href={viewing.repository_url} target="_blank" rel="noreferrer">Link <i className="bi bi-box-arrow-up-right" /></a> : 'N/A'}</p>
            </div>
            <div className="col-6">
              <h6 className="text-muted mb-1">Tech Stack</h6>
              <p>{viewing.tech_stack || 'N/A'}</p>
            </div>
          </div>
          <div className="row">
            <div className="col-6">
              <h6 className="text-muted mb-1">Created By</h6>
              <p>{viewing.creator_name}</p>
            </div>
            <div className="col-6">
              <h6 className="text-muted mb-1">Created At</h6>
              <p>{formatDate(viewing.created_at)}</p>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}
