# Uso

## Endpoints

### Health Check

```bash
curl http://localhost:8000/health
```

### Busca Simples

```bash
curl "http://localhost:8000/api/v1/busca/?q=tributário&pagina=1&limite=20"
```

### Busca com Filtros

```bash
curl "http://localhost:8000/api/v1/busca/filtros?q=tributário&relator=Silva"
```

### Histórico de Consultas

```bash
curl "http://localhost:8000/api/v1/busca/historico?limite=10"
```

## Documentação Interativa

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc