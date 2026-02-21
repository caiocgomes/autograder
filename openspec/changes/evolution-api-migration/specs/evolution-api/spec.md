## ADDED Requirements

### Requirement: WhatsApp message sending
The system SHALL send WhatsApp messages to students via Evolution API using the student's phone number directly (no subscriber resolution needed).

#### Scenario: Send transactional message
- **WHEN** lifecycle side-effect triggers a WhatsApp notification
- **THEN** system calls Evolution API `sendText` with the student's `whatsapp_number` (E.164 format) and message text
- **AND** returns True on HTTP 200, False on error

#### Scenario: Phone number missing
- **WHEN** system attempts to send message but `user.whatsapp_number` is None
- **THEN** system logs warning and skips the send — does not raise exception

#### Scenario: Evolution API unreachable
- **WHEN** Evolution API returns non-200 or connection error
- **THEN** system logs error with status code and response body, returns False
- **AND** caller (lifecycle side-effect machinery) handles retry and admin alert

### Requirement: Evolution API configuration
The system SHALL require the following environment variables.

#### Configuration
- `EVOLUTION_API_URL`: string, base URL of the Evolution API instance (e.g., `https://evo.example.com`)
- `EVOLUTION_API_KEY`: string, API key for authentication (`apikey` header)
- `EVOLUTION_INSTANCE`: string, instance name configured in Evolution API
- `EVOLUTION_ENABLED`: boolean, default false (feature flag)
