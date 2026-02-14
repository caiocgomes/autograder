import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { gradesApi } from '../../api/grades';
import type { StudentGrade } from '../../api/grades';

export function MyGradesPage() {
  const [grades, setGrades] = useState<StudentGrade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        const data = await gradesApi.getMyGrades();
        setGrades(data);
      } catch {
        setError('Failed to load grades');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, []);

  if (isLoading) return <div>Loading grades...</div>;

  return (
    <div>
      <h1 style={{ marginBottom: '20px' }}>My Grades</h1>

      {error && <div style={{ color: '#c00', marginBottom: '15px' }}>{error}</div>}

      {grades.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>No grades available yet. Submit your work and wait for grading.</p>
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: 'white', borderRadius: '8px', overflow: 'hidden' }}>
          <thead>
            <tr style={{ backgroundColor: '#34495e', color: 'white' }}>
              <th style={{ padding: '12px 15px', textAlign: 'left' }}>Exercise</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Test Score</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>LLM Score</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Final Score</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Penalty</th>
              <th style={{ padding: '12px 15px', textAlign: 'left' }}>Submitted</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Details</th>
            </tr>
          </thead>
          <tbody>
            {grades.map((g) => (
              <tr key={g.grade_id} style={{ borderBottom: '1px solid #ecf0f1' }}>
                <td style={{ padding: '12px 15px', fontWeight: 500 }}>{g.exercise_title}</td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  {g.test_score != null ? `${g.test_score.toFixed(1)}%` : '—'}
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  {g.llm_score != null ? g.llm_score.toFixed(1) : '—'}
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center', fontWeight: 700, fontSize: '16px' }}>
                  {g.final_score.toFixed(1)}
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center', color: g.late_penalty_applied > 0 ? '#e74c3c' : '#7f8c8d' }}>
                  {g.late_penalty_applied > 0 ? `-${g.late_penalty_applied.toFixed(1)}` : '0'}
                </td>
                <td style={{ padding: '12px 15px', fontSize: '13px' }}>{new Date(g.submitted_at).toLocaleString()}</td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  <button
                    onClick={() => navigate(`/student/submissions/${g.submission_id}`)}
                    style={{ padding: '5px 10px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
