# Referência da API TJDFT API

Última atualização: 11/03/2026

Esta documentação descreve a API FastAPI exposta por este repositório. Para a API pública original do TJDFT consumida internamente pelo projeto, consulte [docs/tjdft_api.md](/Users/gabrielramos/tjdft-api/docs/tjdft_api.md).

## Visão geral

- Base URL local: `http://127.0.0.1:8000`
- Versão da API: `v1`
- Autenticação: nenhuma
- Content-Type: `application/json`
- Documentação interativa:
  - Swagger UI: `GET /docs`
  - ReDoc: `GET /redoc`
  - OpenAPI: `GET /openapi.json`

## Endpoints

### `GET /`

Retorna informações básicas da aplicação.

#### Exemplo de resposta

```json
{
  "message": "TJDFT API",
  "version": "0.1.0",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

### `GET /health`

Health check simples para monitoramento.

#### Exemplo de resposta

```json
{
  "status": "healthy"
}
```

### `POST /api/v1/busca/`

Busca decisões judiciais e devolve resultados enriquecidos com informações de instância, relevância e densidade.

#### Query params opcionais

| Parâmetro | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `excluir_turmas_recursais` | `boolean` | `false` | Remove resultados classificados como `juizado_especial` |
| `apenas_ativos` | `boolean` | `false` | Mantém apenas resultados com `relatorAtivo=true` |

#### Corpo da requisição

| Campo | Tipo | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- | --- |
| `query` | `string` | sim | — | Termo de busca. O contrato público exige pelo menos 1 caractere |
| `filtros` | `object \| null` | não | `null` | Filtros adicionais |
| `pagina` | `integer` | não | `1` | Página solicitada, indexada a partir de 1 |
| `tamanho` | `integer` | não | `20` | Quantidade de resultados por página |
| `excluir_turmas_recursais` | `boolean \| null` | não | `null` | Também aceito no corpo, mas os query params sobrescrevem esse valor |
| `apenas_ativos` | `boolean \| null` | não | `null` | Também aceito no corpo, mas os query params sobrescrevem esse valor |

#### Filtros suportados hoje

Os filtros efetivamente processados pela API do projeto são:

| Chave em `filtros` | Tipo esperado | Exemplo | Observação |
| --- | --- | --- | --- |
| `relator` | `string` | `"desembargador-faustolo"` | Validado contra `data/referencia.json` |
| `classe` | `string` | `"APC"` | Validado contra `data/referencia.json` |
| `orgao_julgador` | `string` | `"6CC"` | Validado contra `data/referencia.json` |

Observações:

- Os valores aceitos são códigos/identificadores internos do projeto, não necessariamente os nomes completos exibidos pelo TJDFT.
- Chaves fora dessa lista não fazem parte do contrato documentado desta API.

#### Exemplo de requisição

```json
{
  "query": "tributário",
  "filtros": {
    "relator": "desembargador-faustolo",
    "classe": "APC",
    "orgao_julgador": "6CC"
  },
  "pagina": 1,
  "tamanho": 5
}
```

#### Exemplo de resposta `200 OK`

```json
{
  "resultados": [
    {
      "uuid": "uuid-1",
      "numeroProcesso": "0700001-00.2024.8.07.0001",
      "ementa": "Apelação cível. Direito tributário. Repetição de indébito.",
      "inteiroTeorHtml": null,
      "nomeRelator": "Relator Teste",
      "dataJulgamento": "2024-01-10",
      "dataPublicacao": "2024-01-11",
      "descricaoOrgaoJulgador": "1ª Câmara Cível",
      "descricaoClasseCnj": "Apelação Cível",
      "resumo_relevancia": {
        "tema": "tributário"
      },
      "instancia": "tjdft_2a_instancia",
      "relatorAtivo": true
    }
  ],
  "total": 42,
  "total_filtrado": 10,
  "pagina": 1,
  "tamanho": 5,
  "consulta_id": "123e4567-e89b-12d3-a456-426614174000",
  "densidade": {
    "categoria": "moderado"
  }
}
```

#### Campos de resposta

##### Envelope

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `resultados` | `array` | Lista de decisões enriquecidas |
| `total` | `integer` | Total encontrado antes dos filtros em runtime |
| `total_filtrado` | `integer` | Total após aplicar `excluir_turmas_recursais` e `apenas_ativos` |
| `pagina` | `integer` | Página atual |
| `tamanho` | `integer` | Tamanho da página |
| `consulta_id` | `string` | UUID da consulta persistida |
| `densidade` | `object \| null` | Métricas agregadas da busca |

##### Item de `resultados`

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `uuid` | `string \| null` | Identificador TJDFT da decisão |
| `numeroProcesso` | `string \| null` | Número do processo |
| `ementa` | `string \| null` | Ementa da decisão |
| `inteiroTeorHtml` | `string \| null` | Inteiro teor em HTML, quando disponível |
| `nomeRelator` | `string \| null` | Nome do relator |
| `dataJulgamento` | `string(date) \| null` | Data de julgamento |
| `dataPublicacao` | `string(date) \| null` | Data de publicação |
| `descricaoOrgaoJulgador` | `string \| null` | Órgão julgador |
| `descricaoClasseCnj` | `string \| null` | Classe processual |
| `resumo_relevancia` | `object \| null` | Marcadores resumidos de relevância |
| `instancia` | `string \| null` | Valor enriquecido: `juizado_especial` ou `tjdft_2a_instancia` |
| `relatorAtivo` | `boolean \| null` | Indica se o relator está marcado como ativo |

## Exemplos de consumo

### cURL

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/busca/?apenas_ativos=true" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tributário",
    "filtros": {
      "relator": "desembargador-faustolo",
      "classe": "APC"
    },
    "pagina": 1,
    "tamanho": 5
  }'
```

### JavaScript

```javascript
const response = await fetch(
  "http://127.0.0.1:8000/api/v1/busca/?excluir_turmas_recursais=true",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      query: "tributário",
      filtros: {
        classe: "APC",
        orgao_julgador: "6CC"
      },
      pagina: 1,
      tamanho: 10
    })
  }
);

const data = await response.json();
console.log(data);
```

### Python com `httpx`

```python
import httpx

payload = {
    "query": "tributário",
    "filtros": {
        "relator": "desembargador-faustolo",
        "classe": "APC",
    },
    "pagina": 1,
    "tamanho": 5,
}

response = httpx.post(
    "http://127.0.0.1:8000/api/v1/busca/",
    params={"apenas_ativos": True},
    json=payload,
    timeout=30.0,
)

response.raise_for_status()
print(response.json())
```

## Erros e validação

### `422 Unprocessable Entity`

Retornado quando o payload não atende ao schema da API.

Exemplo para `query` vazia:

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "query"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {
        "min_length": 1
      }
    }
  ]
}
```

### `5xx`

Falhas internas ou problemas na API upstream do TJDFT podem resultar em erro `5xx`. Como não há um handler customizado para essas exceções no projeto hoje, o formato exato da resposta pode variar conforme o tipo da falha.

## Boas práticas de uso

- Use `GET /health` em monitoramento e readiness checks.
- Prefira consultar `GET /openapi.json` ou `/docs` quando precisar gerar clientes automaticamente.
- Em integrações, trate `422` como erro de contrato e `5xx` como erro transitório.
- Se precisar entender a origem dos dados e limites da busca do tribunal, consulte [docs/tjdft_api.md](/Users/gabrielramos/tjdft-api/docs/tjdft_api.md).
