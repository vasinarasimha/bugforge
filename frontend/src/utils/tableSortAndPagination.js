export const PRIORITY_RANK = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
}

export const ISSUE_STATUS_RANK = {
  open: 1,
  'in progress': 2,
  'in review': 3,
  resolved: 4,
  verified: 5,
  closed: 6,
}

export const PROJECT_STATUS_RANK = {
  active: 1,
  'on hold': 2,
  completed: 3,
  archived: 4,
}

/**
 * Returns an array of page numbers to display.
 * Displays exactly 3 page numbers whenever possible (totalPages >= 3):
 * Left: previous, Center: current, Right: next.
 * If current is 1: [1, 2, 3]
 * If current is last: [totalPages - 2, totalPages - 1, totalPages]
 * If totalPages < 3: returns only pages that actually exist.
 */
export function getPageNumbers(currentPage, totalPages) {
  if (!totalPages || totalPages <= 0) return []
  if (totalPages <= 3) {
    const pages = []
    for (let i = 1; i <= totalPages; i++) {
      pages.push(i)
    }
    return pages
  }

  if (currentPage <= 1) {
    return [1, 2, 3]
  }

  if (currentPage >= totalPages) {
    return [totalPages - 2, totalPages - 1, totalPages]
  }

  return [currentPage - 1, currentPage, currentPage + 1]
}

/**
 * Sorts an array of items across the entire dataset.
 * Supports text, numbers, dates, status and priority rankings.
 * Null/undefined values are placed consistently at the bottom.
 */
export function sortData(items, sortKey, sortDirection, columnConfigs = {}) {
  if (!sortKey || !Array.isArray(items) || items.length === 0) {
    return items
  }

  const colConfig = columnConfigs[sortKey] || {}
  const type = colConfig.type || 'text'
  const accessor = typeof colConfig.accessor === 'function'
    ? colConfig.accessor
    : (item) => item?.[sortKey]

  return [...items].sort((itemA, itemB) => {
    const rawA = accessor(itemA)
    const rawB = accessor(itemB)

    const isAEmpty = rawA == null || rawA === ''
    const isBEmpty = rawB == null || rawB === ''

    if (isAEmpty && isBEmpty) return 0
    if (isAEmpty) return 1
    if (isBEmpty) return -1

    let comparison = 0

    switch (type) {
      case 'number': {
        const numA = Number(rawA)
        const numB = Number(rawB)
        const aNaN = isNaN(numA)
        const bNaN = isNaN(numB)
        if (aNaN && bNaN) return 0
        if (aNaN) return 1
        if (bNaN) return -1
        comparison = numA - numB
        break
      }

      case 'date': {
        const timeA = new Date(rawA).getTime()
        const timeB = new Date(rawB).getTime()
        const aNaN = isNaN(timeA)
        const bNaN = isNaN(timeB)
        if (aNaN && bNaN) return 0
        if (aNaN) return 1
        if (bNaN) return -1
        comparison = timeA - timeB
        break
      }

      case 'priority': {
        const strA = String(rawA).toLowerCase().trim()
        const strB = String(rawB).toLowerCase().trim()
        const rankA = PRIORITY_RANK[strA] || (typeof itemA.priority_id === 'number' ? itemA.priority_id : 0)
        const rankB = PRIORITY_RANK[strB] || (typeof itemB.priority_id === 'number' ? itemB.priority_id : 0)
        if (rankA !== rankB) {
          comparison = rankA - rankB
        } else {
          comparison = String(rawA).localeCompare(String(rawB), undefined, { sensitivity: 'base' })
        }
        break
      }

      case 'issue_status': {
        const strA = String(rawA).toLowerCase().trim()
        const strB = String(rawB).toLowerCase().trim()
        const rankA = ISSUE_STATUS_RANK[strA] ?? (typeof itemA.status?.order_index === 'number' ? itemA.status.order_index : typeof itemA.order_index === 'number' ? itemA.order_index : 99)
        const rankB = ISSUE_STATUS_RANK[strB] ?? (typeof itemB.status?.order_index === 'number' ? itemB.status.order_index : typeof itemB.order_index === 'number' ? itemB.order_index : 99)
        if (rankA !== rankB) {
          comparison = rankA - rankB
        } else {
          comparison = String(rawA).localeCompare(String(rawB), undefined, { sensitivity: 'base' })
        }
        break
      }

      case 'project_status': {
        const strA = String(rawA).toLowerCase().trim()
        const strB = String(rawB).toLowerCase().trim()
        const rankA = PROJECT_STATUS_RANK[strA] ?? 99
        const rankB = PROJECT_STATUS_RANK[strB] ?? 99
        if (rankA !== rankB) {
          comparison = rankA - rankB
        } else {
          comparison = String(rawA).localeCompare(String(rawB), undefined, { sensitivity: 'base' })
        }
        break
      }

      case 'alphanumeric':
      case 'text':
      default: {
        comparison = String(rawA).localeCompare(String(rawB), undefined, {
          numeric: true,
          sensitivity: 'base',
        })
        break
      }
    }

    return sortDirection === 'desc' ? -comparison : comparison
  })
}
