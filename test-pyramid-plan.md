# Plan: Reestruturar a Pirâmide de Testes

**Generated**: 2026-03-10

## Overview
Objetivo: reorganizar a suíte em três níveis claros para este repositório FastAPI/SQLAlchemy:
1. testes unitários rápidos para utilitários e serviços com mocks;
2. testes de integração de banco para repositórios e fluxos persistentes;
3. poucos testes de API cobrindo contrato HTTP e wiring.

Assumimos que o escopo inclui reorganização da suíte existente, criação de fixtures compartilhadas e aumento de cobertura nas áreas críticas identificadas: `BuscaService`, repositórios, `AIService`, `cache` e `filtros`.

## Prerequisites
- `uv` e `.venv` configurados
- `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`
- Fixtures assíncronas com `AsyncSession`
- Documentação oficial consultada:
  - Pytest markers/customização: `docs.pytest.org`
  - FastAPI async tests e `dependency_overrides`: `fastapi.tiangolo.com`
  - SQLAlchemy asyncio + `aiosqlite`/`StaticPool`: `docs.sqlalchemy.org`

## Dependency Graph

```text
T0 ──┬── T2 ──┬── T6a ──┐
     │        ├── T6b ──┤
T1 ──┼── T3 ──┼── T8  ──┼── T9 ── T10
     ├── T4 ──┤        │
     ├── T5 ──┘        │
     └── T7 ───────────┘
```

## Tasks

### T0: Definir estratégia de banco para integração
- **depends_on**: []
- **location**: `app/models/consulta.py`, `app/repositories/decisao_repo.py`, `tests/conftest.py`
- **description**: Escolher e documentar o backend dos testes de integração, considerando dois bloqueios já visíveis: `Consulta.filtros` usa `JSONB` e não sobe em SQLite in-memory, e `DecisaoRepository.count_by_periodo()` usa `to_char`, o que não é portátil. Decidir entre adaptar modelo/query para compatibilidade, usar backend Postgres dedicado/testcontainer, ou separar escopo de integração por backend.
- **validation**: decisão registrada e reproduzível; comando de smoke do backend escolhido sobe schema e executa pelo menos um repositório alvo.
- **status**: Completed
- **log**: Estratégia definida em `docs/testing-backend-strategy.md`: manter SQLite in-memory como backend padrão de integração, após remover os acoplamentos a PostgreSQL em `Consulta.filtros` e `count_by_periodo()`. Postgres fica reservado para suíte opcional específica se surgir necessidade real de comportamento exclusivo.
- **files edited/created**: `docs/testing-backend-strategy.md`, `test-pyramid-plan.md`

### T1: Definir taxonomia e convenções da suíte
- **depends_on**: []
- **location**: `pyproject.toml`, `tests/`
- **description**: Registrar markers (`unit`, `integration`, `api`), padronizar naming, decidir layout final da suíte e ajustar comandos-alvo (`uv run pytest -m unit`, etc.). Incluir `--strict-markers` e planejar a migração explícita dos testes já existentes para a nova taxonomia.
- **validation**: `uv run pytest --collect-only` sem warnings de markers desconhecidos e com mapeamento documentado dos testes atuais.
- **status**: Completed
- **log**: `unit`, `integration` e `api` foram registrados em `pyproject.toml` com `--strict-markers`. A suíte atual foi classificada por módulo e o mapeamento documentado em `docs/testing-taxonomy.md`.
- **files edited/created**: `pyproject.toml`, `tests/test_main.py`, `tests/test_api/test_busca.py`, `tests/test_services/test_tjdft_client.py`, `tests/test_services/test_estatisticas_service.py`, `tests/test_utils/test_enrichment.py`, `docs/testing-taxonomy.md`, `test-pyramid-plan.md`

### T2: Criar infraestrutura compartilhada de fixtures
- **depends_on**: [T0]
- **location**: `tests/conftest.py`, `app/database.py`
- **description**: Separar fixtures por nível, implementar a estratégia de banco escolhida em `T0`, manter rollback/isolamento por teste e adicionar helpers para override de `get_session`, `AsyncClient`/`ASGITransport` e limpeza de `app.dependency_overrides` no FastAPI.
- **validation**: fixtures de sessão e cliente HTTP sobem/descem sem vazamento; smoke tests com override e cleanup passam.
- **status**: Completed
- **log**: `tests/conftest.py` agora fornece `db_engine`, `db_session_maker`, `db_session` e `api_client`, com cleanup automático de `app.dependency_overrides`. O schema de `Consulta.filtros` foi tornado portátil para permitir `Base.metadata.create_all()` em SQLite. Validado com smoke do metadata completo e testes HTTP/integração.
- **files edited/created**: `app/models/consulta.py`, `tests/conftest.py`, `tests/test_api/test_test_infra.py`, `test-pyramid-plan.md`

### T3: Cobrir utilitários com testes unitários
- **depends_on**: [T1]
- **location**: `tests/test_utils/`, `app/utils/cache.py`, `app/utils/filtros.py`, `app/utils/enrichment.py`
- **description**: Adicionar testes rápidos para `CacheManager` (memória, Redis mockado, falhas), `filtros.py` (carga de referência, cache interno, arquivo inválido, validadores e filtros funcionais) e completar ramos faltantes de `enrichment.py`. Se útil para paralelizar, quebrar a execução em blocos `cache`, `filtros` e `enrichment`.
- **validation**: `uv run pytest -m unit tests/test_utils -q` passa com cobertura relevante nesses módulos.
- **status**: Completed
- **log**: Foram adicionados testes unitários para `CacheManager`, `filtros.py` e os ramos faltantes de `extrair_marcadores_relevancia`. Também foi corrigido o backend em memória do `CacheManager` para desserializar valores na leitura, alinhando a implementação com a API pública documentada.
- **files edited/created**: `app/utils/cache.py`, `tests/test_utils/test_cache.py`, `tests/test_utils/test_filtros.py`, `tests/test_utils/test_enrichment.py`, `test-pyramid-plan.md`

### T4: Cobrir AIService com mocks determinísticos
- **depends_on**: [T1]
- **location**: `tests/test_services/test_ai_service.py`, `app/services/ai_service.py`
- **description**: Criar testes unitários para `initialize`, `_build_prompt`, `_generate_cache_key`, `_call_llm`, cache hit, JSON inválido, indisponibilidade do serviço, exceções da OpenAI e `close()`, sem chamadas externas reais.
- **validation**: `uv run pytest -m unit tests/test_services/test_ai_service.py -q`.
- **status**: Completed
- **log**: Foi criada uma suíte dedicada para `AIService` cobrindo inicialização, fallback sem pacote/chave, parsing JSON, cache hit, erros do cliente, geração de chave, formatação de prompt e fechamento do cliente. A cobertura do módulo subiu para 80%.
- **files edited/created**: `tests/test_services/test_ai_service.py`, `test-pyramid-plan.md`

### T5: Cobrir BuscaService com mocks e foco em orquestração
- **depends_on**: [T1]
- **location**: `tests/test_services/test_busca_service.py`, `app/services/busca_service.py`
- **description**: Testar `buscar`, `buscar_com_filtro_avancado`, `recuperar_busca`, `buscar_todas_paginas`, `buscar_similares`, `historico_consultas`, `_validar_filtros`, `_prepare_api_params`, `_paginar_resultados` e `_salvar_decisoes_cache`, mockando cliente TJDFT e repositórios quando apropriado. Começar com um teste de regressão para o contrato `TJDFTClient -> BuscaService` (`registros` vs `dados`) antes de expandir a matriz de cenários.
- **validation**: `uv run pytest -m unit tests/test_services/test_busca_service.py -q`.
- **status**: Completed
- **log**: Foi criado um conjunto de testes unitários cobrindo os caminhos públicos e helpers do `BuscaService`, incluindo regressão explícita para o mismatch `registros` vs `dados`, filtros inválidos, busca multipágina, similares, histórico, paginação e persistência em cache. Em seguida, o serviço foi corrigido para aceitar tanto `dados` quanto `registros`. A cobertura do módulo subiu para 92%.
- **files edited/created**: `tests/test_services/test_busca_service.py`, `test-pyramid-plan.md`

### T6a: Criar testes de integração portáveis para repositórios
- **depends_on**: [T0, T2]
- **location**: `tests/test_repositories/test_consulta_repo.py`, `tests/test_repositories/test_decisao_repo.py`
- **description**: Exercitar caminhos portáveis de `create`, `get_by_id`, `list`, `count`, `delete`, `create_or_update` e buscas filtradas. Validar ordenação, paginação e caminhos de “não encontrado” no backend definido em `T0`.
- **validation**: `uv run pytest -m integration tests/test_repositories -q` cobrindo CRUD/filtros básicos.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T6b: Cobrir agregações dialeto-específicas dos repositórios
- **depends_on**: [T0, T2]
- **location**: `tests/test_repositories/test_decisao_repo.py`, `app/repositories/decisao_repo.py`
- **description**: Cobrir explicitamente agregações que dependem do dialeto, como `count_by_periodo()`, no backend compatível definido em `T0`. Se necessário, separar marker/backend desses testes para não contaminar o fluxo rápido.
- **validation**: teste dedicado para `count_by_periodo()` verde no backend esperado.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T7: Introduzir seam testável para endpoint de busca
- **depends_on**: [T1]
- **location**: `app/api/v1/endpoints/busca.py`
- **description**: Definir como os testes de API vão injetar `BuscaService` e `CacheManager`: providers/factories explícitos ou monkeypatch controlado. O objetivo é remover improviso em `T9` e deixar a camada HTTP testável sem acoplamento escondido.
- **validation**: existe uma seam documentada e exercitável por teste para substituir sessão, serviço e cache.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T8: Reclassificar e adaptar a suíte existente
- **depends_on**: [T1]
- **location**: `tests/test_main.py`, `tests/test_api/test_busca.py`, `tests/test_services/test_tjdft_client.py`, `tests/test_services/test_estatisticas_service.py`
- **description**: Aplicar markers aos testes atuais, mover o que for apenas estrutural para o nível correto e adaptar nomes/fixtures para que a suíte antiga já respeite a nova pirâmide antes da consolidação final.
- **validation**: todos os testes existentes entram em exatamente uma categoria (`unit`, `integration` ou `api`).
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T9: Adicionar poucos testes de API orientados a contrato
- **depends_on**: [T2, T7]
- **location**: `tests/test_api/test_busca_end_to_end.py`, `app/api/v1/endpoints/busca.py`
- **description**: Substituir testes apenas estruturais por 3-5 cenários de alto valor para `POST /api/v1/busca/`: sucesso, override de query params, erro de filtro inválido, resposta enriquecida e persistência via seam/override definida em `T2` e `T7`.
- **validation**: `uv run pytest -m api tests/test_api -q`.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T10: Ajustar cobertura, seleção por nível e comandos de execução
- **depends_on**: [T3, T4, T5, T6a, T6b, T8, T9]
- **location**: `pyproject.toml`, `README.md`, `AGENTS.md`
- **description**: Consolidar comandos por nível, revisar `addopts`, considerar threshold gradual por módulo ou global e documentar quando usar `unit`, `integration` e `api`.
- **validation**: `uv run pytest --collect-only` da suíte inteira bate com a soma das seleções por marker; comandos documentados executam sem ambiguidade.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T11: Rodada final de validação e estabilização
- **depends_on**: [T10]
- **location**: `tests/`, `pyproject.toml`
- **description**: Executar suíte completa, corrigir flakes, revisar tempo total e garantir que o desenho final reflita a pirâmide proposta sem redundância excessiva entre camadas.
- **validation**: `uv run pytest --cov=app --cov-report=term-missing` verde; tempo e markers reportados no resumo final.
- **status**: Not Completed
- **log**:
- **files edited/created**:

## Parallel Execution Groups

| Wave | Tasks | Can Start When |
|------|-------|----------------|
| 1 | T0, T1 | Imediatamente |
| 2 | T2, T3, T4, T5, T7, T8 | Após T0/T1 conforme dependência |
| 3 | T6a, T6b, T9 | Após infraestrutura e seams prontas |
| 4 | T10 | T3, T4, T5, T6a, T6b, T8, T9 completos |
| 5 | T11 | T10 completo |

## Testing Strategy
- `unit`: sem banco real e sem rede; mocks para OpenAI, TJDFT e Redis.
- `integration`: backend definido em `T0`, com rollback por teste e separação entre cenários portáveis e dialeto-específicos.
- `api`: poucos testes de contrato HTTP usando overrides de dependência do FastAPI e seam explícita para serviço/cache.
- Manter foco em risco: cobertura prioritária para `BuscaService`, repositórios, `AIService`, `cache` e `filtros`.

## Risks & Mitigations
- Fixture atual cria só `Decisao`, bloqueando testes de `ConsultaRepository`.
  Mitigação: `T0` define backend/compatibilidade; `T2` implementa fixtures adequadas.
- Duplicação entre testes unitários e de API pode inflar manutenção.
  Mitigação: limitar API a contrato e deixar lógica detalhada nos unitários/integration.
- Integrações opcionais (`OpenAI`, Redis) podem gerar flaky tests.
  Mitigação: mocks determinísticos e cobertura explícita de fallback.
- Há um mismatch real entre `TJDFTClient` e `BuscaService` (`registros` vs `dados`).
  Mitigação: teste de regressão no início de `T5`, antes da expansão dos demais cenários.
- Threshold global de cobertura pode falhar cedo demais.
  Mitigação: aplicar gate gradual após T3-T7 e revisar números reais antes de travar meta.
