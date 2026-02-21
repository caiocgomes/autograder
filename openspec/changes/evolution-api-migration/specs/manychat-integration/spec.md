## REMOVED Requirements

### Requirement: ManyChat state management
**Reason**: ManyChat removed. State lives entirely in `student_course_status` (SCD Type 2). Segmentation is done by querying the local DB, not by external tag state.
**Migration**: No external tag management. `AccessRuleType.MANYCHAT_TAG` removed from `ProductAccessRule`. Existing `MANYCHAT_TAG` rules in DB must be deleted before migration.

### Requirement: Transactional flow triggers
**Reason**: Replaced by direct WhatsApp message sending via Evolution API. Flows had no interactive logic — were single message dispatches.
**Migration**: Each `trigger_flow` call in lifecycle side-effects is replaced by `evolution.send_message(phone, text)`.

### Requirement: Broadcast notifications
**Reason**: Broadcast use case (new assignment, deadline reminder) is out of scope for this migration. When needed, implementation queries `student_course_status` for the target segment and calls Evolution API per recipient.
**Migration**: `manychat_new_assignment_flow_id` and `manychat_deadline_reminder_flow_id` config removed. Features not replaced in this change.

### Requirement: ManyChat subscriber resolution
**Reason**: Evolution API addresses recipients by phone number directly. No subscriber ID needed.
**Migration**: Remove `User.manychat_subscriber_id` column via Alembic migration.

### Requirement: ManyChat configuration
**Reason**: All ManyChat settings removed.
**Migration**: Remove from `.env`: `MANYCHAT_API_TOKEN`, `MANYCHAT_ENABLED`, and all `MANYCHAT_*_FLOW_ID` variables. Replace with Evolution API settings (see `evolution-api` spec).
