import { apiClient } from './client';

export interface Exercise {
  id: number;
  title: string;
  description: string;
  template_code: string | null;
  language: string;
  max_submissions: number | null;
  timeout_seconds: number;
  memory_limit_mb: number;
  has_tests: boolean;
  llm_grading_enabled: boolean;
  test_weight: number;
  llm_weight: number;
  llm_grading_criteria: string | null;
  created_by: number;
  published: boolean;
  tags: string | null;
  test_cases?: TestCaseResponse[];
}

export interface TestCaseResponse {
  id: number;
  exercise_id: number;
  name: string;
  input_data: string;
  expected_output: string;
  hidden: boolean;
}

export interface ExerciseCreate {
  title: string;
  description: string;
  template_code?: string;
  language?: string;
  max_submissions?: number;
  timeout_seconds?: number;
  memory_limit_mb?: number;
  has_tests?: boolean;
  llm_grading_enabled?: boolean;
  test_weight?: number;
  llm_weight?: number;
  llm_grading_criteria?: string;
  published?: boolean;
  tags?: string;
}

export interface TestCaseCreate {
  name: string;
  input_data: string;
  expected_output: string;
  hidden: boolean;
}

export interface ExerciseListDetail {
  id: number;
  title: string;
  class_id: number;
  group_id: number | null;
  opens_at: number | null;
  closes_at: number | null;
  late_penalty_percent_per_day: number | null;
  auto_publish_grades: boolean;
  randomize_order: boolean;
  exercises: ExerciseInList[];
}

export interface ExerciseInList {
  list_item_id: number;
  exercise_id: number;
  exercise_title: string;
  position: number;
  weight: number;
}

export interface ExerciseListCreate {
  title: string;
  class_id: number;
  group_id?: number;
  opens_at?: number;
  closes_at?: number;
  late_penalty_percent_per_day?: number;
  auto_publish_grades?: boolean;
  randomize_order?: boolean;
}

export const exercisesApi = {
  list: async (params?: { published?: boolean; tags?: string }) => {
    const { data } = await apiClient.get<Exercise[]>('/exercises', { params });
    return data;
  },

  get: async (id: number, includeTests = false) => {
    const { data } = await apiClient.get<Exercise>(`/exercises/${id}`, {
      params: { include_tests: includeTests },
    });
    return data;
  },

  create: async (exercise: ExerciseCreate) => {
    const { data } = await apiClient.post<Exercise>('/exercises', exercise);
    return data;
  },

  update: async (id: number, exercise: Partial<ExerciseCreate>) => {
    const { data } = await apiClient.patch<Exercise>(`/exercises/${id}`, exercise);
    return data;
  },

  publish: async (id: number, published: boolean) => {
    const { data } = await apiClient.patch<Exercise>(`/exercises/${id}/publish`, null, {
      params: { published },
    });
    return data;
  },

  addTestCase: async (exerciseId: number, testCase: TestCaseCreate) => {
    const { data } = await apiClient.post<TestCaseResponse>(
      `/exercises/${exerciseId}/tests`,
      testCase
    );
    return data;
  },
};

export const exerciseListsApi = {
  getForClass: async (classId: number) => {
    const { data } = await apiClient.get<ExerciseListDetail[]>(
      `/exercise-lists/classes/${classId}/lists`
    );
    return data;
  },

  create: async (listData: ExerciseListCreate) => {
    const { data } = await apiClient.post('/exercise-lists', listData);
    return data;
  },

  addExercise: async (listId: number, exerciseId: number, position: number, weight = 1.0) => {
    const { data } = await apiClient.post(`/exercise-lists/${listId}/exercises`, {
      exercise_id: exerciseId,
      position,
      weight,
    });
    return data;
  },

  reorderExercise: async (listId: number, exerciseId: number, position: number) => {
    const { data } = await apiClient.patch(
      `/exercise-lists/${listId}/exercises/${exerciseId}`,
      { position }
    );
    return data;
  },

  removeExercise: async (listId: number, exerciseId: number, confirm = false) => {
    await apiClient.delete(`/exercise-lists/${listId}/exercises/${exerciseId}`, {
      params: { confirm },
    });
  },
};
