## ADDED Requirements

### Requirement: Create exercise list
The system SHALL allow professors to create lists grouping multiple exercises.

#### Scenario: Create list with title
- **WHEN** professor creates list "Assignment 1" for class
- **THEN** system creates empty list and returns list ID

#### Scenario: Set open/close dates
- **WHEN** professor sets opens_at to 2025-03-01 and closes_at to 2025-03-15
- **THEN** system stores dates and enforces access window

### Requirement: Add exercises to list
The system SHALL allow professors to add exercises to lists in specific order.

#### Scenario: Add exercise with weight
- **WHEN** professor adds exercise to list with position=1 and weight=2.0
- **THEN** system adds exercise at position 1, contributing 2x to final grade

#### Scenario: Reorder exercises
- **WHEN** professor changes exercise position from 2 to 1
- **THEN** system reorders list and updates all positions

#### Scenario: Add same exercise to multiple lists
- **WHEN** professor adds exercise to both "List A" and "List B"
- **THEN** system allows (exercises can belong to multiple lists)

### Requirement: Assign list to class
The system SHALL associate lists with specific classes.

#### Scenario: Assign list to class
- **WHEN** professor assigns list to class
- **THEN** all enrolled students see list in their dashboard

#### Scenario: Assign list to group
- **WHEN** professor assigns list to specific group within class
- **THEN** only group members see list, others do not

### Requirement: List visibility based on dates
The system SHALL control list visibility based on open/close dates.

#### Scenario: Before open date
- **WHEN** current date is before opens_at
- **THEN** students see list title but cannot access exercises

#### Scenario: Within active window
- **WHEN** current date is between opens_at and closes_at
- **THEN** students can view and submit all exercises

#### Scenario: After close date
- **WHEN** current date is after closes_at
- **THEN** students can view exercises and past submissions but cannot submit new ones

### Requirement: List progress tracking
The system SHALL show students their progress on lists.

#### Scenario: View list progress
- **WHEN** student views assigned list
- **THEN** system shows completion status (3/5 exercises completed)

#### Scenario: Exercise scores in list
- **WHEN** student views list with graded submissions
- **THEN** system shows score per exercise and weighted total

### Requirement: Randomize exercise order
The system SHALL allow professors to randomize exercise order per student.

#### Scenario: Enable randomization
- **WHEN** professor enables randomization for list
- **THEN** each student sees exercises in different random order

#### Scenario: Preserve order
- **WHEN** professor disables randomization
- **THEN** all students see same exercise order

### Requirement: Remove exercise from list
The system SHALL allow professors to remove exercises from lists.

#### Scenario: Remove exercise with no submissions
- **WHEN** professor removes exercise from list that has zero submissions
- **THEN** system removes exercise from list

#### Scenario: Remove exercise with submissions
- **WHEN** professor removes exercise from list that has student submissions
- **THEN** system warns "X submissions exist" and requires confirmation

### Requirement: List templates
The system SHALL allow professors to clone existing lists.

#### Scenario: Clone list
- **WHEN** professor clones list to new class
- **THEN** system creates new list with same exercises and settings, new dates

### Requirement: Late submission penalty
The system SHALL allow professors to configure late penalties.

#### Scenario: 10% penalty per day
- **WHEN** professor sets late_penalty=10 (percent per day)
- **THEN** submission 1 day late receives 90% of earned score, 2 days = 80%, etc.

#### Scenario: Hard deadline
- **WHEN** professor sets late_penalty=null
- **THEN** submissions after closes_at are rejected
