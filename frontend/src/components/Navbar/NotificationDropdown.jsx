import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { notificationApi } from '../../api/notificationApi'

function formatTimeAgo(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const seconds = Math.floor((now - date) / 1000)
  if (seconds < 60) return 'Just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString()
}

function getNotificationIcon(type) {
  switch (type) {
    case 'FEATURE_REQUEST_SUBMITTED':
      return { icon: 'bi-lightbulb-fill', color: '#3b82f6' }
    case 'FEATURE_ASSIGNED_TO_TEAM':
      return { icon: 'bi-people-fill', color: '#8b5cf6' }
    case 'FEATURE_ASSIGNED_TO_DEV':
      return { icon: 'bi-person-check-fill', color: '#06b6d4' }
    case 'FEATURE_READY_FOR_QA':
      return { icon: 'bi-patch-check-fill', color: '#f59e0b' }
    case 'QA_ASSIGNED':
      return { icon: 'bi-person-badge-fill', color: '#8b5cf6' }
    case 'FEATURE_QA_REWORK':
      return { icon: 'bi-arrow-repeat', color: '#ef4444' }
    case 'FEATURE_CLOSED':
      return { icon: 'bi-check-circle-fill', color: '#10b981' }
    default:
      return { icon: 'bi-bell-fill', color: '#6366f1' }
  }
}

export default function NotificationDropdown({ isOpen, onClose, onCountChange }) {
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const dropdownRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (isOpen) {
      loadNotifications()
    }
  }, [isOpen])

  // Close on outside click or Escape key
  useEffect(() => {
    if (!isOpen) return
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        onClose()
      }
    }
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  const loadNotifications = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await notificationApi.getMyNotifications(false, 30, 0)
      setNotifications(data.items || [])
      if (onCountChange) {
        onCountChange(data.unread_count || 0)
      }
    } catch (err) {
      console.error('Failed to load notifications:', err)
      setError('Unable to load notifications.')
    } finally {
      setLoading(false)
    }
  }

  const handleItemClick = async (notif) => {
    if (!notif.is_read) {
      try {
        await notificationApi.markAsRead(notif.id)
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
        )
        if (onCountChange) {
          onCountChange((prev) => Math.max(0, prev - 1))
        }
      } catch (err) {
        console.error('Failed to mark notification as read:', err)
      }
    }
    onClose()

    const isIssueNotification =
      notif.entity_type?.toLowerCase() === 'issue' ||
      notif.notification_type?.toLowerCase().includes('feature') ||
      notif.notification_type?.toLowerCase().includes('issue')
    const matchId = notif.link_url?.match(/\/issues\/(\d+)/)?.[1]
    const targetIssueId = notif.entity_id || (matchId ? Number(matchId) : null)

    if (isIssueNotification && targetIssueId) {
      navigate(`/issues/${targetIssueId}`, { state: { issueId: Number(targetIssueId) } })
    } else if (notif.link_url) {
      navigate(notif.link_url)
    } else if (targetIssueId) {
      navigate(`/issues/${targetIssueId}`, { state: { issueId: Number(targetIssueId) } })
    } else {
      navigate('/issues')
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await notificationApi.markAllAsRead()
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
      if (onCountChange) {
        onCountChange(0)
      }
    } catch (err) {
      console.error('Failed to mark all as read:', err)
    }
  }

  const handleClearRead = async () => {
    try {
      await notificationApi.clearReadNotifications(0)
      setNotifications((prev) => prev.filter((n) => !n.is_read))
    } catch (err) {
      console.error('Failed to clear read notifications:', err)
    }
  }

  if (!isOpen) return null

  const unreadCount = notifications.filter((n) => !n.is_read).length
  const hasReadNotifications = notifications.some((n) => n.is_read)

  return (
    <div
      ref={dropdownRef}
      className="notification-dropdown-panel"
      role="dialog"
      aria-label="Notifications"
    >
      {/* Header */}
      <div className="notif-dropdown-header">
        <div className="d-flex align-items-center gap-2">
          <span className="notif-title">Notifications</span>
          {unreadCount > 0 && (
            <span className="notif-badge">{unreadCount}</span>
          )}
        </div>
        <div className="d-flex align-items-center gap-2">
          {unreadCount > 0 && (
            <button
              className="notif-mark-all-btn"
              onClick={handleMarkAllRead}
              title="Mark all notifications as read"
            >
              Mark all read
            </button>
          )}
          {hasReadNotifications && (
            <button
              className="notif-clear-read-btn"
              onClick={handleClearRead}
              title="Delete read notifications"
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                fontSize: '0.75rem',
                cursor: 'pointer',
                padding: '2px 6px',
                fontWeight: 600,
                borderRadius: '4px',
              }}
              onMouseEnter={(e) => (e.target.style.color = '#ef4444')}
              onMouseLeave={(e) => (e.target.style.color = '#94a3b8')}
            >
              Clear read
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="notif-dropdown-body">
        {loading ? (
          <div className="notif-empty-state">
            <div className="spinner-border spinner-border-sm text-primary mb-2" role="status" />
            <div className="text-xs text-muted">Loading notifications…</div>
          </div>
        ) : error ? (
          <div className="notif-empty-state text-danger">
            <i className="bi bi-exclamation-triangle mb-1 fs-5" />
            <div className="text-xs">{error}</div>
          </div>
        ) : notifications.length === 0 ? (
          <div className="notif-empty-state">
            <i className="bi bi-bell-slash fs-4 text-muted mb-2" />
            <div className="notif-empty-title">No new notifications</div>
            <div className="notif-empty-sub">You're all caught up!</div>
          </div>
        ) : (
          notifications.map((n) => {
            const { icon, color } = getNotificationIcon(n.notification_type)
            return (
              <div
                key={n.id}
                className={`notif-item ${n.is_read ? 'is-read' : 'is-unread'}`}
                onClick={() => handleItemClick(n)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleItemClick(n)
                }}
              >
                <div
                  className="notif-icon-bubble"
                  style={{ color, background: `${color}18` }}
                >
                  <i className={`bi ${icon}`} />
                </div>
                <div className="notif-item-content">
                  <div className="notif-item-msg" title={n.message}>
                    {n.message}
                  </div>
                  <div className="notif-item-meta">
                    <span className="notif-item-time">{formatTimeAgo(n.created_at)}</span>
                  </div>
                </div>
                {!n.is_read && <span className="notif-item-unread-pip" />}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
