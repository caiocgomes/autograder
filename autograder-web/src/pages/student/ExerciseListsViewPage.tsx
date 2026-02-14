import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { exerciseListsApi } from '../../api/exercises';
import type { ExerciseListDetail } from '../../api/exercises';

export function ExerciseListsViewPage() {
  const { classId } = useParams<{ classId: string }>();
  const [lists, setLists] = useState<ExerciseListDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        const data = await exerciseListsApi.getForClass(Number(classId));
        setLists(data);
      } catch {
        setError('Failed to load exercise lists');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [classId]);

  const formatDate = (ts: number | null) => {
    if (!ts) return null;
    return new Date(ts * 1000).toLocaleString();
  };

  const isOpen = (list: ExerciseListDetail) => {
    const now = Math.floor(Date.now() / 1000);
    if (list.opens_at && now < list.opens_at) return false;
    return true;
  };

  const isClosed = (list: ExerciseListDetail) => {
    if (!list.closes_at) return false;
    return Math.floor(Date.now() / 1000) > list.closes_at;
  };

  if (isLoading) return <div>Loading exercise lists...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>Exercise Lists</h1>
        <Link to="/student/classes" style={{ padding: '8px 16px', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', textDecoration: 'none' }}>
          Back to Classes
        </Link>
      </div>

      {error && <div style={{ color: '#c00', marginBottom: '15px' }}>{error}</div>}

      {lists.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>No exercise lists available for this class yet.</p>
        </div>
      ) : (
        lists.map((list) => {
          const closed = isClosed(list);
          const open = isOpen(list);
          return (
            <div key={list.id} style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', opacity: !open ? 0.6 : 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h3 style={{ margin: 0 }}>{list.title}</h3>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {closed && (
                    <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', backgroundColor: '#e74c3c', color: 'white' }}>
                      Closed
                    </span>
                  )}
                  {!open && (
                    <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', backgroundColor: '#f39c12', color: 'white' }}>
                      Not yet open
                    </span>
                  )}
                  {open && !closed && (
                    <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', backgroundColor: '#2ecc71', color: 'white' }}>
                      Open
                    </span>
                  )}
                </div>
              </div>
              <div style={{ fontSize: '13px', color: '#7f8c8d', marginBottom: '15px' }}>
                {list.opens_at && <span>Opens: {formatDate(list.opens_at)}</span>}
                {list.closes_at && <span>{list.opens_at ? ' | ' : ''}Deadline: {formatDate(list.closes_at)}</span>}
                {list.late_penalty_percent_per_day && <span> | Late penalty: {list.late_penalty_percent_per_day}%/day</span>}
              </div>
              {list.exercises.length === 0 ? (
                <p style={{ color: '#7f8c8d', fontStyle: 'italic' }}>No exercises in this list.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {list.exercises
                    .sort((a, b) => a.position - b.position)
                    .map((ex) => (
                      <Link
                        key={ex.list_item_id}
                        to={`/student/exercises/${ex.exercise_id}`}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '10px 15px',
                          backgroundColor: '#f8f9fa',
                          borderRadius: '4px',
                          textDecoration: 'none',
                          color: '#2c3e50',
                        }}
                      >
                        <span>
                          <span style={{ color: '#7f8c8d', marginRight: '10px' }}>{ex.position}.</span>
                          {ex.exercise_title}
                        </span>
                        <span style={{ fontSize: '12px', color: '#7f8c8d' }}>Weight: {ex.weight}</span>
                      </Link>
                    ))}
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
