import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Navbar.css';

const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  const candidateLinks = [
    { to: '/candidate/dashboard', label: 'Dashboard' },
    { to: '/candidate/jobs', label: 'Browse Jobs' },
    { to: '/candidate/profile', label: 'Profile' },
  ];

  const recruiterLinks = [
    { to: '/recruiter/dashboard', label: 'Dashboard' },
    { to: '/recruiter/post-job', label: 'Postings' },
  ];

  const navLinks = user?.role === 'CANDIDATE'
    ? candidateLinks
    : user?.role === 'RECRUITER'
      ? recruiterLinks
      : [];

  const primaryAction = user?.role === 'CANDIDATE'
    ? { to: '/candidate/generate-resume', label: 'Generate Resume' }
    : null;

  const secondaryAction = user?.role === 'CANDIDATE'
    ? { to: '/candidate/jobs', label: 'Browse Roles' }
    : null;

  const userInitial = user?.email?.[0]?.toUpperCase() || '?';
  const roleBadge = user?.role === 'CANDIDATE' ? 'Candidate' : user?.role === 'RECRUITER' ? 'Recruiter' : '';

  return (
    <header className="navbar">
      <div className="navbar-shell">
        <div className="brand-cluster">
          <Link to="/" className="brand-mark" aria-label="ATS Intelligence home">
            <span className="brand-glow" />
            <span className="brand-text">ATS Intelligence</span>
          </Link>
        </div>

        {user && (
          <nav className="nav-links" aria-label="Primary navigation">
            {navLinks.map((link) => (
              <Link key={link.to} to={link.to} className="nav-link">
                {link.label}
              </Link>
            ))}
          </nav>
        )}

        {user ? (
          <div className="nav-actions">
            {secondaryAction && (
              <Link to={secondaryAction.to} className="btn btn--ghost nav-btn">
                {secondaryAction.label}
              </Link>
            )}
            {primaryAction && (
              <Link to={primaryAction.to} className="btn btn--primary nav-btn">
                {primaryAction.label}
              </Link>
            )}
            <div className="user-chip">
              <span className="user-avatar">{userInitial}</span>
              <div className="user-meta">
                <span className="user-email">{user.email}</span>
                <span className="user-role">{roleBadge}</span>
              </div>
              <button onClick={logout} className="logout-pill" aria-label="Logout">
                Logout
              </button>
            </div>
          </div>
        ) : (
          <div className="nav-actions">
            <Link to="/login" className="btn btn--ghost nav-btn">Login</Link>
            <Link to="/register" className="btn btn--primary nav-btn">Register</Link>
          </div>
        )}
      </div>
    </header>
  );
};

export default Navbar;
