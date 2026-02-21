## ADDED Requirements

### Requirement: Discord bot as separate worker
The system SHALL run a Discord bot as an independent process (not inside FastAPI).

#### Scenario: Bot startup
- **WHEN** discord bot worker starts
- **THEN** bot connects to Discord gateway via WebSocket, registers slash commands, and logs "Bot ready"

#### Scenario: Bot crash recovery
- **WHEN** bot process crashes
- **THEN** docker-compose restarts it automatically (restart: unless-stopped)
- **AND** FastAPI and Celery workers continue operating independently

### Requirement: Role management
The system SHALL manage Discord roles based on student lifecycle transitions.

#### Scenario: Assign roles on activation
- **WHEN** lifecycle service calls discord.assign_roles(discord_id, role_ids)
- **THEN** bot adds specified roles to user in configured Discord server

#### Scenario: Revoke roles on churn
- **WHEN** lifecycle service calls discord.revoke_roles(discord_id, role_ids)
- **THEN** bot removes specified roles from user

#### Scenario: User not found in server
- **WHEN** discord_id is not a member of the configured server
- **THEN** system logs warning, marks side-effect as failed, alerts admin

### Requirement: Registration command
The system SHALL provide a /registrar slash command for students to link accounts.

#### Scenario: Valid registration
- **WHEN** user runs `/registrar codigo:ABC123` in #registro channel
- **THEN** bot validates token, links discord_id to student record, assigns product roles, responds "Registrado! Acesso liberado."
- **AND** lifecycle transitions from pending_onboarding to active

#### Scenario: Invalid token
- **WHEN** user runs `/registrar codigo:INVALID`
- **THEN** bot responds "Codigo invalido. Verifique o WhatsApp com as instrucoes." (ephemeral message, only visible to user)

#### Scenario: Expired token
- **WHEN** user runs `/registrar` with expired token
- **THEN** bot responds "Codigo expirado. Solicite um novo no WhatsApp."

#### Scenario: Already registered
- **WHEN** user runs `/registrar` but their discord_id is already linked
- **THEN** bot responds "Voce ja esta registrado!" (ephemeral)

#### Scenario: Command outside #registro
- **WHEN** user runs `/registrar` in any channel other than configured registration channel
- **THEN** bot responds "Use este comando no canal #registro" (ephemeral)

### Requirement: Welcome channel restriction
The system SHALL restrict unregistered users to only see the #registro channel.

#### Scenario: New member joins server
- **WHEN** user joins Discord server without any product roles
- **THEN** user can only see #registro channel (enforced by Discord role/permission setup)

#### Scenario: After registration
- **WHEN** user completes /registrar successfully
- **THEN** product roles grant visibility to product-specific channels

### Requirement: Notification messages
The system SHALL send notifications to Discord channels.

#### Scenario: New assignment notification
- **WHEN** professor publishes a new exercise list
- **THEN** system posts announcement in product's Discord channel with exercise list title, deadline, and link

#### Scenario: Grade published notification
- **WHEN** professor publishes grades for an exercise
- **THEN** system posts in product's Discord channel that grades are available (no individual scores in public channel)

### Requirement: Discord bot configuration
The system SHALL require the following environment variables.

#### Configuration
- `DISCORD_BOT_TOKEN`: string, bot authentication token
- `DISCORD_GUILD_ID`: string, server (guild) ID
- `DISCORD_REGISTRATION_CHANNEL_ID`: string, channel where /registrar works
- `DISCORD_ENABLED`: boolean, default false (feature flag)
## Requirements
### Requirement: Discord bot as separate worker
The system SHALL run a Discord bot as an independent process (not inside FastAPI).

#### Scenario: Bot startup
- **WHEN** discord bot worker starts
- **THEN** bot connects to Discord gateway via WebSocket, registers slash commands, and logs "Bot ready"

#### Scenario: Bot crash recovery
- **WHEN** bot process crashes
- **THEN** docker-compose restarts it automatically (restart: unless-stopped)
- **AND** FastAPI and Celery workers continue operating independently

### Requirement: Role management
The system SHALL manage Discord roles based on student lifecycle transitions.

#### Scenario: Assign roles on activation
- **WHEN** lifecycle service calls discord.assign_roles(discord_id, role_ids)
- **THEN** bot adds specified roles to user in configured Discord server

#### Scenario: Revoke roles on churn
- **WHEN** lifecycle service calls discord.revoke_roles(discord_id, role_ids)
- **THEN** bot removes specified roles from user

#### Scenario: User not found in server
- **WHEN** discord_id is not a member of the configured server
- **THEN** system logs warning, marks side-effect as failed, alerts admin

### Requirement: Registration command
The system SHALL provide a /registrar slash command for students to link accounts.

#### Scenario: Valid registration
- **WHEN** user runs `/registrar codigo:ABC123` in #registro channel
- **THEN** bot validates token, links discord_id to student record, assigns product roles, responds "Registrado! Acesso liberado."
- **AND** lifecycle transitions from pending_onboarding to active

#### Scenario: Invalid token
- **WHEN** user runs `/registrar codigo:INVALID`
- **THEN** bot responds "Codigo invalido. Verifique o WhatsApp com as instrucoes." (ephemeral message, only visible to user)

#### Scenario: Expired token
- **WHEN** user runs `/registrar` with expired token
- **THEN** bot responds "Codigo expirado. Solicite um novo no WhatsApp."

#### Scenario: Already registered
- **WHEN** user runs `/registrar` but their discord_id is already linked
- **THEN** bot responds "Voce ja esta registrado!" (ephemeral)

#### Scenario: Command outside #registro
- **WHEN** user runs `/registrar` in any channel other than configured registration channel
- **THEN** bot responds "Use este comando no canal #registro" (ephemeral)

### Requirement: Welcome channel restriction
The system SHALL restrict unregistered users to only see the #registro channel.

#### Scenario: New member joins server
- **WHEN** user joins Discord server without any product roles
- **THEN** user can only see #registro channel (enforced by Discord role/permission setup)

#### Scenario: After registration
- **WHEN** user completes /registrar successfully
- **THEN** product roles grant visibility to product-specific channels

### Requirement: Notification messages
The system SHALL send notifications to Discord channels.

#### Scenario: New assignment notification
- **WHEN** professor publishes a new exercise list
- **THEN** system posts announcement in product's Discord channel with exercise list title, deadline, and link

#### Scenario: Grade published notification
- **WHEN** professor publishes grades for an exercise
- **THEN** system posts in product's Discord channel that grades are available (no individual scores in public channel)

### Requirement: Discord bot configuration
The system SHALL require the following environment variables.

#### Configuration
- `DISCORD_BOT_TOKEN`: string, bot authentication token
- `DISCORD_GUILD_ID`: string, server (guild) ID
- `DISCORD_REGISTRATION_CHANNEL_ID`: string, channel where /registrar works
- `DISCORD_ENABLED`: boolean, default false (feature flag)

