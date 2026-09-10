import React from 'react'

const AUDIT_ACTION_CONFIG = {
  STATUS_CREATED: {
    label: 'Status Created',
    bg: '#ecfdf5',
    color: '#047857',
    border: '#a7f3d0',
    icon: 'bi-plus-circle',
  },
  STATUS_UPDATED: {
    label: 'Status Updated',
    bg: '#eff6ff',
    color: '#1d4ed8',
    border: '#bfdbfe',
    icon: 'bi-pencil',
  },
  STATUS_DELETED: {
    label: 'Status Deleted',
    bg: '#fef2f2',
    color: '#b91c1c',
    border: '#fecaca',
    icon: 'bi-trash',
  },
  STATUS_DEACTIVATED_DUE_TO_DEPENDENCIES: {
    label: 'Status Deactivated',
    bg: '#fff7ed',
    color: '#c2410c',
    border: '#fed7aa',
    icon: 'bi-pause-circle',
  },
  STATUS_DEACTIVATED: {
    label: 'Status Deactivated',
    bg: '#fff7ed',
    color: '#c2410c',
    border: '#fed7aa',
    icon: 'bi-pause-circle',
  },
  STATUS_ACTIVATED: {
    label: 'Status Activated',
    bg: '#ecfeff',
    color: '#0e7490',
    border: '#a5f3fc',
    icon: 'bi-check-circle',
  },
  STATUS_REORDERED: {
    label: 'Status Reordered',
    bg: '#eff6ff',
    color: '#1d4ed8',
    border: '#bfdbfe',
    icon: 'bi-arrow-down-up',
  },
  COMPANY_SETTINGS_UPDATED: {
    label: 'Settings Updated',
    bg: '#eff6ff',
    color: '#1d4ed8',
    border: '#bfdbfe',
    icon: 'bi-sliders',
  },
  COMPANY_PROFILE_UPDATED: {
    label: 'Profile Updated',
    bg: '#eff6ff',
    color: '#1d4ed8',
    border: '#bfdbfe',
    icon: 'bi-building',
  },
  COMPANY_CREATED: {
    label: 'Company Created',
    bg: '#ecfdf5',
    color: '#047857',
    border: '#a7f3d0',
    icon: 'bi-building-add',
  },
  COMPANY_UPDATED: {
    label: 'Company Updated',
    bg: '#eff6ff',
    color: '#1d4ed8',
    border: '#bfdbfe',
    icon: 'bi-pencil',
  },
  COMPANY_ACTIVATED: {
    label: 'Company Activated',
    bg: '#ecfeff',
    color: '#0e7490',
    border: '#a5f3fc',
    icon: 'bi-check-circle',
  },
  COMPANY_DEACTIVATED: {
    label: 'Company Deactivated',
    bg: '#fef2f2',
    color: '#b91c1c',
    border: '#fecaca',
    icon: 'bi-slash-circle',
  },
  CUSTOMIZATION_REQUEST_SUBMITTED: {
    label: 'Customization Requested',
    bg: '#f5f3ff',
    color: '#6d28d9',
    border: '#ddd6fe',
    icon: 'bi-lightbulb',
  },
  CUSTOMIZATION_REQUEST_REVIEWED: {
    label: 'Customization Reviewed',
    bg: '#f5f3ff',
    color: '#6d28d9',
    border: '#ddd6fe',
    icon: 'bi-patch-check',
  },
}

function formatUnknownAction(val) {
  if (!val || typeof val !== 'string') return ''
  return val
    .replace(/[_-]+/g, ' ')
    .trim()
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ')
}

export default function AuditActionBadge({
  action,
  size = 'sm',
  showIcon = false,
  className = '',
  fallback = 'Unknown Action',
}) {
  const rawAction = typeof action === 'string' ? action.trim() : ''
  const config = AUDIT_ACTION_CONFIG[rawAction]

  let displayLabel = ''
  let styleConfig = {
    bg: '#f8fafc',
    color: '#334155',
    border: '#cbd5e1',
    icon: 'bi-clock-history',
  }

  if (config) {
    displayLabel = config.label
    styleConfig = config
  } else if (rawAction) {
    displayLabel = formatUnknownAction(rawAction)
    styleConfig = {
      bg: '#f1f5f9',
      color: '#334155',
      border: '#cbd5e1',
      icon: 'bi-activity',
    }
  } else {
    displayLabel = fallback
    styleConfig = {
      bg: '#f8fafc',
      color: '#94a3b8',
      border: '#e2e8f0',
      icon: 'bi-question-circle',
    }
  }

  if (!displayLabel || !displayLabel.trim()) {
    displayLabel = fallback || '—'
  }

  const sizeStyles = {
    xs: { padding: '1px 6px', fontSize: '0.68rem', fontWeight: 600 },
    sm: { padding: '2.5px 8px', fontSize: '0.72rem', fontWeight: 600 },
    md: { padding: '4px 10px', fontSize: '0.8rem', fontWeight: 600 },
  }[size] || { padding: '2.5px 8px', fontSize: '0.72rem', fontWeight: 600 }

  return (
    <span
      className={`d-inline-flex align-items-center gap-1 rounded-pill ${className}`}
      style={{
        ...sizeStyles,
        backgroundColor: styleConfig.bg,
        color: styleConfig.color,
        border: `1px solid ${styleConfig.border}`,
        lineHeight: 1.2,
        whiteSpace: 'nowrap',
      }}
    >
      {showIcon && styleConfig.icon && (
        <i className={`bi ${styleConfig.icon}`} style={{ fontSize: '0.85em' }} />
      )}
      <span>{displayLabel}</span>
    </span>
  )
}
