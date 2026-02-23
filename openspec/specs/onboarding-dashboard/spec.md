## ADDED Requirements

### Requirement: Onboarding students listing endpoint
The system SHALL expose `GET /onboarding/students` that returns students with lifecycle and token information, accessible only by admin.

#### Scenario: List all students with onboarding info
- **WHEN** admin calls `GET /onboarding/students`
- **THEN** returns list of students with fields: `id`, `name`, `email`, `whatsapp_number`, `lifecycle_status`, `token_status` (none/valid/expired/activated), `token_expires_in_days` (nullable), `last_message_at` (nullable)
- **AND** students are ordered by lifecycle_status priority: pending students first (pending_onboarding, pending_payment), then active

#### Scenario: Filter by course
- **WHEN** admin calls `GET /onboarding/students?course_id=5`
- **THEN** returns only students associated with that product via HotmartBuyer

#### Scenario: Token status derivation
- **WHEN** student has `lifecycle_status = active`
- **THEN** `token_status` is `activated`

- **WHEN** student has `onboarding_token IS NULL` and `lifecycle_status != active`
- **THEN** `token_status` is `none`

- **WHEN** student has `onboarding_token_expires_at < now()` and `lifecycle_status != active`
- **THEN** `token_status` is `expired`

- **WHEN** student has valid non-expired token and `lifecycle_status != active`
- **THEN** `token_status` is `valid` and `token_expires_in_days` contains remaining days

#### Scenario: Last message timestamp
- **WHEN** student was included in a previous MessageCampaign with status `sent`
- **THEN** `last_message_at` contains the most recent `MessageRecipient.sent_at` for that user

- **WHEN** student was never included in any campaign
- **THEN** `last_message_at` is null

#### Scenario: Non-admin access denied
- **WHEN** non-admin user calls `GET /onboarding/students`
- **THEN** returns 403

### Requirement: Onboarding summary endpoint
The system SHALL expose `GET /onboarding/summary` that returns funnel counts, accessible only by admin.

#### Scenario: Summary counts
- **WHEN** admin calls `GET /onboarding/summary`
- **THEN** returns `{"activated": <count>, "pending": <count>, "no_whatsapp": <count>, "total": <count>}`
- **AND** `activated` counts students with `lifecycle_status = active`
- **AND** `pending` counts students with `lifecycle_status IN (pending_onboarding, pending_payment)`
- **AND** `no_whatsapp` counts pending students with `whatsapp_number IS NULL`

#### Scenario: Filter summary by course
- **WHEN** admin calls `GET /onboarding/summary?course_id=5`
- **THEN** counts are scoped to students of that product

### Requirement: Onboarding dashboard frontend
The system SHALL provide an admin page showing the onboarding funnel with manual messaging capability.

#### Scenario: Dashboard layout
- **WHEN** admin navigates to the onboarding page
- **THEN** page displays: summary bar with funnel counts, student list table, and compose area for manual messaging

#### Scenario: Student list display
- **WHEN** dashboard loads
- **THEN** table shows columns: name, WhatsApp indicator, token status with visual differentiation (none/valid/expired/activated), last message date
- **AND** pending students with WhatsApp have a selection checkbox
- **AND** activated students do not have a checkbox

#### Scenario: Course filter
- **WHEN** admin selects a course from the dropdown
- **THEN** student list and summary update to show only students from that course

#### Scenario: Manual message composition
- **WHEN** admin selects pending students and writes a message with `{token}`
- **THEN** compose area shows tag insertion buttons for `{primeiro_nome}`, `{nome}`, `{token}`, `{email}`
- **AND** send button shows count of selected recipients

#### Scenario: Send manual message
- **WHEN** admin clicks send with selected students and composed message
- **THEN** system calls `POST /messaging/send` with selected user IDs and template
- **AND** shows confirmation with recipient count before sending
- **AND** displays success feedback with link to campaign detail page

### Requirement: Template config panel
The system SHALL provide a config panel for editing lifecycle message templates from the admin UI.

#### Scenario: Open config panel
- **WHEN** admin clicks the config/gear button on the onboarding dashboard
- **THEN** a modal or drawer opens showing all lifecycle message templates (onboarding, welcome, welcome_back, churn)

#### Scenario: Edit template
- **WHEN** admin modifies a template text and clicks save
- **THEN** system calls `PATCH /admin/templates/{event_type}` with new template text
- **AND** shows success feedback

#### Scenario: Template preview
- **WHEN** admin is editing a template
- **THEN** tag insertion buttons are available for supported variables
- **AND** template shows which variables are valid for each event type
