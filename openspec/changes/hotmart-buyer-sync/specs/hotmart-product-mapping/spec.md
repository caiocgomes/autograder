## ADDED Requirements

### Requirement: Tabela de/para entre produto Hotmart e produtos internos
O sistema SHALL manter uma tabela `hotmart_product_mapping` que associa um `source_hotmart_product_id` (string, ID do produto comprado na Hotmart) a um `target_product_id` (FK para `products.id`), permitindo que um produto Hotmart mapeie para múltiplos produtos internos.

#### Scenario: Um produto Hotmart mapeia para múltiplos produtos internos
- **WHEN** existem três linhas em `hotmart_product_mapping` com o mesmo `source_hotmart_product_id`
- **THEN** uma query de "quais cursos tem o aluno X" retorna os três produtos internos correspondentes

#### Scenario: Restrição de unicidade impede duplicata no de/para
- **WHEN** uma tentativa de inserir (source_hotmart_product_id, target_product_id) já existente ocorre
- **THEN** o banco rejeita a operação com violação de constraint UNIQUE

#### Scenario: Produto interno removido invalida a linha de mapping
- **WHEN** um `Product` interno é deletado do banco
- **THEN** a linha correspondente em `hotmart_product_mapping` é removida via ON DELETE CASCADE no FK `target_product_id`

### Requirement: Derivação de acesso a cursos por comprador
O sistema SHALL permitir consultar quais produtos internos um comprador tem acesso, combinando `hotmart_buyers` com `hotmart_product_mapping`.

#### Scenario: Query de cursos por email de comprador
- **WHEN** um comprador possui linhas em `hotmart_buyers` e existem entradas em `hotmart_product_mapping` para os produtos comprados
- **THEN** um JOIN entre as duas tabelas retorna os produtos internos que o comprador tem direito, com status de pagamento e flag de conta na plataforma (`user_id IS NOT NULL`)

#### Scenario: Comprador sem de/para configurado não aparece na query de cursos
- **WHEN** um comprador tem entrada em `hotmart_buyers` mas o `hotmart_product_id` comprado não tem entradas em `hotmart_product_mapping`
- **THEN** a query de cursos não retorna linhas para esse comprador (resultado correto: produto ainda não mapeado)
