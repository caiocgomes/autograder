interface CodeEditorProps {
  code: string;
  onChange: (code: string) => void;
  requirements: string;
  onRequirementsChange: (requirements: string) => void;
}

export function CodeEditor({ code, onChange, requirements, onRequirementsChange }: CodeEditorProps) {
  return (
    <div className="code-editor">
      <div className="field">
        <label htmlFor="requirements">Requirements</label>
        <textarea
          id="requirements"
          value={requirements}
          onChange={(e) => onRequirementsChange(e.target.value)}
          placeholder="Describe what the code should do..."
          rows={2}
        />
      </div>
      <div className="field">
        <label htmlFor="code">Python Code</label>
        <textarea
          id="code"
          value={code}
          onChange={(e) => onChange(e.target.value)}
          placeholder="def add(a, b):&#10;    return a + b"
          rows={12}
          spellCheck={false}
          className="code-input"
        />
      </div>
    </div>
  );
}
