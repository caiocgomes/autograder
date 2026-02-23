## Why

The onboarding flow sends tokens automatically via webhook side-effects, but there's no admin visibility into the funnel (who activated, who's stuck, who never received) and no way to re-engage students manually. When the automatic send fails or the student ignores it, the only option is direct database access. Lifecycle message templates are hardcoded in Python, requiring a deploy to change wording.

## What Changes

- New admin dashboard showing all students by onboarding status with token state (none/valid/expired/activated) and last message timestamp
- Manual messaging from the dashboard: select pending students, compose message with `{token}` variable, send. System auto-generates or regenerates tokens as needed before sending
- Configurable lifecycle message templates stored in database, editable via admin UI, with hardcoded fallback
- `{token}` added as a valid template variable in the bulk messaging system

## Capabilities

### New Capabilities
- `onboarding-dashboard`: Admin UI for viewing student onboarding funnel, sending manual token messages, and configuring lifecycle templates
- `message-templates`: Database-backed configurable message templates for lifecycle events (onboarding, welcome, welcome_back, churn), global scope, with admin CRUD endpoints

### Modified Capabilities
- `student-lifecycle`: Lifecycle side-effects read message templates from database instead of hardcoded constants, with fallback to current hardcoded values
- `bulk-messaging-api`: Support `{token}` as a valid template variable; auto-generate/regenerate expired or missing tokens on send when `{token}` is used

## Impact

- **Backend**: New `MessageTemplate` model + migration, new admin endpoints for template CRUD, new endpoint for listing students by lifecycle status with token info, modifications to `lifecycle.py` template resolution, `{token}` variable support in messaging task
- **Frontend**: New Onboarding page in admin layout with student list, manual send form, and template config panel
- **APIs**: New `GET /admin/templates`, `PATCH /admin/templates/{event_type}`, new `GET /onboarding/students` endpoint
- **Database**: New `message_templates` table
