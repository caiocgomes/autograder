import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { messagingApi } from '../../api/messaging';
import type { Course, Recipient, Campaign } from '../../api/messaging';

const TAGS = ['{nome}', '{primeiro_nome}', '{email}', '{turma}'];

const STATUS_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  sending: { label: 'Enviando', color: '#d97706', bg: '#fef3c7' },
  completed: { label: 'Completo', color: '#166534', bg: '#dcfce7' },
  partial_failure: { label: 'Falhas parciais', color: '#c2410c', bg: '#fff7ed' },
  failed: { label: 'Falhou', color: '#991b1b', bg: '#fef2f2' },
};

export function MessagingPage() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<number | undefined>();
  const [selectedCourseName, setSelectedCourseName] = useState('');
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [messageTemplate, setMessageTemplate] = useState('');
  const [isLoadingRecipients, setIsLoadingRecipients] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Campaigns
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [isLoadingCampaigns, setIsLoadingCampaigns] = useState(false);

  // Load courses and campaigns on mount
  useEffect(() => {
    messagingApi.getCourses().then(setCourses).catch(() => setError('Erro ao carregar cursos'));
    loadCampaigns();
  }, []);

  const loadCampaigns = () => {
    setIsLoadingCampaigns(true);
    messagingApi
      .getCampaigns({ limit: 20 })
      .then(setCampaigns)
      .catch(() => {})
      .finally(() => setIsLoadingCampaigns(false));
  };

  // Load recipients when course changes
  useEffect(() => {
    if (!selectedCourseId) {
      setRecipients([]);
      setSelectedIds(new Set());
      return;
    }
    setIsLoadingRecipients(true);
    setFeedback(null);
    messagingApi
      .getRecipients({ course_id: selectedCourseId })
      .then((data) => {
        setRecipients(data);
        setSelectedIds(new Set());
      })
      .catch(() => setError('Erro ao carregar destinatários'))
      .finally(() => setIsLoadingRecipients(false));
  }, [selectedCourseId]);

  const handleCourseChange = (courseId: number | undefined) => {
    setSelectedCourseId(courseId);
    const course = courses.find((c) => c.id === courseId);
    setSelectedCourseName(course?.name || '');
  };

  const handleToggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedIds.size === recipients.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(recipients.map((r) => r.id)));
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

  const selectedRecipients = recipients.filter((r) => selectedIds.has(r.id));
  const selectedWithWhatsapp = selectedRecipients.filter((r) => r.has_whatsapp);
  const selectedWithoutWhatsapp = selectedRecipients.filter((r) => !r.has_whatsapp);

  const previewRecipient = selectedWithWhatsapp[0];
  const previewMessage = previewRecipient
    ? messageTemplate
        .replace(/\{nome\}/g, previewRecipient.name)
        .replace(/\{primeiro_nome\}/g, previewRecipient.name.split(' ')[0])
        .replace(/\{email\}/g, previewRecipient.email)
        .replace(/\{turma\}/g, selectedCourseName)
    : '';

  const canSend = selectedIds.size > 0 && messageTemplate.trim().length > 0 && selectedWithWhatsapp.length > 0;

  const handleSend = async () => {
    if (!canSend) return;
    const withoutCount = selectedWithoutWhatsapp.length;
    const withCount = selectedWithWhatsapp.length;
    const msg = withoutCount > 0
      ? `Enviar mensagem para ${withCount} alunos? (${withoutCount} sem WhatsApp serão ignorados)`
      : `Enviar mensagem para ${withCount} alunos?`;
    if (!confirm(msg)) return;

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

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div>
      <h1 style={{ margin: '0 0 20px' }}>Mensagens</h1>

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

      {/* Destinatários */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3 style={{ margin: '0 0 15px', fontSize: '16px', color: '#2c3e50' }}>Destinatários</h3>

        <div style={{ marginBottom: '15px' }}>
          <select
            value={selectedCourseId ?? ''}
            onChange={(e) => handleCourseChange(e.target.value ? Number(e.target.value) : undefined)}
            style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #ccc', width: '100%', maxWidth: '400px' }}
          >
            <option value="">Selecione um curso</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        {isLoadingRecipients ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#7f8c8d' }}>Carregando...</div>
        ) : recipients.length === 0 && selectedCourseId ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#7f8c8d' }}>Nenhum aluno encontrado</div>
        ) : recipients.length > 0 ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <button
                onClick={handleSelectAll}
                style={{ padding: '6px 12px', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer', backgroundColor: 'white', fontSize: '13px' }}
              >
                {selectedIds.size === recipients.length ? 'Desselecionar todos' : 'Selecionar todos'}
              </button>
              <span style={{ fontSize: '13px', color: '#7f8c8d' }}>
                {selectedIds.size} selecionado(s)
                {selectedWithoutWhatsapp.length > 0 && ` (${selectedWithWhatsapp.length} com WhatsApp)`}
              </span>
            </div>

            <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #ecf0f1', borderRadius: '4px' }}>
              {recipients.map((r) => (
                <label
                  key={r.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '8px 12px',
                    borderBottom: '1px solid #ecf0f1',
                    cursor: 'pointer',
                    backgroundColor: selectedIds.has(r.id) ? '#eaf6ff' : 'white',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(r.id)}
                    onChange={() => handleToggleSelect(r.id)}
                    style={{ marginRight: '10px' }}
                  />
                  <span style={{ flex: 1 }}>
                    <span style={{ fontWeight: 500 }}>{r.name}</span>
                    {r.name !== r.email && (
                      <span style={{ color: '#7f8c8d', fontSize: '12px', marginLeft: '8px' }}>{r.email}</span>
                    )}
                  </span>
                  {r.has_whatsapp ? (
                    <span style={{ fontSize: '12px', color: '#2ecc71' }}>WhatsApp</span>
                  ) : (
                    <span style={{ fontSize: '12px', color: '#e74c3c' }}>sem WhatsApp</span>
                  )}
                </label>
              ))}
            </div>
          </>
        ) : null}
      </div>

      {/* Composição */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3 style={{ margin: '0 0 15px', fontSize: '16px', color: '#2c3e50' }}>Mensagem</h3>

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
          placeholder="Escreva sua mensagem aqui..."
          rows={6}
          style={{
            width: '100%',
            padding: '10px 12px',
            border: '1px solid #ccc',
            borderRadius: '4px',
            fontSize: '14px',
            resize: 'vertical',
            fontFamily: 'inherit',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {/* Preview */}
      {previewRecipient && messageTemplate.trim() && (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
          <h3 style={{ margin: '0 0 10px', fontSize: '16px', color: '#2c3e50' }}>Preview</h3>
          <p style={{ margin: '0 0 8px', fontSize: '12px', color: '#7f8c8d' }}>
            Visualizando para: {previewRecipient.name}
          </p>
          <div
            style={{
              padding: '12px',
              backgroundColor: '#dcf8c6',
              borderRadius: '8px',
              fontSize: '14px',
              whiteSpace: 'pre-wrap',
              maxWidth: '400px',
            }}
          >
            {previewMessage}
          </div>
        </div>
      )}

      {/* Enviar */}
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
          marginBottom: '30px',
        }}
      >
        {isSending
          ? 'Enviando...'
          : selectedIds.size > 0
          ? `Enviar para ${selectedWithWhatsapp.length} aluno(s)`
          : 'Enviar'}
      </button>

      {/* Campanhas recentes */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px' }}>
        <h3 style={{ margin: '0 0 15px', fontSize: '16px', color: '#2c3e50' }}>Envios recentes</h3>

        {isLoadingCampaigns ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#7f8c8d' }}>Carregando...</div>
        ) : campaigns.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#7f8c8d' }}>Nenhum envio registrado</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ecf0f1', textAlign: 'left' }}>
                <th style={{ padding: '8px 12px' }}>Mensagem</th>
                <th style={{ padding: '8px 12px' }}>Curso</th>
                <th style={{ padding: '8px 12px' }}>Progresso</th>
                <th style={{ padding: '8px 12px' }}>Status</th>
                <th style={{ padding: '8px 12px' }}>Data</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => {
                const statusInfo = STATUS_LABELS[c.status] || { label: c.status, color: '#666', bg: '#f0f0f0' };
                return (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/professor/messaging/campaigns/${c.id}`)}
                    style={{ borderBottom: '1px solid #ecf0f1', cursor: 'pointer' }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = '#f8f9fa'; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = 'white'; }}
                  >
                    <td style={{ padding: '10px 12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {c.message_template}
                    </td>
                    <td style={{ padding: '10px 12px', color: '#7f8c8d' }}>{c.course_name || '-'}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ fontWeight: 500 }}>{c.sent_count}</span>
                      <span style={{ color: '#7f8c8d' }}>/{c.total_recipients}</span>
                      {c.failed_count > 0 && (
                        <span style={{ color: '#e74c3c', marginLeft: '4px', fontSize: '12px' }}>
                          ({c.failed_count} falha{c.failed_count > 1 ? 's' : ''})
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 500,
                        color: statusInfo.color,
                        backgroundColor: statusInfo.bg,
                      }}>
                        {statusInfo.label}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', color: '#7f8c8d', fontSize: '13px' }}>
                      {formatDate(c.created_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
