## ADDED Requirements

### Requirement: Extended user model for integrations
The User model SHALL include fields for external service linking.

#### Scenario: Integration fields present
- **WHEN** user record is created or updated
- **THEN** system supports the following nullable fields: hotmart_id (string, unique), discord_id (string, unique), whatsapp_number (string, E.164), lifecycle_status (enum), onboarding_token (string, unique), onboarding_token_expires_at (timestamp), manychat_subscriber_id (string)

### Requirement: Automated account creation via webhook
The system SHALL create user accounts automatically when Hotmart purchase is confirmed.

#### Scenario: Auto-create student on purchase
- **WHEN** Hotmart webhook triggers student creation
- **THEN** system creates User with role=student, hotmart_id set, lifecycle_status=pending_onboarding, and generates onboarding_token
- **AND** password is set to a random value (student resets via email or never uses web login if Discord-only)

#### Scenario: Existing user re-purchases
- **WHEN** Hotmart webhook arrives for email that already exists in system
- **THEN** system updates lifecycle_status and triggers reactivation (does not create duplicate)
