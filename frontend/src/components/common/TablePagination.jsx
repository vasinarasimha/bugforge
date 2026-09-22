import React from 'react'
import { getPageNumbers } from '../../utils/tableSortAndPagination'

export default function TablePagination({
  currentPage,
  totalPages,
  totalItems,
  startIndex,
  itemsPerPage,
  onPageChange,
}) {
  if (!totalItems || totalItems <= 0 || !totalPages || totalPages <= 0) {
    return null
  }

  const pageNumbers = getPageNumbers(currentPage, totalPages)
  const isFirstDisabled = currentPage <= 1
  const isLastDisabled = currentPage >= totalPages

  const startEntry = startIndex + 1
  const endEntry = Math.min(startIndex + itemsPerPage, totalItems)

  return (
    <div className="d-flex justify-content-between align-items-center mt-3 flex-wrap gap-2">
      <span className="text-muted" style={{ fontSize: '0.9rem' }}>
        Showing {startEntry} to {endEntry} of {totalItems} entries
      </span>
      <nav aria-label="Table pagination">
        <ul className="pagination pagination-sm mb-0">
          <li className={`page-item ${isFirstDisabled ? 'disabled' : ''}`}>
            <button
              type="button"
              className="page-link"
              onClick={() => onPageChange(1)}
              disabled={isFirstDisabled}
              aria-label="First page"
            >
              First
            </button>
          </li>
          <li className={`page-item ${isFirstDisabled ? 'disabled' : ''}`}>
            <button
              type="button"
              className="page-link"
              onClick={() => onPageChange(currentPage - 1)}
              disabled={isFirstDisabled}
              aria-label="Previous page"
            >
              Previous
            </button>
          </li>
          {pageNumbers.map((page) => (
            <li
              key={page}
              className={`page-item ${currentPage === page ? 'active' : ''}`}
            >
              <button
                type="button"
                className="page-link"
                onClick={() => onPageChange(page)}
                aria-current={currentPage === page ? 'page' : undefined}
              >
                {page}
              </button>
            </li>
          ))}
          <li className={`page-item ${isLastDisabled ? 'disabled' : ''}`}>
            <button
              type="button"
              className="page-link"
              onClick={() => onPageChange(currentPage + 1)}
              disabled={isLastDisabled}
              aria-label="Next page"
            >
              Next
            </button>
          </li>
          <li className={`page-item ${isLastDisabled ? 'disabled' : ''}`}>
            <button
              type="button"
              className="page-link"
              onClick={() => onPageChange(totalPages)}
              disabled={isLastDisabled}
              aria-label="Last page"
            >
              Last
            </button>
          </li>
        </ul>
      </nav>
    </div>
  )
}
