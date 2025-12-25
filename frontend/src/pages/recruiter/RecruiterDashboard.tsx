import React, { useState, useEffect } from 'react';
import { recruiterService } from '../../services/recruiter.service';
import { JobDescription } from '../../types';
import { Link } from 'react-router-dom';
import './RecruiterDashboard.css';

const RecruiterDashboard: React.FC = () => {
  const [jobs, setJobs] = useState<JobDescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      const data = await recruiterService.getJobs();
      setJobs(data);
    } catch (err: any) {
      setError('Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="recruiter-container">Loading...</div>;
  }

  return (
    <div className="recruiter-container">
      <div className="recruiter-header">
        <h1>Recruiter Dashboard</h1>
        <Link to="/recruiter/post-job" className="btn-primary">
          Post New Job
        </Link>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="stats-section">
        <div className="stat-card">
          <h3>Total Jobs</h3>
          <p className="stat-number">{jobs.length}</p>
        </div>
        <div className="stat-card">
          <h3>Active Listings</h3>
          <p className="stat-number">{jobs.filter(j => j.is_active).length}</p>
        </div>
      </div>

      <div className="jobs-section">
        <h2>Posted Jobs</h2>
        {jobs.length === 0 ? (
          <div className="empty-state">
            <p>No jobs posted yet. Create your first job posting!</p>
          </div>
        ) : (
          <div className="jobs-grid">
            {jobs.map((job) => (
              <div key={job.id} className="job-card">
                <div className="job-header">
                  <h3>{job.title}</h3>
                  <span className={`job-status ${job.is_active ? 'active' : 'inactive'}`}>
                    {job.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p className="job-company">{job.company}</p>
                <p className="job-description">{job.description.substring(0, 150)}...</p>
                
                <div className="job-competencies">
                  <strong>Required Competencies:</strong>
                  <div className="competencies-list">
                    {job.required_competencies.slice(0, 5).map((comp, idx) => (
                      <span key={idx} className="competency-badge">{comp}</span>
                    ))}
                    {job.required_competencies.length > 5 && (
                      <span className="competency-badge">+{job.required_competencies.length - 5} more</span>
                    )}
                  </div>
                </div>

                <div className="job-actions">
                  <Link to={`/recruiter/applications/${job.id}`} className="btn-secondary">
                    View Applications
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RecruiterDashboard;
