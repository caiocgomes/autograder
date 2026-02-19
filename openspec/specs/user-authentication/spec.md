## ADDED Requirements

### Requirement: User registration
The system SHALL allow new users to register with email and password.

#### Scenario: Successful registration
- **WHEN** user submits valid email and password (min 8 characters)
- **THEN** system creates account, sends confirmation email, and returns success

#### Scenario: Duplicate email
- **WHEN** user attempts to register with existing email
- **THEN** system returns error "Email already registered"

#### Scenario: Weak password
- **WHEN** user submits password shorter than 8 characters
- **THEN** system returns error "Password must be at least 8 characters"

### Requirement: User login
The system SHALL authenticate users with email and password.

#### Scenario: Successful login
- **WHEN** user submits correct email and password
- **THEN** system returns JWT access token (15 min expiry) and refresh token (7 days expiry)

#### Scenario: Invalid credentials
- **WHEN** user submits incorrect email or password
- **THEN** system returns error "Invalid credentials" without revealing which field is wrong

#### Scenario: Rate limiting
- **WHEN** user attempts more than 5 failed logins within 15 minutes
- **THEN** system blocks further login attempts for 15 minutes and returns error "Too many attempts"

### Requirement: Password security
The system SHALL hash passwords with bcrypt before storage.

#### Scenario: Password storage
- **WHEN** user registers or changes password
- **THEN** system stores bcrypt hash (cost factor 12), never plaintext

### Requirement: Token refresh
The system SHALL allow users to refresh expired access tokens using valid refresh tokens.

#### Scenario: Valid refresh token
- **WHEN** user submits valid refresh token
- **THEN** system issues new access token and optionally rotates refresh token

#### Scenario: Expired refresh token
- **WHEN** user submits expired refresh token
- **THEN** system returns error "Token expired, please login again"

### Requirement: Password reset
The system SHALL allow users to reset forgotten passwords via email.

#### Scenario: Request password reset
- **WHEN** user submits email for password reset
- **THEN** system sends reset link with token (valid 1 hour) to email

#### Scenario: Complete password reset
- **WHEN** user clicks reset link and submits new password
- **THEN** system updates password and invalidates reset token

#### Scenario: Expired reset token
- **WHEN** user attempts reset with expired token
- **THEN** system returns error "Reset link expired"

### Requirement: Role-based access control
The system SHALL enforce role-based permissions (Admin, Professor, Student, TA).

#### Scenario: Admin permissions
- **WHEN** admin user accesses admin-only endpoint
- **THEN** system allows access

#### Scenario: Student blocked from professor endpoint
- **WHEN** student user attempts to access professor-only endpoint (create exercise)
- **THEN** system returns 403 Forbidden

#### Scenario: TA permissions
- **WHEN** TA user attempts to view submissions
- **THEN** system allows read access but blocks create/delete operations

### Requirement: User profile management
The system SHALL allow users to view and update their profile information.

#### Scenario: View profile
- **WHEN** authenticated user requests /users/me
- **THEN** system returns user data (id, email, role, created_at) excluding password hash

#### Scenario: Update email
- **WHEN** user updates email to new unique address
- **THEN** system sends confirmation to new email and updates after verification

#### Scenario: Update password
- **WHEN** user submits current password and new password
- **THEN** system verifies current password, hashes new password, and updates

## ADDED Requirements (orchestrator integration)

### Requirement: Extended user model for integrations
The User model SHALL include fields for external service linking.

#### Data model additions
- `hotmart_id`: string, nullable, unique — Hotmart buyer identifier (email)
- `discord_id`: string, nullable, unique — Discord user snowflake ID
- `whatsapp_number`: string, nullable — E.164 format phone number
- `lifecycle_status`: enum (pending_payment, pending_onboarding, active, churned), nullable — null for manually-created users (professors, admins)
- `onboarding_token`: string, nullable, unique — token for Discord registration
- `onboarding_token_expires_at`: timestamp, nullable
- `manychat_subscriber_id`: string, nullable — cached ManyChat subscriber ID

### Requirement: Automated account creation via webhook
The system SHALL create user accounts automatically when Hotmart purchase is confirmed.

#### Scenario: Auto-create student on purchase
- **WHEN** Hotmart webhook triggers student creation
- **THEN** system creates User with role=student, hotmart_id set, lifecycle_status=pending_onboarding, and generates onboarding_token
- **AND** password is set to a random value (student resets via email or never uses web login if Discord-only)

#### Scenario: Existing user re-purchases
- **WHEN** Hotmart webhook arrives for email that already exists in system
- **THEN** system updates lifecycle_status and triggers reactivation (does not create duplicate)
