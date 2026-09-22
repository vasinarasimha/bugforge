import { useState, useMemo, useEffect } from 'react'
import Modal from '../Modal/Modal'
import TablePagination from '../common/TablePagination'
import { sortData } from '../../utils/tableSortAndPagination'

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

const projectColumnConfigs = {
  name: {
    type: 'text',
    accessor: (p) => p.name || p.project_name || '',
  },
  client_name: {
    type: 'text',
    accessor: (p) => p.client_name || '',
  },
  status: {
    type: 'project_status',
    accessor: (p) => p.status || 'Active',
  },
  start_date: {
    type: 'date',
    accessor: (p) => p.start_date || '',
  },
  created_at: {
    type: 'date',
    accessor: (p) => p.created_at || '',
  },
}

export default function ProjectTable({ projects = [], onEdit, onDelete, canEdit = true, canDelete = true, onView, onViewHistory }) {
  const [viewing, setViewing] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [sortKey, setSortKey] = useState(null)
  const [sortDirection, setSortDirection] = useState('asc')
  const itemsPerPage = 10

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDirection('asc')
    }
  }

  const sortedProjects = useMemo(() => {
    return sortData(projects, sortKey, sortDirection, projectColumnConfigs)
  }, [projects, sortKey, sortDirection])

  const totalPages = Math.ceil(sortedProjects.length / itemsPerPage)
  const safeCurrentPage = totalPages > 0 ? Math.min(Math.max(1, currentPage), totalPages) : 1
  const startIndex = (safeCurrentPage - 1) * itemsPerPage
  const paginatedProjects = sortedProjects.slice(startIndex, startIndex + itemsPerPage)

  useEffect(() => {
    if (totalPages > 0 && currentPage > totalPages) {
      setCurrentPage(totalPages)
    }
  }, [totalPages, currentPage])

  return (
    <>
      <style>{`
        .project-table th.sortable-header {
          cursor: pointer;
          user-select: none;
          white-space: nowrap;
        }
        .project-table th.sortable-header:hover {
          background-color: rgba(0, 0, 0, 0.05);
        }
        .project-table th.sortable-header .sort-icon {
          display: inline-block;
          margin-left: 6px;
          font-weight: 700;
        }
      `}</style>

      <div className="table-responsive">
        <table className="table table-striped align-middle project-table">
          <thead>
            <tr>
              <th
                role="button"
                tabIndex={0}
                className="sortable-header"
                onClick={() => handleSort('name')}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('name'); } }}
                aria-sort={sortKey === 'name' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Project Name
                {sortKey === 'name' && (
                  <span className="sort-icon" aria-hidden="true">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th
                role="button"
                tabIndex={0}
                className="sortable-header"
                onClick={() => handleSort('client_name')}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('client_name'); } }}
                aria-sort={sortKey === 'client_name' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Client
                {sortKey === 'client_name' && (
                  <span className="sort-icon" aria-hidden="true">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th
                role="button"
                tabIndex={0}
                className="sortable-header"
                onClick={() => handleSort('status')}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('status'); } }}
                aria-sort={sortKey === 'status' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Status
                {sortKey === 'status' && (
                  <span className="sort-icon" aria-hidden="true">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th
                role="button"
                tabIndex={0}
                className="sortable-header"
                onClick={() => handleSort('start_date')}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('start_date'); } }}
                aria-sort={sortKey === 'start_date' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Start Date
                {sortKey === 'start_date' && (
                  <span className="sort-icon" aria-hidden="true">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th
                role="button"
                tabIndex={0}
                className="sortable-header"
                onClick={() => handleSort('created_at')}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('created_at'); } }}
                aria-sort={sortKey === 'created_at' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
              >
                Created Date
                {sortKey === 'created_at' && (
                  <span className="sort-icon" aria-hidden="true">
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th>Actions</th>
            </tr>
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

      <TablePagination
        currentPage={safeCurrentPage}
        totalPages={totalPages}
        totalItems={sortedProjects.length}
        startIndex={startIndex}
        itemsPerPage={itemsPerPage}
        onPageChange={setCurrentPage}
      />
      
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
          <div className="row mb-3">
            <div className="col-4">
              <h6 className="text-muted mb-1">Assigned Team</h6>
              <p><span className="badge bg-primary-subtle text-primary border border-primary-subtle">{viewing.team_name || 'No Team Assigned'}</span></p>
            </div>
            <div className="col-4">
              <h6 className="text-muted mb-1">Project Manager</h6>
              <p>{viewing.project_manager_name || 'Unassigned'}</p>
            </div>
            <div className="col-4">
              <h6 className="text-muted mb-1">Team Leader</h6>
              <p>{viewing.team_leader_name || 'Unassigned'}</p>
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
