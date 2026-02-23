## 1. MessageTemplate model and migration

- [x] 1.1 Create `MessageTemplate` SQLAlchemy model (event_type enum, template_text, updated_at, updated_by FK) in `app/models/`
- [x] 1.2 Create Alembic migration for `message_templates` table with unique constraint on event_type
- [x] 1.3 Write tests for MessageTemplate model constraints (unique event_type, valid enum values)

## 2. Admin template endpoints

- [x] 2.1 Create Pydantic schemas for template CRUD (request/response) with variable validation per event_type
- [x] 2.2 Write tests for `GET /admin/templates` (returns all 4 templates, includes hardcoded defaults for missing rows)
- [x] 2.3 Write tests for `PATCH /admin/templates/{event_type}` (upsert, variable validation, 422 on invalid vars)
- [x] 2.4 Write tests for `DELETE /admin/templates/{event_type}` (reset to default)
- [x] 2.5 Write tests for 403 on non-admin access
- [x] 2.6 Implement admin template router (`app/routers/admin_templates.py`) to pass all tests

## 3. Lifecycle template resolution from database

- [x] 3.1 Write tests for lifecycle reading template from DB (found → uses DB, not found → uses hardcoded, DB error → uses hardcoded)
- [x] 3.2 Modify `lifecycle.py` to query MessageTemplate before composing WhatsApp messages, with fallback to constants
- [x] 3.3 Add template variable resolution in lifecycle (replace `{primeiro_nome}`, `{nome}`, `{token}`, `{product_name}`)

## 4. Token auto-management in bulk messaging

- [x] 4.1 Write tests for `{token}` variable support: token null → generates, token expired → regenerates, token valid → uses existing
- [x] 4.2 Add `{token}` to allowed variables in messaging schema validation
- [x] 4.3 Implement token auto-management logic in `send_bulk_messages` task before template resolution

## 5. Onboarding API endpoints

- [x] 5.1 Create Pydantic schemas for onboarding responses (student list with token_status, summary counts)
- [x] 5.2 Write tests for `GET /onboarding/students` (token status derivation, last_message_at join, course filter, ordering)
- [x] 5.3 Write tests for `GET /onboarding/summary` (funnel counts, course filter)
- [x] 5.4 Write tests for 403 on non-admin access
- [x] 5.5 Implement onboarding router (`app/routers/onboarding.py`) to pass all tests

## 6. Frontend: Onboarding dashboard page

- [x] 6.1 Create OnboardingPage component with summary bar, student list table, and compose area
- [x] 6.2 Implement student list with token status display (none/valid/expired/activated), WhatsApp indicator, last message date
- [x] 6.3 Implement course filter dropdown (reuse existing courses endpoint)
- [x] 6.4 Implement student selection (checkboxes for pending + WhatsApp only)
- [x] 6.5 Implement compose area with tag insertion buttons ({primeiro_nome}, {nome}, {token}, {email}) and send action
- [x] 6.6 Add send confirmation dialog with recipient count
- [x] 6.7 Add route to admin layout and navigation

## 7. Frontend: Template config panel

- [x] 7.1 Create TemplateConfigModal component showing all 4 lifecycle templates with edit capability
- [x] 7.2 Implement template editing with tag insertion buttons and save/reset-to-default actions
- [x] 7.3 Wire config button on OnboardingPage to open the modal
