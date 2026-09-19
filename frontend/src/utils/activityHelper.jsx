import React from 'react'

/**
 * Fields that must NEVER be displayed in the UI activity log/timeline.
 */
export const IGNORED_TIMELINE_FIELDS = new Set([
  'id',
  'issue_key',
  'company_id',
  'company',
  'requesting_company_id',
  'requesting_company',
  'ai_root_cause_session_id',
  'developer_fixed_at',
  'qa_verified_at',
  'qa_verified_by_id',
  'created_at',
  'updated_at',
  'is_deleted',
  'embedding_vector',
])

export const isIgnoredTimelineField = (field) => {
  if (!field) return true
  const normalized = String(field).toLowerCase().trim()
  return IGNORED_TIMELINE_FIELDS.has(normalized)
}

/**
 * Clean field name mapping: maps database/API internal names to human-readable labels.
 */
export const FIELD_LABELS = {
  status_id: 'status',
  priority_id: 'priority',
  severity_id: 'severity',
  project_id: 'project',
  assigned_to: 'assignee',
  assignee_id: 'assignee',
  reporter_id: 'reporter',
  category_id: 'category',
  module_id: 'module',
  sprint_id: 'sprint',
  issue_type: 'issue type',
  title: 'title',
  description: 'description',
  reproduction_steps: 'reproduction steps',
  expected_behavior: 'expected behavior',
  actual_behavior: 'actual behavior',
  root_cause: 'root cause',
  resolution: 'resolution',
  environment: 'environment',
  browser: 'browser',
  operating_system: 'operating system',
  attachment_path: 'attachment',
  is_active: 'active status'
}

/**
 * Returns a user-friendly field label from a raw database field name.
 */
export const getFieldLabel = (field) => {
  if (!field) return 'field'
  const normalized = String(field).toLowerCase().trim()
  if (IGNORED_TIMELINE_FIELDS.has(normalized)) return ''
  if (FIELD_LABELS[normalized]) return FIELD_LABELS[normalized]
  // Fallback: strip _id suffix and convert underscores to spaces
  return normalized.replace(/_id$/i, '').replace(/_/g, ' ')
}

/**
 * Resolves a field value, checking if it's a numeric ID that can be mapped to a human-readable name.
 */
export const resolveFieldValue = (field, value, lookups = {}) => {
  if (value === null || value === undefined || value === 'None' || value === '' || value === 'null') {
    return null
  }

  const valStr = String(value).trim()
  const isNumericId = /^\d+$/.test(valStr)
  const normalizedField = String(field || '').toLowerCase().trim()

  if (isNumericId) {
    // Status ID
    if (normalizedField === 'status_id' || normalizedField === 'status') {
      const match = lookups.statuses?.find(s => String(s.id) === valStr)
      if (match?.name) return match.name
    }
    // Priority ID
    if (normalizedField === 'priority_id' || normalizedField === 'priority') {
      const match = lookups.priorities?.find(p => String(p.id) === valStr)
      if (match?.name) return match.name
    }
    // Severity ID
    if (normalizedField === 'severity_id' || normalizedField === 'severity') {
      const match = lookups.severities?.find(s => String(s.id) === valStr)
      if (match?.name) return match.name
    }
    // Project ID
    if (normalizedField === 'project_id' || normalizedField === 'project') {
      const match = (lookups.allProjects || lookups.projects)?.find(p => String(p.id) === valStr)
      if (match?.name) return match.name
    }
    // Category ID
    if (normalizedField === 'category_id' || normalizedField === 'category') {
      const match = lookups.categories?.find(c => String(c.id) === valStr)
      if (match?.name) return match.name
    }
    // Module ID
    if (normalizedField === 'module_id' || normalizedField === 'module') {
      const match = lookups.modules?.find(m => String(m.id) === valStr)
      if (match?.name) return match.name
    }
    // Assignee / User / Reporter ID
    if (
      normalizedField === 'assigned_to' ||
      normalizedField === 'assignee_id' ||
      normalizedField === 'assignee' ||
      normalizedField === 'reporter_id' ||
      normalizedField === 'reporter' ||
      normalizedField === 'user_id'
    ) {
      const match = (lookups.allUsers || lookups.users)?.find(u => String(u.id) === valStr)
      if (match?.full_name) return match.full_name
      if (match?.email) return match.email
    }
    // Sprint ID
    if (normalizedField === 'sprint_id' || normalizedField === 'sprint') {
      const match = (lookups.projectSprints || lookups.sprints)?.find(sp => String(sp.id) === valStr)
      if (match?.name) return match.name
    }
  }

  return valStr
}

/**
 * Returns plain text sentence for activity log.
 */
export const formatActivitySentenceText = (event, lookups = {}) => {
  const rawField = event.field_name
  if (isIgnoredTimelineField(rawField)) return null
  const user = event.user_name || 'System'
  const fieldLabel = getFieldLabel(rawField)
  const oldVal = resolveFieldValue(rawField, event.old_value, lookups)
  const newVal = resolveFieldValue(rawField, event.new_value, lookups)

  if (['description', 'reproduction steps', 'expected behavior', 'actual behavior', 'root cause', 'resolution'].includes(fieldLabel)) {
    if (!oldVal && newVal) return `${user} added ${fieldLabel}.`
    if (oldVal && !newVal) return `${user} removed ${fieldLabel}.`
    return `${user} updated ${fieldLabel}.`
  }

  if (fieldLabel === 'title') {
    if (oldVal && newVal) return `${user} changed title from "${oldVal}" to "${newVal}".`
    if (newVal) return `${user} set title to "${newVal}".`
    return `${user} changed title.`
  }

  if (oldVal && newVal) {
    return `${user} changed ${fieldLabel} from ${oldVal} to ${newVal}.`
  }
  if (!oldVal && newVal) {
    return `${user} set ${fieldLabel} to ${newVal}.`
  }
  if (oldVal && !newVal) {
    return `${user} cleared ${fieldLabel} (was ${oldVal}).`
  }
  return `${user} changed ${fieldLabel}.`
}

/**
 * React Component that renders a beautifully formatted, natural activity sentence.
 */
export function ActivitySentence({ event, lookups = {} }) {
  const rawField = event.field_name
  if (isIgnoredTimelineField(rawField)) return null
  const user = event.user_name || 'System'
  const fieldLabel = getFieldLabel(rawField)
  const oldVal = resolveFieldValue(rawField, event.old_value, lookups)
  const newVal = resolveFieldValue(rawField, event.new_value, lookups)

  // Long text / documentation fields
  if (['description', 'reproduction steps', 'expected behavior', 'actual behavior', 'root cause', 'resolution'].includes(fieldLabel)) {
    if (!oldVal && newVal) {
      return <span><strong>{user}</strong> added <strong>{fieldLabel}</strong>.</span>
    }
    if (oldVal && !newVal) {
      return <span><strong>{user}</strong> removed <strong>{fieldLabel}</strong>.</span>
    }
    return <span><strong>{user}</strong> updated <strong>{fieldLabel}</strong>.</span>
  }

  // Title field
  if (fieldLabel === 'title') {
    if (oldVal && newVal) {
      return <span><strong>{user}</strong> changed title from <em>"{oldVal}"</em> to <em>"{newVal}"</em>.</span>
    }
    if (newVal) {
      return <span><strong>{user}</strong> set title to <em>"{newVal}"</em>.</span>
    }
    return <span><strong>{user}</strong> changed title.</span>
  }

  // Standard fields
  if (oldVal && newVal) {
    return (
      <span>
        <strong>{user}</strong> changed <strong>{fieldLabel}</strong> from <span className="badge bg-secondary text-white mx-1">{oldVal}</span> to <span className="badge bg-primary text-white mx-1">{newVal}</span>.
      </span>
    )
  }

  if (!oldVal && newVal) {
    return (
      <span>
        <strong>{user}</strong> set <strong>{fieldLabel}</strong> to <span className="badge bg-primary text-white mx-1">{newVal}</span>.
      </span>
    )
  }

  if (oldVal && !newVal) {
    return (
      <span>
        <strong>{user}</strong> cleared <strong>{fieldLabel}</strong> (was <span className="badge bg-secondary text-white mx-1">{oldVal}</span>).
      </span>
    )
  }

  return <span><strong>{user}</strong> changed <strong>{fieldLabel}</strong>.</span>
}
