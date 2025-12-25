import React, { useState } from 'react';
import { resumeService } from '../../services/resume.service';
import './GenerateResume.css';

const GenerateResume: React.FC = () => {
  const [jdText, setJdText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!jdText.trim()) {
      setError('Please enter a job description');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await resumeService.generateResume({ jd_text: jdText });
      setResult(response);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to generate resume');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!result?.resume_id) return;

    try {
      const blob = await resumeService.downloadResume(result.resume_id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resume_${result.resume_id}.pdf`;
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

      {result && (
        <div className="result-section">
          <h2>Resume Generated Successfully!</h2>
          <div className="result-details">
            <p><strong>Resume ID:</strong> {result.resume_id}</p>
            <p><strong>Attempt:</strong> {result.attempt} / 3</p>
            <p><strong>PDF Path:</strong> {result.pdf_path}</p>
            
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
          
          <button onClick={handleDownload} className="btn-primary">
            Download PDF
          </button>
        </div>
      )}
    </div>
  );
};

export default GenerateResume;
