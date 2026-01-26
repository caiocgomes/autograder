import { useState } from 'react';
import { CodeEditor, TestCases, Results } from './components';
import { gradeCode } from './api/grader';
import type { TestCase, GradeResponse } from './types';
import './App.css';

function App() {
  const [code, setCode] = useState('def add(a, b):\n    return a + b');
  const [requirements, setRequirements] = useState('Write a function that adds two numbers');
  const [testCases, setTestCases] = useState<TestCase[]>([
    { input: 'add(1, 2)', expected: '3' },
    { input: 'add(-1, 1)', expected: '0' },
  ]);
  const [results, setResults] = useState<GradeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await gradeCode({
        code,
        requirements,
        test_cases: testCases,
      });
      setResults(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>Autograder</h1>
        <p>Submit Python code for automated grading</p>
      </header>

      <main>
        <form onSubmit={handleSubmit} className="submission-form">
          <CodeEditor
            code={code}
            onChange={setCode}
            requirements={requirements}
            onRequirementsChange={setRequirements}
          />
          <TestCases testCases={testCases} onChange={setTestCases} />
          <button type="submit" disabled={loading} className="btn-submit">
            {loading ? 'Grading...' : 'Grade Code'}
          </button>
        </form>

        <Results results={results} loading={loading} error={error} />
      </main>
    </div>
  );
}

export default App;
