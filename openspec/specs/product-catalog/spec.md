## ADDED Requirements

### Requirement: Define products
The system SHALL allow admins to register products that map to Hotmart product IDs.

#### Scenario: Create product
- **WHEN** admin submits product name and hotmart_product_id
- **THEN** system creates product record and returns product ID

#### Scenario: Duplicate hotmart_product_id
- **WHEN** admin submits hotmart_product_id that already exists
- **THEN** system returns error "Product already registered for this Hotmart ID"

#### Scenario: List products
- **WHEN** admin requests product list
- **THEN** system returns all products with their access rules and active student counts

### Requirement: Configure access rules per product
The system SHALL allow admins to define what resources each product grants.

#### Scenario: Map product to Discord role
- **WHEN** admin associates product with a Discord role ID
- **THEN** system stores mapping; students who purchase this product receive this role

#### Scenario: Map product to classes
- **WHEN** admin associates product with one or more class IDs
- **THEN** system stores mapping; students who purchase this product are auto-enrolled in these classes

#### Scenario: Map product to ManyChat tag
- **WHEN** admin associates product with a ManyChat tag name
- **THEN** system stores mapping; students who purchase this product are tagged in ManyChat

#### Scenario: Multiple access rules
- **WHEN** admin configures product with Discord role + classes + ManyChat tag
- **THEN** system stores all rules; all are applied on enrollment, all revoked on churn

### Requirement: Update access rules
The system SHALL allow admins to modify product access rules.

#### Scenario: Add new class to product
- **WHEN** admin adds class to existing product's access rules
- **THEN** system stores new rule; existing active students are NOT retroactively enrolled (manual action required)

#### Scenario: Remove Discord role from product
- **WHEN** admin removes Discord role mapping from product
- **THEN** system removes rule; existing students keep role until next lifecycle transition

### Requirement: Product access rule entities
The system SHALL store access rules as typed records.

#### Data model: Product
- `id`: integer, primary key
- `name`: string, display name
- `hotmart_product_id`: string, unique, Hotmart's product identifier
- `is_active`: boolean, default true
- `created_at`: timestamp

#### Data model: ProductAccessRule
- `id`: integer, primary key
- `product_id`: FK to Product
- `rule_type`: enum (discord_role, class_enrollment, manychat_tag)
- `rule_value`: string (Discord role ID, class ID, or ManyChat tag name)
- `created_at`: timestamp
## Requirements
### Requirement: Define products
The system SHALL allow admins to register products that map to Hotmart product IDs.

#### Scenario: Create product
- **WHEN** admin submits product name and hotmart_product_id
- **THEN** system creates product record and returns product ID

#### Scenario: Duplicate hotmart_product_id
- **WHEN** admin submits hotmart_product_id that already exists
- **THEN** system returns error "Product already registered for this Hotmart ID"

#### Scenario: List products
- **WHEN** admin requests product list
- **THEN** system returns all products with their access rules and active student counts

### Requirement: Configure access rules per product
The system SHALL allow admins to define what resources each product grants.

#### Scenario: Map product to Discord role
- **WHEN** admin associates product with a Discord role ID
- **THEN** system stores mapping; students who purchase this product receive this role

#### Scenario: Map product to classes
- **WHEN** admin associates product with one or more class IDs
- **THEN** system stores mapping; students who purchase this product are auto-enrolled in these classes

#### Scenario: Map product to ManyChat tag
- **WHEN** admin associates product with a ManyChat tag name
- **THEN** system stores mapping; students who purchase this product are tagged in ManyChat

#### Scenario: Multiple access rules
- **WHEN** admin configures product with Discord role + classes + ManyChat tag
- **THEN** system stores all rules; all are applied on enrollment, all revoked on churn

### Requirement: Update access rules
The system SHALL allow admins to modify product access rules.

#### Scenario: Add new class to product
- **WHEN** admin adds class to existing product's access rules
- **THEN** system stores new rule; existing active students are NOT retroactively enrolled (manual action required)

#### Scenario: Remove Discord role from product
- **WHEN** admin removes Discord role mapping from product
- **THEN** system removes rule; existing students keep role until next lifecycle transition

### Requirement: Product access rule entities
The system SHALL store access rules as typed records.

#### Data model: Product
- `id`: integer, primary key
- `name`: string, display name
- `hotmart_product_id`: string, unique, Hotmart's product identifier
- `is_active`: boolean, default true
- `created_at`: timestamp

#### Data model: ProductAccessRule
- `id`: integer, primary key
- `product_id`: FK to Product
- `rule_type`: enum (discord_role, class_enrollment, manychat_tag)
- `rule_value`: string (Discord role ID, class ID, or ManyChat tag name)
- `created_at`: timestamp

