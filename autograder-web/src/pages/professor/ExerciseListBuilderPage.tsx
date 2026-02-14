import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { exercisesApi, exerciseListsApi } from '../../api/exercises';
import type { Exercise, ExerciseListDetail, ExerciseListCreate } from '../../api/exercises';

export function ExerciseListBuilderPage() {
  const { classId } = useParams<{ classId: string }>();
  const navigate = useNavigate();
  const numericClassId = Number(classId);

  const [lists, setLists] = useState<ExerciseListDetail[]>([]);
  const [availableExercises, setAvailableExercises] = useState<Exercise[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create list form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newList, setNewList] = useState<Partial<ExerciseListCreate>>({
    title: '',
    class_id: numericClassId,
    auto_publish_grades: true,
    randomize_order: false,
  });

  // Add exercise to list state
  const [addingToList, setAddingToList] = useState<number | null>(null);
  const [selectedExerciseId, setSelectedExerciseId] = useState<number | 0>(0);
  const [selectedWeight, setSelectedWeight] = useState(1.0);

  const load = async () => {
    try {
      setIsLoading(true);
      const [listsData, exercisesData] = await Promise.all([
        exerciseListsApi.getForClass(numericClassId),
        exercisesApi.list({ published: true }),
      ]);
      setLists(listsData);
      setAvailableExercises(exercisesData);
    } catch {
      setError('Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [classId]);

  const handleCreateList = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await exerciseListsApi.create({
        title: newList.title!,
        class_id: numericClassId,
        opens_at: newList.opens_at,
        closes_at: newList.closes_at,
        late_penalty_percent_per_day: newList.late_penalty_percent_per_day,
        auto_publish_grades: newList.auto_publish_grades,
        randomize_order: newList.randomize_order,
      });
      setShowCreateForm(false);
      setNewList({ title: '', class_id: numericClassId, auto_publish_grades: true, randomize_order: false });
      load();
    } catch {
      alert('Failed to create exercise list');
    }
  };

  const handleAddExercise = async (listId: number) => {
    if (!selectedExerciseId) return;
    const list = lists.find((l) => l.id === listId);
    const position = (list?.exercises.length || 0) + 1;
    try {
      await exerciseListsApi.addExercise(listId, selectedExerciseId, position, selectedWeight);
      setAddingToList(null);
      setSelectedExerciseId(0);
      setSelectedWeight(1.0);
      load();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to add exercise');
    }
  };

  const handleRemoveExercise = async (listId: number, exerciseId: number) => {
    if (!confirm('Remove this exercise from the list?')) return;
    try {
      await exerciseListsApi.removeExercise(listId, exerciseId, true);
      load();
    } catch {
      alert('Failed to remove exercise');
    }
  };

  const handleMoveExercise = async (listId: number, exerciseId: number, newPosition: number) => {
    try {
      await exerciseListsApi.reorderExercise(listId, exerciseId, newPosition);
      load();
    } catch {
      alert('Failed to reorder exercise');
    }
  };

  const formatDate = (ts: number | null) => {
    if (!ts) return 'Not set';
    return new Date(ts * 1000).toLocaleString();
  };

  if (isLoading) return <div>Loading exercise lists...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>Exercise Lists</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => navigate(`/professor/classes/${classId}`)}
            style={{ padding: '8px 16px', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Back to Class
          </button>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            style={{ padding: '8px 16px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            {showCreateForm ? 'Cancel' : 'New List'}
          </button>
        </div>
      </div>

      {error && <div style={{ color: '#c00', marginBottom: '15px' }}>{error}</div>}

      {showCreateForm && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0 }}>Create New Exercise List</h3>
          <form onSubmit={handleCreateList}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 600, fontSize: '14px' }}>Title</label>
                <input
                  type="text"
                  value={newList.title || ''}
                  onChange={(e) => setNewList((p) => ({ ...p, title: e.target.value }))}
                  required
                  style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 600, fontSize: '14px' }}>Late Penalty (%/day)</label>
                <input
                  type="number"
                  value={newList.late_penalty_percent_per_day ?? ''}
                  onChange={(e) => setNewList((p) => ({ ...p, late_penalty_percent_per_day: e.target.value ? Number(e.target.value) : undefined }))}
                  style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
                  min={0}
                  max={100}
                  placeholder="None"
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 600, fontSize: '14px' }}>Opens At</label>
                <input
                  type="datetime-local"
                  onChange={(e) => setNewList((p) => ({ ...p, opens_at: e.target.value ? Math.floor(new Date(e.target.value).getTime() / 1000) : undefined }))}
                  style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 600, fontSize: '14px' }}>Closes At</label>
                <input
                  type="datetime-local"
                  onChange={(e) => setNewList((p) => ({ ...p, closes_at: e.target.value ? Math.floor(new Date(e.target.value).getTime() / 1000) : undefined }))}
                  style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
                />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '20px', marginBottom: '15px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input type="checkbox" checked={newList.auto_publish_grades} onChange={(e) => setNewList((p) => ({ ...p, auto_publish_grades: e.target.checked }))} />
                Auto-publish grades
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input type="checkbox" checked={newList.randomize_order} onChange={(e) => setNewList((p) => ({ ...p, randomize_order: e.target.checked }))} />
                Randomize exercise order per student
              </label>
            </div>
            <button type="submit" style={{ padding: '8px 16px', backgroundColor: '#2ecc71', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              Create List
            </button>
          </form>
        </div>
      )}

      {lists.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>No exercise lists yet. Create one to assign exercises to this class.</p>
        </div>
      ) : (
        lists.map((list) => (
          <div key={list.id} style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
              <div>
                <h3 style={{ margin: '0 0 5px' }}>{list.title}</h3>
                <div style={{ fontSize: '13px', color: '#7f8c8d' }}>
                  Opens: {formatDate(list.opens_at)} | Closes: {formatDate(list.closes_at)}
                  {list.late_penalty_percent_per_day ? ` | Penalty: ${list.late_penalty_percent_per_day}%/day` : ''}
                  {list.randomize_order ? ' | Randomized' : ''}
                </div>
              </div>
              <button
                onClick={() => setAddingToList(addingToList === list.id ? null : list.id)}
                style={{ padding: '6px 12px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}
              >
                {addingToList === list.id ? 'Cancel' : 'Add Exercise'}
              </button>
            </div>

            {addingToList === list.id && (
              <div style={{ padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '4px', marginBottom: '15px', display: 'flex', gap: '10px', alignItems: 'end' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: 600 }}>Exercise</label>
                  <select
                    value={selectedExerciseId}
                    onChange={(e) => setSelectedExerciseId(Number(e.target.value))}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
                  >
                    <option value={0}>Select an exercise...</option>
                    {availableExercises
                      .filter((ex) => !list.exercises.some((le) => le.exercise_id === ex.id))
                      .map((ex) => (
                        <option key={ex.id} value={ex.id}>{ex.title}</option>
                      ))}
                  </select>
                </div>
                <div style={{ width: '100px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: 600 }}>Weight</label>
                  <input
                    type="number"
                    value={selectedWeight}
                    onChange={(e) => setSelectedWeight(Number(e.target.value))}
                    min={0.1}
                    step={0.1}
                    style={{ width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px' }}
                  />
                </div>
                <button
                  onClick={() => handleAddExercise(list.id)}
                  disabled={!selectedExerciseId}
                  style={{ padding: '8px 16px', backgroundColor: '#2ecc71', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  Add
                </button>
              </div>
            )}

            {list.exercises.length === 0 ? (
              <p style={{ color: '#7f8c8d', fontStyle: 'italic' }}>No exercises in this list yet.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #ecf0f1' }}>
                    <th style={{ padding: '8px', textAlign: 'center', width: '50px' }}>#</th>
                    <th style={{ padding: '8px', textAlign: 'left' }}>Exercise</th>
                    <th style={{ padding: '8px', textAlign: 'center', width: '80px' }}>Weight</th>
                    <th style={{ padding: '8px', textAlign: 'center', width: '120px' }}>Order</th>
                    <th style={{ padding: '8px', textAlign: 'center', width: '80px' }}>Remove</th>
                  </tr>
                </thead>
                <tbody>
                  {list.exercises
                    .sort((a, b) => a.position - b.position)
                    .map((ex) => (
                      <tr key={ex.list_item_id} style={{ borderBottom: '1px solid #ecf0f1' }}>
                        <td style={{ padding: '8px', textAlign: 'center', color: '#7f8c8d' }}>{ex.position}</td>
                        <td style={{ padding: '8px' }}>{ex.exercise_title}</td>
                        <td style={{ padding: '8px', textAlign: 'center' }}>{ex.weight}</td>
                        <td style={{ padding: '8px', textAlign: 'center' }}>
                          <button
                            onClick={() => handleMoveExercise(list.id, ex.exercise_id, ex.position - 1)}
                            disabled={ex.position <= 1}
                            style={{ padding: '2px 8px', cursor: 'pointer', border: '1px solid #ccc', borderRadius: '3px', backgroundColor: 'white', marginRight: '4px' }}
                          >
                            Up
                          </button>
                          <button
                            onClick={() => handleMoveExercise(list.id, ex.exercise_id, ex.position + 1)}
                            disabled={ex.position >= list.exercises.length}
                            style={{ padding: '2px 8px', cursor: 'pointer', border: '1px solid #ccc', borderRadius: '3px', backgroundColor: 'white' }}
                          >
                            Down
                          </button>
                        </td>
                        <td style={{ padding: '8px', textAlign: 'center' }}>
                          <button
                            onClick={() => handleRemoveExercise(list.id, ex.exercise_id)}
                            style={{ padding: '4px 8px', backgroundColor: '#e74c3c', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}
          </div>
        ))
      )}
    </div>
  );
}
