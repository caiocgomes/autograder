## ADDED Requirements

### Requirement: Professor can define rubric dimensions for an exercise

The system SHALL allow professors to define a structured rubric when creating or editing an exercise with `grading_mode == llm_first`. Each rubric dimension MUST have a name, description, weight (0.0-1.0), and position. The sum of all dimension weights MUST equal 1.0.

#### Scenario: Create exercise with rubric

- **WHEN** a professor creates an exercise with `grading_mode == llm_first` and provides rubric dimensions with weights summing to 1.0
- **THEN** the system creates the exercise and persists each `RubricDimension` record linked to the exercise

#### Scenario: Rejected rubric with invalid weights

- **WHEN** a professor creates an exercise with `grading_mode == llm_first` and provides rubric dimensions with weights summing to a value other than 1.0
- **THEN** the system returns HTTP 400 with message indicating weights must sum to 1.0

#### Scenario: Exercise with llm_first requires rubric

- **WHEN** a professor creates an exercise with `grading_mode == llm_first` and provides no rubric dimensions
- **THEN** the system returns HTTP 400 with message indicating that LLM-first exercises require at least one rubric dimension

#### Scenario: Test-first exercise ignores rubric

- **WHEN** a professor creates an exercise with `grading_mode == test_first` and provides rubric dimensions
- **THEN** the system ignores the rubric dimensions and creates the exercise without them

### Requirement: LLM-first grading pipeline

The system SHALL evaluate submissions against the exercise rubric using the configured LLM provider. The pipeline MUST produce a score (0-100) and feedback per rubric dimension, plus an overall feedback text.

#### Scenario: Successful LLM-first grading of file submission

- **WHEN** a submission is created for an exercise with `grading_mode == llm_first` and `submission_type == file_upload`
- **THEN** the system enqueues a `grade_llm_first` Celery task that extracts content from the file, builds a prompt with the rubric dimensions, calls the LLM, parses per-dimension scores, persists `RubricScore` records, computes the weighted `final_score`, creates a `Grade` record, and marks the submission as `COMPLETED`

#### Scenario: Successful LLM-first grading of code submission

- **WHEN** a submission is created for an exercise with `grading_mode == llm_first` and `submission_type == code`
- **THEN** the system enqueues `grade_llm_first` that uses the `code` field directly (no file extraction), builds the rubric prompt, and follows the same scoring pipeline

#### Scenario: LLM response cache hit

- **WHEN** the `grade_llm_first` task processes a submission whose `content_hash` matches a previous evaluation for the same exercise
- **THEN** the system copies the cached scores and feedback without calling the LLM, marks `RubricScore` records as cached

#### Scenario: LLM returns malformed response

- **WHEN** the LLM returns a response that cannot be parsed as valid JSON or contains dimension names not matching the rubric
- **THEN** the system retries the LLM call once with a corrective prompt. If the second attempt also fails, the submission is marked as `FAILED` with an internal error message

#### Scenario: LLM API failure

- **WHEN** the LLM API returns an error or times out
- **THEN** the system retries up to 3 times with exponential backoff. After exhausting retries, the submission is marked as `FAILED`

### Requirement: Per-dimension scores visible to student

The system SHALL return per-dimension scores and feedback when a student or professor retrieves submission results for an LLM-first exercise.

#### Scenario: Student views rubric scores

- **WHEN** a student requests submission results for an exercise with `grading_mode == llm_first`
- **THEN** the response includes `rubric_scores`: an array of objects with `dimension_name`, `dimension_weight`, `score`, and `feedback`, plus `overall_feedback` from the LLM evaluation

#### Scenario: Professor views rubric scores for any student

- **WHEN** a professor requests submission results for a student's submission on an LLM-first exercise
- **THEN** the response includes the same `rubric_scores` array as the student view

### Requirement: Final score calculation for LLM-first exercises

The system SHALL compute the final score as the weighted sum of per-dimension scores: `final_score = sum(dimension.weight * rubric_score.score)` for all dimensions. Late penalty MUST be applied after the weighted sum.

#### Scenario: Weighted score calculation

- **WHEN** an exercise has three rubric dimensions with weights 0.4, 0.3, 0.3 and the LLM assigns scores 80, 90, 70
- **THEN** the `final_score` is `0.4*80 + 0.3*90 + 0.3*70 = 32 + 27 + 21 = 80`

#### Scenario: Late penalty applied to LLM-first score

- **WHEN** a submission is late by 2 days and the exercise list has `late_penalty_percent_per_day = 10`
- **THEN** the system computes `final_score = weighted_sum - 20` (clamped to minimum 0)
