import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { recruiterService } from '../../services/recruiter.service';
import './PostJob.css';

const EditJob: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const [generatingCompetencies, setGeneratingCompetencies] = useState(false);

  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [description, setDescription] = useState('');
  const [competencies, setCompetencies] = useState('');
  const [status, setStatus] = useState<'ACTIVE' | 'CLOSED'>('ACTIVE');

  useEffect(() => {
    loadJob();
  }, [id]);

  const loadJob = async () => {
    if (!id) return;
    
    try {
      const jobs = await recruiterService.getJobs();
      const job = jobs.find(j => j.id === parseInt(id));
      
      if (!job) {
        setError('Job not found');
        return;
      }

      setTitle(job.title);
      setCompany(job.company);
      setDescription(job.description);
      setCompetencies((job.required_competencies || []).join(', '));
      setStatus(job.status || 'ACTIVE');
    } catch (err: any) {
      setError('Failed to load job');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!title || !company || !description || !competencies) {
      setError('All fields are required');
      return;
    }

    if (!id) return;

    setSaving(true);
    setError('');

    try {
      const competenciesArray = competencies
        .split(',')
        .map(c => c.trim())
        .filter(c => c.length > 0);

      await recruiterService.updateJob(parseInt(id), {
        title,
        company,
        description,
        required_competencies: competenciesArray,
        status,
      });

      navigate('/recruiter/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to update job');
    } finally {
      setSaving(false);
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

  const handleDelete = async () => {
    if (!id) return;
    
    if (!window.confirm('Are you sure you want to delete this job? This action cannot be undone.')) {
      return;
    }

    setDeleting(true);
    setError('');

    try {
      await recruiterService.deleteJob(parseInt(id));
      navigate('/recruiter/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to delete job');
      setDeleting(false);
    }
  };

  if (loading) {
    return <div className="post-job-container">Loading...</div>;
  }

  return (
    <div className="post-job-container">
      <h1>Edit Job</h1>

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

        <div className="form-group">
          <label htmlFor="status">Status *</label>
          <select
            id="status"
            value={status}
            onChange={(e) => setStatus(e.target.value as 'ACTIVE' | 'CLOSED')}
            required
          >
            <option value="ACTIVE">Active</option>
            <option value="CLOSED">Closed</option>
          </select>
        </div>

        <div className="form-actions">
          <button
            type="button"
            onClick={handleDelete}
            className="btn-danger"
            disabled={saving || deleting}
          >
            {deleting ? 'Deleting...' : 'Delete Job'}
          </button>
          <div style={{ flex: 1 }}></div>
          <button
            type="button"
            onClick={() => navigate('/recruiter/dashboard')}
            className="btn btn-secondary-light"
            disabled={saving || deleting}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving || deleting}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default EditJob;
