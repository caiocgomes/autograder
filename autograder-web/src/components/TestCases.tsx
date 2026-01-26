import type { TestCase } from '../types';

interface TestCasesProps {
  testCases: TestCase[];
  onChange: (testCases: TestCase[]) => void;
}

export function TestCases({ testCases, onChange }: TestCasesProps) {
  const addTestCase = () => {
    onChange([...testCases, { input: '', expected: '' }]);
  };

  const removeTestCase = (index: number) => {
    onChange(testCases.filter((_, i) => i !== index));
  };

  const updateTestCase = (index: number, field: keyof TestCase, value: string) => {
    const updated = testCases.map((tc, i) =>
      i === index ? { ...tc, [field]: value } : tc
    );
    onChange(updated);
  };

  return (
    <div className="test-cases">
      <div className="test-cases-header">
        <label>Test Cases</label>
        <button type="button" onClick={addTestCase} className="btn-add">
          + Add Test
        </button>
      </div>
      {testCases.map((tc, index) => (
        <div key={index} className="test-case">
          <div className="test-case-inputs">
            <input
              type="text"
              value={tc.input}
              onChange={(e) => updateTestCase(index, 'input', e.target.value)}
              placeholder="add(1, 2)"
            />
            <span className="arrow">=</span>
            <input
              type="text"
              value={tc.expected}
              onChange={(e) => updateTestCase(index, 'expected', e.target.value)}
              placeholder="3"
            />
          </div>
          {testCases.length > 1 && (
            <button
              type="button"
              onClick={() => removeTestCase(index)}
              className="btn-remove"
            >
              x
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
