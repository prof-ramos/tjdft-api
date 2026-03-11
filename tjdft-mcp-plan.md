# Plan: TJDFT MCP (camada do projeto) com implementação e testes

**Generated**: 2026-03-11
**Status**: IMPLEMENTED (see app/mcp/)

## Overview
Implementar um servidor MCP em Python/FastMCP que expõe ferramentas orientadas a workflow usando a camada de código do projeto (serviços/adapters), não a API bruta do TJDFT. O plano corrige os riscos de concorrência de edição, define semântica de paginação/filtros e separa trilha core da trilha opcional de IA.

Objetivos:
- Tools MCP úteis para agentes (`search`, `metadata`, `history`, `consulta`, `similar`).
- Contrato estável e compacto (`markdown` + `json`, paginação, truncamento, erros acionáveis).
- Execução via `stdio` com testes unitários e integração determinísticos.
- Pacote de avaliação com 10 perguntas read-only e estáveis.

## Prerequisites
- Ambiente local com `uv` e `.venv` ativo.
- Projeto com Python 3.11+.
- Dependência MCP SDK Python adicionada ao projeto.
- Política de side effects definida para tools core:
  - padrão recomendado: tools de busca no MCP devem ser efetivamente read-only (sem persistência em banco/histórico).

## Dependency Graph

```text
T1 ──┬─────────────┐
     │             ├── T4 ──┬── T6 ──┬── T8 ──┬── T9 ──┬── T11 ──┐
T2 ──┴── T3 ───────┘        │        │        │        └── T14 ──┼── T16
                            │        │        └── T10 ────────────┤
                            │        └── T7 ──────────────────────┘
                            └── T5 ──┬── T12 ── T13 ──────────────┘
                                     └── T15 ──────────────────────┘
```

## Tasks

### T1: Fechar contrato funcional MCP (sem ambiguidades)
- **depends_on**: []
- **location**: `docs/mcp/contract.md`, `docs/mcp/tool_catalog.md`
- **description**: Definir contrato de I/O das tools e decisões de semântica:
  - paginação única no MCP (`page` 1-indexed para humanos; adapter converte internamente).
  - filtros oficialmente suportados (sem campos quebrados como `data_inicio/data_fim` enquanto não suportados).
  - política para `query` vazia.
  - comportamento de erro e resultados vazios.
  - decisão explícita de side effects: tools core de busca do MCP devem evitar persistência para manter `readOnlyHint=true`.
- **validation**: checklist de consistência contra `app/services/tjdft_client.py`, `app/services/busca_service.py` e `app/schemas/consulta.py`.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T2: Bootstrap técnico MCP (dependências + estrutura)
- **depends_on**: []
- **location**: `pyproject.toml`, `app/mcp/__init__.py`, `app/mcp/server.py`, `app/mcp/__main__.py`
- **description**: Adicionar dependência do SDK MCP e criar estrutura mínima do servidor FastMCP com entrypoint.
- **validation**:
  - `uv pip install -e ".[dev]"`
  - `uv run python -c "from app.mcp.server import mcp; print(bool(mcp))"`
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T3: Reconciliação de configuração e ambiente
- **depends_on**: [T2]
- **location**: `.env.example`, `app/config.py`, `docs/mcp/configuration.md`
- **description**: Alinhar variáveis documentadas com `Settings` real (sem drift silencioso), definir flags MCP (`MCP_CHARACTER_LIMIT`, `MCP_ENABLE_AI_TOOLS`, timeouts), e documentar defaults.
- **validation**:
  - teste automatizado de consistência entre chaves de `.env.example` e `Settings`.
  - `uv run python -c "from app.config import Settings; s=Settings(); print(s.app_name)"`
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T4: Runtime MCP explícito e seguro
- **depends_on**: [T1, T2, T3]
- **location**: `app/mcp/runtime.py`, `app/mcp/errors.py`
- **description**: Criar `MCPRuntime` com ciclo de vida claro:
  - factories para `TJDFTClient`, `BuscaService`/adapters read-only, `AIService`.
  - init/teardown (`AIService.initialize()/close()`, sessão DB com rollback/close).
  - cache instanciado por `Settings` (evitar dependência do cache global implícito).
- **validation**:
  - `uv run python -m py_compile app/mcp/runtime.py`
  - testes unitários de lifecycle e mapeamento de erro.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T5: Schemas MCP, formatação e limites de resposta
- **depends_on**: [T1, T2]
- **location**: `app/mcp/schemas.py`, `app/mcp/formatters.py`, `app/mcp/constants.py`
- **description**: Implementar modelos Pydantic v2 e utilitários compartilhados:
  - `response_format` (`markdown`/`json`)
  - paginação consistente
  - truncamento com mensagem acionável
  - envelope de resposta padronizado para tools de listagem
- **validation**:
  - `uv run python -m py_compile app/mcp/schemas.py app/mcp/formatters.py`
  - testes unitários de schema/formatter/truncamento.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T6: Implementar tools core de busca e metadados (módulo isolado)
- **depends_on**: [T4, T5]
- **location**: `app/mcp/tools/search_tools.py`
- **description**: Implementar `register_search_tools(mcp, runtime)` com:
  - `tjdft_search_decisions`
  - `tjdft_get_metadata`
  - `tjdft_search_all_pages` (com limites seguros)
  - anotações MCP corretas para read-only.
- **validation**:
  - `uv run python -m py_compile app/mcp/tools/search_tools.py`
  - testes unitários com mocks de runtime/client.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T7: Implementar tools core de histórico/consulta/similares (módulo isolado)
- **depends_on**: [T4, T5]
- **location**: `app/mcp/tools/history_tools.py`
- **description**: Implementar `register_history_tools(mcp, runtime)` com:
  - `tjdft_get_consulta`
  - `tjdft_list_history`
  - `tjdft_find_similar_decisions`
  - comportamento consistente para não encontrado/entrada inválida.
- **validation**:
  - `uv run python -m py_compile app/mcp/tools/history_tools.py`
  - testes unitários de casos de borda.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T8: Composição serializada do servidor core
- **depends_on**: [T6, T7]
- **location**: `app/mcp/server.py`, `app/mcp/__main__.py`
- **description**: Registrar módulos de tools no servidor em etapa única (evita colisão paralela):
  - `register_search_tools(...)`
  - `register_history_tools(...)`
  - sem IA nesta etapa.
- **validation**:
  - `uv run python -c "from app.mcp.server import mcp; print(mcp.name)"`
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T9: Harness e fixtures determinísticos para protocolo
- **depends_on**: [T8]
- **location**: `tests/test_mcp_integration/conftest.py`, `tests/fixtures/mcp/*.json`
- **description**: Criar base determinística para integração `stdio`:
  - fixtures estáveis de payload/resposta.
  - setup controlado para evitar variação de dados externos.
- **validation**:
  - `uv run pytest tests/test_mcp_integration -k fixture -v`
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T10: Testes unitários do core MCP
- **depends_on**: [T6, T7]
- **location**: `tests/test_mcp/test_schemas.py`, `tests/test_mcp/test_formatters.py`, `tests/test_mcp/test_search_tools.py`, `tests/test_mcp/test_history_tools.py`
- **description**: Cobrir contrato, validações, paginação, truncamento e mapeamento de erros do core.
- **validation**:
  - `uv run pytest tests/test_mcp -v`
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T11: Testes de integração `stdio` (core)
- **depends_on**: [T8, T9]
- **location**: `tests/test_mcp_integration/test_stdio_core.py`
- **description**: Validar handshake MCP, listagem de tools e chamadas reais das tools core em transporte `stdio`.
- **validation**:
  - `uv run pytest tests/test_mcp_integration/test_stdio_core.py -v`
  - execução com timeout no teste para evitar hang.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T12: Implementar trilha opcional de IA (módulo isolado)
- **depends_on**: [T4, T5]
- **location**: `app/mcp/tools/ai_tools.py`
- **description**: Implementar `register_ai_tools(mcp, runtime)` com fallback quando IA estiver desabilitada/não configurada:
  - `tjdft_ai_summarize`
  - `tjdft_ai_extract_theses`
  - `tjdft_ai_compare_decisions`
- **validation**:
  - `uv run python -m py_compile app/mcp/tools/ai_tools.py`
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T13: Testes da trilha opcional de IA
- **depends_on**: [T12, T9]
- **location**: `tests/test_mcp/test_ai_tools.py`, `tests/test_mcp_integration/test_stdio_ai.py`
- **description**: Cobrir cenários com IA habilitada e desabilitada, inclusive mensagens de degradação graciosa.
- **validation**:
  - `uv run pytest tests/test_mcp/test_ai_tools.py -v`
  - `uv run pytest tests/test_mcp_integration/test_stdio_ai.py -v`
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T14: Pacote de avaliação MCP (core)
- **depends_on**: [T8, T9]
- **location**: `evals/tjdft_mcp_evaluation.xml`, `docs/mcp/evaluation_notes.md`
- **description**: Criar 10 questões read-only, independentes e estáveis, com resposta verificável por string comparison.
- **validation**:
  - XML válido.
  - checklist de estabilidade e independência.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T15: Documentação e exemplo de configuração MCP (sem tocar `.mcp.json` local)
- **depends_on**: [T8, T11]
- **location**: `README.md`, `docs/mcp/quickstart.md`, `docs/mcp/example.mcp.json`
- **description**: Documentar execução via `uv`, uso das tools core e troubleshooting. Publicar arquivo de exemplo de configuração em `docs/mcp/example.mcp.json` em vez de editar a raiz `.mcp.json`.
- **validation**:
  - seguir quickstart do zero.
  - validar JSON do arquivo de exemplo.
- **status**: Not Completed
- **log**:
- **files edited/created**:

### T16: Quality gate final
- **depends_on**: [T10, T11, T14, T15]
- **location**: pipeline local / `Makefile` (opcional)
- **description**: Rodar validação final do core; se IA estiver habilitada no escopo, incluir T13 no gate.
- **validation**:
  - `uv run pytest`
  - `uv run black --check .`
  - `uv run isort --check-only .`
  - `uv run flake8 app tests`
  - `uv run mypy app`
- **status**: Not Completed
- **log**:
- **files edited/created**:

## Parallel Execution Groups

| Wave | Tasks | Can Start When |
|------|-------|----------------|
| 1 | T1, T2 | Immediately |
| 2 | T3, T5 | T2 complete |
| 3 | T4 | T1, T2, T3 complete |
| 4 | T6, T7 | T4, T5 complete |
| 5 | T8, T10 | T6, T7 complete |
| 6 | T9 | T8 complete |
| 7 | T11, T14, T15 | T8, T9 complete |
| 8 | T12 | T4, T5 complete (optional IA lane) |
| 9 | T13 | T12, T9 complete (optional IA lane) |
| 10 | T16 | T10, T11, T14, T15 complete (+T13 se IA habilitada) |

## Testing Strategy
- Unit tests (core): schemas, formatters, truncamento, adapters e tools isoladas.
- Integration tests (core): protocolo `stdio`, `list_tools`, `call_tool` com fixtures determinísticos.
- Optional lane (IA): testes separados para não bloquear o core.
- Gating: core MCP aprovado sem dependência de credenciais OpenAI.

## Risks & Mitigations
- Risco: colisão de arquivos em execução paralela.
  - Mitigação: composição final do servidor centralizada em T8.
- Risco: tools marcadas como read-only gerarem escrita local.
  - Mitigação: contrato T1 + adapter/read-only flow em T4/T6.
- Risco: inconsistência de paginação/filtros entre camadas.
  - Mitigação: normalização explícita no contrato e nos schemas MCP.
- Risco: flakiness em integração por dados externos.
  - Mitigação: harness e fixtures determinísticos antes dos testes de `stdio`.
- Risco: drift entre `.env.example` e `Settings`.
  - Mitigação: teste dedicado de consistência de configuração.
