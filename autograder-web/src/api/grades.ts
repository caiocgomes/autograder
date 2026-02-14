import { apiClient } from './client';

export interface GradeListItem {
  grade_id: number;
  submission_id: number;
  student_id: number;
  exercise_id: number;
  test_score: number | null;
  llm_score: number | null;
  final_score: number;
  late_penalty_applied: number;
  published: boolean;
  submitted_at: string;
}

export interface StudentGrade {
  grade_id: number;
  submission_id: number;
  exercise_id: number;
  exercise_title: string;
  test_score: number | null;
  llm_score: number | null;
  final_score: number;
  late_penalty_applied: number;
  published: boolean;
  submitted_at: string;
}

export const gradesApi = {
  list: async (params?: {
    class_id?: number;
    exercise_id?: number;
    student_id?: number;
    published_only?: boolean;
  }) => {
    const { data } = await apiClient.get<GradeListItem[]>('/grades', { params });
    return data;
  },

  getMyGrades: async () => {
    const { data } = await apiClient.get<StudentGrade[]>('/grades/me');
    return data;
  },

  publish: async (gradeId: number) => {
    const { data } = await apiClient.post(`/grades/${gradeId}/publish`);
    return data;
  },

  update: async (gradeId: number, updates: {
    llm_score?: number;
    llm_feedback?: string;
    published?: boolean;
  }) => {
    const { data } = await apiClient.patch(`/grades/${gradeId}`, null, { params: updates });
    return data;
  },

  exportCsv: async (classId: number) => {
    const { data } = await apiClient.get(`/grades/export/class/${classId}`, {
      responseType: 'blob',
    });
    return data;
  },
};
