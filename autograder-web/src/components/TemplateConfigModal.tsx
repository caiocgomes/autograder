import { useState, useEffect, useRef } from 'react';
import { onboardingApi } from '../api/onboarding';
import type { TemplateInfo } from '../api/onboarding';

const EVENT_LABELS: Record<string, string> = {
  onboarding: 'Onboarding (token)',
  welcome: 'Boas-vindas',
  welcome_back: 'Retorno',
  churn: 'Cancelamento',
};

const EVENT_VARIABLES: Record<string, string[]> = {
  onboarding: ['{primeiro_nome}', '{nome}', '{token}', '{product_name}'],
  welcome: ['{primeiro_nome}', '{nome}', '{product_name}'],
  welcome_back: ['{primeiro_nome}', '{nome}', '{product_name}'],
  churn: ['{primeiro_nome}', '{nome}', '{product_name}'],
};

interface Props {
  onClose: () => void;
}

export function TemplateConfigModal({ onClose }: Props) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingType, setEditingType] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setIsLoading(true);
    try {
      const data = await onboardingApi.getTemplates();
      setTemplates(data);
    } catch {
      setError('Erro ao carregar templates');
    } finally {
      setIsLoading(false);
    }
  };

  const startEditing = (t: TemplateInfo) => {
    setEditingType(t.event_type);
    setEditText(t.template_text);
    setError(null);
  };

  const cancelEditing = () => {
    setEditingType(null);
    setEditText('');
    setError(null);
  };

  const insertTag = (tag: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = editText.substring(0, start);
    const after = editText.substring(end);
    setEditText(before + tag + after);
    setTimeout(() => {
      textarea.focus();
      textarea.selectionStart = textarea.selectionEnd = start + tag.length;
    }, 0);
  };

  const handleSave = async () => {
    if (!editingType || !editText.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onboardingApi.updateTemplate(editingType, editText);
      await loadTemplates();
      setEditingType(null);
      setEditText('');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Erro ao salvar template');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async (eventType: string) => {
    if (!confirm('Restaurar template para o valor padrão?')) return;
    setError(null);
    try {
      await onboardingApi.deleteTemplate(eventType);
      await loadTemplates();
      if (editingType === eventType) {
        setEditingType(null);
        setEditText('');
      }
    } catch {
      setError('Erro ao restaurar template');
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '24px',
          width: '90%',
          maxWidth: '700px',
          maxHeight: '80vh',
          overflow: 'auto',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '18px', color: '#2c3e50' }}>Templates de mensagens automáticas</h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#7f8c8d' }}
          >
            ×
          </button>
        </div>

        {error && (
          <div style={{ color: '#c00', marginBottom: '15px', padding: '10px', backgroundColor: '#fef2f2', borderRadius: '4px', fontSize: '14px' }}>
            {error}
          </div>
        )}

        {isLoading ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#7f8c8d' }}>Carregando...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {templates.map((t) => (
              <div
                key={t.event_type}
                style={{
                  border: '1px solid #ecf0f1',
                  borderRadius: '6px',
                  padding: '16px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: '14px', color: '#2c3e50' }}>
                      {EVENT_LABELS[t.event_type] || t.event_type}
                    </span>
                    {t.is_default && (
                      <span style={{ marginLeft: '8px', fontSize: '11px', color: '#7f8c8d', fontStyle: 'italic' }}>
                        (padrão)
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {editingType !== t.event_type && (
                      <button
                        onClick={() => startEditing(t)}
                        style={{
                          padding: '4px 12px',
                          fontSize: '12px',
                          border: '1px solid #3498db',
                          borderRadius: '4px',
                          backgroundColor: 'white',
                          color: '#3498db',
                          cursor: 'pointer',
                        }}
                      >
                        Editar
                      </button>
                    )}
                    {!t.is_default && editingType !== t.event_type && (
                      <button
                        onClick={() => handleReset(t.event_type)}
                        style={{
                          padding: '4px 12px',
                          fontSize: '12px',
                          border: '1px solid #e74c3c',
                          borderRadius: '4px',
                          backgroundColor: 'white',
                          color: '#e74c3c',
                          cursor: 'pointer',
                        }}
                      >
                        Restaurar padrão
                      </button>
                    )}
                  </div>
                </div>

                {editingType === t.event_type ? (
                  <div>
                    <div style={{ display: 'flex', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                      {(EVENT_VARIABLES[t.event_type] || []).map((tag) => (
                        <button
                          key={tag}
                          onClick={() => insertTag(tag)}
                          style={{
                            padding: '3px 8px',
                            fontSize: '11px',
                            border: '1px solid #3498db',
                            borderRadius: '4px',
                            backgroundColor: 'white',
                            color: '#3498db',
                            cursor: 'pointer',
                          }}
                        >
                          {tag}
                        </button>
                      ))}
                    </div>
                    <textarea
                      ref={textareaRef}
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      rows={5}
                      style={{
                        width: '100%',
                        padding: '10px',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                        fontSize: '13px',
                        resize: 'vertical',
                        fontFamily: 'inherit',
                        boxSizing: 'border-box',
                        marginBottom: '8px',
                      }}
                    />
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        onClick={handleSave}
                        disabled={saving || !editText.trim()}
                        style={{
                          padding: '6px 16px',
                          fontSize: '13px',
                          border: 'none',
                          borderRadius: '4px',
                          backgroundColor: saving ? '#bdc3c7' : '#2ecc71',
                          color: 'white',
                          cursor: saving ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {saving ? 'Salvando...' : 'Salvar'}
                      </button>
                      <button
                        onClick={cancelEditing}
                        style={{
                          padding: '6px 16px',
                          fontSize: '13px',
                          border: '1px solid #ccc',
                          borderRadius: '4px',
                          backgroundColor: 'white',
                          cursor: 'pointer',
                        }}
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                ) : (
                  <pre
                    style={{
                      margin: 0,
                      padding: '10px',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '4px',
                      fontSize: '13px',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      color: '#2c3e50',
                      lineHeight: '1.5',
                    }}
                  >
                    {t.template_text}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
