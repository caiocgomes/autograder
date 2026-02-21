# student-course-status Specification

## Purpose
TBD - created by archiving change manychat-tag-sync. Update Purpose after archive.
## Requirements
### Requirement: SCD Type 2 status history per (user, product)
The system SHALL maintain a `student_course_status` table with one row per status version per `(user_id, product_id)` pair, using valid_from/valid_to date ranges and an `is_current` boolean flag.

#### Scenario: New enrollment recorded
- **WHEN** sync detects a buyer active in a Hotmart product for the first time
- **THEN** system inserts a row with `valid_from = now()`, `valid_to = NULL`, `is_current = true`

#### Scenario: Status change recorded
- **WHEN** sync detects a status change for an existing `(user, product)` pair
- **THEN** system closes the current row (`valid_to = now()`, `is_current = false`) and inserts a new row with the new status, `valid_from = now()`, `valid_to = NULL`, `is_current = true`

#### Scenario: No-op on same status
- **WHEN** sync detects that the status for `(user, product)` is unchanged from `is_current` row
- **THEN** system makes no writes to the database (idempotent)

#### Scenario: Query current state
- **WHEN** any process needs the current status of a student per product
- **THEN** query `WHERE is_current = true` returns exactly one row per `(user_id, product_id)` pair

#### Scenario: Query status history
- **WHEN** admin queries history for a student
- **THEN** all rows for that `(user_id, product_id)` ordered by `valid_from` reconstruct the complete status timeline

### Requirement: Status vocabulary
The system SHALL map Hotmart transaction statuses to four business statuses.

#### Scenario: Active status mapping
- **WHEN** buyer's last relevant transaction has status APPROVED or COMPLETE (and no REFUNDED/CHARGEBACK)
- **THEN** `student_course_status.status = 'Ativo'`

#### Scenario: Overdue status mapping
- **WHEN** buyer has an OVERDUE transaction and no subsequent APPROVED/COMPLETE
- **THEN** `student_course_status.status = 'Inadimplente'`

#### Scenario: Cancelled status mapping
- **WHEN** buyer's subscription is CANCELLED or EXPIRED with no active renewal
- **THEN** `student_course_status.status = 'Cancelado'`

#### Scenario: Refunded status mapping
- **WHEN** buyer has a REFUNDED or CHARGEBACK transaction and no subsequent APPROVED/COMPLETE
- **THEN** `student_course_status.status = 'Reembolsado'`

### Requirement: Derived product access
The system SHALL apply status rows for all products a buyer has access to, including products derived from ProductAccessRule configuration.

#### Scenario: Direct purchase
- **WHEN** buyer purchases product A directly
- **THEN** a `student_course_status` row is created for product A

#### Scenario: Derived access via access rule
- **WHEN** buyer purchases product B, and product B has a ProductAccessRule granting access to product C
- **THEN** `student_course_status` rows are created for both product B and product C with the same status

#### Scenario: Access rule removal does not retroactively delete history
- **WHEN** a ProductAccessRule mapping is removed from the database
- **THEN** existing `student_course_status` rows are not deleted or modified

### Requirement: Historical coverage
The system SHALL scan Hotmart transaction history up to 6 years back to ensure complete coverage of older purchases.

#### Scenario: Old purchase discovered
- **WHEN** sync scans historical window and finds a buyer with COMPLETE status from 3 years ago
- **THEN** a `student_course_status` row is created with `valid_from` set to the discovery time (not the original purchase date)

#### Scenario: Window-based pagination
- **WHEN** product has more than 500 transactions in a 30-day window
- **THEN** system paginates via `page_token` until all results are consumed before advancing the window

