## MODIFIED Requirements

### Requirement: Side-effects per transition
The system SHALL execute defined side-effects on each state transition.

#### Transition: → pending_onboarding
Side-effects:
1. Create student record in database
2. Generate onboarding token
3. Read message template from database (event_type: onboarding), fallback to hardcoded MSG_ONBOARDING
4. Resolve template variables (`{token}`, `{primeiro_nome}`, `{nome}`, `{product_name}`)
5. Send resolved message via Evolution API

#### Transition: → active
Side-effects:
1. Assign Discord roles (per product access rules)
2. Enroll in classes (per product access rules)
3. Read message template from database (event_type: welcome), fallback to hardcoded MSG_WELCOME
4. Resolve template variables (`{primeiro_nome}`, `{nome}`, `{product_name}`)
5. Send resolved message via Evolution API

#### Transition: → churned
Side-effects:
1. Revoke Discord roles
2. Unenroll from classes
3. Read message template from database (event_type: churn), fallback to hardcoded MSG_CHURN
4. Resolve template variables (`{primeiro_nome}`, `{nome}`, `{product_name}`)
5. Send resolved message via Evolution API

#### Transition: → active (reactivation from churned)
Side-effects:
1. Assign Discord roles
2. Enroll in classes
3. Read message template from database (event_type: welcome_back), fallback to hardcoded MSG_WELCOME_BACK
4. Resolve template variables (`{primeiro_nome}`, `{nome}`, `{product_name}`)
5. Send resolved message via Evolution API
