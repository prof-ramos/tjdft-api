# Cliente TJDFT - Melhorias Implementadas

## 📋 Sumário das Melhorias

### 1. ✅ Timeouts + Retry Configuráveis
- Timeout configurável via `timeout` (default: 30.0s)
- Número máximo de retries configurável via `max_retries` (default: 3)
- Delay base configurável via `retry_delay` (default: 1.0s)
- Limite de conexões configurável (max_keepalive_connections: 5, max_connections: 10)

### 2. ✅ Retry com Exponential Backoff
- Implementação do método `_request_with_retry()`
- Backoff exponencial: `delay = retry_delay * (2 ** attempt)`
- Retries para: TimeoutException, NetworkError, HTTPStatusError (5xx)
- Logs estruturados em cada tentativa de retry

### 3. ✅ Rate Limiting Local
- Implementação da classe `RateLimiter` com Token Bucket
- Rate padrão: 2 requisições/segundo
- Rate configurável via `rate_limit` no construtor
- Context manager assíncrono para uso simples: `async with self._rate_limiter:`

### 4. ✅ Fallback Graceful
- Nova classe `TJDFTResponse` (dataclass)
- Todos os métodos retornam `TJDFTResponse` em vez de levantar exceções
- Flags: `success`, `data`, `error`, `cached`, `fallback`
- Mensagens de erro amigáveis para o usuário final

### 5. ✅ Logs Estruturados
- Classe `StructuredFormatter` para logs em JSON
- Logger configurado como `"tjdft_client"`
- Logs com timestamp, level, message, module, function
- Suporte a `extra_data` para contexto adicional
- Logs informativos em pontos-chave (cache hit, busca iniciada, etc.)

### 6. ✅ Validação de Resposta
- Schemas Pydantic: `TJDFTItem` e `TJDFTSearchResult`
- Método `_validate_response()` para validar formato da API
- Validação de campos obrigatórios e tipos
- Logs de aviso quando resposta inválida é detectada

---

## 📝 Mudanças Implementadas

### Arquivo: `/root/projetos/tjdft-api/app/services/tjdft_client.py`

#### Novas Importações

```python
import asyncio
import hashlib
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx  # Substituí httpx individual por import completo
from pydantic import BaseModel, ValidationError
```

#### Novas Classes

**1. `StructuredFormatter`**
- Formata logs em JSON estruturado
- Adiciona timestamp, level, module, function
- Suporta `extra_data` para contexto

**2. `TJDFTItem` (Pydantic)**
- Schema para item de jurisprudência
- Campos: id, numero_processo, ementa, relator, data_julgamento, orgao_julgador, classe
- Todos os campos são Optional

**3. `TJDFTSearchResult` (Pydantic)**
- Schema para resposta de busca
- Campos: total, itens (List[TJDFTItem]), pagina, tamanho_pagina

**4. `TJDFTResponse` (dataclass)**
- Resposta padrão com fallback graceful
- Campos: success (bool), data (Optional[dict]), error (Optional[str]), cached (bool), fallback (bool)

**5. `RateLimiter`**
- Implementação de Token Bucket
- Configuração de rate (req/s)
- Métodos: `__init__`, `acquire`, `__aenter__`, `__aexit__`

#### Mudanças em `TJDFTClient.__init__()`

```python
def __init__(
    self,
    cache_manager: CacheManager,
    timeout: float = 30.0,           # NOVO: Timeout configurável
    max_retries: int = 3,             # NOVO: Max retries configurável
    retry_delay: float = 1.0,         # NOVO: Retry delay configurável
    rate_limit: float = 2.0,          # NOVO: Rate limit configurável
):
    self.cache = cache_manager
    self.timeout = timeout            # NOVO: Armazena timeout
    self.max_retries = max_retries    # NOVO: Armazena max_retries
    self.retry_delay = retry_delay    # NOVO: Armazena retry_delay
    self._client: Optional[httpx.AsyncClient] = None
    self._rate_limiter = RateLimiter(rate=rate_limit)  # NOVO: Rate limiter
```

#### Mudanças em `TJDFTClient.__aenter__()`

```python
async def __aenter__(self):
    self._client = httpx.AsyncClient(
        timeout=httpx.Timeout(self.timeout),  # NOVO: Usa timeout configurável
        limits=httpx.Limits(                  # NOVO: Limites de conexão
            max_keepalive_connections=5,
            max_connections=10
        ),
        follow_redirects=True,
        headers={
            "User-Agent": "TJDFT-API/1.0",
            "Accept": "application/json",
        }
    )
    return self
```

#### Novo Método: `_request_with_retry()`

```python
async def _request_with_retry(
    self,
    method: str,
    url: str,
    **kwargs
) -> dict:
    """
    Request com retry automático e backoff exponencial.

    - Tenta até self.max_retries vezes
    - Backoff exponencial: retry_delay * (2 ** attempt)
    - Retries para: TimeoutException, NetworkError, HTTPStatusError (5xx)
    - Levanta TJDFTConnectionError após esgotar retries
    """
    # Implementação com loop for e exponential backoff
```

#### Novo Método: `_validate_response()`

```python
def _validate_response(self, data: dict) -> bool:
    """
    Valida se resposta do TJDFT está no formato esperado.

    - Usa Pydantic para validação
    - Retorna True se válido, False caso contrário
    - Log de aviso quando resposta inválida é detectada
    """
    # Implementação com Pydantic validation
```

#### Mudanças em Métodos Públicos

Todos os métodos públicos agora:

1. **Retornam `TJDFTResponse`** em vez de levantar exceções
2. **Usam rate limiting** com `async with self._rate_limiter:`
3. **Tentam cache primeiro** antes de fazer requisições
4. **Validam respostas** com `_validate_response()`
5. **Tratam exceções** e retornam `TJDFTResponse` com `fallback=True`

Métodos alterados:
- `buscar_simples()` → retorna `TJDFTResponse`
- `buscar_com_filtros()` → retorna `TJDFTResponse`
- `buscar_todas_paginas()` → retorna `TJDFTResponse`
- `get_metadata()` → retorna `TJDFTResponse`

#### Adições de Logging

Logs estruturados em todos os pontos-chave:

```python
logger.info(
    "Busca iniciada",
    extra={"extra_data": {
        "query": texto,
        "pagina": pagina,
        "cache_hit": False,
    }}
)

logger.warning(
    f"Retry {attempt + 1}/{self.max_retries} em {delay}s: {e}",
    extra={"extra_data": {"delay": delay, "error": str(e)}}
)
```

---

## 💻 Exemplo de Uso

### Exemplo Básico

```python
import asyncio
from app.utils.cache import CacheManager
from app.services.tjdft_client import TJDFTClient

async def main():
    cache = CacheManager()

    # Cria cliente com configurações padrão
    async with TJDFTClient(cache) as client:
        # Busca simples
        response = await client.buscar_simples(
            texto="tributário",
            pagina=1,
            tamanho_pagina=20
        )

        # Verifica se foi bem-sucedido
        if response.success:
            print(f"✅ Sucesso!")
            print(f"📦 Cache: {response.cached}")
            print(f"📄 Resultados: {len(response.data['dados'])}")

            # Acessa os dados
            for item in response.data['dados']:
                print(f"- {item.get('numero_processo')}: {item.get('ementa', '')[:50]}...")
        else:
            print(f"❌ Erro: {response.error}")
            print(f"🔄 Fallback: {response.fallback}")

asyncio.run(main())
```

### Exemplo com Configurações Customizadas

```python
import asyncio
from app.utils.cache import CacheManager
from app.services.tjdft_client import TJDFTClient

async def main():
    cache = CacheManager()

    # Configurações customizadas
    async with TJDFTClient(
        cache_manager=cache,
        timeout=45.0,           # Timeout de 45 segundos
        max_retries=5,           # Até 5 tentativas
        retry_delay=2.0,         # Delay inicial de 2s
        rate_limit=1.0,          # 1 req/s (mais conservador)
    ) as client:
        # Busca com filtros
        response = await client.buscar_com_filtros(
            query="tributário ICMS",
            relator="Ministro João",
            classe="Apelação",
            data_inicio="2023-01-01",
            data_fim="2023-12-31",
            pagina=1,
            tamanho_pagina=50
        )

        if response.success:
            dados = response.data
            paginacao = dados.get('paginacao', {})

            print(f"Total: {paginacao.get('total', 0)}")
            print(f"Página: {paginacao.get('pagina', 1)}")
            print(f"Cache: {response.cached}")
        else:
            print(f"Erro: {response.error}")

asyncio.run(main())
```

### Exemplo Multi-Página

```python
import asyncio
from app.utils.cache import CacheManager
from app.services.tjdft_client import TJDFTClient

async def main():
    cache = CacheManager()

    async with TJDFTClient(cache) as client:
        # Busca todas as páginas até max_paginas
        response = await client.buscar_todas_paginas(
            query="direito tributário",
            max_paginas=5,
            tamanho_pagina=20
        )

        if response.success:
            todos_resultados = response.data['dados']
            print(f"📊 Total de resultados: {len(todos_resultados)}")
        else:
            print(f"❌ Erro: {response.error}")

asyncio.run(main())
```

### Exemplo com Tratamento de Erros

```python
import asyncio
from app.utils.cache import CacheManager
from app.services.tjdft_client import TJDFTResponse

async def buscar_com_retry_demonstracao():
    cache = CacheManager()

    async with TJDFTClient(cache) as client:
        response = await client.buscar_simples(
            texto="termo que não existe",
            pagina=1,
            tamanho_pagina=20
        )

        # Tratamento graceful de erros
        if not response.success:
            if response.fallback:
                print("⚠️ Modo fallback ativado - resposta parcial")
            if response.cached:
                print("📦 Resposta vinda do cache")
            print(f"❌ Erro: {response.error}")
            return

        # Sucesso - processa dados
        dados = response.data['dados']
        paginacao = response.data['paginacao']

        print(f"✅ Encontrados {paginacao.get('total', 0)} resultados")
        print(f"📦 Cache: {response.cached}")

        for item in dados:
            print(f"  - {item.get('numero_processo')}")

asyncio.run(buscar_com_retry_demonstracao())
```

---

## ⚙️ Configurações Recomendadas

### Para Produção

```python
client = TJDFTClient(
    cache_manager=cache,
    timeout=30.0,          # 30 segundos é adequado para maioria das APIs
    max_retries=3,         # 3 tentativas é um bom padrão
    retry_delay=1.0,       # 1s de delay inicial
    rate_limit=2.0,        # 2 req/s respeita a maioria dos APIs
)
```

### Para Ambientes Instáveis (rede lenta ou falha)

```python
client = TJDFTClient(
    cache_manager=cache,
    timeout=60.0,          # Timeout maior
    max_retries=5,         # Mais tentativas
    retry_delay=2.0,       # Delay inicial maior
    rate_limit=1.0,        # Rate mais conservador
)
```

### Para Alta Performance (com API rápida e confiável)

```python
client = TJDFTClient(
    cache_manager=cache,
    timeout=15.0,          # Timeout menor
    max_retries=2,         # Menos tentativas
    retry_delay=0.5,       # Delay menor
    rate_limit=5.0,        # Mais requisições/segundo
)
```

### Para Testing/Desenvolvimento

```python
client = TJDFTClient(
    cache_manager=cache,
    timeout=10.0,          # Timeout menor para falhar rápido
    max_retries=1,         # Apenas 1 tentativa
    retry_delay=0.1,       # Delay mínimo
    rate_limit=10.0,       # Sem rate limit efetivo
)
```

---

## 📊 Comparativo: Antes vs Depois

| Característica | Antes | Depois |
|----------------|-------|--------|
| **Timeout** | Fixo (30.0s) | Configurável |
| **Retries** | Fixo (3) | Configurável |
| **Retry Delay** | Exponencial hardcoded | Configurável + Exponencial |
| **Rate Limiting** | ❌ Não implementado | ✅ Token Bucket configurável |
| **Fallback** | ❌ Levanta exceções | ✅ TJDFTResponse graceful |
| **Logging** | Simples (text) | ✅ Estruturado (JSON) |
| **Validação** | ❌ Não implementada | ✅ Pydantic schemas |
| **Cache** | ✅ Implementado | ✅ Mantido + melhorias |
| **Conexões** | Padrão httpx | ✅ Configurável (limits) |

---

## 🔧 Testes Recomendados

```python
import pytest
from app.services.tjdft_client import TJDFTClient, TJDFTResponse

@pytest.mark.asyncio
async def test_busca_simples_sucesso():
    """Testa busca simples com sucesso."""
    cache = CacheManager()
    async with TJDFTClient(cache) as client:
        response = await client.buscar_simples("tributário")
        assert response.success is True
        assert response.data is not None
        assert isinstance(response.data, dict)

@pytest.mark.asyncio
async def test_busca_simples_cache():
    """Testa funcionamento do cache."""
    cache = CacheManager()
    async with TJDFTClient(cache) as client:
        # Primeira chamada
        response1 = await client.buscar_simples("tributário")
        assert response1.cached is False

        # Segunda chamada (deve vir do cache)
        response2 = await client.buscar_simples("tributário")
        assert response2.cached is True

@pytest.mark.asyncio
async def test_rate_limiting():
    """Testa rate limiting."""
    cache = CacheManager()
    async with TJDFTClient(cache, rate_limit=1.0) as client:
        import time
        start = time.time()

        # 3 requisições devem levar pelo menos 2 segundos (1 req/s)
        for _ in range(3):
            await client.buscar_simples("test")

        elapsed = time.time() - start
        assert elapsed >= 2.0  # Pelo menos 2 segundos

@pytest.mark.asyncio
async def test_fallback_graceful():
    """Testa fallback graceful em caso de erro."""
    cache = CacheManager()
    async with TJDFTClient(cache) as client:
        response = await client.buscar_simples("")
        assert response.success is False
        assert response.error is not None
        assert response.fallback is True

@pytest.mark.asyncio
async def test_validacao_resposta():
    """Testa validação de resposta."""
    cache = CacheManager()
    async with TJDFTClient(cache) as client:
        assert client._validate_response({
            "dados": [],
            "paginacao": {"total": 0, "pagina": 1, "tamanho": 20}
        }) is True

        assert client._validate_response({
            "invalid": "format"
        }) is False
```

---

## 🎯 Próximos Passos Opcionais

1. **Metrics/Monitoring**: Adicionar métricas (Prometheus, Datadog)
2. **Circuit Breaker**: Implementar pattern de circuit breaker
3. **Request Tracing**: Adicionar tracing distribuído (OpenTelemetry)
4. **Batch Requests**: Suportar requisições em batch
5. **Webhook Support**: Notificações assíncronas
6. **Request Queuing**: Fila de requisições com prioridade

---

## 📄 Licença

Este código faz parte do projeto TJDFT-API e mantém a mesma licença do projeto principal.
