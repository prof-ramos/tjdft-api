# Configuração do MCP

Este documento descreve as variáveis de ambiente usadas pela camada MCP do projeto.

## Variáveis base da aplicação

| Variável | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `DATABASE_URL` | string | `sqlite+aiosqlite:///./tjdft.db` | URL de conexão do banco |
| `OPENAI_API_KEY` | string opcional | vazio | Chave da OpenAI para funcionalidades de IA |
| `REDIS_URL` | string | `redis://localhost:6379` | URL do Redis para cache |
| `CACHE_TTL` | inteiro | `3600` | TTL default do cache em segundos |
| `APP_NAME` | string | `TJDFT API` | Nome da aplicação |
| `APP_VERSION` | string | `1.0.0` | Versão da aplicação |
| `DEBUG` | boolean | `false` | Habilita logs/debug adicionais |
| `CORS_ORIGINS` | JSON array | `["http://localhost:3000","http://localhost:8000"]` | Origens permitidas |

## Variáveis da camada MCP

| Variável | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `MCP_CHARACTER_LIMIT` | inteiro | `25000` | Limite máximo de caracteres por resposta de tool |
| `MCP_ENABLE_AI_TOOLS` | boolean | `false` | Habilita tools opcionais baseadas em IA |
| `MCP_REQUEST_TIMEOUT_SECONDS` | float | `30.0` | Timeout padrão para chamadas externas no runtime MCP |

## Observações

- O arquivo `.env.example` é o contrato de configuração para desenvolvimento.
- Existe teste automático para garantir que `.env.example` e `Settings` permaneçam sincronizados.
