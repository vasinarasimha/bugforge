import React from 'react'

const CATEGORY_CONFIG = {
  open: {
    label: 'Open',
    bg: '#eff6ff',
    color: '#1d4ed8',
    border: '#bfdbfe',
  },
  to_do: {
    label: 'Open',
    bg: '#eff6ff',
    color: '#1d4ed8',
    border: '#bfdbfe',
  },
  'to do': {
    label: 'Open',
    bg: '#eff6ff',
    color: '#1d4ed8',
    border: '#bfdbfe',
  },
  in_progress: {
    label: 'In Progress',
    bg: '#f5f3ff',
    color: '#6d28d9',
    border: '#ddd6fe',
  },
  'in progress': {
    label: 'In Progress',
    bg: '#f5f3ff',
    color: '#6d28d9',
    border: '#ddd6fe',
  },
  resolved: {
    label: 'Resolved',
    bg: '#ecfdf5',
    color: '#047857',
    border: '#a7f3d0',
  },
  closed: {
    label: 'Closed',
    bg: '#f1f5f9',
    color: '#475569',
    border: '#cbd5e1',
  },
  bug: {
    label: 'Bug',
    bg: '#fef2f2',
    color: '#b91c1c',
    border: '#fecaca',
  },
  defect: {
    label: 'Defect',
    bg: '#fef2f2',
    color: '#b91c1c',
    border: '#fecaca',
  },
  feature: {
    label: 'Feature',
    bg: '#eef2ff',
    color: '#4338ca',
    border: '#c7d2fe',
  },
  task: {
    label: 'Task',
    bg: '#f0f9ff',
    color: '#0369a1',
    border: '#bae6fd',
  },
  improvement: {
    label: 'Improvement',
    bg: '#fffbeb',
    color: '#b45309',
    border: '#fde68a',
  },
}

function formatCustomCategory(val) {
  if (!val || typeof val !== 'string') return ''
  return val
    .replace(/[_-]+/g, ' ')
    .trim()
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ')
}

export default function CategoryBadge({
  category,
  size = 'sm',
  className = '',
  fallback = 'Uncategorized',
}) {
  const rawKey = typeof category === 'string' ? category.trim().toLowerCase() : ''
  const config = CATEGORY_CONFIG[rawKey]

  let displayLabel = ''
  let styleConfig = {
    bg: '#f8fafc',
    color: '#475569',
    border: '#cbd5e1',
  }

  if (config) {
    displayLabel = config.label
    styleConfig = { bg: config.bg, color: config.color, border: config.border }
  } else if (rawKey) {
    displayLabel = formatCustomCategory(rawKey)
    styleConfig = { bg: '#f1f5f9', color: '#334155', border: '#cbd5e1' }
  } else {
    displayLabel = fallback
    styleConfig = { bg: '#f8fafc', color: '#94a3b8', border: '#e2e8f0' }
  }

  // Ensure label is never empty or whitespace
  if (!displayLabel || !displayLabel.trim()) {
    displayLabel = fallback || '—'
  }

  const sizeStyles = {
    xs: { padding: '1px 6px', fontSize: '0.68rem', fontWeight: 600 },
    sm: { padding: '2px 8px', fontSize: '0.72rem', fontWeight: 600 },
    md: { padding: '4px 10px', fontSize: '0.8rem', fontWeight: 600 },
  }[size] || { padding: '2px 8px', fontSize: '0.72rem', fontWeight: 600 }

  return (
    <span
      className={`d-inline-flex align-items-center rounded-pill ${className}`}
      style={{
        ...sizeStyles,
        backgroundColor: styleConfig.bg,
        color: styleConfig.color,
        border: `1px solid ${styleConfig.border}`,
        lineHeight: 1.2,
        whiteSpace: 'nowrap',
      }}
    >
      {displayLabel}
    </span>
  )
}
