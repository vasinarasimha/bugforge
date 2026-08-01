import UserCard from '../UserCard/UserCard'

export default function Navbar({ title, onMenu }) {
  const today = new Intl.DateTimeFormat('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  }).format(new Date())

  return (
    <header className="top-navbar">
      <div className="d-flex align-items-center gap-3">
        <button
          className="btn btn-light border d-lg-none"
          onClick={onMenu}
          aria-label="Open menu"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--border)', color: 'var(--text-secondary)', borderRadius: 'var(--r-sm)', width: 36, height: 36, placeItems: 'center' }}
        >
          <i className="bi bi-list fs-5" />
        </button>
        <div>
          <h1>{title}</h1>
          <p>{today}</p>
        </div>
      </div>

      <div className="navbar-actions">
        <button className="icon-button position-relative" aria-label="Notifications">
          <i className="bi bi-bell" />
          <span className="notification-dot" />
        </button>
        <UserCard compact />
      </div>
    </header>
  )
}
