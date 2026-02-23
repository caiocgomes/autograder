import { apiClient } from './client';

export interface OnboardingStudent {
  id: number;
  name: string | null;
  email: string;
  whatsapp_number: string | null;
  lifecycle_status: string | null;
  token_status: 'none' | 'valid' | 'expired' | 'activated';
  token_expires_in_days: number | null;
  last_message_at: string | null;
}

export interface OnboardingSummary {
  total: number;
  activated: number;
  pending: number;
  no_whatsapp: number;
}

export interface TemplateInfo {
  event_type: string;
  template_text: string;
  is_default: boolean;
  updated_at: string | null;
}

export const onboardingApi = {
  getStudents: async (params?: { course_id?: number }) => {
    const { data } = await apiClient.get<OnboardingStudent[]>('/onboarding/students', { params });
    return data;
  },

  getSummary: async (params?: { course_id?: number }) => {
    const { data } = await apiClient.get<OnboardingSummary>('/onboarding/summary', { params });
    return data;
  },

  getTemplates: async () => {
    const { data } = await apiClient.get<TemplateInfo[]>('/admin/templates');
    return data;
  },

  updateTemplate: async (eventType: string, templateText: string) => {
    const { data } = await apiClient.patch<TemplateInfo>(`/admin/templates/${eventType}`, {
      template_text: templateText,
    });
    return data;
  },

  deleteTemplate: async (eventType: string) => {
    const { data } = await apiClient.delete<TemplateInfo>(`/admin/templates/${eventType}`);
    return data;
  },
};
