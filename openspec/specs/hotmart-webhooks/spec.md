## ADDED Requirements

### Requirement: Receive Hotmart webhooks
The system SHALL expose an endpoint to receive Hotmart webhook events.

#### Scenario: Valid webhook received
- **WHEN** Hotmart sends POST to /webhooks/hotmart with valid HMAC signature
- **THEN** system persists raw event, returns 200 immediately, and enqueues processing

#### Scenario: Invalid signature
- **WHEN** request arrives with invalid or missing HMAC signature
- **THEN** system returns 401 Unauthorized and does not process

#### Scenario: Duplicate event
- **WHEN** Hotmart sends webhook with transaction_id that was already processed
- **THEN** system returns 200 (idempotent) and skips processing

### Requirement: Supported Hotmart events
The system SHALL process the following Hotmart webhook event types.

#### Scenario: PURCHASE_APPROVED
- **WHEN** event type is PURCHASE_APPROVED
- **THEN** system extracts buyer email, product ID, and transaction ID
- **AND** triggers lifecycle transition (→ pending_onboarding or → active for re-purchase)

#### Scenario: PURCHASE_DELAYED
- **WHEN** event type is PURCHASE_DELAYED (boleto pending)
- **THEN** system extracts buyer email and product ID
- **AND** triggers lifecycle transition (→ pending_payment)

#### Scenario: PURCHASE_REFUNDED
- **WHEN** event type is PURCHASE_REFUNDED
- **THEN** system extracts buyer email and transaction ID
- **AND** triggers lifecycle transition (→ churned)

#### Scenario: SUBSCRIPTION_CANCELLATION
- **WHEN** event type is SUBSCRIPTION_CANCELLATION
- **THEN** system extracts subscriber email
- **AND** triggers lifecycle transition (→ churned)

#### Scenario: Unrecognized event type
- **WHEN** event type is not in supported list
- **THEN** system persists raw event with status "ignored" and returns 200

### Requirement: Webhook processing pipeline
The system SHALL process webhooks asynchronously via Celery.

#### Scenario: Async processing
- **WHEN** valid webhook is received
- **THEN** system persists event in event_log, enqueues Celery task `process_hotmart_event`, and returns 200
- **AND** Celery task parses payload, resolves student by hotmart email, and calls lifecycle.transition()

#### Scenario: Student not found for cancellation
- **WHEN** cancellation event arrives for email not in system
- **THEN** system logs warning and marks event as "no_match"

#### Scenario: Processing failure
- **WHEN** Celery task fails (DB error, integration timeout)
- **THEN** task retries once; if still fails, event marked as "failed" in event_log and admin alerted

### Requirement: Webhook signature validation
The system SHALL validate Hotmart webhook authenticity via HMAC.

#### Scenario: HMAC validation
- **WHEN** webhook arrives with X-Hotmart-Hottok header
- **THEN** system compares header value against configured HOTMART_HOTTOK secret
- **AND** rejects request if mismatch

### Requirement: Webhook configuration
The system SHALL require the following environment variables for Hotmart integration.

#### Configuration
- `HOTMART_HOTTOK`: string, secret token for webhook validation
- `HOTMART_WEBHOOK_ENABLED`: boolean, default false (feature flag to enable/disable processing)
