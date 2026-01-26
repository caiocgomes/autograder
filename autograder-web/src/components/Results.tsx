import type { GradeResponse } from '../types';

interface ResultsProps {
  results: GradeResponse | null;
  loading: boolean;
  error: string | null;
}

export function Results({ results, loading, error }: ResultsProps) {
  if (loading) {
    return (
      <div className="results loading">
        <div className="spinner"></div>
        <p>Grading submission...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="results error">
        <h3>Error</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="results empty">
        <p>Submit your code to see results</p>
      </div>
    );
  }

  return (
    <div className={`results ${results.passed ? 'passed' : 'failed'}`}>
      <div className="results-header">
        <h3>{results.passed ? 'All Tests Passed!' : 'Some Tests Failed'}</h3>
        <span className="score">{results.score.toFixed(0)}%</span>
      </div>

      <div className="validation">
        <h4>Code Validation</h4>
        <div className={`validation-status ${results.llm_validation.valid ? 'valid' : 'invalid'}`}>
          {results.llm_validation.valid ? 'Valid' : 'Invalid'}
        </div>
        <p>{results.llm_validation.feedback}</p>
      </div>

      <div className="test-results">
        <h4>Test Results</h4>
        {results.test_results.map((tr, index) => (
          <div key={index} className={`test-result ${tr.passed ? 'passed' : 'failed'}`}>
            <div className="test-result-header">
              <code>{tr.input}</code>
              <span className="status">{tr.passed ? 'PASS' : 'FAIL'}</span>
            </div>
            {!tr.passed && (
              <div className="test-result-details">
                {tr.error ? (
                  <p className="error-msg">{tr.error}</p>
                ) : (
                  <>
                    <p>Expected: <code>{tr.expected}</code></p>
                    <p>Actual: <code>{tr.actual}</code></p>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
