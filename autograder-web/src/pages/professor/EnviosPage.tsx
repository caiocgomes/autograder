import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { messagingApi } from '../../api/messaging';
import type { Course, Recipient, Campaign } from '../../api/messaging';
import { TemplateConfigModal } from '../../components/TemplateConfigModal';

const TAGS = ['{nome}', '{primeiro_nome}', '{email}', '{turma}', '{token}'];

const STATUS_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  sending: { label: 'Enviando', color: '#d97706', bg: '#fef3c7' },
  completed: { label: 'Completo', color: '#166534', bg: '#dcfce7' },
  partial_failure: { label: 'Falhas parciais', color: '#c2410c', bg: '#fff7ed' },
  failed: { label: 'Falhou', color: '#991b1b', bg: '#fef2f2' },
};

const LIFECYCLE_FILTERS = [
  { value: '', label: 'Todos' },
  { value: 'pending_payment', label: 'Pending Payment' },
  { value: 'pending_onboarding', label: 'Pending Onboarding' },
  { value: 'active', label: 'Active' },
  { value: 'churned', label: 'Churned' },
];

export function EnviosPage() {
  const navigate = useNavigate();

  // View state
  const [showNewSend, setShowNewSend] = useState(false);
  const [showTemplateConfig, setShowTemplateConfig] = useState(false);

  // Campaigns
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [isLoadingCampaigns, setIsLoadingCampaigns] = useState(false);

  // Audience
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<number | undefined>();
  const [selectedCourseName, setSelectedCourseName] = useState('');
  const [lifecycleFilter, setLifecycleFilter] = useState('');
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isLoadingRecipients, setIsLoadingRecipients] = useState(false);

  // Message
  const [messageTemplate, setMessageTemplate] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Throttle
  const [throttleMin, setThrottleMin] = useState(15);
  const [throttleMax, setThrottleMax] = useState(25);

  // Variations
  const [useVariations, setUseVariations] = useState(false);
  const [variations, setVariations] = useState<string[]>([]);
  const [selectedVariations, setSelectedVariations] = useState<Set<number>>(new Set());
  const [editingVariation, setEditingVariation] = useState<number | null>(null);
  const [isGeneratingVariations, setIsGeneratingVariations] = useState(false);
  const [variationWarning, setVariationWarning] = useState<string | null>(null);

  // UI state
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    messagingApi.getCourses().then(setCourses).catch(() => setError('Erro ao carregar cursos'));
    loadCampaigns();
  }, []);

  const loadCampaigns = () => {
    setIsLoadingCampaigns(true);
    messagingApi
      .getCampaigns({ limit: 50 })
      .then(setCampaigns)
      .catch(() => {})
      .finally(() => setIsLoadingCampaigns(false));
  };

  // Load recipients when course or lifecycle filter changes
  useEffect(() => {
    if (!selectedCourseId) {
      setRecipients([]);
      setSelectedIds(new Set());
      return;
    }
    setIsLoadingRecipients(true);
    const params: { course_id: number; lifecycle_status?: string } = { course_id: selectedCourseId };
    if (lifecycleFilter) params.lifecycle_status = lifecycleFilter;
    messagingApi
      .getRecipients(params)
      .then((data) => {
        setRecipients(data);
        setSelectedIds(new Set());
      })
      .catch(() => setError('Erro ao carregar destinatários'))
      .finally(() => setIsLoadingRecipients(false));
  }, [selectedCourseId, lifecycleFilter]);

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
    const withWhatsapp = recipients.filter((r) => r.has_whatsapp);
    if (selectedIds.size === withWhatsapp.length && withWhatsapp.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(withWhatsapp.map((r) => r.id)));
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

  const handleGenerateVariations = async () => {
    if (!messageTemplate.trim()) return;
    setIsGeneratingVariations(true);
    setVariationWarning(null);
    setError(null);
    try {
      const result = await messagingApi.generateVariations({
        message_template: messageTemplate,
        num_variations: 6,
      });
      setVariations(result.variations);
      setSelectedVariations(new Set(result.variations.map((_, i) => i)));
      setVariationWarning(result.warning);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Erro ao gerar variações');
    } finally {
      setIsGeneratingVariations(false);
    }
  };

  const handleToggleVariation = (index: number) => {
    setSelectedVariations((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const handleEditVariation = (index: number, newText: string) => {
    setVariations((prev) => prev.map((v, i) => (i === index ? newText : v)));
  };

  const approvedVariations = variations.filter((_, i) => selectedVariations.has(i));
  const selectedRecipients = recipients.filter((r) => selectedIds.has(r.id));
  const selectedWithWhatsapp = selectedRecipients.filter((r) => r.has_whatsapp);
  const selectedWithoutWhatsapp = selectedRecipients.filter((r) => !r.has_whatsapp);
  const recipientsWithoutWhatsapp = recipients.filter((r) => !r.has_whatsapp);

  const previewRecipient = selectedWithWhatsapp[0];
  const previewMessage = previewRecipient
    ? messageTemplate
        .replace(/\{nome\}/g, previewRecipient.name)
        .replace(/\{primeiro_nome\}/g, previewRecipient.name.split(' ')[0])
        .replace(/\{email\}/g, previewRecipient.email)
        .replace(/\{turma\}/g, selectedCourseName)
        .replace(/\{token\}/g, 'ABC12345')
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
    setError(null);
    try {
      const request: any = {
        user_ids: Array.from(selectedIds),
        message_template: messageTemplate,
        course_id: selectedCourseId,
        throttle_min_seconds: throttleMin,
        throttle_max_seconds: throttleMax,
      };
      if (useVariations && approvedVariations.length > 0) {
        request.variations = approvedVariations;
      }
      const result = await messagingApi.sendBulk(request);
      navigate(`/professor/envios/campaigns/${result.campaign_id}`);
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>Envios</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => setShowTemplateConfig(true)}
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
          <button
            onClick={() => setShowNewSend(!showNewSend)}
            style={{
              padding: '8px 16px',
              backgroundColor: showNewSend ? '#e74c3c' : '#2ecc71',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            {showNewSend ? 'Cancelar' : '+ Novo Envio'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ color: '#c00', marginBottom: '15px', padding: '10px', backgroundColor: '#fef2f2', borderRadius: '4px' }}>
          {error}
        </div>
      )}

      {/* New Send Flow */}
      {showNewSend && (
        <div style={{ marginBottom: '30px' }}>
          {/* Audience */}
          <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
            <h3 style={{ margin: '0 0 15px', fontSize: '16px', color: '#2c3e50' }}>Audiência</h3>

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

            {selectedCourseId && (
              <div style={{ display: 'flex', gap: '8px', marginBottom: '15px', flexWrap: 'wrap' }}>
                {LIFECYCLE_FILTERS.map((f) => (
                  <button
                    key={f.value}
                    onClick={() => setLifecycleFilter(f.value)}
                    style={{
                      padding: '6px 14px',
                      fontSize: '13px',
                      border: lifecycleFilter === f.value ? '2px solid #3498db' : '1px solid #ccc',
                      borderRadius: '20px',
                      backgroundColor: lifecycleFilter === f.value ? '#eaf6ff' : 'white',
                      color: lifecycleFilter === f.value ? '#2980b9' : '#555',
                      cursor: 'pointer',
                      fontWeight: lifecycleFilter === f.value ? 600 : 400,
                    }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            )}

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
                    {selectedIds.size === recipients.filter((r) => r.has_whatsapp).length && recipients.filter((r) => r.has_whatsapp).length > 0
                      ? 'Desselecionar todos'
                      : 'Selecionar todos com WhatsApp'}
                  </button>
                  <span style={{ fontSize: '13px', color: '#7f8c8d' }}>
                    {selectedIds.size} selecionado(s)
                    {recipientsWithoutWhatsapp.length > 0 && ` (${recipientsWithoutWhatsapp.length} sem WhatsApp)`}
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
                        cursor: r.has_whatsapp ? 'pointer' : 'default',
                        backgroundColor: selectedIds.has(r.id) ? '#eaf6ff' : 'white',
                        opacity: r.has_whatsapp ? 1 : 0.5,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.has(r.id)}
                        onChange={() => handleToggleSelect(r.id)}
                        disabled={!r.has_whatsapp}
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

          {/* Message */}
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

            {messageTemplate.includes('{token}') && (
              <div style={{ marginTop: '8px', fontSize: '12px', color: '#8e44ad', padding: '6px 10px', backgroundColor: '#f5f0ff', borderRadius: '4px' }}>
                Mensagens com {'{'} token {'}'} geram/regeneram o token de onboarding automaticamente.
              </div>
            )}
          </div>

          {/* Variations */}
          <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: useVariations ? '15px' : '0' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={useVariations}
                  onChange={(e) => {
                    setUseVariations(e.target.checked);
                    if (!e.target.checked) {
                      setVariations([]);
                      setSelectedVariations(new Set());
                      setVariationWarning(null);
                    }
                  }}
                />
                <span style={{ fontSize: '14px', fontWeight: 500 }}>Gerar variações (anti-spam)</span>
              </label>
              {useVariations && (
                <button
                  onClick={handleGenerateVariations}
                  disabled={!messageTemplate.trim() || isGeneratingVariations}
                  style={{
                    padding: '6px 14px',
                    fontSize: '13px',
                    border: '1px solid #8e44ad',
                    borderRadius: '4px',
                    backgroundColor: !messageTemplate.trim() || isGeneratingVariations ? '#e8e8e8' : 'white',
                    color: !messageTemplate.trim() || isGeneratingVariations ? '#999' : '#8e44ad',
                    cursor: !messageTemplate.trim() || isGeneratingVariations ? 'not-allowed' : 'pointer',
                  }}
                >
                  {isGeneratingVariations ? 'Gerando...' : variations.length > 0 ? 'Regenerar' : 'Gerar variações'}
                </button>
              )}
            </div>

            {useVariations && variationWarning && (
              <div style={{ color: '#d97706', fontSize: '13px', marginBottom: '10px', padding: '8px', backgroundColor: '#fef3c7', borderRadius: '4px' }}>
                {variationWarning}
              </div>
            )}

            {useVariations && variations.length > 0 && (
              <div style={{ border: '1px solid #ecf0f1', borderRadius: '4px' }}>
                {variations.map((v, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '10px',
                      padding: '10px 12px',
                      borderBottom: i < variations.length - 1 ? '1px solid #ecf0f1' : 'none',
                      backgroundColor: selectedVariations.has(i) ? '#f0fdf4' : '#fafafa',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedVariations.has(i)}
                      onChange={() => handleToggleVariation(i)}
                      style={{ marginTop: '3px' }}
                    />
                    <div style={{ flex: 1 }}>
                      {editingVariation === i ? (
                        <textarea
                          value={v}
                          onChange={(e) => handleEditVariation(i, e.target.value)}
                          onBlur={() => setEditingVariation(null)}
                          onKeyDown={(e) => { if (e.key === 'Escape') setEditingVariation(null); }}
                          autoFocus
                          rows={3}
                          style={{
                            width: '100%',
                            padding: '6px 8px',
                            border: '1px solid #3498db',
                            borderRadius: '4px',
                            fontSize: '13px',
                            resize: 'vertical',
                            fontFamily: 'inherit',
                            boxSizing: 'border-box',
                          }}
                        />
                      ) : (
                        <div
                          onClick={() => setEditingVariation(i)}
                          style={{ fontSize: '13px', cursor: 'text', whiteSpace: 'pre-wrap', minHeight: '20px' }}
                        >
                          {v}
                        </div>
                      )}
                    </div>
                    <span style={{ fontSize: '11px', color: '#999', whiteSpace: 'nowrap' }}>#{i + 1}</span>
                  </div>
                ))}
                <div style={{ padding: '8px 12px', fontSize: '12px', color: '#7f8c8d', backgroundColor: '#f8f9fa' }}>
                  {approvedVariations.length} de {variations.length} variação(ões) selecionada(s). Clique no texto para editar.
                </div>
              </div>
            )}
          </div>

          {/* Throttle + Preview + Send */}
          <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '20px' }}>
              <span style={{ fontSize: '14px', fontWeight: 500, color: '#2c3e50' }}>Throttle:</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="number"
                  value={throttleMin}
                  onChange={(e) => setThrottleMin(Number(e.target.value))}
                  min={5}
                  max={60}
                  style={{ width: '60px', padding: '4px 8px', border: '1px solid #ccc', borderRadius: '4px', textAlign: 'center' }}
                />
                <span style={{ color: '#7f8c8d' }}>-</span>
                <input
                  type="number"
                  value={throttleMax}
                  onChange={(e) => setThrottleMax(Number(e.target.value))}
                  min={5}
                  max={120}
                  style={{ width: '60px', padding: '4px 8px', border: '1px solid #ccc', borderRadius: '4px', textAlign: 'center' }}
                />
                <span style={{ fontSize: '13px', color: '#7f8c8d' }}>segundos entre mensagens</span>
              </div>
            </div>

            {previewRecipient && messageTemplate.trim() && (
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '14px', color: '#2c3e50' }}>Preview</h4>
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
                ? `Enviar para ${selectedWithWhatsapp.length} aluno(s)`
                : 'Enviar'}
            </button>
          </div>
        </div>
      )}

      {/* Campaign list */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px' }}>
        <h3 style={{ margin: '0 0 15px', fontSize: '16px', color: '#2c3e50' }}>Campanhas</h3>

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
                    onClick={() => navigate(`/professor/envios/campaigns/${c.id}`)}
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

      {showTemplateConfig && (
        <TemplateConfigModal onClose={() => setShowTemplateConfig(false)} />
      )}
    </div>
  );
}
