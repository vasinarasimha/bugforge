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
      <Link to="/profile" className="d-flex align-items-center gap-2 text-decoration-none text-reset flex-grow-1" title="View Profile">
        <div className="avatar avatar-primary">{initials(user?.full_name)}</div>
        <div className="user-card-copy">
          <strong>{user?.full_name || 'Staff Member'}</strong>
          <span>{user?.role || (user?.roles?.[0]?.name) || 'Developer'}</span>
          <small>{user?.email || 'user@bugforge.com'}</small>
        </div>
      </Link>
      {onLogout && (
        <button className="btn btn-light btn-sm logout-btn" onClick={onLogout} title="Sign out">
          <i className="bi bi-box-arrow-right" />
        </button>
      )}
    </div>
  )
}
