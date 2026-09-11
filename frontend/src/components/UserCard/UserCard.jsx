import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

const initials = (name) =>
  name
    ?.split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase() || 'BF'

export default function UserCard({ onLogout, compact = false }) {
  const { user } = useAuth()

  if (compact) {
    return (
      <Link to="/profile" className="user-card user-card-compact" title="View Profile" style={{ textDecoration: 'none' }}>
        <div className="avatar avatar-primary">{initials(user?.full_name)}</div>
      </Link>
    )
  }

  return (
    <div className="user-card">
      <Link to="/profile" className="user-card-link" title="View Profile">
        <div className="avatar avatar-primary">{initials(user?.full_name)}</div>
        <div className="user-card-copy">
          <strong title={user?.full_name || 'Staff Member'}>{user?.full_name || 'Staff Member'}</strong>
          <span>{user?.role || (user?.roles?.[0]?.name) || 'Developer'}</span>
          <small title={user?.email || 'user@bugforge.com'}>{user?.email || 'user@bugforge.com'}</small>
        </div>
      </Link>
      {onLogout && (
        <button
          type="button"
          className="logout-btn"
          onClick={(e) => {
            e.stopPropagation()
            onLogout()
          }}
          title="Sign out"
          aria-label="Sign out"
        >
          <i className="bi bi-box-arrow-right" />
        </button>
      )}
    </div>
  )
}
