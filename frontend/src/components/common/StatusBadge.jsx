import React from 'react'

const DEFAULT_STATUS_COLORS = {
  'Open': '#3b82f6',
  'In Progress': '#8b5cf6',
  'Resolved': '#10b981',
  'Verified': '#06b6d4',
  'Closed': '#64748b',
  'Pending': '#f59e0b',
  'Under Review': '#8b5cf6',
  'Approved': '#10b981',
  'Rejected': '#ef4444',
  'Implemented': '#059669',
  'Cancelled': '#94a3b8',
}

function getSafeColor(rawColor, statusName) {
  if (typeof rawColor === 'string' && rawColor.startsWith('#') && (rawColor.length === 4 || rawColor.length === 7)) {
    return rawColor
  }
  return DEFAULT_STATUS_COLORS[statusName] || '#6366f1'
}

export default function StatusBadge({
  status,
  color,
  category,
  size = 'md',
  showDot = true,
  className = '',
  fallback = 'Unknown',
}) {
  let statusName = ''
  let explicitColor = color

  if (typeof status === 'object' && status !== null) {
    statusName = status.name || status.status_name || status.status || status.label || ''
    explicitColor = status.color || explicitColor
  } else if (typeof status === 'string') {
    statusName = status.trim()
  }

  if (!statusName) {
    statusName = fallback || '—'
  }

  const badgeColor = getSafeColor(explicitColor, statusName)

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs font-medium',
    lg: 'px-3 py-1.5 text-sm font-semibold',
  }[size] || 'px-2.5 py-1 text-xs font-medium'

  // Determine hex opacity or fallback backgroundColor
  const isHex = badgeColor.startsWith('#') && badgeColor.length === 7
  const bgStyle = isHex ? `${badgeColor}18` : 'rgba(99, 102, 241, 0.12)'
  const borderStyle = isHex ? `${badgeColor}35` : 'rgba(99, 102, 241, 0.25)'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium transition-all ${sizeClasses} ${className}`}
      style={{
        backgroundColor: bgStyle,
        color: badgeColor,
        border: `1px solid ${borderStyle}`,
      }}
    >
      {showDot && (
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0"
          style={{ backgroundColor: badgeColor }}
        />
      )}
      <span>{statusName}</span>
    </span>
  )
}
