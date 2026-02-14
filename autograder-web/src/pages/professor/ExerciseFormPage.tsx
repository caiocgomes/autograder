import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { exercisesApi } from '../../api/exercises';
import { apiClient } from '../../api/client';
import type { ExerciseCreate, TestCaseResponse, TestCaseCreate } from '../../api/exercises';

const inputStyle = {
  width: '100%',
  padding: '8px 12px',
  border: '1px solid #ccc',
  borderRadius: '4px',
  fontSize: '14px',
  boxSizing: 'border-box' as const,
};

const labelStyle = {
  display: 'block',
  marginBottom: '4px',
  fontWeight: 600 as const,
  fontSize: '14px',
  color: '#2c3e50',
};

const sectionStyle = {
  backgroundColor: 'white',
  padding: '20px',
  borderRadius: '8px',
  marginBottom: '20px',
  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
};

export function ExerciseFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditing = id && id !== 'new';

  const [form, setForm] = useState<ExerciseCreate>({
    title: '',
    description: '',
    template_code: '',
    language: 'python',
    max_submissions: undefined,
    timeout_seconds: 30,
    memory_limit_mb: 512,
    has_tests: true,
    llm_grading_enabled: false,
    test_weight: 0.7,
    llm_weight: 0.3,
    llm_grading_criteria: '',
    published: false,
    tags: '',
  });

  const [showPreview, setShowPreview] = useState(false);
  const [testCases, setTestCases] = useState<TestCaseResponse[]>([]);
  const [newTest, setNewTest] = useState<TestCaseCreate>({
    name: '',
    input_data: '',
    expected_output: '',
    hidden: false,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(!!isEditing);
  const [error, setError] = useState<string | null>(null);
  const [exerciseId, setExerciseId] = useState<number | null>(isEditing ? Number(id) : null);

  useEffect(() => {
    if (isEditing) {
      loadExercise();
    }
  }, [id]);

  const loadExercise = async () => {
    try {
      const ex = await exercisesApi.get(Number(id), true);
      setForm({
        title: ex.title,
        description: ex.description,
        template_code: ex.template_code || '',
        language: ex.language,
        max_submissions: ex.max_submissions ?? undefined,
        timeout_seconds: ex.timeout_seconds,
        memory_limit_mb: ex.memory_limit_mb,
        has_tests: ex.has_tests,
        llm_grading_enabled: ex.llm_grading_enabled,
        test_weight: ex.test_weight,
        llm_weight: ex.llm_weight,
        llm_grading_criteria: ex.llm_grading_criteria || '',
        published: ex.published,
        tags: ex.tags || '',
      });
      setTestCases(ex.test_cases || []);
      setExerciseId(ex.id);
    } catch {
      setError('Failed to load exercise');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: keyof ExerciseCreate, value: string | number | boolean | undefined) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleWeightChange = (testWeight: number) => {
    const clamped = Math.min(1, Math.max(0, testWeight));
    setForm((prev) => ({ ...prev, test_weight: clamped, llm_weight: Math.round((1 - clamped) * 100) / 100 }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      if (isEditing) {
        await exercisesApi.update(Number(id), form);
      } else {
        const created = await exercisesApi.create(form);
        setExerciseId(created.id);
        navigate(`/professor/exercises/${created.id}/edit`, { replace: true });
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save exercise');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddTestCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!exerciseId) {
      alert('Save the exercise first before adding test cases.');
      return;
    }
    try {
      const created = await exercisesApi.addTestCase(exerciseId, newTest);
      setTestCases((prev) => [...prev, created]);
      setNewTest({ name: '', input_data: '', expected_output: '', hidden: false });
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to add test case');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !exerciseId) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const { data } = await apiClient.post(
        `/exercises/${exerciseId}/dataset`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      alert(`Dataset uploaded: ${data.filename}`);
    } catch {
      alert('Failed to upload dataset');
    }
  };

  if (isLoading) return <div>Loading exercise...</div>;

  return (
    <div style={{ maxWidth: '900px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>{isEditing ? 'Edit Exercise' : 'Create Exercise'}</h1>
        <button
          onClick={() => navigate('/professor/exercises')}
          style={{ padding: '8px 16px', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Back to List
        </button>
      </div>

      {error && <div style={{ color: '#c00', marginBottom: '15px', padding: '10px', backgroundColor: '#fee', borderRadius: '4px' }}>{error}</div>}

      <form onSubmit={handleSubmit}>
        {/* Basic Info */}
        <div style={sectionStyle}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Basic Information</h3>
          <div style={{ marginBottom: '15px' }}>
            <label style={labelStyle}>Title</label>
            <input type="text" value={form.title} onChange={(e) => handleChange('title', e.target.value)} required style={inputStyle} />
          </div>
          <div style={{ marginBottom: '15px' }}>
            <label style={labelStyle}>
              Description (Markdown + LaTeX supported)
              <button
                type="button"
                onClick={() => setShowPreview(!showPreview)}
                style={{ marginLeft: '10px', fontSize: '12px', padding: '2px 8px', cursor: 'pointer', border: '1px solid #ccc', borderRadius: '3px', backgroundColor: showPreview ? '#3498db' : 'white', color: showPreview ? 'white' : '#333' }}
              >
                {showPreview ? 'Edit' : 'Preview'}
              </button>
            </label>
            {showPreview ? (
              <div style={{ ...inputStyle, minHeight: '200px', padding: '12px', backgroundColor: '#fafafa', whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                {form.description || '(empty)'}
              </div>
            ) : (
              <textarea
                value={form.description}
                onChange={(e) => handleChange('description', e.target.value)}
                required
                rows={10}
                style={{ ...inputStyle, fontFamily: 'monospace', resize: 'vertical' }}
              />
            )}
          </div>
          <div style={{ marginBottom: '15px' }}>
            <label style={labelStyle}>Template Code (starter code for students)</label>
            <textarea
              value={form.template_code || ''}
              onChange={(e) => handleChange('template_code', e.target.value)}
              rows={6}
              style={{ ...inputStyle, fontFamily: 'monospace', resize: 'vertical' }}
              placeholder="# Write your code here..."
            />
          </div>
          <div style={{ marginBottom: '15px' }}>
            <label style={labelStyle}>Tags (comma-separated)</label>
            <input type="text" value={form.tags || ''} onChange={(e) => handleChange('tags', e.target.value)} style={inputStyle} placeholder="loops, strings, basics" />
          </div>
          {exerciseId && (
            <div>
              <label style={labelStyle}>Upload Dataset (max 10MB)</label>
              <input type="file" onChange={handleFileUpload} style={{ fontSize: '14px' }} />
            </div>
          )}
        </div>

        {/* Constraints */}
        <div style={sectionStyle}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Constraints</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
            <div>
              <label style={labelStyle}>Max Submissions</label>
              <input type="number" value={form.max_submissions ?? ''} onChange={(e) => handleChange('max_submissions', e.target.value ? Number(e.target.value) : undefined)} style={inputStyle} placeholder="Unlimited" min={1} />
            </div>
            <div>
              <label style={labelStyle}>Timeout (seconds)</label>
              <input type="number" value={form.timeout_seconds} onChange={(e) => handleChange('timeout_seconds', Number(e.target.value))} style={inputStyle} min={1} max={300} />
            </div>
            <div>
              <label style={labelStyle}>Memory Limit (MB)</label>
              <input type="number" value={form.memory_limit_mb} onChange={(e) => handleChange('memory_limit_mb', Number(e.target.value))} style={inputStyle} min={128} max={2048} />
            </div>
          </div>
        </div>

        {/* Grading Config */}
        <div style={sectionStyle}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Grading Configuration</h3>
          <div style={{ display: 'flex', gap: '20px', marginBottom: '15px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <input type="checkbox" checked={form.has_tests} onChange={(e) => handleChange('has_tests', e.target.checked)} />
              Enable Test Cases
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <input type="checkbox" checked={form.llm_grading_enabled} onChange={(e) => handleChange('llm_grading_enabled', e.target.checked)} />
              Enable LLM Grading
            </label>
          </div>
          {form.has_tests && form.llm_grading_enabled && (
            <div style={{ marginBottom: '15px' }}>
              <label style={labelStyle}>Test Weight: {form.test_weight} / LLM Weight: {form.llm_weight}</label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={form.test_weight}
                onChange={(e) => handleWeightChange(Number(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>
          )}
          {form.llm_grading_enabled && (
            <div>
              <label style={labelStyle}>LLM Grading Criteria</label>
              <textarea
                value={form.llm_grading_criteria || ''}
                onChange={(e) => handleChange('llm_grading_criteria', e.target.value)}
                rows={4}
                style={{ ...inputStyle, resize: 'vertical' }}
                placeholder="Describe what the LLM should evaluate: code quality, naming conventions, efficiency..."
              />
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <button
            type="submit"
            disabled={isSubmitting}
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
            {isSubmitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Exercise'}
          </button>
        </div>
      </form>

      {/* Test Cases Section (only when exercise exists) */}
      {exerciseId && form.has_tests && (
        <div style={sectionStyle}>
          <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Test Cases ({testCases.length})</h3>

          {testCases.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '20px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #ecf0f1' }}>
                  <th style={{ padding: '8px', textAlign: 'left' }}>Name</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>Input</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>Expected Output</th>
                  <th style={{ padding: '8px', textAlign: 'center' }}>Hidden</th>
                </tr>
              </thead>
              <tbody>
                {testCases.map((tc) => (
                  <tr key={tc.id} style={{ borderBottom: '1px solid #ecf0f1' }}>
                    <td style={{ padding: '8px' }}>{tc.name}</td>
                    <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '12px' }}>{tc.input_data.substring(0, 80)}</td>
                    <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '12px' }}>{tc.expected_output.substring(0, 80)}</td>
                    <td style={{ padding: '8px', textAlign: 'center' }}>{tc.hidden ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h4 style={{ color: '#2c3e50' }}>Add Test Case</h4>
          <form onSubmit={handleAddTestCase}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
              <div>
                <label style={labelStyle}>Name</label>
                <input type="text" value={newTest.name} onChange={(e) => setNewTest((p) => ({ ...p, name: e.target.value }))} required style={inputStyle} placeholder="test_add_positive" />
              </div>
              <div>
                <label style={{ ...labelStyle, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <input type="checkbox" checked={newTest.hidden} onChange={(e) => setNewTest((p) => ({ ...p, hidden: e.target.checked }))} />
                  Hidden from students
                </label>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
              <div>
                <label style={labelStyle}>Input</label>
                <textarea value={newTest.input_data} onChange={(e) => setNewTest((p) => ({ ...p, input_data: e.target.value }))} required rows={3} style={{ ...inputStyle, fontFamily: 'monospace', resize: 'vertical' }} />
              </div>
              <div>
                <label style={labelStyle}>Expected Output</label>
                <textarea value={newTest.expected_output} onChange={(e) => setNewTest((p) => ({ ...p, expected_output: e.target.value }))} required rows={3} style={{ ...inputStyle, fontFamily: 'monospace', resize: 'vertical' }} />
              </div>
            </div>
            <button
              type="submit"
              style={{ padding: '8px 16px', backgroundColor: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              Add Test Case
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
