import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { candidateService } from '../../services/candidate.service';
import { resumeService } from '../../services/resume.service';
import {
  CandidateProfile,
  CandidateSkill,
  Application,
  GeneratedResumeRecord,
} from '../../types';
import './CandidateDashboard.css';

const ACTIVE_APPLICATION_STATUSES: Array<Application['status']> = [
  'PENDING',
  'SHORTLISTED',
  'INTERVIEWED',
];

const statusLabels: Record<Application['status'], string> = {
  PENDING: 'Pending review',
  SHORTLISTED: 'Shortlisted',
  REJECTED: 'Rejected',
  INTERVIEWED: 'Interviewing',
  HIRED: 'Hired',
};

const statusTone: Record<Application['status'], string> = {
  PENDING: 'status--pending',
  SHORTLISTED: 'status--shortlisted',
  INTERVIEWED: 'status--interview',
  REJECTED: 'status--rejected',
  HIRED: 'status--hired',
};

const CandidateDashboard: React.FC = () => {
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [skills, setSkills] = useState<CandidateSkill[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [resumeHistory, setResumeHistory] = useState<GeneratedResumeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [
        profileData,
        skillsData,
        applicationsData,
        resumeHistoryResponse,
      ] = await Promise.all([
        candidateService.getProfile(),
        candidateService.getMySkills(),
        candidateService.getMyApplications(),
        resumeService.getResumeHistory(),
      ]);

      setProfile(profileData);
      setSkills(skillsData);

      const normalizedApplications: Application[] = Array.isArray(applicationsData)
        ? applicationsData
        : [];
      setApplications(normalizedApplications);

      const historyList = resumeHistoryResponse?.resumes || [];
      const sortedHistory = [...historyList].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setResumeHistory(sortedHistory);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
      setError('Could not load dashboard data. Please retry in a moment.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadResume = async (resumeId: string, label?: string) => {
    try {
      const blob = await resumeService.downloadResume(resumeId);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      const safeLabel = (label || `resume-${resumeId}`).replace(/[^a-z0-9]+/gi, '-').toLowerCase();
      anchor.href = url;
      anchor.download = `${safeLabel}.pdf`;
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download resume. Please try again.');
    }
  };

  const preferredRole = profile?.preferred_roles?.[0];
  const summarySnippet = useMemo(() => {
    if (!profile?.summary) return '';
    return profile.summary.length > 260
      ? `${profile.summary.slice(0, 257)}...`
      : profile.summary;
  }, [profile?.summary]);

  const focusSkills = skills.slice(0, 6);
  const skillTeaser = focusSkills
    .map((skill) => skill.skill_name)
    .filter((name): name is string => Boolean(name))
    .join(', ');
  const activeApplications = applications.filter((application) =>
    ACTIVE_APPLICATION_STATUSES.includes(application.status)
  );
  const recentApplications = [...applications]
    .sort((a, b) => new Date(b.applied_at).getTime() - new Date(a.applied_at).getTime())
    .slice(0, 4);
  const recentResumes = resumeHistory.slice(0, 4);

  const metrics = [
    {
      label: 'Active Applications',
      value: activeApplications.length,
      detail: `${applications.length} total tracked`,
    },
    {
      label: 'Resumes Generated',
      value: resumeHistory.length,
      detail: recentResumes[0]?.display_label || 'No resumes yet',
    },
    {
      label: 'Skills Locked',
      value: skills.length,
      detail: skillTeaser || 'Document your stack',
    },
  ];

  if (loading) {
    return (
      <div className="candidate-dashboard">
        <div className="dashboard-hero dashboard-hero--loading">
          <p>Calibrating your workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="candidate-dashboard">
      {error && <div className="dashboard-error">{error}</div>}

      <section className="dashboard-hero">
        <div className="hero-copy">
          <p className="hero-kicker">Ready for your next move</p>
          <h1>
            Let's target your next {preferredRole || 'role'}
          </h1>
          <p className="hero-summary">
            {summarySnippet || 'Tell us your story in the profile tab and we will turn it into tailored resumes, match previews, and recruiter-ready applications.'}
          </p>
          <div className="hero-actions">
            <Link to="/candidate/generate-resume" className="btn btn--primary">
              Generate resume
            </Link>
            <Link to="/candidate/jobs" className="btn btn--secondary">
              Browse live jobs
            </Link>
            <Link to="/candidate/profile" className="btn btn--ghost">
              Update profile
            </Link>
          </div>
        </div>
        <div className="hero-stats">
          <div className="hero-stats-card">
            <span>Preferred roles</span>
            <p>{profile?.preferred_roles?.join(' / ') || 'Add roles to prioritize matches'}</p>
          </div>
          <div className="hero-stats-card">
            <span>Location</span>
            <p>{profile?.location || 'Set your base city'}</p>
          </div>
          <div className="hero-stats-card">
            <span>Latest resume</span>
            <p>{recentResumes[0]?.display_label || 'No resumes yet'}</p>
          </div>
        </div>
      </section>

      <section className="metric-grid">
        {metrics.map((metric) => (
          <article key={metric.label} className="metric-card">
            <p className="metric-label">{metric.label}</p>
            <p className="metric-value">{metric.value}</p>
            <p className="metric-detail">{metric.detail}</p>
          </article>
        ))}
      </section>

      <div className="insight-grid">
        <section className="insight-card">
          <header>
            <div>
              <p className="insight-kicker">Pipeline</p>
              <h2>Application pulse</h2>
            </div>
            <Link to="/candidate/jobs" className="text-link">View jobs</Link>
          </header>
          {recentApplications.length === 0 ? (
            <p className="empty-state">You haven't applied to any jobs yet. Head over to Browse Jobs to start.</p>
          ) : (
            <ul className="application-list">
              {recentApplications.map((application) => (
                <li key={application.id}>
                  <div>
                    <p className="application-title">{application.job_title}</p>
                    <p className="application-meta">{application.job_company}</p>
                  </div>
                  <div className="application-status">
                    <span className={`status-badge ${statusTone[application.status]}`}>
                      {statusLabels[application.status]}
                    </span>
                    <p>{new Date(application.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="insight-card">
          <header>
            <div>
              <p className="insight-kicker">Resume lab</p>
              <h2>Recent exports</h2>
            </div>
            <Link to="/candidate/generate-resume" className="text-link">Open generator</Link>
          </header>
          {recentResumes.length === 0 ? (
            <p className="empty-state">No resumes generated yet. Use the generator to create a tailored PDF.</p>
          ) : (
            <ul className="resume-list">
              {recentResumes.map((record) => (
                <li key={record.resume_id}>
                  <div>
                    <p className="resume-title">{record.display_label}</p>
                    <p className="resume-meta">
                      Version {record.version}
                      {record.jd_company ? ` - ${record.jd_company}` : ''}
                    </p>
                  </div>
                  <button
                    className="btn btn--ghost"
                    onClick={() => handleDownloadResume(record.resume_id, record.display_label)}
                  >
                    Download
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="highlight-grid">
        <section className="highlight-card">
          <header>
            <p className="insight-kicker">Skills to surface</p>
            <h2>Signature stack</h2>
          </header>
          {focusSkills.length === 0 ? (
            <p className="empty-state">Document your top skills so recruiters can filter you into shortlists.</p>
          ) : (
            <div className="skill-pills">
              {focusSkills.map((skill) => (
                <span key={skill.id} className="skill-pill">
                  {skill.skill_name || `Skill ${skill.skill}`} - {skill.proficiency_level}
                </span>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default CandidateDashboard;
