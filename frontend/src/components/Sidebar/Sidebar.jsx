import { NavLink } from 'react-router-dom'
import UserCard from '../UserCard/UserCard'

const links = [
  { to: '/dashboard', icon: 'bi-grid-1x2-fill', label: 'Dashboard' },
  { to: '/projects',  icon: 'bi-folder-fill',   label: 'Projects'   },
  { to: '/issues',    icon: 'bi-bug-fill',       label: 'Reported Issues' },
]

export default function Sidebar({ open, onClose, onLogout }) {
  return (
    <>
      <aside className={`app-sidebar ${open ? 'is-open' : ''}`}>
        <div className="sidebar-brand">
          <img src="/logo.png" alt="BugForge Logo" style={{ height: 80, objectFit: 'contain' }} />
          <button className="btn-close d-lg-none" onClick={onClose} aria-label="Close menu" style={{ marginLeft: 'auto' }} />
        </div>

        <nav className="sidebar-nav">
          <p className="sidebar-section-label">Navigation</p>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              onClick={onClose}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <i className={`bi ${link.icon}`} />
              <span>{link.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <p className="sidebar-section-label">Account</p>
          <UserCard onLogout={onLogout} />
        </div>
      </aside>
      {open && (
        <button
          className="sidebar-backdrop d-lg-none"
          onClick={onClose}
          aria-label="Close navigation"
        />
      )}
    </>
  )
}
