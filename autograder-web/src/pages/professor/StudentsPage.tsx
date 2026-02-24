import { useState, useEffect, useCallback, useRef } from 'react';
import { studentsApi } from '../../api/students';
import type { StudentListItem, SyncSummary } from '../../api/students';
import { apiClient } from '../../api/client';

interface Product {
  id: number;
  name: string;
}

const STATUS_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'Ativo', label: 'Ativo' },
  { value: 'Inadimplente', label: 'Inadimplente' },
  { value: 'Cancelado', label: 'Cancelado' },
  { value: 'Reembolsado', label: 'Reembolsado' },
  { value: 'sem_status', label: 'Sem status' },
];

const DISCORD_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'true', label: 'Conectado' },
  { value: 'false', label: 'Não conectado' },
];

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  'Ativo': { bg: '#d5f5e3', text: '#1e8449' },
  'Inadimplente': { bg: '#fdebd0', text: '#b9770e' },
  'Cancelado': { bg: '#fadbd8', text: '#c0392b' },
  'Reembolsado': { bg: '#e5e7e9', text: '#5d6d7e' },
};

const PAGE_SIZE = 50;

export function StudentsPage() {
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [discordFilter, setDiscordFilter] = useState('');
  const [productFilter, setProductFilter] = useState<number | undefined>();
  const [products, setProducts] = useState<Product[]>([]);

  // Pagination
  const [page, setPage] = useState(0);

  // Sync state
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncSummary, setSyncSummary] = useState<SyncSummary | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadStudents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      };
      if (statusFilter) params.status = statusFilter;
      if (discordFilter) params.discord = discordFilter;
      if (productFilter) params.product_id = productFilter;

      const data = await studentsApi.list(params);
      setStudents(data.items);
      setTotal(data.total);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Erro ao carregar alunos');
    } finally {
      setIsLoading(false);
    }
  }, [page, statusFilter, discordFilter, productFilter]);

  const loadProducts = useCallback(async () => {
    try {
      const { data } = await apiClient.get<Product[]>('/products');
      setProducts(data);
    } catch {
      // Products filter is optional, don't block page
    }
  }, []);

  useEffect(() => {
    loadStudents();
  }, [loadStudents]);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  // Reset to page 0 when filters change
  useEffect(() => {
    setPage(0);
  }, [statusFilter, discordFilter, productFilter]);

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncSummary(null);
    setSyncError(null);

    try {
      const { task_id } = await studentsApi.triggerSync(productFilter);

      // Poll every 3 seconds
      pollRef.current = setInterval(async () => {
        try {
          const status = await studentsApi.pollSyncStatus(task_id);

          if (status.status === 'completed') {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setIsSyncing(false);
            setSyncSummary(status.summary);
            loadStudents();
          } else if (status.status === 'failed') {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setIsSyncing(false);
            setSyncError(status.error || 'Sync falhou');
            if (status.summary) setSyncSummary(status.summary);
          }
        } catch {
          // Polling error, keep trying
        }
      }, 3000);
    } catch (e: any) {
      setIsSyncing(false);
      if (e.response?.status === 409) {
        setSyncError('Uma sincronização já está em andamento');
      } else {
        setSyncError(e.response?.data?.detail || 'Erro ao iniciar sync');
      }
    }
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0, fontSize: '24px', color: '#2c3e50' }}>Alunos</h1>
        <button
          onClick={handleSync}
          disabled={isSyncing}
          style={{
            padding: '10px 20px',
            backgroundColor: isSyncing ? '#95a5a6' : '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: isSyncing ? 'not-allowed' : 'pointer',
            fontSize: '14px',
            fontWeight: 500,
          }}
        >
          {isSyncing ? 'Sincronizando...' : 'Sincronizar'}
        </button>
      </div>

      {/* Sync feedback */}
      {syncSummary && (
        <div style={{
          padding: '16px',
          marginBottom: '16px',
          backgroundColor: syncError ? '#fdf2f2' : '#f0fdf4',
          border: `1px solid ${syncError ? '#fecaca' : '#bbf7d0'}`,
          borderRadius: '8px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <strong style={{ color: syncError ? '#991b1b' : '#166534' }}>
                {syncError ? 'Sync parcial' : 'Sincronização concluída'}
              </strong>
              <div style={{ marginTop: '8px', fontSize: '14px', color: '#374151' }}>
                <div>{syncSummary.total_processed} alunos processados</div>
                {syncSummary.new_students > 0 && <div>{syncSummary.new_students} novos</div>}
                {syncSummary.status_changes.to_ativo > 0 && <div>{syncSummary.status_changes.to_ativo} tornaram-se ativos</div>}
                {syncSummary.status_changes.to_inadimplente > 0 && <div>{syncSummary.status_changes.to_inadimplente} inadimplentes</div>}
                {syncSummary.status_changes.to_cancelado > 0 && <div>{syncSummary.status_changes.to_cancelado} cancelamentos</div>}
                {syncSummary.status_changes.to_reembolsado > 0 && <div>{syncSummary.status_changes.to_reembolsado} reembolsos</div>}
                {syncSummary.errors > 0 && <div style={{ color: '#dc2626' }}>{syncSummary.errors} erros</div>}
              </div>
            </div>
            <button
              onClick={() => { setSyncSummary(null); setSyncError(null); }}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', color: '#6b7280' }}
            >
              x
            </button>
          </div>
        </div>
      )}

      {syncError && !syncSummary && (
        <div style={{
          padding: '12px 16px',
          marginBottom: '16px',
          backgroundColor: '#fdf2f2',
          border: '1px solid #fecaca',
          borderRadius: '8px',
          color: '#991b1b',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span>{syncError}</span>
          <button
            onClick={() => setSyncError(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', color: '#6b7280' }}
          >
            x
          </button>
        </div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={selectStyle}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        <select
          value={discordFilter}
          onChange={(e) => setDiscordFilter(e.target.value)}
          style={selectStyle}
        >
          {DISCORD_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        <select
          value={productFilter ?? ''}
          onChange={(e) => setProductFilter(e.target.value ? Number(e.target.value) : undefined)}
          style={selectStyle}
        >
          <option value="">Todos os produtos</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Count */}
      <div style={{ marginBottom: '12px', fontSize: '14px', color: '#6b7280' }}>
        Mostrando {students.length} de {total} alunos
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '12px', backgroundColor: '#fdf2f2', color: '#991b1b', borderRadius: '6px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>Carregando...</div>
      ) : (
        <>
          {/* Table */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: 'white', borderRadius: '8px', overflow: 'hidden' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8fafc' }}>
                  <th style={thStyle}>Nome</th>
                  <th style={thStyle}>Email</th>
                  <th style={thStyle}>Produtos</th>
                  <th style={{ ...thStyle, textAlign: 'center', width: '80px' }}>Discord</th>
                  <th style={{ ...thStyle, textAlign: 'center', width: '90px' }}>WhatsApp</th>
                </tr>
              </thead>
              <tbody>
                {students.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
                      Nenhum aluno encontrado
                    </td>
                  </tr>
                ) : (
                  students.map((student, idx) => (
                    <tr key={student.email} style={{ backgroundColor: idx % 2 === 0 ? 'white' : '#f9fafb' }}>
                      <td style={tdStyle}>{student.name || <span style={{ color: '#9ca3af' }}>-</span>}</td>
                      <td style={tdStyle}>{student.email}</td>
                      <td style={tdStyle}>
                        {student.products.length === 0 ? (
                          <span style={{ color: '#9ca3af', fontSize: '13px' }}>Sem produto</span>
                        ) : (
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {student.products.map((p) => {
                              const colors = STATUS_COLORS[p.status] || { bg: '#e5e7e9', text: '#5d6d7e' };
                              return (
                                <span
                                  key={p.product_name}
                                  style={{
                                    display: 'inline-block',
                                    padding: '2px 8px',
                                    borderRadius: '12px',
                                    fontSize: '12px',
                                    fontWeight: 500,
                                    backgroundColor: colors.bg,
                                    color: colors.text,
                                    whiteSpace: 'nowrap',
                                  }}
                                >
                                  {p.product_name} {p.status === 'Ativo' ? '' : `(${p.status})`}
                                </span>
                              );
                            })}
                          </div>
                        )}
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'center' }}>
                        <span style={{
                          display: 'inline-block',
                          width: '10px',
                          height: '10px',
                          borderRadius: '50%',
                          backgroundColor: student.discord_connected ? '#2ecc71' : '#d1d5db',
                        }} />
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'center' }}>
                        <span style={{
                          display: 'inline-block',
                          width: '10px',
                          height: '10px',
                          borderRadius: '50%',
                          backgroundColor: student.has_whatsapp ? '#2ecc71' : '#d1d5db',
                        }} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', marginTop: '16px' }}>
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                style={paginationBtnStyle(page === 0)}
              >
                Anterior
              </button>
              <span style={{ fontSize: '14px', color: '#374151' }}>
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page >= totalPages - 1}
                style={paginationBtnStyle(page >= totalPages - 1)}
              >
                Próximo
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  padding: '8px 12px',
  borderRadius: '6px',
  border: '1px solid #d1d5db',
  fontSize: '14px',
  backgroundColor: 'white',
  color: '#374151',
  minWidth: '160px',
};

const thStyle: React.CSSProperties = {
  padding: '12px 16px',
  textAlign: 'left',
  fontSize: '13px',
  fontWeight: 600,
  color: '#6b7280',
  borderBottom: '2px solid #e5e7eb',
};

const tdStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: '14px',
  color: '#1f2937',
  borderBottom: '1px solid #f3f4f6',
};

function paginationBtnStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: '6px 14px',
    borderRadius: '4px',
    border: '1px solid #d1d5db',
    backgroundColor: disabled ? '#f3f4f6' : 'white',
    color: disabled ? '#9ca3af' : '#374151',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontSize: '13px',
  };
}
