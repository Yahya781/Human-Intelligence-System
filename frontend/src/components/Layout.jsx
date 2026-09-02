import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/',         icon: '🏠', label: 'Dashboard' },
  { to: '/upload-cv',icon: '📄', label: 'Upload CV' },
  { to: '/create-job',icon: '💼', label: 'Create Job' },
  { to: '/matches',  icon: '🎯', label: 'View Matches' },
  { to: '/candidates',icon: '👥', label: 'Candidates' },
  { to: '/jobs',     icon: '📋', label: 'Jobs' },
]

export default function Layout({ children }) {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          HR <span>Management</span>
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `nav-link ${isActive ? 'active' : ''}`
              }
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}
