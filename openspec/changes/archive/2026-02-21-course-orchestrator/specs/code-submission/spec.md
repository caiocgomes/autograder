## ADDED Requirements

### Requirement: Submit via Discord bot (planned, not in MVP)
The system SHALL support code submission via Discord slash command in a future iteration.

#### Scenario: Code paste submission
- **WHEN** student runs `/submit exercicio:3` and pastes code in Discord
- **THEN** bot extracts code, creates submission via internal API, and posts result in channel

#### Scenario: Repo-based submission (future design TBD)
- **WHEN** student runs `/submit repo:url exercicio:3`
- **THEN** bot clones repo, extracts relevant code (mechanism TBD), and submits
- **NOTE** Repo file resolution strategy not yet designed; needs separate spec work
