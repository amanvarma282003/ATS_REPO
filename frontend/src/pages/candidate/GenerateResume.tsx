import React, { useState, useEffect, useCallback } from 'react';
import { resumeService } from '../../services/resume.service';
import {
  GeneratedResumeRecord,
  ResumeGenerationResponse,
  ResumeLabelPreview,
} from '../../types';
import './GenerateResume.css';

const GenerateResume: React.FC = () => {
  const [jdText, setJdText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResumeGenerationResponse | null>(null);
  const [error, setError] = useState('');
  const [labelPreview, setLabelPreview] = useState<ResumeLabelPreview | null>(null);
  const [history, setHistory] = useState<GeneratedResumeRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState('');

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError('');
    try {
      const response = await resumeService.getResumeHistory();
      setHistory(response.resumes || []);
    } catch (err) {
      setHistoryError('Failed to load resume history');
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleGenerate = async () => {
    if (!jdText.trim()) {
      setError('Please enter a job description');
      return;
    }

    const payload = { jd_text: jdText };
    setLoading(true);
    setError('');
    setResult(null);
    setLabelPreview(null);

    // Start label preview (fast) - update UI immediately when ready
    resumeService.previewLabel(payload)
      .then((label) => {
        setLabelPreview(label);
      })
      .catch((err) => {
        console.error('Label preview failed', err);
      });

    try {
      // Start resume generation (slow) - this runs in parallel with label
      const resumeResult = await resumeService.generateResume(payload);
      setResult(resumeResult);
      await loadHistory();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to generate resume');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (resumeId: string, label?: string) => {
    try {
      const blob = await resumeService.downloadResume(resumeId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      const safeLabel = (label || `resume_${resumeId}`).replace(/[^a-z0-9]+/gi, '-').toLowerCase();
      a.href = url;
      a.download = `${safeLabel}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download resume');
    }
  };

  return (
    <div className="generate-container">
      <h1>Generate Resume</h1>

      <div className="generate-section">
        <h2>Paste Job Description</h2>
        <textarea
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          placeholder="Paste the job description here..."
          rows={15}
          className="jd-textarea"
        />
        
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="btn-primary"
        >
          {loading ? 'Generating... (This may take 10-30 seconds)' : 'Generate Resume'}
        </button>
      </div>

      {error && (
        <div className="error-message">{error}</div>
      )}

      {labelPreview && (
        <div className="label-preview">
          <h2>Upcoming Resume Label</h2>
          <p className="label-preview-primary">{labelPreview.display_label}</p>
          <p className="label-preview-meta">
            Version {labelPreview.next_version} · Base label: {labelPreview.base_label}
          </p>
        </div>
      )}

      {result && (
        <div className="result-section">
          <h2>Resume Generated Successfully!</h2>
          <div className="result-details">
            <p><strong>Label:</strong> {result.display_label}</p>
            <p><strong>Version:</strong> {result.version}</p>
            
            {result.match_explanation && (
              <div className="match-explanation">
                <h3>Match Analysis</h3>
                <p><strong>Decision:</strong> {result.match_explanation.decision}</p>
                <p><strong>Confidence:</strong> {(result.match_explanation.confidence * 100).toFixed(1)}%</p>
                <p><strong>Explanation:</strong> {result.match_explanation.explanation}</p>
                
                {result.match_explanation.strengths?.length > 0 && (
                  <div>
                    <h4>Strengths:</h4>
                    <ul>
                      {result.match_explanation.strengths.map((s: string, i: number) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {result.match_explanation.gaps?.length > 0 && (
                  <div>
                    <h4>Gaps:</h4>
                    <ul>
                      {result.match_explanation.gaps.map((g: string, i: number) => (
                        <li key={i}>{g}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
          
          <button
            onClick={() => handleDownload(result.resume_id, result.display_label)}
            className="btn btn-primary"
          >
            Download PDF
          </button>
        </div>
      )}

      <div className="history-section">
        <div className="history-header">
          <h2>Resume History</h2>
          <button
            className="btn btn-secondary-light"
            onClick={() => loadHistory()}
            disabled={historyLoading}
          >
            {historyLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        {historyError && <div className="error-message">{historyError}</div>}
        {historyLoading && history.length === 0 ? (
          <p className="history-empty">Loading history...</p>
        ) : history.length === 0 ? (
          <p className="history-empty">No resumes generated yet.</p>
        ) : (
          <ul className="history-list">
            {history.map((record) => (
              <li key={record.resume_id} className="history-card">
                <div className="history-meta">
                  <h3>{record.display_label}</h3>
                  <p>{record.jd_title || 'Custom Role'}{record.jd_company ? ` @ ${record.jd_company}` : ''}</p>
                  <p>Version {record.version} · {new Date(record.created_at).toLocaleString()}</p>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => handleDownload(record.resume_id, record.display_label)}
                >
                  Download PDF
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default GenerateResume;
