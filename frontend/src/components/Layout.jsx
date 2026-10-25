import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS, label } from '../utils';

export default function Layout() {
  const { user, logout, isAdmin, isStaff } = useAuth();
  const location = useLocation();
  const [unread, setUnread] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = () => api.get('/notifications/unread_count/').then((r) => alive && setUnread(r.data.count)).catch(() => {});
    load();
    window.addEventListener('notifications:changed', load);
    const timer = setInterval(load, 60000);
    return () => { alive = false; clearInterval(timer); window.removeEventListener('notifications:changed', load); };
  }, [location.pathname]);

  useEffect(() => setMenuOpen(false), [location.pathname]);

  const link = (to, text, end) => (
    <NavLink to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>{text}</NavLink>
  );

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
        <div className="brand">DeskPilot</div>
        <div className="brand-sub">IT Helpdesk &amp; Assets</div>
        <nav className="nav flex-column">
          {link('/', 'Dashboard', true)}
          {link('/tickets', isStaff ? 'Tickets' : 'My tickets')}
          {link('/assets', isStaff ? 'Assets' : 'My assets')}
          {link('/notifications', unread ? `Notifications (${unread})` : 'Notifications')}
          {isAdmin && link('/users', 'Users')}
          {isAdmin && link('/settings', 'Departments & categories')}
        </nav>
        <div className="sidebar-bottom">
          <div className="fw-semibold">{user.full_name}</div>
          <div className="small text-white-50">{label(ROLE_LABELS, user.role)}</div>
          <button className="btn btn-outline-light btn-sm mt-3" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <button className="btn btn-sm btn-outline-secondary menu-btn" onClick={() => setMenuOpen((v) => !v)} aria-label="Toggle menu">Menu</button>
          <span className="text-muted small d-none d-sm-inline">{user.department_name || 'No department'}</span>
          <div className="d-flex align-items-center gap-3 ms-auto">
            <Link to="/notifications" className="bell" aria-label={`${unread} unread notifications`}>
              Notifications{unread > 0 && <span className="badge text-bg-danger ms-1">{unread}</span>}
            </Link>
            <span className="small">{user.email}</span>
          </div>
        </header>
        <div className="page-content"><Outlet /></div>
      </main>
    </div>
  );
}
