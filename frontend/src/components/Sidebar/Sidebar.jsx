import { NavLink } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import UserCard from '../UserCard/UserCard'

const baseLinks = [
  { to: '/dashboard', icon: 'bi-grid-1x2-fill', label: 'Dashboard' },
  { to: '/analytics', icon: 'bi-graph-up-arrow', label: 'Analytics' },
  { to: '/projects', icon: 'bi-folder-fill', label: 'Projects' },
  { to: '/sprints', icon: 'bi-clock', label: 'Sprints' },
  { to: '/issues', icon: 'bi-bug-fill', label: 'Reported Issues' },
]

export default function Sidebar({ open, onClose, onLogout }) {
  const { user } = useAuth()
  const isSuperAdmin = user?.role === 'Super Admin' || user?.roles?.some((r) => r.name === 'Super Admin')
  const isCompanyAdmin = !isSuperAdmin && (user?.role === 'Admin' || user?.roles?.some((r) => r.name === 'Admin'))

  return (
    <>
      <aside className={`app-sidebar ${open ? 'is-open' : ''}`}>
        <div className="sidebar-brand">
          <div className="brand-icon-wrap">
            <img src="/logo.png" alt="BugForge logo" height="28" />
          </div>
          <div className="sidebar-brand-text">
            <strong>BugForge</strong>
            <span>{isSuperAdmin ? 'Platform Management' : 'Defect Intelligence'}</span>
          </div>
          <button
            className="btn-close d-lg-none"
            onClick={onClose}
            aria-label="Close menu"
            style={{ marginLeft: 'auto' }}
          />
        </div>

        <nav className="sidebar-nav">
          {isSuperAdmin ? (
            <>
              <p className="sidebar-section-label">Platform Control</p>
              <NavLink
                to="/dashboard"
                onClick={onClose}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <i className="bi bi-grid-1x2-fill" />
                <span>Platform Dashboard</span>
              </NavLink>
              <NavLink
                to="/super-admin/companies"
                onClick={onClose}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <i className="bi bi-buildings-fill" />
                <span>Companies</span>
              </NavLink>
              <NavLink
                to="/analytics"
                onClick={onClose}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <i className="bi bi-graph-up-arrow" />
                <span>Platform Analytics</span>
              </NavLink>
              <NavLink
                to="/super-admin/customization-requests"
                onClick={onClose}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <i className="bi bi-envelope-paper-fill" />
                <span>Customization Requests</span>
              </NavLink>
            </>
          ) : (
            <>
              <p className="sidebar-section-label">Navigation</p>
              <NavLink
                to="/dashboard"
                onClick={onClose}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <i className="bi bi-grid-1x2-fill" />
                <span>Dashboard</span>
              </NavLink>
              <NavLink
                to="/analytics"
                onClick={onClose}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <i className="bi bi-graph-up-arrow" />
                <span>Analytics</span>
              </NavLink>
              <NavLink
                to="/projects"
                onClick={onClose}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <i className="bi bi-folder-fill" />
                <span>Projects</span>
              </NavLink>
              <NavLink
                to="/sprints"
                onClick={onClose}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <i className="bi bi-clock" />
                <span>Sprints</span>
              </NavLink>
              <NavLink
                to="/issues"
                onClick={onClose}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <i className="bi bi-bug-fill" />
                <span>Reported Issues</span>
              </NavLink>

              {/* Company Admin Section */}
              {isCompanyAdmin && (
                <>
                  <p className="sidebar-section-label mt-3">Company Management</p>
                  <NavLink
                    to="/company/profile"
                    onClick={onClose}
                    className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                  >
                    <i className="bi bi-building-gear" />
                    <span>Company Profile & Settings</span>
                  </NavLink>
                  <NavLink
                    to="/company/customization-requests"
                    onClick={onClose}
                    className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                  >
                    <i className="bi bi-sliders2" />
                    <span>Customization Requests</span>
                  </NavLink>
                  <NavLink
                    to="/employees"
                    onClick={onClose}
                    className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                  >
                    <i className="bi bi-people-fill" />
                    <span>Employee Management</span>
                  </NavLink>
                  <NavLink
                    to="/teams"
                    onClick={onClose}
                    className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                  >
                    <i className="bi bi-diagram-3-fill" />
                    <span>Team Management</span>
                  </NavLink>
                </>
              )}
            </>
          )}

          {/* Personal Account Section */}
          <p className="sidebar-section-label mt-3">Personal</p>
          <NavLink
            to="/profile"
            onClick={onClose}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          >
            <i className="bi bi-person-circle" />
            <span>My Profile</span>
          </NavLink>
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
