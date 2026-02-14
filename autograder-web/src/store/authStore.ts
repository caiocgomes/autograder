import { create } from 'zustand';
import { apiClient, tokenStorage } from '../api/client';

export interface User {
  id: number;
  email: string;
  role: 'admin' | 'professor' | 'student' | 'ta';
  created_at: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, role: User['role']) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  updateUser: (updates: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email: string, password: string) => {
    try {
      const { data } = await apiClient.post('/auth/login', { email, password });
      tokenStorage.setTokens(data.access_token, data.refresh_token);

      const userResponse = await apiClient.get('/users/me');
      set({ user: userResponse.data, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      throw error;
    }
  },

  register: async (email: string, password: string, role: User['role']) => {
    try {
      await apiClient.post('/auth/register', { email, password, role });
      // After registration, user needs to login
    } catch (error) {
      throw error;
    }
  },

  logout: () => {
    tokenStorage.clearTokens();
    set({ user: null, isAuthenticated: false, isLoading: false });
  },

  loadUser: async () => {
    const token = tokenStorage.getAccessToken();
    if (!token) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return;
    }

    try {
      const { data } = await apiClient.get('/users/me');
      set({ user: data, isAuthenticated: true, isLoading: false });
    } catch (error) {
      tokenStorage.clearTokens();
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  updateUser: (updates: Partial<User>) => {
    set((state) => ({
      user: state.user ? { ...state.user, ...updates } : null,
    }));
  },
}));
