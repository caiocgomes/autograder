import { apiClient } from './client';

export interface StudentProductStatus {
  product_name: string;
  status: string;
}

export interface StudentListItem {
  email: string;
  name: string | null;
  phone: string | null;
  discord_connected: boolean;
  has_whatsapp: boolean;
  has_account: boolean;
  products: StudentProductStatus[];
}

export interface StudentListResponse {
  items: StudentListItem[];
  total: number;
}

export interface StudentListParams {
  status?: string;
  discord?: string;
  product_id?: number;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface SyncStatusTransitions {
  to_ativo: number;
  to_inadimplente: number;
  to_cancelado: number;
  to_reembolsado: number;
}

export interface SyncSummary {
  total_processed: number;
  new_students: number;
  status_changes: SyncStatusTransitions;
  errors: number;
}

export interface SyncStatusResponse {
  status: 'running' | 'completed' | 'failed';
  started_at: string | null;
  completed_at: string | null;
  summary: SyncSummary | null;
  error: string | null;
}

export const studentsApi = {
  list: async (params?: StudentListParams) => {
    const { data } = await apiClient.get<StudentListResponse>('/admin/students', { params });
    return data;
  },

  triggerSync: async (productId?: number) => {
    const body = productId ? { product_id: productId } : {};
    const { data } = await apiClient.post<{ task_id: string }>('/admin/students/sync', body);
    return data;
  },

  pollSyncStatus: async (taskId: string) => {
    const { data } = await apiClient.get<SyncStatusResponse>(`/admin/students/sync/${taskId}`);
    return data;
  },
};
