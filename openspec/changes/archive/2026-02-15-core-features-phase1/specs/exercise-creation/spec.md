## ADDED Requirements

### Requirement: Create exercise
The system SHALL allow professors to create exercises with rich descriptions.

#### Scenario: Successful exercise creation
- **WHEN** professor submits exercise with title, Markdown description, and Python language
- **THEN** system creates exercise, returns exercise ID, and sets status to draft

#### Scenario: Markdown with LaTeX
- **WHEN** professor includes LaTeX math in description (e.g., `$E = mc^2$`)
- **THEN** system stores Markdown as-is for rendering

#### Scenario: Missing required fields
- **WHEN** professor submits exercise without title
- **THEN** system returns error "Title is required"

### Requirement: Code template
The system SHALL allow professors to provide starter code templates.

#### Scenario: Python template with function signature
- **WHEN** professor sets template code with function `def solve(data):`
- **THEN** system stores template and provides it to students on exercise view

#### Scenario: Empty template
- **WHEN** professor leaves template empty
- **THEN** system allows exercise creation with blank starting code

### Requirement: Dataset upload
The system SHALL allow professors to upload datasets for exercises.

#### Scenario: Upload CSV dataset
- **WHEN** professor uploads CSV file (< 10MB)
- **THEN** system stores file, returns file URL, and associates with exercise

#### Scenario: Multiple datasets
- **WHEN** professor uploads multiple files (train.csv, test.csv)
- **THEN** system stores all files and makes them available to students

#### Scenario: File size limit
- **WHEN** professor uploads file > 10MB
- **THEN** system returns error "File size exceeds 10MB limit"

### Requirement: Grading configuration
The system SHALL allow professors to configure automated grading methods.

#### Scenario: Enable unit tests only
- **WHEN** professor sets `has_tests=true` and `llm_grading_enabled=false`
- **THEN** system evaluates submissions only via unit tests

#### Scenario: Enable LLM grading only
- **WHEN** professor sets `has_tests=false` and `llm_grading_enabled=true`
- **THEN** system evaluates submissions only via LLM feedback

#### Scenario: Hybrid grading
- **WHEN** professor sets both `has_tests=true` and `llm_grading_enabled=true`
- **THEN** system combines test score (70%) and LLM score (30%) for final grade

#### Scenario: No grading method
- **WHEN** professor sets both `has_tests=false` and `llm_grading_enabled=false`
- **THEN** system returns error "At least one grading method required"

### Requirement: Test case definition
The system SHALL allow professors to define unit test cases for exercises.

#### Scenario: Add test case with input/output
- **WHEN** professor adds test with input `[1, 2, 3]` and expected output `6`
- **THEN** system stores test case and runs it against student submissions

#### Scenario: Multiple test cases
- **WHEN** professor adds 5 test cases with different inputs
- **THEN** system evaluates all tests and calculates score as (passed / total)

#### Scenario: Hidden tests
- **WHEN** professor marks test as hidden
- **THEN** students see "Test failed" without specific input/output details

### Requirement: Execution constraints
The system SHALL allow professors to set resource limits per exercise.

#### Scenario: Set timeout
- **WHEN** professor sets timeout to 30 seconds
- **THEN** system terminates student code execution after 30 seconds

#### Scenario: Set memory limit
- **WHEN** professor sets memory limit to 512MB
- **THEN** system enforces 512MB RAM limit during execution

#### Scenario: Default limits
- **WHEN** professor does not specify limits
- **THEN** system uses defaults (30s timeout, 512MB memory)

### Requirement: Submission limits
The system SHALL allow professors to limit submissions per student.

#### Scenario: Max 5 submissions
- **WHEN** professor sets `max_submissions=5`
- **THEN** students can submit up to 5 times, then receive error "Submission limit reached"

#### Scenario: Unlimited submissions
- **WHEN** professor sets `max_submissions=null`
- **THEN** students can submit unlimited times

### Requirement: Exercise visibility
The system SHALL allow professors to control exercise visibility.

#### Scenario: Draft mode
- **WHEN** professor saves exercise without publishing
- **THEN** exercise is visible only to professor, not students

#### Scenario: Publish exercise
- **WHEN** professor publishes exercise
- **THEN** exercise becomes visible to students in assigned classes

### Requirement: Exercise tags and categories
The system SHALL allow professors to tag exercises for organization.

#### Scenario: Add tags
- **WHEN** professor adds tags ["regression", "pandas", "intermediate"]
- **THEN** system stores tags and enables filtering by tag

### Requirement: Edit exercise
The system SHALL allow professors to modify existing exercises.

#### Scenario: Update description
- **WHEN** professor updates exercise description
- **THEN** system saves changes and updates timestamp

#### Scenario: Edit with existing submissions
- **WHEN** professor edits exercise that has student submissions
- **THEN** system warns "X students have already submitted" but allows edits
