import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { classesApi } from '../../api/classes';
import type { Class } from '../../api/classes';

export function MyClassesPage() {
  const [classes, setClasses] = useState<Class[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showJoinForm, setShowJoinForm] = useState(false);
  const [inviteCode, setInviteCode] = useState('');
  const [classIdToJoin, setClassIdToJoin] = useState('');
  const [isJoining, setIsJoining] = useState(false);

  const loadClasses = async () => {
    try {
      setIsLoading(true);
      const data = await classesApi.list();
      setClasses(data);
    } catch {
      setError('Failed to load classes');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadClasses();
  }, []);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsJoining(true);
    try {
      await classesApi.enroll(Number(classIdToJoin), inviteCode);
      setShowJoinForm(false);
      setInviteCode('');
      setClassIdToJoin('');
      loadClasses();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to join class');
    } finally {
      setIsJoining(false);
    }
  };

  if (isLoading) return <div>Loading classes...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>My Classes</h1>
        <button
          onClick={() => setShowJoinForm(!showJoinForm)}
          style={{ padding: '10px 20px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          {showJoinForm ? 'Cancel' : 'Join Class'}
        </button>
      </div>

      {error && <div style={{ color: '#c00', marginBottom: '20px' }}>{error}</div>}

      {showJoinForm && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
          <h3>Join a Class</h3>
          <form onSubmit={handleJoin}>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
              <input
                type="number"
                placeholder="Class ID"
                value={classIdToJoin}
                onChange={(e) => setClassIdToJoin(e.target.value)}
                required
                style={{ padding: '8px', width: '120px', fontSize: '14px', border: '1px solid #ccc', borderRadius: '4px' }}
              />
              <input
                type="text"
                placeholder="Invite code"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                required
                style={{ flex: 1, padding: '8px', fontSize: '14px', border: '1px solid #ccc', borderRadius: '4px' }}
              />
            </div>
            <button
              type="submit"
              disabled={isJoining}
              style={{ padding: '8px 16px', backgroundColor: '#2ecc71', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              {isJoining ? 'Joining...' : 'Join'}
            </button>
          </form>
        </div>
      )}

      {classes.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>You are not enrolled in any classes. Join a class using an invite code.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
          {classes.map((cls) => (
            <Link
              key={cls.id}
              to={`/student/classes/${cls.id}/lists`}
              style={{
                textDecoration: 'none',
                backgroundColor: 'white',
                padding: '20px',
                borderRadius: '8px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              }}
            >
              <h3 style={{ margin: '0 0 10px', color: '#2c3e50' }}>{cls.name}</h3>
              <p style={{ margin: 0, fontSize: '12px', color: '#7f8c8d' }}>
                Enrolled {new Date(cls.created_at).toLocaleDateString()}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
