export interface TestCase {
  input: string;
  expected: string;
}

export interface TestResult {
  input: string;
  expected: string;
  actual: string;
  passed: boolean;
  error: string | null;
}

export interface LLMValidation {
  valid: boolean;
  feedback: string;
}

export interface GradeRequest {
  code: string;
  requirements: string;
  test_cases: TestCase[];
}

export interface GradeResponse {
  passed: boolean;
  score: number;
  llm_validation: LLMValidation;
  test_results: TestResult[];
}
