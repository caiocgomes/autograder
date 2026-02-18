import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { exercisesApi } from '../../api/exercises';
import { submissionsApi } from '../../api/submissions';
import type { Exercise } from '../../api/exercises';
import type { SubmissionListItem } from '../../api/submissions';

const ACCEPTED_FILE_TYPES = '.pdf,.xlsx,.png,.jpg,.jpeg';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ExerciseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [submissions, setSubmissions] = useState<SubmissionListItem[]>([]);
  const [code, setCode] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pollingId, setPollingId] = useState<number | null>(null);
  const [pollingStatus, setPollingStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadFileInputRef = useRef<HTMLInputElement>(null);

  const isFileUpload = exercise?.submission_type === 'file_upload';

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        const [ex, subs] = await Promise.all([
          exercisesApi.get(Number(id)),
          submissionsApi.list({ exercise_id: Number(id) }),
        ]);
        setExercise(ex);
        setSubmissions(subs);
        if (ex.template_code && !code) setCode(ex.template_code);
      } catch {
        setError('Failed to load exercise');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [id]);

  // Poll for submission status
  useEffect(() => {
    if (!pollingId) return;
    const interval = setInterval(async () => {
      try {
        const status = await submissionsApi.getStatus(pollingId);
        setPollingStatus(status.status);
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval);
          setPollingId(null);
          // Reload submissions
          const subs = await submissionsApi.list({ exercise_id: Number(id) });
          setSubmissions(subs);
        }
      } catch {
        clearInterval(interval);
        setPollingId(null);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [pollingId, id]);

  const handleSubmitCode = async () => {
    if (!code.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const sub = await submissionsApi.submit(Number(id), code);
      setPollingId(sub.id);
      setPollingStatus(sub.status);
      const subs = await submissionsApi.list({ exercise_id: Number(id) });
      setSubmissions(subs);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit code');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileSubmit = async (file?: File) => {
    const f = file || selectedFile;
    if (!f) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const sub = await submissionsApi.submitFile(Number(id), f);
      setPollingId(sub.id);
      setPollingStatus(sub.status);
      setSelectedFile(null);
      const subs = await submissionsApi.list({ exercise_id: Number(id) });
      setSubmissions(subs);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit file');
    } finally {
      setIsSubmitting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (uploadFileInputRef.current) uploadFileInputRef.current.value = '';
    }
  };

  const handleCodeFileSubmit = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const sub = await submissionsApi.submitFile(Number(id), file);
      setPollingId(sub.id);
      setPollingStatus(sub.status);
      const subs = await submissionsApi.list({ exercise_id: Number(id) });
      setSubmissions(subs);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit file');
    } finally {
      setIsSubmitting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  };

  if (isLoading) return <div>Loading exercise...</div>;
  if (!exercise) return <div>Exercise not found</div>;

  const remainingAttempts = exercise.max_submissions
    ? exercise.max_submissions - submissions.length
    : null;

  return (
    <div style={{ maxWidth: '1000px' }}>
      <button
        onClick={() => navigate(-1)}
        style={{ padding: '6px 12px', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginBottom: '15px' }}
      >
        Back
      </button>

      {/* Exercise Description */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <h1 style={{ margin: '0 0 15px', color: '#2c3e50' }}>{exercise.title}</h1>
        <div style={{ display: 'flex', gap: '15px', marginBottom: '15px', fontSize: '13px', color: '#7f8c8d' }}>
          {!isFileUpload && <span>Language: {exercise.language}</span>}
          {!isFileUpload && <span>Timeout: {exercise.timeout_seconds}s</span>}
          {!isFileUpload && <span>Memory: {exercise.memory_limit_mb}MB</span>}
          {exercise.max_submissions && <span>Max submissions: {exercise.max_submissions}</span>}
          <span style={{ padding: '1px 6px', backgroundColor: isFileUpload ? '#9b59b6' : '#3498db', color: 'white', borderRadius: '3px', fontSize: '11px' }}>
            {isFileUpload ? 'File Upload' : 'Code'}
          </span>
        </div>
        {exercise.tags && (
          <div style={{ marginBottom: '15px' }}>
            {exercise.tags.split(',').map((tag) => (
              <span key={tag.trim()} style={{ display: 'inline-block', padding: '2px 8px', backgroundColor: '#ecf0f1', borderRadius: '3px', fontSize: '12px', marginRight: '5px', color: '#7f8c8d' }}>
                {tag.trim()}
              </span>
            ))}
          </div>
        )}
        <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
          {exercise.description}
        </div>
      </div>

      {/* Submission Area */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h3 style={{ margin: 0, color: '#2c3e50' }}>{isFileUpload ? 'Upload File' : 'Your Code'}</h3>
          {remainingAttempts !== null && (
            <span style={{ fontSize: '13px', color: remainingAttempts <= 1 ? '#e74c3c' : '#7f8c8d' }}>
              {remainingAttempts} attempt{remainingAttempts !== 1 ? 's' : ''} remaining
            </span>
          )}
        </div>

        {error && <div style={{ color: '#c00', marginBottom: '10px', padding: '8px', backgroundColor: '#fee', borderRadius: '4px', fontSize: '13px' }}>{error}</div>}

        {isFileUpload ? (
          /* File Upload UI */
          <>
            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              style={{
                border: '2px dashed #ccc',
                borderRadius: '8px',
                padding: '40px 20px',
                textAlign: 'center',
                backgroundColor: selectedFile ? '#eafaf1' : '#fafafa',
                cursor: 'pointer',
                marginBottom: '10px',
              }}
              onClick={() => uploadFileInputRef.current?.click()}
            >
              {selectedFile ? (
                <div>
                  <p style={{ margin: '0 0 5px', fontWeight: 600, color: '#2c3e50' }}>{selectedFile.name}</p>
                  <p style={{ margin: 0, fontSize: '13px', color: '#7f8c8d' }}>{formatFileSize(selectedFile.size)}</p>
                </div>
              ) : (
                <div>
                  <p style={{ margin: '0 0 5px', color: '#7f8c8d' }}>Drag and drop a file here, or click to browse</p>
                  <p style={{ margin: 0, fontSize: '12px', color: '#95a5a6' }}>Accepted: PDF, XLSX, PNG, JPG (max 10MB)</p>
                </div>
              )}
              <input
                ref={uploadFileInputRef}
                type="file"
                accept={ACCEPTED_FILE_TYPES}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) setSelectedFile(f); }}
                style={{ display: 'none' }}
              />
            </div>
            <button
              onClick={() => handleFileSubmit()}
              disabled={isSubmitting || !selectedFile || (remainingAttempts !== null && remainingAttempts <= 0)}
              style={{
                padding: '10px 24px',
                backgroundColor: '#2ecc71',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: 600,
              }}
            >
              {isSubmitting ? 'Submitting...' : 'Submit File'}
            </button>
          </>
        ) : (
          /* Code Editor UI */
          <>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              rows={15}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #ccc',
                borderRadius: '4px',
                fontFamily: 'monospace',
                fontSize: '14px',
                lineHeight: '1.5',
                resize: 'vertical',
                boxSizing: 'border-box',
                backgroundColor: '#1e1e1e',
                color: '#d4d4d4',
              }}
              placeholder="# Write your code here..."
              spellCheck={false}
            />
            <div style={{ display: 'flex', gap: '10px', marginTop: '10px', alignItems: 'center' }}>
              <button
                onClick={handleSubmitCode}
                disabled={isSubmitting || !code.trim() || (remainingAttempts !== null && remainingAttempts <= 0)}
                style={{
                  padding: '10px 24px',
                  backgroundColor: '#2ecc71',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 600,
                }}
              >
                {isSubmitting ? 'Submitting...' : 'Submit Code'}
              </button>
              <span style={{ color: '#7f8c8d', fontSize: '13px' }}>or</span>
              <label style={{ padding: '10px 16px', backgroundColor: '#3498db', color: 'white', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}>
                Upload File
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".py"
                  onChange={handleCodeFileSubmit}
                  style={{ display: 'none' }}
                />
              </label>
            </div>
          </>
        )}

        {/* Polling indicator */}
        {pollingId && (
          <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#fff9e6', borderRadius: '4px', fontSize: '13px' }}>
            Submission #{pollingId} is <strong>{pollingStatus}</strong>...
            {(pollingStatus === 'queued' || pollingStatus === 'running') && ' Please wait.'}
            {pollingStatus === 'completed' && (
              <button
                onClick={() => navigate(`/student/submissions/${pollingId}`)}
                style={{ marginLeft: '10px', padding: '4px 10px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
              >
                View Results
              </button>
            )}
          </div>
        )}
      </div>

      {/* Submission History */}
      {submissions.length > 0 && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Submission History ({submissions.length})</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ecf0f1' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>#</th>
                {isFileUpload && <th style={{ padding: '8px', textAlign: 'left' }}>File</th>}
                <th style={{ padding: '8px', textAlign: 'center' }}>Status</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Submitted</th>
                <th style={{ padding: '8px', textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((sub, idx) => (
                <tr key={sub.id} style={{ borderBottom: '1px solid #ecf0f1' }}>
                  <td style={{ padding: '8px' }}>{submissions.length - idx}</td>
                  {isFileUpload && (
                    <td style={{ padding: '8px', fontSize: '13px', color: '#555' }}>
                      {sub.file_name || '-'}
                    </td>
                  )}
                  <td style={{ padding: '8px', textAlign: 'center' }}>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      backgroundColor: sub.status === 'completed' ? '#2ecc71' : sub.status === 'failed' ? '#e74c3c' : '#f39c12',
                      color: 'white',
                    }}>
                      {sub.status}
                    </span>
                  </td>
                  <td style={{ padding: '8px', fontSize: '13px' }}>{new Date(sub.submitted_at).toLocaleString()}</td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>
                    <button
                      onClick={() => navigate(`/student/submissions/${sub.id}`)}
                      style={{ padding: '4px 10px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                    >
                      View
                    </button>
                    {!isFileUpload && idx < submissions.length - 1 && (
                      <button
                        onClick={() => navigate(`/student/submissions/${sub.id}/diff/${submissions[idx + 1].id}`)}
                        style={{ padding: '4px 10px', backgroundColor: '#9b59b6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', marginLeft: '5px' }}
                      >
                        Diff
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
