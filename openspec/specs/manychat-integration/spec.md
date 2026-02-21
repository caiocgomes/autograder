## ADDED Requirements

### Requirement: ManyChat state management
The system SHALL manage subscriber tags and custom fields in ManyChat per product.

#### Scenario: Add product tag on purchase
- **WHEN** lifecycle transitions student to pending_onboarding or active
- **THEN** system calls ManyChat API to add product-specific tag to subscriber (e.g., "curso-ml", "curso-dados")

#### Scenario: Remove product tag on churn
- **WHEN** lifecycle transitions student to churned
- **THEN** system calls ManyChat API to remove product-specific tag from subscriber

#### Scenario: Set custom fields
- **WHEN** student record is created or updated
- **THEN** system syncs relevant custom fields to ManyChat (name, email, onboarding_token, lifecycle_status)

#### Scenario: Subscriber not found
- **WHEN** ManyChat API returns 404 for subscriber (phone number not in ManyChat)
- **THEN** system logs warning, marks side-effect as failed, alerts admin
- **NOTE** This means the student hasn't interacted with ManyChat before; admin may need to manually trigger first contact

### Requirement: Transactional flow triggers
The system SHALL trigger ManyChat flows for lifecycle events.

#### Scenario: Onboarding flow
- **WHEN** student transitions to pending_onboarding
- **THEN** system triggers ManyChat flow "onboarding" with custom fields: student name, onboarding token, Discord invite link, product name

#### Scenario: Welcome confirmation flow
- **WHEN** student transitions to active
- **THEN** system triggers ManyChat flow "welcome-confirmed" confirming all access is set up

#### Scenario: Churn flow
- **WHEN** student transitions to churned
- **THEN** system triggers ManyChat flow "churn-notification" informing access has been revoked

#### Scenario: Welcome back flow
- **WHEN** churned student re-purchases (transitions to active)
- **THEN** system triggers ManyChat flow "welcome-back" confirming reactivation

### Requirement: Broadcast notifications
The system SHALL support sending notifications to product subscriber segments.

#### Scenario: New assignment notification
- **WHEN** professor publishes exercise list for a class linked to a product
- **THEN** system triggers ManyChat flow "new-assignment" for all subscribers with that product's tag, including exercise title and deadline

#### Scenario: Deadline reminder
- **WHEN** exercise list deadline is within 24 hours
- **THEN** system triggers ManyChat flow "deadline-reminder" for product subscribers who haven't submitted

### Requirement: ManyChat subscriber resolution
The system SHALL resolve ManyChat subscribers by phone number.

#### Scenario: Resolve subscriber
- **WHEN** system needs to interact with ManyChat for a student
- **THEN** system uses student's whatsapp_number to find ManyChat subscriber ID via API
- **AND** caches subscriber_id in student record for subsequent calls

#### Data model addition to User
- `manychat_subscriber_id`: string, nullable, cached ManyChat subscriber ID

### Requirement: ManyChat configuration
The system SHALL require the following environment variables.

#### Configuration
- `MANYCHAT_API_TOKEN`: string, ManyChat API authentication token
- `MANYCHAT_ENABLED`: boolean, default false (feature flag)
- `MANYCHAT_ONBOARDING_FLOW_ID`: string, flow ID for onboarding
- `MANYCHAT_WELCOME_FLOW_ID`: string, flow ID for welcome confirmation
- `MANYCHAT_CHURN_FLOW_ID`: string, flow ID for churn notification
- `MANYCHAT_WELCOME_BACK_FLOW_ID`: string, flow ID for reactivation
- `MANYCHAT_NEW_ASSIGNMENT_FLOW_ID`: string, flow ID for new assignment notification
- `MANYCHAT_DEADLINE_REMINDER_FLOW_ID`: string, flow ID for deadline reminder
## Requirements
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

