import React, { useState, useEffect, useCallback } from 'react';
import { candidateService } from '../../services/candidate.service';
import { recruiterService } from '../../services/recruiter.service';
import { resumeService } from '../../services/resume.service';
import {
  JobDescription,
  GeneratedResumeRecord,
  CandidateApplicationPreview,
} from '../../types';
import './BrowseJobs.css';

const SNAPSHOT_OPTION = '__snapshot__';

const BrowseJobs: React.FC = () => {
  const [jobs, setJobs] = useState<JobDescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [applyModalJob, setApplyModalJob] = useState<JobDescription | null>(null);
  const [resumeHistory, setResumeHistory] = useState<GeneratedResumeRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [matchPreview, setMatchPreview] = useState<CandidateApplicationPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [selectedResumeId, setSelectedResumeId] = useState<string>(SNAPSHOT_OPTION);
  const [submittingApplication, setSubmittingApplication] = useState(false);
  const [modalError, setModalError] = useState('');

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const jobList = await recruiterService.getJobs();
      const activeJobs = (jobList || []).filter((job) => job.status !== 'CLOSED');
      setJobs(activeJobs);
    } catch (err: any) {
      const message = err?.response?.data?.error || 'Failed to load jobs. Please try again.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    if (!applyModalJob) {
      return;
    }

    let isMounted = true;
    setResumeHistory([]);
    setMatchPreview(null);
    setHistoryError('');
    setPreviewError('');
    setHistoryLoading(true);
    setPreviewLoading(true);

    const fetchModalData = async () => {
      const [historyResult, previewResult] = await Promise.allSettled([
        resumeService.getResumeHistory(),
        candidateService.previewApplication({ job_id: applyModalJob.id }),
      ]);

      if (!isMounted) {
        return;
      }

      if (historyResult.status === 'fulfilled') {
        setResumeHistory(historyResult.value.resumes || []);
      } else {
        setHistoryError('Failed to load existing resumes. You can still apply using a fresh snapshot.');
      }

      if (previewResult.status === 'fulfilled') {
        setMatchPreview(previewResult.value);
      } else {
        setPreviewError('Could not evaluate match strength right now. You can still apply.');
      }

      setHistoryLoading(false);
      setPreviewLoading(false);
    };

    fetchModalData();

    return () => {
      isMounted = false;
    };
  }, [applyModalJob]);

  const openApplyModal = (job: JobDescription) => {
    setApplyModalJob(job);
    setSelectedResumeId(SNAPSHOT_OPTION);
    setModalError('');
    setHistoryError('');
    setPreviewError('');
  };

  const closeApplyModal = () => {
    setApplyModalJob(null);
    setSelectedResumeId(SNAPSHOT_OPTION);
    setResumeHistory([]);
    setMatchPreview(null);
    setHistoryError('');
    setPreviewError('');
    setModalError('');
    setHistoryLoading(false);
    setPreviewLoading(false);
  };

  const handleSubmitApplication = async () => {
    if (!applyModalJob) {
      return;
    }

    setSubmittingApplication(true);
    setModalError('');

    try {
      const payload: { job_id: number; resume_id?: string } = {
        job_id: applyModalJob.id,
      };

      if (selectedResumeId && selectedResumeId !== SNAPSHOT_OPTION) {
        payload.resume_id = selectedResumeId;
      }

      const response = await candidateService.applyToJob(payload);
      setBanner({ type: 'success', text: response.message || 'Application submitted successfully!' });
      closeApplyModal();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.error || 'Failed to submit application. Please try again.';
      setModalError(errorMsg);
    } finally {
      setSubmittingApplication(false);
    }
  };

  const renderResumeLabel = (record: GeneratedResumeRecord) => {
    const createdAt = new Date(record.created_at).toLocaleString();
    return (
      <>
        <div className="resume-option-title">{record.display_label}</div>
        <div className="resume-option-meta">Version {record.version} · {createdAt}</div>
        {record.jd_title && (
          <div className="resume-option-job">
            {record.jd_title}
            {record.jd_company ? ` · ${record.jd_company}` : ''}
          </div>
        )}
      </>
    );
  };

  const renderMatchPreview = () => {
    if (!applyModalJob) {
      return null;
    }

    const matchPercent = Math.round(
      Math.min(Math.max(matchPreview?.match_strength ?? 0, 0), 1) * 100
    );

    const graphPercent = matchPreview?.selected_content?.match_strength;

    return (
      <div className="match-preview-section">
        <div className="match-preview-header">
          <h4>Match Preview</h4>
          {previewLoading && <span>Analyzing your profile...</span>}
        </div>

        {previewError && <p className="match-preview-status error">{previewError}</p>}
        {!previewLoading && !previewError && !matchPreview && (
          <p className="match-preview-status">Match preview is not available right now.</p>
        )}

        {matchPreview && (
          <div className="match-preview-grid">
            <div className="match-preview-card">
              <p className="match-preview-label">Match Strength</p>
              <div className="match-preview-score">
                <span>{matchPercent}%</span>
                <small>{applyModalJob.title}</small>
              </div>
              <div className="match-preview-meter">
                <div className="match-preview-meter-fill" style={{ width: `${matchPercent}%` }} />
              </div>
              <p className="match-preview-footnote">Based on graph reasoning for this role.</p>
            </div>

            <div className="match-preview-card">
              <p className="match-preview-label">Highlighted Content</p>
              <ul>
                <li>
                  <strong>{matchPreview.selected_projects}</strong> project(s) selected
                </li>
                <li>
                  <strong>{matchPreview.selected_skills}</strong> skill(s) emphasized
                </li>
              </ul>
              {typeof graphPercent === 'number' && (
                <p className="match-preview-footnote">
                  Internal score: {Math.round(Math.min(Math.max(graphPercent, 0), 1) * 100)}%
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderModal = () => {
    if (!applyModalJob) {
      return null;
    }

    return (
      <div className="apply-modal-overlay" onClick={closeApplyModal}>
        <div className="apply-modal" onClick={(event) => event.stopPropagation()}>
          <div className="apply-modal-header">
            <h3>Apply to {applyModalJob.title}</h3>
            <p className="apply-modal-job-meta">{applyModalJob.company}</p>
          </div>
          <p className="apply-modal-description">
            Choose whether to send a fresh snapshot of your profile or reuse any previously generated resume.
          </p>

          {renderMatchPreview()}

          <div className="apply-modal-options">
            <label className={`resume-option ${selectedResumeId === SNAPSHOT_OPTION ? 'selected' : ''}`}>
              <input
                type="radio"
                value={SNAPSHOT_OPTION}
                checked={selectedResumeId === SNAPSHOT_OPTION}
                onChange={(event) => setSelectedResumeId(event.target.value)}
                disabled={submittingApplication}
              />
              <div className="resume-option-content">
                <div className="resume-option-title">Quick Snapshot</div>
                <div className="resume-option-meta">Use your latest profile data instantly</div>
                <p className="resume-option-detail">
                  We will capture your profile, run graph reasoning, and attach the structured snapshot so recruiters can
                  review immediately.
                </p>
              </div>
            </label>
          </div>

          <div className="resume-history-section">
            <div className="resume-history-header">
              <h4>Use an existing resume</h4>
              <span>Optional</span>
            </div>

            {historyLoading && <p className="resume-history-status">Loading your saved resumes...</p>}
            {historyError && <p className="resume-history-status error">{historyError}</p>}

            {!historyLoading && resumeHistory.length === 0 && !historyError && (
              <p className="resume-history-empty">
                You have not generated any resumes yet. Select Quick Snapshot above to continue.
              </p>
            )}

            {!historyLoading && resumeHistory.length > 0 && (
              <div className="resume-history-scroll">
                {resumeHistory.map((record) => (
                  <label
                    key={record.resume_id}
                    className={`resume-option ${selectedResumeId === record.resume_id ? 'selected' : ''}`}
                  >
                    <input
                      type="radio"
                      value={record.resume_id}
                      checked={selectedResumeId === record.resume_id}
                      onChange={(event) => setSelectedResumeId(event.target.value)}
                      disabled={submittingApplication}
                    />
                    <div className="resume-option-content">{renderResumeLabel(record)}</div>
                  </label>
                ))}
              </div>
            )}
          </div>

          {modalError && <div className="modal-error">{modalError}</div>}

          <div className="modal-actions">
            <button className="btn btn-secondary-light" onClick={closeApplyModal} disabled={submittingApplication}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSubmitApplication} disabled={submittingApplication}>
              {submittingApplication ? 'Submitting...' : 'Submit Application'}
            </button>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return <div className="browse-jobs-container">Loading jobs...</div>;
  }

  return (
    <div className="browse-jobs-container">
      <div className="browse-header">
        <h1>Browse Jobs</h1>
        <p className="browse-subtitle">Find your next opportunity</p>
      </div>

      {banner && <div className={`browse-banner ${banner.type}`}>{banner.text}</div>}
      {error && <div className="error-message">{error}</div>}

      {jobs.length === 0 ? (
        <div className="empty-state">
          <p>No active job postings available at the moment.</p>
          <p>Check back later for new opportunities!</p>
        </div>
      ) : (
        <div className="jobs-list">
          {jobs.map((job) => (
            <div key={job.id} className="job-listing-card">
              <div className="job-listing-header">
                <div>
                  <h2>{job.title}</h2>
                  <p className="job-company">{job.company}</p>
                </div>
                <span className="job-badge active">Active</span>
              </div>

              <div className="job-description">
                <p>
                  {job.description.length > 300
                    ? `${job.description.substring(0, 300)}...`
                    : job.description}
                </p>
              </div>

              <div className="job-competencies">
                <strong>Required Skills:</strong>
                <div className="competencies-tags">
                  {(job.required_competencies || []).slice(0, 8).map((comp, idx) => (
                    <span key={idx} className="competency-tag">
                      {comp}
                    </span>
                  ))}
                  {(job.required_competencies || []).length > 8 && (
                    <span className="competency-tag more">
                      +{(job.required_competencies || []).length - 8} more
                    </span>
                  )}
                </div>
              </div>

              <div className="job-footer">
                <span className="job-posted">Posted: {new Date(job.posted_at).toLocaleDateString()}</span>
                <button onClick={() => openApplyModal(job)} className="btn-apply" disabled={Boolean(applyModalJob)}>
                  Apply Now
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {renderModal()}
    </div>
  );
};

export default BrowseJobs;
