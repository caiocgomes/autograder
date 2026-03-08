## MODIFIED Requirements

### Requirement: Discord bot process management
The Discord bot SHALL run as a systemd service (`autograder-discord.service`) instead of a Docker container. No functional changes to the bot logic.

#### Scenario: Bot runs as systemd service
- **WHEN** `systemctl start autograder-discord` is executed
- **THEN** the bot process starts and connects to Discord using the token from `/opt/autograder/.env`

#### Scenario: Bot restarts on crash
- **WHEN** the bot process crashes
- **THEN** systemd restarts it within 5 seconds
