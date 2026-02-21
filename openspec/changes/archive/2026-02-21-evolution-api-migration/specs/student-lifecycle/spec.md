## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Extended user model
**Reason**: `manychat_subscriber_id` field removed from User model — Evolution API uses `whatsapp_number` directly.
**Migration**: Alembic migration to drop `manychat_subscriber_id` column. All references to `user.manychat_subscriber_id` removed from lifecycle side-effects.
