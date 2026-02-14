import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { classesApi } from '../../api/classes';
import type { Class } from '../../api/classes';

export function ClassesListPage() {
  const [classes, setClasses] = useState<Class[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newClassName, setNewClassName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const loadClasses = async () => {
    try {
      setIsLoading(true);
      const data = await classesApi.list();
      setClasses(data);
    } catch (err) {
      setError('Failed to load classes');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadClasses();
  }, []);

  const handleCreateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    try {
      await classesApi.create(newClassName);
      setNewClassName('');
      setShowCreateForm(false);
      loadClasses();
    } catch (err) {
      alert('Failed to create class');
    } finally {
      setIsCreating(false);
    }
  };

  if (isLoading) {
    return <div>Loading classes...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>My Classes</h1>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          style={{
            padding: '10px 20px',
            backgroundColor: '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          {showCreateForm ? 'Cancel' : 'Create Class'}
        </button>
      </div>

      {error && <div style={{ color: '#c00', marginBottom: '20px' }}>{error}</div>}

      {showCreateForm && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
          <h3>Create New Class</h3>
          <form onSubmit={handleCreateClass}>
            <input
              type="text"
              placeholder="Class name"
              value={newClassName}
              onChange={(e) => setNewClassName(e.target.value)}
              required
              style={{ width: '100%', padding: '8px', marginBottom: '10px', fontSize: '14px' }}
            />
            <button
              type="submit"
              disabled={isCreating}
              style={{
                padding: '8px 16px',
                backgroundColor: '#2ecc71',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              {isCreating ? 'Creating...' : 'Create'}
            </button>
          </form>
        </div>
      )}

      {classes.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>No classes yet. Create your first class to get started!</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
          {classes.map((cls) => (
            <Link
              key={cls.id}
              to={`/professor/classes/${cls.id}`}
              style={{
                textDecoration: 'none',
                backgroundColor: 'white',
                padding: '20px',
                borderRadius: '8px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                transition: 'transform 0.2s',
              }}
            >
              <h3 style={{ margin: '0 0 10px', color: '#2c3e50' }}>{cls.name}</h3>
              <p style={{ margin: '0', fontSize: '12px', color: '#7f8c8d' }}>
                Created {new Date(cls.created_at).toLocaleDateString()}
              </p>
              {cls.archived && (
                <span
                  style={{
                    display: 'inline-block',
                    marginTop: '10px',
                    padding: '4px 8px',
                    backgroundColor: '#e74c3c',
                    color: 'white',
                    fontSize: '12px',
                    borderRadius: '4px',
                  }}
                >
                  Archived
                </span>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
