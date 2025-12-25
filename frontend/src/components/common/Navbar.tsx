import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Navbar.css';

const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          ATS Intelligence
        </Link>
        
        {user && (
          <div className="navbar-menu">
            <span className="navbar-user">
              {user.email} ({user.role})
            </span>
            {user.role === 'CANDIDATE' && (
              <>
                <Link to="/candidate/dashboard" className="navbar-link">Dashboard</Link>
                <Link to="/candidate/profile" className="navbar-link">Profile</Link>
                <Link to="/candidate/generate-resume" className="navbar-link">Generate Resume</Link>
              </>
            )}
            {user.role === 'RECRUITER' && (
              <>
                <Link to="/recruiter/dashboard" className="navbar-link">Dashboard</Link>
                <Link to="/recruiter/jobs" className="navbar-link">Jobs</Link>
                <Link to="/recruiter/applications" className="navbar-link">Applications</Link>
              </>
            )}
            <button onClick={logout} className="navbar-logout">
              Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
