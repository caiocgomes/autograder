import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { gradesApi } from '../../api/grades';
import { classesApi } from '../../api/classes';
import type { GradeListItem } from '../../api/grades';
import type { Class } from '../../api/classes';

export function GradesPage() {
  const [grades, setGrades] = useState<GradeListItem[]>([]);
  const [classes, setClasses] = useState<Class[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedClassId, setSelectedClassId] = useState<number | undefined>(undefined);
  const [publishedFilter, setPublishedFilter] = useState<boolean | undefined>(undefined);
  const [selectedGrades, setSelectedGrades] = useState<Set<number>>(new Set());
  const [isPublishing, setIsPublishing] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    classesApi.list().then(setClasses).catch(() => {});
  }, []);

  const loadGrades = async () => {
    try {
      setIsLoading(true);
      const params: { class_id?: number; published_only?: boolean } = {};
      if (selectedClassId) params.class_id = selectedClassId;
      if (publishedFilter !== undefined) params.published_only = publishedFilter;
      const data = await gradesApi.list(params);
      setGrades(data);
    } catch {
      setError('Failed to load grades');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadGrades();
  }, [selectedClassId, publishedFilter]);

  const handleToggleSelect = (gradeId: number) => {
    setSelectedGrades((prev) => {
      const next = new Set(prev);
      if (next.has(gradeId)) next.delete(gradeId);
      else next.add(gradeId);
      return next;
    });
  };

  const handleSelectAll = () => {
    const unpublished = grades.filter((g) => !g.published).map((g) => g.grade_id);
    if (selectedGrades.size === unpublished.length) {
      setSelectedGrades(new Set());
    } else {
      setSelectedGrades(new Set(unpublished));
    }
  };

  const handleBatchPublish = async () => {
    if (selectedGrades.size === 0) return;
    setIsPublishing(true);
    try {
      await Promise.all(Array.from(selectedGrades).map((id) => gradesApi.publish(id)));
      setSelectedGrades(new Set());
      loadGrades();
    } catch {
      alert('Some grades failed to publish');
    } finally {
      setIsPublishing(false);
    }
  };

  const handleExportCsv = async () => {
    if (!selectedClassId) {
      alert('Select a class first to export grades.');
      return;
    }
    try {
      const blob = await gradesApi.exportCsv(selectedClassId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `grades_class_${selectedClassId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Failed to export CSV');
    }
  };

  if (isLoading && grades.length === 0) return <div>Loading grades...</div>;

  const unpublishedCount = grades.filter((g) => !g.published).length;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>Grades</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          {selectedGrades.size > 0 && (
            <button
              onClick={handleBatchPublish}
              disabled={isPublishing}
              style={{ padding: '8px 16px', backgroundColor: '#2ecc71', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              {isPublishing ? 'Publishing...' : `Publish ${selectedGrades.size} Selected`}
            </button>
          )}
          <button
            onClick={handleExportCsv}
            style={{ padding: '8px 16px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Export CSV
          </button>
        </div>
      </div>

      {error && <div style={{ color: '#c00', marginBottom: '15px' }}>{error}</div>}

      {/* Filters */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', alignItems: 'center' }}>
        <select
          value={selectedClassId ?? ''}
          onChange={(e) => setSelectedClassId(e.target.value ? Number(e.target.value) : undefined)}
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        >
          <option value="">All classes</option>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <select
          value={publishedFilter === undefined ? '' : String(publishedFilter)}
          onChange={(e) => setPublishedFilter(e.target.value === '' ? undefined : e.target.value === 'true')}
          style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        >
          <option value="">All grades</option>
          <option value="true">Published only</option>
          <option value="false">Unpublished only</option>
        </select>
        {unpublishedCount > 0 && (
          <button
            onClick={handleSelectAll}
            style={{ padding: '6px 12px', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', backgroundColor: 'white', fontSize: '13px' }}
          >
            {selectedGrades.size === unpublishedCount ? 'Deselect All' : 'Select All Unpublished'}
          </button>
        )}
      </div>

      {grades.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>No grades found for the current filters.</p>
        </div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: 'white', borderRadius: '8px', overflow: 'hidden' }}>
          <thead>
            <tr style={{ backgroundColor: '#34495e', color: 'white' }}>
              <th style={{ padding: '12px 10px', width: '40px' }}></th>
              <th style={{ padding: '12px 15px', textAlign: 'left' }}>Student</th>
              <th style={{ padding: '12px 15px', textAlign: 'left' }}>Exercise</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Test Score</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>LLM Score</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Final</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Penalty</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Status</th>
              <th style={{ padding: '12px 15px', textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {grades.map((g) => (
              <tr key={g.grade_id} style={{ borderBottom: '1px solid #ecf0f1' }}>
                <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                  {!g.published && (
                    <input
                      type="checkbox"
                      checked={selectedGrades.has(g.grade_id)}
                      onChange={() => handleToggleSelect(g.grade_id)}
                    />
                  )}
                </td>
                <td style={{ padding: '12px 15px' }}>#{g.student_id}</td>
                <td style={{ padding: '12px 15px' }}>#{g.exercise_id}</td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  {g.test_score != null ? `${g.test_score.toFixed(1)}%` : '—'}
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  {g.llm_score != null ? `${g.llm_score.toFixed(1)}` : '—'}
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center', fontWeight: 600 }}>
                  {g.final_score.toFixed(1)}
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center', color: g.late_penalty_applied > 0 ? '#e74c3c' : '#7f8c8d' }}>
                  {g.late_penalty_applied > 0 ? `-${g.late_penalty_applied.toFixed(1)}` : '0'}
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    backgroundColor: g.published ? '#2ecc71' : '#f39c12',
                    color: 'white',
                  }}>
                    {g.published ? 'Published' : 'Draft'}
                  </span>
                </td>
                <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                  <button
                    onClick={() => navigate(`/professor/submissions/${g.submission_id}/review`)}
                    style={{ padding: '5px 10px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', marginRight: '5px' }}
                  >
                    Review
                  </button>
                  {!g.published && (
                    <button
                      onClick={async () => { await gradesApi.publish(g.grade_id); loadGrades(); }}
                      style={{ padding: '5px 10px', backgroundColor: '#2ecc71', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                    >
                      Publish
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
