## 1. Dependencies & Config

- [x] 1.1 Add `pdfplumber` and `openpyxl` to backend dependencies in `pyproject.toml`
- [x] 1.2 Add `UPLOAD_BASE_DIR` setting to `app/config.py` (default `./uploads`, type `Path`)
- [x] 1.3 Increase `max_submission_file_size_mb` default from 1 to 10 in `app/config.py`
- [x] 1.4 Add `UPLOAD_BASE_DIR` to `.env.example` and `docker-compose.yml` volumes

## 2. Database Models & Migration

- [x] 2.1 Create `SubmissionType` enum (`code`, `file_upload`) and `GradingMode` enum (`test_first`, `llm_first`) in `app/models/exercise.py`
- [x] 2.2 Add `submission_type` and `grading_mode` columns to `Exercise` model with defaults `code` and `test_first`
- [x] 2.3 Create `RubricDimension` model in `app/models/exercise.py` (id, exercise_id FK, name, description, weight, position) with relationship on `Exercise`
- [x] 2.4 Make `code` column nullable on `Submission` model
- [x] 2.5 Rename `code_hash` to `content_hash` on `Submission` model (update model + all references in tasks.py, routers, schemas)
- [x] 2.6 Add file metadata fields to `Submission` model: `file_path` (String, nullable), `file_name` (String, nullable), `file_size` (Integer, nullable), `content_type` (String, nullable)
- [x] 2.7 Create `RubricScore` model in `app/models/submission.py` (id, submission_id FK, dimension_id FK, score Float, feedback Text) with unique constraint on `(submission_id, dimension_id)`
- [x] 2.8 Update `app/models/__init__.py` to export new models
- [x] 2.9 Generate Alembic migration: add enums + new columns on exercises, alter submissions (nullable code, rename code_hash, add file fields), create rubric_dimensions table, create rubric_scores table. Backfill existing exercises with `submission_type=code, grading_mode=test_first`

## 3. Schemas

- [x] 3.1 Create `RubricDimensionCreate` and `RubricDimensionResponse` schemas in `app/schemas/exercises.py`
- [x] 3.2 Add `submission_type`, `grading_mode`, and `rubric_dimensions` (list of `RubricDimensionCreate`) to `ExerciseCreate` schema. Make `rubric_dimensions` required when `grading_mode == llm_first`
- [x] 3.3 Add `submission_type`, `grading_mode`, and `rubric_dimensions` (list of `RubricDimensionResponse`) to `ExerciseResponse` schema
- [x] 3.4 Update `ExerciseCreate` validation: skip `test_weight + llm_weight == 1.0` check when `grading_mode == llm_first`; validate rubric dimension weights sum to 1.0 for `llm_first`
- [x] 3.5 Make `code` nullable in `SubmissionResponse` and `SubmissionCreate` (code optional, not required for file uploads)
- [x] 3.6 Add `file_name`, `file_size`, `content_type` (all nullable) to `SubmissionResponse`
- [x] 3.7 Rename `code_hash` to `content_hash` in any schema that references it (e.g., `LLMEvaluationResponse`)
- [x] 3.8 Create `RubricScoreResponse` schema (dimension_name, dimension_weight, score, feedback) and add `rubric_scores` + `overall_feedback` fields to `SubmissionDetailResponse`

## 4. File Storage

- [x] 4.1 Create `app/services/file_storage.py` with `save_submission_file(exercise_id, submission_id, upload_file) -> (relative_path, content_hash)` that writes to `UPLOAD_BASE_DIR/{exercise_id}/{submission_id}/{filename}` and returns path + SHA256 hash
- [x] 4.2 Create `app/services/content_extractor.py` with `extract_content(file_path, content_type) -> str` dispatching to PDF, XLSX, or raising for images
- [x] 4.3 Implement PDF extraction in `content_extractor.py` using `pdfplumber` (text per page, preserve table structure)
- [x] 4.4 Implement XLSX extraction in `content_extractor.py` using `openpyxl` (serialize sheets as markdown tables)
- [x] 4.5 Implement content truncation at 50k characters with truncation notice appended

## 5. LLM-first Grading Pipeline

- [x] 5.1 Create `create_rubric_prompt(exercise, rubric_dimensions, content, is_image=False) -> str|list` in `app/tasks.py` that builds the structured prompt with rubric dimensions and weights
- [x] 5.2 Implement multimodal input preparation for image submissions (base64 encode for Anthropic, URL/base64 for OpenAI) in the prompt builder
- [x] 5.3 Create `parse_rubric_response(response_text, expected_dimensions) -> dict` that validates JSON structure, checks dimension names match, and clamps scores to 0-100
- [x] 5.4 Implement `grade_llm_first` Celery task: load submission + exercise + rubric dimensions, check cache by `(content_hash, exercise_id)`, extract content or prepare image, build prompt, call LLM, parse response, persist RubricScore records and Grade, mark submission COMPLETED
- [x] 5.5 Add retry logic to `grade_llm_first`: on malformed LLM response, retry once with corrective prompt; on API failure, retry up to 3 times with exponential backoff; on exhausted retries, mark submission FAILED
- [x] 5.6 Update `llm_evaluate_submission` task to use `content_hash` instead of `code_hash` for cache lookups

## 6. Router Updates

- [x] 6.1 Update exercise creation endpoint in `app/routers/exercises.py` to accept `submission_type`, `grading_mode`, and `rubric_dimensions`. Persist `RubricDimension` records when `grading_mode == llm_first`
- [x] 6.2 Update exercise update endpoint to handle `rubric_dimensions` changes (only if no submissions exist for the exercise)
- [x] 6.3 Update exercise GET endpoints to include `rubric_dimensions` in response
- [x] 6.4 Update `POST /submissions` in `app/routers/submissions.py`: branch on exercise `submission_type`. For `file_upload`: validate extension (pdf, xlsx, png, jpg, jpeg), validate size, save file via `file_storage.save_submission_file()`, compute content_hash from file bytes, create submission with file metadata and `code=NULL`. For `code`: existing behavior (syntax validation, code hash)
- [x] 6.5 Update `POST /submissions` to dispatch to correct Celery task: `execute_submission` for `grading_mode == test_first`, `grade_llm_first` for `grading_mode == llm_first`
- [x] 6.6 Update `GET /submissions/{id}/results` to include `rubric_scores` and `overall_feedback` when exercise is `llm_first`
- [x] 6.7 Reject mismatched submission types: code text to `file_upload` exercise → HTTP 400; non-.py file to `code` exercise → HTTP 400

## 7. Frontend - Exercise Creation

- [x] 7.1 Add `submission_type` selector (dropdown: Code / File Upload) to exercise creation form
- [x] 7.2 Add `grading_mode` selector (dropdown: Test-first / LLM-first) to exercise creation form
- [x] 7.3 Conditionally show/hide code-specific fields (template_code, language, timeout, memory limit, test cases) when `submission_type == file_upload` and `grading_mode == llm_first`
- [x] 7.4 Build rubric editor component: list of dimension rows with name, description, weight inputs, add/remove buttons. Show when `grading_mode == llm_first`
- [x] 7.5 Add client-side validation that rubric dimension weights sum to 1.0
- [x] 7.6 Wire exercise creation form to send `submission_type`, `grading_mode`, and `rubric_dimensions` to API

## 8. Frontend - Submission

- [x] 8.1 Create file upload component (drag-and-drop or file picker) with accepted extensions filter (pdf, xlsx, png, jpg) and file size display
- [x] 8.2 Conditionally render file upload component (when `submission_type == file_upload`) or code editor (when `submission_type == code`) in submission view
- [x] 8.3 Update submission API call to send multipart/form-data with file when `submission_type == file_upload`
- [x] 8.4 Show file name and size in submission list/detail views for file submissions

## 9. Frontend - Results & Grading

- [x] 9.1 Create rubric scores display component: table/cards showing each dimension name, weight, score, and feedback
- [x] 9.2 Show rubric scores component in submission results view when exercise is `llm_first` (instead of test results)
- [x] 9.3 Show overall feedback text below rubric scores
- [x] 9.4 Update professor grade view to show per-dimension rubric scores for `llm_first` exercises

## 10. Tests

- [x] 10.1 Unit tests for `content_extractor.py`: PDF extraction, XLSX extraction, truncation at 50k chars
- [x] 10.2 Unit tests for `file_storage.py`: save file, verify path structure, verify content hash
- [x] 10.3 Unit tests for `parse_rubric_response`: valid JSON, malformed JSON, missing dimensions, out-of-range scores
- [x] 10.4 Unit tests for `create_rubric_prompt`: text content prompt, image multimodal prompt
- [x] 10.5 Router tests for exercise creation with `submission_type` and `grading_mode` + rubric dimensions (valid and invalid cases)
- [x] 10.6 Router tests for `POST /submissions` with file upload: valid extensions, rejected extensions, size limit, code-to-file-exercise mismatch
- [x] 10.7 Router tests for `GET /submissions/{id}/results` with rubric scores for `llm_first` exercise
- [x] 10.8 Integration test for `grade_llm_first` task: mock LLM response, verify RubricScore records created, Grade final_score calculation, cache hit on duplicate hash
- [x] 10.9 Migration test: verify existing exercises get default `submission_type=code` and `grading_mode=test_first`, existing submissions retain non-null code
