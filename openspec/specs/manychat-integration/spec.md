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
