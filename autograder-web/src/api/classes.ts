import { apiClient } from './client';

export interface Class {
  id: number;
  name: string;
  professor_id: number;
  invite_code: string;
  archived: boolean;
  created_at: string;
}

export interface ClassWithDetails extends Class {
  students: Array<{
    id: number;
    email: string;
    enrolled_at: string;
  }>;
  groups: Array<{
    id: number;
    name: string;
    members: Array<{ id: number; email: string }>;
  }>;
}

export const classesApi = {
  list: async () => {
    const { data } = await apiClient.get<Class[]>('/classes');
    return data;
  },

  get: async (id: number) => {
    const { data } = await apiClient.get<ClassWithDetails>(`/classes/${id}`);
    return data;
  },

  create: async (name: string) => {
    const { data } = await apiClient.post<Class>('/classes', { name });
    return data;
  },

  enroll: async (classId: number, inviteCode: string) => {
    const { data } = await apiClient.post(`/classes/${classId}/enroll`, {
      invite_code: inviteCode,
    });
    return data;
  },

  addStudents: async (classId: number, csvFile: File) => {
    const formData = new FormData();
    formData.append('file', csvFile);
    const { data } = await apiClient.post(`/classes/${classId}/students`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  removeStudent: async (classId: number, studentId: number) => {
    await apiClient.delete(`/classes/${classId}/students/${studentId}`);
  },

  createGroup: async (classId: number, name: string) => {
    const { data } = await apiClient.post(`/classes/${classId}/groups`, { name });
    return data;
  },

  addGroupMembers: async (groupId: number, studentIds: number[]) => {
    const { data } = await apiClient.post(`/groups/${groupId}/members`, {
      student_ids: studentIds,
    });
    return data;
  },

  archive: async (classId: number) => {
    const { data } = await apiClient.patch(`/classes/${classId}/archive`);
    return data;
  },
};
