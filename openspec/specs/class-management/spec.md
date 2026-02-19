## ADDED Requirements

### Requirement: Create class
The system SHALL allow professors to create classes.

#### Scenario: Successful class creation
- **WHEN** professor submits class name
- **THEN** system creates class, assigns professor as owner, generates invite code, and returns class ID

#### Scenario: Empty class name
- **WHEN** professor submits empty or whitespace-only class name
- **THEN** system returns error "Class name is required"

### Requirement: List classes
The system SHALL show users their associated classes.

#### Scenario: Professor views classes
- **WHEN** professor requests their classes
- **THEN** system returns all classes they created or teach

#### Scenario: Student views enrolled classes
- **WHEN** student requests their classes
- **THEN** system returns all classes they are enrolled in

### Requirement: Student enrollment via invite code
The system SHALL allow students to join classes using invite codes.

#### Scenario: Valid invite code
- **WHEN** student submits valid invite code
- **THEN** system enrolls student in class and returns success

#### Scenario: Invalid invite code
- **WHEN** student submits non-existent invite code
- **THEN** system returns error "Invalid invite code"

#### Scenario: Already enrolled
- **WHEN** student submits invite code for class they are already in
- **THEN** system returns error "Already enrolled in this class"

### Requirement: Bulk student enrollment
The system SHALL allow professors to import students via CSV.

#### Scenario: Valid CSV import
- **WHEN** professor uploads CSV with columns (email, name)
- **THEN** system creates accounts for new emails, enrolls all students, and returns summary (created X, enrolled Y)

#### Scenario: Invalid CSV format
- **WHEN** professor uploads CSV missing required columns
- **THEN** system returns error "CSV must have 'email' and 'name' columns"

#### Scenario: Partial success
- **WHEN** professor uploads CSV with some invalid emails
- **THEN** system enrolls valid entries, skips invalid ones, and returns detailed report

### Requirement: Create groups within class
The system SHALL allow professors to create groups within a class.

#### Scenario: Create group
- **WHEN** professor creates group with name in their class
- **THEN** system creates group and returns group ID

#### Scenario: Assign students to group
- **WHEN** professor adds student IDs to group
- **THEN** system assigns students to group

#### Scenario: Student in multiple groups
- **WHEN** professor attempts to add student already in another group of same class
- **THEN** system allows (students can belong to multiple groups)

### Requirement: Archive class
The system SHALL allow professors to archive completed classes.

#### Scenario: Archive class
- **WHEN** professor archives a class
- **THEN** system marks class as archived, hides from default listings, but preserves all data

#### Scenario: View archived classes
- **WHEN** professor requests archived classes
- **THEN** system returns list of archived classes with read-only access

### Requirement: Class roster management
The system SHALL allow professors to view and manage class roster.

#### Scenario: View enrolled students
- **WHEN** professor requests class roster
- **THEN** system returns list of enrolled students with enrollment dates

#### Scenario: Remove student from class
- **WHEN** professor removes student from class
- **THEN** system unenrolls student and revokes access to class exercises

### Requirement: Multiple class enrollment
The system SHALL allow students to enroll in multiple classes simultaneously.

#### Scenario: Student enrolls in second class
- **WHEN** student joins class B while already enrolled in class A
- **THEN** system enrolls student in both classes independently

## ADDED Requirements (orchestrator integration)

### Requirement: Automatic enrollment via product purchase
The system SHALL auto-enroll students in classes mapped to their purchased product.

#### Scenario: Product-driven enrollment
- **WHEN** student lifecycle transitions to active and product access rules include class enrollment
- **THEN** system enrolls student in all mapped classes automatically

#### Scenario: Product-driven unenrollment
- **WHEN** student lifecycle transitions to churned
- **THEN** system unenrolls student from all classes linked to the churned product
- **AND** submission history and grades are preserved (read-only)

#### Scenario: Manual enrollment coexists
- **WHEN** professor manually enrolls student via invite code
- **THEN** enrollment works as before, independent of product-based enrollment
- **AND** manual enrollments are NOT affected by churn (only product-driven enrollments are revoked)
