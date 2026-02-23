import { apiClient } from './client';

export interface SystemSettingsResponse {
  openai_api_key_masked: string;
  anthropic_api_key_masked: string;
  openai_configured: boolean;
  anthropic_configured: boolean;
}

export interface SystemSettingsUpdate {
  openai_api_key?: string;
  anthropic_api_key?: string;
}

export const settingsApi = {
  getSettings: async () => {
    const { data } = await apiClient.get<SystemSettingsResponse>('/admin/settings');
    return data;
  },

  updateSettings: async (payload: SystemSettingsUpdate) => {
    const { data } = await apiClient.put<SystemSettingsResponse>('/admin/settings', payload);
    return data;
  },
};
