import type { GradeRequest, GradeResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function gradeCode(request: GradeRequest): Promise<GradeResponse> {
  const response = await fetch(`${API_BASE_URL}/grade`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to grade code');
  }

  return response.json();
}
