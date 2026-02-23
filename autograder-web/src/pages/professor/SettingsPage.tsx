import { useState, useEffect } from 'react';
import { settingsApi } from '../../api/settings';
import type { SystemSettingsResponse } from '../../api/settings';

export function SettingsPage() {
  const [settings, setSettings] = useState<SystemSettingsResponse | null>(null);
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    settingsApi.getSettings()
      .then((data) => {
        setSettings(data);
        setLoading(false);
      })
      .catch(() => {
        setMessage({ type: 'error', text: 'Erro ao carregar configuracoes' });
        setLoading(false);
      });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const payload: Record<string, string> = {};
      if (openaiKey) payload.openai_api_key = openaiKey;
      if (anthropicKey) payload.anthropic_api_key = anthropicKey;

      if (Object.keys(payload).length === 0) {
        setMessage({ type: 'error', text: 'Preencha pelo menos um token para salvar' });
        setSaving(false);
        return;
      }

      const updated = await settingsApi.updateSettings(payload);
      setSettings(updated);
      setOpenaiKey('');
      setAnthropicKey('');
      setMessage({ type: 'success', text: 'Tokens salvos com sucesso!' });
    } catch {
      setMessage({ type: 'error', text: 'Erro ao salvar tokens' });
    }
    setSaving(false);
  };

  if (loading) {
    return <div style={{ padding: '20px' }}>Carregando...</div>;
  }

  return (
    <div>
      <h1 style={{ margin: '0 0 8px', fontSize: '24px' }}>Configuracoes</h1>
      <p style={{ margin: '0 0 30px', color: '#666', fontSize: '14px' }}>
        Tokens de API para integracao com LLMs. Os tokens sao armazenados de forma encriptada.
      </p>

      {message && (
        <div
          style={{
            padding: '12px 16px',
            marginBottom: '20px',
            borderRadius: '6px',
            backgroundColor: message.type === 'success' ? '#d4edda' : '#f8d7da',
            color: message.type === 'success' ? '#155724' : '#721c24',
            border: `1px solid ${message.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`,
          }}
        >
          {message.text}
        </div>
      )}

      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '24px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', fontSize: '14px' }}>
            OpenAI API Key
          </label>
          <div style={{ fontSize: '12px', color: '#888', marginBottom: '8px' }}>
            {settings?.openai_configured
              ? `Configurado: ${settings.openai_api_key_masked}`
              : 'Nao configurado (usando variavel de ambiente se disponivel)'}
          </div>
          <input
            type="password"
            value={openaiKey}
            onChange={(e) => setOpenaiKey(e.target.value)}
            placeholder="sk-proj-..."
            style={{
              width: '100%',
              padding: '10px 12px',
              border: '1px solid #ddd',
              borderRadius: '6px',
              fontSize: '14px',
              fontFamily: 'monospace',
              boxSizing: 'border-box',
            }}
          />
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', fontSize: '14px' }}>
            Anthropic API Key
          </label>
          <div style={{ fontSize: '12px', color: '#888', marginBottom: '8px' }}>
            {settings?.anthropic_configured
              ? `Configurado: ${settings.anthropic_api_key_masked}`
              : 'Nao configurado (usando variavel de ambiente se disponivel)'}
          </div>
          <input
            type="password"
            value={anthropicKey}
            onChange={(e) => setAnthropicKey(e.target.value)}
            placeholder="sk-ant-..."
            style={{
              width: '100%',
              padding: '10px 12px',
              border: '1px solid #ddd',
              borderRadius: '6px',
              fontSize: '14px',
              fontFamily: 'monospace',
              boxSizing: 'border-box',
            }}
          />
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: '10px 24px',
            backgroundColor: saving ? '#95a5a6' : '#2c3e50',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: saving ? 'not-allowed' : 'pointer',
            fontSize: '14px',
            fontWeight: 600,
          }}
        >
          {saving ? 'Salvando...' : 'Salvar Tokens'}
        </button>
      </div>
    </div>
  );
}
