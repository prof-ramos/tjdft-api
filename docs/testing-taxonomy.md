# Testing Taxonomy

## Markers
- `unit`: testes rápidos e isolados, sem banco real ou rede
- `integration`: testes com banco local ou múltiplas camadas locais
- `api`: testes de contrato HTTP e wiring da aplicação FastAPI

## Current Mapping
- `tests/test_utils/test_enrichment.py` -> `unit`
- `tests/test_services/test_tjdft_client.py` -> `unit`
- `tests/test_services/test_estatisticas_service.py` -> `integration`
- `tests/test_main.py` -> `api`
- `tests/test_api/test_busca.py` -> `api`

## Notes
- `tests/test_api/test_busca.py` ainda é um smoke test estrutural de rota; ele fica em `api` até ser substituído por cenários de contrato mais completos.
- Testes novos devem declarar seu nível no módulo inteiro com `pytestmark = pytest.mark.<marker>` sempre que possível.
- A coleta usa `--strict-markers`, então qualquer marker novo precisa ser registrado primeiro no `pyproject.toml`.

## Useful Commands
```bash
uv run pytest --collect-only
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m api
```
