## ADDED Requirements

### Requirement: Test-based grading
The system SHALL grade submissions by running unit tests.

#### Scenario: All tests pass
- **WHEN** student code passes all 10 test cases
- **THEN** test score is 100%

#### Scenario: Partial pass
- **WHEN** student code passes 7 out of 10 tests
- **THEN** test score is 70%

#### Scenario: All tests fail
- **WHEN** student code passes 0 tests
- **THEN** test score is 0%

### Requirement: Test result details
The system SHALL provide detailed feedback per test case.

#### Scenario: Test passed
- **WHEN** test case succeeds
- **THEN** result shows "✓ Test: <name> - Passed"

#### Scenario: Test failed with message
- **WHEN** test case fails with assertion error
- **THEN** result shows "✗ Test: <name> - Failed: Expected 6, got 5"

#### Scenario: Hidden test feedback
- **WHEN** test is marked hidden and fails
- **THEN** result shows "✗ Test: <name> - Failed" without input/output details

### Requirement: LLM qualitative grading
The system SHALL evaluate code quality using LLM when enabled.

#### Scenario: LLM grading enabled
- **WHEN** exercise has llm_grading_enabled=true
- **THEN** system sends code + prompt to LLM API after test execution

#### Scenario: LLM feedback structure
- **WHEN** LLM evaluates code
- **THEN** response includes feedback text and numerical score (0-100)

#### Scenario: LLM prompt includes context
- **WHEN** LLM request is made
- **THEN** prompt includes: exercise description, student code, grading criteria

### Requirement: Composite scoring
The system SHALL combine test and LLM scores when both are enabled.

#### Scenario: Hybrid grading default weights
- **WHEN** exercise has both tests and LLM enabled
- **THEN** final score = (test_score * 0.7) + (llm_score * 0.3)

#### Scenario: Custom weights
- **WHEN** professor sets test_weight=0.5 and llm_weight=0.5
- **THEN** final score = (test_score * 0.5) + (llm_score * 0.5)

### Requirement: LLM response caching
The system SHALL cache LLM evaluations by code hash to reduce API costs.

#### Scenario: First submission of unique code
- **WHEN** student submits code never seen before
- **THEN** system calls LLM API and caches response with code hash

#### Scenario: Identical code resubmission
- **WHEN** student resubmits identical code
- **THEN** system retrieves cached LLM response without API call

#### Scenario: Cache hit across students
- **WHEN** student B submits same code as student A
- **THEN** system uses cached LLM response from student A's submission

### Requirement: Grading criteria configuration
The system SHALL allow professors to define custom grading criteria for LLM.

#### Scenario: Custom criteria
- **WHEN** professor sets criteria "Code clarity, efficiency, edge case handling"
- **THEN** LLM prompt includes these criteria for evaluation

#### Scenario: Default criteria
- **WHEN** professor does not specify criteria
- **THEN** system uses default "Code correctness, readability, best practices"

### Requirement: Grade publication control
The system SHALL allow professors to control when grades are visible to students.

#### Scenario: Auto-publish
- **WHEN** professor enables auto_publish for exercise
- **THEN** grades are visible immediately after grading completes

#### Scenario: Manual review
- **WHEN** professor disables auto_publish
- **THEN** grades remain hidden until professor manually publishes

#### Scenario: Batch publish
- **WHEN** professor reviews LLM feedback and clicks "Publish All"
- **THEN** all pending grades become visible to students

### Requirement: LLM feedback review
The system SHALL allow professors to review and edit LLM-generated feedback before publishing.

#### Scenario: View LLM feedback
- **WHEN** professor views submission with LLM grading
- **THEN** system displays LLM-generated feedback and suggested score

#### Scenario: Edit LLM feedback
- **WHEN** professor edits LLM feedback text or score
- **THEN** system saves edited version and marks as "reviewed"

#### Scenario: Override LLM score
- **WHEN** professor changes LLM score from 85 to 90
- **THEN** final score recalculates using new LLM score

### Requirement: Failure handling
The system SHALL handle grading failures gracefully.

#### Scenario: Test execution crash
- **WHEN** test harness crashes due to student code error
- **THEN** system marks submission as failed with error message, score = 0

#### Scenario: LLM API timeout
- **WHEN** LLM API call times out
- **THEN** system retries once, then falls back to test score only with note "LLM grading unavailable"

#### Scenario: LLM API rate limit
- **WHEN** LLM API returns rate limit error
- **THEN** system queues LLM grading for retry after 60 seconds

### Requirement: Partial credit for edge cases
The system SHALL support partial credit scenarios.

#### Scenario: Timeout on some tests
- **WHEN** student code times out on 2 out of 10 tests
- **THEN** those tests count as failed, score based on remaining 8 tests

#### Scenario: Syntax error in test setup
- **WHEN** test harness fails to import student code
- **THEN** all tests fail with error "Import failed: <error message>"

### Requirement: Score history
The system SHALL track score changes over multiple submissions.

#### Scenario: Improved score
- **WHEN** student's 2nd submission scores higher than 1st
- **THEN** system updates best score and marks 2nd as active grade

#### Scenario: Lower score
- **WHEN** student's 2nd submission scores lower than 1st
- **THEN** system keeps 1st submission's score as best score

### Requirement: Feedback accessibility
The system SHALL make grading feedback accessible to students.

#### Scenario: View test results
- **WHEN** student views graded submission
- **THEN** system displays test-by-test results with pass/fail status

#### Scenario: View LLM feedback
- **WHEN** submission has LLM grading and is published
- **THEN** system displays LLM feedback text and score breakdown
