## REMOVED Requirements

### Requirement: Onboarding dashboard frontend
**Reason**: Funcionalidade de envio absorvida pela seção unificada "Envios" (`unified-envios`). O dashboard de onboarding como página separada não é mais necessário.
**Migration**: Usar a página `/professor/envios` com filtro `lifecycle_status=pending_onboarding` para o mesmo fluxo de envio. Endpoints backend (`GET /onboarding/students`, `GET /onboarding/summary`) permanecem disponíveis para consulta programática.
