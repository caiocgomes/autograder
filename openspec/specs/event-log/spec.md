## ADDED Requirements

### Requirement: Persist all lifecycle events
The system SHALL log every significant action as an append-only event record.

#### Scenario: Successful event
- **WHEN** any lifecycle transition, side-effect, or webhook processing completes
- **THEN** system creates event record with type, actor, target, payload, and status "processed"

#### Scenario: Failed event
- **WHEN** a side-effect or webhook processing fails after retry
- **THEN** system creates event record with status "failed" and error details in payload

### Requirement: Event types
The system SHALL support the following event types.

#### Event types
- `hotmart.purchase_approved`: Hotmart purchase webhook received
- `hotmart.purchase_delayed`: Hotmart boleto webhook received
- `hotmart.purchase_refunded`: Hotmart refund webhook received
- `hotmart.subscription_cancelled`: Hotmart cancellation webhook received
- `lifecycle.transition`: Student state changed (payload includes from_state, to_state, trigger)
- `discord.role_assigned`: Discord role added to user
- `discord.role_revoked`: Discord role removed from user
- `discord.registration_completed`: Student linked Discord account
- `manychat.tag_added`: ManyChat tag added to subscriber
- `manychat.tag_removed`: ManyChat tag removed from subscriber
- `manychat.flow_triggered`: ManyChat flow triggered
- `enrollment.enrolled`: Student enrolled in class
- `enrollment.unenrolled`: Student unenrolled from class
- `submission.created`: Student submitted work
- `grade.published`: Grade made visible to student
- `admin.manual_retry`: Admin manually retried a failed side-effect

### Requirement: Event data model
The system SHALL store events with the following structure.

#### Data model: Event
- `id`: integer, primary key, auto-increment
- `type`: string, event type from supported list
- `actor_id`: integer, nullable, FK to User (who triggered; null for system/webhook)
- `target_id`: integer, nullable, FK to User (who was affected)
- `payload`: JSONB, event-specific data
- `status`: enum (processed, failed, ignored)
- `error_message`: text, nullable (populated on failure)
- `created_at`: timestamp, server default now()

### Requirement: Admin dashboard for failed events
The system SHALL provide an admin view of events that need attention.

#### Scenario: View failed events
- **WHEN** admin requests failed events list
- **THEN** system returns events with status "failed", ordered by most recent, with event type, target student, error message, and timestamp

#### Scenario: Manual retry
- **WHEN** admin clicks retry on a failed event
- **THEN** system re-executes the failed side-effect and updates event status to "processed" on success or creates new "failed" event on failure

#### Scenario: Filter events by student
- **WHEN** admin filters events by student ID
- **THEN** system returns all events where target_id matches, providing full audit trail for that student

#### Scenario: Filter events by type
- **WHEN** admin filters events by type (e.g., "discord.role_assigned")
- **THEN** system returns matching events across all students

### Requirement: Event retention
The system SHALL retain all events indefinitely (append-only, no automatic deletion).

#### Scenario: Event immutability
- **WHEN** event is created
- **THEN** event record is never updated or deleted (new events are created for retries, status changes create new events)

#### Exception: Status update on retry
- **WHEN** admin manually retries a failed event and it succeeds
- **THEN** original event status is updated from "failed" to "processed" (only exception to immutability)
## Requirements
### Requirement: Persist all lifecycle events
The system SHALL log every significant action as an append-only event record.

#### Scenario: Successful event
- **WHEN** any lifecycle transition, side-effect, or webhook processing completes
- **THEN** system creates event record with type, actor, target, payload, and status "processed"

#### Scenario: Failed event
- **WHEN** a side-effect or webhook processing fails after retry
- **THEN** system creates event record with status "failed" and error details in payload

### Requirement: Event types
The system SHALL support the following event types.

#### Event types
- `hotmart.purchase_approved`: Hotmart purchase webhook received
- `hotmart.purchase_delayed`: Hotmart boleto webhook received
- `hotmart.purchase_refunded`: Hotmart refund webhook received
- `hotmart.subscription_cancelled`: Hotmart cancellation webhook received
- `lifecycle.transition`: Student state changed (payload includes from_state, to_state, trigger)
- `discord.role_assigned`: Discord role added to user
- `discord.role_revoked`: Discord role removed from user
- `discord.registration_completed`: Student linked Discord account
- `manychat.tag_added`: ManyChat tag added to subscriber
- `manychat.tag_removed`: ManyChat tag removed from subscriber
- `manychat.flow_triggered`: ManyChat flow triggered
- `enrollment.enrolled`: Student enrolled in class
- `enrollment.unenrolled`: Student unenrolled from class
- `submission.created`: Student submitted work
- `grade.published`: Grade made visible to student
- `admin.manual_retry`: Admin manually retried a failed side-effect

### Requirement: Event data model
The system SHALL store events with the following structure.

#### Data model: Event
- `id`: integer, primary key, auto-increment
- `type`: string, event type from supported list
- `actor_id`: integer, nullable, FK to User (who triggered; null for system/webhook)
- `target_id`: integer, nullable, FK to User (who was affected)
- `payload`: JSONB, event-specific data
- `status`: enum (processed, failed, ignored)
- `error_message`: text, nullable (populated on failure)
- `created_at`: timestamp, server default now()

### Requirement: Admin dashboard for failed events
The system SHALL provide an admin view of events that need attention.

#### Scenario: View failed events
- **WHEN** admin requests failed events list
- **THEN** system returns events with status "failed", ordered by most recent, with event type, target student, error message, and timestamp

#### Scenario: Manual retry
- **WHEN** admin clicks retry on a failed event
- **THEN** system re-executes the failed side-effect and updates event status to "processed" on success or creates new "failed" event on failure

#### Scenario: Filter events by student
- **WHEN** admin filters events by student ID
- **THEN** system returns all events where target_id matches, providing full audit trail for that student

#### Scenario: Filter events by type
- **WHEN** admin filters events by type (e.g., "discord.role_assigned")
- **THEN** system returns matching events across all students

### Requirement: Event retention
The system SHALL retain all events indefinitely (append-only, no automatic deletion).

#### Scenario: Event immutability
- **WHEN** event is created
- **THEN** event record is never updated or deleted (new events are created for retries, status changes create new events)

#### Exception: Status update on retry
- **WHEN** admin manually retries a failed event and it succeeds
- **THEN** original event status is updated from "failed" to "processed" (only exception to immutability)

