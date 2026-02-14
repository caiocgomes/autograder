import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { submissionsApi } from '../../api/submissions';
import type { SubmissionDetail } from '../../api/submissions';

export function SubmissionResultsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        const data = await submissionsApi.getResults(Number(id));
        setDetail(data);
      } catch {
        setError('Failed to load submission results');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [id]);

  if (isLoading) return <div>Loading results...</div>;
  if (error) return <div style={{ color: '#c00' }}>{error}</div>;
  if (!detail) return <div>Submission not found</div>;

  const { submission, test_results, llm_evaluation, grade } = detail;

  return (
    <div style={{ maxWidth: '900px' }}>
      <button
        onClick={() => navigate(-1)}
        style={{ padding: '6px 12px', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginBottom: '15px' }}
      >
        Back
      </button>

      <h1 style={{ marginBottom: '20px' }}>Submission #{submission.id} Results</h1>

      {/* Status */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
          <div>
            <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Status</span>
            <span style={{
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              backgroundColor: submission.status === 'completed' ? '#2ecc71' : submission.status === 'failed' ? '#e74c3c' : '#f39c12',
              color: 'white',
            }}>
              {submission.status}
            </span>
          </div>
          <div>
            <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Submitted</span>
            <span>{new Date(submission.submitted_at).toLocaleString()}</span>
          </div>
          {grade && (
            <div>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Final Score</span>
              <span style={{ fontSize: '24px', fontWeight: 700, color: '#2c3e50' }}>{grade.final_score.toFixed(1)}</span>
              {!grade.published && <span style={{ fontSize: '12px', color: '#f39c12', marginLeft: '8px' }}>(pending review)</span>}
            </div>
          )}
        </div>
      </div>

      {submission.error_message && (
        <div style={{ backgroundColor: '#fee', padding: '15px', borderRadius: '8px', marginBottom: '15px', color: '#c00', fontSize: '13px' }}>
          {submission.error_message}
        </div>
      )}

      {/* Your Code */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Your Code</h3>
        <pre style={{
          backgroundColor: '#1e1e1e',
          color: '#d4d4d4',
          padding: '15px',
          borderRadius: '4px',
          overflow: 'auto',
          maxHeight: '300px',
          fontSize: '13px',
          lineHeight: '1.5',
          fontFamily: 'monospace',
        }}>
          {submission.code}
        </pre>
      </div>

      {/* Test Results */}
      {test_results && test_results.length > 0 && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>
            Test Results ({test_results.filter((t) => t.passed).length}/{test_results.length} passed)
          </h3>
          {test_results.map((tr) => (
            <div key={tr.id} style={{ padding: '10px', marginBottom: '8px', backgroundColor: tr.passed ? '#eafaf1' : '#fef2f2', borderRadius: '4px', borderLeft: `4px solid ${tr.passed ? '#2ecc71' : '#e74c3c'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>{tr.test_name}</strong>
                <span style={{ color: tr.passed ? '#2ecc71' : '#e74c3c', fontWeight: 600, fontSize: '13px' }}>
                  {tr.passed ? 'PASSED' : 'FAILED'}
                </span>
              </div>
              {tr.message && <p style={{ margin: '5px 0 0', fontSize: '13px', color: '#555' }}>{tr.message}</p>}
              {tr.stdout && (
                <pre style={{ margin: '5px 0 0', fontSize: '11px', color: '#333', backgroundColor: 'rgba(0,0,0,0.05)', padding: '5px', borderRadius: '3px' }}>
                  {tr.stdout}
                </pre>
              )}
              {tr.stderr && (
                <pre style={{ margin: '5px 0 0', fontSize: '11px', color: '#e74c3c', backgroundColor: 'rgba(0,0,0,0.05)', padding: '5px', borderRadius: '3px' }}>
                  {tr.stderr}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}

      {/* LLM Feedback */}
      {llm_evaluation && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>
            AI Feedback (Score: {llm_evaluation.score.toFixed(1)}/100)
          </h3>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', color: '#333' }}>
            {llm_evaluation.feedback}
          </div>
        </div>
      )}

      {/* Grade Breakdown */}
      {grade && grade.published && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Grade Breakdown</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '15px' }}>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Test Score</span>
              <span style={{ fontSize: '20px', fontWeight: 600 }}>{grade.test_score != null ? `${grade.test_score.toFixed(1)}%` : '—'}</span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>LLM Score</span>
              <span style={{ fontSize: '20px', fontWeight: 600 }}>{grade.llm_score != null ? grade.llm_score.toFixed(1) : '—'}</span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Late Penalty</span>
              <span style={{ fontSize: '20px', fontWeight: 600, color: grade.late_penalty_applied > 0 ? '#e74c3c' : 'inherit' }}>
                {grade.late_penalty_applied > 0 ? `-${grade.late_penalty_applied.toFixed(1)}` : '0'}
              </span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Final Score</span>
              <span style={{ fontSize: '28px', fontWeight: 700, color: '#2c3e50' }}>{grade.final_score.toFixed(1)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
