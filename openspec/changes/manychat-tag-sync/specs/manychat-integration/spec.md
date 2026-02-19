## ADDED Requirements

### Requirement: Dual tag schema per course
The system SHALL maintain two ManyChat tags per course for each student: a permanent course tag and a mutable status tag.

#### Scenario: Course tag applied on first enrollment
- **WHEN** sync processes a student active in a product for the first time
- **THEN** system adds tag `{course_name}` to ManyChat subscriber (e.g., "Senhor das LLMs")
- **AND** adds tag `{course_name}, Ativo` (e.g., "Senhor das LLMs, Ativo")

#### Scenario: Status tag updated on status change
- **WHEN** sync detects status change for a student in a course
- **THEN** system removes ALL possible status tags for that course: `{course_name}, Ativo`, `{course_name}, Inadimplente`, `{course_name}, Cancelado`, `{course_name}, Reembolsado`
- **AND** adds only the current status tag: `{course_name}, {new_status}`
- **AND** course tag `{course_name}` is NOT removed (it is permanent)

#### Scenario: Total tags per student
- **WHEN** student has N courses in their history
- **THEN** student has exactly 2×N tags: one course tag and one status tag per course

#### Scenario: Subscriber not found in ManyChat
- **WHEN** `find_subscriber(whatsapp_number)` returns None for a student
- **THEN** system logs warning with student email and skips tag operations for that student
- **AND** sync continues to next student without failure

#### Scenario: Student has no whatsapp_number
- **WHEN** student record has no `whatsapp_number`
- **THEN** system skips ManyChat operations and logs info-level message
- **AND** `student_course_status` is still updated in the database

### Requirement: Batch sync job
The system SHALL provide a Celery task `sync_manychat_tags` that reconciles ManyChat tags for all active products.

#### Scenario: Full sync run
- **WHEN** `sync_manychat_tags` executes
- **THEN** system fetches active buyers from Hotmart for each configured product
- **AND** updates `student_course_status` table for all discovered (user, product) pairs
- **AND** applies ManyChat tags for all students with a known subscriber_id
- **AND** logs a `manychat.sync_completed` event with counters: `synced`, `skipped_no_phone`, `skipped_no_subscriber`, `status_changes`

#### Scenario: Idempotent execution
- **WHEN** `sync_manychat_tags` runs twice in a row without any Hotmart status changes
- **THEN** no database writes occur and no ManyChat API tag changes are made

#### Scenario: Partial failure tolerance
- **WHEN** ManyChat API returns an error for one student
- **THEN** system logs the error and continues processing remaining students
- **AND** failed student is included in `skipped_error` counter in completion event

### Requirement: Manual sync trigger
The system SHALL expose an admin endpoint to trigger ManyChat tag sync on demand.

#### Scenario: Admin triggers sync
- **WHEN** admin sends `POST /admin/events/manychat-sync` with optional `product_id` body parameter
- **THEN** system enqueues `sync_manychat_tags` Celery task
- **AND** returns `{"task_id": "...", "message": "Sync enqueued"}`
- **AND** requires ADMIN role

#### Scenario: Product-scoped sync
- **WHEN** admin includes `product_id` in request body
- **THEN** sync runs only for the specified product
- **AND** all other products are skipped

### Requirement: Daily beat schedule
The system SHALL run `sync_manychat_tags` automatically once per day.

#### Scenario: Scheduled execution
- **WHEN** Celery beat triggers at configured time (default: 02:00 UTC)
- **THEN** `sync_manychat_tags` runs for all products with no `product_id` filter

### Requirement: Phone number population from Hotmart
The system SHALL populate `user.whatsapp_number` from Hotmart `GET /sales/users` during the student import sync.

#### Scenario: Phone found in Hotmart
- **WHEN** `sync_hotmart_students` processes a buyer and Hotmart returns `cellphone` or `phone`
- **THEN** system sets `user.whatsapp_number` to the non-empty value (preferring `cellphone`)
- **AND** value is stored without country code prefix (raw from Hotmart)

#### Scenario: Phone already set
- **WHEN** `user.whatsapp_number` is already populated
- **THEN** system does not overwrite unless the new value is non-empty and different
