import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { messagingApi } from '../../api/messaging';
import type { CampaignDetail } from '../../api/messaging';

const STATUS_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  sending: { label: 'Enviando...', color: '#d97706', bg: '#fef3c7' },
  completed: { label: 'Completo', color: '#166534', bg: '#dcfce7' },
  partial_failure: { label: 'Falhas parciais', color: '#c2410c', bg: '#fff7ed' },
  failed: { label: 'Falhou', color: '#991b1b', bg: '#fef2f2' },
};

const RECIPIENT_STATUS: Record<string, { label: string; color: string }> = {
  pending: { label: 'Pendente', color: '#d97706' },
  sent: { label: 'Enviado', color: '#166534' },
  failed: { label: 'Falhou', color: '#991b1b' },
};

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState<CampaignDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadCampaign = async () => {
    if (!id) return;
    try {
      const data = await messagingApi.getCampaign(Number(id));
      setCampaign(data);
      setLoading(false);

      // Stop polling when no longer sending
      if (data.status !== 'sending' && pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    } catch {
      setError('Erro ao carregar campanha');
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaign();
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [id]);

  // Start polling when campaign is sending
  useEffect(() => {
    if (campaign?.status === 'sending' && !pollingRef.current) {
      pollingRef.current = setInterval(loadCampaign, 5000);
    }
    return () => {
      if (pollingRef.current && campaign?.status !== 'sending') {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [campaign?.status]);

  const handleRetry = async () => {
    if (!campaign) return;
    if (!confirm(`Reenviar para ${campaign.failed_count} destinatário(s) que falharam?`)) return;

    setRetrying(true);
    try {
      await messagingApi.retryCampaign(campaign.id);
      // Reload and start polling
      await loadCampaign();
      if (!pollingRef.current) {
        pollingRef.current = setInterval(loadCampaign, 5000);
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Erro ao reenviar');
    } finally {
      setRetrying(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#7f8c8d' }}>Carregando...</div>;
  }

  if (error || !campaign) {
    return (
      <div>
        <button onClick={() => navigate('/professor/envios')} style={backButtonStyle}>Voltar</button>
        <div style={{ color: '#c00', padding: '20px', backgroundColor: '#fef2f2', borderRadius: '4px' }}>
          {error || 'Campanha não encontrada'}
        </div>
      </div>
    );
  }

  const statusInfo = STATUS_LABELS[campaign.status] || { label: campaign.status, color: '#666', bg: '#f0f0f0' };
  const progressPercent = campaign.total_recipients > 0
    ? Math.round(((campaign.sent_count + campaign.failed_count) / campaign.total_recipients) * 100)
    : 0;
  const showRetry = (campaign.status === 'partial_failure' || campaign.status === 'failed') && campaign.failed_count > 0;

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('pt-BR');
  };

  return (
    <div>
      <button onClick={() => navigate('/professor/envios')} style={backButtonStyle}>Voltar</button>

      <h1 style={{ margin: '0 0 20px', fontSize: '20px' }}>Detalhe do envio #{campaign.id}</h1>

      {/* Info card */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px' }}>
          <div>
            <span style={{
              display: 'inline-block',
              padding: '4px 12px',
              borderRadius: '12px',
              fontSize: '13px',
              fontWeight: 500,
              color: statusInfo.color,
              backgroundColor: statusInfo.bg,
            }}>
              {statusInfo.label}
            </span>
            {campaign.course_name && (
              <span style={{ marginLeft: '12px', color: '#7f8c8d', fontSize: '14px' }}>
                {campaign.course_name}
              </span>
            )}
          </div>
          <span style={{ color: '#7f8c8d', fontSize: '13px' }}>{formatDate(campaign.created_at)}</span>
        </div>

        {/* Progress bar */}
        <div style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
            <span>
              <strong>{campaign.sent_count}</strong> enviado{campaign.sent_count !== 1 ? 's' : ''}
              {campaign.failed_count > 0 && (
                <span style={{ color: '#e74c3c', marginLeft: '8px' }}>
                  {campaign.failed_count} falha{campaign.failed_count > 1 ? 's' : ''}
                </span>
              )}
            </span>
            <span style={{ color: '#7f8c8d' }}>{progressPercent}% de {campaign.total_recipients}</span>
          </div>
          <div style={{ height: '8px', backgroundColor: '#ecf0f1', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              display: 'flex',
            }}>
              {campaign.sent_count > 0 && (
                <div style={{
                  width: `${(campaign.sent_count / campaign.total_recipients) * 100}%`,
                  backgroundColor: '#2ecc71',
                  transition: 'width 0.3s ease',
                }} />
              )}
              {campaign.failed_count > 0 && (
                <div style={{
                  width: `${(campaign.failed_count / campaign.total_recipients) * 100}%`,
                  backgroundColor: '#e74c3c',
                  transition: 'width 0.3s ease',
                }} />
              )}
            </div>
          </div>
        </div>

        {/* Template */}
        <div style={{ padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '4px', fontSize: '14px', whiteSpace: 'pre-wrap' }}>
          {campaign.message_template}
        </div>

        {/* Retry button */}
        {showRetry && (
          <button
            onClick={handleRetry}
            disabled={retrying}
            style={{
              marginTop: '15px',
              padding: '8px 16px',
              backgroundColor: retrying ? '#bdc3c7' : '#e67e22',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: retrying ? 'not-allowed' : 'pointer',
              fontSize: '14px',
            }}
          >
            {retrying ? 'Reenviando...' : `Reenviar falhados (${campaign.failed_count})`}
          </button>
        )}
      </div>

      {/* Recipients table */}
      <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px' }}>
        <h3 style={{ margin: '0 0 15px', fontSize: '16px', color: '#2c3e50' }}>
          Destinatários ({campaign.recipients.length})
        </h3>

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ecf0f1', textAlign: 'left' }}>
              <th style={{ padding: '8px 12px' }}>Nome</th>
              <th style={{ padding: '8px 12px' }}>Telefone</th>
              <th style={{ padding: '8px 12px' }}>Status</th>
              <th style={{ padding: '8px 12px' }}>Enviado em</th>
              <th style={{ padding: '8px 12px' }}>Erro</th>
            </tr>
          </thead>
          <tbody>
            {campaign.recipients.map((r) => {
              const rStatus = RECIPIENT_STATUS[r.status] || { label: r.status, color: '#666' };
              return (
                <tr key={`${r.user_id}-${r.phone}`} style={{ borderBottom: '1px solid #ecf0f1' }}>
                  <td style={{ padding: '8px 12px' }}>{r.name || '-'}</td>
                  <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: '13px' }}>{r.phone}</td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{ color: rStatus.color, fontWeight: 500 }}>{rStatus.label}</span>
                  </td>
                  <td style={{ padding: '8px 12px', color: '#7f8c8d', fontSize: '13px' }}>
                    {r.sent_at ? formatDate(r.sent_at) : '-'}
                  </td>
                  <td style={{ padding: '8px 12px', color: '#e74c3c', fontSize: '13px' }}>
                    {r.error_message || ''}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const backButtonStyle: React.CSSProperties = {
  padding: '6px 12px',
  border: '1px solid #ccc',
  borderRadius: '4px',
  backgroundColor: 'white',
  cursor: 'pointer',
  fontSize: '13px',
  marginBottom: '15px',
};
