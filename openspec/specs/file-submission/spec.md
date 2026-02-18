## ADDED Requirements

### Requirement: Student can upload file as submission

The system SHALL accept file uploads (PDF, XLSX, PNG, JPG) as submissions for exercises with `submission_type == file_upload`. The uploaded file MUST be stored on the local filesystem under `UPLOAD_BASE_DIR/{exercise_id}/{submission_id}/{original_filename}` and referenced by relative path in the database.

#### Scenario: Successful PDF upload

- **WHEN** a student submits a PDF file to an exercise with `submission_type == file_upload`
- **THEN** the system stores the file on disk, creates a submission record with `file_path`, `file_name`, `file_size`, and `content_type` populated, `code` set to NULL, and `status` set to `queued`

#### Scenario: Successful XLSX upload

- **WHEN** a student submits an XLSX file to an exercise with `submission_type == file_upload`
- **THEN** the system stores the file on disk and creates a submission record with the same fields as PDF upload

#### Scenario: Successful image upload

- **WHEN** a student submits a PNG or JPG file to an exercise with `submission_type == file_upload`
- **THEN** the system stores the file on disk and creates a submission record with `content_type` set to `image/png` or `image/jpeg`

### Requirement: File upload validation

The system SHALL validate uploaded files before accepting them. Validation MUST check file extension, file size, and content type.

#### Scenario: Rejected file extension

- **WHEN** a student uploads a file with an extension not in the allowed set (pdf, xlsx, png, jpg, jpeg)
- **THEN** the system returns HTTP 400 with message indicating the allowed file types

#### Scenario: Rejected file size

- **WHEN** a student uploads a file exceeding `max_submission_file_size_mb` (from config)
- **THEN** the system returns HTTP 400 with message indicating the size limit

#### Scenario: Code submission to file-upload exercise rejected

- **WHEN** a student submits code text (not a file) to an exercise with `submission_type == file_upload`
- **THEN** the system returns HTTP 400 with message indicating that this exercise requires file upload

#### Scenario: File submission to code exercise rejected

- **WHEN** a student uploads a non-Python file to an exercise with `submission_type == code`
- **THEN** the system returns HTTP 400 with message indicating that this exercise requires code submission (existing .py upload behavior is preserved)

### Requirement: Content hash for file submissions

The system SHALL compute a SHA256 hash of the uploaded file content and store it in the `content_hash` field. This hash MUST be used for LLM evaluation caching.

#### Scenario: Duplicate file detection via hash

- **WHEN** a student uploads a file with identical binary content to a previous submission for the same exercise
- **THEN** the `content_hash` matches the previous submission's hash, enabling LLM cache lookup

### Requirement: Content extraction from uploaded files

The system SHALL extract text content from uploaded files for use in LLM evaluation prompts. Extraction MUST be performed as a separate step before the LLM call.

#### Scenario: PDF text extraction

- **WHEN** the grading pipeline processes a PDF submission
- **THEN** the system extracts text from all pages using `pdfplumber`, preserving table structure as formatted text

#### Scenario: XLSX data extraction

- **WHEN** the grading pipeline processes an XLSX submission
- **THEN** the system serializes each sheet as a markdown table (headers + rows) using `openpyxl`

#### Scenario: Image submission passed to vision model

- **WHEN** the grading pipeline processes a PNG or JPG submission
- **THEN** the system passes the image file directly to the LLM as multimodal input without text extraction

#### Scenario: Extracted content truncation

- **WHEN** the extracted text exceeds 50,000 characters
- **THEN** the system truncates to 50,000 characters and includes a note in the LLM prompt indicating the content was truncated
