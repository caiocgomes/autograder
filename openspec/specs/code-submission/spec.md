## ADDED Requirements

### Requirement: Submit code via upload
The system SHALL allow students to submit code by uploading files.

#### Scenario: Upload Python file
- **WHEN** student uploads .py file with valid Python code
- **THEN** system validates file extension, stores code, creates submission record with status "queued"

#### Scenario: Invalid file type
- **WHEN** student uploads .txt or non-Python file for Python exercise
- **THEN** system returns error "Only .py files accepted"

#### Scenario: File size limit
- **WHEN** student uploads file > 1MB
- **THEN** system returns error "File exceeds 1MB limit"

### Requirement: Submit code via in-browser editor
The system SHALL provide in-browser code editor for submissions.

#### Scenario: Submit via editor
- **WHEN** student edits code in browser editor and clicks Submit
- **THEN** system captures editor content, validates syntax, and creates submission

#### Scenario: Syntax highlighting
- **WHEN** student types Python code in editor
- **THEN** editor displays syntax highlighting for Python

#### Scenario: Template pre-loaded
- **WHEN** student opens editor for exercise with template
- **THEN** editor shows template code as starting point

### Requirement: Basic validation before submission
The system SHALL validate code before enqueuing for execution.

#### Scenario: Python syntax check
- **WHEN** student submits code with syntax errors
- **THEN** system returns error "Syntax error at line X" without enqueuing

#### Scenario: Empty submission
- **WHEN** student submits empty code
- **THEN** system returns error "Code cannot be empty"

### Requirement: Submission history
The system SHALL maintain complete history of student submissions per exercise.

#### Scenario: View past submissions
- **WHEN** student requests submission history for exercise
- **THEN** system returns list of all submissions with timestamps, status, and scores

#### Scenario: Compare submissions
- **WHEN** student views two submissions
- **THEN** system displays side-by-side diff highlighting changes

### Requirement: Enforce submission limits
The system SHALL enforce max submissions per exercise if configured.

#### Scenario: Within limit
- **WHEN** student submits 3rd attempt on exercise with max=5
- **THEN** system accepts submission

#### Scenario: Exceeded limit
- **WHEN** student attempts 6th submission on exercise with max=5
- **THEN** system returns error "You have reached the maximum of 5 submissions"

### Requirement: Submission status tracking
The system SHALL track submission lifecycle states.

#### Scenario: Queued status
- **WHEN** submission is created
- **THEN** status is "queued" until worker picks it up

#### Scenario: Running status
- **WHEN** worker begins execution
- **THEN** status changes to "running"

#### Scenario: Completed status
- **WHEN** execution finishes successfully
- **THEN** status changes to "completed" and results are saved

#### Scenario: Failed status
- **WHEN** execution times out or crashes
- **THEN** status changes to "failed" with error message

### Requirement: Real-time submission feedback
The system SHALL notify students when submission completes.

#### Scenario: Execution completes
- **WHEN** submission execution finishes
- **THEN** student receives notification and can view results

#### Scenario: Polling for status
- **WHEN** student polls submission status endpoint
- **THEN** system returns current status (queued/running/completed/failed)

### Requirement: Deadline enforcement
The system SHALL reject submissions after exercise deadline.

#### Scenario: Before deadline
- **WHEN** student submits before closes_at timestamp
- **THEN** system accepts submission

#### Scenario: After deadline without late penalty
- **WHEN** student submits after closes_at and late_penalty=null
- **THEN** system returns error "Deadline has passed"

#### Scenario: After deadline with late penalty
- **WHEN** student submits after closes_at and late_penalty is configured
- **THEN** system accepts submission and applies penalty to final score

### Requirement: Resubmission
The system SHALL allow students to resubmit if under submission limit.

#### Scenario: Resubmit after failure
- **WHEN** student's previous submission failed tests
- **THEN** student can submit new code attempt

#### Scenario: Best score kept
- **WHEN** student has multiple submissions
- **THEN** system uses highest score for final grade
