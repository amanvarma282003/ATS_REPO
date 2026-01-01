import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { recruiterService } from '../../services/recruiter.service';
import './PostJob.css';

const PostJob: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [generatingCompetencies, setGeneratingCompetencies] = useState(false);

  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [description, setDescription] = useState('');
  const [competencies, setCompetencies] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!title || !company || !description || !competencies) {
      setError('All fields are required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const competenciesArray = competencies
        .split(',')
        .map(c => c.trim())
        .filter(c => c.length > 0);

      await recruiterService.createJob({
        title,
        company,
        description,
        required_competencies: competenciesArray,
      });

      navigate('/recruiter/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to create job');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCompetencies = async () => {
    if (!description.trim()) {
      setError('Please enter a job description first');
      return;
    }

    setGeneratingCompetencies(true);
    setError('');

    try {
      const parsed = await recruiterService.parseJobDescription(description);
      // Combine required and optional skills, removing duplicates
      const allSkills = [...parsed.required_skills, ...parsed.optional_skills];
      const uniqueSkills = Array.from(new Set(allSkills));
      const skillsList = uniqueSkills.join(', ');
      setCompetencies(skillsList);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to extract competencies');
    } finally {
      setGeneratingCompetencies(false);
    }
  };

  return (
    <div className="post-job-container">
      <h1>Post New Job</h1>

      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit} className="job-form">
        <div className="form-group">
          <label htmlFor="title">Job Title *</label>
          <input
            type="text"
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Senior Software Engineer"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="company">Company *</label>
          <input
            type="text"
            id="company"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g., Tech Corp"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="description">Job Description *</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the role, responsibilities, and requirements..."
            rows={10}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="competencies">Required Competencies (comma-separated) *</label>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
            <input
              type="text"
              id="competencies"
              value={competencies}
              onChange={(e) => setCompetencies(e.target.value)}
              placeholder="e.g., Python, Django, REST API, PostgreSQL"
              required
              style={{ flex: 1 }}
            />
            <button
              type="button"
              onClick={handleGenerateCompetencies}
              className="btn btn-secondary-light"
              disabled={generatingCompetencies || !description.trim()}
              style={{ whiteSpace: 'nowrap' }}
            >
              {generatingCompetencies ? 'Generating...' : 'Generate'}
            </button>
          </div>
          <small className="help-text">
            Enter skills, technologies, and competencies separated by commas
          </small>
        </div>

        <div className="form-actions">
          <button
            type="button"
            onClick={() => navigate('/recruiter/dashboard')}
            className="btn btn-secondary-light"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? 'Posting...' : 'Post Job'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default PostJob;
