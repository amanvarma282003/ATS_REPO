import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { useAuth } from './contexts/AuthContext';
import Navbar from './components/common/Navbar';
import PrivateRoute from './components/common/PrivateRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import CandidateDashboard from './pages/candidate/CandidateDashboard';
import ProfilePage from './pages/candidate/ProfilePage';
import GenerateResume from './pages/candidate/GenerateResume';
import BrowseJobs from './pages/candidate/BrowseJobs';
import RecruiterDashboard from './pages/recruiter/RecruiterDashboard';
import PostJob from './pages/recruiter/PostJob';
import EditJob from './pages/recruiter/EditJob';
import ApplicationsPage from './pages/recruiter/ApplicationsPage';
import './App.css';

const HomePage: React.FC = () => {
  const { user } = useAuth();

  if (user) {
    // Redirect based on role
    const redirectPath = user.role === 'CANDIDATE' ? '/candidate/dashboard' : '/recruiter/dashboard';
    return <Navigate to={redirectPath} replace />;
  }

  return (
    <div className="home-container">
      <div className="home-hero">
        <h1>ATS + Resume Intelligence Platform</h1>
        <p>Bidirectional feedback loop for candidates and recruiters</p>
        <div className="home-actions">
          <Link to="/login" className="btn-primary">Login</Link>
          <Link to="/register" className="btn-secondary">Register</Link>
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app">
          <Navbar />
          <div className="main-content">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/* Candidate Routes */}
              <Route
                path="/candidate/dashboard"
                element={
                  <PrivateRoute allowedRole="CANDIDATE">
                    <CandidateDashboard />
                  </PrivateRoute>
                }
              />
              <Route
                path="/candidate/profile"
                element={
                  <PrivateRoute allowedRole="CANDIDATE">
                    <ProfilePage />
                  </PrivateRoute>
                }
              />
              <Route
                path="/candidate/generate-resume"
                element={
                  <PrivateRoute allowedRole="CANDIDATE">
                    <GenerateResume />
                  </PrivateRoute>
                }
              />
              <Route
                path="/candidate/jobs"
                element={
                  <PrivateRoute allowedRole="CANDIDATE">
                    <BrowseJobs />
                  </PrivateRoute>
                }
              />

              {/* Recruiter Routes */}
              <Route
                path="/recruiter/dashboard"
                element={
                  <PrivateRoute allowedRole="RECRUITER">
                    <RecruiterDashboard />
                  </PrivateRoute>
                }
              />
              <Route
                path="/recruiter/post-job"
                element={
                  <PrivateRoute allowedRole="RECRUITER">
                    <PostJob />
                  </PrivateRoute>
                }
              />
              <Route
                path="/recruiter/edit-job/:id"
                element={
                  <PrivateRoute allowedRole="RECRUITER">
                    <EditJob />
                  </PrivateRoute>
                }
              />
              <Route
                path="/recruiter/applications/:jobId"
                element={
                  <PrivateRoute allowedRole="RECRUITER">
                    <ApplicationsPage />
                  </PrivateRoute>
                }
              />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
