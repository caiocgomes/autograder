## ADDED Requirements

### Requirement: Submission supports nullable code field

The `code` field in `Submission` SHALL be nullable. For submissions to `file_upload` exercises, `code` MUST be NULL. For submissions to `code` exercises, `code` MUST NOT be NULL (validated at API level).

#### Scenario: File submission has null code

- **WHEN** a student submits a file to a `file_upload` exercise
- **THEN** the submission record has `code == NULL` and `file_path` populated

#### Scenario: Code submission has non-null code

- **WHEN** a student submits code to a `code` exercise
- **THEN** the submission record has `code` populated and `file_path == NULL`

#### Scenario: Existing submissions unaffected

- **WHEN** the migration runs on a database with existing submissions
- **THEN** all existing submissions retain their `code` values (none are NULL)

### Requirement: Submission stores file metadata

The `Submission` model SHALL include nullable fields: `file_path` (String), `file_name` (String), `file_size` (Integer, bytes), and `content_type` (String). These fields MUST be populated for file submissions and NULL for code submissions.

#### Scenario: File metadata stored on upload

- **WHEN** a student uploads a PDF file named "relatorio.pdf" of 245,000 bytes
- **THEN** the submission record has `file_name == "relatorio.pdf"`, `file_size == 245000`, `content_type == "application/pdf"`, and `file_path` set to the relative storage path

### Requirement: Content hash replaces code hash

The field `code_hash` SHALL be renamed to `content_hash`. For code submissions, `content_hash` is the SHA256 of the code text (preserving existing behavior). For file submissions, `content_hash` is the SHA256 of the file binary content.

#### Scenario: Content hash for code submission

- **WHEN** a student submits code text
- **THEN** `content_hash` equals `SHA256(code.encode('utf-8'))`

#### Scenario: Content hash for file submission

- **WHEN** a student uploads a file
- **THEN** `content_hash` equals `SHA256(file_bytes)`

#### Scenario: Existing code_hash values preserved

- **WHEN** the migration renames `code_hash` to `content_hash`
- **THEN** all existing hash values and the database index are preserved

### Requirement: Submission dispatches to correct grading pipeline

The submission endpoint SHALL route to the correct Celery task based on the exercise's `grading_mode`. Exercises with `grading_mode == test_first` dispatch to `execute_submission`. Exercises with `grading_mode == llm_first` dispatch to `grade_llm_first`.

#### Scenario: Test-first submission dispatched to sandbox

- **WHEN** a submission is created for an exercise with `grading_mode == test_first`
- **THEN** the system enqueues `execute_submission` Celery task (existing behavior)

#### Scenario: LLM-first submission dispatched to LLM pipeline

- **WHEN** a submission is created for an exercise with `grading_mode == llm_first`
- **THEN** the system enqueues `grade_llm_first` Celery task (no sandbox, no Docker)

### Requirement: Submission response includes file metadata

The submission API response SHALL include `file_name`, `file_size`, and `content_type` fields when the submission is a file upload. The `code` field SHALL be nullable in the response schema.

#### Scenario: File submission response

- **WHEN** a client requests a file submission's details
- **THEN** the response includes `file_name`, `file_size`, `content_type` with values, and `code` as null

#### Scenario: Code submission response unchanged

- **WHEN** a client requests a code submission's details
- **THEN** the response includes `code` with the code text, and `file_name`, `file_size`, `content_type` as null

### Requirement: Submission results include rubric scores for LLM-first exercises

The submission results endpoint SHALL include `rubric_scores` when the exercise uses `grading_mode == llm_first`. Each rubric score entry MUST include `dimension_name`, `dimension_weight`, `score`, and `feedback`.

#### Scenario: Results for LLM-first submission

- **WHEN** a client requests results for a completed submission on an LLM-first exercise with 3 rubric dimensions
- **THEN** the response includes `rubric_scores` array with 3 entries, each containing dimension details and the LLM-assigned score and feedback, plus `overall_feedback`

#### Scenario: Results for test-first submission unchanged

- **WHEN** a client requests results for a completed submission on a test-first exercise
- **THEN** the response includes `test_results` and optionally `llm_evaluation` (existing behavior), with `rubric_scores` as null or empty
