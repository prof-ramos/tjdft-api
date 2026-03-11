# API Reference

## Endpoints

### GET /health

Health check da aplicação.

**Response:**
```json
{
  "status": "ok"
}
```

### GET /api/v1/busca/

Busca simples de jurisprudência.

**Parâmetros:**
- `q` (string, required): Texto da busca
- `pagina` (int, optional): Página (default: 1)
- `limite` (int, optional): Resultados por página (default: 20)

**Response:**
```json
{
  "success": true,
  "query": "tributário",
  "pagina": 1,
  "limite": 20,
  "total": 100,
  "resultados": [...]
}
```

### GET /api/v1/busca/filtros

Busca avançada com filtros.

**Parâmetros:**
- `q` (string, required): Texto da busca
- `relator` (string, optional): Nome do relator
- `classe` (string, optional): Classe processual
- `orgao` (string, optional): Órgão julgador
- `data_inicio` (string, optional): Data inicial (YYYY-MM-DD)
- `data_fim` (string, optional): Data final (YYYY-MM-DD)

### GET /api/v1/busca/historico

Retorna histórico de consultas.

**Parâmetros:**
- `limite` (int, optional): Número de registros (default: 10)