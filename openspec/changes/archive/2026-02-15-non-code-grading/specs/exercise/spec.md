## ADDED Requirements

### Requirement: Exercise has submission_type field

The system SHALL store a `submission_type` enum on each exercise with values `code` (default) and `file_upload`. This field determines what the student submits.

#### Scenario: Default submission type for new exercises

- **WHEN** a professor creates an exercise without specifying `submission_type`
- **THEN** the exercise is created with `submission_type == code`

#### Scenario: Existing exercises retain code type

- **WHEN** the migration runs on a database with existing exercises
- **THEN** all existing exercises receive `submission_type == code`

#### Scenario: Professor sets file_upload type

- **WHEN** a professor creates an exercise with `submission_type == file_upload`
- **THEN** the exercise is created with `submission_type == file_upload` and the fields `template_code`, `language`, `timeout_seconds`, `memory_limit_mb` are ignored during grading

### Requirement: Exercise has grading_mode field

The system SHALL store a `grading_mode` enum on each exercise with values `test_first` (default) and `llm_first`. This field determines how the submission is evaluated.

#### Scenario: Default grading mode for new exercises

- **WHEN** a professor creates an exercise without specifying `grading_mode`
- **THEN** the exercise is created with `grading_mode == test_first`

#### Scenario: Existing exercises retain test_first mode

- **WHEN** the migration runs on a database with existing exercises
- **THEN** all existing exercises receive `grading_mode == test_first`

#### Scenario: Professor sets llm_first mode

- **WHEN** a professor creates an exercise with `grading_mode == llm_first`
- **THEN** the exercise is created with `grading_mode == llm_first` and the system requires rubric dimensions to be provided

### Requirement: Grading config fields conditional on grading_mode

The system SHALL validate exercise configuration fields based on `grading_mode`. Fields `has_tests`, `test_weight`, `llm_weight`, and test cases are relevant only for `test_first`. Rubric dimensions are relevant only for `llm_first`.

#### Scenario: Test-first exercise requires grading weights

- **WHEN** a professor creates an exercise with `grading_mode == test_first`
- **THEN** the system validates that `test_weight + llm_weight == 1.0` (existing behavior)

#### Scenario: LLM-first exercise ignores test weights

- **WHEN** a professor creates an exercise with `grading_mode == llm_first`
- **THEN** the system does not require or validate `test_weight` and `llm_weight` fields. The final score is computed from rubric dimension weights.

### Requirement: Exercise response includes new fields

The exercise API response MUST include `submission_type` and `grading_mode` fields. For exercises with `grading_mode == llm_first`, the response MUST also include `rubric_dimensions` as an array of objects with `id`, `name`, `description`, `weight`, and `position`.

#### Scenario: Exercise response with rubric

- **WHEN** a client requests an exercise with `grading_mode == llm_first` that has 3 rubric dimensions
- **THEN** the response includes `submission_type`, `grading_mode`, and `rubric_dimensions` array with 3 elements

#### Scenario: Exercise response without rubric

- **WHEN** a client requests an exercise with `grading_mode == test_first`
- **THEN** the response includes `submission_type`, `grading_mode`, and `rubric_dimensions` as null or empty array
