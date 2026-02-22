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
  task_id: string;
  total_recipients: number;
  skipped_no_phone: number;
  skipped_users: SkippedUser[];
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
};
