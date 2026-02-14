import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { classesApi } from '../../api/classes';
import type { ClassWithDetails } from '../../api/classes';

export function ClassDetailPage() {
  const { id } = useParams<{ id: string }>();
  const classId = id ? parseInt(id) : 0;

  const [classData, setClassData] = useState<ClassWithDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddStudentsForm, setShowAddStudentsForm] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [showInviteCode, setShowInviteCode] = useState(false);

  const loadClass = async () => {
    try {
      setIsLoading(true);
      const data = await classesApi.get(classId);
      setClassData(data);
    } catch (err) {
      setError('Failed to load class details');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (classId) {
      loadClass();
    }
  }, [classId]);

  const handleCsvUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile) return;

    setIsUploading(true);
    try {
      await classesApi.addStudents(classId, csvFile);
      setCsvFile(null);
      setShowAddStudentsForm(false);
      loadClass();
    } catch (err) {
      alert('Failed to upload students');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveStudent = async (studentId: number) => {
    if (!confirm('Remove this student from the class?')) return;

    try {
      await classesApi.removeStudent(classId, studentId);
      loadClass();
    } catch (err) {
      alert('Failed to remove student');
    }
  };

  const copyInviteCode = () => {
    if (classData) {
      navigator.clipboard.writeText(classData.invite_code);
      alert('Invite code copied to clipboard!');
    }
  };

  if (isLoading) {
    return <div>Loading class details...</div>;
  }

  if (error || !classData) {
    return <div style={{ color: '#c00' }}>{error || 'Class not found'}</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: '30px' }}>
        <h1 style={{ margin: '0 0 10px' }}>{classData.name}</h1>
        <p style={{ margin: 0, color: '#7f8c8d' }}>
          Created {new Date(classData.created_at).toLocaleDateString()}
        </p>
      </div>

      {/* Invite Code Section */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h2 style={{ margin: '0 0 15px' }}>Invite Code</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => setShowInviteCode(!showInviteCode)}
            style={{
              padding: '8px 16px',
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            {showInviteCode ? 'Hide Code' : 'Show Code'}
          </button>
          {showInviteCode && (
            <>
              <code
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#ecf0f1',
                  borderRadius: '4px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                }}
              >
                {classData.invite_code}
              </code>
              <button
                onClick={copyInviteCode}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#2ecc71',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                Copy
              </button>
            </>
          )}
        </div>
      </div>

      {/* Students Section */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h2 style={{ margin: 0 }}>Students ({classData.students.length})</h2>
          <button
            onClick={() => setShowAddStudentsForm(!showAddStudentsForm)}
            style={{
              padding: '8px 16px',
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            {showAddStudentsForm ? 'Cancel' : 'Add Students (CSV)'}
          </button>
        </div>

        {showAddStudentsForm && (
          <form onSubmit={handleCsvUpload} style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#ecf0f1', borderRadius: '4px' }}>
            <p style={{ margin: '0 0 10px', fontSize: '14px' }}>Upload a CSV file with columns: email, name</p>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
              required
              style={{ marginBottom: '10px' }}
            />
            <button
              type="submit"
              disabled={isUploading || !csvFile}
              style={{
                padding: '8px 16px',
                backgroundColor: '#2ecc71',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              {isUploading ? 'Uploading...' : 'Upload'}
            </button>
          </form>
        )}

        {classData.students.length === 0 ? (
          <p style={{ color: '#7f8c8d' }}>No students enrolled yet.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ecf0f1' }}>
                <th style={{ padding: '10px', textAlign: 'left' }}>Email</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Enrolled</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {classData.students.map((student) => (
                <tr key={student.id} style={{ borderBottom: '1px solid #ecf0f1' }}>
                  <td style={{ padding: '10px' }}>{student.email}</td>
                  <td style={{ padding: '10px' }}>{new Date(student.enrolled_at).toLocaleDateString()}</td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    <button
                      onClick={() => handleRemoveStudent(student.id)}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: '#e74c3c',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '12px',
                      }}
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

      {/* Groups Section */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px' }}>
        <h2 style={{ margin: '0 0 15px' }}>Groups ({classData.groups.length})</h2>
        {classData.groups.length === 0 ? (
          <p style={{ color: '#7f8c8d' }}>No groups created yet.</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '15px' }}>
            {classData.groups.map((group) => (
              <div
                key={group.id}
                style={{
                  padding: '15px',
                  backgroundColor: '#ecf0f1',
                  borderRadius: '4px',
                }}
              >
                <h4 style={{ margin: '0 0 10px' }}>{group.name}</h4>
                <p style={{ margin: 0, fontSize: '12px', color: '#7f8c8d' }}>
                  {group.members.length} members
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
