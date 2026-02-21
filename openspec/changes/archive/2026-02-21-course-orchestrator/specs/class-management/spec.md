## ADDED Requirements

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
