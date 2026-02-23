import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { onboardingApi } from '../../api/onboarding';
import { messagingApi } from '../../api/messaging';
import { TemplateConfigModal } from '../../components/TemplateConfigModal';
import type { OnboardingStudent, OnboardingSummary } from '../../api/onboarding';
import type { Course } from '../../api/messaging';

const TAGS = ['{primeiro_nome}', '{nome}', '{token}', '{email}'];

const TOKEN_STATUS_DISPLAY: Record<string, { label: string; color: string; bg: string }> = {
  activated: { label: 'Ativado', color: '#166534', bg: '#dcfce7' },
  valid: { label: 'Válido', color: '#1d4ed8', bg: '#dbeafe' },
  expired: { label: 'Expirado', color: '#c2410c', bg: '#fff7ed' },
  none: { label: 'Sem token', color: '#6b7280', bg: '#f3f4f6' },
};

export function OnboardingPage() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<number | undefined>();
  const [students, setStudents] = useState<OnboardingStudent[]>([]);
  const [summary, setSummary] = useState<OnboardingSummary | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [messageTemplate, setMessageTemplate] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagingApi.getCourses().then(setCourses).catch(() => {});
    loadData();
  }, []);

  useEffect(() => {
    loadData();
  }, [selectedCourseId]);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = selectedCourseId ? { course_id: selectedCourseId } : undefined;
      const [studentsData, summaryData] = await Promise.all([
        onboardingApi.getStudents(params),
        onboardingApi.getSummary(params),
      ]);
      setStudents(studentsData);
      setSummary(summaryData);
      setSelectedIds(new Set());
    } catch {
      setError('Erro ao carregar dados de onboarding');
    } finally {
      setIsLoading(false);
    }
  };

  const pendingStudents = students.filter(
    (s) => s.token_status !== 'activated' && s.whatsapp_number
  );
  const activatedStudents = students.filter((s) => s.token_status === 'activated');

  const handleToggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSelectAllPending = () => {
    const pendingIds = pendingStudents.map((s) => s.id);
    if (pendingIds.every((id) => selectedIds.has(id))) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(pendingIds));
    }
  };

  const insertTag = (tag: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = messageTemplate.substring(0, start);
    const after = messageTemplate.substring(end);
    setMessageTemplate(before + tag + after);
    setTimeout(() => {
      textarea.focus();
      textarea.selectionStart = textarea.selectionEnd = start + tag.length;
    }, 0);
  };

  const canSend = selectedIds.size > 0 && messageTemplate.trim().length > 0;

  const handleSend = async () => {
    if (!canSend) return;
    if (!confirm(`Enviar mensagem para ${selectedIds.size} aluno(s)?`)) return;

    setIsSending(true);
    setFeedback(null);
    setError(null);
    try {
      const result = await messagingApi.sendBulk({
        user_ids: Array.from(selectedIds),
        message_template: messageTemplate,
        course_id: selectedCourseId,
      });
      navigate(`/professor/messaging/campaigns/${result.campaign_id}`);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Erro ao enviar mensagem');
    } finally {
      setIsSending(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>Onboarding</h1>
        <button
          onClick={() => setShowConfig(true)}
          style={{
            padding: '8px 16px',
            border: '1px solid #ccc',
            borderRadius: '4px',
            backgroundColor: 'white',
            cursor: 'pointer',
            fontSize: '14px',
          }}
        >
          Configurar templates
        </button>
      </div>

      {error && (
        <div style={{ color: '#c00', marginBottom: '15px', padding: '10px', backgroundColor: '#fef2f2', borderRadius: '4px' }}>
          {error}
        </div>
      )}
      {feedback && (
        <div style={{ color: '#166534', marginBottom: '15px', padding: '10px', backgroundColor: '#f0fdf4', borderRadius: '4px' }}>
          {feedback}
        </div>
      )}

      {/* Course filter */}
      <div style={{ marginBottom: '20px' }}>
        <select
          value={selectedCourseId ?? ''}
          onChange={(e) => setSelectedCourseId(e.target.value ? Number(e.target.value) : undefined)}
          style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #ccc', width: '100%', maxWidth: '400px' }}
        >
          <option value="">Todos os cursos</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* Summary bar */}
      {summary && (
        <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' }}>
          {[
            { label: 'Total', value: summary.total, color: '#2c3e50', bg: '#ecf0f1' },
            { label: 'Ativados', value: summary.activated, color: '#166534', bg: '#dcfce7' },
            { label: 'Pendentes', value: summary.pending, color: '#d97706', bg: '#fef3c7' },
            { label: 'Sem WhatsApp', value: summary.no_whatsapp, color: '#991b1b', bg: '#fef2f2' },
          ].map((item) => (
            <div
              key={item.label}
              style={{
                flex: '1 1 150px',
                backgroundColor: item.bg,
                borderRadius: '8px',
                padding: '16px 20px',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '28px', fontWeight: 700, color: item.color }}>{item.value}</div>
              <div style={{ fontSize: '13px', color: item.color, marginTop: '4px' }}>{item.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Student list */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3 style={{ margin: '0 0 15px', fontSize: '16px', color: '#2c3e50' }}>Alunos</h3>

        {isLoading ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#7f8c8d' }}>Carregando...</div>
        ) : students.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#7f8c8d' }}>Nenhum aluno encontrado</div>
        ) : (
          <>
            {pendingStudents.length > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <button
                  onClick={handleSelectAllPending}
                  style={{ padding: '6px 12px', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', backgroundColor: 'white', fontSize: '13px' }}
                >
                  {pendingStudents.every((s) => selectedIds.has(s.id)) ? 'Desselecionar pendentes' : 'Selecionar pendentes'}
                </button>
                <span style={{ fontSize: '13px', color: '#7f8c8d' }}>{selectedIds.size} selecionado(s)</span>
              </div>
            )}

            <div style={{ border: '1px solid #ecf0f1', borderRadius: '4px', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #ecf0f1', textAlign: 'left', backgroundColor: '#fafafa' }}>
                    <th style={{ padding: '8px 12px', width: '40px' }}></th>
                    <th style={{ padding: '8px 12px' }}>Nome</th>
                    <th style={{ padding: '8px 12px' }}>WhatsApp</th>
                    <th style={{ padding: '8px 12px' }}>Token</th>
                    <th style={{ padding: '8px 12px' }}>Última msg</th>
                  </tr>
                </thead>
                <tbody>
                  {/* Pending students first */}
                  {students.map((s) => {
                    const statusInfo = TOKEN_STATUS_DISPLAY[s.token_status] || TOKEN_STATUS_DISPLAY.none;
                    const isPending = s.token_status !== 'activated';
                    const canSelect = isPending && !!s.whatsapp_number;

                    return (
                      <tr
                        key={s.id}
                        style={{
                          borderBottom: '1px solid #ecf0f1',
                          backgroundColor: selectedIds.has(s.id) ? '#eaf6ff' : 'white',
                          opacity: !isPending ? 0.6 : 1,
                        }}
                      >
                        <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                          {canSelect && (
                            <input
                              type="checkbox"
                              checked={selectedIds.has(s.id)}
                              onChange={() => handleToggleSelect(s.id)}
                            />
                          )}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <span style={{ fontWeight: 500 }}>{s.name || s.email}</span>
                          {s.name && (
                            <span style={{ color: '#7f8c8d', fontSize: '12px', marginLeft: '8px' }}>{s.email}</span>
                          )}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          {s.whatsapp_number ? (
                            <span style={{ fontSize: '12px', color: '#2ecc71' }}>Sim</span>
                          ) : (
                            <span style={{ fontSize: '12px', color: '#e74c3c' }}>Nao</span>
                          )}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <span
                            style={{
                              display: 'inline-block',
                              padding: '2px 8px',
                              borderRadius: '12px',
                              fontSize: '12px',
                              fontWeight: 500,
                              color: statusInfo.color,
                              backgroundColor: statusInfo.bg,
                            }}
                          >
                            {statusInfo.label}
                            {s.token_status === 'valid' && s.token_expires_in_days !== null && (
                              <span style={{ marginLeft: '4px' }}>({s.token_expires_in_days}d)</span>
                            )}
                          </span>
                        </td>
                        <td style={{ padding: '8px 12px', color: '#7f8c8d', fontSize: '13px' }}>
                          {formatDate(s.last_message_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Compose area */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3 style={{ margin: '0 0 15px', fontSize: '16px', color: '#2c3e50' }}>Envio manual</h3>

        <div style={{ display: 'flex', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
          {TAGS.map((tag) => (
            <button
              key={tag}
              onClick={() => insertTag(tag)}
              style={{
                padding: '4px 10px',
                fontSize: '12px',
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
          value={messageTemplate}
          onChange={(e) => setMessageTemplate(e.target.value)}
          placeholder="Escreva sua mensagem aqui... Use {token} para incluir o token do aluno."
          rows={5}
          style={{
            width: '100%',
            padding: '10px 12px',
            border: '1px solid #ccc',
            borderRadius: '4px',
            fontSize: '14px',
            resize: 'vertical',
            fontFamily: 'inherit',
            boxSizing: 'border-box',
            marginBottom: '10px',
          }}
        />

        {messageTemplate.includes('{token}') && (
          <p style={{ margin: '0 0 10px', fontSize: '12px', color: '#7f8c8d' }}>
            Tokens expirados ou inexistentes serao gerados automaticamente ao enviar.
          </p>
        )}

        <button
          onClick={handleSend}
          disabled={!canSend || isSending}
          style={{
            padding: '12px 24px',
            backgroundColor: canSend && !isSending ? '#2ecc71' : '#bdc3c7',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: canSend && !isSending ? 'pointer' : 'not-allowed',
            fontSize: '16px',
          }}
        >
          {isSending
            ? 'Enviando...'
            : selectedIds.size > 0
            ? `Enviar para ${selectedIds.size} aluno(s)`
            : 'Enviar'}
        </button>
      </div>

      {/* Template config modal */}
      {showConfig && <TemplateConfigModal onClose={() => setShowConfig(false)} />}
    </div>
  );
}
