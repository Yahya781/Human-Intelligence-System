import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

const navItems = [
  { to: '/',         icon: '🏠', label: 'Dashboard' },
  { to: '/upload-cv',icon: '📄', label: 'Upload CV' },
  { to: '/create-job',icon: '💼', label: 'Create Job' },
  { to: '/matches',  icon: '🎯', label: 'View Matches' },
  { to: '/candidates',icon: '👥', label: 'Candidates' },
  { to: '/jobs',     icon: '📋', label: 'Jobs' },
]

export default function Layout({ children }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  // Close the drawer whenever the route changes (after tapping a link)
  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  return (
    <div className="app-layout">
      <header className="mobile-topbar">
        <button
          className="menu-toggle"
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          onClick={() => setMenuOpen(o => !o)}
        >
          {menuOpen ? '✕' : '☰'}
        </button>
        <div className="mobile-title">HR <span>Management</span></div>
      </header>

      {menuOpen && (
        <div className="sidebar-overlay" onClick={() => setMenuOpen(false)} />
      )}

      <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
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
