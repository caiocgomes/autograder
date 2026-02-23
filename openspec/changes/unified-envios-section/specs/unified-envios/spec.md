## ADDED Requirements

### Requirement: Envios page with campaign list
The system SHALL provide a page at `/professor/envios` that displays all message campaigns in a table, ordered by creation date descending. Accessible by admin only.

#### Scenario: Campaign list display
- **WHEN** admin navigates to `/professor/envios`
- **THEN** page displays a table with columns: course name, status (badge), progress (sent/total), created date
- **AND** campaigns are fetched via `GET /messaging/campaigns`
- **AND** clicking a row navigates to `/professor/envios/campaigns/:id`

#### Scenario: Status badges
- **WHEN** campaign has status `sending`
- **THEN** badge is blue/yellow indicating in-progress
- **WHEN** campaign has status `completed`
- **THEN** badge is green
- **WHEN** campaign has status `partial_failure` or `failed`
- **THEN** badge is red/orange

#### Scenario: New send button
- **WHEN** admin clicks "+ Novo Envio" button
- **THEN** the page shows the new send flow inline or navigates to the compose section

### Requirement: Unified new send flow
The system SHALL provide a single compose flow for creating message campaigns, replacing both MessagingPage and OnboardingPage compose flows.

#### Scenario: Course selection
- **WHEN** admin starts a new send
- **THEN** a course dropdown is shown, populated via `GET /messaging/courses`
- **AND** selecting a course loads recipients for that course

#### Scenario: Audience filter by lifecycle status
- **WHEN** admin selects a course
- **THEN** filter buttons appear: Todos, Pending Payment, Pending Onboarding, Active, Churned
- **AND** default is "Todos"
- **AND** selecting a filter calls `GET /messaging/recipients?course_id=X&lifecycle_status=Y`
- **AND** recipient list updates to show only matching students

#### Scenario: Recipient selection
- **WHEN** recipients are loaded
- **THEN** each recipient with a WhatsApp number has a checkbox
- **AND** a "select all" checkbox selects all recipients with WhatsApp
- **AND** a count shows "N alunos selecionados (M sem WhatsApp)"

#### Scenario: Template editor with all tags
- **WHEN** admin composes a message
- **THEN** a textarea is shown with tag insertion buttons: `{nome}`, `{primeiro_nome}`, `{email}`, `{turma}`, `{token}`
- **AND** clicking a tag inserts it at cursor position in the textarea

#### Scenario: Message preview
- **WHEN** admin has selected at least one recipient and typed a template
- **THEN** a preview section shows the resolved message for the first selected recipient

#### Scenario: LLM variations
- **WHEN** admin clicks "Gerar variações"
- **THEN** system calls `POST /messaging/variations` with the template
- **AND** displays generated variations with checkboxes for approval
- **AND** only approved variations are included in the send request

#### Scenario: Throttle configuration
- **WHEN** compose flow is visible
- **THEN** throttle min/max fields are shown with defaults 15s and 25s

#### Scenario: Send confirmation and dispatch
- **WHEN** admin clicks send button
- **THEN** a confirmation dialog shows recipient count
- **AND** on confirm, calls `POST /messaging/send` with user_ids, message_template, course_id, throttle config, and approved variations
- **AND** on success, navigates to campaign detail page at `/professor/envios/campaigns/:id`

### Requirement: Template config accessible from Envios
The system SHALL provide access to the lifecycle template configuration modal from the Envios page.

#### Scenario: Open template config
- **WHEN** admin clicks "Configurar templates" button on the Envios page
- **THEN** the existing TemplateConfigModal opens
- **AND** admin can view and edit lifecycle templates (onboarding, welcome, welcome_back, churn)

### Requirement: Sidebar navigation updated
The system SHALL show "Envios" in the professor/admin sidebar, replacing "Mensagens" and "Onboarding".

#### Scenario: Sidebar items
- **WHEN** admin views the sidebar
- **THEN** "Envios" link is shown pointing to `/professor/envios`
- **AND** "Mensagens" and "Onboarding" links are removed
