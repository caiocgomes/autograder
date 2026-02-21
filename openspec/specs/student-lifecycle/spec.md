## ADDED Requirements

### Requirement: Lifecycle state machine
The system SHALL manage student lifecycle through defined states and transitions.

#### States
- `pending_payment`: Hotmart purchase initiated but not confirmed (boleto)
- `pending_onboarding`: Payment confirmed, awaiting Discord registration
- `active`: Fully onboarded, all access granted
- `churned`: Subscription cancelled or refunded, access revoked
- `reactivated`: Re-purchased after churn (transitions immediately to active with side-effects)

#### Scenario: Purchase approved
- **WHEN** Hotmart webhook reports PURCHASE_APPROVED for new student
- **THEN** system creates student record with status `pending_onboarding` and triggers onboarding side-effects

#### Scenario: Purchase delayed (boleto)
- **WHEN** Hotmart webhook reports PURCHASE_DELAYED
- **THEN** system creates student record with status `pending_payment`; no access granted yet

#### Scenario: Delayed purchase confirmed
- **WHEN** Hotmart webhook reports PURCHASE_APPROVED for student in `pending_payment`
- **THEN** system transitions to `pending_onboarding` and triggers onboarding side-effects

#### Scenario: Discord registration completed
- **WHEN** student runs /registrar command in Discord with valid token
- **THEN** system transitions from `pending_onboarding` to `active` and triggers activation side-effects

#### Scenario: Subscription cancelled
- **WHEN** Hotmart webhook reports SUBSCRIPTION_CANCELLATION for active student
- **THEN** system transitions to `churned` and triggers churn side-effects

#### Scenario: Purchase refunded
- **WHEN** Hotmart webhook reports PURCHASE_REFUNDED for active student
- **THEN** system transitions to `churned` and triggers churn side-effects

#### Scenario: Re-purchase after churn
- **WHEN** Hotmart webhook reports PURCHASE_APPROVED for churned student
- **THEN** system transitions to `active` and triggers reactivation side-effects

### Requirement: Side-effects per transition
The system SHALL execute defined side-effects on each state transition.

#### Transition: → pending_onboarding
Side-effects:
1. Create student record in database
2. Add ManyChat tag for the product
3. Trigger ManyChat onboarding flow (sends WhatsApp with instructions + token)

#### Transition: → active
Side-effects:
1. Assign Discord roles (per product access rules)
2. Enroll in classes (per product access rules)
3. Send welcome message via ManyChat

#### Transition: → churned
Side-effects:
1. Revoke Discord roles
2. Unenroll from classes
3. Remove ManyChat product tag
4. Send churn notification via ManyChat

#### Transition: → active (reactivation from churned)
Side-effects:
1. Assign Discord roles
2. Enroll in classes
3. Add ManyChat product tag
4. Send welcome-back message via ManyChat

### Requirement: Side-effect failure handling
The system SHALL retry failed side-effects once, then alert on persistent failure.

#### Scenario: Side-effect succeeds
- **WHEN** side-effect executes successfully
- **THEN** system logs success in event log and continues to next side-effect

#### Scenario: Side-effect fails, retry succeeds
- **WHEN** side-effect fails on first attempt but succeeds on retry
- **THEN** system logs retry success in event log and continues

#### Scenario: Side-effect fails after retry
- **WHEN** side-effect fails on both attempts
- **THEN** system logs failure in event log, sends alert to admin (Discord DM or WhatsApp), and continues with remaining side-effects
- **AND** student remains in target state (partial side-effects applied)
- **AND** failed side-effect appears in admin dashboard "pending actions" view

### Requirement: Onboarding token
The system SHALL generate unique tokens for Discord registration linking.

#### Scenario: Token generation
- **WHEN** student transitions to `pending_onboarding`
- **THEN** system generates unique alphanumeric token (8 chars), stores with expiry (7 days), and includes in ManyChat onboarding flow

#### Scenario: Token validation
- **WHEN** student uses /registrar command with token
- **THEN** system validates token exists, is not expired, and is not already used

#### Scenario: Expired token
- **WHEN** student uses expired token
- **THEN** bot responds "Token expirado. Solicite um novo no WhatsApp." and system can regenerate via admin action

### Requirement: Extended user model
The User model SHALL include integration fields for lifecycle management.

#### Data model additions to User
- `hotmart_id`: string, nullable, unique (Hotmart buyer email or ID)
- `discord_id`: string, nullable, unique (Discord user snowflake ID)
- `whatsapp_number`: string, nullable (E.164 format)
- `lifecycle_status`: enum (pending_payment, pending_onboarding, active, churned)
- `onboarding_token`: string, nullable, unique
- `onboarding_token_expires_at`: timestamp, nullable
## Requirements
### Requirement: Lifecycle state machine
The system SHALL manage student lifecycle through defined states and transitions.

#### States
- `pending_payment`: Hotmart purchase initiated but not confirmed (boleto)
- `pending_onboarding`: Payment confirmed, awaiting Discord registration
- `active`: Fully onboarded, all access granted
- `churned`: Subscription cancelled or refunded, access revoked
- `reactivated`: Re-purchased after churn (transitions immediately to active with side-effects)

#### Scenario: Purchase approved
- **WHEN** Hotmart webhook reports PURCHASE_APPROVED for new student
- **THEN** system creates student record with status `pending_onboarding` and triggers onboarding side-effects

#### Scenario: Purchase delayed (boleto)
- **WHEN** Hotmart webhook reports PURCHASE_DELAYED
- **THEN** system creates student record with status `pending_payment`; no access granted yet

#### Scenario: Delayed purchase confirmed
- **WHEN** Hotmart webhook reports PURCHASE_APPROVED for student in `pending_payment`
- **THEN** system transitions to `pending_onboarding` and triggers onboarding side-effects

#### Scenario: Discord registration completed
- **WHEN** student runs /registrar command in Discord with valid token
- **THEN** system transitions from `pending_onboarding` to `active` and triggers activation side-effects

#### Scenario: Subscription cancelled
- **WHEN** Hotmart webhook reports SUBSCRIPTION_CANCELLATION for active student
- **THEN** system transitions to `churned` and triggers churn side-effects

#### Scenario: Purchase refunded
- **WHEN** Hotmart webhook reports PURCHASE_REFUNDED for active student
- **THEN** system transitions to `churned` and triggers churn side-effects

#### Scenario: Re-purchase after churn
- **WHEN** Hotmart webhook reports PURCHASE_APPROVED for churned student
- **THEN** system transitions to `active` and triggers reactivation side-effects

### Requirement: Side-effects per transition
The system SHALL execute defined side-effects on each state transition.

#### Transition: → pending_onboarding
Side-effects:
1. Create student record in database
2. Generate onboarding token
3. Send WhatsApp onboarding message via Evolution API (instructions + token + product name)

#### Transition: → active
Side-effects:
1. Assign Discord roles (per product access rules)
2. Enroll in classes (per product access rules)
3. Send WhatsApp welcome message via Evolution API

#### Transition: → churned
Side-effects:
1. Revoke Discord roles
2. Unenroll from classes
3. Send WhatsApp churn notification via Evolution API

#### Transition: → active (reactivation from churned)
Side-effects:
1. Assign Discord roles
2. Enroll in classes
3. Send WhatsApp welcome-back message via Evolution API

### Requirement: Side-effect failure handling
The system SHALL retry failed side-effects once, then alert on persistent failure.

#### Scenario: Side-effect succeeds
- **WHEN** side-effect executes successfully
- **THEN** system logs success in event log and continues to next side-effect

#### Scenario: Side-effect fails, retry succeeds
- **WHEN** side-effect fails on first attempt but succeeds on retry
- **THEN** system logs retry success in event log and continues

#### Scenario: Side-effect fails after retry
- **WHEN** side-effect fails on both attempts
- **THEN** system logs failure in event log, sends alert to admin (Discord DM or WhatsApp), and continues with remaining side-effects
- **AND** student remains in target state (partial side-effects applied)
- **AND** failed side-effect appears in admin dashboard "pending actions" view

### Requirement: Onboarding token
The system SHALL generate unique tokens for Discord registration linking.

#### Scenario: Token generation
- **WHEN** student transitions to `pending_onboarding`
- **THEN** system generates unique alphanumeric token (8 chars), stores with expiry (7 days), and includes in ManyChat onboarding flow

#### Scenario: Token validation
- **WHEN** student uses /registrar command with token
- **THEN** system validates token exists, is not expired, and is not already used

#### Scenario: Expired token
- **WHEN** student uses expired token
- **THEN** bot responds "Token expirado. Solicite um novo no WhatsApp." and system can regenerate via admin action

