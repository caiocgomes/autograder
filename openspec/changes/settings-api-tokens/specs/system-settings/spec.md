## ADDED Requirements

### Requirement: System settings persistence
The system SHALL store LLM API tokens (OpenAI and Anthropic) in a database table `system_settings` as encrypted values. The table SHALL contain at most one row. Encryption SHALL use Fernet symmetric encryption with a key derived from the application's JWT secret.

#### Scenario: First-time token configuration
- **WHEN** no `system_settings` row exists in the database
- **THEN** the system SHALL use tokens from environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) as fallback

#### Scenario: Token stored in database takes precedence
- **WHEN** a `system_settings` row exists with a non-empty encrypted token
- **THEN** the system SHALL decrypt and use the database token instead of the environment variable

#### Scenario: Partial configuration
- **WHEN** only one token (e.g., Anthropic) is configured in the database and the other is empty
- **THEN** the system SHALL use the database token for the configured one and fall back to the environment variable for the other

### Requirement: Admin API for settings management
The system SHALL expose endpoints under `/admin/settings` restricted to users with the `admin` role.

#### Scenario: Read current settings
- **WHEN** an admin sends `GET /admin/settings`
- **THEN** the system SHALL return a JSON object with masked token values (first 10 characters + `****`) and boolean flags indicating whether each token is configured

#### Scenario: Read settings when none configured
- **WHEN** an admin sends `GET /admin/settings` and no database row exists
- **THEN** the system SHALL return empty masked values and `false` for configuration flags

#### Scenario: Update settings
- **WHEN** an admin sends `PUT /admin/settings` with `{ "openai_api_key": "sk-...", "anthropic_api_key": "sk-ant-..." }`
- **THEN** the system SHALL encrypt and store both tokens, creating the row if it doesn't exist or updating if it does

#### Scenario: Partial update
- **WHEN** an admin sends `PUT /admin/settings` with only one token field (e.g., `{ "openai_api_key": "sk-..." }`)
- **THEN** the system SHALL update only the provided token, leaving the other unchanged

#### Scenario: Clear a token
- **WHEN** an admin sends `PUT /admin/settings` with an empty string for a token (e.g., `{ "openai_api_key": "" }`)
- **THEN** the system SHALL clear that token from the database, causing the system to fall back to the environment variable

#### Scenario: Non-admin access denied
- **WHEN** a non-admin user sends any request to `/admin/settings`
- **THEN** the system SHALL return HTTP 403

### Requirement: Token masking in API responses
The system SHALL never return full API tokens in any API response. Tokens SHALL be masked showing at most the first 10 characters followed by `****`.

#### Scenario: Short token masking
- **WHEN** a stored token has fewer than 10 characters
- **THEN** the system SHALL mask the entire token as `****`

#### Scenario: Normal token masking
- **WHEN** a stored token is `sk-proj-abc123456789xyz`
- **THEN** the masked value SHALL be `sk-proj-ab****`

### Requirement: Settings UI in frontend
The system SHALL provide a settings page at `/professor/settings`, visible only to admin users via the sidebar navigation.

#### Scenario: Admin views settings page
- **WHEN** an admin navigates to `/professor/settings`
- **THEN** the page SHALL display two text input fields labeled "OpenAI API Key" and "Anthropic API Key", each showing the masked current value as placeholder, and a save button

#### Scenario: Admin saves new tokens
- **WHEN** an admin enters new token values and clicks save
- **THEN** the system SHALL send a `PUT /admin/settings` request and display a success confirmation

#### Scenario: Non-admin cannot see settings
- **WHEN** a professor (non-admin) views the sidebar
- **THEN** the "Configuracoes" nav item SHALL NOT appear

### Requirement: LLM token resolution
Code that calls LLM APIs (message rewriter, exercise grading) SHALL resolve API tokens through a centralized function that checks the database first and falls back to environment variables.

#### Scenario: Message rewriter uses database token
- **WHEN** `generate_variations()` is called and an Anthropic token exists in `system_settings`
- **THEN** the Anthropic client SHALL be initialized with the database token

#### Scenario: Exercise grading uses database token
- **WHEN** a grading task runs and an OpenAI/Anthropic token exists in `system_settings`
- **THEN** the LLM client SHALL be initialized with the database token for the configured provider

#### Scenario: No token available anywhere
- **WHEN** no token exists in the database or environment variables for the required provider
- **THEN** the system SHALL raise an error with a clear message indicating the missing configuration
