import { useAuth } from '../../hooks/useAuth'

const initials = (name) => name?.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase() || 'BF'

export default function UserCard({ onLogout, compact = false }) {
  const { user } = useAuth()
  return (
    <div className={`user-card ${compact ? 'user-card-compact' : ''}`}>
      <div className="avatar avatar-primary">{initials(user?.full_name)}</div>
      {!compact && <div className="user-card-copy"><strong>{user?.full_name || 'Reporter'}</strong><span>{user?.role || 'Reporter'}</span><small>{user?.email || 'reporter@bugforge.com'}</small></div>}
      {!compact && <button className="btn btn-light btn-sm logout-btn" onClick={onLogout}><i className="bi bi-box-arrow-right" /> Logout</button>}
    </div>
  )
}
