import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { exercisesApi } from '../../api/exercises';
import type { Exercise } from '../../api/exercises';

export function ExercisesListPage() {
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterPublished, setFilterPublished] = useState<boolean | undefined>(undefined);
  const [filterTag, setFilterTag] = useState('');
  const navigate = useNavigate();

  const loadExercises = async () => {
    try {
      setIsLoading(true);
      const params: { published?: boolean; tags?: string } = {};
      if (filterPublished !== undefined) params.published = filterPublished;
      if (filterTag.trim()) params.tags = filterTag.trim();
      const data = await exercisesApi.list(params);
      setExercises(data);
    } catch {
      setError('Failed to load exercises');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadExercises();
  }, [filterPublished, filterTag]);

  const handleTogglePublish = async (exercise: Exercise) => {
    try {
      await exercisesApi.publish(exercise.id, !exercise.published);
      loadExercises();
    } catch {
      alert('Failed to update publish status');
    }
  };

  if (isLoading) return <div>Loading exercises...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>My Exercises</h1>
        <button
          onClick={() => navigate('/professor/exercises/new')}
          style={{
            padding: '10px 20px',
            backgroundColor: '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Create Exercise
        </button>
      </div>

      {error && <div style={{ color: '#c00', marginBottom: '20px' }}>{error}</div>}

      {/* Filters */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', alignItems: 'center' }}>
        <select
          value={filterPublished === undefined ? '' : String(filterPublished)}
          onChange={(e) => setFilterPublished(e.target.value === '' ? undefined : e.target.value === 'true')}
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        >
          <option value="">All statuses</option>
          <option value="true">Published</option>
          <option value="false">Draft</option>
        </select>
        <input
          type="text"
          placeholder="Filter by tag..."
          value={filterTag}
          onChange={(e) => setFilterTag(e.target.value)}
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc', width: '200px' }}
        />
      </div>

      {exercises.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>No exercises yet. Create your first exercise to get started!</p>
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: 'white', borderRadius: '8px', overflow: 'hidden' }}>
          <thead>
            <tr style={{ backgroundColor: '#34495e', color: 'white' }}>
              <th style={{ padding: '12px 15px', textAlign: 'left' }}>Title</th>
              <th style={{ padding: '12px 15px', textAlign: 'left' }}>Tags</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Tests</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>LLM</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Status</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {exercises.map((ex) => (
              <tr key={ex.id} style={{ borderBottom: '1px solid #ecf0f1' }}>
                <td style={{ padding: '12px 15px' }}>
                  <span
                    style={{ color: '#3498db', cursor: 'pointer', fontWeight: 500 }}
                    onClick={() => navigate(`/professor/exercises/${ex.id}`)}
                  >
                    {ex.title}
                  </span>
                </td>
                <td style={{ padding: '12px 15px', color: '#7f8c8d', fontSize: '13px' }}>
                  {ex.tags || '—'}
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  {ex.has_tests ? 'Yes' : 'No'}
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  {ex.llm_grading_enabled ? 'Yes' : 'No'}
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  <span
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      backgroundColor: ex.published ? '#2ecc71' : '#f39c12',
                      color: 'white',
                    }}
                  >
                    {ex.published ? 'Published' : 'Draft'}
                  </span>
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  <button
                    onClick={() => navigate(`/professor/exercises/${ex.id}/edit`)}
                    style={{
                      padding: '5px 10px',
                      backgroundColor: '#3498db',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      marginRight: '5px',
                      fontSize: '12px',
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleTogglePublish(ex)}
                    style={{
                      padding: '5px 10px',
                      backgroundColor: ex.published ? '#e67e22' : '#2ecc71',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '12px',
                    }}
                  >
                    {ex.published ? 'Unpublish' : 'Publish'}
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
