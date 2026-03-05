import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { recruiterService } from '../../services/recruiter.service';
import { Application } from '../../types';
import './ApplicationsPage.css';

const ApplicationsPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  // Feedback form
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackApp, setFeedbackApp] = useState<number | null>(null);
  const [action, setAction] = useState<'SHORTLIST' | 'REJECT' | 'INTERVIEW' | 'HIRE'>('SHORTLIST');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [questionsLoading, setQuestionsLoading] = useState<number | null>(null);
  const [questionsMap, setQuestionsMap] = useState<Record<number, { category: string; question: string }[]>>({});
  const [questionsModalApp, setQuestionsModalApp] = useState<number | null>(null);

  const loadApplications = useCallback(async () => {
    if (!jobId) return;
    
    try {
      const data = await recruiterService.getApplications(parseInt(jobId));
      setApplications(data);
    } catch (err: any) {
      setError('Failed to load applications');
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    loadApplications();
  }, [loadApplications]);

  const handleViewDetails = async (appId: number) => {
    try {
      const details = await recruiterService.getApplication(appId);
      setSelectedApp(details);
    } catch (err: any) {
      setError('Failed to load application details');
    }
  };

  const handleOpenFeedback = (appId: number) => {
    setFeedbackApp(appId);
    setShowFeedback(true);
    setAction('SHORTLIST');
    setReason('');
  };

  const handleSubmitFeedback = async () => {
    if (!feedbackApp || !reason.trim()) {
      alert('Please provide a reason');
      return;
    }

    setSubmitting(true);
    try {
      await recruiterService.submitFeedback({
        application: feedbackApp,
        action,
        reason,
      });
      setShowFeedback(false);
      setFeedbackApp(null);
      await loadApplications();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadResume = async (application: Application) => {
    setDownloadingId(application.id);
    setError('');
    try {
      const blob = await recruiterService.downloadApplicationResume(application.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const candidateLabel = application.candidate_info?.full_name || application.candidate_info?.email || `candidate-${application.candidate}`;
      link.download = `${candidateLabel || 'candidate'}-application-${application.id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err?.response?.data?.error || 'Failed to download resume');
    } finally {
      setDownloadingId(null);
    }
  };

  const handleGenerateQuestions = async (appId: number) => {
    setQuestionsLoading(appId);
    setError('');
    try {
      const data = await recruiterService.getInterviewQuestions(appId);
      setQuestionsMap((prev) => ({ ...prev, [appId]: data.questions }));
      setSelectedApp((prev) =>
        prev && prev.id === appId
          ? { ...prev, interview_questions: data.questions }
          : prev
      );
      setQuestionsModalApp(appId);
    } catch (err: any) {
      setError(err?.response?.data?.error || 'Failed to generate interview questions');
    } finally {
      setQuestionsLoading(null);
    }
  };

  if (loading) {
    return <div className="applications-container">Loading...</div>;
  }

  return (
    <div className="applications-container">
      <h1>Applications for Job #{jobId}</h1>

      {error && <div className="error-message">{error}</div>}

      {applications.length === 0 ? (
        <div className="empty-state">
          <p>No applications received yet for this job.</p>
        </div>
      ) : (
        <div className="applications-list">
          {applications.map((app) => (
            <div key={app.id} className="application-card">
              <div className="app-header">
                <h3>Application #{app.id}</h3>
                <span className={`status-badge status-${app.status.toLowerCase()}`}>
                  {app.status}
                </span>
              </div>
              
              <div className="app-info">
                <p><strong>Candidate:</strong> {app.candidate_info?.email || `Candidate #${app.candidate}`}</p>
                <p><strong>Applied:</strong> {new Date(app.applied_at).toLocaleString()}</p>
                {app.match_explanation?.decision && (
                  <p><strong>Match Decision:</strong> {app.match_explanation.decision}</p>
                )}
                {app.match_explanation?.confidence !== undefined && (
                  <p><strong>Confidence:</strong> {(app.match_explanation.confidence * 100).toFixed(1)}%</p>
                )}
              </div>

              <div className="app-actions">
                <button
                  onClick={() => handleViewDetails(app.id)}
                  className="btn btn-secondary-light"
                >
                  View Details
                </button>
                <button
                  onClick={() => handleDownloadResume(app)}
                  className="btn btn-secondary-light"
                  disabled={downloadingId === app.id}
                >
                  {downloadingId === app.id ? 'Preparing PDF...' : 'View Resume PDF'}
                </button>
                {app.match_explanation?.decision === 'SHORTLIST' && (
                  <button
                    onClick={() => {
                      if (app.interview_questions?.length > 0 || questionsMap[app.id]?.length > 0) {
                        setQuestionsModalApp(app.id);
                      } else {
                        handleGenerateQuestions(app.id);
                      }
                    }}
                    className="btn btn-secondary-light"
                    disabled={questionsLoading === app.id}
                  >
                    {questionsLoading === app.id
                      ? 'Generating...'
                      : (app.interview_questions?.length > 0 || questionsMap[app.id]?.length > 0)
                        ? 'View Questions'
                        : 'Generate Questions'}
                  </button>
                )}
                {app.status === 'PENDING' && (
                  <button
                    onClick={() => handleOpenFeedback(app.id)}
                    className="btn btn-primary"
                  >
                    Submit Feedback
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedApp && (
        <div className="modal-overlay" onClick={() => setSelectedApp(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Application Details</h2>
            <div className="details-section">
              <p><strong>Application ID:</strong> {selectedApp.id}</p>
              <p><strong>Status:</strong> {selectedApp.status}</p>
              <p><strong>Match Decision:</strong> {selectedApp.match_explanation?.decision}</p>
              <p><strong>Confidence:</strong> {((selectedApp.match_explanation?.confidence || 0) * 100).toFixed(1)}%</p>
              
              {selectedApp.match_explanation?.explanation && (
                <div className="explanation-box">
                  <h4>Match Explanation:</h4>
                  <p>{selectedApp.match_explanation.explanation}</p>
                </div>
              )}

              {selectedApp.match_explanation?.strengths && selectedApp.match_explanation.strengths.length > 0 && (
                <div>
                  <h4>Strengths:</h4>
                  <ul>
                    {selectedApp.match_explanation.strengths.map((s: string, i: number) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              )}

              {selectedApp.match_explanation?.gaps && selectedApp.match_explanation.gaps.length > 0 && (
                <div>
                  <h4>Gaps:</h4>
                  <ul>
                    {selectedApp.match_explanation.gaps.map((g: string, i: number) => <li key={i}>{g}</li>)}
                  </ul>
                </div>
              )}

              {selectedApp.match_explanation?.decision === 'SHORTLIST' &&
                !(selectedApp.interview_questions?.length > 0 || questionsMap[selectedApp.id]?.length > 0) && (
                <div className="questions-generate-row">
                  <button
                    onClick={() => handleGenerateQuestions(selectedApp.id)}
                    className="btn btn-secondary-light"
                    disabled={questionsLoading === selectedApp.id}
                  >
                    {questionsLoading === selectedApp.id ? 'Generating...' : 'Generate Interview Questions'}
                  </button>
                </div>
              )}

              {(() => {
                const qs = selectedApp.interview_questions?.length > 0
                  ? selectedApp.interview_questions
                  : questionsMap[selectedApp.id];
                if (!qs || qs.length === 0) return null;
                const categories = qs.reduce((acc: string[], q) => acc.includes(q.category) ? acc : [...acc, q.category], []);
                return (
                  <div className="questions-panel">
                    <h4>Interview Questions</h4>
                    {categories.map((cat) => (
                      <div key={cat} className="question-category">
                        <h5>{cat}</h5>
                        <ol>
                          {qs.filter((q) => q.category === cat).map((q, i) => (
                            <li key={i} className="question-item">{q.question}</li>
                          ))}
                        </ol>
                      </div>
                    ))}
                  </div>
                );
              })()}
            </div>
            <button onClick={() => setSelectedApp(null)} className="btn btn-primary">
              Close
            </button>
          </div>
        </div>
      )}

      {questionsModalApp !== null && (() => {
        const app = applications.find((a) => a.id === questionsModalApp);
        const qs = (app?.interview_questions?.length ?? 0) > 0
          ? app!.interview_questions
          : questionsMap[questionsModalApp] ?? [];
        const categories = qs.reduce((acc: string[], q) =>
          acc.includes(q.category) ? acc : [...acc, q.category], []);
        return (
          <div className="modal-overlay" onClick={() => setQuestionsModalApp(null)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <h2>Interview Questions</h2>
              <div className="questions-panel">
                {categories.map((cat) => (
                  <div key={cat} className="question-category">
                    <h5>{cat}</h5>
                    <ol>
                      {qs.filter((q) => q.category === cat).map((q, i) => (
                        <li key={i} className="question-item">{q.question}</li>
                      ))}
                    </ol>
                  </div>
                ))}
              </div>
              <button onClick={() => setQuestionsModalApp(null)} className="btn btn-primary">
                Close
              </button>
            </div>
          </div>
        );
      })()}

      {showFeedback && (
        <div className="modal-overlay" onClick={() => setShowFeedback(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Submit Feedback</h2>
            <div className="feedback-form">
              <div className="form-group">
                <label>Action:</label>
                <select
                  value={action}
                  onChange={(e) => setAction(e.target.value as 'SHORTLIST' | 'REJECT' | 'INTERVIEW' | 'HIRE')}
                >
                  <option value="SHORTLIST">Shortlist</option>
                  <option value="INTERVIEW">Interview</option>
                  <option value="HIRE">Hire</option>
                  <option value="REJECT">Reject</option>
                </select>
              </div>
              <div className="form-group">
                <label>Reason:</label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  rows={5}
                  placeholder="Provide feedback reason..."
                />
              </div>
              <div className="form-actions">
                <button
                  onClick={() => setShowFeedback(false)}
                  className="btn btn-secondary-light"
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmitFeedback}
                  className="btn btn-primary"
                  disabled={submitting}
                >
                  {submitting ? 'Submitting...' : 'Submit'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApplicationsPage;
