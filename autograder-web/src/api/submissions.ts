import { apiClient } from './client';

export interface Submission {
  id: number;
  exercise_id: number;
  student_id: number;
  code: string | null;
  status: 'queued' | 'running' | 'completed' | 'failed';
  submitted_at: string;
  error_message: string | null;
  file_name: string | null;
  file_size: number | null;
  content_type: string | null;
}

export interface SubmissionListItem {
  id: number;
  exercise_id: number;
  student_id: number;
  status: 'queued' | 'running' | 'completed' | 'failed';
  submitted_at: string;
  file_name: string | null;
}

export interface TestResultDetail {
  id: number;
  test_name: string;
  passed: boolean;
  message: string | null;
  stdout: string | null;
  stderr: string | null;
}

export interface LLMEvaluation {
  id: number;
  feedback: string;
  score: number;
  cached: boolean;
  created_at: string;
}

export interface GradeDetail {
  id: number;
  test_score: number | null;
  llm_score: number | null;
  final_score: number;
  late_penalty_applied: number;
  published: boolean;
}

export interface RubricScoreDetail {
  dimension_name: string;
  dimension_weight: number;
  score: number;
  feedback: string | null;
}

export interface SubmissionDetail {
  submission: Submission;
  test_results: TestResultDetail[] | null;
  llm_evaluation: LLMEvaluation | null;
  grade: GradeDetail | null;
  rubric_scores: RubricScoreDetail[] | null;
  overall_feedback: string | null;
}

export const submissionsApi = {
  list: async (params?: { exercise_id?: number; student_id?: number }) => {
    const { data } = await apiClient.get<SubmissionListItem[]>('/submissions', { params });
    return data;
  },

  get: async (id: number) => {
    const { data } = await apiClient.get<Submission>(`/submissions/${id}`);
    return data;
  },

  getResults: async (id: number) => {
    const { data } = await apiClient.get<SubmissionDetail>(`/submissions/${id}/results`);
    return data;
  },

  getStatus: async (id: number) => {
    const { data } = await apiClient.get<{ id: number; status: string; error_message: string | null }>(
      `/submissions/${id}/status`
    );
    return data;
  },

  submit: async (exerciseId: number, code: string) => {
    const formData = new FormData();
    formData.append('exercise_id', String(exerciseId));
    formData.append('code', code);
    const { data } = await apiClient.post<Submission>('/submissions', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  submitFile: async (exerciseId: number, file: File) => {
    const formData = new FormData();
    formData.append('exercise_id', String(exerciseId));
    formData.append('file', file);
    const { data } = await apiClient.post<Submission>('/submissions', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  getDiff: async (submissionId: number, comparisonId: number) => {
    const { data } = await apiClient.get<string>(
      `/submissions/${submissionId}/diff/${comparisonId}`
    );
    return data;
  },
};
