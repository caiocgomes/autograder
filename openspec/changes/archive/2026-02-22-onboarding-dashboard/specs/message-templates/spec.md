## ADDED Requirements

### Requirement: MessageTemplate model
The system SHALL store lifecycle message templates in the database with a `message_templates` table.

#### Scenario: Table schema
- **WHEN** the migration runs
- **THEN** `message_templates` table exists with columns: `id` (PK), `event_type` (unique enum: onboarding, welcome, welcome_back, churn), `template_text` (text, not null), `updated_at` (timestamp), `updated_by` (FK to users, nullable)

#### Scenario: One template per event type
- **WHEN** a template row exists for event_type `onboarding`
- **THEN** no second row with event_type `onboarding` can be inserted (unique constraint)

### Requirement: Admin template endpoints
The system SHALL expose CRUD endpoints for managing lifecycle message templates, accessible only by admin.

#### Scenario: List all templates
- **WHEN** admin calls `GET /admin/templates`
- **THEN** returns list of all templates with `event_type`, `template_text`, `updated_at`
- **AND** for event types without a DB row, returns the hardcoded default with a `is_default: true` flag

#### Scenario: Update template
- **WHEN** admin calls `PATCH /admin/templates/onboarding` with `{"template_text": "Oi {primeiro_nome}! Token: {token}"}`
- **THEN** upserts the template row (creates if not exists, updates if exists)
- **AND** sets `updated_at` to current timestamp and `updated_by` to the admin user
- **AND** returns the updated template

#### Scenario: Reset to default
- **WHEN** admin calls `DELETE /admin/templates/onboarding`
- **THEN** deletes the DB row for that event type
- **AND** subsequent reads return the hardcoded default with `is_default: true`

#### Scenario: Validate template variables
- **WHEN** admin submits a template with `{saldo_bancario}`
- **THEN** returns 422 with error indicating invalid variable
- **AND** valid variables per event type: onboarding allows `{primeiro_nome}`, `{nome}`, `{token}`, `{product_name}`; welcome/welcome_back/churn allow `{primeiro_nome}`, `{nome}`, `{product_name}`

#### Scenario: Non-admin access denied
- **WHEN** non-admin user calls any `/admin/templates` endpoint
- **THEN** returns 403

### Requirement: Lifecycle template resolution from database
The system SHALL read message templates from database when executing lifecycle side-effects, falling back to hardcoded constants.

#### Scenario: Template exists in database
- **WHEN** lifecycle transition triggers a WhatsApp message
- **THEN** system queries `message_templates` for the matching event_type
- **AND** uses the DB template for message composition

#### Scenario: No template in database (fallback)
- **WHEN** lifecycle transition triggers a WhatsApp message and no DB row exists for that event_type
- **THEN** system uses the hardcoded constant (MSG_ONBOARDING, MSG_WELCOME, etc.)

#### Scenario: Database query fails (fallback)
- **WHEN** lifecycle transition triggers a WhatsApp message and the DB query raises an exception
- **THEN** system logs the error and uses the hardcoded constant
- **AND** lifecycle transition continues without interruption
