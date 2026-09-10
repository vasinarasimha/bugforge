import React, { useState, useEffect } from 'react'
import UserCard from '../UserCard/UserCard'
import NotificationDropdown from './NotificationDropdown'
import { notificationApi } from '../../api/notificationApi'

export default function Navbar({ title, onMenu }) {
  const [unreadCount, setUnreadCount] = useState(0)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)

  const today = new Intl.DateTimeFormat('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  }).format(new Date())

  // Load unread count on mount and poll periodically
  useEffect(() => {
    let mounted = true
    const fetchCount = async () => {
      try {
        const data = await notificationApi.getUnreadCount()
        if (mounted) {
          setUnreadCount(data.unread_count || 0)
        }
      } catch {
        // Silently handle if user session expired or not authenticated
      }
    }

    fetchCount()
    const interval = setInterval(fetchCount, 30000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  const toggleDropdown = () => {
    setIsDropdownOpen((prev) => !prev)
  }

  return (
    <header className="top-navbar">
      <div className="d-flex align-items-center gap-3">
        <button
          className="btn btn-light border d-lg-none"
          onClick={onMenu}
          aria-label="Open menu"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--border)', color: 'var(--text-secondary)', borderRadius: 'var(--r-sm)', width: 36, height: 36, display: 'grid', placeItems: 'center' }}
        >
          <i className="bi bi-list fs-5" />
        </button>
        <div>
          <h1>{title}</h1>
          <p>{today}</p>
        </div>
      </div>

      <div className="navbar-actions">
        <div className="notification-wrapper">
          <button
            className="icon-button position-relative"
            aria-label="Notifications"
            onClick={toggleDropdown}
            title={unreadCount > 0 ? `${unreadCount} unread notification(s)` : 'Notifications'}
          >
            <i className="bi bi-bell" />
            {unreadCount > 0 && <span className="notification-dot" />}
          </button>
          <NotificationDropdown
            isOpen={isDropdownOpen}
            onClose={() => setIsDropdownOpen(false)}
            onCountChange={(count) => setUnreadCount(count)}
          />
        </div>
        <UserCard compact />
      </div>
    </header>
  )
}
