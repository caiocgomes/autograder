import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { submissionsApi } from '../../api/submissions';

export function SubmissionDiffPage() {
  const { id, comparisonId } = useParams<{ id: string; comparisonId: string }>();
  const navigate = useNavigate();
  const [diff, setDiff] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        const data = await submissionsApi.getDiff(Number(id), Number(comparisonId));
        setDiff(data);
      } catch {
        setError('Failed to load diff');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [id, comparisonId]);

  if (isLoading) return <div>Loading diff...</div>;
  if (error) return <div style={{ color: '#c00' }}>{error}</div>;

  return (
    <div style={{ maxWidth: '900px' }}>
      <button
        onClick={() => navigate(-1)}
        style={{ padding: '6px 12px', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginBottom: '15px' }}
      >
        Back
      </button>
      <h1 style={{ marginBottom: '20px' }}>Diff: Submission #{id} vs #{comparisonId}</h1>
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <pre style={{
          backgroundColor: '#1e1e1e',
          color: '#d4d4d4',
          padding: '15px',
          borderRadius: '4px',
          overflow: 'auto',
          fontSize: '13px',
          lineHeight: '1.5',
          fontFamily: 'monospace',
          whiteSpace: 'pre-wrap',
        }}>
          {diff || '(no differences)'}
        </pre>
      </div>
    </div>
  );
}
