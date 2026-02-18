import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { submissionsApi } from '../../api/submissions';
import { gradesApi } from '../../api/grades';
import type { SubmissionDetail } from '../../api/submissions';

export function SubmissionReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingScore, setEditingScore] = useState(false);
  const [editLlmScore, setEditLlmScore] = useState<number>(0);
  const [editFeedback, setEditFeedback] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const load = async () => {
    try {
      setIsLoading(true);
      const data = await submissionsApi.getResults(Number(id));
      setDetail(data);
      if (data.grade) {
        setEditLlmScore(data.grade.llm_score ?? 0);
      }
      if (data.llm_evaluation) {
        setEditFeedback(data.llm_evaluation.feedback);
      }
    } catch {
      setError('Failed to load submission details');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  const handleSaveScore = async () => {
    if (!detail?.grade) return;
    setIsSaving(true);
    try {
      await gradesApi.update(detail.grade.id, {
        llm_score: editLlmScore,
        llm_feedback: editFeedback,
      });
      setEditingScore(false);
      load();
    } catch {
      alert('Failed to save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!detail?.grade) return;
    try {
      await gradesApi.publish(detail.grade.id);
      load();
    } catch {
      alert('Failed to publish grade');
    }
  };

  if (isLoading) return <div>Loading submission...</div>;
  if (error) return <div style={{ color: '#c00' }}>{error}</div>;
  if (!detail) return <div>Submission not found</div>;

  const { submission, test_results, llm_evaluation, grade, rubric_scores, overall_feedback } = detail;
  const isFileSubmission = !submission.code && submission.file_name;

  return (
    <div style={{ maxWidth: '1000px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>Submission Review #{submission.id}</h1>
        <button
          onClick={() => navigate(-1)}
          style={{ padding: '8px 16px', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Back
        </button>
      </div>

      {/* Submission Info */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '15px', marginBottom: '15px' }}>
          <div>
            <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Student</span>
            <span style={{ fontWeight: 600 }}>#{submission.student_id}</span>
          </div>
          <div>
            <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Exercise</span>
            <span style={{ fontWeight: 600 }}>#{submission.exercise_id}</span>
          </div>
          <div>
            <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Status</span>
            <span style={{
              padding: '2px 8px',
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
        </div>
      </div>

      {/* Content: Code or File */}
      {isFileSubmission ? (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Submitted File</h3>
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <div>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>File Name</span>
              <span style={{ fontWeight: 600 }}>{submission.file_name}</span>
            </div>
            {submission.file_size && (
              <div>
                <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Size</span>
                <span>{submission.file_size < 1024 * 1024 ? `${(submission.file_size / 1024).toFixed(1)} KB` : `${(submission.file_size / (1024 * 1024)).toFixed(1)} MB`}</span>
              </div>
            )}
            {submission.content_type && (
              <div>
                <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Type</span>
                <span>{submission.content_type}</span>
              </div>
            )}
          </div>
        </div>
      ) : submission.code ? (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Student Code</h3>
          <pre style={{
            backgroundColor: '#1e1e1e',
            color: '#d4d4d4',
            padding: '15px',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '400px',
            fontSize: '13px',
            lineHeight: '1.5',
            fontFamily: 'monospace',
          }}>
            {submission.code}
          </pre>
        </div>
      ) : null}

      {/* Rubric Scores (for llm_first exercises) */}
      {rubric_scores && rubric_scores.length > 0 && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Rubric Evaluation</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ecf0f1' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>Dimension</th>
                <th style={{ padding: '8px', textAlign: 'center', width: '80px' }}>Weight</th>
                <th style={{ padding: '8px', textAlign: 'center', width: '80px' }}>Score</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Feedback</th>
              </tr>
            </thead>
            <tbody>
              {rubric_scores.map((rs, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #ecf0f1' }}>
                  <td style={{ padding: '8px', fontWeight: 600 }}>{rs.dimension_name}</td>
                  <td style={{ padding: '8px', textAlign: 'center', color: '#7f8c8d' }}>
                    {(rs.dimension_weight * 100).toFixed(0)}%
                  </td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>
                    <span style={{
                      fontWeight: 700,
                      color: rs.score >= 70 ? '#2ecc71' : rs.score >= 40 ? '#f39c12' : '#e74c3c',
                    }}>
                      {rs.score.toFixed(1)}
                    </span>
                  </td>
                  <td style={{ padding: '8px', fontSize: '13px', color: '#555', whiteSpace: 'pre-wrap' }}>
                    {rs.feedback || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Overall Feedback (for llm_first exercises) */}
      {overall_feedback && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Overall Feedback</h3>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', color: '#333' }}>
            {overall_feedback}
          </div>
        </div>
      )}

      {/* Test Results */}
      {test_results && test_results.length > 0 && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>
            Test Results ({test_results.filter((t) => t.passed).length}/{test_results.length} passed)
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ecf0f1' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>Test</th>
                <th style={{ padding: '8px', textAlign: 'center', width: '80px' }}>Result</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Message</th>
              </tr>
            </thead>
            <tbody>
              {test_results.map((tr) => (
                <tr key={tr.id} style={{ borderBottom: '1px solid #ecf0f1' }}>
                  <td style={{ padding: '8px' }}>{tr.test_name}</td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>
                    <span style={{ color: tr.passed ? '#2ecc71' : '#e74c3c', fontWeight: 600 }}>
                      {tr.passed ? 'PASS' : 'FAIL'}
                    </span>
                  </td>
                  <td style={{ padding: '8px', fontSize: '13px', color: '#7f8c8d' }}>
                    {tr.message || '-'}
                    {tr.stderr && (
                      <pre style={{ margin: '5px 0 0', fontSize: '11px', color: '#e74c3c', whiteSpace: 'pre-wrap' }}>
                        {tr.stderr}
                      </pre>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* LLM Feedback (for test_first with llm enabled) */}
      {llm_evaluation && !rubric_scores && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>
            LLM Evaluation (Score: {llm_evaluation.score.toFixed(1)})
            {llm_evaluation.cached && <span style={{ fontSize: '12px', color: '#7f8c8d', marginLeft: '10px' }}>(cached)</span>}
          </h3>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', color: '#333' }}>
            {llm_evaluation.feedback}
          </div>
        </div>
      )}

      {/* Grade & Actions */}
      {grade && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <h3 style={{ margin: 0, color: '#2c3e50' }}>Grade</h3>
            <div style={{ display: 'flex', gap: '10px' }}>
              {!editingScore && (
                <button
                  onClick={() => setEditingScore(true)}
                  style={{ padding: '6px 12px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}
                >
                  Edit Score
                </button>
              )}
              {!grade.published && (
                <button
                  onClick={handlePublish}
                  style={{ padding: '6px 12px', backgroundColor: '#2ecc71', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}
                >
                  Publish Grade
                </button>
              )}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', gap: '15px', marginBottom: '15px' }}>
            <div>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Test Score</span>
              <span style={{ fontSize: '18px', fontWeight: 600 }}>{grade.test_score != null ? `${grade.test_score.toFixed(1)}%` : '-'}</span>
            </div>
            <div>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>LLM Score</span>
              <span style={{ fontSize: '18px', fontWeight: 600 }}>{grade.llm_score != null ? grade.llm_score.toFixed(1) : '-'}</span>
            </div>
            <div>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Late Penalty</span>
              <span style={{ fontSize: '18px', fontWeight: 600, color: grade.late_penalty_applied > 0 ? '#e74c3c' : 'inherit' }}>
                {grade.late_penalty_applied > 0 ? `-${grade.late_penalty_applied.toFixed(1)}` : '0'}
              </span>
            </div>
            <div>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Final Score</span>
              <span style={{ fontSize: '24px', fontWeight: 700, color: '#2c3e50' }}>{grade.final_score.toFixed(1)}</span>
            </div>
            <div>
              <span style={{ fontSize: '12px', color: '#7f8c8d', display: 'block' }}>Status</span>
              <span style={{
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                backgroundColor: grade.published ? '#2ecc71' : '#f39c12',
                color: 'white',
              }}>
                {grade.published ? 'Published' : 'Draft'}
              </span>
            </div>
          </div>

          {editingScore && (
            <div style={{ padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
              <h4 style={{ marginTop: 0, color: '#2c3e50' }}>Edit Grade</h4>
              <div style={{ marginBottom: '10px' }}>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 600, fontSize: '14px' }}>LLM Score (0-100)</label>
                <input
                  type="number"
                  value={editLlmScore}
                  onChange={(e) => setEditLlmScore(Number(e.target.value))}
                  min={0}
                  max={100}
                  style={{ width: '150px', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
                />
              </div>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 600, fontSize: '14px' }}>LLM Feedback</label>
                <textarea
                  value={editFeedback}
                  onChange={(e) => setEditFeedback(e.target.value)}
                  rows={4}
                  style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', resize: 'vertical', boxSizing: 'border-box' }}
                />
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={handleSaveScore}
                  disabled={isSaving}
                  style={{ padding: '8px 16px', backgroundColor: '#2ecc71', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
                <button
                  onClick={() => setEditingScore(false)}
                  style={{ padding: '8px 16px', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
