import { apiClient } from './client';

export interface Course {
  id: number;
  name: string;
}

export interface Recipient {
  id: number;
  name: string;
  email: string;
  whatsapp_number: string | null;
  has_whatsapp: boolean;
}

export interface SkippedUser {
  id: number;
  name: string;
  reason: string;
}

export interface BulkSendRequest {
  user_ids: number[];
  message_template: string;
  course_id?: number;
}

export interface BulkSendResponse {
  campaign_id: number;
  task_id: string;
  total_recipients: number;
  skipped_no_phone: number;
  skipped_users: SkippedUser[];
}

export interface RecipientStatus {
  user_id: number;
  name: string | null;
  phone: string;
  status: 'pending' | 'sent' | 'failed';
  resolved_message: string | null;
  sent_at: string | null;
  error_message: string | null;
}

export interface Campaign {
  id: number;
  message_template: string;
  course_name: string | null;
  total_recipients: number;
  sent_count: number;
  failed_count: number;
  status: 'sending' | 'completed' | 'partial_failure' | 'failed';
  created_at: string;
  completed_at: string | null;
}

export interface CampaignDetail extends Campaign {
  recipients: RecipientStatus[];
}

export interface RetryResponse {
  retrying: number;
  campaign_id: number;
}

export const messagingApi = {
  getCourses: async () => {
    const { data } = await apiClient.get<Course[]>('/messaging/courses');
    return data;
  },

  getRecipients: async (params: { course_id: number; has_whatsapp?: boolean }) => {
    const { data } = await apiClient.get<Recipient[]>('/messaging/recipients', { params });
    return data;
  },

  sendBulk: async (request: BulkSendRequest) => {
    const { data } = await apiClient.post<BulkSendResponse>('/messaging/send', request);
    return data;
  },

  getCampaigns: async (params?: { status?: string; limit?: number; offset?: number }) => {
    const { data } = await apiClient.get<Campaign[]>('/messaging/campaigns', { params });
    return data;
  },

  getCampaign: async (id: number) => {
    const { data } = await apiClient.get<CampaignDetail>(`/messaging/campaigns/${id}`);
    return data;
  },

  retryCampaign: async (id: number) => {
    const { data } = await apiClient.post<RetryResponse>(`/messaging/campaigns/${id}/retry`);
    return data;
  },
};
