# Testing Backend Strategy

## Decision
Adotar **SQLite in-memory como backend padrão dos testes de integração**, mas somente após tornar os pontos hoje acoplados ao PostgreSQL compatíveis com múltiplos dialetos.

## Why
- O projeto já usa `sqlite+aiosqlite` nos testes atuais, então manter esse backend preserva velocidade e simplicidade local.
- `Consulta.filtros` usa `JSONB`, que é específico de PostgreSQL e impede `Base.metadata.create_all()` no SQLite.
- `DecisaoRepository.count_by_periodo()` usa `to_char`, que também é específico de PostgreSQL.
- Nenhum desses dois pontos parece depender de operadores exclusivos de `JSONB` ou de formatação SQL que justifique forçar Postgres para toda a suíte.

## Chosen Approach
1. Tornar o schema de `Consulta.filtros` portátil:
   usar o tipo genérico `JSON` com variante PostgreSQL `JSONB` via `with_variant(...)`.
2. Tornar `count_by_periodo()` portátil:
   refatorar a agregação para uma forma compatível com SQLite e PostgreSQL, ou encapsular a diferença por dialeto.
3. Manter Postgres como **suite opcional e específica**, apenas se surgirem caminhos realmente dependentes de recursos exclusivos do banco.

## Practical Consequences
- `unit`: continua sem banco real.
- `integration`: roda localmente com SQLite in-memory depois dos ajustes de compatibilidade.
- `api`: usa overrides/seams e não deve depender do vendor do banco.
- Se um teste precisar de comportamento estritamente PostgreSQL, ele deve receber marker próprio, por exemplo `integration_pg`, em vez de contaminar a suíte principal.

## Follow-up
- Ajustar `app/models/consulta.py`
- Ajustar `app/repositories/decisao_repo.py`
- Atualizar `tests/conftest.py` para subir o metadata completo
- Só então avançar para `T2`, `T6a` e `T6b`
