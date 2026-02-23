## Context

Lifecycle message templates (onboarding, welcome, welcome_back, churn) are hardcoded as Python constants in `lifecycle.py`. Admin has no visibility into the onboarding funnel without database access. When automatic WhatsApp sends fail or students ignore tokens, there's no way to re-engage them without manual DB queries and Evolution API calls.

The bulk messaging V2 system already handles campaign tracking, template resolution, throttled sending, and retry. The onboarding dashboard reuses this infrastructure but adds token-aware logic and lifecycle-filtered views.

## Goals / Non-Goals

**Goals:**
- Admin can view onboarding funnel: who activated, who's pending, who never received a message
- Admin can send manual messages with `{token}` to selected pending students
- System auto-generates/regenerates tokens when sending messages with `{token}`
- Admin can configure lifecycle message templates from the UI
- Lifecycle side-effects read templates from database with hardcoded fallback

**Non-Goals:**
- Per-product template customization (global only for now)
- Automatic re-engagement drip campaigns (manual only)
- Editing templates for non-lifecycle messages (bulk campaigns compose freely)
- Token management outside of the send flow (no standalone regenerate button)

## Decisions

### 1. MessageTemplate model: single table with event_type enum

Store templates in a `message_templates` table with `event_type` as unique key (onboarding, welcome, welcome_back, churn). One row per event type, global scope.

**Why not config file or env vars?** Admin needs to edit from UI without deploys. DB is the simplest path given the existing stack.

**Why not per-product?** User explicitly scoped this to global. Adding `product_id` nullable FK later is a non-breaking migration.

### 2. Lifecycle reads from DB with hardcoded fallback

`lifecycle.py` queries `MessageTemplate` by event_type. If no row exists or DB query fails, falls back to current hardcoded constants. This ensures zero downtime during migration and graceful degradation.

**Alternative considered:** Seed templates on migration. Rejected because fallback is safer and the hardcoded messages are already working.

### 3. Token auto-management on send

When the bulk messaging task encounters `{token}` in the template, for each recipient:
- No token → generate new token (same logic as `generate_onboarding_token()`)
- Expired token → regenerate (new token, new expiry)
- Valid token → use existing

This happens in the Celery task before template resolution, not in the API endpoint. Keeps the endpoint fast and the token generation transactional with the send.

**Alternative considered:** Generate in the endpoint. Rejected because if the send fails/is cancelled, you've regenerated tokens unnecessarily.

### 4. Onboarding students endpoint: dedicated route

New `GET /onboarding/students` endpoint returns students filtered by lifecycle status with token info and last message timestamp. Separate from existing `/messaging/recipients` because:
- Different filters (lifecycle_status vs course)
- Different response shape (includes token status, expiry, activation info)
- Different access pattern (dashboard view vs send form)

Last message timestamp: join on `MessageRecipient` for the user's most recent `sent` entry. Simple query, no denormalization needed given the small scale (hundreds of students, not millions).

### 5. Frontend: new Onboarding page in admin layout

Single page with three sections:
1. **Summary bar**: counts by status (activated, pending, no WhatsApp)
2. **Student list**: table with name, WhatsApp, token status, last message, checkbox for pending students
3. **Compose area**: template textarea with tag buttons, send button

Config panel: modal/drawer opened by gear icon. Shows lifecycle templates with edit capability. Reuses the tag insertion pattern from MessagingPage.

### 6. Token status derivation (not stored)

Token status is computed, not stored as a separate field:
- `lifecycle_status == active` → "ativado"
- `onboarding_token IS NULL` → "sem token"
- `onboarding_token_expires_at < now()` → "expirado"
- else → "valido" (with days remaining)

No new column needed. Frontend displays computed status from the API response.

## Risks / Trade-offs

**[Token regeneration during send is not atomic with message delivery]** → If message fails after token regeneration, student has a new token they don't know about. Mitigation: the old token was either null or expired anyway, so no regression. Admin can resend.

**[Lifecycle template cache]** → Every lifecycle transition hits DB for template. At current scale (tens of events/day) this is negligible. If scale increases, add in-memory cache with short TTL.

**[No rate limiting on manual sends from dashboard]** → Admin could spam students. Mitigation: the Evolution API throttle in the Celery task (10-30s between messages) prevents actual spam. UI shows confirmation with recipient count.
